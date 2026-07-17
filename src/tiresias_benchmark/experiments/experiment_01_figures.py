from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import mean, median, pstdev

import numpy as np

from tiresias_benchmark.experiments import experiment_01
from tiresias_benchmark.metrics.orientation import (
    angular_error_stats,
    circular_difference_deg,
    normalize_yaw_360_deg,
)


RUN_COLORS = {
    "ascending": "#1b9e77",
    "descending": "#d95f02",
    "randomized": "#7570b3",
}


@dataclass(frozen=True)
class FigureOutputs:
    orientation_summary_svg: Path
    drift_correction_svg: Path
    ble_timing_svg: Path
    position_summary_csv: Path
    ble_summary_csv: Path
    metrics_json: Path
    results_table_md: Path


def generate_experiment_01_figures(
    config: dict,
    *,
    input_csvs: list[Path] | None = None,
    processed_dir: Path | None = None,
    raw_dir: Path | None = None,
    output_dir: Path | None = None,
    metrics_dir: Path | None = None,
    require_all_runs: bool = True,
    sign_mode: str = "auto",
    overwrite: bool = False,
) -> FigureOutputs:
    base = Path("experiments/exp01_orientation_characterization")
    processed_dir = processed_dir or base / "processed"
    raw_dir = raw_dir or base / "raw"
    output_dir = output_dir or base / "figures"
    metrics_dir = metrics_dir or base / "metrics"
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)

    segmented_paths = input_csvs or _latest_segmented_paths(
        processed_dir,
        runs=list(config.get("runs", ["ascending", "descending", "randomized"])),
        require_all=require_all_runs,
    )
    if not segmented_paths:
        raise FileNotFoundError("no segmented Experiment 1 CSV files found")

    samples = _load_samples(segmented_paths, config)
    corrected_samples, group_models = _apply_groupwise_drift_correction(
        samples,
        sign_mode=sign_mode,
    )
    position_rows = _position_summary_rows(corrected_samples)
    ble_rows, ble_intervals = _ble_summary_rows(
        segmented_paths,
        raw_dir=raw_dir,
        config=config,
    )
    metrics = _combined_metrics(corrected_samples, group_models, ble_rows)

    outputs = FigureOutputs(
        orientation_summary_svg=output_dir / "exp01_orientation_summary.svg",
        drift_correction_svg=output_dir / "exp01_drift_correction.svg",
        ble_timing_svg=output_dir / "exp01_ble_timing.svg",
        position_summary_csv=metrics_dir / "exp01_position_summary.csv",
        ble_summary_csv=metrics_dir / "exp01_ble_summary.csv",
        metrics_json=metrics_dir / "exp01_combined_metrics.json",
        results_table_md=metrics_dir / "exp01_results_table.md",
    )
    _ensure_can_write(outputs, overwrite=overwrite)

    _write_position_summary_csv(outputs.position_summary_csv, position_rows)
    _write_ble_summary_csv(outputs.ble_summary_csv, ble_rows)
    outputs.metrics_json.write_text(json.dumps(metrics, indent=2) + "\n")
    outputs.results_table_md.write_text(_results_table_markdown(metrics, ble_rows) + "\n")
    outputs.orientation_summary_svg.write_text(_orientation_summary_svg(position_rows))
    outputs.drift_correction_svg.write_text(_drift_correction_svg(corrected_samples, group_models))
    outputs.ble_timing_svg.write_text(_ble_timing_svg(ble_intervals, ble_rows))
    return outputs


def _latest_segmented_paths(processed_dir: Path, *, runs: list[str], require_all: bool) -> list[Path]:
    paths = []
    missing = []
    for run in runs:
        matches = sorted(
            processed_dir.glob(f"segmented_{run}_*.csv"),
            key=lambda path: path.stat().st_mtime,
        )
        if matches:
            paths.append(matches[-1])
        else:
            missing.append(run)
    if missing and require_all:
        raise FileNotFoundError(
            "missing segmented CSV for run(s): "
            + ", ".join(missing)
            + f" in {processed_dir}"
        )
    return paths


def _load_samples(paths: list[Path], config: dict) -> list[dict]:
    samples = []
    for path in paths:
        with path.open() as file:
            for row in csv.DictReader(file):
                sample = experiment_01._sample_from_row(row, config)
                if sample is None:
                    continue
                sample["source_csv"] = str(path)
                sample["source_stem"] = path.stem
                sample["group_key"] = _correction_group_key(sample, path)
                sample["receive_interval_ms"] = _float_or_none(row.get("receive_interval_ms", ""))
                sample["packet_loss_count"] = _float_or_none(row.get("packet_loss_count", ""))
                samples.append(sample)
    if not samples:
        raise ValueError("no usable Experiment 1 samples found")
    return samples


def _correction_group_key(sample: dict, path: Path) -> str:
    return f"{sample['run_type']}::{path.name}"


def _apply_groupwise_drift_correction(samples: list[dict], *, sign_mode: str) -> tuple[list[dict], dict]:
    grouped = defaultdict(list)
    for sample in samples:
        grouped[sample["group_key"]].append(sample)

    models = {}
    corrected = []
    for key, rows in grouped.items():
        model = experiment_01._fit_posthoc_drift_model(rows, sign_mode=sign_mode)
        models[key] = model
        for sample in rows:
            item = dict(sample)
            signed = float(normalize_yaw_360_deg(model["sign"] * item["calibrated_yaw_deg"]))
            item["yaw_sign_corrected_deg"] = signed
            item["error_sign_corrected_deg"] = float(
                circular_difference_deg(signed, item["reference_angle_normalized_deg"])
            )
            if item["host_time_ns"] is not None:
                drift_model = experiment_01._drift_model_for_sample(item, model)
                corrected_yaw = float(normalize_yaw_360_deg(signed - drift_model))
                item["drift_model_deg"] = float(drift_model)
                item["yaw_drift_corrected_deg"] = corrected_yaw
                item["error_drift_corrected_deg"] = float(
                    circular_difference_deg(corrected_yaw, item["reference_angle_normalized_deg"])
                )
                item["elapsed_s"] = (item["host_time_ns"] - model["t0_ns"]) / 1_000_000_000.0
            else:
                item["drift_model_deg"] = None
                item["yaw_drift_corrected_deg"] = signed
                item["error_drift_corrected_deg"] = item["error_sign_corrected_deg"]
                item["elapsed_s"] = None
            corrected.append(item)
    return corrected, models


def _position_summary_rows(samples: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for sample in samples:
        key = (
            sample["run_type"],
            sample["source_stem"],
            sample["position_index"],
            sample["reference_angle_commanded_deg"],
            sample["reference_angle_normalized_deg"],
            sample["is_closure_measurement"],
        )
        grouped[key].append(sample)

    rows = []
    for key, values in grouped.items():
        run_type, source_stem, position_index, commanded, normalized, closure = key
        raw_errors = [v["error_sign_corrected_deg"] for v in values]
        corrected_errors = [v["error_drift_corrected_deg"] for v in values]
        signed_yaws = [v["yaw_sign_corrected_deg"] for v in values]
        corrected_yaws = [v["yaw_drift_corrected_deg"] for v in values]
        elapsed = [v["elapsed_s"] for v in values if v["elapsed_s"] is not None]
        rows.append(
            {
                "run_type": run_type,
                "source_stem": source_stem,
                "position_index": position_index,
                "reference_angle_commanded_deg": commanded,
                "reference_angle_normalized_deg": normalized,
                "is_closure_measurement": closure,
                "sample_count": len(values),
                "elapsed_mid_s": mean(elapsed) if elapsed else "",
                "yaw_sign_corrected_mean_deg": _angle_from_error_mean(normalized, raw_errors),
                "yaw_drift_corrected_mean_deg": _angle_from_error_mean(normalized, corrected_errors),
                "error_sign_corrected_mean_deg": mean(raw_errors),
                "error_sign_corrected_sd_deg": pstdev(raw_errors) if len(raw_errors) > 1 else 0.0,
                "error_drift_corrected_mean_deg": mean(corrected_errors),
                "error_drift_corrected_sd_deg": pstdev(corrected_errors)
                if len(corrected_errors) > 1
                else 0.0,
                "yaw_sign_corrected_sd_deg": pstdev(signed_yaws) if len(signed_yaws) > 1 else 0.0,
                "yaw_drift_corrected_sd_deg": pstdev(corrected_yaws)
                if len(corrected_yaws) > 1
                else 0.0,
            }
        )
    return sorted(rows, key=lambda row: (row["run_type"], row["position_index"]))


def _angle_from_error_mean(reference_deg: float, errors_deg: list[float]) -> float:
    return float(normalize_yaw_360_deg(reference_deg + mean(errors_deg)))


def _ble_summary_rows(
    segmented_paths: list[Path],
    *,
    raw_dir: Path,
    config: dict,
) -> tuple[list[dict], dict[str, list[float]]]:
    rows = []
    intervals_by_run = {}
    for segmented_path in segmented_paths:
        raw_path = _infer_raw_path(segmented_path, raw_dir)
        source_path = raw_path if raw_path.exists() else segmented_path
        telemetry_rows = _read_csv_rows(source_path)
        run_type = _run_type_from_path_or_rows(segmented_path, telemetry_rows)
        summary, intervals = _ble_summary_for_rows(telemetry_rows, source_path=source_path)
        summary["run_type"] = run_type
        summary["source_csv"] = str(source_path)
        summary["raw_file_found"] = raw_path.exists()
        rows.append(summary)
        intervals_by_run[run_type] = intervals
    return rows, intervals_by_run


def _infer_raw_path(segmented_path: Path, raw_dir: Path) -> Path:
    stem = segmented_path.stem
    if stem.startswith("segmented_"):
        return raw_dir / f"exp01_guided_{stem.removeprefix('segmented_')}.csv"
    return raw_dir / f"{stem}.csv"


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open() as file:
        return list(csv.DictReader(file))


def _run_type_from_path_or_rows(path: Path, rows: list[dict[str, str]]) -> str:
    for run in RUN_COLORS:
        if f"_{run}_" in path.name or path.name.startswith(f"segmented_{run}"):
            return run
    for row in rows:
        if row.get("run_type"):
            return row["run_type"]
    return path.stem


def _ble_summary_for_rows(rows: list[dict[str, str]], *, source_path: Path) -> tuple[dict, list[float]]:
    intervals = [
        float(row["receive_interval_ms"])
        for row in rows
        if row.get("receive_interval_ms") not in {"", None}
    ]
    intervals = [value for value in intervals if math.isfinite(value) and value >= 0]
    seq_values = [
        int(float(row["seq"]))
        for row in rows
        if row.get("seq") not in {"", None}
    ]
    seq_deltas = [b - a for a, b in zip(seq_values, seq_values[1:])]
    positive_deltas = [delta for delta in seq_deltas if delta > 0]
    seq_delta_mode = Counter(positive_deltas).most_common(1)[0][0] if positive_deltas else None
    unit_missing = sum(max(0, delta - 1) for delta in positive_deltas)
    unit_expected = sum(max(0, delta) for delta in positive_deltas)
    modal_missing = 0
    modal_expected = 0
    if seq_delta_mode:
        for delta in positive_deltas:
            modal_missing += max(0, round(delta / seq_delta_mode) - 1)
            modal_expected += max(0, round(delta / seq_delta_mode))

    interval_mean = mean(intervals) if intervals else None
    interval_median = median(intervals) if intervals else None
    jitter_abs = [abs(value - interval_median) for value in intervals] if interval_median is not None else []
    return (
        {
            "sample_count": len(rows),
            "interval_count": len(intervals),
            "effective_rate_hz": 1000.0 / interval_mean if interval_mean else None,
            "interval_mean_ms": interval_mean,
            "interval_median_ms": interval_median,
            "interval_p95_ms": _percentile(intervals, 95),
            "interval_p99_ms": _percentile(intervals, 99),
            "jitter_abs_from_median_p95_ms": _percentile(jitter_abs, 95),
            "jitter_abs_from_median_p99_ms": _percentile(jitter_abs, 99),
            "seq_count": len(seq_values),
            "seq_delta_mode": seq_delta_mode,
            "seq_delta_min": min(positive_deltas) if positive_deltas else None,
            "seq_delta_max": max(positive_deltas) if positive_deltas else None,
            "packet_loss_percent_assuming_unit_seq": (
                100.0 * unit_missing / unit_expected if unit_expected else None
            ),
            "packet_loss_percent_relative_to_modal_step": (
                100.0 * modal_missing / modal_expected if modal_expected else None
            ),
            "seq_semantics_note": (
                "packet loss relative to modal step is preferred when seq_delta_mode is not 1"
            ),
        },
        intervals,
    )


def _combined_metrics(samples: list[dict], models: dict, ble_rows: list[dict]) -> dict:
    global_rows = [sample for sample in samples if not sample["is_closure_measurement"]]
    reference = np.array([sample["reference_angle_normalized_deg"] for sample in global_rows])
    signed = np.array([sample["yaw_sign_corrected_deg"] for sample in global_rows])
    corrected = np.array([sample["yaw_drift_corrected_deg"] for sample in global_rows])
    signed_stats = angular_error_stats(reference, signed)
    corrected_stats = angular_error_stats(reference, corrected)
    closure = _corrected_closure_errors(samples)
    model_rows = [
        {
            "group_key": key,
            "sign_label": "normal" if model["sign"] > 0 else "inverted",
            "slope_deg_per_minute": model["slope_deg_per_s"] * 60.0,
            "intercept_deg": model["intercept_deg"],
            "fit_samples": model["fit_samples"],
            "fit_duration_s": model["fit_duration_s"],
        }
        for key, model in models.items()
    ]
    return {
        "input_groups": model_rows,
        "samples": {
            "global_samples_used": len(global_rows),
            "closure_samples_excluded": len(samples) - len(global_rows),
        },
        "sign_corrected": _stats_dict(signed_stats),
        "drift_corrected": _stats_dict(corrected_stats),
        "closure_errors_deg": closure,
        "ble": ble_rows,
    }


def _corrected_closure_errors(samples: list[dict]) -> dict[str, dict[str, float]]:
    grouped = defaultdict(list)
    for sample in samples:
        grouped[sample["group_key"]].append(sample)
    results = {}
    for key, rows in grouped.items():
        run_type = rows[0]["run_type"]
        rows = sorted(rows, key=lambda row: row["position_index"] or 0)
        if run_type == "ascending":
            start = _mean_corrected_yaw(rows, 0, closure=False)
            end = _mean_corrected_yaw(rows, 360, closure=True)
        elif run_type == "descending":
            start = _mean_corrected_yaw(rows, 360, closure=False)
            end = _mean_corrected_yaw(rows, 0, closure=True)
        elif run_type == "randomized":
            start = _mean_corrected_yaw(rows, 0, closure=False)
            end = _mean_corrected_yaw(rows, 360, closure=True)
        else:
            continue
        if start is not None and end is not None:
            results[run_type] = {
                "sign_corrected_deg": float(circular_difference_deg(
                    _mean_signed_yaw(rows, end_command(run_type), closure=True),
                    _mean_signed_yaw(rows, start_command(run_type), closure=False),
                )),
                "drift_corrected_deg": float(circular_difference_deg(end, start)),
                "group_key": key,
            }
    return results


def start_command(run_type: str) -> float:
    return 360.0 if run_type == "descending" else 0.0


def end_command(run_type: str) -> float:
    return 0.0 if run_type == "descending" else 360.0


def _mean_corrected_yaw(rows: list[dict], commanded: float, *, closure: bool) -> float | None:
    values = [
        row["yaw_drift_corrected_deg"]
        for row in rows
        if row["reference_angle_commanded_deg"] == commanded
        and row["is_closure_measurement"] is closure
    ]
    return _circular_mean(values)


def _mean_signed_yaw(rows: list[dict], commanded: float, *, closure: bool) -> float | None:
    values = [
        row["yaw_sign_corrected_deg"]
        for row in rows
        if row["reference_angle_commanded_deg"] == commanded
        and row["is_closure_measurement"] is closure
    ]
    return _circular_mean(values)


def _circular_mean(values: list[float]) -> float | None:
    if not values:
        return None
    radians = np.radians(values)
    return float(normalize_yaw_360_deg(np.degrees(np.arctan2(
        np.mean(np.sin(radians)),
        np.mean(np.cos(radians)),
    ))))


def _write_position_summary_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "run_type",
        "source_stem",
        "position_index",
        "reference_angle_commanded_deg",
        "reference_angle_normalized_deg",
        "is_closure_measurement",
        "sample_count",
        "elapsed_mid_s",
        "yaw_sign_corrected_mean_deg",
        "yaw_drift_corrected_mean_deg",
        "error_sign_corrected_mean_deg",
        "error_sign_corrected_sd_deg",
        "error_drift_corrected_mean_deg",
        "error_drift_corrected_sd_deg",
        "yaw_sign_corrected_sd_deg",
        "yaw_drift_corrected_sd_deg",
    ]
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_ble_summary_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = [
        "run_type",
        "source_csv",
        "raw_file_found",
        "sample_count",
        "interval_count",
        "effective_rate_hz",
        "interval_mean_ms",
        "interval_median_ms",
        "interval_p95_ms",
        "interval_p99_ms",
        "jitter_abs_from_median_p95_ms",
        "jitter_abs_from_median_p99_ms",
        "seq_count",
        "seq_delta_mode",
        "seq_delta_min",
        "seq_delta_max",
        "packet_loss_percent_assuming_unit_seq",
        "packet_loss_percent_relative_to_modal_step",
        "seq_semantics_note",
    ]
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _orientation_summary_svg(rows: list[dict]) -> str:
    width = 1200
    height = 760
    panel_h = 280
    margin_l = 86
    margin_r = 38
    top_y = 72
    bottom_y = 430
    plot_w = width - margin_l - margin_r
    title = "Experiment 1: orientation characterization"

    def x_angle(value: float) -> float:
        return margin_l + (value / 360.0) * plot_w

    def y_angle(value: float) -> float:
        return top_y + panel_h - (value / 360.0) * panel_h

    def y_error(value: float) -> float:
        return bottom_y + panel_h - ((value + 40.0) / 80.0) * panel_h

    parts = [_svg_header(width, height), f'<text x="{margin_l}" y="34" class="title">{escape(title)}</text>']
    parts += _axes(
        margin_l,
        top_y,
        plot_w,
        panel_h,
        x_label="physical platform angle (deg)",
        y_label="measured yaw (deg)",
        y_ticks=[0, 90, 180, 270, 360],
        y_map=y_angle,
        x_map=x_angle,
        x_ticks=[0, 60, 120, 180, 240, 300, 360],
    )
    parts += _axes(
        margin_l,
        bottom_y,
        plot_w,
        panel_h,
        x_label="physical platform angle (deg)",
        y_label="signed error (deg)",
        y_ticks=[-40, -20, 0, 20, 40],
        y_map=y_error,
        x_map=x_angle,
        x_ticks=[0, 60, 120, 180, 240, 300, 360],
    )
    parts.append(
        f'<line x1="{x_angle(0)}" y1="{y_angle(0)}" x2="{x_angle(360)}" '
        f'y2="{y_angle(360)}" class="ideal"/>'
    )
    parts.append(
        f'<line x1="{x_angle(0)}" y1="{y_error(0)}" x2="{x_angle(360)}" '
        f'y2="{y_error(0)}" class="zero"/>'
    )

    for run_type in sorted({row["run_type"] for row in rows}):
        color = RUN_COLORS.get(run_type, "#333333")
        run_rows = sorted(
            [row for row in rows if row["run_type"] == run_type],
            key=lambda row: row["position_index"],
        )
        for row in run_rows:
            x = x_angle(float(row["reference_angle_commanded_deg"]))
            corrected_y = y_angle(float(row["yaw_drift_corrected_mean_deg"]))
            signed_y = y_angle(float(row["yaw_sign_corrected_mean_deg"]))
            error_signed_y = y_error(float(row["error_sign_corrected_mean_deg"]))
            error_corrected_y = y_error(float(row["error_drift_corrected_mean_deg"]))
            opacity = "0.45" if row["is_closure_measurement"] else "0.82"
            parts.append(
                f'<circle cx="{x:.2f}" cy="{signed_y:.2f}" r="3.2" '
                f'fill="none" stroke="{color}" opacity="0.38"/>'
            )
            marker = "rect" if row["is_closure_measurement"] else "circle"
            if marker == "rect":
                parts.append(
                    f'<rect x="{x-4:.2f}" y="{corrected_y-4:.2f}" width="8" height="8" '
                    f'fill="{color}" opacity="{opacity}"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{x:.2f}" cy="{corrected_y:.2f}" r="4" '
                    f'fill="{color}" opacity="{opacity}"/>'
                )
            parts.append(
                f'<circle cx="{x:.2f}" cy="{error_signed_y:.2f}" r="2.4" '
                f'fill="none" stroke="{color}" opacity="0.38"/>'
            )
            parts.append(
                f'<circle cx="{x:.2f}" cy="{error_corrected_y:.2f}" r="3.6" '
                f'fill="{color}" opacity="{opacity}"/>'
            )

    parts.append(_legend(760, 92, [("ascending", RUN_COLORS["ascending"]), ("descending", RUN_COLORS["descending"]), ("randomized", RUN_COLORS["randomized"])]))
    parts.append('<text x="86" y="64" class="panel">A. Yaw angle after sign inversion and drift correction</text>')
    parts.append('<text x="86" y="422" class="panel">B. Signed circular error</text>')
    parts.append('<text x="760" y="178" class="note">open circles: sign-corrected only; filled markers: post-hoc drift-corrected; squares: closure measurements</text>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def _drift_correction_svg(samples: list[dict], models: dict) -> str:
    width = 1200
    run_types = sorted({sample["run_type"] for sample in samples})
    panel_h = 190
    gap = 54
    top = 72
    height = top + len(run_types) * panel_h + (len(run_types) - 1) * gap + 90
    margin_l = 86
    margin_r = 38
    plot_w = width - margin_l - margin_r
    parts = [_svg_header(width, height), '<text x="86" y="34" class="title">Experiment 1: yaw drift and post-hoc correction</text>']
    for idx, run_type in enumerate(run_types):
        y0 = top + idx * (panel_h + gap)
        run_samples = [sample for sample in samples if sample["run_type"] == run_type and not sample["is_closure_measurement"]]
        if not run_samples:
            continue
        max_t_min = max(sample["elapsed_s"] for sample in run_samples if sample["elapsed_s"] is not None) / 60.0
        max_t_min = max(max_t_min, 1.0)

        def x_time(value_s: float) -> float:
            return margin_l + ((value_s / 60.0) / max_t_min) * plot_w

        def y_err(value: float) -> float:
            return y0 + panel_h - ((value + 40.0) / 80.0) * panel_h

        parts += _axes(
            margin_l,
            y0,
            plot_w,
            panel_h,
            x_label="elapsed time in run (min)",
            y_label="error (deg)",
            y_ticks=[-40, -20, 0, 20, 40],
            y_map=y_err,
            x_map=lambda value: margin_l + (value / max_t_min) * plot_w,
            x_ticks=_nice_time_ticks(max_t_min),
        )
        parts.append(f'<text x="{margin_l}" y="{y0 - 14}" class="panel">{escape(run_type)}</text>')
        parts.append(
            f'<line x1="{margin_l}" y1="{y_err(0):.2f}" x2="{margin_l + plot_w}" '
            f'y2="{y_err(0):.2f}" class="zero"/>'
        )
        group_key = run_samples[0]["group_key"]
        model = models[group_key]
        x1, x2 = 0.0, max(sample["elapsed_s"] for sample in run_samples)
        y1 = model["intercept_deg"]
        y2 = model["intercept_deg"] + model["slope_deg_per_s"] * x2
        parts.append(
            f'<line x1="{x_time(x1):.2f}" y1="{y_err(y1):.2f}" '
            f'x2="{x_time(x2):.2f}" y2="{y_err(y2):.2f}" class="fit"/>'
        )
        step = max(1, len(run_samples) // 700)
        color = RUN_COLORS.get(run_type, "#333333")
        for sample in run_samples[::step]:
            x = x_time(sample["elapsed_s"])
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y_err(sample["error_sign_corrected_deg"]):.2f}" '
                f'r="1.8" fill="{color}" opacity="0.28"/>'
            )
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y_err(sample["error_drift_corrected_deg"]):.2f}" '
                f'r="1.8" fill="#111111" opacity="0.42"/>'
            )
        parts.append(
            f'<text x="{width - 360}" y="{y0 + 18}" class="note">'
            f'slope={model["slope_deg_per_s"] * 60.0:+.2f} deg/min, sign='
            f'{"normal" if model["sign"] > 0 else "inverted"}</text>'
        )
    parts.append('<text x="760" y="54" class="note">colored points: sign-corrected raw error; black points: corrected residual; red line: fitted linear drift</text>')
    parts.append("</svg>\n")
    return "\n".join(parts)


def _ble_timing_svg(intervals_by_run: dict[str, list[float]], ble_rows: list[dict]) -> str:
    width = 1200
    height = 460
    margin_l = 86
    margin_r = 38
    top = 72
    plot_h = 270
    plot_w = width - margin_l - margin_r
    all_intervals = [value for values in intervals_by_run.values() for value in values]
    max_x = max(80.0, _percentile(all_intervals, 99) or 80.0)

    def x_ms(value: float) -> float:
        return margin_l + (min(value, max_x) / max_x) * plot_w

    def y_count(value: float, max_count: float) -> float:
        return top + plot_h - (value / max_count) * plot_h

    bins = np.linspace(0, max_x, 42)
    histograms = {}
    max_count = 1
    for run_type, values in intervals_by_run.items():
        counts, _ = np.histogram(values, bins=bins)
        histograms[run_type] = counts
        max_count = max(max_count, int(np.max(counts)) if len(counts) else 1)

    parts = [_svg_header(width, height), '<text x="86" y="34" class="title">Experiment 1: BLE notification timing</text>']
    parts += _axes(
        margin_l,
        top,
        plot_w,
        plot_h,
        x_label="receive interval (ms)",
        y_label="count",
        y_ticks=[0, max_count / 2, max_count],
        y_map=lambda value: y_count(value, max_count),
        x_map=x_ms,
        x_ticks=[0, 20, 40, 60, 80],
    )
    bar_group_w = plot_w / (len(bins) - 1)
    run_order = sorted(histograms)
    for run_idx, run_type in enumerate(run_order):
        color = RUN_COLORS.get(run_type, "#333333")
        counts = histograms[run_type]
        bar_w = max(2.0, bar_group_w / max(1, len(run_order)) - 1)
        for i, count in enumerate(counts):
            x = x_ms(float(bins[i])) + run_idx * bar_w
            y = y_count(float(count), max_count)
            h = top + plot_h - y
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" '
                f'fill="{color}" opacity="0.56"/>'
            )
    parts.append(_legend(790, 80, [(run, RUN_COLORS.get(run, "#333333")) for run in run_order]))
    note_y = 372
    for row in ble_rows:
        parts.append(
            f'<text x="86" y="{note_y}" class="note">{escape(row["run_type"])}: '
            f'{_fmt(row["effective_rate_hz"])} Hz, interval P95={_fmt(row["interval_p95_ms"])} ms, '
            f'jitter P95={_fmt(row["jitter_abs_from_median_p95_ms"])} ms, '
            f'seq step mode={row["seq_delta_mode"]}, packet loss vs modal step='
            f'{_fmt(row["packet_loss_percent_relative_to_modal_step"])}%</text>'
        )
        note_y += 22
    parts.append("</svg>\n")
    return "\n".join(parts)


def _axes(
    x0: float,
    y0: float,
    width: float,
    height: float,
    *,
    x_label: str,
    y_label: str,
    x_ticks: list[float],
    y_ticks: list[float],
    x_map,
    y_map,
) -> list[str]:
    parts = [
        f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" class="plot-bg"/>',
        f'<line x1="{x0}" y1="{y0 + height}" x2="{x0 + width}" y2="{y0 + height}" class="axis"/>',
        f'<line x1="{x0}" y1="{y0}" x2="{x0}" y2="{y0 + height}" class="axis"/>',
    ]
    for tick in x_ticks:
        x = x_map(tick)
        parts.append(f'<line x1="{x:.2f}" y1="{y0}" x2="{x:.2f}" y2="{y0 + height}" class="grid"/>')
        parts.append(f'<text x="{x:.2f}" y="{y0 + height + 24}" class="tick" text-anchor="middle">{_fmt(tick)}</text>')
    for tick in y_ticks:
        y = y_map(tick)
        parts.append(f'<line x1="{x0}" y1="{y:.2f}" x2="{x0 + width}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{x0 - 12}" y="{y + 4:.2f}" class="tick" text-anchor="end">{_fmt(tick)}</text>')
    parts.append(f'<text x="{x0 + width / 2:.2f}" y="{y0 + height + 52}" class="label" text-anchor="middle">{escape(x_label)}</text>')
    parts.append(
        f'<text x="{x0 - 58}" y="{y0 + height / 2:.2f}" class="label" '
        f'text-anchor="middle" transform="rotate(-90 {x0 - 58} {y0 + height / 2:.2f})">{escape(y_label)}</text>'
    )
    return parts


def _legend(x: float, y: float, items: list[tuple[str, str]]) -> str:
    parts = [f'<g transform="translate({x},{y})">']
    for idx, (label, color) in enumerate(items):
        yy = idx * 24
        parts.append(f'<circle cx="0" cy="{yy}" r="5" fill="{color}"/>')
        parts.append(f'<text x="14" y="{yy + 5}" class="note">{escape(label)}</text>')
    parts.append("</g>")
    return "\n".join(parts)


def _svg_header(width: int, height: int) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
<style>
  text {{ font-family: Arial, Helvetica, sans-serif; fill: #202020; }}
  .title {{ font-size: 24px; font-weight: 700; }}
  .panel {{ font-size: 15px; font-weight: 700; }}
  .label {{ font-size: 13px; }}
  .tick {{ font-size: 11px; fill: #555; }}
  .note {{ font-size: 12px; fill: #444; }}
  .plot-bg {{ fill: #fbfbfb; stroke: #d7d7d7; }}
  .axis {{ stroke: #222; stroke-width: 1.1; }}
  .grid {{ stroke: #dedede; stroke-width: 0.8; }}
  .ideal {{ stroke: #111; stroke-width: 1.3; stroke-dasharray: 6 5; }}
  .zero {{ stroke: #111; stroke-width: 1.0; }}
  .fit {{ stroke: #c0392b; stroke-width: 2.0; }}
</style>'''


def _results_table_markdown(metrics: dict, ble_rows: list[dict]) -> str:
    signed = metrics["sign_corrected"]
    corrected = metrics["drift_corrected"]
    lines = [
        "# Experiment 1 Summary Tables",
        "",
        "## Orientation",
        "",
        "| Metric | Sign-corrected | Drift-corrected |",
        "|---|---:|---:|",
        f"| MAE (deg) | {_fmt(signed['mae_deg'])} | {_fmt(corrected['mae_deg'])} |",
        f"| RMSE (deg) | {_fmt(signed['rmse_deg'])} | {_fmt(corrected['rmse_deg'])} |",
        f"| Bias (deg) | {_fmt(signed['bias_deg'])} | {_fmt(corrected['bias_deg'])} |",
        f"| Max abs error (deg) | {_fmt(signed['max_abs_error_deg'])} | {_fmt(corrected['max_abs_error_deg'])} |",
        "",
        "## BLE Timing",
        "",
        "| Run | Rate (Hz) | Mean interval (ms) | Interval P95 (ms) | Jitter P95 (ms) | Seq step mode | Packet loss vs modal step (%) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in ble_rows:
        lines.append(
            f"| {row['run_type']} | {_fmt(row['effective_rate_hz'])} | "
            f"{_fmt(row['interval_mean_ms'])} | {_fmt(row['interval_p95_ms'])} | "
            f"{_fmt(row['jitter_abs_from_median_p95_ms'])} | {row['seq_delta_mode']} | "
            f"{_fmt(row['packet_loss_percent_relative_to_modal_step'])} |"
        )
    lines.extend(
        [
            "",
            "Packet loss is reported relative to the modal sequence-counter step. "
            "If the firmware sequence counter is expected to increment by one per notification, "
            "also inspect `packet_loss_percent_assuming_unit_seq` in `exp01_ble_summary.csv`.",
        ]
    )
    return "\n".join(lines)


def _stats_dict(stats) -> dict[str, float]:
    return {
        "mae_deg": stats.mae_deg,
        "rmse_deg": stats.rmse_deg,
        "bias_deg": stats.bias_deg,
        "max_abs_error_deg": stats.max_abs_error_deg,
    }


def _ensure_can_write(outputs: FigureOutputs, *, overwrite: bool) -> None:
    if overwrite:
        return
    for path in outputs.__dict__.values():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {path}")


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    return float(np.percentile(np.asarray(values, dtype=float), percentile))


def _nice_time_ticks(max_t_min: float) -> list[float]:
    if max_t_min <= 4:
        step = 1.0
    elif max_t_min <= 12:
        step = 2.0
    else:
        step = 5.0
    ticks = list(np.arange(0, max_t_min + step, step))
    return [float(tick) for tick in ticks if tick <= max_t_min + 1e-9]


def _fmt(value) -> str:
    if value is None or value == "":
        return "NA"
    value = float(value)
    if abs(value) >= 100:
        return f"{value:.1f}"
    if abs(value) >= 10:
        return f"{value:.2f}"
    return f"{value:.3f}"


def _float_or_none(value: str | None) -> float | None:
    if value in {"", None}:
        return None
    return float(value)
