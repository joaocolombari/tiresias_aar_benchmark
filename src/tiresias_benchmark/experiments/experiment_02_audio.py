from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import hashlib
import json
from math import ceil
from pathlib import Path
import struct
import threading
import time
from typing import Any

import numpy as np

from tiresias_benchmark.acoustics.sweep import exponential_sine_sweep, sweep_with_silence


@dataclass(frozen=True)
class AudioSelection:
    input_device_index: int
    output_device_index: int
    input_device_name: str
    output_device_name: str
    host_api_name: str
    input_channel_count: int
    output_channel_count: int


@dataclass(frozen=True)
class TrialAudioResult:
    attempt_dir: Path
    raw_input_wav: Path
    playback_output_wav: Path
    metadata_json: Path
    callback_timeline_csv: Path
    qc_json: Path

    def as_dict(self) -> dict[str, str]:
        return {key: str(value) for key, value in asdict(self).items()}


def list_audio_devices() -> dict[str, Any]:
    sd = _require_sounddevice()
    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    return {
        "hostapis": [
            {
                "index": index,
                "name": api["name"],
                "default_input_device": api["default_input_device"],
                "default_output_device": api["default_output_device"],
            }
            for index, api in enumerate(hostapis)
        ],
        "devices": [
            {
                "index": index,
                "name": device["name"],
                "hostapi": device["hostapi"],
                "hostapi_name": hostapis[int(device["hostapi"])]["name"],
                "max_input_channels": device["max_input_channels"],
                "max_output_channels": device["max_output_channels"],
                "default_samplerate": device["default_samplerate"],
            }
            for index, device in enumerate(devices)
        ],
    }


def preflight_audio(config: dict, duration_s: float = 0.25, open_stream: bool = True) -> dict:
    sd = _require_sounddevice()
    selection = select_audio_device(config)
    audio = config["audio_device"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    dtype = str(audio.get("dtype", "float32"))

    sd.check_input_settings(
        device=selection.input_device_index,
        channels=selection.input_channel_count,
        samplerate=sample_rate,
        dtype=dtype,
    )
    sd.check_output_settings(
        device=selection.output_device_index,
        channels=selection.output_channel_count,
        samplerate=sample_rate,
        dtype=dtype,
    )

    opened_stream = False
    if open_stream:
        frames_seen = 0

        def callback(indata, outdata, frames, callback_time, status):  # noqa: ARG001
            nonlocal frames_seen
            outdata.fill(0.0)
            frames_seen += frames
            if frames_seen >= int(round(duration_s * sample_rate)):
                raise sd.CallbackStop()

        with sd.Stream(
            device=(selection.input_device_index, selection.output_device_index),
            samplerate=sample_rate,
            blocksize=block_size,
            dtype=dtype,
            channels=(selection.input_channel_count, selection.output_channel_count),
            callback=callback,
        ):
            sd.sleep(int((duration_s + 0.5) * 1000))
        opened_stream = True

    return {
        "selection": asdict(selection),
        "sample_rate_hz": sample_rate,
        "block_size_frames": block_size,
        "dtype": dtype,
        "opened_zero_output_stream": opened_stream,
    }


def select_audio_device(config: dict) -> AudioSelection:
    sd = _require_sounddevice()
    audio = config["audio_device"]
    preferred_api = str(audio.get("preferred_host_api", "")).lower()
    name_contains = str(audio.get("device_name_contains", "")).lower()
    required_inputs = int(audio.get("open_input_channel_count", 0))
    required_outputs = int(audio.get("open_output_channel_count", 0))

    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    candidates: list[tuple[int, dict]] = []
    for index, device in enumerate(devices):
        api_name = str(hostapis[int(device["hostapi"])]["name"])
        if preferred_api and preferred_api not in api_name.lower():
            continue
        if name_contains and name_contains not in str(device["name"]).lower():
            continue
        if int(device["max_input_channels"]) < required_inputs:
            continue
        if int(device["max_output_channels"]) < required_outputs:
            continue
        candidates.append((index, device))

    if not candidates:
        raise RuntimeError(
            "No full-duplex audio device matches the Experiment 2 config. "
            "Check preferred_host_api, device_name_contains and channel counts."
        )

    index, device = candidates[0]
    host_api_name = str(hostapis[int(device["hostapi"])]["name"])
    return AudioSelection(
        input_device_index=index,
        output_device_index=index,
        input_device_name=str(device["name"]),
        output_device_name=str(device["name"]),
        host_api_name=host_api_name,
        input_channel_count=required_inputs,
        output_channel_count=required_outputs,
    )


def record_probe(
    config: dict,
    speaker: str,
    session_id: str,
    output_root: str | Path | None = None,
    attempt: int = 1,
    armed: bool = False,
    simulate: bool = False,
    overwrite: bool = False,
) -> TrialAudioResult:
    probe = config["audio_device"]["probe_signal"]
    sample_rate = int(config["audio_device"]["sample_rate_hz"])
    tone = _probe_tone(
        sample_rate_hz=sample_rate,
        frequency_hz=float(probe["frequency_hz"]),
        level_dbfs=float(probe["level_dbfs"]),
        duration_s=float(probe["duration_s"]),
        fade_in_s=float(probe["fade_in_s"]),
        fade_out_s=float(probe["fade_out_s"]),
    )
    signal = sweep_with_silence(
        tone,
        sample_rate,
        pre_silence_s=float(probe["pre_silence_s"]),
        post_silence_s=float(probe["post_silence_s"]),
    )
    return _record_signal(
        config=config,
        signal=signal,
        signal_kind="channel_probe",
        speaker=speaker,
        angle_deg=0,
        repetition=1,
        session_id=session_id,
        output_root=output_root,
        attempt=attempt,
        armed=armed,
        simulate=simulate,
        overwrite=overwrite,
        subdirectory="probes",
    )


def record_test_sweep(
    config: dict,
    speaker: str,
    angle_deg: int,
    repetition: int,
    session_id: str,
    output_root: str | Path | None = None,
    attempt: int = 1,
    armed: bool = False,
    simulate: bool = False,
    overwrite: bool = False,
) -> TrialAudioResult:
    sweep_config = config["sweep"]
    sample_rate = int(sweep_config["sample_rate_hz"])
    duration_s = int(sweep_config["sweep_frames"]) / sample_rate
    sweep = exponential_sine_sweep(
        duration_s=duration_s,
        sample_rate_hz=sample_rate,
        start_hz=float(sweep_config["sweep_start_hz"]),
        stop_hz=float(sweep_config["sweep_end_hz"]),
        amplitude=10.0 ** (float(sweep_config["level_dbfs"]) / 20.0),
    )
    signal = sweep_with_silence(
        sweep,
        sample_rate,
        pre_silence_s=float(sweep_config["pre_silence_s"]),
        post_silence_s=float(sweep_config["post_silence_s"]),
    )
    return _record_signal(
        config=config,
        signal=signal,
        signal_kind="test_sweep",
        speaker=speaker,
        angle_deg=angle_deg,
        repetition=repetition,
        session_id=session_id,
        output_root=output_root,
        attempt=attempt,
        armed=armed,
        simulate=simulate,
        overwrite=overwrite,
        subdirectory="sweeps",
    )


def _record_signal(
    config: dict,
    signal: np.ndarray,
    signal_kind: str,
    speaker: str,
    angle_deg: int,
    repetition: int,
    session_id: str,
    output_root: str | Path | None,
    attempt: int,
    armed: bool,
    simulate: bool,
    overwrite: bool,
    subdirectory: str,
) -> TrialAudioResult:
    speaker = speaker.upper()
    if speaker not in {"A", "B"}:
        raise ValueError("speaker must be A or B")
    if not simulate and not armed:
        raise RuntimeError("Refusing to emit audio without --armed. Use --simulate for dry runs.")

    audio = config["audio_device"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    input_count = int(audio["open_input_channel_count"])
    output_count = int(audio["open_output_channel_count"])
    channels = audio["channel_selection"]

    playback = _build_playback_matrix(signal, output_count, speaker, channels)
    raw = np.zeros((len(playback), 3), dtype=np.float32)
    max_blocks = ceil(len(playback) / block_size) + 8
    timeline = _empty_timeline(max_blocks)

    if simulate:
        _simulate_capture(playback, raw, timeline, sample_rate, block_size, channels)
        selection: AudioSelection | None = None
    else:
        selection = select_audio_device(config)
        _capture_full_duplex(
            config=config,
            playback=playback,
            raw=raw,
            timeline=timeline,
            selection=selection,
        )

    attempt_dir = _attempt_directory(
        config=config,
        session_id=session_id,
        subdirectory=subdirectory,
        speaker=speaker,
        angle_deg=angle_deg,
        repetition=repetition,
        attempt=attempt,
        output_root=output_root,
    )
    if attempt_dir.exists() and not overwrite:
        raise FileExistsError(f"refusing to overwrite existing attempt directory: {attempt_dir}")
    attempt_dir.mkdir(parents=True, exist_ok=True)

    raw_input_wav = attempt_dir / "raw_input.wav"
    playback_output_wav = attempt_dir / "playback_output.wav"
    metadata_json = attempt_dir / "metadata.json"
    callback_timeline_csv = attempt_dir / "callback_timeline.csv"
    qc_json = attempt_dir / "qc.json"

    _write_wav_float32(raw_input_wav, raw, sample_rate)
    _write_wav_float32(playback_output_wav, playback, sample_rate)
    _write_timeline_csv(callback_timeline_csv, timeline)
    qc = _compute_qc(raw, playback, channels, config)
    qc_json.write_text(json.dumps(qc, indent=2))
    metadata = _metadata(
        config=config,
        signal_kind=signal_kind,
        speaker=speaker,
        angle_deg=angle_deg,
        repetition=repetition,
        attempt=attempt,
        session_id=session_id,
        sample_rate=sample_rate,
        block_size=block_size,
        playback=playback,
        raw=raw,
        selection=selection,
        simulate=simulate,
        files={
            "raw_input_wav": raw_input_wav,
            "playback_output_wav": playback_output_wav,
            "callback_timeline_csv": callback_timeline_csv,
            "qc_json": qc_json,
        },
    )
    metadata_json.write_text(json.dumps(metadata, indent=2))

    return TrialAudioResult(
        attempt_dir=attempt_dir,
        raw_input_wav=raw_input_wav,
        playback_output_wav=playback_output_wav,
        metadata_json=metadata_json,
        callback_timeline_csv=callback_timeline_csv,
        qc_json=qc_json,
    )


def _capture_full_duplex(
    config: dict,
    playback: np.ndarray,
    raw: np.ndarray,
    timeline: dict[str, np.ndarray],
    selection: AudioSelection,
) -> None:
    sd = _require_sounddevice()
    audio = config["audio_device"]
    channels = audio["channel_selection"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    dtype = str(audio.get("dtype", "float32"))
    mic_l = int(channels["mic_left_index"])
    mic_r = int(channels["mic_right_index"])
    ref = int(channels["reference_input_index"])

    done = threading.Event()
    error: list[BaseException] = []
    cursor = 0
    block_index = 0

    def callback(indata, outdata, frames, callback_time, status):
        nonlocal cursor, block_index
        try:
            outdata.fill(0.0)
            start = cursor
            stop = min(start + frames, len(playback))
            valid = stop - start
            if valid > 0:
                outdata[:valid, :] = playback[start:stop, :]
                raw[start:stop, 0] = indata[:valid, mic_l]
                raw[start:stop, 1] = indata[:valid, mic_r]
                raw[start:stop, 2] = indata[:valid, ref]
            if block_index < len(timeline["frame_start"]):
                timeline["frame_start"][block_index] = start
                timeline["frames"][block_index] = frames
                timeline["status_flags"][block_index] = _callback_status_flags(status)
                timeline["input_adc_time"][block_index] = callback_time.inputBufferAdcTime
                timeline["current_time"][block_index] = callback_time.currentTime
                timeline["output_dac_time"][block_index] = callback_time.outputBufferDacTime
                timeline["perf_counter_ns"][block_index] = time.perf_counter_ns()
                timeline["valid"][block_index] = True
            cursor = stop
            block_index += 1
            if cursor >= len(playback):
                done.set()
                raise sd.CallbackStop()
        except BaseException as exc:  # pragma: no cover - exercised only by hardware callback
            error.append(exc)
            done.set()
            raise

    with sd.Stream(
        device=(selection.input_device_index, selection.output_device_index),
        samplerate=sample_rate,
        blocksize=block_size,
        dtype=dtype,
        channels=(selection.input_channel_count, selection.output_channel_count),
        callback=callback,
    ):
        timeout_s = len(playback) / sample_rate + 5.0
        if not done.wait(timeout_s):
            raise TimeoutError("audio capture did not finish before timeout")
    if error:
        raise error[0]


def _simulate_capture(
    playback: np.ndarray,
    raw: np.ndarray,
    timeline: dict[str, np.ndarray],
    sample_rate: int,
    block_size: int,
    channels: dict,
) -> None:
    ref_index = int(channels["reference_output_index"])
    reference = playback[:, ref_index]
    delay_l = int(round(0.0030 * sample_rate))
    delay_r = int(round(0.0034 * sample_rate))
    raw[:, 2] = reference + _noise(len(reference), 2e-5)
    raw[:, 0] = _delayed(reference, delay_l, 0.18) + _noise(len(reference), 1e-4)
    raw[:, 1] = _delayed(reference, delay_r, 0.16) + _noise(len(reference), 1e-4)
    for block_index, start in enumerate(range(0, len(playback), block_size)):
        frames = min(block_size, len(playback) - start)
        timeline["frame_start"][block_index] = start
        timeline["frames"][block_index] = frames
        timeline["status_flags"][block_index] = 0
        timeline["input_adc_time"][block_index] = start / sample_rate
        timeline["current_time"][block_index] = start / sample_rate
        timeline["output_dac_time"][block_index] = start / sample_rate
        timeline["perf_counter_ns"][block_index] = time.perf_counter_ns()
        timeline["valid"][block_index] = True


def _build_playback_matrix(
    signal: np.ndarray,
    output_count: int,
    speaker: str,
    channels: dict,
) -> np.ndarray:
    playback = np.zeros((len(signal), output_count), dtype=np.float32)
    speaker_key = f"speaker_{speaker}_output_index"
    active_index = int(channels[speaker_key])
    reference_index = int(channels["reference_output_index"])
    playback[:, active_index] = signal.astype(np.float32, copy=False)
    playback[:, reference_index] = signal.astype(np.float32, copy=False)
    return playback


def _probe_tone(
    sample_rate_hz: int,
    frequency_hz: float,
    level_dbfs: float,
    duration_s: float,
    fade_in_s: float,
    fade_out_s: float,
) -> np.ndarray:
    frames = int(round(sample_rate_hz * duration_s))
    t = np.arange(frames, dtype=np.float64) / sample_rate_hz
    tone = (10.0 ** (level_dbfs / 20.0)) * np.sin(2.0 * np.pi * frequency_hz * t)
    fade_in = min(frames, int(round(fade_in_s * sample_rate_hz)))
    fade_out = min(frames, int(round(fade_out_s * sample_rate_hz)))
    if fade_in > 0:
        tone[:fade_in] *= np.linspace(0.0, 1.0, fade_in)
    if fade_out > 0:
        tone[-fade_out:] *= np.linspace(1.0, 0.0, fade_out)
    return tone.astype(np.float32)


def _attempt_directory(
    config: dict,
    session_id: str,
    subdirectory: str,
    speaker: str,
    angle_deg: int,
    repetition: int,
    attempt: int,
    output_root: str | Path | None,
) -> Path:
    root = Path(output_root or config["outputs"]["sessions_root"])
    trial_id = f"brir_theta_{angle_deg:03d}_spk_{speaker}_rep{repetition:02d}"
    return root / session_id / subdirectory / trial_id / f"attempt_{attempt:02d}"


def _compute_qc(raw: np.ndarray, playback: np.ndarray, channels: dict, config: dict) -> dict:
    qc_config = config.get("qc", {})
    reference_output = playback[:, int(channels["reference_output_index"])]
    reference_input = raw[:, 2]
    peaks = {
        "ear_L": _peak_dbfs(raw[:, 0]),
        "ear_R": _peak_dbfs(raw[:, 1]),
        "reference": _peak_dbfs(reference_input),
    }
    rms = {
        "ear_L": _rms_dbfs(raw[:, 0]),
        "ear_R": _rms_dbfs(raw[:, 1]),
        "reference": _rms_dbfs(reference_input),
    }
    clipping_threshold = float(qc_config.get("clipping_threshold_linear", 0.999))
    clipping = {
        "ear_L": bool(np.max(np.abs(raw[:, 0])) >= clipping_threshold),
        "ear_R": bool(np.max(np.abs(raw[:, 1])) >= clipping_threshold),
        "reference": bool(np.max(np.abs(reference_input)) >= clipping_threshold),
    }
    reference_correlation = _normalized_correlation(reference_input, reference_output)
    fail_reasons = []
    if any(clipping.values()):
        fail_reasons.append("clipping_detected")
    if rms["reference"] < float(qc_config.get("min_reference_rms_dbfs", -60.0)):
        fail_reasons.append("reference_rms_too_low")
    if reference_correlation < float(qc_config.get("min_loopback_correlation", 0.8)):
        fail_reasons.append("low_reference_correlation")
    return {
        "passed_basic_qc": not fail_reasons,
        "fail_reasons": fail_reasons,
        "peak_dbfs": peaks,
        "rms_dbfs": rms,
        "clipping": clipping,
        "reference_correlation": reference_correlation,
        "frames": int(len(raw)),
        "raw_shape": list(raw.shape),
        "playback_shape": list(playback.shape),
    }


def _metadata(
    config: dict,
    signal_kind: str,
    speaker: str,
    angle_deg: int,
    repetition: int,
    attempt: int,
    session_id: str,
    sample_rate: int,
    block_size: int,
    playback: np.ndarray,
    raw: np.ndarray,
    selection: AudioSelection | None,
    simulate: bool,
    files: dict[str, Path],
) -> dict:
    trial_id = f"brir_theta_{angle_deg:03d}_spk_{speaker}_rep{repetition:02d}"
    return {
        "experiment_id": config.get("experiment_id", "exp02_brir_measurement"),
        "session_id": session_id,
        "trial_id": trial_id,
        "signal_kind": signal_kind,
        "angle_nominal_deg": angle_deg,
        "angle_wrapped_deg": angle_deg % 360,
        "closure_measurement": angle_deg == int(config["planning"].get("closure_measurement_deg", 360)),
        "speaker": speaker,
        "repetition": repetition,
        "attempt": attempt,
        "simulated": simulate,
        "sample_rate_hz": sample_rate,
        "block_size_frames": block_size,
        "raw_channel_order": ["ear_L", "ear_R", "electrical_reference"],
        "audio_selection": asdict(selection) if selection else None,
        "audio_device_config": config["audio_device"],
        "playback_sha256": _array_sha256(playback),
        "raw_sha256": _array_sha256(raw),
        "files": {key: str(value) for key, value in files.items()},
        "created_host_time_ns": time.time_ns(),
    }


def _empty_timeline(max_blocks: int) -> dict[str, np.ndarray]:
    return {
        "frame_start": np.zeros(max_blocks, dtype=np.int64),
        "frames": np.zeros(max_blocks, dtype=np.int32),
        "status_flags": np.zeros(max_blocks, dtype=np.int32),
        "input_adc_time": np.zeros(max_blocks, dtype=np.float64),
        "current_time": np.zeros(max_blocks, dtype=np.float64),
        "output_dac_time": np.zeros(max_blocks, dtype=np.float64),
        "perf_counter_ns": np.zeros(max_blocks, dtype=np.int64),
        "valid": np.zeros(max_blocks, dtype=bool),
    }


def _write_timeline_csv(path: Path, timeline: dict[str, np.ndarray]) -> None:
    fields = [
        "frame_start",
        "frames",
        "status_flags",
        "input_adc_time",
        "current_time",
        "output_dac_time",
        "perf_counter_ns",
    ]
    valid_indices = np.flatnonzero(timeline["valid"])
    with path.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        for index in valid_indices:
            writer.writerow([timeline[field][index].item() for field in fields])


def _write_wav_float32(path: Path, data: np.ndarray, sample_rate: int) -> None:
    try:
        import soundfile as sf

        sf.write(path, data.astype(np.float32, copy=False), sample_rate, subtype="FLOAT")
    except ImportError:
        _write_wav_float32_stdlib(path, data, sample_rate)


def _write_wav_float32_stdlib(path: Path, data: np.ndarray, sample_rate: int) -> None:
    array = np.asarray(data, dtype="<f4")
    if array.ndim == 1:
        array = array[:, np.newaxis]
    frames, channels = array.shape
    byte_rate = sample_rate * channels * 4
    block_align = channels * 4
    payload = np.ascontiguousarray(array).tobytes()
    fmt_chunk = struct.pack(
        "<HHIIHH",
        3,  # WAVE_FORMAT_IEEE_FLOAT
        channels,
        sample_rate,
        byte_rate,
        block_align,
        32,
    )
    fact_chunk = struct.pack("<I", frames)
    riff_size = 4 + (8 + len(fmt_chunk)) + (8 + len(fact_chunk)) + (8 + len(payload))
    with path.open("wb") as file:
        file.write(b"RIFF")
        file.write(struct.pack("<I", riff_size))
        file.write(b"WAVE")
        file.write(b"fmt ")
        file.write(struct.pack("<I", len(fmt_chunk)))
        file.write(fmt_chunk)
        file.write(b"fact")
        file.write(struct.pack("<I", len(fact_chunk)))
        file.write(fact_chunk)
        file.write(b"data")
        file.write(struct.pack("<I", len(payload)))
        file.write(payload)


def _array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array.astype(np.float32, copy=False))
    return hashlib.sha256(contiguous.tobytes()).hexdigest()


def _peak_dbfs(signal: np.ndarray) -> float:
    peak = float(np.max(np.abs(signal)))
    if peak <= 0.0:
        return float("-inf")
    return float(20.0 * np.log10(peak))


def _rms_dbfs(signal: np.ndarray) -> float:
    rms = float(np.sqrt(np.mean(np.square(signal, dtype=np.float64))))
    if rms <= 0.0:
        return float("-inf")
    return float(20.0 * np.log10(rms))


def _normalized_correlation(a: np.ndarray, b: np.ndarray) -> float:
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    denom = float(np.linalg.norm(a64) * np.linalg.norm(b64))
    if denom <= 0.0:
        return 0.0
    return float(np.dot(a64, b64) / denom)


def _delayed(signal: np.ndarray, delay_samples: int, gain: float) -> np.ndarray:
    out = np.zeros_like(signal, dtype=np.float32)
    if delay_samples < len(signal):
        out[delay_samples:] = gain * signal[: len(signal) - delay_samples]
    return out


def _noise(length: int, scale: float) -> np.ndarray:
    rng = np.random.default_rng(20260713)
    return rng.normal(0.0, scale, length).astype(np.float32)


def _require_sounddevice():
    try:
        import sounddevice as sd
    except ImportError as exc:  # pragma: no cover - depends on local optional package
        raise RuntimeError(
            "sounddevice is required for Experiment 2 audio hardware commands. "
            "Install with: python -m pip install -e '.[acquisition]'"
        ) from exc
    return sd


def _callback_status_flags(status: object) -> int:
    try:
        return int(status)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        flags = getattr(status, "_flags", None)
        if flags is not None:
            return int(flags)
        return 1 if bool(status) else 0
