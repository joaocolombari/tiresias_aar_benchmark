from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
import json
from pathlib import Path

import numpy as np

from tiresias_benchmark.acoustics.deconvolution import (
    regularized_deconvolution,
    trim_response_around_peak,
)


@dataclass(frozen=True)
class BrirTrial:
    trial_id: str
    condition_id: str
    angle_sequence_index: int
    angle_nominal_deg: int
    angle_wrapped_deg: int
    closure_measurement: bool
    speaker: str
    repetition: int
    expected_output_channel: str
    expected_reference_output_channel: str
    expected_input_channels: str
    status: str = "planned"
    attempt_number: int = 1
    notes: str = ""

    def as_csv_row(self) -> dict[str, str | int | bool]:
        return {
            "trial_id": self.trial_id,
            "condition_id": self.condition_id,
            "angle_sequence_index": self.angle_sequence_index,
            "angle_nominal_deg": self.angle_nominal_deg,
            "angle_wrapped_deg": self.angle_wrapped_deg,
            "closure_measurement": self.closure_measurement,
            "speaker": self.speaker,
            "repetition": self.repetition,
            "expected_output_channel": self.expected_output_channel,
            "expected_reference_output_channel": self.expected_reference_output_channel,
            "expected_input_channels": self.expected_input_channels,
            "status": self.status,
            "attempt_number": self.attempt_number,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class ProcessedBrir:
    trial_id: str
    session_id: str
    angle_sequence_index: int
    angle_nominal_deg: int
    angle_wrapped_deg: int
    closure_measurement: bool
    speaker: str
    speaker_azimuth_deg: float
    speaker_distance_m: float | None
    repetition: int
    attempt: int
    sample_rate_hz: int
    frames_in: int
    ir_samples: int
    window_start_sample: int
    left_peak_sample_full: int
    right_peak_sample_full: int
    left_peak_sample_windowed: int
    right_peak_sample_windowed: int
    itd_ms: float
    ild_db: float
    reference_rms_dbfs: float
    loopback_lag_samples: int | None
    loopback_lag_ms: float | None
    loopback_correlation: float | None
    ear_l_rms_dbfs: float
    ear_r_rms_dbfs: float
    qc_passed_basic: bool | None
    qc_fail_reasons: str
    ear_l_wav: str
    ear_r_wav: str
    stereo_wav: str
    metadata_json: str

    def as_csv_row(self) -> dict[str, str | int | float | bool | None]:
        return {
            "trial_id": self.trial_id,
            "session_id": self.session_id,
            "angle_sequence_index": self.angle_sequence_index,
            "angle_nominal_deg": self.angle_nominal_deg,
            "angle_wrapped_deg": self.angle_wrapped_deg,
            "closure_measurement": self.closure_measurement,
            "speaker": self.speaker,
            "speaker_azimuth_deg": self.speaker_azimuth_deg,
            "speaker_distance_m": self.speaker_distance_m,
            "repetition": self.repetition,
            "attempt": self.attempt,
            "sample_rate_hz": self.sample_rate_hz,
            "frames_in": self.frames_in,
            "ir_samples": self.ir_samples,
            "window_start_sample": self.window_start_sample,
            "left_peak_sample_full": self.left_peak_sample_full,
            "right_peak_sample_full": self.right_peak_sample_full,
            "left_peak_sample_windowed": self.left_peak_sample_windowed,
            "right_peak_sample_windowed": self.right_peak_sample_windowed,
            "itd_ms": self.itd_ms,
            "ild_db": self.ild_db,
            "reference_rms_dbfs": self.reference_rms_dbfs,
            "loopback_lag_samples": self.loopback_lag_samples,
            "loopback_lag_ms": self.loopback_lag_ms,
            "loopback_correlation": self.loopback_correlation,
            "ear_l_rms_dbfs": self.ear_l_rms_dbfs,
            "ear_r_rms_dbfs": self.ear_r_rms_dbfs,
            "qc_passed_basic": self.qc_passed_basic,
            "qc_fail_reasons": self.qc_fail_reasons,
            "ear_l_wav": self.ear_l_wav,
            "ear_r_wav": self.ear_r_wav,
            "stereo_wav": self.stereo_wav,
            "metadata_json": self.metadata_json,
        }


@dataclass(frozen=True)
class StereoDeconvolutionResult:
    left_ir: np.ndarray
    right_ir: np.ndarray
    window_start_sample: int
    left_peak_sample_full: int
    right_peak_sample_full: int
    left_peak_sample_windowed: int
    right_peak_sample_windowed: int
    itd_ms: float
    ild_db: float
    regularization: float


@dataclass(frozen=True)
class BrirValidationResult:
    validation_id: str
    validation_type: str
    session_id: str
    source_trial_id: str
    target_trial_id: str
    angle_nominal_deg: int
    angle_wrapped_deg: int
    closure_measurement: bool
    speaker: str
    source_repetition: int
    target_repetition: int
    sample_rate_hz: int
    frames_compared: int
    source_window_start_sample: int
    ear_l_prediction_sdr_db: float
    ear_r_prediction_sdr_db: float
    mean_prediction_sdr_db: float
    ear_l_corr: float
    ear_r_corr: float
    mean_corr: float
    ear_l_nrmse: float
    ear_r_nrmse: float
    mean_nrmse: float
    ear_l_residual_rms_dbfs: float
    ear_r_residual_rms_dbfs: float
    ear_l_best_fit_gain: float
    ear_r_best_fit_gain: float
    ear_l_gain_corrected_sdr_db: float
    ear_r_gain_corrected_sdr_db: float
    predicted_wav: str
    residual_wav: str

    def as_csv_row(self) -> dict[str, str | int | float | bool]:
        return {
            "validation_id": self.validation_id,
            "validation_type": self.validation_type,
            "session_id": self.session_id,
            "source_trial_id": self.source_trial_id,
            "target_trial_id": self.target_trial_id,
            "angle_nominal_deg": self.angle_nominal_deg,
            "angle_wrapped_deg": self.angle_wrapped_deg,
            "closure_measurement": self.closure_measurement,
            "speaker": self.speaker,
            "source_repetition": self.source_repetition,
            "target_repetition": self.target_repetition,
            "sample_rate_hz": self.sample_rate_hz,
            "frames_compared": self.frames_compared,
            "source_window_start_sample": self.source_window_start_sample,
            "ear_l_prediction_sdr_db": self.ear_l_prediction_sdr_db,
            "ear_r_prediction_sdr_db": self.ear_r_prediction_sdr_db,
            "mean_prediction_sdr_db": self.mean_prediction_sdr_db,
            "ear_l_corr": self.ear_l_corr,
            "ear_r_corr": self.ear_r_corr,
            "mean_corr": self.mean_corr,
            "ear_l_nrmse": self.ear_l_nrmse,
            "ear_r_nrmse": self.ear_r_nrmse,
            "mean_nrmse": self.mean_nrmse,
            "ear_l_residual_rms_dbfs": self.ear_l_residual_rms_dbfs,
            "ear_r_residual_rms_dbfs": self.ear_r_residual_rms_dbfs,
            "ear_l_best_fit_gain": self.ear_l_best_fit_gain,
            "ear_r_best_fit_gain": self.ear_r_best_fit_gain,
            "ear_l_gain_corrected_sdr_db": self.ear_l_gain_corrected_sdr_db,
            "ear_r_gain_corrected_sdr_db": self.ear_r_gain_corrected_sdr_db,
            "predicted_wav": self.predicted_wav,
            "residual_wav": self.residual_wav,
        }


PLAN_CSV_FIELDS = [
    "trial_id",
    "condition_id",
    "angle_sequence_index",
    "angle_nominal_deg",
    "angle_wrapped_deg",
    "closure_measurement",
    "speaker",
    "repetition",
    "expected_output_channel",
    "expected_reference_output_channel",
    "expected_input_channels",
    "status",
    "attempt_number",
    "notes",
]


PROCESS_SUMMARY_FIELDS = [
    "trial_id",
    "session_id",
    "angle_sequence_index",
    "angle_nominal_deg",
    "angle_wrapped_deg",
    "closure_measurement",
    "speaker",
    "speaker_azimuth_deg",
    "speaker_distance_m",
    "repetition",
    "attempt",
    "sample_rate_hz",
    "frames_in",
    "ir_samples",
    "window_start_sample",
    "left_peak_sample_full",
    "right_peak_sample_full",
    "left_peak_sample_windowed",
    "right_peak_sample_windowed",
    "itd_ms",
    "ild_db",
    "reference_rms_dbfs",
    "loopback_lag_samples",
    "loopback_lag_ms",
    "loopback_correlation",
    "ear_l_rms_dbfs",
    "ear_r_rms_dbfs",
    "qc_passed_basic",
    "qc_fail_reasons",
    "ear_l_wav",
    "ear_r_wav",
    "stereo_wav",
    "metadata_json",
]


VALIDATION_SUMMARY_FIELDS = [
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


def build_trial_plan(config: dict) -> list[BrirTrial]:
    planning = config.get("planning", {})
    angles = [int(angle) for angle in planning.get("angles_deg", [])]
    if not angles:
        raise ValueError("Experiment 2 config must define planning.angles_deg")
    if angles[0] != 0 or angles[-1] != 360:
        raise ValueError("Experiment 2 plan must preserve nominal 0 and nominal 360 endpoints")
    if len(angles) != 37 or angles[:-1] != list(range(0, 360, 10)):
        raise ValueError("Experiment 2 plan must contain 0, 10, ..., 350, 360")

    closure_angle = int(planning.get("closure_measurement_deg", 360))
    repetitions_per_speaker = int(planning.get("repetitions_per_speaker", 2))
    if repetitions_per_speaker != 2:
        raise ValueError("Experiment 2 currently expects two independent repetitions per speaker")

    audio = config.get("audio_device", {})
    channels = audio.get("channel_selection", {})
    speaker_outputs = {
        "A": _format_output_channel(channels.get("speaker_A_output_index", 0)),
        "B": _format_output_channel(channels.get("speaker_B_output_index", 1)),
    }
    reference_output = _format_output_channel(channels.get("reference_output_index", 2))
    input_channels = _format_input_channels(channels)

    even_order = planning.get(
        "even_angle_index_order",
        [
            {"speaker": "A", "repetition": 1},
            {"speaker": "B", "repetition": 1},
            {"speaker": "A", "repetition": 2},
            {"speaker": "B", "repetition": 2},
        ],
    )
    odd_order = planning.get(
        "odd_angle_index_order",
        [
            {"speaker": "B", "repetition": 1},
            {"speaker": "A", "repetition": 1},
            {"speaker": "B", "repetition": 2},
            {"speaker": "A", "repetition": 2},
        ],
    )

    trials: list[BrirTrial] = []
    for angle_index, angle in enumerate(angles):
        order = even_order if angle_index % 2 == 0 else odd_order
        for item in order:
            speaker = str(item["speaker"])
            repetition = int(item["repetition"])
            if speaker not in speaker_outputs:
                raise ValueError(f"unknown speaker in Experiment 2 plan: {speaker}")
            if repetition not in {1, 2}:
                raise ValueError(f"invalid repetition in Experiment 2 plan: {repetition}")
            trial_id = f"brir_theta_{angle:03d}_spk_{speaker}_rep{repetition:02d}"
            trials.append(
                BrirTrial(
                    trial_id=trial_id,
                    condition_id=trial_id,
                    angle_sequence_index=angle_index,
                    angle_nominal_deg=angle,
                    angle_wrapped_deg=angle % 360,
                    closure_measurement=angle == closure_angle,
                    speaker=speaker,
                    repetition=repetition,
                    expected_output_channel=speaker_outputs[speaker],
                    expected_reference_output_channel=reference_output,
                    expected_input_channels=input_channels,
                )
            )

    if len(trials) != 148:
        raise ValueError(f"Experiment 2 plan must contain 148 trials, got {len(trials)}")
    if len({trial.trial_id for trial in trials}) != 148:
        raise ValueError("Experiment 2 trial IDs are not unique")
    return trials


def write_plan_csv(
    trials: list[BrirTrial],
    output_csv: str | Path,
    overwrite: bool = False,
) -> Path:
    output_path = Path(output_csv)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=PLAN_CSV_FIELDS)
    writer.writeheader()
    for trial in trials:
        writer.writerow(trial.as_csv_row())
    csv_text = buffer.getvalue()

    if output_path.exists() and not overwrite:
        with output_path.open("r", newline="") as file:
            existing_text = file.read()
        if existing_text == csv_text:
            return output_path
        raise FileExistsError(f"refusing to overwrite existing plan CSV: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as file:
        file.write(csv_text)
    return output_path


def process_brir_session(
    config: dict,
    session_id: str,
    overwrite: bool = False,
) -> dict:
    import soundfile as sf

    trials = build_trial_plan(config)
    outputs = config.get("outputs", {})
    raw_root = Path(outputs.get("sessions_root", "experiments/exp02_brir_measurement/raw"))
    processed_root = Path(
        outputs.get("processed_root", "experiments/exp02_brir_measurement/processed")
    )
    metrics_root = Path(outputs.get("metrics_root", "experiments/exp02_brir_measurement/metrics"))
    session_raw = raw_root / session_id / "sweeps"
    if not session_raw.exists():
        raise FileNotFoundError(f"session sweeps directory not found: {session_raw}")

    session_processed = processed_root / session_id
    ir_root = session_processed / "irs"
    metadata_root = session_processed / "metadata"
    summary_csv = metrics_root / session_id / "brir_processing_summary.csv"
    summary_json = metrics_root / session_id / "brir_processing_summary.json"

    planned_outputs = [summary_csv, summary_json]
    for trial in trials:
        planned_outputs.extend(
            [
                ir_root / f"{trial.trial_id}_ear_L.wav",
                ir_root / f"{trial.trial_id}_ear_R.wav",
                ir_root / f"{trial.trial_id}_stereo.wav",
                metadata_root / f"{trial.trial_id}.json",
            ]
        )
    _ensure_can_write(planned_outputs, overwrite=overwrite)

    ir_root.mkdir(parents=True, exist_ok=True)
    metadata_root.mkdir(parents=True, exist_ok=True)
    summary_csv.parent.mkdir(parents=True, exist_ok=True)

    processed: list[ProcessedBrir] = []
    missing: list[str] = []
    for trial in trials:
        try:
            processed.append(
                _process_brir_trial(
                    config=config,
                    trial=trial,
                    session_id=session_id,
                    session_raw=session_raw,
                    ir_root=ir_root,
                    metadata_root=metadata_root,
                    sf=sf,
                )
            )
        except FileNotFoundError as exc:
            missing.append(str(exc))

    _write_processing_summary_csv(summary_csv, processed)
    summary = {
        "experiment_id": config.get("experiment_id", "exp02_brir_measurement"),
        "session_id": session_id,
        "processed_trials": len(processed),
        "processed_impulse_responses": len(processed) * 2,
        "expected_trials": len(trials),
        "expected_impulse_responses": len(trials) * 2,
        "missing_trials": missing,
        "summary_csv": str(summary_csv),
        "processed_root": str(session_processed),
        "geometry": config.get("geometry", {}),
    }
    summary_json.write_text(json.dumps(summary, indent=2))
    return summary


def validate_brir_session(
    config: dict,
    session_id: str,
    mode: str = "both",
    write_wavs: bool = False,
    overwrite: bool = False,
) -> dict:
    import soundfile as sf

    if mode not in {"same", "cross", "both"}:
        raise ValueError("validation mode must be 'same', 'cross' or 'both'")

    trials = build_trial_plan(config)
    outputs = config.get("outputs", {})
    raw_root = Path(outputs.get("sessions_root", "experiments/exp02_brir_measurement/raw"))
    processed_root = Path(
        outputs.get("processed_root", "experiments/exp02_brir_measurement/processed")
    )
    metrics_root = Path(outputs.get("metrics_root", "experiments/exp02_brir_measurement/metrics"))
    session_raw = raw_root / session_id / "sweeps"
    session_processed = processed_root / session_id
    ir_root = session_processed / "irs"
    metadata_root = session_processed / "metadata"
    if not session_raw.exists():
        raise FileNotFoundError(f"session sweeps directory not found: {session_raw}")
    if not ir_root.exists() or not metadata_root.exists():
        raise FileNotFoundError(
            f"processed BRIRs not found for {session_id}; run brir-process first"
        )

    validations = _validation_pairs(trials, mode)
    summary_dir = metrics_root / session_id
    summary_csv = summary_dir / "brir_validation_summary.csv"
    summary_json = summary_dir / "brir_validation_summary.json"
    validation_audio_root = session_processed / "validation"
    planned_outputs = [summary_csv, summary_json]
    if write_wavs:
        for validation_type, source, target in validations:
            validation_id = _validation_id(validation_type, source.trial_id, target.trial_id)
            planned_outputs.extend(
                [
                    validation_audio_root / f"{validation_id}_predicted.wav",
                    validation_audio_root / f"{validation_id}_residual.wav",
                ]
            )
    _ensure_can_write(planned_outputs, overwrite=overwrite)
    summary_dir.mkdir(parents=True, exist_ok=True)
    if write_wavs:
        validation_audio_root.mkdir(parents=True, exist_ok=True)

    rows: list[BrirValidationResult] = []
    for validation_type, source, target in validations:
        rows.append(
            _validate_brir_pair(
                source=source,
                target=target,
                validation_type=validation_type,
                session_id=session_id,
                session_raw=session_raw,
                ir_root=ir_root,
                metadata_root=metadata_root,
                validation_audio_root=validation_audio_root,
                write_wavs=write_wavs,
                sf=sf,
            )
        )

    _write_validation_summary_csv(summary_csv, rows)
    same_rows = [row for row in rows if row.validation_type == "same_trial"]
    cross_rows = [row for row in rows if row.validation_type == "cross_repetition"]
    summary = {
        "experiment_id": config.get("experiment_id", "exp02_brir_measurement"),
        "session_id": session_id,
        "mode": mode,
        "validation_rows": len(rows),
        "same_trial_rows": len(same_rows),
        "cross_repetition_rows": len(cross_rows),
        "summary_csv": str(summary_csv),
        "validation_audio_root": str(validation_audio_root) if write_wavs else None,
        "same_trial_mean_prediction_sdr_db": _mean_or_none(
            [row.mean_prediction_sdr_db for row in same_rows]
        ),
        "cross_repetition_mean_prediction_sdr_db": _mean_or_none(
            [row.mean_prediction_sdr_db for row in cross_rows]
        ),
        "same_trial_mean_corr": _mean_or_none([row.mean_corr for row in same_rows]),
        "cross_repetition_mean_corr": _mean_or_none([row.mean_corr for row in cross_rows]),
        "same_trial_mean_nrmse": _mean_or_none([row.mean_nrmse for row in same_rows]),
        "cross_repetition_mean_nrmse": _mean_or_none([row.mean_nrmse for row in cross_rows]),
    }
    summary_json.write_text(json.dumps(summary, indent=2))
    return summary


def run(config: dict) -> dict:
    if config.get("validate_session_id"):
        return validate_brir_session(
            config,
            session_id=str(config["validate_session_id"]),
            mode=str(config.get("validation_mode", "both")),
            write_wavs=bool(config.get("write_validation_wavs", False)),
            overwrite=bool(config.get("overwrite_validation", False)),
        )

    if config.get("process_session_id"):
        return process_brir_session(
            config,
            session_id=str(config["process_session_id"]),
            overwrite=bool(config.get("overwrite_processing", False)),
        )

    if "planning" in config:
        trials = build_trial_plan(config)
        outputs = config.get("outputs", {})
        plan_csv = outputs.get("plan_csv")
        if plan_csv:
            write_plan_csv(
                trials,
                plan_csv,
                overwrite=bool(outputs.get("overwrite_existing", False)),
            )
        return {
            "experiment_id": config.get("experiment_id", "exp02_brir_measurement"),
            "angle_blocks": len({trial.angle_sequence_index for trial in trials}),
            "unique_spatial_orientations": len(
                {trial.angle_wrapped_deg for trial in trials if not trial.closure_measurement}
            ),
            "planned_trials": len(trials),
            "expected_impulse_responses": len(trials) * 2,
            "closure_trials": sum(1 for trial in trials if trial.closure_measurement),
            "first_trial_id": trials[0].trial_id,
            "last_trial_id": trials[-1].trial_id,
            "plan_csv": str(plan_csv) if plan_csv else None,
        }

    recorded_wav = Path(config["recorded_wav"])
    reference_wav = Path(config["reference_wav"])
    output_wav = Path(config["output_ir_wav"])
    response_length_samples = int(config.get("response_length_samples", 14_400))
    import soundfile as sf

    recorded, fs_r = sf.read(recorded_wav, dtype="float32")
    reference, fs_x = sf.read(reference_wav, dtype="float32")
    if fs_r != fs_x:
        raise ValueError("recorded and reference WAV sample rates differ")
    if recorded.ndim > 1:
        recorded = recorded[:, int(config.get("recorded_channel", 0))]
    if reference.ndim > 1:
        reference = reference[:, int(config.get("reference_channel", 0))]
    response = regularized_deconvolution(recorded, reference)
    response = trim_response_around_peak(response, length_samples=response_length_samples)
    output_wav.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_wav, response, fs_r)
    return {"output_ir_wav": str(output_wav), "sample_rate_hz": fs_r, "samples": len(response)}


def deconvolve_stereo_brir(
    ear_l: np.ndarray,
    ear_r: np.ndarray,
    reference: np.ndarray,
    sample_rate_hz: int,
    response_length_samples: int,
    regularization_fraction: float,
    pre_samples: int = 32,
) -> StereoDeconvolutionResult:
    regularization = _regularization_from_reference(
        reference,
        recorded_length=max(len(ear_l), len(ear_r)),
        fraction=regularization_fraction,
    )
    left_full = regularized_deconvolution(ear_l, reference, regularization=regularization)
    right_full = regularized_deconvolution(ear_r, reference, regularization=regularization)
    left_peak = int(np.argmax(np.abs(left_full)))
    right_peak = int(np.argmax(np.abs(right_full)))
    window_start = max(0, min(left_peak, right_peak) - pre_samples)
    left_ir = _window_response(left_full, window_start, response_length_samples)
    right_ir = _window_response(right_full, window_start, response_length_samples)
    left_peak_windowed = left_peak - window_start
    right_peak_windowed = right_peak - window_start
    itd_ms = 1000.0 * (right_peak - left_peak) / float(sample_rate_hz)
    ild_db = _rms_dbfs(left_ir) - _rms_dbfs(right_ir)
    return StereoDeconvolutionResult(
        left_ir=left_ir,
        right_ir=right_ir,
        window_start_sample=window_start,
        left_peak_sample_full=left_peak,
        right_peak_sample_full=right_peak,
        left_peak_sample_windowed=left_peak_windowed,
        right_peak_sample_windowed=right_peak_windowed,
        itd_ms=float(itd_ms),
        ild_db=float(ild_db),
        regularization=float(regularization),
    )


def _format_output_channel(array_index: object) -> str:
    return f"output_{int(array_index) + 1}"


def _format_input_channels(channels: dict) -> str:
    mic_l = int(channels.get("mic_left_index", 0)) + 1
    mic_r = int(channels.get("mic_right_index", 1)) + 1
    ref = int(channels.get("reference_input_index", 4)) + 1
    return f"input_{mic_l}:ear_L;input_{mic_r}:ear_R;input_{ref}:reference"


def _process_brir_trial(
    config: dict,
    trial: BrirTrial,
    session_id: str,
    session_raw: Path,
    ir_root: Path,
    metadata_root: Path,
    sf,
) -> ProcessedBrir:
    attempt_dir = _select_attempt_dir(session_raw / trial.trial_id)
    attempt = _attempt_number(attempt_dir)
    raw_wav = attempt_dir / "raw_input.wav"
    playback_wav = attempt_dir / "playback_output.wav"
    qc_json = attempt_dir / "qc.json"
    metadata_json_in = attempt_dir / "metadata.json"
    if not raw_wav.exists():
        raise FileNotFoundError(f"missing raw_input.wav for {trial.trial_id}: {raw_wav}")

    raw, sample_rate = sf.read(raw_wav, dtype="float32", always_2d=True)
    if raw.shape[1] < 3:
        raise ValueError(f"expected raw_input.wav with at least 3 channels: {raw_wav}")

    qc = json.loads(qc_json.read_text()) if qc_json.exists() else {}
    acquisition_metadata = (
        json.loads(metadata_json_in.read_text()) if metadata_json_in.exists() else {}
    )
    qc_config = config.get("qc", {})
    loopback_lag_samples: int | None = None
    loopback_lag_ms: float | None = None
    loopback_correlation: float | None = None
    if playback_wav.exists():
        playback, playback_sample_rate = sf.read(playback_wav, dtype="float32", always_2d=True)
        if int(playback_sample_rate) == int(sample_rate):
            reference_output_index = int(
                config.get("audio_device", {})
                .get("channel_selection", {})
                .get("reference_output_index", 2)
            )
            if playback.shape[1] > reference_output_index:
                lag, corr = _lagged_normalized_correlation(
                    raw[:, 2],
                    playback[:, reference_output_index],
                    max_lag_samples=int(round(0.5 * float(sample_rate))),
                )
                loopback_lag_samples = lag
                loopback_lag_ms = 1000.0 * lag / float(sample_rate)
                loopback_correlation = corr
    response_length = int(
        round(float(qc_config.get("ir_window_duration_s", 0.5)) * float(sample_rate))
    )
    pre_samples = int(qc_config.get("ir_pre_peak_samples", 32))
    result = deconvolve_stereo_brir(
        ear_l=raw[:, 0],
        ear_r=raw[:, 1],
        reference=raw[:, 2],
        sample_rate_hz=int(sample_rate),
        response_length_samples=response_length,
        regularization_fraction=float(qc_config.get("deconvolution_lambda_fraction", 1e-10)),
        pre_samples=pre_samples,
    )

    ear_l_wav = ir_root / f"{trial.trial_id}_ear_L.wav"
    ear_r_wav = ir_root / f"{trial.trial_id}_ear_R.wav"
    stereo_wav = ir_root / f"{trial.trial_id}_stereo.wav"
    sf.write(ear_l_wav, result.left_ir, sample_rate, subtype="FLOAT")
    sf.write(ear_r_wav, result.right_ir, sample_rate, subtype="FLOAT")
    sf.write(
        stereo_wav,
        np.column_stack([result.left_ir, result.right_ir]),
        sample_rate,
        subtype="FLOAT",
    )

    speaker_info = config.get("geometry", {}).get("speaker_reference", {}).get(trial.speaker, {})
    speaker_azimuth = float(speaker_info.get("azimuth_deg", 0.0))
    speaker_distance = speaker_info.get("distance_m")
    speaker_distance_m = float(speaker_distance) if speaker_distance is not None else None

    metadata_out = metadata_root / f"{trial.trial_id}.json"
    metadata = {
        "trial": trial.as_csv_row(),
        "session_id": session_id,
        "attempt": attempt,
        "source_raw_wav": str(raw_wav),
        "source_playback_wav": str(playback_wav),
        "source_qc_json": str(qc_json),
        "source_metadata_json": str(metadata_json_in),
        "geometry": config.get("geometry", {}),
        "speaker_azimuth_deg": speaker_azimuth,
        "speaker_distance_m": speaker_distance_m,
        "sample_rate_hz": int(sample_rate),
        "frames_in": int(raw.shape[0]),
        "raw_channel_order": ["ear_L", "ear_R", "electrical_reference"],
        "deconvolution": {
            "reference_channel": "electrical_reference",
            "regularization": result.regularization,
            "regularization_fraction": float(
                qc_config.get("deconvolution_lambda_fraction", 1e-10)
            ),
            "ir_samples": response_length,
            "window_start_sample": result.window_start_sample,
            "common_left_right_window": True,
            "itd_preserved": True,
        },
        "metrics": {
            "left_peak_sample_full": result.left_peak_sample_full,
            "right_peak_sample_full": result.right_peak_sample_full,
            "left_peak_sample_windowed": result.left_peak_sample_windowed,
            "right_peak_sample_windowed": result.right_peak_sample_windowed,
            "itd_ms": result.itd_ms,
            "ild_db": result.ild_db,
            "reference_rms_dbfs": _rms_dbfs(raw[:, 2]),
            "loopback_lag_samples": loopback_lag_samples,
            "loopback_lag_ms": loopback_lag_ms,
            "loopback_correlation": loopback_correlation,
            "ear_l_rms_dbfs": _rms_dbfs(raw[:, 0]),
            "ear_r_rms_dbfs": _rms_dbfs(raw[:, 1]),
        },
        "qc": qc,
        "acquisition_metadata": acquisition_metadata,
        "outputs": {
            "ear_l_wav": str(ear_l_wav),
            "ear_r_wav": str(ear_r_wav),
            "stereo_wav": str(stereo_wav),
        },
    }
    metadata_out.write_text(json.dumps(metadata, indent=2))

    fail_reasons = qc.get("fail_reasons", qc.get("qc_failures", []))
    if isinstance(fail_reasons, list):
        fail_text = ";".join(str(item) for item in fail_reasons)
    else:
        fail_text = str(fail_reasons)
    return ProcessedBrir(
        trial_id=trial.trial_id,
        session_id=session_id,
        angle_sequence_index=trial.angle_sequence_index,
        angle_nominal_deg=trial.angle_nominal_deg,
        angle_wrapped_deg=trial.angle_wrapped_deg,
        closure_measurement=trial.closure_measurement,
        speaker=trial.speaker,
        speaker_azimuth_deg=speaker_azimuth,
        speaker_distance_m=speaker_distance_m,
        repetition=trial.repetition,
        attempt=attempt,
        sample_rate_hz=int(sample_rate),
        frames_in=int(raw.shape[0]),
        ir_samples=response_length,
        window_start_sample=result.window_start_sample,
        left_peak_sample_full=result.left_peak_sample_full,
        right_peak_sample_full=result.right_peak_sample_full,
        left_peak_sample_windowed=result.left_peak_sample_windowed,
        right_peak_sample_windowed=result.right_peak_sample_windowed,
        itd_ms=result.itd_ms,
        ild_db=result.ild_db,
        reference_rms_dbfs=_rms_dbfs(raw[:, 2]),
        loopback_lag_samples=loopback_lag_samples,
        loopback_lag_ms=loopback_lag_ms,
        loopback_correlation=loopback_correlation,
        ear_l_rms_dbfs=_rms_dbfs(raw[:, 0]),
        ear_r_rms_dbfs=_rms_dbfs(raw[:, 1]),
        qc_passed_basic=qc.get("passed_basic_qc"),
        qc_fail_reasons=fail_text,
        ear_l_wav=str(ear_l_wav),
        ear_r_wav=str(ear_r_wav),
        stereo_wav=str(stereo_wav),
        metadata_json=str(metadata_out),
    )


def _validation_pairs(
    trials: list[BrirTrial],
    mode: str,
) -> list[tuple[str, BrirTrial, BrirTrial]]:
    pairs: list[tuple[str, BrirTrial, BrirTrial]] = []
    if mode in {"same", "both"}:
        pairs.extend(("same_trial", trial, trial) for trial in trials)
    if mode in {"cross", "both"}:
        by_key = {
            (trial.angle_nominal_deg, trial.speaker, trial.repetition): trial for trial in trials
        }
        for trial in trials:
            other_repetition = 2 if trial.repetition == 1 else 1
            other = by_key[(trial.angle_nominal_deg, trial.speaker, other_repetition)]
            pairs.append(("cross_repetition", trial, other))
    return pairs


def _validate_brir_pair(
    source: BrirTrial,
    target: BrirTrial,
    validation_type: str,
    session_id: str,
    session_raw: Path,
    ir_root: Path,
    metadata_root: Path,
    validation_audio_root: Path,
    write_wavs: bool,
    sf,
) -> BrirValidationResult:
    source_metadata_path = metadata_root / f"{source.trial_id}.json"
    source_metadata = json.loads(source_metadata_path.read_text())
    window_start = int(source_metadata["deconvolution"]["window_start_sample"])
    source_ir, ir_sample_rate = sf.read(
        ir_root / f"{source.trial_id}_stereo.wav",
        dtype="float32",
        always_2d=True,
    )
    target_attempt = _select_attempt_dir(session_raw / target.trial_id)
    target_raw, raw_sample_rate = sf.read(
        target_attempt / "raw_input.wav",
        dtype="float32",
        always_2d=True,
    )
    if int(ir_sample_rate) != int(raw_sample_rate):
        raise ValueError(
            f"sample rate mismatch for {source.trial_id} -> {target.trial_id}: "
            f"{ir_sample_rate} vs {raw_sample_rate}"
        )
    if source_ir.shape[1] < 2 or target_raw.shape[1] < 3:
        raise ValueError(f"invalid channel count for {source.trial_id} -> {target.trial_id}")

    reference = target_raw[:, 2]
    predicted = np.column_stack(
        [
            predict_recording_from_ir(reference, source_ir[:, 0], window_start, len(target_raw)),
            predict_recording_from_ir(reference, source_ir[:, 1], window_start, len(target_raw)),
        ]
    )
    recorded = target_raw[:, :2].astype(np.float32, copy=False)
    residual = recorded - predicted

    left = _prediction_metrics(recorded[:, 0], predicted[:, 0])
    right = _prediction_metrics(recorded[:, 1], predicted[:, 1])
    validation_id = _validation_id(validation_type, source.trial_id, target.trial_id)
    predicted_wav = ""
    residual_wav = ""
    if write_wavs:
        predicted_path = validation_audio_root / f"{validation_id}_predicted.wav"
        residual_path = validation_audio_root / f"{validation_id}_residual.wav"
        sf.write(predicted_path, predicted, raw_sample_rate, subtype="FLOAT")
        sf.write(residual_path, residual, raw_sample_rate, subtype="FLOAT")
        predicted_wav = str(predicted_path)
        residual_wav = str(residual_path)

    return BrirValidationResult(
        validation_id=validation_id,
        validation_type=validation_type,
        session_id=session_id,
        source_trial_id=source.trial_id,
        target_trial_id=target.trial_id,
        angle_nominal_deg=target.angle_nominal_deg,
        angle_wrapped_deg=target.angle_wrapped_deg,
        closure_measurement=target.closure_measurement,
        speaker=target.speaker,
        source_repetition=source.repetition,
        target_repetition=target.repetition,
        sample_rate_hz=int(raw_sample_rate),
        frames_compared=int(len(recorded)),
        source_window_start_sample=window_start,
        ear_l_prediction_sdr_db=left["prediction_sdr_db"],
        ear_r_prediction_sdr_db=right["prediction_sdr_db"],
        mean_prediction_sdr_db=float(
            np.mean([left["prediction_sdr_db"], right["prediction_sdr_db"]])
        ),
        ear_l_corr=left["corr"],
        ear_r_corr=right["corr"],
        mean_corr=float(np.mean([left["corr"], right["corr"]])),
        ear_l_nrmse=left["nrmse"],
        ear_r_nrmse=right["nrmse"],
        mean_nrmse=float(np.mean([left["nrmse"], right["nrmse"]])),
        ear_l_residual_rms_dbfs=left["residual_rms_dbfs"],
        ear_r_residual_rms_dbfs=right["residual_rms_dbfs"],
        ear_l_best_fit_gain=left["best_fit_gain"],
        ear_r_best_fit_gain=right["best_fit_gain"],
        ear_l_gain_corrected_sdr_db=left["gain_corrected_sdr_db"],
        ear_r_gain_corrected_sdr_db=right["gain_corrected_sdr_db"],
        predicted_wav=predicted_wav,
        residual_wav=residual_wav,
    )


def predict_recording_from_ir(
    reference: np.ndarray,
    windowed_ir: np.ndarray,
    window_start_sample: int,
    output_length: int,
) -> np.ndarray:
    reference32 = np.asarray(reference, dtype=np.float32)
    ir32 = np.asarray(windowed_ir, dtype=np.float32)
    try:
        from scipy.signal import fftconvolve

        convolution = fftconvolve(reference32, ir32, mode="full")
    except ModuleNotFoundError:  # pragma: no cover - exercised in minimal local envs
        convolution = np.convolve(reference32, ir32, mode="full")
    predicted = np.zeros(output_length, dtype=np.float32)
    start = int(window_start_sample)
    if start >= output_length:
        return predicted
    count = min(output_length - start, len(convolution))
    predicted[start : start + count] = convolution[:count].astype(np.float32, copy=False)
    return predicted


def _prediction_metrics(recorded: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    recorded64 = np.asarray(recorded, dtype=np.float64)
    predicted64 = np.asarray(predicted, dtype=np.float64)
    residual = recorded64 - predicted64
    recorded_norm = float(np.linalg.norm(recorded64))
    predicted_norm = float(np.linalg.norm(predicted64))
    residual_norm = float(np.linalg.norm(residual))
    nrmse = residual_norm / recorded_norm if recorded_norm > 0.0 else float("inf")
    prediction_sdr = _ratio_db(recorded_norm, residual_norm)
    corr = _zero_lag_corr(recorded64, predicted64)
    if predicted_norm > 0.0:
        gain = float(np.dot(recorded64, predicted64) / np.dot(predicted64, predicted64))
        gain_residual_norm = float(np.linalg.norm(recorded64 - gain * predicted64))
        gain_corrected_sdr = _ratio_db(recorded_norm, gain_residual_norm)
    else:
        gain = 0.0
        gain_corrected_sdr = float("-inf")
    return {
        "prediction_sdr_db": prediction_sdr,
        "corr": corr,
        "nrmse": nrmse,
        "residual_rms_dbfs": _rms_dbfs(residual),
        "best_fit_gain": gain,
        "gain_corrected_sdr_db": gain_corrected_sdr,
    }


def _validation_id(validation_type: str, source_trial_id: str, target_trial_id: str) -> str:
    if source_trial_id == target_trial_id:
        return f"{validation_type}__{source_trial_id}"
    return f"{validation_type}__{source_trial_id}__to__{target_trial_id}"


def _select_attempt_dir(trial_dir: Path) -> Path:
    if not trial_dir.exists():
        raise FileNotFoundError(f"missing trial directory: {trial_dir}")
    attempts = sorted(
        [path for path in trial_dir.glob("attempt_*") if path.is_dir()],
        key=_attempt_number,
    )
    attempts_with_raw = [path for path in attempts if (path / "raw_input.wav").exists()]
    if not attempts_with_raw:
        raise FileNotFoundError(f"no attempt with raw_input.wav found in {trial_dir}")
    return attempts_with_raw[-1]


def _attempt_number(attempt_dir: Path) -> int:
    try:
        return int(attempt_dir.name.split("_")[-1])
    except ValueError:
        return -1


def _regularization_from_reference(
    reference: np.ndarray,
    recorded_length: int,
    fraction: float,
) -> float:
    reference = np.asarray(reference, dtype=float)
    n_fft = 1 << int(np.ceil(np.log2(recorded_length + len(reference) - 1)))
    reference_spectrum = np.fft.rfft(reference, n=n_fft)
    max_power = float(np.max(np.abs(reference_spectrum) ** 2))
    return max(max_power * fraction, np.finfo(float).eps)


def _window_response(response: np.ndarray, start: int, length: int) -> np.ndarray:
    end = start + length
    windowed = np.asarray(response[start:end], dtype=np.float32)
    if len(windowed) < length:
        windowed = np.pad(windowed, (0, length - len(windowed)))
    return windowed.astype(np.float32)


def _lagged_normalized_correlation(
    measured: np.ndarray,
    reference: np.ndarray,
    max_lag_samples: int,
) -> tuple[int, float]:
    from scipy.signal import correlate, correlation_lags

    length = min(len(measured), len(reference))
    measured64 = np.asarray(measured[:length], dtype=np.float64)
    reference64 = np.asarray(reference[:length], dtype=np.float64)
    measured64 = measured64 - float(np.mean(measured64))
    reference64 = reference64 - float(np.mean(reference64))
    corr = correlate(measured64, reference64, mode="full", method="fft")
    lags = correlation_lags(len(measured64), len(reference64), mode="full")
    mask = np.abs(lags) <= max_lag_samples
    if not np.any(mask):
        return 0, 0.0
    corr_window = corr[mask]
    lags_window = lags[mask]
    best_index = int(np.argmax(np.abs(corr_window)))
    best_lag = int(lags_window[best_index])
    denom = float(np.linalg.norm(measured64) * np.linalg.norm(reference64))
    if denom <= 0.0:
        return best_lag, 0.0
    return best_lag, float(corr_window[best_index] / denom)


def _ensure_can_write(paths: list[Path], overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if path.exists()]
    if existing:
        sample = "\n".join(str(path) for path in existing[:5])
        raise FileExistsError(
            "refusing to overwrite existing Experiment 2 processed outputs. "
            f"Use --overwrite to replace them. Existing files include:\n{sample}"
        )


def _write_processing_summary_csv(path: Path, rows: list[ProcessedBrir]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=PROCESS_SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv_row())


def _write_validation_summary_csv(path: Path, rows: list[BrirValidationResult]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=VALIDATION_SUMMARY_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.as_csv_row())


def _rms_dbfs(signal: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(np.asarray(signal, dtype=np.float64)))))
    if rms <= 0.0:
        return float("-inf")
    return float(20.0 * np.log10(rms))


def _ratio_db(numerator_norm: float, denominator_norm: float) -> float:
    if denominator_norm <= 0.0:
        return float("inf")
    if numerator_norm <= 0.0:
        return float("-inf")
    return float(20.0 * np.log10(numerator_norm / denominator_norm))


def _zero_lag_corr(a: np.ndarray, b: np.ndarray) -> float:
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    a64 = a64 - float(np.mean(a64))
    b64 = b64 - float(np.mean(b64))
    denom = float(np.linalg.norm(a64) * np.linalg.norm(b64))
    if denom <= 0.0:
        return 0.0
    return float(np.dot(a64, b64) / denom)


def _mean_or_none(values: list[float]) -> float | None:
    if not values:
        return None
    return float(np.mean(values))
