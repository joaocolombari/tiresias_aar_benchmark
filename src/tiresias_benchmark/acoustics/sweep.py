from __future__ import annotations

import numpy as np


def exponential_sine_sweep(
    duration_s: float,
    sample_rate_hz: int,
    start_hz: float = 20.0,
    stop_hz: float = 20_000.0,
    amplitude: float = 0.5,
) -> np.ndarray:
    if duration_s <= 0 or sample_rate_hz <= 0:
        raise ValueError("duration_s and sample_rate_hz must be positive")
    t = np.arange(int(round(duration_s * sample_rate_hz)), dtype=float) / sample_rate_hz
    k = duration_s / np.log(stop_hz / start_hz)
    phase = 2.0 * np.pi * start_hz * k * (np.exp(t / k) - 1.0)
    sweep = amplitude * np.sin(phase)
    fade_n = min(len(sweep) // 10, int(0.02 * sample_rate_hz))
    if fade_n > 0:
        fade = 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, fade_n))
        sweep[:fade_n] *= fade
        sweep[-fade_n:] *= fade[::-1]
    return sweep.astype(np.float32)


def sweep_with_silence(
    sweep: np.ndarray,
    sample_rate_hz: int,
    pre_silence_s: float = 1.0,
    post_silence_s: float = 2.0,
) -> np.ndarray:
    pre = np.zeros(int(round(pre_silence_s * sample_rate_hz)), dtype=np.float32)
    post = np.zeros(int(round(post_silence_s * sample_rate_hz)), dtype=np.float32)
    return np.concatenate([pre, sweep.astype(np.float32), post])
