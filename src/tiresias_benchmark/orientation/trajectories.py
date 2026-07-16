from __future__ import annotations

import numpy as np


def minimum_jerk_turn(
    start_deg: float,
    stop_deg: float,
    duration_s: float,
    sample_rate_hz: float,
) -> tuple[np.ndarray, np.ndarray]:
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    n = max(2, int(round(duration_s * sample_rate_hz)))
    t = np.arange(n, dtype=float) / sample_rate_hz
    u = np.clip(t / duration_s, 0.0, 1.0)
    profile = 10 * u**3 - 15 * u**4 + 6 * u**5
    yaw = start_deg + (stop_deg - start_deg) * profile
    return t, yaw


def hold_turn_hold(
    start_deg: float,
    stop_deg: float,
    angular_velocity_deg_s: float,
    hold_s: float,
    sample_rate_hz: float,
) -> tuple[np.ndarray, np.ndarray]:
    if angular_velocity_deg_s <= 0:
        raise ValueError("angular_velocity_deg_s must be positive")
    turn_duration_s = abs(stop_deg - start_deg) / angular_velocity_deg_s
    hold_n = int(round(hold_s * sample_rate_hz))
    _, turn = minimum_jerk_turn(start_deg, stop_deg, turn_duration_s, sample_rate_hz)
    yaw = np.concatenate(
        [
            np.full(hold_n, start_deg, dtype=float),
            turn,
            np.full(hold_n, stop_deg, dtype=float),
        ]
    )
    t = np.arange(len(yaw), dtype=float) / sample_rate_hz
    return t, yaw
