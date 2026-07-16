from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from tiresias_benchmark.attention.gaussian import AttentionResult
from tiresias_benchmark.telemetry.decoder import OrientationTelemetry


def telemetry_fieldnames(max_sources: int = 2) -> list[str]:
    fields = [
        "session_id",
        "host_monotonic_timestamp_ns",
        "receive_interval_ms",
        "packet_loss_count",
        "device_timestamp_ms",
        "seq",
        "packet_format",
        "packet_version",
        "flags",
        "ax_m_s2",
        "ay_m_s2",
        "az_m_s2",
        "gx_rad_s",
        "gy_rad_s",
        "gz_rad_s",
        "qw",
        "qx",
        "qy",
        "qz",
        "yaw_deg",
        "calibrated_yaw_deg",
        "sigma_deg",
        "bmax_db",
        "audio_frame_index",
        "calibration_state",
    ]
    for i in range(max_sources):
        fields.extend(
            [
                f"source_{i}_name",
                f"source_{i}_gain_linear",
                f"source_{i}_attention_pct",
                f"source_{i}_distance_factor",
                f"source_{i}_gain_db",
                f"source_{i}_relative_angle_deg",
            ]
        )
    return fields


class TelemetryCsvLogger:
    def __init__(self, path: str | Path, session_id: str, max_sources: int = 2):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.session_id = session_id
        self.max_sources = max_sources
        self._file = self.path.open("w", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=telemetry_fieldnames(max_sources))
        self._writer.writeheader()
        self._last_host_time_ns: int | None = None
        self._last_seq: int | None = None

    def write(
        self,
        *,
        host_monotonic_timestamp_ns: int,
        telemetry: OrientationTelemetry,
        calibrated_yaw_deg: float,
        sigma_deg: float,
        bmax_db: float,
        audio_frame_index: int | None,
        attention: Iterable[AttentionResult] = (),
    ) -> None:
        receive_interval_ms = ""
        if self._last_host_time_ns is not None:
            receive_interval_ms = (host_monotonic_timestamp_ns - self._last_host_time_ns) / 1_000_000.0
        self._last_host_time_ns = host_monotonic_timestamp_ns

        packet_loss_count = ""
        if telemetry.seq is not None and self._last_seq is not None:
            packet_loss_count = max(0, telemetry.seq - self._last_seq - 1)
        if telemetry.seq is not None:
            self._last_seq = telemetry.seq

        row = {
            "session_id": self.session_id,
            "host_monotonic_timestamp_ns": host_monotonic_timestamp_ns,
            "receive_interval_ms": receive_interval_ms,
            "packet_loss_count": packet_loss_count,
            "device_timestamp_ms": telemetry.device_time_ms if telemetry.device_time_ms is not None else "",
            "seq": telemetry.seq if telemetry.seq is not None else "",
            "packet_format": telemetry.packet_format,
            "packet_version": telemetry.version if telemetry.version is not None else "",
            "flags": telemetry.flags if telemetry.flags is not None else "",
            "ax_m_s2": telemetry.ax_m_s2 if telemetry.ax_m_s2 is not None else "",
            "ay_m_s2": telemetry.ay_m_s2 if telemetry.ay_m_s2 is not None else "",
            "az_m_s2": telemetry.az_m_s2 if telemetry.az_m_s2 is not None else "",
            "gx_rad_s": telemetry.gx_rad_s if telemetry.gx_rad_s is not None else "",
            "gy_rad_s": telemetry.gy_rad_s if telemetry.gy_rad_s is not None else "",
            "gz_rad_s": telemetry.gz_rad_s if telemetry.gz_rad_s is not None else "",
            "qw": telemetry.qw,
            "qx": telemetry.qx,
            "qy": telemetry.qy,
            "qz": telemetry.qz,
            "yaw_deg": telemetry.yaw_deg if telemetry.yaw_deg is not None else "",
            "calibrated_yaw_deg": calibrated_yaw_deg,
            "sigma_deg": sigma_deg,
            "bmax_db": bmax_db,
            "audio_frame_index": audio_frame_index if audio_frame_index is not None else "",
            "calibration_state": telemetry.calibration_state
            if telemetry.calibration_state is not None
            else "",
        }
        for i, item in enumerate(attention):
            if i >= self.max_sources:
                break
            row[f"source_{i}_name"] = item.source_name
            row[f"source_{i}_gain_linear"] = item.gain_linear
            row[f"source_{i}_attention_pct"] = item.attention_pct
            row[f"source_{i}_distance_factor"] = item.distance_factor
            row[f"source_{i}_gain_db"] = item.gain_db
            row[f"source_{i}_relative_angle_deg"] = item.relative_angle_deg
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "TelemetryCsvLogger":
        return self

    def __exit__(self, *args) -> None:
        self.close()
