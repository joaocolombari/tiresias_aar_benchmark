import unittest

import numpy as np

from tiresias_benchmark.experiments.experiment_03 import (
    circular_difference_deg,
    global_sigma_ranking_rows,
    normalized_trapezoid_mean,
    pair_sigma_angular_scores,
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

    def test_normalized_trapezoid_mean_returns_angular_average(self):
        points = [(0.0, 0.0), (10.0, 10.0), (20.0, 20.0)]

        self.assertAlmostEqual(normalized_trapezoid_mean(points), 10.0)

    def test_global_sigma_ranking_is_invariant_to_row_order(self):
        rows = self._ranking_fixture_rows()

        first = global_sigma_ranking_rows(
            pair_sigma_angular_scores(rows),
            bootstrap_iterations=250,
            bootstrap_seed=123,
        )
        second = global_sigma_ranking_rows(
            pair_sigma_angular_scores(list(reversed(rows))),
            bootstrap_iterations=250,
            bootstrap_seed=123,
        )

        self.assertEqual(first, second)

    def test_global_sigma_ranking_bootstrap_is_reproducible(self):
        pair_sigma_rows = pair_sigma_angular_scores(self._ranking_fixture_rows())

        first = global_sigma_ranking_rows(pair_sigma_rows, bootstrap_iterations=250, bootstrap_seed=321)
        second = global_sigma_ranking_rows(pair_sigma_rows, bootstrap_iterations=250, bootstrap_seed=321)

        self.assertEqual(first, second)

    def test_pair_sigma_scores_average_target_auc_equally(self):
        rows = []
        for yaw, value in ((0.0, 0.0), (10.0, 10.0), (20.0, 20.0)):
            rows.append(self._ranking_row("pair_01", 10.0, "source_a", yaw, 0.0, value))
            rows.append(self._ranking_row("pair_01", 10.0, "source_b", yaw, 0.0, 4.0))

        scores = pair_sigma_angular_scores(rows)

        self.assertEqual(len(scores), 1)
        self.assertAlmostEqual(scores[0]["source_a_angular_mean_delta_tir_db"], 10.0)
        self.assertAlmostEqual(scores[0]["source_b_angular_mean_delta_tir_db"], 4.0)
        self.assertAlmostEqual(scores[0]["angular_mean_delta_tir_db"], 7.0)

    def test_pair_sigma_scores_use_target_side_region_to_avoid_symmetric_cancellation(self):
        rows = [
            self._ranking_row("pair_01", 20.0, "source_a", -30.0, -30.0, 10.0),
            self._ranking_row("pair_01", 20.0, "source_a", 0.0, -30.0, 0.0),
            self._ranking_row("pair_01", 20.0, "source_a", 30.0, -30.0, -10.0),
            self._ranking_row("pair_01", 20.0, "source_b", -30.0, 30.0, -10.0),
            self._ranking_row("pair_01", 20.0, "source_b", 0.0, 30.0, 0.0),
            self._ranking_row("pair_01", 20.0, "source_b", 30.0, 30.0, 10.0),
        ]

        scores = pair_sigma_angular_scores(rows)

        self.assertEqual(len(scores), 1)
        self.assertAlmostEqual(scores[0]["source_a_angular_mean_delta_tir_db"], 5.0)
        self.assertAlmostEqual(scores[0]["source_b_angular_mean_delta_tir_db"], 5.0)
        self.assertAlmostEqual(scores[0]["angular_mean_delta_tir_db"], 5.0)

    def _ranking_fixture_rows(self) -> list[dict]:
        rows = []
        for pair_index, pair_offset in enumerate((0.0, 0.4, -0.2), start=1):
            pair_id = f"pair_{pair_index:02d}"
            for sigma, base in ((10.0, 5.0), (20.0, 5.3), (30.0, 4.1)):
                for target in ("source_a", "source_b"):
                    target_angle = -30.0 if target == "source_a" else 30.0
                    for relative_yaw, shape_value in ((-20.0, 0.0), (0.0, base), (20.0, 0.0)):
                        head_yaw = target_angle + relative_yaw
                        rows.append(
                            self._ranking_row(
                                pair_id,
                                sigma,
                                target,
                                head_yaw,
                                target_angle,
                                shape_value + pair_offset,
                            )
                        )
        return rows

    def _ranking_row(
        self,
        pair_id: str,
        sigma: float,
        target: str,
        head_yaw: float,
        target_angle: float,
        tir_improvement: float,
    ) -> dict:
        return {
            "pair_id": pair_id,
            "sigma_deg": sigma,
            "target_source": target,
            "head_yaw_deg": head_yaw,
            "target_angle_deg": target_angle,
            "tir_improvement_db": tir_improvement,
        }


if __name__ == "__main__":
    unittest.main()
