import unittest

from tiresias_benchmark.experiments.experiment_01 import build_reference_sequences


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


if __name__ == "__main__":
    unittest.main()
