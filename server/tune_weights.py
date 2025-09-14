"""
Tune fallback weights for similarity features using labeled feedback.

- Loads features (jaccard, tfidf, ngram, paraphrase, re_rank_score?) and labels from server/data/feedback.db
- Optimizes non-negative weights that sum to 1 to maximize ROC-AUC on feedback
- Saves artifacts to server/artifacts/weights.json with best weights and metrics

Pure-Python implementation (no numpy/sklearn) for easy portability.

Run: python -m server.tune_weights  (from repo root) or python server/tune_weights.py
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


def load_feedback() -> Tuple[List[List[float]], List[int], List[str]]:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"DB not found: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Discover available columns
        cur.execute("PRAGMA table_info(feedback)")
        cols = [r[1] for r in cur.fetchall()]
        wanted = ["jaccard", "tfidf", "ngram", "paraphrase"]
        include_ce = "re_rank_score" in cols
        select_cols = wanted + (["re_rank_score"] if include_ce else []) + ["label"]
        sql = (
            "SELECT "
            + ", ".join(select_cols)
            + " FROM feedback WHERE jaccard IS NOT NULL"
        )
        cur.execute(sql)
        rows = cur.fetchall()
    if not rows:
        raise RuntimeError("No labeled feedback rows found.")
    X: List[List[float]] = []
    y: List[int] = []
    for row in rows:
        *feat_vals, lab = row
        feats: List[float] = [float(v if v is not None else 0.0) for v in feat_vals]
        X.append(feats)
        y.append(int(lab))
    # Feature order names (match X columns)
    if len(X[0]) == 5:
        names = ["jaccard", "tfidf", "ngram", "paraphrase", "re_rank_score"]
    else:
        names = ["jaccard", "tfidf", "ngram", "paraphrase"]
    return X, y, names


def random_simplex(dim: int) -> List[float]:
    x = [random.random() for _ in range(dim)]
    s = sum(x)
    if s == 0:
        return [1.0 / dim for _ in range(dim)]
    return [v / s for v in x]


def dot(u: List[float], v: List[float]) -> float:
    return sum((a * b for a, b in zip(u, v)))


def eval_auc(X: List[List[float]], y: List[int], w: List[float]) -> float:
    # Compute scores
    scores = [dot(row, w) for row in X]
    pos = [s for s, lab in zip(scores, y) if lab == 1]
    neg = [s for s, lab in zip(scores, y) if lab == 0]
    n_pos, n_neg = len(pos), len(neg)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    neg_sorted = sorted(neg)
    better = 0.0
    for s in pos:
        # Count negatives strictly less than s
        lt = bisect_left(neg_sorted, s)
        # Count ties
        rt = bisect_right(neg_sorted, s)
        ties = rt - lt
        better += lt + 0.5 * ties
    auc = better / (n_pos * n_neg)
    return float(auc)


def tune_weights(X: List[List[float]], y: List[int], trials: int = 5000) -> List[float]:
    dim = len(X[0])
    best_w = [1.0 / dim for _ in range(dim)]
    best_auc = eval_auc(X, y, best_w)

    # Seeded candidates: emphasize semantic features a bit more
    seeds: List[List[float]] = []
    if dim == 5:
        seeds += [
            [0.15, 0.20, 0.10, 0.35, 0.20],
            [0.10, 0.15, 0.10, 0.45, 0.20],
        ]
    else:
        seeds += [
            [0.20, 0.25, 0.15, 0.40],
            [0.15, 0.20, 0.10, 0.55],
        ]
    for s in seeds:
        s_sum = sum(s)
        s = [v / s_sum for v in s]
        auc = eval_auc(X, y, s)
        if auc > best_auc:
            best_auc, best_w = auc, s

    # Random search on simplex
    for _ in range(trials):
        w = random_simplex(dim)
        auc = eval_auc(X, y, w)
        if auc > best_auc:
            best_auc, best_w = auc, w

    return best_w


def main():
    random.seed(42)
    X, y, names = load_feedback()
    # Baselines
    dim = len(X[0])
    equal = [1.0 / dim for _ in range(dim)]
    equal_auc = eval_auc(X, y, equal)
    default = None
    default_auc = None
    if dim == 5:
        default = [0.18, 0.18, 0.09, 0.40, 0.15]
        default_auc = eval_auc(X, y, default)
    elif dim == 4:
        # Legacy fallback (no cross-encoder)
        default = [0.18, 0.18, 0.09, 0.40]
        default_auc = eval_auc(X, y, default)
    # Tune
    w = tune_weights(X, y, trials=3000)
    auc = eval_auc(X, y, w)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    payload = {
        "feature_order": names,
        "weights": [float(x) for x in w],
        "auc": float(auc),
        "n_samples": int(len(y)),
        "baseline_auc": {
            "equal": float(equal_auc),
            **({"default": float(default_auc)} if default_auc is not None else {}),
        },
    }
    with open(WEIGHTS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(
        f"Saved tuned weights to {WEIGHTS_PATH}: AUC={auc:.4f} ; weights={payload['weights']}"
    )


if __name__ == "__main__":
    main()
