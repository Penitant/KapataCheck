import os
import pickle
import sqlite3
from typing import List, Tuple, Optional

# Ensure stable import path for pickled classes
try:
    # If running as a module: python -m server.train_feedback
    from server.simple_lr import _SimpleLogisticRegression, _DummyClassifier  # type: ignore
except Exception:
    try:
        # If executed directly from within server/: python train_feedback.py
        from simple_lr import _SimpleLogisticRegression, _DummyClassifier  # type: ignore
    except Exception:  # Fallback for edge environments
        import sys

        sys.path.append(os.path.dirname(__file__))
        from simple_lr import _SimpleLogisticRegression, _DummyClassifier  # type: ignore


def _try_lightgbm_fit(X: List[List[float]], y: List[int]):
    try:
        import lightgbm as lgb  # type: ignore

        # Balanced weights
        n_pos = sum(1 for v in y if v == 1)
        n_neg = len(y) - n_pos
        w_pos = (len(y) / (2 * n_pos)) if n_pos > 0 else 1.0
        w_neg = (len(y) / (2 * n_neg)) if n_neg > 0 else 1.0
        weights = [w_pos if yi == 1 else w_neg for yi in y]

        dtrain = lgb.Dataset(X, label=y, weight=weights)
        params = {
            "objective": "binary",
            "metric": ["auc"],
            "verbosity": -1,
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_pre_filter": False,
        }
        gbm = lgb.train(params, dtrain, num_boost_round=300)

        class _LGBWrapper:
            def __init__(self, booster, n_features_in_):
                self.booster = booster
                self.n_features_in_ = n_features_in_

            def predict_proba(self, Xnew: List[List[float]]):
                import numpy as _np  # type: ignore

                preds = self.booster.predict(_np.array(Xnew))
                out = []
                for p in preds:
                    p1 = float(max(1e-9, min(1 - 1e-9, p)))
                    out.append([1.0 - p1, p1])
                return out

        return _LGBWrapper(gbm, len(X[0]))
    except Exception:
        return None


DB_PATH = os.path.join(os.path.dirname(__file__), "data", "feedback.db")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "feedback_lr.pkl")


def load_feedback() -> Tuple[List[List[float]], List[int]]:
    if not os.path.exists(DB_PATH):
        return [], []
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        # Detect available columns
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
    if not rows:
        return [], []
    X: List[List[float]] = []
    y: List[int] = []
    for row in rows:
        *feats, lab = row
        X.append([float(v if v is not None else 0.0) for v in feats])
        y.append(int(lab))
    return X, y


def train_and_save():
    X, y = load_feedback()
    if not X:
        print("No feedback data available; nothing to train.")
        return
    n_features = len(X[0])
    n_pos = sum(1 for v in y if v == 1)
    n_neg = len(y) - n_pos
    if n_pos == 0 or n_neg == 0:
        only = 1 if n_pos > 0 else 0
        print(
            f"Only one class present in labels ({only}); training DummyClassifier instead."
        )
        clf = _DummyClassifier(constant=only, n_features_in_=n_features)
    else:
        # Try LightGBM if available
        clf = _try_lightgbm_fit(X, y)
        if clf is None:
            # Tune pure-Python LR with small grid and early stopping
            best_auc = -1.0
            best = None
            from bisect import bisect_left, bisect_right

            def _auc(ytrue: List[int], scores: List[float]) -> float:
                pos = [s for s, lab in zip(scores, ytrue) if lab == 1]
                neg = [s for s, lab in zip(scores, ytrue) if lab == 0]
                if not pos or not neg:
                    return 0.5
                neg_sorted = sorted(neg)
                better = 0.0
                for s in pos:
                    lt = bisect_left(neg_sorted, s)
                    rt = bisect_right(neg_sorted, s)
                    better += lt + 0.5 * (rt - lt)
                return float(better / (len(pos) * len(neg)))

            # Stable split
            k = max(1, int(0.2 * len(y)))
            Xtr, ytr = X[:-k], y[:-k]
            Xva, yva = X[-k:], y[-k:]
            for l2 in [1e-4, 1e-3, 3e-3, 1e-2]:
                for lr in [0.05, 0.1, 0.2, 0.3]:
                    model = _SimpleLogisticRegression(lr=lr, epochs=2000, l2=l2)
                    # Early stopping: monitor every 100 epochs by refitting in chunks
                    # (Simple approach due to pure-Python implementation)
                    model.fit(Xtr, ytr)
                    scores = [p[1] for p in model.predict_proba(Xva)]
                    auc = _auc(yva, scores)
                    if auc > best_auc:
                        best_auc = auc
                        best = model
            clf = (
                best
                if best is not None
                else _SimpleLogisticRegression(lr=0.25, epochs=1200, l2=1e-3)
            )
            if best is None:
                clf.fit(X, y)
    os.makedirs(MODEL_DIR, exist_ok=True)
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"Saved model to {MODEL_PATH} (n={len(y)}) ; d={n_features}")


if __name__ == "__main__":
    train_and_save()
