from __future__ import annotations

import numpy as np


def regularized_deconvolution(
    recorded: np.ndarray,
    reference: np.ndarray,
    regularization: float = 1e-8,
    response_length_samples: int | None = None,
) -> np.ndarray:
    recorded = np.asarray(recorded, dtype=float)
    reference = np.asarray(reference, dtype=float)
    n_fft = 1 << int(np.ceil(np.log2(len(recorded) + len(reference) - 1)))
    y = np.fft.rfft(recorded, n=n_fft)
    x = np.fft.rfft(reference, n=n_fft)
    h = np.fft.irfft(y * np.conj(x) / (np.abs(x) ** 2 + regularization), n=n_fft)
    if response_length_samples is not None:
        h = h[:response_length_samples]
    return h.astype(np.float32)


def trim_response_around_peak(
    response: np.ndarray,
    pre_samples: int = 32,
    length_samples: int = 14_400,
) -> np.ndarray:
    response = np.asarray(response)
    peak = int(np.argmax(np.abs(response)))
    start = max(0, peak - pre_samples)
    end = start + length_samples
    trimmed = response[start:end]
    if len(trimmed) < length_samples:
        trimmed = np.pad(trimmed, (0, length_samples - len(trimmed)))
    return trimmed.astype(np.float32)
