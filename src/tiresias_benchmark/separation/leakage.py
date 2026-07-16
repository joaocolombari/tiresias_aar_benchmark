from __future__ import annotations

import math

import numpy as np


def leakage_coefficient_from_sdr_db(separation_sdr_db: float | str) -> float:
    if isinstance(separation_sdr_db, str) and separation_sdr_db.lower() in {"inf", "infinity"}:
        return 0.0
    value = float(separation_sdr_db)
    if math.isinf(value):
        return 0.0
    return float(10 ** (-value / 20.0))


def delay_signal_samples(signal: np.ndarray, delay_samples: int) -> np.ndarray:
    if delay_samples < 0:
        raise ValueError("delay_samples must be non-negative")
    signal = np.asarray(signal)
    if delay_samples == 0:
        return signal.copy()
    pad_shape = list(signal.shape)
    pad_shape[0] = delay_samples
    pad = np.zeros(pad_shape, dtype=signal.dtype)
    return np.concatenate([pad, signal[:-delay_samples]], axis=0)


def mix_cross_source_leakage(
    source_a: np.ndarray,
    source_b: np.ndarray,
    leakage: float,
) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(source_a, dtype=float)
    b = np.asarray(source_b, dtype=float)
    n = min(len(a), len(b))
    ahat = a[:n] + leakage * b[:n]
    bhat = b[:n] + leakage * a[:n]
    return ahat.astype(np.float32), bhat.astype(np.float32)
