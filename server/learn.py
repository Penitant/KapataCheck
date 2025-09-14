import os
from os import path
import pickle
import json
from typing import Dict, List, Optional

MODEL_DIR = path.join(path.dirname(__file__), "models")
MODEL_PATH = path.join(MODEL_DIR, "feedback_lr.pkl")
ARTIFACTS_DIR = path.join(path.dirname(__file__), "artifacts")
WEIGHTS_PATH = path.join(ARTIFACTS_DIR, "weights.json")
PLATT_PATH = path.join(MODEL_DIR, "platt.pkl")
ISOTONIC_PATH = path.join(MODEL_DIR, "isotonic.pkl")

_loaded_lr_model = None
_last_model_mtime: float = 0.0
_weights_cache: Optional[Dict] = None
_last_weights_mtime: float = 0.0
_cal_platt = None
_cal_iso = None
_last_platt_mtime: float = 0.0
_last_iso_mtime: float = 0.0


def maybe_reload_model() -> None:
    global _loaded_lr_model, _last_model_mtime
    try:
        if path.exists(MODEL_PATH):
            mtime = path.getmtime(MODEL_PATH)
            if mtime != _last_model_mtime:
                os.makedirs(MODEL_DIR, exist_ok=True)
                with open(MODEL_PATH, "rb") as f:
                    _loaded_lr_model = pickle.load(f)
                _last_model_mtime = mtime
    except Exception:
        # Keep running even if reload fails
        pass

    # Try loading calibrators lazily
    global _cal_platt, _cal_iso, _last_platt_mtime, _last_iso_mtime
    try:
        if path.exists(PLATT_PATH):
            mtime = path.getmtime(PLATT_PATH)
            if mtime != _last_platt_mtime:
                with open(PLATT_PATH, "rb") as f:
                    _cal_platt = pickle.load(f)
                _last_platt_mtime = mtime
    except Exception:
        pass
    try:
        if path.exists(ISOTONIC_PATH):
            mtime = path.getmtime(ISOTONIC_PATH)
            if mtime != _last_iso_mtime:
                with open(ISOTONIC_PATH, "rb") as f:
                    _cal_iso = pickle.load(f)
                _last_iso_mtime = mtime
    except Exception:
        pass


def maybe_reload_weights() -> None:
    """Reload tuned weights from artifacts if present. Silently ignore errors.

    Expected JSON structure:
    {
      "feature_order": ["jaccard","tfidf","ngram","paraphrase","re_rank_score"],
      "weights": [w1, w2, ...],
      "auc": <float>,
      ...
    }
    """
    global _weights_cache, _last_weights_mtime
    try:
        if path.exists(WEIGHTS_PATH):
            mtime = path.getmtime(WEIGHTS_PATH)
            if mtime != _last_weights_mtime:
                os.makedirs(ARTIFACTS_DIR, exist_ok=True)
                with open(WEIGHTS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Basic validation
                if (
                    isinstance(data, dict)
                    and "weights" in data
                    and isinstance(data["weights"], list)
                ):
                    _weights_cache = data
                    _last_weights_mtime = mtime
    except Exception:
        pass


def model_loaded() -> bool:
    return _loaded_lr_model is not None


def get_smart_score(similarities: Dict[str, float]) -> float:
    """Return a calibrated probability if model is available, else weighted sum.

    Feature inputs may include both core and diagnostic features:
    - Core: jaccard, tfidf, ngram, paraphrase, re_rank_score
    - Diagnostics: bm25_pair, ann_cosine, simhash, minhash, cluster_same
    """
    maybe_reload_model()
    if _loaded_lr_model is None:
        # Fallback weighted blend; prefer tuned weights if available, else defaults
        maybe_reload_weights()
        if _weights_cache and isinstance(_weights_cache.get("weights"), list):
            weights: List[float] = [float(x) for x in _weights_cache.get("weights", [])]
            # Use declared order if provided, else default order
            order: List[str] = _weights_cache.get(
                "feature_order",
                ["jaccard", "tfidf", "ngram", "paraphrase", "re_rank_score"],
            )
            # Compute dot product over available features
            s = 0.0
            for k, w in zip(order, weights):
                s += float(similarities.get(k, 0.0)) * w
            return float(s)
        # Default weights: include diagnostics with small influence; sums to 1.0 after renormalization over provided keys
        default_weights = {
            # Core
            "jaccard": 0.18,
            "tfidf": 0.27,
            "ngram": 0.23,
            "paraphrase": 0.22,
            "re_rank_score": 0.06,
            # Diagnostics (light impact by default)
            "bm25_pair": 0.02,
            "ann_cosine": 0.015,
            "simhash": 0.01,
            "minhash": 0.01,
            "cluster_same": 0.005,
        }
        # Use only provided keys and renormalize to sum=1.0
        keys = [k for k in default_weights.keys() if k in similarities]
        total = sum(default_weights[k] for k in keys) or 1.0
        s = 0.0
        for k in keys:
            w = default_weights[k] / total
            s += float(similarities.get(k, 0.0)) * w
        return float(s)
    try:
        # Support both legacy (4 features) and extended (5 features including CE) models
        expected = getattr(_loaded_lr_model, "n_features_in_", 4)
        base = [
            float(similarities.get("jaccard", 0.0)),
            float(similarities.get("tfidf", 0.0)),
            float(similarities.get("ngram", 0.0)),
            float(similarities.get("paraphrase", 0.0)),
            float(similarities.get("re_rank_score", 0.0)),
        ]
        feats = base[:expected]
        if len(feats) < expected:
            feats += [0.0] * (expected - len(feats))
        X = [feats]
        proba = _loaded_lr_model.predict_proba(X)[0][1]
        # Apply calibrator if available (prefer Platt, then Isotonic)
        if _cal_platt is not None:
            try:
                proba = _cal_platt.predict([float(proba)])[0]
            except Exception:
                pass
        elif _cal_iso is not None:
            try:
                proba = _cal_iso.predict([float(proba)])[0]
            except Exception:
                pass
        # Optionally nudge with diagnostics post-model using tiny weights to reflect ancillary signals.
        try:
            diag = 0.0
            diag += 0.02 * float(similarities.get("bm25_pair", 0.0))
            diag += 0.015 * float(similarities.get("ann_cosine", 0.0))
            diag += 0.01 * float(similarities.get("simhash", 0.0))
            diag += 0.01 * float(similarities.get("minhash", 0.0))
            diag += 0.005 * float(similarities.get("cluster_same", 0.0))
            proba = float(max(0.0, min(1.0, proba + diag)))
        except Exception:
            pass
        return float(proba)
    except Exception:
        return 0.0


def predict_proba_bulk(feature_rows: List[List[float]]):
    """Batch predict probabilities for rows [[jaccard, tfidf, ngram, paraphrase], ...].
    Returns None if model not loaded or on error.
    """
    maybe_reload_model()
    if _loaded_lr_model is None:
        return None
    try:
        expected = getattr(
            _loaded_lr_model,
            "n_features_in_",
            len(feature_rows[0]) if feature_rows else 4,
        )
        X = []
        for row in feature_rows:
            # Assume order [jaccard, tfidf, ngram, paraphrase, re_rank_score?]
            adapted = list(row[:expected])
            if len(adapted) < expected:
                adapted += [0.0] * (expected - len(adapted))
            X.append([float(v) for v in adapted])
        probs = _loaded_lr_model.predict_proba(X)
        # probs shape: (n, 2); select P(class=1) and calibrate if available
        out = [float(p[1]) for p in probs]
        if _cal_platt is not None:
            try:
                return [float(v) for v in _cal_platt.predict(out)]
            except Exception:
                return out
        if _cal_iso is not None:
            try:
                return [float(v) for v in _cal_iso.predict(out)]
            except Exception:
                return out
        return out
    except Exception:
        return None
