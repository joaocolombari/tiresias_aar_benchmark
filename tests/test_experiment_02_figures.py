import csv
import tempfile
import unittest
from pathlib import Path

from tiresias_benchmark.experiments.experiment_02_figures import (
    generate_experiment_02_validation_report,
)


class Experiment02FigureTests(unittest.TestCase):
    def test_generate_reconvolution_report(self):
        try:
            import matplotlib  # noqa: F401
        except ImportError:
            self.skipTest("matplotlib is not installed in this Python environment")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metrics = root / "metrics"
            figures = root / "figures"
            session = "exp02_test_session"
            validation_csv = metrics / session / "brir_validation_summary.csv"
            validation_csv.parent.mkdir(parents=True)
            self._write_validation_csv(validation_csv, session)

            outputs = generate_experiment_02_validation_report(
                {},
                session_id=session,
                metrics_dir=metrics,
                output_dir=figures,
            )

            self.assertTrue(outputs.results_table_md.exists())
            self.assertTrue(outputs.metrics_json.exists())
            self.assertTrue(outputs.reconvolution_png.exists())
            self.assertTrue(outputs.reconvolution_svg.exists())
            table = outputs.results_table_md.read_text()
            self.assertIn("Cross-repetition", table)
            self.assertIn("| cross repetition | A |", table)

    def _write_validation_csv(self, path: Path, session: str) -> None:
        fieldnames = [
            "validation_id",
            "validation_type",
            "session_id",
            "source_trial_id",
            "target_trial_id",
            "angle_nominal_deg",
            "angle_wrapped_deg",
            "closure_measurement",
            "speaker",
            "source_repetition",
            "target_repetition",
            "sample_rate_hz",
            "frames_compared",
            "source_window_start_sample",
            "ear_l_prediction_sdr_db",
            "ear_r_prediction_sdr_db",
            "mean_prediction_sdr_db",
            "ear_l_corr",
            "ear_r_corr",
            "mean_corr",
            "ear_l_nrmse",
            "ear_r_nrmse",
            "mean_nrmse",
            "ear_l_residual_rms_dbfs",
            "ear_r_residual_rms_dbfs",
            "ear_l_best_fit_gain",
            "ear_r_best_fit_gain",
            "ear_l_gain_corrected_sdr_db",
            "ear_r_gain_corrected_sdr_db",
            "predicted_wav",
            "residual_wav",
        ]
        rows = []
        for angle in (0, 10, 360):
            for speaker in ("A", "B"):
                for validation_type, source_rep, target_rep, sdr in (
                    ("same_trial", 1, 1, 28.0),
                    ("cross_repetition", 1, 2, 23.0),
                ):
                    rows.append(
                        {
                            "validation_id": f"{validation_type}_{angle}_{speaker}",
                            "validation_type": validation_type,
                            "session_id": session,
                            "source_trial_id": f"brir_theta_{angle:03d}_spk_{speaker}_rep01",
                            "target_trial_id": f"brir_theta_{angle:03d}_spk_{speaker}_rep0{target_rep}",
                            "angle_nominal_deg": angle,
                            "angle_wrapped_deg": angle % 360,
                            "closure_measurement": str(angle == 360),
                            "speaker": speaker,
                            "source_repetition": source_rep,
                            "target_repetition": target_rep,
                            "sample_rate_hz": 48000,
                            "frames_compared": 48000,
                            "source_window_start_sample": 200,
                            "ear_l_prediction_sdr_db": sdr,
                            "ear_r_prediction_sdr_db": sdr - 1.0,
                            "mean_prediction_sdr_db": sdr - 0.5,
                            "ear_l_corr": 0.998,
                            "ear_r_corr": 0.997,
                            "mean_corr": 0.9975,
                            "ear_l_nrmse": 0.06,
                            "ear_r_nrmse": 0.07,
                            "mean_nrmse": 0.065,
                            "ear_l_residual_rms_dbfs": -60.0,
                            "ear_r_residual_rms_dbfs": -61.0,
                            "ear_l_best_fit_gain": 1.0,
                            "ear_r_best_fit_gain": 1.0,
                            "ear_l_gain_corrected_sdr_db": sdr + 0.1,
                            "ear_r_gain_corrected_sdr_db": sdr - 0.9,
                            "predicted_wav": "",
                            "residual_wav": "",
                        }
                    )
        with path.open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
