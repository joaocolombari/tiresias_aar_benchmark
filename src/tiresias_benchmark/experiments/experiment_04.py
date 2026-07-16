from __future__ import annotations

import numpy as np

from tiresias_benchmark.attention.gaussian import Source, compute_attention_from_yaw
from tiresias_benchmark.telemetry.replay import delayed_yaw_series


def run(config: dict) -> list[dict]:
    sources = [
        Source(name=item["name"], azimuth_deg=float(item["azimuth_deg"]), distance_m=float(item.get("distance_m", 1.0)))
        for item in config["sources"]
    ]
    fs = float(config.get("control_sample_rate_hz", 100.0))
    duration = float(config.get("duration_s", 4.0))
    t = np.arange(int(duration * fs), dtype=float) / fs
    yaw = np.linspace(float(config["start_yaw_deg"]), float(config["stop_yaw_deg"]), len(t))
    rows = []
    for sigma in config["sigma_deg"]:
        ideal = [
            compute_attention_from_yaw(y, sources, float(sigma), float(config["bmax_db"])) for y in yaw
        ]
        ideal_gain_db = np.array([frame[0].gain_db for frame in ideal], dtype=float)
        for delay_ms in config["orientation_delay_ms"]:
            delayed_yaw = delayed_yaw_series(t, yaw, float(delay_ms))
            delayed = [
                compute_attention_from_yaw(y, sources, float(sigma), float(config["bmax_db"]))
                for y in delayed_yaw
            ]
            gain_db = np.array([frame[0].gain_db for frame in delayed], dtype=float)
            rows.append(
                {
                    "sigma_deg": float(sigma),
                    "orientation_delay_ms": float(delay_ms),
                    "gain_error_rms_db": float(np.sqrt(np.mean((gain_db - ideal_gain_db) ** 2))),
                    "angular_velocity_delay_deg": float(config.get("angular_velocity_deg_s", 0.0))
                    * float(delay_ms)
                    / 1000.0,
                }
            )
    return rows
