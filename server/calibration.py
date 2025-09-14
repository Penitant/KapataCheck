"""
Model calibration utilities: Platt scaling (logistic) and Isotonic regression
on top of model scores using held-out validation data.

Usage:
  python -m server.calibration --split 0.2

This reads features+labels from the feedback DB, performs a stable split,
fits calibrators, reports ROC-AUC and PR-AUC, and saves calibrators under
server/models/ (platt.pkl / isotonic.pkl). At inference, learn.get_smart_score
can apply a chosen calibrator (if present) to model probabilities.
"""

import os
import pickle
import sqlite3
from typing import List, Tuple

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.db")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
PLATT_PATH = os.path.join(MODEL_DIR, "platt.pkl")
ISOTONIC_PATH = os.path.join(MODEL_DIR, "isotonic.pkl")

# Shared metrics
try:
    from .metrics import auc_from_scores, pr_auc  # type: ignore
except Exception:
    from metrics import auc_from_scores, pr_auc  # type: ignore


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


class Platt:
    # Simple logistic calibration: p' = 1 / (1 + exp(A * s + B))
    def __init__(self):
        self.A = 0.0
        self.B = 0.0

    @staticmethod
    def _sigmoid(z: float) -> float:
        import math

        if z < -35:
            return 1e-15
        if z > 35:
            return 1 - 1e-15
        return 1.0 / (1.0 + math.exp(-z))

    def fit(
        self, scores: List[float], y: List[int], lr: float = 0.1, epochs: int = 800
    ):
        A, B = 0.0, 0.0
        n = len(scores)
        for _ in range(epochs):
            gA = 0.0
            gB = 0.0
            for s, yi in zip(scores, y):
                p = self._sigmoid(A * s + B)
                err = p - (1.0 if yi == 1 else 0.0)
                gA += err * s
                gB += err
            A -= lr * (gA / max(1, n))
            B -= lr * (gB / max(1, n))
        self.A, self.B = A, B

    def predict(self, scores: List[float]) -> List[float]:
        return [self._sigmoid(self.A * s + self.B) for s in scores]


class Isotonic:
    # Pool-adjacent-violators algorithm (PAVA)
    def __init__(self):
        self.x: List[float] = []
        self.y: List[float] = []

    def fit(self, scores: List[float], y: List[int]):
        pairs = sorted(zip(scores, y), key=lambda t: t[0])
        self.x = [s for s, _ in pairs]
        # running mean with PAVA
        blocks = [[lab] for _s, lab in pairs]
        means = [sum(b) / len(b) for b in blocks]
        i = 0
        while i < len(means) - 1:
            if means[i] <= means[i + 1]:
                i += 1
            else:
                # merge blocks i and i+1
                merged = blocks[i] + blocks[i + 1]
                blocks[i : i + 2] = [merged]
                means[i : i + 2] = [sum(merged) / len(merged)]
                i = max(0, i - 1)
        self.y = means

    def predict(self, scores: List[float]) -> List[float]:
        if not self.x:
            return scores
        out: List[float] = []
        j = 0
        for s in sorted(scores):
            # find last x[j] <= s
            while j + 1 < len(self.x) and self.x[j + 1] <= s:
                j += 1
            out.append(self.y[j])
        return out


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Calibrate model probabilities with held-out feedback"
    )
    parser.add_argument(
        "--split", type=float, default=0.2, help="Validation split fraction [0,1)"
    )
    args = parser.parse_args()

    from .train_feedback import load_feedback  # reuse same loader

    X, y = load_feedback()
    if not X:
        print("No feedback data available")
        return

    # Stable split by index
    n = len(y)
    k = max(1, int(args.split * n))
    X_train, X_val = X[:-k], X[-k:]
    y_train, y_val = y[:-k], y[-k:]

    # Load model and get scores on val
    from .learn import maybe_reload_model, predict_proba_bulk

    maybe_reload_model()
    scores_val = predict_proba_bulk(X_val)
    if scores_val is None:
        print("No model loaded; train a model first: python -m server.train_feedback")
        return

    # Metrics before calibration
    auc_before = auc_from_scores(y_val, scores_val)
    pr_before = pr_auc(y_val, scores_val)

    # Fit Platt and Isotonic
    platt = Platt()
    platt.fit(scores_val, y_val)
    iso = Isotonic()
    iso.fit(scores_val, y_val)

    # Scores after calibration
    scores_platt = platt.predict(scores_val)
    scores_iso = iso.predict(scores_val)
    auc_platt = auc_from_scores(y_val, scores_platt)
    pr_platt = pr_auc(y_val, scores_platt)
    auc_iso = auc_from_scores(y_val, scores_iso)
    pr_iso = pr_auc(y_val, scores_iso)

    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(PLATT_PATH, "wb") as f:
        pickle.dump(platt, f)
    with open(ISOTONIC_PATH, "wb") as f:
        pickle.dump(iso, f)

    print(
        {
            "n_val": len(y_val),
            "auc_before": auc_before,
            "pr_before": pr_before,
            "auc_platt": auc_platt,
            "pr_platt": pr_platt,
            "auc_iso": auc_iso,
            "pr_iso": pr_iso,
            "paths": {"platt": PLATT_PATH, "isotonic": ISOTONIC_PATH},
        }
    )


if __name__ == "__main__":
    main()
