from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from tiresias_benchmark.orientation.quaternion import wrap_angle_deg


@dataclass(frozen=True)
class AngularErrorStats:
    mae_deg: float
    rmse_deg: float
    bias_deg: float
    max_abs_error_deg: float


def angular_error_stats(reference_yaw_deg: np.ndarray, measured_yaw_deg: np.ndarray) -> AngularErrorStats:
    reference = np.asarray(reference_yaw_deg, dtype=float)
    measured = np.asarray(measured_yaw_deg, dtype=float)
    if reference.shape != measured.shape:
        raise ValueError("reference and measured arrays must have the same shape")
    err = circular_difference_deg(measured, reference)
    return AngularErrorStats(
        mae_deg=float(np.mean(np.abs(err))),
        rmse_deg=float(np.sqrt(np.mean(err**2))),
        bias_deg=float(np.mean(err)),
        max_abs_error_deg=float(np.max(np.abs(err))),
    )


def normalize_yaw_360_deg(yaw_deg: np.ndarray | float) -> np.ndarray | float:
    """Normalize yaw angle(s) to [0, 360)."""

    return np.mod(yaw_deg, 360.0)


def circular_difference_deg(
    measured_deg: np.ndarray | float,
    reference_deg: np.ndarray | float,
) -> np.ndarray | float:
    """Signed circular difference in [-180, 180)."""

    return np.mod(np.asarray(measured_deg) - np.asarray(reference_deg) + 180.0, 360.0) - 180.0


def circular_mean_deg(angles_deg: np.ndarray) -> float:
    angles = np.asarray(angles_deg, dtype=float)
    if len(angles) == 0:
        raise ValueError("at least one angle is required")
    radians = np.radians(angles)
    mean = np.degrees(np.arctan2(np.mean(np.sin(radians)), np.mean(np.cos(radians))))
    return float(normalize_yaw_360_deg(mean))


def drift_deg_per_minute(timestamps_s: np.ndarray, yaw_deg: np.ndarray) -> float:
    t = np.asarray(timestamps_s, dtype=float)
    y = np.unwrap(np.radians(np.asarray(yaw_deg, dtype=float)))
    if len(t) < 2:
        return 0.0
    slope_rad_s = np.polyfit(t - t[0], y, 1)[0]
    return float(np.degrees(slope_rad_s) * 60.0)
