from __future__ import annotations

from tiresias_benchmark.separation.leakage import leakage_coefficient_from_sdr_db


def run(config: dict) -> list[dict]:
    rows = []
    for sigma in config["sigma_deg"]:
        for orientation_delay_ms in config["orientation_delay_ms"]:
            for source_delay_ms in config["source_estimate_delay_ms"]:
                for sdr in config["separator_sdr_db"]:
                    rows.append(
                        {
                            "sigma_deg": float(sigma),
                            "orientation_delay_ms": float(orientation_delay_ms),
                            "source_estimate_delay_ms": float(source_delay_ms),
                            "separator_sdr_db": sdr,
                            "leakage_linear": leakage_coefficient_from_sdr_db(sdr),
                        }
                    )
    return rows
