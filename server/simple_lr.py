import math
from typing import List


class _DummyClassifier:
    """Minimal constant-probability classifier compatible with predict_proba API."""

    def __init__(self, constant: int, n_features_in_: int):
        self.constant = 1 if constant else 0
        self.n_features_in_ = int(n_features_in_)

    def predict_proba(self, X: List[List[float]]):  # type: ignore[name-defined]
        p = 1.0 if self.constant == 1 else 0.0
        out = []
        for _ in X:
            out.append([1.0 - p, p])
        return out


class _SimpleLogisticRegression:
    """Pure-Python logistic regression with balanced class weights and L2."""

    def __init__(self, lr: float = 0.1, epochs: int = 800, l2: float = 1e-3):
        self.lr = lr
        self.epochs = epochs
        self.l2 = l2
        self.coef_: List[float] = []
        self.intercept_: float = 0.0
        self.n_features_in_: int = 0

    @staticmethod
    def _sigmoid(z: float) -> float:
        if z < -35:
            return 1e-15
        if z > 35:
            return 1.0 - 1e-15
        return 1.0 / (1.0 + math.exp(-z))

    def fit(self, X: List[List[float]], y: List[int]):
        if not X:
            raise ValueError("Empty training data")
        n, d = len(X), len(X[0])
        self.n_features_in_ = d
        self.coef_ = [0.0] * d
        self.intercept_ = 0.0

        # Balanced class weights
        n_pos = sum(1 for v in y if v == 1)
        n_neg = n - n_pos
        w_pos = (n / (2 * n_pos)) if n_pos > 0 else 1.0
        w_neg = (n / (2 * n_neg)) if n_neg > 0 else 1.0

        for _ in range(self.epochs):
            grad_w = [0.0] * d
            grad_b = 0.0
            for xi, yi in zip(X, y):
                z = self.intercept_ + sum(w * f for w, f in zip(self.coef_, xi))
                p = self._sigmoid(z)
                err = p - (1.0 if yi == 1 else 0.0)
                weight = w_pos if yi == 1 else w_neg
                for j in range(d):
                    grad_w[j] += weight * err * xi[j]
                grad_b += weight * err
            # L2
            for j in range(d):
                grad_w[j] += self.l2 * self.coef_[j]
            # Update
            for j in range(d):
                self.coef_[j] -= self.lr * (grad_w[j] / n)
            self.intercept_ -= self.lr * (grad_b / n)

    def predict_proba(self, X: List[List[float]]):
        out = []
        for xi in X:
            xi_adapt = list(xi[: self.n_features_in_])
            if len(xi_adapt) < self.n_features_in_:
                xi_adapt += [0.0] * (self.n_features_in_ - len(xi_adapt))
            z = self.intercept_ + sum(w * f for w, f in zip(self.coef_, xi_adapt))
            p1 = self._sigmoid(z)
            out.append([1.0 - p1, p1])
        return out
