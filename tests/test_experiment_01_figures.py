import csv
import tempfile
import unittest
from pathlib import Path

from tiresias_benchmark.experiments.experiment_01_figures import (
    generate_experiment_01_figures,
)


class Experiment01FigureTests(unittest.TestCase):
    def test_generate_figures_combines_three_runs(self):
        config = {"runs": ["ascending", "descending", "randomized"]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            raw = root / "raw"
            figures = root / "figures"
            metrics = root / "metrics"
            processed.mkdir()
            raw.mkdir()

            self._write_segmented(
                processed / "segmented_ascending_20260717_120000.csv",
                "ascending",
                [(0, 0, False), (1, 10, False), (2, 360, True)],
            )
            self._write_segmented(
                processed / "segmented_descending_20260717_121000.csv",
                "descending",
                [(0, 360, False), (1, 350, False), (2, 0, True)],
            )
            self._write_segmented(
                processed / "segmented_randomized_20260717_122000.csv",
                "randomized",
                [(0, 0, False), (1, 20, False), (2, 360, True)],
            )
            for name in (
                "exp01_guided_ascending_20260717_120000.csv",
                "exp01_guided_descending_20260717_121000.csv",
                "exp01_guided_randomized_20260717_122000.csv",
            ):
                self._write_raw(raw / name)

            outputs = generate_experiment_01_figures(
                config,
                processed_dir=processed,
                raw_dir=raw,
                output_dir=figures,
                metrics_dir=metrics,
            )

            for path in outputs.__dict__.values():
                self.assertTrue(path.exists(), path)

            table = outputs.results_table_md.read_text()
            self.assertIn("| ascending |", table)
            self.assertIn("| descending |", table)
            self.assertIn("| randomized |", table)

    def _write_segmented(self, path: Path, run_type: str, positions: list[tuple[int, int, bool]]) -> None:
        fieldnames = [
            "host_monotonic_timestamp_ns",
            "receive_interval_ms",
            "seq",
            "calibrated_yaw_deg",
            "reference_angle_commanded_deg",
            "reference_angle_normalized_deg",
            "run_type",
            "run_id",
            "position_index",
            "is_closure_measurement",
            "segment_kind",
            "include_in_analysis",
        ]
        rows = []
        seq = 0
        for position_index, commanded, closure in positions:
            normalized = commanded % 360
            for sample_index in range(3):
                rows.append(
                    {
                        "host_monotonic_timestamp_ns": str((position_index * 10 + sample_index) * 1_000_000_000),
                        "receive_interval_ms": "25",
                        "seq": str(seq),
                        "calibrated_yaw_deg": str(-(normalized + 0.2 * position_index)),
                        "reference_angle_commanded_deg": str(commanded),
                        "reference_angle_normalized_deg": str(normalized),
                        "run_type": run_type,
                        "run_id": run_type,
                        "position_index": str(position_index),
                        "is_closure_measurement": str(closure).lower(),
                        "segment_kind": "angle",
                        "include_in_analysis": "true",
                    }
                )
                seq += 2
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _write_raw(self, path: Path) -> None:
        fieldnames = ["receive_interval_ms", "seq", "run_type"]
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for index in range(20):
                writer.writerow(
                    {
                        "receive_interval_ms": "" if index == 0 else "25",
                        "seq": str(index * 2),
                        "run_type": "",
                    }
                )


if __name__ == "__main__":
    unittest.main()
