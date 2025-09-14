"""
Evaluate the trained model on feedback DB (pure Python, no numpy).

Outputs ROC-AUC and simple risk distribution using model predictions.

Run:
  python -m server.eval_model
"""

import os
import pickle
from typing import List

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "feedback_lr.pkl")

# Reuse shared loaders and metrics
try:
    from .train_feedback import load_feedback  # type: ignore
    from .metrics import auc_from_scores  # type: ignore
except Exception:
    from train_feedback import load_feedback  # type: ignore
    from metrics import auc_from_scores  # type: ignore


def main():
    if not os.path.exists(MODEL_PATH):
        print("No model found.")
        return
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    X, y = load_feedback()
    if not X:
        print("No data.")
        return
    probs = model.predict_proba(X)
    y_scores = [float(p[1]) for p in probs]
    auc = auc_from_scores(y, y_scores)
    # Risk buckets
    buckets = {"High": 0, "Medium": 0, "Low": 0, "Normal": 0}
    for s in y_scores:
        if s >= 0.85:
            buckets["High"] += 1
        elif s >= 0.70:
            buckets["Medium"] += 1
        elif s >= 0.50:
            buckets["Low"] += 1
        else:
            buckets["Normal"] += 1
    print({"n": len(y), "d": len(X[0]), "auc": auc, "risk_dist": buckets})


if __name__ == "__main__":
    main()
