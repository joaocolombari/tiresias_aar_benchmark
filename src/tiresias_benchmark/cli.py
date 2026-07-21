from __future__ import annotations

import argparse
import asyncio
import csv
from importlib import import_module
import json
from pathlib import Path
import sys

from tiresias_benchmark.acoustics.sweep import exponential_sine_sweep, sweep_with_silence
from tiresias_benchmark.attention.gaussian import Source
from tiresias_benchmark.telemetry.ble_client import BleRecordConfig, record_ble_telemetry
from tiresias_benchmark.telemetry.replay import delayed_yaw_series, read_telemetry_csv, records_to_time_yaw


def load_yaml(path: str | Path) -> dict:
    text = Path(path).read_text()
    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ImportError:
        return _load_simple_yaml(text)


def _parse_scalar(text: str):
    text = text.strip()
    if text == "":
        return ""
    if text.lower() in {"inf", ".inf", "infinity"}:
        return float("inf")
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    if text.lower() in {"null", "none", "~"}:
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    try:
        if any(ch in text for ch in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        return text.strip("\"'")


def _load_simple_yaml(text: str) -> dict:
    parsed_lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        parsed_lines.append((indent, raw.strip()))

    def parse_block(index: int, indent: int):
        if index >= len(parsed_lines):
            return {}, index
        if parsed_lines[index][1].startswith("- "):
            items = []
            while index < len(parsed_lines) and parsed_lines[index][0] == indent:
                item_text = parsed_lines[index][1][2:].strip()
                if ":" in item_text:
                    key, _, value = item_text.partition(":")
                    item = {key.strip(): _parse_scalar(value.strip())}
                    index += 1
                    while index < len(parsed_lines) and parsed_lines[index][0] > indent:
                        sub_indent, sub_text = parsed_lines[index]
                        sub_key, _, sub_value = sub_text.partition(":")
                        if sub_value.strip():
                            item[sub_key.strip()] = _parse_scalar(sub_value.strip())
                            index += 1
                        else:
                            child, index = parse_block(index + 1, sub_indent + 2)
                            item[sub_key.strip()] = child
                    items.append(item)
                else:
                    items.append(_parse_scalar(item_text))
                    index += 1
            return items, index

        mapping = {}
        while index < len(parsed_lines) and parsed_lines[index][0] == indent:
            _, line = parsed_lines[index]
            key, _, value = line.partition(":")
            if value.strip():
                mapping[key.strip()] = _parse_scalar(value.strip())
                index += 1
            else:
                child, index = parse_block(index + 1, indent + 2)
                mapping[key.strip()] = child
        return mapping, index

    data, _ = parse_block(0, 0)
    return data


def cmd_telemetry_record(args: argparse.Namespace) -> None:
    config = load_yaml(args.config) if args.config else {}
    sources = [
        Source(item["name"], float(item["azimuth_deg"]), float(item.get("distance_m", 1.0)))
        for item in config.get("sources", [{"name": "A", "azimuth_deg": -45}, {"name": "B", "azimuth_deg": 45}])
    ]
    record_config = BleRecordConfig(
        device_name=config.get("device_name", "Tiresias_DK"),
        sigma_deg=float(config.get("sigma_deg", 20.0)),
        bmax_db=float(config.get("bmax_db", 10.0)),
        reference_distance_m=float(config.get("reference_distance_m", 1.0)),
        scan_timeout_s=float(config.get("scan_timeout_s", 10.0)),
        duration_s=args.duration_s,
    )
    path = asyncio.run(record_ble_telemetry(args.output, record_config, sources))
    print(path)


def cmd_telemetry_replay(args: argparse.Namespace) -> None:
    records = read_telemetry_csv(args.input)
    t, yaw = records_to_time_yaw(records)
    delayed = delayed_yaw_series(t, yaw, args.delay_ms)
    if args.output:
        with args.output.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["time_s", "calibrated_yaw_deg", "delayed_yaw_deg"])
            writer.writerows(zip(t, yaw, delayed))
    else:
        writer = csv.writer(sys.stdout)
        writer.writerow(["time_s", "calibrated_yaw_deg", "delayed_yaw_deg"])
        writer.writerows(zip(t, yaw, delayed))


def cmd_sweep_generate(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    fs = int(config.get("sample_rate_hz", 48_000))
    sweep = exponential_sine_sweep(
        duration_s=float(config.get("sweep_duration_s", 5.0)),
        sample_rate_hz=fs,
        start_hz=float(config.get("sweep_start_hz", 20.0)),
        stop_hz=float(config.get("sweep_stop_hz", 20_000.0)),
        amplitude=float(config.get("sweep_amplitude", 0.5)),
    )
    signal = sweep_with_silence(
        sweep,
        fs,
        pre_silence_s=float(config.get("pre_silence_s", 1.0)),
        post_silence_s=float(config.get("post_silence_s", 2.0)),
    )
    try:
        import soundfile as sf

        sf.write(args.output, signal, fs)
    except ImportError:
        try:
            from scipy.io import wavfile

            wavfile.write(args.output, fs, signal)
        except ImportError:
            import wave
            import numpy as np

            pcm16 = (np.clip(signal, -1.0, 1.0) * 32767.0).astype("<i2")
            with wave.open(str(args.output), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(fs)
                wav.writeframes(pcm16.tobytes())
    print(args.output)


def cmd_brir_process(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    if args.session_id:
        config["process_session_id"] = args.session_id
    if args.overwrite:
        config["overwrite_processing"] = True
    experiment_02 = import_module("tiresias_benchmark.experiments.experiment_02")
    try:
        result = experiment_02.run(config)
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))


def cmd_brir_validate(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    config["validate_session_id"] = args.session_id
    config["validation_mode"] = args.mode
    config["write_validation_wavs"] = args.write_wavs
    if args.overwrite:
        config["overwrite_validation"] = True
    experiment_02 = import_module("tiresias_benchmark.experiments.experiment_02")
    try:
        result = experiment_02.run(config)
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))


def cmd_experiment_run(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    if args.telemetry_csv:
        config["telemetry_csv"] = str(args.telemetry_csv)
    runners = {
        "1": "tiresias_benchmark.experiments.experiment_01",
        "2": "tiresias_benchmark.experiments.experiment_02",
        "3": "tiresias_benchmark.experiments.experiment_03",
        "4": "tiresias_benchmark.experiments.experiment_04",
        "5": "tiresias_benchmark.experiments.experiment_05",
        "6": "tiresias_benchmark.experiments.experiment_06",
    }
    result = import_module(runners[str(args.experiment)]).run(config)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.output).open("w") as file:
            json.dump(result, file, indent=2)
    print(json.dumps(result, indent=2))


def cmd_exp01_drift_correct(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    if args.input:
        input_csv = Path(args.input)
    else:
        input_csv = Path(config["telemetry_csv"])
    output_csv = Path(args.output_csv or "experiments/exp01_orientation_characterization/processed/segmented_orientation_drift_corrected.csv")
    output_json = Path(args.output_json or "experiments/exp01_orientation_characterization/metrics/exp01_drift_corrected_metrics.json")
    experiment_01 = import_module("tiresias_benchmark.experiments.experiment_01")
    result = experiment_01.write_drift_corrected_csv(
        input_csv=input_csv,
        output_csv=output_csv,
        config=config,
        sign_mode=args.sign,
        overwrite=args.overwrite,
    )
    output_json.parent.mkdir(parents=True, exist_ok=True)
    if output_json.exists() and not args.overwrite:
        raise FileExistsError(f"refusing to overwrite existing file: {output_json}")
    with output_json.open("w") as file:
        json.dump(result, file, indent=2)
    print(json.dumps({"corrected_csv": str(output_csv), "metrics_json": str(output_json), **result}, indent=2))


def cmd_exp01_guided_acquire(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    guided = import_module("tiresias_benchmark.experiments.experiment_01_guided")
    default_outputs = guided.default_guided_outputs(config, args.run)
    outputs = guided.GuidedOutputs(
        raw_csv=Path(args.raw_output) if args.raw_output else default_outputs.raw_csv,
        segmented_csv=Path(args.segmented_output)
        if args.segmented_output
        else default_outputs.segmented_csv,
        drift_before_csv=Path(args.drift_before_output)
        if args.drift_before_output
        else default_outputs.drift_before_csv,
        drift_after_csv=Path(args.drift_after_output)
        if args.drift_after_output
        else default_outputs.drift_after_csv,
    )
    asyncio.run(
        guided.run_guided_experiment_01(
            config,
            run_name=args.run,
            outputs=outputs,
            device_name=args.device_name,
            include_drift=not args.no_drift,
            measure_drift_before=False if args.no_drift else args.drift_before,
            measure_drift_after=False if args.no_drift else args.drift_after,
        )
    )


def cmd_figures_generate(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    try:
        if args.experiment == "1":
            figure_module = import_module("tiresias_benchmark.experiments.experiment_01_figures")
            if args.review:
                outputs = figure_module.generate_experiment_01_review_figures(
                    config,
                    input_csvs=[Path(item) for item in args.input] if args.input else None,
                    processed_dir=Path(args.processed_dir) if args.processed_dir else None,
                    raw_dir=Path(args.raw_dir) if args.raw_dir else None,
                    output_dir=Path(args.output_dir) if args.output_dir else None,
                    require_all_runs=not args.allow_missing_runs,
                    sign_mode=args.sign,
                    overwrite=args.overwrite,
                )
            else:
                outputs = figure_module.generate_experiment_01_figures(
                    config,
                    input_csvs=[Path(item) for item in args.input] if args.input else None,
                    processed_dir=Path(args.processed_dir) if args.processed_dir else None,
                    raw_dir=Path(args.raw_dir) if args.raw_dir else None,
                    output_dir=Path(args.output_dir) if args.output_dir else None,
                    metrics_dir=Path(args.metrics_dir) if args.metrics_dir else None,
                    require_all_runs=not args.allow_missing_runs,
                    sign_mode=args.sign,
                    overwrite=args.overwrite,
                )
        else:
            figure_module = import_module("tiresias_benchmark.experiments.experiment_02_figures")
            if args.review:
                outputs = figure_module.generate_experiment_02_review_validation_figure(
                    config,
                    session_id=args.session_id,
                    output_dir=Path(args.output_dir) if args.output_dir else None,
                    metrics_dir=Path(args.metrics_dir) if args.metrics_dir else None,
                    overwrite=args.overwrite,
                )
            else:
                outputs = figure_module.generate_experiment_02_validation_report(
                    config,
                    session_id=args.session_id,
                    output_dir=Path(args.output_dir) if args.output_dir else None,
                    metrics_dir=Path(args.metrics_dir) if args.metrics_dir else None,
                    overwrite=args.overwrite,
                )
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({key: str(value) for key, value in outputs.__dict__.items()}, indent=2))


def cmd_exp02_audio_list_devices(args: argparse.Namespace) -> None:
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    config = load_yaml(args.config) if args.config else None
    try:
        result = audio.list_audio_devices(config)
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, indent=2))


def cmd_exp02_audio_preflight(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    try:
        result = audio.preflight_audio(
            config,
            duration_s=args.duration_s,
            open_stream=not args.no_open_stream,
        )
    except getattr(audio, "AudioPreflightError") as exc:
        _write_optional_json(args.output, exc.report)
        raise SystemExit(str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    _write_optional_json(args.output, result)
    print(json.dumps(result, indent=2))


def cmd_exp02_audio_format_probe(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    try:
        result = audio.probe_audio_formats(
            config,
            duration_s=args.duration_s,
            open_stream=not args.no_open_stream,
        )
    except (RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    _write_optional_json(args.output, result)
    print(json.dumps(result, indent=2))


def cmd_exp02_channel_probe(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    try:
        result = audio.record_probe(
            config=config,
            speaker=args.speaker,
            session_id=args.session_id,
            output_root=args.output_root,
            attempt=args.attempt,
            armed=args.armed,
            simulate=args.simulate,
            overwrite=args.overwrite,
        )
    except (FileExistsError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result.as_dict(), indent=2))


def cmd_exp02_output_probe(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    try:
        result = audio.record_output_channel_probe(
            config=config,
            output_index=args.output_index,
            session_id=args.session_id,
            output_root=args.output_root,
            attempt=args.attempt,
            armed=args.armed,
            simulate=args.simulate,
            overwrite=args.overwrite,
        )
    except (FileExistsError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result.as_dict(), indent=2))


def cmd_exp02_record_test_sweep(args: argparse.Namespace) -> None:
    config = load_yaml(args.config)
    audio = import_module("tiresias_benchmark.experiments.experiment_02_audio")
    try:
        result = audio.record_test_sweep(
            config=config,
            speaker=args.speaker,
            angle_deg=args.angle,
            repetition=args.repetition,
            session_id=args.session_id,
            output_root=args.output_root,
            attempt=args.attempt,
            armed=args.armed,
            simulate=args.simulate,
            overwrite=args.overwrite,
        )
    except (FileExistsError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result.as_dict(), indent=2))


def _write_optional_json(path: str | Path | None, data: dict) -> None:
    if not path:
        return
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as file:
        json.dump(data, file, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tiresias-benchmark")
    sub = parser.add_subparsers(required=True)

    p = sub.add_parser("telemetry-record")
    p.add_argument("--config")
    p.add_argument("--output", required=True)
    p.add_argument("--duration-s", type=float)
    p.set_defaults(func=cmd_telemetry_record)

    p = sub.add_parser("telemetry-replay")
    p.add_argument("--input", required=True)
    p.add_argument("--output", type=Path)
    p.add_argument("--delay-ms", type=float, default=0.0)
    p.set_defaults(func=cmd_telemetry_replay)

    p = sub.add_parser("sweep-generate")
    p.add_argument("--config", required=True)
    p.add_argument("--output", required=True)
    p.set_defaults(func=cmd_sweep_generate)

    p = sub.add_parser("brir-process")
    p.add_argument("--config", required=True)
    p.add_argument("--session-id")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_brir_process)

    p = sub.add_parser("brir-validate")
    p.add_argument("--config", required=True)
    p.add_argument("--session-id", required=True)
    p.add_argument("--mode", choices=["same", "cross", "both"], default="both")
    p.add_argument("--write-wavs", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_brir_validate)

    p = sub.add_parser("experiment-run")
    p.add_argument("--experiment", required=True, choices=["1", "2", "3", "4", "5", "6"])
    p.add_argument("--config", required=True)
    p.add_argument("--telemetry-csv")
    p.add_argument("--output")
    p.set_defaults(func=cmd_experiment_run)

    p = sub.add_parser("exp01-drift-correct")
    p.add_argument("--config", required=True)
    p.add_argument("--input")
    p.add_argument("--output-csv")
    p.add_argument("--output-json")
    p.add_argument("--sign", choices=["auto", "normal", "inverted"], default="auto")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_exp01_drift_correct)

    p = sub.add_parser("exp01-guided-acquire")
    p.add_argument("--config", required=True)
    p.add_argument("--run", choices=["all", "ascending", "descending", "randomized"], default="all")
    p.add_argument("--device-name")
    p.add_argument("--raw-output")
    p.add_argument("--segmented-output")
    p.add_argument("--drift-before-output")
    p.add_argument("--drift-after-output")
    p.add_argument("--drift-before", action="store_true", default=None)
    p.add_argument("--drift-after", action="store_true", default=None)
    p.add_argument("--no-drift", action="store_true")
    p.set_defaults(func=cmd_exp01_guided_acquire)

    p = sub.add_parser("figures-generate")
    p.add_argument("--experiment", choices=["1", "2"], default="1")
    p.add_argument("--config", required=True)
    p.add_argument("--input", action="append", help="Segmented Experiment 1 CSV. Repeat for multiple runs.")
    p.add_argument("--processed-dir")
    p.add_argument("--raw-dir")
    p.add_argument("--output-dir")
    p.add_argument("--metrics-dir")
    p.add_argument("--session-id", help="Experiment 2 session id for BRIR validation figures.")
    p.add_argument("--sign", choices=["auto", "normal", "inverted"], default="auto")
    p.add_argument("--allow-missing-runs", action="store_true")
    p.add_argument("--review", action="store_true", help="Write Experiment 1 review figures with separate filenames.")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_figures_generate)

    p = sub.add_parser("exp02-audio-list-devices")
    p.add_argument("--config", default="experiments/exp02_brir_measurement/config.yaml")
    p.set_defaults(func=cmd_exp02_audio_list_devices)

    p = sub.add_parser("exp02-audio-preflight")
    p.add_argument("--config", required=True)
    p.add_argument("--duration-s", type=float, default=0.25)
    p.add_argument("--no-open-stream", action="store_true")
    p.add_argument("--output")
    p.set_defaults(func=cmd_exp02_audio_preflight)

    p = sub.add_parser("exp02-audio-format-probe")
    p.add_argument("--config", required=True)
    p.add_argument("--duration-s", type=float, default=0.05)
    p.add_argument("--no-open-stream", action="store_true")
    p.add_argument("--output")
    p.set_defaults(func=cmd_exp02_audio_format_probe)

    p = sub.add_parser("exp02-channel-probe")
    p.add_argument("--config", required=True)
    p.add_argument("--speaker", required=True, choices=["A", "B"])
    p.add_argument("--session-id", default="exp02_probe")
    p.add_argument("--output-root")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--armed", action="store_true")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_exp02_channel_probe)

    p = sub.add_parser("exp02-output-probe")
    p.add_argument("--config", required=True)
    p.add_argument("--output-index", type=int, required=True)
    p.add_argument("--session-id", default="exp02_output_probe")
    p.add_argument("--output-root")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--armed", action="store_true")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_exp02_output_probe)

    p = sub.add_parser("exp02-record-test-sweep")
    p.add_argument("--config", required=True)
    p.add_argument("--speaker", required=True, choices=["A", "B"])
    p.add_argument("--angle", type=int, default=0)
    p.add_argument("--repetition", type=int, choices=[1, 2], default=1)
    p.add_argument("--session-id", default="exp02_test")
    p.add_argument("--output-root")
    p.add_argument("--attempt", type=int, default=1)
    p.add_argument("--armed", action="store_true")
    p.add_argument("--simulate", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(func=cmd_exp02_record_test_sweep)
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
