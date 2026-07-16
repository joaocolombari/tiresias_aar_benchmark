from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TelemetryStats:
    update_rate_hz: float
    interval_mean_ms: float
    interval_std_ms: float
    interval_p95_ms: float
    interval_p99_ms: float
    lost_packets: int | None
    packet_loss_percent: float | None


def telemetry_stats(host_timestamps_ns: np.ndarray, seq: np.ndarray | None = None) -> TelemetryStats:
    t = np.asarray(host_timestamps_ns, dtype=float)
    if len(t) < 2:
        raise ValueError("at least two timestamps are required")
    intervals_ms = np.diff(t) / 1_000_000.0
    lost_packets = None
    loss_percent = None
    if seq is not None:
        seq = np.asarray(seq, dtype=float)
        seq = seq[~np.isnan(seq)].astype(int)
        if len(seq) >= 2:
            gaps = np.diff(seq) - 1
            lost_packets = int(np.sum(np.maximum(gaps, 0)))
            expected = int(seq[-1] - seq[0])
            loss_percent = 100.0 * lost_packets / expected if expected > 0 else 0.0
    return TelemetryStats(
        update_rate_hz=float(1000.0 / np.mean(intervals_ms)),
        interval_mean_ms=float(np.mean(intervals_ms)),
        interval_std_ms=float(np.std(intervals_ms)),
        interval_p95_ms=float(np.percentile(intervals_ms, 95)),
        interval_p99_ms=float(np.percentile(intervals_ms, 99)),
        lost_packets=lost_packets,
        packet_loss_percent=loss_percent,
    )
