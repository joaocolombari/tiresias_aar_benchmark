import tempfile
import unittest
import json
from pathlib import Path

from tiresias_benchmark.cli import load_yaml
import numpy as np

from tiresias_benchmark.experiments.experiment_02 import (
    build_trial_plan,
    deconvolve_stereo_brir,
    predict_recording_from_ir,
    run,
    write_plan_csv,
)
from tiresias_benchmark.experiments.experiment_02_audio import record_probe


CONFIG_PATH = Path("experiments/exp02_brir_measurement/config.yaml")


class Experiment02PlanTests(unittest.TestCase):
    def test_default_plan_totals_and_closure_identity(self):
        config = load_yaml(CONFIG_PATH)
        trials = build_trial_plan(config)

        self.assertEqual(len(trials), 148)
        self.assertEqual(len({trial.trial_id for trial in trials}), 148)
        self.assertEqual(len({trial.angle_sequence_index for trial in trials}), 37)
        self.assertEqual(
            len({trial.angle_wrapped_deg for trial in trials if not trial.closure_measurement}),
            36,
        )
        self.assertEqual(sum(1 for trial in trials if trial.angle_nominal_deg == 0), 4)
        self.assertEqual(sum(1 for trial in trials if trial.angle_nominal_deg == 360), 4)
        self.assertEqual(sum(1 for trial in trials if trial.closure_measurement), 4)
        self.assertTrue(
            all(trial.angle_wrapped_deg == 0 for trial in trials if trial.angle_nominal_deg == 360)
        )
        self.assertIn("brir_theta_000_spk_A_rep01", {trial.trial_id for trial in trials})
        self.assertIn("brir_theta_360_spk_A_rep01", {trial.trial_id for trial in trials})

    def test_default_plan_alternates_speaker_order_by_angle_index(self):
        config = load_yaml(CONFIG_PATH)
        trials = build_trial_plan(config)

        first_angle = [(trial.speaker, trial.repetition) for trial in trials[:4]]
        second_angle = [(trial.speaker, trial.repetition) for trial in trials[4:8]]

        self.assertEqual(first_angle, [("A", 1), ("B", 1), ("A", 2), ("B", 2)])
        self.assertEqual(second_angle, [("B", 1), ("A", 1), ("B", 2), ("A", 2)])

    def test_default_geometry_matches_measured_rig(self):
        config = load_yaml(CONFIG_PATH)
        speakers = config["geometry"]["speaker_reference"]

        self.assertEqual(config["geometry"]["positive_rotation_direction"], "clockwise")
        self.assertEqual(speakers["A"]["azimuth_deg"], -30)
        self.assertEqual(speakers["B"]["azimuth_deg"], 30)
        self.assertEqual(speakers["A"]["distance_m"], 1.0)
        self.assertEqual(speakers["B"]["distance_m"], 1.0)

    def test_run_writes_plan_csv_without_merging_360(self):
        config = load_yaml(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            plan_csv = Path(tmp) / "plan.csv"
            config["outputs"] = {"plan_csv": str(plan_csv), "overwrite_existing": False}
            result = run(config)
            text = plan_csv.read_text()

        self.assertEqual(result["angle_blocks"], 37)
        self.assertEqual(result["unique_spatial_orientations"], 36)
        self.assertEqual(result["planned_trials"], 148)
        self.assertEqual(result["expected_impulse_responses"], 296)
        self.assertIn("brir_theta_000_spk_A_rep01", text)
        self.assertIn("brir_theta_360_spk_A_rep01", text)

    def test_plan_csv_refuses_overwrite_by_default(self):
        config = load_yaml(CONFIG_PATH)
        trials = build_trial_plan(config)
        with tempfile.TemporaryDirectory() as tmp:
            plan_csv = Path(tmp) / "plan.csv"
            write_plan_csv(trials, plan_csv)
            write_plan_csv(trials, plan_csv)
            plan_csv.write_text("different existing plan\n")
            with self.assertRaises(FileExistsError):
                write_plan_csv(trials, plan_csv)

    def test_simulated_probe_writes_next_stage_artifacts(self):
        config = load_yaml(CONFIG_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            result = record_probe(
                config=config,
                speaker="A",
                session_id="sim_test",
                output_root=tmp,
                simulate=True,
            )
            metadata = json.loads(result.metadata_json.read_text())
            qc = json.loads(result.qc_json.read_text())
            self.assertTrue(result.raw_input_wav.exists())
            self.assertTrue(result.playback_output_wav.exists())
            self.assertTrue(result.callback_timeline_csv.exists())
        self.assertEqual(metadata["trial_id"], "brir_theta_000_spk_A_rep01")
        self.assertEqual(metadata["raw_channel_order"], ["ear_L", "ear_R", "electrical_reference"])
        self.assertTrue(qc["passed_basic_qc"])

    def test_stereo_deconvolution_uses_common_window_and_preserves_itd(self):
        fs = 48_000
        reference = np.zeros(256, dtype=np.float32)
        reference[0] = 1.0
        ear_l = np.zeros(512, dtype=np.float32)
        ear_r = np.zeros(512, dtype=np.float32)
        ear_l[120] = 1.0
        ear_r[132] = 0.5

        result = deconvolve_stereo_brir(
            ear_l=ear_l,
            ear_r=ear_r,
            reference=reference,
            sample_rate_hz=fs,
            response_length_samples=128,
            regularization_fraction=1e-12,
            pre_samples=8,
        )

        self.assertEqual(result.window_start_sample, 112)
        self.assertEqual(result.left_peak_sample_windowed, 8)
        self.assertEqual(result.right_peak_sample_windowed, 20)
        self.assertAlmostEqual(result.itd_ms, 1000.0 * 12 / fs)

    def test_predict_recording_from_windowed_ir_restores_window_offset(self):
        reference = np.zeros(16, dtype=np.float32)
        reference[2] = 1.0
        windowed_ir = np.zeros(8, dtype=np.float32)
        windowed_ir[3] = 0.5

        predicted = predict_recording_from_ir(
            reference=reference,
            windowed_ir=windowed_ir,
            window_start_sample=10,
            output_length=32,
        )

        self.assertAlmostEqual(float(predicted[15]), 0.5)
        self.assertEqual(np.count_nonzero(predicted), 1)


if __name__ == "__main__":
    unittest.main()
