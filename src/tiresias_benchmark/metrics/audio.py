from __future__ import annotations

import numpy as np


def power_db(signal: np.ndarray, eps: float = 1e-12) -> float:
    return float(10.0 * np.log10(np.mean(np.asarray(signal, dtype=float) ** 2) + eps))


def tir_db(target_component: np.ndarray, interferer_component: np.ndarray, eps: float = 1e-12) -> float:
    target_power = np.mean(np.asarray(target_component, dtype=float) ** 2)
    interferer_power = np.mean(np.asarray(interferer_component, dtype=float) ** 2)
    return float(10.0 * np.log10((target_power + eps) / (interferer_power + eps)))


def tir_improvement_db(
    target_in: np.ndarray,
    interferer_in: np.ndarray,
    target_out: np.ndarray,
    interferer_out: np.ndarray,
) -> float:
    return tir_db(target_out, interferer_out) - tir_db(target_in, interferer_in)


def si_sdr_db(estimate: np.ndarray, reference: np.ndarray, eps: float = 1e-12) -> float:
    estimate = np.asarray(estimate, dtype=float)
    reference = np.asarray(reference, dtype=float)
    n = min(len(estimate), len(reference))
    estimate = estimate[:n] - np.mean(estimate[:n])
    reference = reference[:n] - np.mean(reference[:n])
    scale = np.dot(estimate, reference) / (np.dot(reference, reference) + eps)
    target = scale * reference
    noise = estimate - target
    return float(10.0 * np.log10((np.sum(target**2) + eps) / (np.sum(noise**2) + eps)))


def stoi_score(estimate: np.ndarray, reference: np.ndarray, sample_rate_hz: int) -> float:
    try:
        from pystoi.stoi import stoi
    except ImportError as exc:
        raise RuntimeError("STOI requires installing the 'metrics' optional dependency") from exc
    n = min(len(estimate), len(reference))
    return float(stoi(reference[:n], estimate[:n], sample_rate_hz, extended=False))


def normalized_rms_error(estimate: np.ndarray, reference: np.ndarray, eps: float = 1e-12) -> float:
    n = min(len(estimate), len(reference))
    err = np.asarray(estimate[:n], dtype=float) - np.asarray(reference[:n], dtype=float)
    return float(np.sqrt(np.mean(err**2)) / (np.sqrt(np.mean(np.asarray(reference[:n]) ** 2)) + eps))
