from __future__ import annotations

import numpy as np

from tiresias_benchmark.attention.gaussian import Source, compute_attention_from_yaw


def run(config: dict) -> list[dict]:
    sources = [
        Source(name=item["name"], azimuth_deg=float(item["azimuth_deg"]), distance_m=float(item.get("distance_m", 1.0)))
        for item in config["sources"]
    ]
    rows = []
    for sigma in config["sigma_deg"]:
        for head_yaw in config["head_yaw_deg"]:
            attention = compute_attention_from_yaw(
                float(head_yaw),
                sources,
                sigma_deg=float(sigma),
                bmax_db=float(config["bmax_db"]),
                reference_distance_m=float(config.get("reference_distance_m", 1.0)),
            )
            row = {"sigma_deg": float(sigma), "head_yaw_deg": float(head_yaw)}
            for item in attention:
                row[f"{item.source_name}_gain_linear"] = item.gain_linear
                row[f"{item.source_name}_gain_db"] = item.gain_db
                row[f"{item.source_name}_relative_angle_deg"] = item.relative_angle_deg
            rows.append(row)
    return rows


def gain_ratio_db(gain_target: float, gain_interferer: float) -> float:
    return float(20.0 * np.log10((gain_target + 1e-12) / (gain_interferer + 1e-12)))
