from __future__ import annotations

import csv
from pathlib import Path
from collections import defaultdict

import numpy as np

from tiresias_benchmark.metrics.orientation import (
    angular_error_stats,
    circular_difference_deg,
    circular_mean_deg,
    drift_deg_per_minute,
    normalize_yaw_360_deg,
)
from tiresias_benchmark.metrics.telemetry import TelemetryStats


ALLOWED_ROTATION_DIRECTIONS = {"clockwise", "counterclockwise"}


def build_reference_sequences(config: dict) -> dict[str, list[dict]]:
    protocol = config.get("angular_protocol", {})
    runs = config.get("runs", ["ascending", "descending", "randomized"])
    start = int(protocol.get("start_deg", 0))
    stop = int(protocol.get("stop_deg", 360))
    step = int(protocol.get("step_deg", 10))
    include_closure = bool(protocol.get("include_closure_endpoint", True))
    if step <= 0:
        raise ValueError("angular_protocol.step_deg must be positive")
    unique = list(range(start, stop, step))
    sequences: dict[str, list[int]] = {}
    if "ascending" in runs:
        sequences["ascending"] = unique + ([stop] if include_closure else [])
    if "descending" in runs:
        sequences["descending"] = ([stop] if include_closure else []) + list(range(stop - step, start - step, -step))
    if "randomized" in runs:
        randomized_config = config.get("randomized_run", {})
        rng = np.random.default_rng(int(randomized_config.get("seed", 20260713)))
        randomized = [int(value) for value in rng.permutation(unique)]
        closure = randomized_config.get("append_closure_measurement_deg")
        if closure is not None:
            randomized.append(int(closure))
        sequences["randomized"] = randomized
    return {
        run_name: [
            {
                "run_type": run_name,
                "position_index": idx,
                "reference_angle_commanded_deg": angle,
                "reference_angle_normalized_deg": float(normalize_yaw_360_deg(angle)),
                "is_closure_measurement": _is_plan_closure(run_name, idx, angle, sequence),
            }
            for idx, angle in enumerate(sequence)
        ]
        for run_name, sequence in sequences.items()
    }


def _is_plan_closure(run_type: str, idx: int, angle: int, sequence: list[int]) -> bool:
    if run_type == "ascending":
        return idx == len(sequence) - 1 and angle == 360
    if run_type == "descending":
        return idx == len(sequence) - 1 and angle == 0
    if run_type == "randomized":
        return idx == len(sequence) - 1 and angle == 360
    return False


def run(config: dict) -> dict:
    telemetry_csv = Path(config["telemetry_csv"])
    _validate_coordinate_system(config)
    with telemetry_csv.open() as file:
        rows = list(csv.DictReader(file))
    sample_rows = [_sample_from_row(row, config) for row in rows]
    sample_rows = [row for row in sample_rows if row is not None]
    if not sample_rows:
        raise ValueError("no usable calibrated_yaw_deg rows found")

    global_rows = [row for row in sample_rows if not row["is_closure_measurement"]]
    measured = np.array([row["measured_yaw_360_deg"] for row in global_rows], dtype=float)
    reference = np.array([row["reference_angle_normalized_deg"] for row in global_rows], dtype=float)
    stats = angular_error_stats(reference, measured)
    telemetry = _telemetry_from_sample_rows(sample_rows)
    result = {
        "mae_deg": stats.mae_deg,
        "rmse_deg": stats.rmse_deg,
        "bias_deg": stats.bias_deg,
        "max_abs_error_deg": stats.max_abs_error_deg,
        "global_samples_used": len(global_rows),
        "closure_samples_excluded": len(sample_rows) - len(global_rows),
        "reference_sequences": build_reference_sequences(config),
        "closure_errors_deg": _closure_errors(sample_rows),
    }
    global_host_ns = np.array(
        [row["host_time_ns"] for row in global_rows if row["host_time_ns"] is not None],
        dtype=float,
    )
    if len(global_host_ns) == len(measured) and len(global_host_ns) > 1:
        t_s = (global_host_ns - global_host_ns[0]) / 1_000_000_000.0
        result["drift_deg_per_minute"] = drift_deg_per_minute(t_s, measured)
    if telemetry:
        result.update(
            {
                "update_rate_hz": telemetry.update_rate_hz,
                "interval_p95_ms": telemetry.interval_p95_ms,
                "lost_packets": telemetry.lost_packets,
                "packet_loss_percent": telemetry.packet_loss_percent,
            }
        )
    result.update(_optional_drift_results(config))
    return result


def _validate_coordinate_system(config: dict) -> None:
    direction = config.get("coordinate_system", {}).get("positive_rotation_direction", "clockwise")
    if direction not in ALLOWED_ROTATION_DIRECTIONS:
        raise ValueError(
            "coordinate_system.positive_rotation_direction must be "
            f"one of {sorted(ALLOWED_ROTATION_DIRECTIONS)}"
        )


def _sample_from_row(row: dict[str, str], config: dict) -> dict | None:
    segment_kind = row.get("segment_kind", "")
    if segment_kind and segment_kind != "angle":
        return None

    include_in_analysis = _bool_field(row.get("include_in_analysis", ""))
    if include_in_analysis is False:
        return None

    yaw_text = row.get("calibrated_yaw_deg", "")
    if yaw_text == "":
        return None
    commanded = _float_field(row, "reference_angle_commanded_deg")
    if commanded is None:
        commanded = _float_field(row, "reference_yaw_deg")
    if commanded is None:
        commanded = float(config.get("reference_yaw_deg", 0.0))
    normalized = _float_field(row, "reference_angle_normalized_deg")
    if normalized is None:
        normalized = float(normalize_yaw_360_deg(commanded))
    measured_yaw = float(yaw_text)
    measured_360 = float(normalize_yaw_360_deg(measured_yaw))
    run_type = row.get("run_type") or row.get("run_name") or row.get("run_id") or "static"
    position_index = row.get("position_index", "")
    return {
        "run_type": run_type,
        "run_id": row.get("run_id") or run_type,
        "position_index": int(float(position_index)) if position_index != "" else None,
        "reference_angle_commanded_deg": commanded,
        "reference_angle_normalized_deg": normalized,
        "calibrated_yaw_deg": measured_yaw,
        "measured_yaw_360_deg": measured_360,
        "error_deg": float(circular_difference_deg(measured_360, normalized)),
        "is_closure_measurement": _is_row_closure(row, run_type, commanded, config),
        "host_time_ns": _host_time_ns(row),
        "seq": _float_field(row, "seq"),
    }


def _telemetry_from_sample_rows(sample_rows: list[dict]) -> TelemetryStats | None:
    intervals_ms = []
    lost_packets = 0
    expected_packets = 0
    saw_seq = False
    grouped: dict[tuple, list[dict]] = defaultdict(list)
    for row in sample_rows:
        if row["host_time_ns"] is None:
            continue
        key = (
            row["run_id"],
            row["position_index"],
            row["is_closure_measurement"],
        )
        grouped[key].append(row)

    for rows in grouped.values():
        host_ns = np.array([row["host_time_ns"] for row in rows], dtype=float)
        if len(host_ns) >= 2:
            intervals_ms.extend((np.diff(host_ns) / 1_000_000.0).tolist())
        seq = np.array([row["seq"] for row in rows if row["seq"] is not None], dtype=float)
        if len(seq) >= 2:
            saw_seq = True
            gaps = np.diff(seq.astype(int)) - 1
            lost_packets += int(np.sum(np.maximum(gaps, 0)))
            expected_packets += max(int(seq[-1] - seq[0]), 0)

    if not intervals_ms:
        return None
    intervals = np.array(intervals_ms, dtype=float)
    return TelemetryStats(
        update_rate_hz=float(1000.0 / np.mean(intervals)),
        interval_mean_ms=float(np.mean(intervals)),
        interval_std_ms=float(np.std(intervals)),
        interval_p95_ms=float(np.percentile(intervals, 95)),
        interval_p99_ms=float(np.percentile(intervals, 99)),
        lost_packets=lost_packets if saw_seq else None,
        packet_loss_percent=(
            100.0 * lost_packets / expected_packets
            if saw_seq and expected_packets > 0
            else (0.0 if saw_seq else None)
        ),
    )


def _host_time_ns(row: dict[str, str]) -> float | None:
    value = row.get("host_monotonic_timestamp_ns") or row.get("host_time_ns") or ""
    return None if value == "" else float(value)


def _float_field(row: dict[str, str], key: str) -> float | None:
    value = row.get(key, "")
    return None if value == "" or value is None else float(value)


def _bool_field(value: str) -> bool | None:
    if value == "":
        return None
    return value.lower() in {"1", "true", "yes", "y"}


def _is_row_closure(row: dict[str, str], run_type: str, commanded: float, config: dict) -> bool:
    explicit = _bool_field(row.get("is_closure_measurement", ""))
    if explicit is not None:
        return explicit
    protocol = config.get("angular_protocol", {})
    start = float(protocol.get("start_deg", 0))
    stop = float(protocol.get("stop_deg", 360))
    if run_type == "ascending":
        return commanded == stop
    if run_type == "descending":
        return commanded == start
    if run_type == "randomized":
        closure = config.get("randomized_run", {}).get("append_closure_measurement_deg", stop)
        return commanded == float(closure)
    return False


def _closure_errors(sample_rows: list[dict]) -> dict[str, float]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in sample_rows:
        grouped[row["run_id"]].append(row)
    results = {}
    for run_id, rows in grouped.items():
        rows = sorted(rows, key=lambda row: row["position_index"] if row["position_index"] is not None else 0)
        run_type = rows[0]["run_type"]
        if run_type == "ascending":
            start = _mean_for_command(rows, 0, closure=False)
            end = _mean_for_command(rows, 360, closure=True)
        elif run_type == "descending":
            start = _mean_for_command(rows, 360, closure=False)
            end = _mean_for_command(rows, 0, closure=True)
        elif run_type == "randomized":
            start = _mean_for_command(rows, 0, closure=False)
            end = _mean_for_command(rows, 360, closure=True)
        else:
            continue
        if start is not None and end is not None:
            results[run_id] = float(circular_difference_deg(end, start))
    return results


def _mean_for_command(rows: list[dict], commanded_deg: float, closure: bool) -> float | None:
    values = [
        row["measured_yaw_360_deg"]
        for row in rows
        if row["reference_angle_commanded_deg"] == commanded_deg
        and row["is_closure_measurement"] is closure
    ]
    return circular_mean_deg(np.array(values, dtype=float)) if values else None


def _optional_drift_results(config: dict) -> dict:
    drift = config.get("drift", {})
    result = {}
    for label, key in (("before", "before_csv"), ("after", "after_csv")):
        if key in drift:
            result[f"drift_{label}_deg_per_minute"] = _drift_from_csv(Path(drift[key]))
    return result


def _drift_from_csv(path: Path) -> float:
    with path.open() as file:
        rows = list(csv.DictReader(file))
    host_ns = []
    yaws = []
    for row in rows:
        time_text = row.get("host_monotonic_timestamp_ns") or row.get("host_time_ns") or ""
        yaw_text = row.get("calibrated_yaw_deg", "")
        if time_text and yaw_text:
            host_ns.append(float(time_text))
            yaws.append(float(yaw_text))
    if len(host_ns) < 2:
        return 0.0
    t_s = (np.array(host_ns, dtype=float) - host_ns[0]) / 1_000_000_000.0
    return drift_deg_per_minute(t_s, np.array(yaws, dtype=float))
