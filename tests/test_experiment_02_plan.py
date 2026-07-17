import tempfile
import unittest
import json
from pathlib import Path

from tiresias_benchmark.cli import load_yaml
from tiresias_benchmark.experiments.experiment_02 import build_trial_plan, run, write_plan_csv
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


if __name__ == "__main__":
    unittest.main()
