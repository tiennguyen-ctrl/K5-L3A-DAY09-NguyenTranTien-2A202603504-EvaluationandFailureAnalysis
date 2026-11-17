"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
from math import comb

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError(f"length mismatch: {len(human)} human vs {len(judge)} judge labels")
    cm = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for h, j in zip(human, judge):
        if h == POS:
            cm["tp" if j == POS else "fn"] += 1
        else:
            cm["fp" if j == POS else "tn"] += 1
    return cm


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    flagged, actual = cm["tp"] + cm["fp"], cm["tp"] + cm["fn"]
    precision = cm["tp"] / flagged if flagged else 0.0
    recall = cm["tp"] / actual if actual else 0.0
    return precision, recall


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = sum(cm.values())
    if n == 0:
        raise ValueError("kappa undefined: no labels")
    p_o = (cm["tp"] + cm["tn"]) / n
    # Chance agreement from the two raters' marginal FAIL / PASS rates.
    human_fail, judge_fail = (cm["tp"] + cm["fn"]) / n, (cm["tp"] + cm["fp"]) / n
    p_e = human_fail * judge_fail + (1 - human_fail) * (1 - judge_fail)
    if p_e == 1:
        raise ValueError("kappa undefined: both raters are constant")
    return (p_o - p_e) / (1 - p_e)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denom = sensitivity + specificity - 1
    if denom <= 0:
        raise ValueError("Rogan-Gladen undefined: sensitivity + specificity <= 1 (judge no better than chance)")
    return min(1.0, max(0.0, (observed_rate + specificity - 1) / denom))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy import stats as sp_stats

    if len(a) != len(b):
        raise ValueError(f"paired samples need the same items: {len(a)} vs {len(b)}")
    if len(a) < 2:
        raise ValueError("paired bootstrap needs at least 2 items")
    x, y = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if np.array_equal(x, y):
        return (0.0, 0.0, 0.0)          # no difference anywhere: scipy would divide 0 by 0
    res = sp_stats.bootstrap(
        (x, y), lambda u, v, axis=-1: np.mean(u - v, axis=axis), paired=True, vectorized=True,
        n_resamples=n_resamples, confidence_level=confidence, method="percentile",
        rng=np.random.default_rng(rng),
    )
    ci = res.confidence_interval
    return (float(np.mean(x - y)), float(ci.low), float(ci.high))


def _check_nck(n: int, c: int, k: int) -> None:
    """Reject arguments the estimators are not defined for, instead of returning a number."""
    if n < 1 or k < 1:
        raise ValueError(f"need n >= 1 and k >= 1, got n={n}, k={k}")
    if not 0 <= c <= n:
        raise ValueError(f"passes c={c} must be within 0..n={n}")
    if k > n:
        raise ValueError(f"k={k} exceeds the number of trials n={n}")


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _check_nck(n, c, k)
    if n - c < k:
        return 1.0                      # fewer than k failures: every draw of k contains a pass
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _check_nck(n, c, k)
    return comb(c, k) / comb(n, k)
