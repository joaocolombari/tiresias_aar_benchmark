import csv
import tempfile
import unittest
from pathlib import Path

from tiresias_benchmark.experiments.experiment_01 import build_reference_sequences, run


class Experiment01ProtocolTests(unittest.TestCase):
    def test_sequences_include_closure_but_randomized_has_unique_36_before_closure(self):
        config = {
            "angular_protocol": {"start_deg": 0, "stop_deg": 360, "step_deg": 10, "include_closure_endpoint": True},
            "runs": ["ascending", "descending", "randomized"],
            "randomized_run": {"seed": 20260713, "append_closure_measurement_deg": 360},
        }
        sequences = build_reference_sequences(config)
        self.assertEqual(sequences["ascending"][0]["reference_angle_commanded_deg"], 0)
        self.assertEqual(sequences["ascending"][-1]["reference_angle_commanded_deg"], 360)
        self.assertTrue(sequences["ascending"][-1]["is_closure_measurement"])
        self.assertEqual(sequences["descending"][0]["reference_angle_commanded_deg"], 360)
        self.assertEqual(sequences["descending"][-1]["reference_angle_commanded_deg"], 0)
        self.assertTrue(sequences["descending"][-1]["is_closure_measurement"])

        randomized = sequences["randomized"]
        unique_before_closure = [row["reference_angle_commanded_deg"] for row in randomized[:-1]]
        self.assertEqual(len(unique_before_closure), 36)
        self.assertEqual(sorted(unique_before_closure), list(range(0, 360, 10)))
        self.assertEqual(randomized[-1]["reference_angle_commanded_deg"], 360)
        self.assertTrue(randomized[-1]["is_closure_measurement"])

    def test_run_ignores_guided_non_analysis_and_non_angle_segments(self):
        fieldnames = [
            "host_monotonic_timestamp_ns",
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
        rows = [
            {
                "host_monotonic_timestamp_ns": "0",
                "calibrated_yaw_deg": "99",
                "reference_angle_commanded_deg": "0",
                "reference_angle_normalized_deg": "0",
                "run_type": "drift_before",
                "run_id": "drift_before",
                "position_index": "0",
                "is_closure_measurement": "false",
                "segment_kind": "drift_before",
                "include_in_analysis": "true",
            },
            {
                "host_monotonic_timestamp_ns": "1000000000",
                "calibrated_yaw_deg": "25",
                "reference_angle_commanded_deg": "0",
                "reference_angle_normalized_deg": "0",
                "run_type": "ascending",
                "run_id": "ascending",
                "position_index": "0",
                "is_closure_measurement": "false",
                "segment_kind": "angle",
                "include_in_analysis": "false",
            },
            {
                "host_monotonic_timestamp_ns": "2000000000",
                "calibrated_yaw_deg": "1",
                "reference_angle_commanded_deg": "0",
                "reference_angle_normalized_deg": "0",
                "run_type": "ascending",
                "run_id": "ascending",
                "position_index": "0",
                "is_closure_measurement": "false",
                "segment_kind": "angle",
                "include_in_analysis": "true",
            },
            {
                "host_monotonic_timestamp_ns": "3000000000",
                "calibrated_yaw_deg": "359",
                "reference_angle_commanded_deg": "360",
                "reference_angle_normalized_deg": "0",
                "run_type": "ascending",
                "run_id": "ascending",
                "position_index": "36",
                "is_closure_measurement": "true",
                "segment_kind": "angle",
                "include_in_analysis": "true",
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "guided_raw.csv"
            with csv_path.open("w", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            result = run({"telemetry_csv": str(csv_path)})

        self.assertEqual(result["global_samples_used"], 1)
        self.assertEqual(result["closure_samples_excluded"], 1)
        self.assertAlmostEqual(result["mae_deg"], 1.0)
        self.assertAlmostEqual(result["closure_errors_deg"]["ascending"], -2.0)


if __name__ == "__main__":
    unittest.main()
