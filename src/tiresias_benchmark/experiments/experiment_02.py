from __future__ import annotations

import csv
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

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


def run(config: dict) -> dict:
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


def _format_output_channel(array_index: object) -> str:
    return f"output_{int(array_index) + 1}"


def _format_input_channels(channels: dict) -> str:
    mic_l = int(channels.get("mic_left_index", 0)) + 1
    mic_r = int(channels.get("mic_right_index", 1)) + 1
    ref = int(channels.get("reference_input_index", 4)) + 1
    return f"input_{mic_l}:ear_L;input_{mic_r}:ear_R;input_{ref}:reference"
