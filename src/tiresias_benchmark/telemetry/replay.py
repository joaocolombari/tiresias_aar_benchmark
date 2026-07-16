from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class TelemetryCsvRecord:
    row: dict[str, str]

    def value(self, key: str, default: float | None = None) -> float | None:
        text = self.row.get(key, "")
        if text == "" or text is None:
            return default
        return float(text)

    @property
    def host_time_ns(self) -> int | None:
        for key in ("host_monotonic_timestamp_ns", "host_time_ns"):
            text = self.row.get(key, "")
            if text:
                return int(float(text))
        return None

    @property
    def calibrated_yaw_deg(self) -> float | None:
        return self.value("calibrated_yaw_deg")


def read_telemetry_csv(path: str | Path) -> list[TelemetryCsvRecord]:
    with Path(path).open(newline="") as file:
        return [TelemetryCsvRecord(row) for row in csv.DictReader(file)]


def delayed_yaw_series(
    timestamps_s: np.ndarray,
    yaw_deg: np.ndarray,
    delay_ms: float,
    mode: str = "hold",
) -> np.ndarray:
    if timestamps_s.ndim != 1 or yaw_deg.ndim != 1:
        raise ValueError("timestamps_s and yaw_deg must be 1-D arrays")
    if len(timestamps_s) != len(yaw_deg):
        raise ValueError("timestamps_s and yaw_deg must have the same length")
    query = timestamps_s - delay_ms / 1000.0
    if mode == "hold":
        idx = np.searchsorted(timestamps_s, query + 1e-12, side="right") - 1
        idx = np.clip(idx, 0, len(yaw_deg) - 1)
        return yaw_deg[idx]
    if mode == "linear":
        return np.interp(query, timestamps_s, yaw_deg, left=yaw_deg[0], right=yaw_deg[-1])
    raise ValueError(f"unsupported delay mode {mode}")


def records_to_time_yaw(
    records: list[TelemetryCsvRecord],
    yaw_field: str = "calibrated_yaw_deg",
) -> tuple[np.ndarray, np.ndarray]:
    times = []
    yaws = []
    for record in records:
        t_ns = record.host_time_ns
        yaw = record.value(yaw_field)
        if t_ns is None or yaw is None:
            continue
        times.append(t_ns / 1_000_000_000.0)
        yaws.append(yaw)
    if not times:
        raise ValueError("no usable timestamp/yaw rows found")
    t = np.asarray(times, dtype=float)
    t -= t[0]
    return t, np.asarray(yaws, dtype=float)
