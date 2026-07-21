import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from tiresias_benchmark.experiments.experiment_04 import (
    attention_gain_db_series,
    build_representative_trace_rows,
    build_trajectories,
    interpolate_brir_images,
    select_speech_pairs,
)


class Experiment04LatencyTests(unittest.TestCase):
    def test_trajectory_uses_updated_30_degree_geometry(self):
        trajectories = build_trajectories(
            {
                "start_yaw_deg": -30,
                "stop_yaw_deg": 30,
                "hold_before_s": 1.0,
                "hold_after_s": 1.0,
                "control_sample_rate_hz": 100,
                "angular_velocity_deg_s": [60],
            }
        )

        trajectory = trajectories[0]
        self.assertAlmostEqual(float(trajectory.yaw_deg[0]), -30.0)
        self.assertAlmostEqual(float(trajectory.yaw_deg[-1]), 30.0)
        self.assertGreater(trajectory.switch_time_s, trajectory.rotation_start_s)
        self.assertLess(trajectory.switch_time_s, trajectory.rotation_end_s)

    def test_attention_gain_prefers_source_at_current_yaw(self):
        gain_a, gain_b = attention_gain_db_series(
            np.asarray([-30.0, 30.0]),
            source_a_angle_deg=-30.0,
            source_b_angle_deg=30.0,
            sigma_deg=20.0,
            bmax_db=10.0,
        )

        self.assertGreater(gain_a[0], gain_b[0])
        self.assertGreater(gain_b[1], gain_a[1])

    def test_brir_interpolation_wraps_negative_yaw_to_330(self):
        convolved = {
            320: np.full((2, 2), 320.0, dtype=np.float32),
            330: np.full((2, 2), 330.0, dtype=np.float32),
            340: np.full((2, 2), 340.0, dtype=np.float32),
        }
        # Add missing regular grid angles used by the interpolation helper.
        for angle in range(0, 360, 10):
            convolved.setdefault(angle, np.full((2, 2), float(angle), dtype=np.float32))

        out = interpolate_brir_images(convolved, np.asarray([-30.0, -25.0]))

        self.assertTrue(np.allclose(out[0], 330.0))
        self.assertTrue(np.allclose(out[1], 335.0))

    def test_speech_pair_selection_avoids_same_speaker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio").mkdir()
            manifest = root / "manifest.csv"
            rows = [
                ("A1", "spk1"),
                ("A2", "spk1"),
                ("B1", "spk2"),
                ("C1", "spk3"),
            ]
            with manifest.open("w", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "sample_id",
                        "archive_path",
                        "speaker_id",
                        "original_relative_path",
                    ],
                )
                writer.writeheader()
                for sample_id, speaker_id in rows:
                    writer.writerow(
                        {
                            "sample_id": sample_id,
                            "archive_path": f"audio/{sample_id}.flac",
                            "speaker_id": speaker_id,
                            "original_relative_path": f"{speaker_id}/{sample_id}.flac",
                        }
                    )

            pairs = select_speech_pairs(
                {
                    "speech_dataset": {
                        "root": str(root),
                        "manifest": "manifest.csv",
                        "pair_count": 1,
                        "pair_seed": 1,
                    }
                }
            )

        self.assertEqual(len(pairs), 1)
        self.assertNotEqual(pairs[0].source_a.speaker_id, pairs[0].source_b.speaker_id)

    def test_representative_trace_rows_are_rebuilt_from_control_config(self):
        rows = build_representative_trace_rows(
            {
                "sources": [
                    {"name": "source_a", "azimuth_deg": -30},
                    {"name": "source_b", "azimuth_deg": 30},
                ],
                "angular_velocity_deg_s": [60, 120],
                "trace_velocity_deg_s": 120,
                "trace_sigma_deg": 20,
                "trace_delay_ms": [0, 80],
                "control_sample_rate_hz": 20,
                "start_yaw_deg": -30,
                "stop_yaw_deg": 30,
                "hold_before_s": 0.2,
                "hold_after_s": 0.2,
                "bmax_db": 10,
            }
        )

        self.assertTrue(rows)
        self.assertEqual({row["orientation_delay_ms"] for row in rows}, {0.0, 80.0})
        self.assertEqual({row["angular_velocity_deg_s"] for row in rows}, {120.0})


if __name__ == "__main__":
    unittest.main()
