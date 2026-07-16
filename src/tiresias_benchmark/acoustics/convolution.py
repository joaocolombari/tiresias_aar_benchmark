from __future__ import annotations

import numpy as np
from scipy.signal import fftconvolve


def convolve_mono_to_binaural(mono: np.ndarray, left_ir: np.ndarray, right_ir: np.ndarray) -> np.ndarray:
    left = fftconvolve(np.asarray(mono, dtype=float), np.asarray(left_ir, dtype=float), mode="full")
    right = fftconvolve(np.asarray(mono, dtype=float), np.asarray(right_ir, dtype=float), mode="full")
    return np.column_stack([left, right]).astype(np.float32)


def apply_source_gain(binaural_image: np.ndarray, gain: np.ndarray | float) -> np.ndarray:
    image = np.asarray(binaural_image, dtype=float)
    if np.isscalar(gain):
        return (image * float(gain)).astype(np.float32)
    gain_arr = np.asarray(gain, dtype=float)
    if gain_arr.ndim != 1:
        raise ValueError("time-varying gain must be a 1-D array")
    n = min(len(image), len(gain_arr))
    out = np.zeros_like(image, dtype=float)
    out[:n] = image[:n] * gain_arr[:n, None]
    if len(image) > n:
        out[n:] = image[n:]
    return out.astype(np.float32)


def sum_binaural_components(components: list[np.ndarray]) -> np.ndarray:
    if not components:
        raise ValueError("at least one component is required")
    max_len = max(len(component) for component in components)
    out = np.zeros((max_len, 2), dtype=np.float32)
    for component in components:
        out[: len(component)] += component.astype(np.float32)
    return out
