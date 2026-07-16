from __future__ import annotations

import numpy as np


def transition_time_s(
    timestamps_s: np.ndarray,
    ratio: np.ndarray,
    target_ratio: float,
    threshold_fraction: float = 0.9,
) -> float | None:
    t = np.asarray(timestamps_s, dtype=float)
    r = np.asarray(ratio, dtype=float)
    threshold = threshold_fraction * target_ratio
    hits = np.flatnonzero(r >= threshold)
    if len(hits) == 0:
        return None
    return float(t[hits[0]] - t[0])


def gain_error_rms_db(applied_gain_db: np.ndarray, ideal_gain_db: np.ndarray) -> float:
    n = min(len(applied_gain_db), len(ideal_gain_db))
    err = np.asarray(applied_gain_db[:n], dtype=float) - np.asarray(ideal_gain_db[:n], dtype=float)
    return float(np.sqrt(np.mean(err**2)))
