from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from os import makedirs, path
import os as _os
import pickle
import sqlite3
from typing import List
import uuid
import time

try:
    # Preferred relative imports when running as a package
    from .db import init_db, insert_feedback, get_db_path
    from .verify import (
        analyze_files,
    )  # assuming analyze_files exists and works as before
    from .learn import get_smart_score, predict_proba_bulk, maybe_reload_model
except Exception:
    # Fallback for direct script execution
    import sys, os as __os

    sys.path.append(__os.path.dirname(__file__))
    from db import init_db, insert_feedback, get_db_path  # type: ignore
    from verify import analyze_files  # type: ignore
    from learn import get_smart_score, predict_proba_bulk, maybe_reload_model  # type: ignore

# App initialization
app = Flask(__name__)

# Allow only a specific frontend origin; no cookies/credentials are needed
ALLOWED_ORIGIN = "http://localhost:5173"
CORS(app, resources={r"/*": {"origins": [ALLOWED_ORIGIN]}}, supports_credentials=False)

# Set upload folder
UPLOAD_FOLDER = "server/uploads"
RUNS_FOLDER = path.join(UPLOAD_FOLDER, "runs")
makedirs(UPLOAD_FOLDER, exist_ok=True)
makedirs(RUNS_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Initialize SQLite DB
init_db()

# Touch the model loader on startup
maybe_reload_model()


@app.route("/")
def home():
    return "Tender similarity checking server."


@app.route("/feedback", methods=["POST"])
def collect_feedback():
    data = request.get_json(silent=True) or {}
    try:
        scores = data.get("scores", {}) or {}
        row = {
            "file1": data.get("file1"),
            "file2": data.get("file2"),
            "label": int(data.get("label")),
            "jaccard": scores.get("jaccard"),
            "ngram": scores.get("ngram"),
            "tfidf": scores.get("tfidf"),
            "paraphrase": scores.get("paraphrase"),
            "re_rank_score": scores.get("re_rank_score"),
            "score": scores.get("score"),
            "risk": scores.get("risk"),
            "model": scores.get("model"),
        }
        insert_feedback(row)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 400


def get_uncertain_pairs(threshold_low=0.4, threshold_high=0.6, limit=20):
    conn = sqlite3.connect(get_db_path())
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT file1, file2, jaccard, ngram, tfidf, paraphrase, score
        FROM feedback
        WHERE score BETWEEN ? AND ?
        ORDER BY created_at DESC
        LIMIT ?
    """,
        (threshold_low, threshold_high, limit),
    )
    results = cursor.fetchall()
    conn.close()
    pairs = []
    for row in results:
        pairs.append(
            {
                "file1": row[0],
                "file2": row[1],
                "jaccard": row[2],
                "ngram": row[3],
                "tfidf": row[4],
                "paraphrase": row[5],
                "score": row[6],
            }
        )
    return pairs


@app.route("/review")
def review():
    pairs = get_uncertain_pairs()
    return render_template("review.html", pairs=pairs)


@app.route("/retrain", methods=["POST"])
def retrain():
    import traceback as _tb

    try:
        try:
            from .train_feedback import train_and_save  # type: ignore
        except Exception:
            from train_feedback import train_and_save  # type: ignore

        train_and_save()
        maybe_reload_model()
        return jsonify({"status": "retrained"})
    except Exception as e:
        return (
            jsonify(
                {"error": "internal_error", "detail": str(e), "trace": _tb.format_exc()}
            ),
            500,
        )


@app.route("/verify", methods=["POST"])
def verify_endpoint():
    import traceback as _tb

    try:
        if "files" not in request.files:
            return jsonify({"error": "No files provided (use form field 'files')"}), 400

        files = request.files.getlist("files")
        saved_paths: List[str] = []
        original_name_by_basename = {}
        for f in files:
            if not f.filename:
                continue
            ext = path.splitext(f.filename)[1]
            unique = f"{uuid.uuid4().hex}{ext}"
            dest = path.join(app.config["UPLOAD_FOLDER"], unique)
            f.save(dest)
            saved_paths.append(dest)
            original_name_by_basename[path.basename(dest)] = f.filename

        if len(saved_paths) < 2:
            return jsonify({"error": "Need at least two files for comparison"}), 400

        model_name = request.args.get("model") or "all-mpnet-base-v2"

        # Flags (heavy features default to OFF; pass paraphrase=1, ce=1, etc. to enable)
        def _flag(name: str, default: bool = True) -> bool:
            val = request.args.get(name)
            if val is None:
                return default
            v = val.lower()
            if v in {"1", "true", "yes", "on"}:
                return True
            if v in {"0", "false", "no", "off"}:
                return False
            return default

        # Heavy/optional features default to OFF for faster local runs and tests
        use_para = _flag("paraphrase", False)
        use_ce = _flag("ce", False)
        use_hash = _flag("hash", False)
        use_hybrid = _flag("hybrid", False)
        use_cluster = _flag("cluster", False)
        try:
            ce_top_k = int(request.args.get("ce_top_k") or 10)
            if ce_top_k < 0:
                ce_top_k = 0
        except Exception:
            ce_top_k = 10
        include_timings = _flag("timings", False)

        # Diagnostics nudge level: off|low|med|high
        diag_level = (request.args.get("diag") or "med").lower()
        if diag_level not in {"off", "low", "med", "high"}:
            diag_level = "med"

        t0 = time.time()

        df = analyze_files(
            saved_paths,
            model_name=model_name,
            use_paraphrase=use_para,
            use_cross_encoder=use_ce,
            use_hash=use_hash,
            use_hybrid=use_hybrid,
            use_clustering=use_cluster,
            diag_level=diag_level,
            ce_top_k=ce_top_k,
        )
        t1 = time.time()
        results = df.to_dict(orient="records")

        # Augment with learned probabilities if a model is available
        feats = [
            [
                r.get("jaccard", 0.0),
                r.get("tfidf", 0.0),
                r.get("ngram", 0.0),
                r.get("paraphrase", 0.0),
                r.get("re_rank_score", 0.0),
            ]
            for r in results
        ]
        probs = predict_proba_bulk(feats)
        if probs is not None:
            for r, p in zip(results, probs):
                r["learned_prob"] = float(p)
                r["learned_risk"] = (
                    "High"
                    if p >= 0.85
                    else "Medium" if p >= 0.7 else "Low" if p >= 0.5 else "Normal"
                )

        # Add original filenames for client clarity (keep saved UUIDs for traceability)
        for r in results:
            b1 = r.get("file1")
            b2 = r.get("file2")
            r["original_file1"] = original_name_by_basename.get(b1, b1)
            r["original_file2"] = original_name_by_basename.get(b2, b2)

        # Persist analysis to a run folder and optionally cleanup upload temps
        run_id = uuid.uuid4().hex
        run_dir = path.join(RUNS_FOLDER, run_id)
        makedirs(run_dir, exist_ok=True)
        # Save analysis JSON and CSV in run_dir
        try:
            import json as _json
            import pandas as _pd

            _pd.DataFrame(results).to_csv(
                path.join(run_dir, "results.csv"), index=False
            )
            with open(path.join(run_dir, "results.json"), "w", encoding="utf-8") as f:
                _json.dump(results, f, ensure_ascii=False, indent=2)
            # Save meta
            meta = {
                "model": model_name,
                "paraphrase": use_para,
                "cross_encoder": use_ce,
                "hash": use_hash,
                "hybrid": use_hybrid,
                "cluster": use_cluster,
                "ce_top_k": ce_top_k,
                "count": len(results),
                "original_name_by_basename": original_name_by_basename,
                "saved_paths": saved_paths,
            }
            with open(path.join(run_dir, "meta.json"), "w", encoding="utf-8") as f:
                _json.dump(meta, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Cleanup: delete saved UUID files unless explicitly kept via ?keep=true
        keep = (request.args.get("keep") or "").lower() in {"1", "true", "yes"}
        if not keep:
            for pth in saved_paths:
                try:
                    _os.remove(pth)
                except Exception:
                    pass

        payload = {
            "model": model_name,
            "paraphrase": use_para,
            "cross_encoder": use_ce,
            "hash": use_hash,
            "hybrid": use_hybrid,
            "cluster": use_cluster,
            "ce_top_k": ce_top_k,
            "diag": diag_level,
            "count": len(results),
            "results": results,
            "run_id": run_id,
        }
        if include_timings:
            payload["timings"] = {"analyze_ms": int((t1 - t0) * 1000)}
        return jsonify(payload)
    except Exception as e:
        return (
            jsonify(
                {"error": "internal_error", "detail": str(e), "trace": _tb.format_exc()}
            ),
            500,
        )


@app.route("/prepare_feedback_folder", methods=["POST"])
def prepare_feedback_folder():
    """Create a derived folder from a run with two new columns (input_score,input_risk)."""
    import json as _json

    data = request.get_json(silent=True) or {}
    run_id = data.get("run_id")
    rows = data.get("rows") or []
    if not run_id:
        return jsonify({"error": "missing_run_id"}), 400
    run_dir = path.join(RUNS_FOLDER, run_id)
    if not path.isdir(run_dir):
        return jsonify({"error": "run_not_found"}), 404
    # Read results.csv if present
    csv_path = path.join(run_dir, "results.csv")
    json_path = path.join(run_dir, "results.json")
    try:
        import pandas as _pd

        if path.exists(csv_path):
            df = _pd.read_csv(csv_path)
        elif path.exists(json_path):
            import pandas as _pd

            with open(json_path, "r", encoding="utf-8") as f:
                df = _pd.DataFrame(_json.load(f))
        else:
            df = _pd.DataFrame([])
        # Map feedback rows by (file1,file2) using original filenames if present
        fb_map = {}
        for r in rows:
            k = (str(r.get("file1")), str(r.get("file2")))
            fb_map[k] = {
                "input_score": r.get("input_score"),
                "input_risk": r.get("input_risk"),
            }

        # Compute keys from df
        def _k(row):
            f1 = row.get("original_file1") or row.get("file1")
            f2 = row.get("original_file2") or row.get("file2")
            return (str(f1), str(f2))

        inputs_score = []
        inputs_risk = []
        for _, row in df.iterrows():
            k = _k(row)
            fb = fb_map.get(k, {})
            inputs_score.append(fb.get("input_score", ""))
            inputs_risk.append(fb.get("input_risk", ""))
        df["input_score"] = inputs_score
        df["input_risk"] = inputs_risk
        # Save to a new folder
        out_dir = path.join(run_dir, "feedback")
        makedirs(out_dir, exist_ok=True)
        df.to_csv(path.join(out_dir, "results_with_feedback.csv"), index=False)
        return jsonify({"status": "ok", "folder": out_dir})
    except Exception as e:
        return jsonify({"error": "internal_error", "detail": str(e)}), 500


if __name__ == "__main__":
    app.run()
