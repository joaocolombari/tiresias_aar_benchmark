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


DEFAULT_STREAM_DTYPE_CANDIDATES = ["float32", "int32", "int16"]


@dataclass(frozen=True)
class AudioDevicePair:
    input_device_index: int
    input_device_name: str
    output_device_index: int
    output_device_name: str
    host_api_index: int
    host_api_name: str
    max_input_channels: int
    max_output_channels: int
    requested_input_channels: int
    requested_output_channels: int


@dataclass(frozen=True)
class CandidatePair:
    input_device_index: int | None
    input_device_name: str | None
    output_device_index: int | None
    output_device_name: str | None
    host_api_index: int | None
    host_api_name: str | None
    max_input_channels: int
    max_output_channels: int
    requested_input_channels: int
    requested_output_channels: int
    supports_requested_settings: bool
    rejection_reason: str | None


class AudioPreflightError(RuntimeError):
    def __init__(self, message: str, report: dict[str, Any]):
        super().__init__(message)
        self.report = report


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


def list_audio_devices(config: dict | None = None) -> dict[str, Any]:
    sd = _require_sounddevice()
    hostapis = sd.query_hostapis()
    devices = sd.query_devices()
    config_for_pairs = config or _default_audio_listing_config()
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
                "direction": _device_direction(device),
            }
            for index, device in enumerate(devices)
        ],
        "candidate_pairs": [
            asdict(candidate)
            for candidate in find_audio_device_pairs(config_for_pairs, hostapis, devices)
        ],
    }


def preflight_audio(config: dict, duration_s: float = 0.25, open_stream: bool = True) -> dict:
    sd = _require_sounddevice()
    selection = select_audio_device_pair(config)
    audio = config["audio_device"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    dtype_probe = probe_audio_formats(config, duration_s=duration_s, open_stream=open_stream)
    dtype = dtype_probe.get("selected_stream_dtype")
    report: dict[str, Any] = {
        "selection": asdict(selection),
        "sample_rate_hz": sample_rate,
        "block_size_frames": block_size,
        "stream_dtype": dtype,
        "storage_dtype": _storage_dtype(config),
        "dtype_probe": dtype_probe,
        "input_latency": None,
        "output_latency": None,
        "check_input_settings": {"passed": False, "exception": None},
        "check_output_settings": {"passed": False, "exception": None},
        "full_duplex_open": {"passed": False, "attempted": open_stream, "exception": None},
    }
    if not dtype:
        report["passed"] = False
        raise AudioPreflightError("no supported stream dtype found", report)

    try:
        sd.check_input_settings(
            device=selection.input_device_index,
            channels=selection.requested_input_channels,
            samplerate=sample_rate,
            dtype=dtype,
        )
        report["check_input_settings"]["passed"] = True
    except Exception as exc:
        report["check_input_settings"]["exception"] = repr(exc)
        report["passed"] = False
        raise AudioPreflightError(f"unsupported input settings: {exc}", report) from exc

    try:
        sd.check_output_settings(
            device=selection.output_device_index,
            channels=selection.requested_output_channels,
            samplerate=sample_rate,
            dtype=dtype,
        )
        report["check_output_settings"]["passed"] = True
    except Exception as exc:
        report["check_output_settings"]["exception"] = repr(exc)
        report["passed"] = False
        raise AudioPreflightError(f"unsupported output settings: {exc}", report) from exc

    if open_stream:
        frames_seen = 0

        def callback(indata, outdata, frames, callback_time, status):  # noqa: ARG001
            nonlocal frames_seen
            outdata.fill(0.0)
            frames_seen += frames
            if frames_seen >= int(round(duration_s * sample_rate)):
                raise sd.CallbackStop()

        try:
            with sd.Stream(
                device=(selection.input_device_index, selection.output_device_index),
                samplerate=sample_rate,
                blocksize=block_size,
                dtype=dtype,
                channels=(selection.requested_input_channels, selection.requested_output_channels),
                callback=callback,
            ) as stream:
                report["input_latency"] = getattr(stream, "latency", (None, None))[0]
                report["output_latency"] = getattr(stream, "latency", (None, None))[1]
                sd.sleep(int((duration_s + 0.5) * 1000))
            report["full_duplex_open"]["passed"] = True
        except Exception as exc:
            report["full_duplex_open"]["exception"] = repr(exc)
            report["passed"] = False
            raise AudioPreflightError(f"full-duplex pair open failed: {exc}", report) from exc

    report["passed"] = bool(
        report["check_input_settings"]["passed"]
        and report["check_output_settings"]["passed"]
        and open_stream
        and report["full_duplex_open"]["passed"]
    )
    return report


def probe_audio_formats(config: dict, duration_s: float = 0.05, open_stream: bool = True) -> dict:
    sd = _require_sounddevice()
    selection = select_audio_device_pair(config)
    audio = config["audio_device"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    candidates = _stream_dtype_candidates(config)
    results = []
    selected = None
    for dtype in candidates:
        item: dict[str, Any] = {
            "stream_dtype": dtype,
            "check_input_settings": {"passed": False, "exception": None},
            "check_output_settings": {"passed": False, "exception": None},
            "full_duplex_open": {"passed": False, "attempted": open_stream, "exception": None},
            "passed": False,
        }
        try:
            sd.check_input_settings(
                device=selection.input_device_index,
                channels=selection.requested_input_channels,
                samplerate=sample_rate,
                dtype=dtype,
            )
            item["check_input_settings"]["passed"] = True
        except Exception as exc:
            item["check_input_settings"]["exception"] = repr(exc)
            results.append(item)
            continue
        try:
            sd.check_output_settings(
                device=selection.output_device_index,
                channels=selection.requested_output_channels,
                samplerate=sample_rate,
                dtype=dtype,
            )
            item["check_output_settings"]["passed"] = True
        except Exception as exc:
            item["check_output_settings"]["exception"] = repr(exc)
            results.append(item)
            continue
        if open_stream:
            frames_seen = 0

            def callback(indata, outdata, frames, callback_time, status):  # noqa: ARG001
                nonlocal frames_seen
                outdata.fill(0)
                frames_seen += frames
                if frames_seen >= int(round(duration_s * sample_rate)):
                    raise sd.CallbackStop()

            try:
                with sd.Stream(
                    device=(selection.input_device_index, selection.output_device_index),
                    samplerate=sample_rate,
                    blocksize=block_size,
                    dtype=dtype,
                    channels=(selection.requested_input_channels, selection.requested_output_channels),
                    callback=callback,
                ):
                    sd.sleep(int((duration_s + 0.5) * 1000))
                item["full_duplex_open"]["passed"] = True
            except Exception as exc:
                item["full_duplex_open"]["exception"] = repr(exc)
                results.append(item)
                continue
        item["passed"] = bool(
            item["check_input_settings"]["passed"]
            and item["check_output_settings"]["passed"]
            and (not open_stream or item["full_duplex_open"]["passed"])
        )
        results.append(item)
        if item["passed"] and selected is None:
            selected = dtype
    return {
        "selection": asdict(selection),
        "sample_rate_hz": sample_rate,
        "block_size_frames": block_size,
        "candidates": results,
        "selected_stream_dtype": selected,
        "storage_dtype": _storage_dtype(config),
    }


def select_audio_device_pair(config: dict) -> AudioDevicePair:
    sd = _require_sounddevice()
    return select_audio_device_pair_from_query(
        config,
        hostapis=sd.query_hostapis(),
        devices=sd.query_devices(),
    )


def select_audio_device_pair_from_query(
    config: dict,
    hostapis: list[dict],
    devices: list[dict],
) -> AudioDevicePair:
    audio = config["audio_device"]
    input_override = audio.get("input_device_index_override")
    output_override = audio.get("output_device_index_override")
    if input_override is not None or output_override is not None:
        if input_override is None or output_override is None:
            raise RuntimeError(
                "input_device_index_override and output_device_index_override "
                "must be provided together"
            )
        return _pair_from_indices(config, hostapis, devices, int(input_override), int(output_override))

    candidates = find_audio_device_pairs(config, hostapis, devices)
    accepted = [candidate for candidate in candidates if candidate.supports_requested_settings]
    if not accepted:
        reasons = sorted({candidate.rejection_reason for candidate in candidates if candidate.rejection_reason})
        raise RuntimeError("No audio device pair matches Experiment 2 config: " + "; ".join(reasons))
    selected = accepted[0]
    return AudioDevicePair(
        input_device_index=int(selected.input_device_index),
        input_device_name=str(selected.input_device_name),
        output_device_index=int(selected.output_device_index),
        output_device_name=str(selected.output_device_name),
        host_api_index=int(selected.host_api_index),
        host_api_name=str(selected.host_api_name),
        max_input_channels=selected.max_input_channels,
        max_output_channels=selected.max_output_channels,
        requested_input_channels=selected.requested_input_channels,
        requested_output_channels=selected.requested_output_channels,
    )


def find_audio_device_pairs(
    config: dict,
    hostapis: list[dict],
    devices: list[dict],
) -> list[CandidatePair]:
    audio = config["audio_device"]
    preferred_api = str(audio.get("preferred_host_api", "")).lower()
    input_name = str(
        audio.get("input_device_name_contains", audio.get("device_name_contains", ""))
    ).lower()
    output_name = str(
        audio.get("output_device_name_contains", audio.get("device_name_contains", ""))
    ).lower()
    required_inputs = int(audio.get("open_input_channel_count", 0))
    required_outputs = int(audio.get("open_output_channel_count", 0))

    input_candidates: list[tuple[int, dict]] = []
    output_candidates: list[tuple[int, dict]] = []
    pairs: list[CandidatePair] = []

    for index, device in enumerate(devices):
        api_name = str(hostapis[int(device["hostapi"])]["name"])
        if preferred_api and preferred_api not in api_name.lower():
            continue
        device_name = str(device["name"]).lower()
        input_name_matches = not input_name or input_name in device_name
        output_name_matches = not output_name or output_name in device_name
        if input_name_matches:
            if int(device["max_input_channels"]) > 0:
                input_candidates.append((index, device))
            else:
                pairs.append(
                    _rejected_candidate(
                        config,
                        hostapis,
                        input_index=index,
                        input_device=device,
                        reason="insufficient input channels",
                    )
                )
        if output_name_matches:
            if int(device["max_output_channels"]) > 0:
                output_candidates.append((index, device))
            else:
                pairs.append(
                    _rejected_candidate(
                        config,
                        hostapis,
                        output_index=index,
                        output_device=device,
                        reason="insufficient output channels",
                    )
                )

    if not input_candidates:
        pairs.append(_rejected_candidate(config, hostapis, reason="input device not found"))
    if not output_candidates:
        pairs.append(_rejected_candidate(config, hostapis, reason="output device not found"))

    for input_index, input_device in input_candidates:
        for output_index, output_device in output_candidates:
            pairs.append(
                _candidate_pair(
                    config,
                    hostapis,
                    input_index,
                    input_device,
                    output_index,
                    output_device,
                )
            )
    return sorted(
        pairs,
        key=lambda pair: (
            pair.rejection_reason is not None,
            pair.host_api_name or "",
            pair.input_device_name or "",
            pair.output_device_name or "",
        ),
    )


def _candidate_pair(
    config: dict,
    hostapis: list[dict],
    input_index: int,
    input_device: dict,
    output_index: int,
    output_device: dict,
) -> CandidatePair:
    audio = config["audio_device"]
    required_inputs = int(audio.get("open_input_channel_count", 0))
    required_outputs = int(audio.get("open_output_channel_count", 0))
    input_hostapi = int(input_device["hostapi"])
    output_hostapi = int(output_device["hostapi"])
    max_inputs = int(input_device["max_input_channels"])
    max_outputs = int(output_device["max_output_channels"])
    rejection_reason = None
    if input_hostapi != output_hostapi:
        rejection_reason = "host API mismatch"
    elif max_inputs < required_inputs:
        rejection_reason = "insufficient input channels"
    elif max_outputs < required_outputs:
        rejection_reason = "insufficient output channels"
    return CandidatePair(
        input_device_index=input_index,
        input_device_name=str(input_device["name"]),
        output_device_index=output_index,
        output_device_name=str(output_device["name"]),
        host_api_index=input_hostapi if input_hostapi == output_hostapi else None,
        host_api_name=str(hostapis[input_hostapi]["name"]) if input_hostapi == output_hostapi else None,
        max_input_channels=max_inputs,
        max_output_channels=max_outputs,
        requested_input_channels=required_inputs,
        requested_output_channels=required_outputs,
        supports_requested_settings=rejection_reason is None,
        rejection_reason=rejection_reason,
    )


def _rejected_candidate(
    config: dict,
    hostapis: list[dict],
    input_index: int | None = None,
    input_device: dict | None = None,
    output_index: int | None = None,
    output_device: dict | None = None,
    reason: str = "device not found",
) -> CandidatePair:
    audio = config["audio_device"]
    input_hostapi = int(input_device["hostapi"]) if input_device else None
    output_hostapi = int(output_device["hostapi"]) if output_device else None
    if input_hostapi is not None and output_hostapi is not None and input_hostapi == output_hostapi:
        host_api_index = input_hostapi
    elif input_hostapi is not None:
        host_api_index = input_hostapi
    else:
        host_api_index = output_hostapi
    return CandidatePair(
        input_device_index=input_index,
        input_device_name=str(input_device["name"]) if input_device else None,
        output_device_index=output_index,
        output_device_name=str(output_device["name"]) if output_device else None,
        host_api_index=host_api_index,
        host_api_name=str(hostapis[host_api_index]["name"]) if host_api_index is not None else None,
        max_input_channels=int(input_device["max_input_channels"]) if input_device else 0,
        max_output_channels=int(output_device["max_output_channels"]) if output_device else 0,
        requested_input_channels=int(audio.get("open_input_channel_count", 0)),
        requested_output_channels=int(audio.get("open_output_channel_count", 0)),
        supports_requested_settings=False,
        rejection_reason=reason,
    )


def _pair_from_indices(
    config: dict,
    hostapis: list[dict],
    devices: list[dict],
    input_index: int,
    output_index: int,
) -> AudioDevicePair:
    if input_index < 0 or input_index >= len(devices):
        raise RuntimeError("input device not found")
    if output_index < 0 or output_index >= len(devices):
        raise RuntimeError("output device not found")
    candidate = _candidate_pair(
        config,
        hostapis,
        input_index,
        devices[input_index],
        output_index,
        devices[output_index],
    )
    if candidate.rejection_reason:
        raise RuntimeError(candidate.rejection_reason)
    return AudioDevicePair(
        input_device_index=input_index,
        input_device_name=str(devices[input_index]["name"]),
        output_device_index=output_index,
        output_device_name=str(devices[output_index]["name"]),
        host_api_index=int(candidate.host_api_index),
        host_api_name=str(candidate.host_api_name),
        max_input_channels=candidate.max_input_channels,
        max_output_channels=candidate.max_output_channels,
        requested_input_channels=candidate.requested_input_channels,
        requested_output_channels=candidate.requested_output_channels,
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
        selection: AudioDevicePair | None = None
        stream_dtype = "simulated_float32"
    else:
        selection = select_audio_device_pair(config)
        stream_dtype = _select_stream_dtype_for_capture(config)
        _capture_full_duplex(
            config=config,
            playback=playback,
            raw=raw,
            timeline=timeline,
            selection=selection,
            stream_dtype=stream_dtype,
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
        stream_dtype=stream_dtype,
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
    selection: AudioDevicePair,
    stream_dtype: str,
) -> None:
    sd = _require_sounddevice()
    audio = config["audio_device"]
    channels = audio["channel_selection"]
    sample_rate = int(audio["sample_rate_hz"])
    block_size = int(audio["block_size_frames"])
    dtype = stream_dtype
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
                _copy_float_playback_to_stream_out(outdata[:valid, :], playback[start:stop, :])
                raw[start:stop, 0] = _stream_input_to_float32(indata[:valid, mic_l])
                raw[start:stop, 1] = _stream_input_to_float32(indata[:valid, mic_r])
                raw[start:stop, 2] = _stream_input_to_float32(indata[:valid, ref])
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
            if isinstance(exc, sd.CallbackStop):
                raise
            error.append(exc)
            done.set()
            raise

    with sd.Stream(
        device=(selection.input_device_index, selection.output_device_index),
        samplerate=sample_rate,
        blocksize=block_size,
        dtype=dtype,
        channels=(selection.requested_input_channels, selection.requested_output_channels),
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
    selection: AudioDevicePair | None,
    simulate: bool,
    stream_dtype: str,
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
        "stream_dtype": stream_dtype,
        "storage_dtype": _storage_dtype(config),
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


def _select_stream_dtype_for_capture(config: dict) -> str:
    audio = config["audio_device"]
    configured = str(audio.get("stream_dtype", audio.get("dtype", "float32")))
    if configured.lower() != "auto":
        return configured
    probe = probe_audio_formats(config, duration_s=0.02, open_stream=False)
    selected = probe.get("selected_stream_dtype")
    if not selected:
        raise RuntimeError("no supported stream dtype found")
    return str(selected)


def _stream_dtype_candidates(config: dict) -> list[str]:
    audio = config["audio_device"]
    configured = str(audio.get("stream_dtype", audio.get("dtype", "float32")))
    if configured.lower() != "auto":
        return [configured]
    candidates = audio.get("stream_dtype_candidates", DEFAULT_STREAM_DTYPE_CANDIDATES)
    return [str(candidate) for candidate in candidates]


def _storage_dtype(config: dict) -> str:
    return str(config["audio_device"].get("storage_dtype", "float32"))


def _copy_float_playback_to_stream_out(outdata: np.ndarray, playback: np.ndarray) -> None:
    if np.issubdtype(outdata.dtype, np.floating):
        outdata[:, :] = playback
        return
    if np.issubdtype(outdata.dtype, np.signedinteger):
        info = np.iinfo(outdata.dtype)
        scaled = np.clip(playback, -1.0, 1.0) * float(info.max)
        outdata[:, :] = scaled.astype(outdata.dtype)
        return
    if np.issubdtype(outdata.dtype, np.unsignedinteger):
        info = np.iinfo(outdata.dtype)
        midpoint = (float(info.max) + 1.0) / 2.0
        scaled = np.clip(playback, -1.0, 1.0) * (midpoint - 1.0) + midpoint
        outdata[:, :] = np.clip(scaled, info.min, info.max).astype(outdata.dtype)
        return
    raise TypeError(f"unsupported PortAudio output dtype: {outdata.dtype}")


def _stream_input_to_float32(indata: np.ndarray) -> np.ndarray:
    if np.issubdtype(indata.dtype, np.floating):
        return indata.astype(np.float32, copy=False)
    if np.issubdtype(indata.dtype, np.signedinteger):
        info = np.iinfo(indata.dtype)
        return (indata.astype(np.float32) / float(info.max)).astype(np.float32)
    if np.issubdtype(indata.dtype, np.unsignedinteger):
        info = np.iinfo(indata.dtype)
        midpoint = (float(info.max) + 1.0) / 2.0
        return ((indata.astype(np.float32) - midpoint) / midpoint).astype(np.float32)
    raise TypeError(f"unsupported PortAudio input dtype: {indata.dtype}")


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


def _device_direction(device: dict) -> str:
    has_input = int(device["max_input_channels"]) > 0
    has_output = int(device["max_output_channels"]) > 0
    if has_input and has_output:
        return "full-duplex"
    if has_input:
        return "input-only"
    if has_output:
        return "output-only"
    return "no-audio"


def _default_audio_listing_config() -> dict:
    return {
        "audio_device": {
            "preferred_host_api": "Windows WDM-KS",
            "input_device_name_contains": "Analogue 1 + 2",
            "output_device_name_contains": "Speakers",
            "open_input_channel_count": 4,
            "open_output_channel_count": 4,
        }
    }


def _callback_status_flags(status: object) -> int:
    try:
        return int(status)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        flags = getattr(status, "_flags", None)
        if flags is not None:
            return int(flags)
        return 1 if bool(status) else 0
