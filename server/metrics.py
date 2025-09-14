"""
Shared evaluation metrics (pure-Python, no numpy/pandas dependencies).
"""

from bisect import bisect_left, bisect_right
from typing import List


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


def pr_auc(y: List[int], scores: List[float]) -> float:
    # Stepwise PR-AUC without numpy
    paired = sorted(zip(scores, y), key=lambda t: t[0], reverse=True)
    tp = 0
    fp = 0
    fn = sum(1 for _s, lab in paired if lab == 1)
    if fn == 0:
        return 0.0
    last_recall = 0.0
    area = 0.0
    for s, lab in paired:
        if lab == 1:
            tp += 1
            fn -= 1
        else:
            fp += 1
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        area += precision * max(0.0, recall - last_recall)
        last_recall = recall
    return float(area)
