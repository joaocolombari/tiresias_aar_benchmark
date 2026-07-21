import unittest

import numpy as np

from tiresias_benchmark.experiments.experiment_05 import (
    compute_requirement_rows,
    separator_component_metrics,
    source_overlay_output_window,
)


class Experiment05SeparatorTests(unittest.TestCase):
    def test_perfect_separator_improves_tir_when_target_gain_is_larger(self):
        samples = 200
        time = np.linspace(0.0, 1.0, samples, endpoint=False)
        target_mono = np.sin(2.0 * np.pi * 5.0 * time)
        interferer_mono = 0.5 * np.sin(2.0 * np.pi * 11.0 * time)
        target = np.column_stack([target_mono, target_mono]).astype(np.float32)
        interferer = np.column_stack([interferer_mono, interferer_mono]).astype(np.float32)
        gain_target = np.full(samples, 2.0)
        gain_interferer = np.full(samples, 0.5)

        metrics = separator_component_metrics(
            physical_a=interferer,
            physical_b=target,
            estimate_a=interferer,
            estimate_b=target,
            gain_a=gain_interferer,
            gain_b=gain_target,
            leakage=0.0,
            sample_rate_hz=100,
            switch_time_s=0.0,
            window_s=1.0,
        )

        self.assertGreater(metrics["tir_improvement_db"], 0.0)
        self.assertGreater(metrics["output_tir_db"], metrics["input_tir_db"])

    def test_cross_source_leakage_reduces_tir_improvement(self):
        samples = 200
        target = np.ones((samples, 2), dtype=np.float32)
        interferer = 0.5 * np.ones((samples, 2), dtype=np.float32)
        gain_target = np.full(samples, 2.0)
        gain_interferer = np.full(samples, 0.5)

        clean = separator_component_metrics(
            physical_a=interferer,
            physical_b=target,
            estimate_a=interferer,
            estimate_b=target,
            gain_a=gain_interferer,
            gain_b=gain_target,
            leakage=0.0,
            sample_rate_hz=100,
            switch_time_s=0.0,
            window_s=1.0,
        )
        leaky = separator_component_metrics(
            physical_a=interferer,
            physical_b=target,
            estimate_a=interferer,
            estimate_b=target,
            gain_a=gain_interferer,
            gain_b=gain_target,
            leakage=1.0,
            sample_rate_hz=100,
            switch_time_s=0.0,
            window_s=1.0,
        )

        self.assertLess(leaky["tir_improvement_db"], clean["tir_improvement_db"])

    def test_source_overlay_matches_gain_render_when_estimate_is_ideal(self):
        samples = 16
        source_a = np.column_stack(
            [np.linspace(0.0, 1.0, samples), np.linspace(1.0, 0.0, samples)]
        ).astype(np.float32)
        source_b = 0.25 * np.ones((samples, 2), dtype=np.float32)
        gain_a = np.full(samples, 1.5)
        gain_b = np.full(samples, 2.0)

        output = source_overlay_output_window(
            physical_a=source_a,
            physical_b=source_b,
            estimate_a=source_a,
            estimate_b=source_b,
            gain_a=gain_a,
            gain_b=gain_b,
            leakage=0.0,
            sample_rate_hz=100,
            switch_time_s=0.0,
            window_s=1.0,
        )

        expected = gain_a[:, None] * source_a + gain_b[:, None] * source_b
        np.testing.assert_allclose(output, expected)

    def test_requirement_rows_choose_lowest_acceptable_separator_sdr(self):
        rows = []
        for sdr, retention, sisdr_loss in [
            (0.0, 0.50, -3.0),
            (5.0, 0.85, -1.2),
            (10.0, 0.92, -0.8),
            (20.0, 0.98, -0.2),
        ]:
            rows.append(
                {
                    "trajectory": "30_deg_s",
                    "angular_velocity_deg_s": 30.0,
                    "sigma_deg": 20.0,
                    "orientation_delay_ms": 0.0,
                    "source_estimate_delay_ms": 80.0,
                    "source_delay_angular_lag_deg": 2.4,
                    "separator_sdr_db": sdr,
                    "separator_sdr_label": f"{sdr:g}",
                    "tir_retention_fraction_mean": retention,
                    "tir_loss_vs_ideal_db_mean": -1.0,
                    "si_sdr_loss_vs_ideal_db_mean": sisdr_loss,
                    "component_si_sdr_loss_vs_ideal_db_mean": sisdr_loss,
                }
            )

        requirements = compute_requirement_rows(
            rows,
            {"requirements": {"tir_retention_fraction": 0.90, "max_si_sdr_loss_db": 1.0}},
        )

        self.assertEqual(len(requirements), 1)
        self.assertEqual(requirements[0]["minimum_separator_sdr_label"], "10")
        self.assertTrue(requirements[0]["acceptable"])

    def test_requirement_rows_preserve_infinite_sdr_label_for_no_leakage_separator(self):
        rows = []
        for label, retention, sisdr_loss in [
            ("0", 0.20, -4.0),
            ("5", 0.45, -3.0),
            ("10", 0.70, -2.0),
            ("20", 0.88, -1.2),
            ("inf", 1.00, 0.0),
        ]:
            rows.append(
                {
                    "trajectory": "30_deg_s",
                    "angular_velocity_deg_s": 30.0,
                    "sigma_deg": 20.0,
                    "orientation_delay_ms": 0.0,
                    "source_estimate_delay_ms": 80.0,
                    "source_delay_angular_lag_deg": 2.4,
                    "separator_sdr_db": label,
                    "separator_sdr_label": label,
                    "tir_retention_fraction_mean": retention,
                    "tir_loss_vs_ideal_db_mean": -1.0,
                    "si_sdr_loss_vs_ideal_db_mean": sisdr_loss,
                    "component_si_sdr_loss_vs_ideal_db_mean": sisdr_loss,
                }
            )

        requirements = compute_requirement_rows(
            rows,
            {
                "requirements": {
                    "tir_retention_fraction": 0.90,
                    "max_si_sdr_loss_db": 1.0,
                }
            },
        )

        self.assertEqual(requirements[0]["minimum_separator_sdr_label"], "inf")
        self.assertTrue(requirements[0]["acceptable"])


if __name__ == "__main__":
    unittest.main()
