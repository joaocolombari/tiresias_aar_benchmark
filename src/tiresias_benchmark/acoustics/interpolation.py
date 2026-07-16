from __future__ import annotations

import numpy as np


def linear_crossfade(a: np.ndarray, b: np.ndarray, weight: float) -> np.ndarray:
    weight = float(np.clip(weight, 0.0, 1.0))
    n = min(len(a), len(b))
    out = (1.0 - weight) * np.asarray(a[:n], dtype=float) + weight * np.asarray(b[:n], dtype=float)
    return out.astype(np.float32)


def interpolate_angle_images(
    lower_image: np.ndarray,
    upper_image: np.ndarray,
    lower_angle_deg: float,
    upper_angle_deg: float,
    target_angle_deg: float,
) -> np.ndarray:
    if lower_angle_deg == upper_angle_deg:
        return np.asarray(lower_image, dtype=np.float32)
    weight = (target_angle_deg - lower_angle_deg) / (upper_angle_deg - lower_angle_deg)
    return linear_crossfade(lower_image, upper_image, weight)
