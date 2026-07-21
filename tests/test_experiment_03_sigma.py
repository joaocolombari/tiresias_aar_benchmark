import unittest

import numpy as np

from tiresias_benchmark.experiments.experiment_03 import (
    circular_difference_deg,
    static_target_metrics,
    summarize_sigma_rows,
)


class Experiment03SigmaTests(unittest.TestCase):
    def test_circular_difference_supports_negative_source_angle(self):
        self.assertAlmostEqual(float(circular_difference_deg(-30.0, 330.0)), 0.0)
        self.assertAlmostEqual(float(circular_difference_deg(30.0, -30.0)), 60.0)

    def test_static_target_metrics_reward_larger_target_gain(self):
        samples = 128
        target = np.ones((samples, 2), dtype=np.float32)
        interferer = 0.5 * np.ones((samples, 2), dtype=np.float32)
        metrics = static_target_metrics(
            interferer,
            target,
            np.full(samples, 0.5),
            np.full(samples, 2.0),
            target="source_b",
        )

        self.assertGreater(metrics["tir_improvement_db"], 0.0)
        self.assertGreater(metrics["output_tir_db"], metrics["input_tir_db"])

    def test_summary_keeps_independent_target_definitions(self):
        rows = []
        for target in ("source_a", "source_b"):
            rows.append(
                {
                    "target_source": target,
                    "head_yaw_deg": 0.0,
                    "target_angle_deg": -30.0 if target == "source_a" else 30.0,
                    "target_error_deg": 30.0,
                    "sigma_deg": 20.0,
                    "source_a_gain_db": 3.0,
                    "source_b_gain_db": 3.0,
                    "target_gain_db": 3.0,
                    "interferer_gain_db": 3.0,
                    "target_to_interferer_gain_db": 0.0,
                    "tir_improvement_db": 0.0,
                    "input_tir_db": 0.0,
                    "output_tir_db": 0.0,
                    "input_si_sdr_db": 0.0,
                    "output_si_sdr_db": 0.0,
                    "si_sdr_improvement_db": 0.0,
                }
            )

        summary = summarize_sigma_rows(rows)

        self.assertEqual({row["target_source"] for row in summary}, {"source_a", "source_b"})
        self.assertEqual(len(summary), 2)


if __name__ == "__main__":
    unittest.main()
