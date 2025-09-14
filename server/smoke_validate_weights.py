"""
Validate tuned fallback weights against feedback labels (no numpy/sklearn).

Computes ROC-AUC for:
- tuned weights from server/artifacts/weights.json
- equal weights baseline
- default legacy weights (4 or 5 dims)

Also prints simple risk distribution using thresholds:
  High>=0.85, Medium>=0.70, Low>=0.50, else Normal

Run: python server/smoke_validate_weights.py
"""

import json
import os
import random
import sqlite3
from bisect import bisect_left, bisect_right
from typing import List, Tuple


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DATA_DIR, "feedback.db")
ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
WEIGHTS_PATH = os.path.join(ARTIFACTS_DIR, "weights.json")


def load_feedback() -> Tuple[List[List[float]], List[int]]:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(feedback)")
        cols = [r[1] for r in cur.fetchall()]
        base = ["jaccard", "tfidf", "ngram", "paraphrase"]
        if "re_rank_score" in cols:
            sel = base + ["re_rank_score", "label"]
        else:
            sel = base + ["label"]
        cur.execute(
            "SELECT " + ", ".join(sel) + " FROM feedback WHERE jaccard IS NOT NULL"
        )
        rows = cur.fetchall()
    X: List[List[float]] = []
    y: List[int] = []
    for row in rows:
        *feats, lab = row
        X.append([float(v if v is not None else 0.0) for v in feats])
        y.append(int(lab))
    return X, y


def auc_from_scores(y: List[int], scores: List[float]) -> float:
    pos = [s for s, lab in zip(scores, y) if lab == 1]
    neg = [s for s, lab in zip(scores, y) if lab == 0]
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    neg_sorted = sorted(neg)
    better = 0.0
    for s in pos:
        lt = bisect_left(neg_sorted, s)
        rt = bisect_right(neg_sorted, s)
        better += lt + 0.5 * (rt - lt)
    return float(better / (n_pos * n_neg))


def dot(u: List[float], v: List[float]) -> float:
    return sum((a * b for a, b in zip(u, v)))


def main():
    X, y = load_feedback()
    dim = len(X[0]) if X else 0
    if dim == 0:
        print("No features found.")
        return
    # Load tuned weights
    tuned = None
    if os.path.exists(WEIGHTS_PATH):
        with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            tuned = [float(w) for w in data.get("weights", [])]
            if len(tuned) != dim:
                tuned = None
    equal = [1.0 / dim for _ in range(dim)]
    if dim == 5:
        default = [0.18, 0.18, 0.09, 0.40, 0.15]
    else:
        default = [0.18, 0.18, 0.09, 0.40]

    def scores_for(w: List[float]) -> List[float]:
        return [dot(row, w) for row in X]

    res = {}
    res["equal_auc"] = auc_from_scores(y, scores_for(equal))
    res["default_auc"] = auc_from_scores(y, scores_for(default))
    if tuned is not None:
        res["tuned_auc"] = auc_from_scores(y, scores_for(tuned))
    else:
        res["tuned_auc"] = None

    # Risk distribution using tuned if present else default
    use_w = tuned or default
    scores = scores_for(use_w)
    buckets = {"High": 0, "Medium": 0, "Low": 0, "Normal": 0}
    for s in scores:
        if s >= 0.85:
            buckets["High"] += 1
        elif s >= 0.70:
            buckets["Medium"] += 1
        elif s >= 0.50:
            buckets["Low"] += 1
        else:
            buckets["Normal"] += 1

    print({"dim": dim, **res, "risk_dist": buckets, "n": len(y)})


if __name__ == "__main__":
    main()
