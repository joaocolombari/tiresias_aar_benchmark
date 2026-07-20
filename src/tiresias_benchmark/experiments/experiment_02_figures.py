from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev


@dataclass(frozen=True)
class Experiment02FigureOutputs:
    reconvolution_png: Path
    reconvolution_svg: Path
    metrics_json: Path
    results_table_md: Path


def generate_experiment_02_validation_report(
    config: dict,
    *,
    session_id: str | None = None,
    metrics_dir: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool = False,
) -> Experiment02FigureOutputs:
    outputs_config = config.get("outputs", {})
    metrics_root = metrics_dir or Path(
        outputs_config.get("metrics_root", "experiments/exp02_brir_measurement/metrics")
    )
    figures_root = output_dir or Path(
        outputs_config.get("figures_root", "experiments/exp02_brir_measurement/figures")
    )
    session_id = session_id or _latest_validation_session(metrics_root)
    validation_csv = metrics_root / session_id / "brir_validation_summary.csv"
    if not validation_csv.exists():
        raise FileNotFoundError(
            f"BRIR validation summary not found: {validation_csv}. Run `brir-validate` first."
        )

    rows = _load_validation_rows(validation_csv)
    if not rows:
        raise ValueError(f"no rows found in {validation_csv}")

    session_metrics_dir = metrics_root / session_id
    session_figures_dir = figures_root / session_id
    outputs = Experiment02FigureOutputs(
        reconvolution_png=session_figures_dir / "exp02_reconvolution_validation.png",
        reconvolution_svg=session_figures_dir / "exp02_reconvolution_validation.svg",
        metrics_json=session_metrics_dir / "exp02_reconvolution_metrics.json",
        results_table_md=session_metrics_dir / "exp02_reconvolution_results.md",
    )
    _ensure_can_write(outputs, overwrite=overwrite)
    session_metrics_dir.mkdir(parents=True, exist_ok=True)
    session_figures_dir.mkdir(parents=True, exist_ok=True)

    metrics = _combined_metrics(
        rows,
        session_id=session_id,
        validation_csv=validation_csv,
        microphone_calibration=_microphone_calibration_summary(config),
    )
    outputs.metrics_json.write_text(json.dumps(metrics, indent=2) + "\n")
    outputs.results_table_md.write_text(_results_markdown(metrics, outputs) + "\n")
    _write_reconvolution_figure(rows, metrics, outputs)
    return outputs


def _latest_validation_session(metrics_root: Path) -> str:
    candidates = [
        path
        for path in metrics_root.iterdir()
        if path.is_dir() and (path / "brir_validation_summary.csv").exists()
    ]
    if not candidates:
        raise FileNotFoundError(f"no validation sessions found in {metrics_root}")
    return max(candidates, key=lambda path: (path / "brir_validation_summary.csv").stat().st_mtime).name


def _load_validation_rows(path: Path) -> list[dict]:
    rows = []
    with path.open(newline="") as file:
        for row in csv.DictReader(file):
            item = dict(row)
            for field in (
                "angle_nominal_deg",
                "angle_wrapped_deg",
                "source_repetition",
                "target_repetition",
                "sample_rate_hz",
                "frames_compared",
                "mean_prediction_sdr_db",
                "mean_corr",
                "mean_nrmse",
                "ear_l_prediction_sdr_db",
                "ear_r_prediction_sdr_db",
                "ear_l_corr",
                "ear_r_corr",
                "ear_l_nrmse",
                "ear_r_nrmse",
                "ear_l_gain_corrected_sdr_db",
                "ear_r_gain_corrected_sdr_db",
            ):
                if field in item:
                    item[field] = _float_or_none(item[field])
            item["closure_measurement"] = str(item.get("closure_measurement", "")).lower() == "true"
            item["mean_gain_corrected_sdr_db"] = _mean_ignore_none(
                [
                    item.get("ear_l_gain_corrected_sdr_db"),
                    item.get("ear_r_gain_corrected_sdr_db"),
                ]
            )
            rows.append(item)
    return rows


def _combined_metrics(
    rows: list[dict],
    *,
    session_id: str,
    validation_csv: Path,
    microphone_calibration: dict,
) -> dict:
    by_type = defaultdict(list)
    by_type_speaker = defaultdict(list)
    by_angle_type = defaultdict(list)
    for row in rows:
        by_type[row["validation_type"]].append(row)
        by_type_speaker[(row["validation_type"], row["speaker"])].append(row)
        by_angle_type[(int(row["angle_nominal_deg"]), row["validation_type"])].append(row)

    return {
        "session_id": session_id,
        "validation_csv": str(validation_csv),
        "row_count": len(rows),
        "microphone_calibration": microphone_calibration,
        "summary_by_validation_type": {
            validation_type: _summary_for_rows(values)
            for validation_type, values in sorted(by_type.items())
        },
        "summary_by_validation_type_and_speaker": {
            f"{validation_type}_{speaker}": {
                "validation_type": validation_type,
                "speaker": speaker,
                **_summary_for_rows(values),
            }
            for (validation_type, speaker), values in sorted(by_type_speaker.items())
        },
        "summary_by_angle_and_validation_type": [
            {
                "angle_nominal_deg": angle,
                "validation_type": validation_type,
                **_summary_for_rows(values),
            }
            for (angle, validation_type), values in sorted(by_angle_type.items())
        ],
        "worst_cross_repetition": _worst_rows(rows, validation_type="cross_repetition", limit=10),
    }


def _summary_for_rows(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "prediction_sdr_db": _stats([row.get("mean_prediction_sdr_db") for row in rows]),
        "gain_corrected_sdr_db": _stats(
            [row.get("mean_gain_corrected_sdr_db") for row in rows]
        ),
        "correlation": _stats([row.get("mean_corr") for row in rows]),
        "nrmse": _stats([row.get("mean_nrmse") for row in rows]),
    }


def _stats(values: list[float | None]) -> dict:
    clean = [float(value) for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"mean": None, "sd": None, "median": None, "min": None, "max": None}
    return {
        "mean": mean(clean),
        "sd": pstdev(clean) if len(clean) > 1 else 0.0,
        "median": median(clean),
        "min": min(clean),
        "max": max(clean),
    }


def _worst_rows(rows: list[dict], *, validation_type: str, limit: int) -> list[dict]:
    filtered = [
        row
        for row in rows
        if row.get("validation_type") == validation_type
        and row.get("mean_prediction_sdr_db") is not None
    ]
    filtered.sort(key=lambda row: row["mean_prediction_sdr_db"])
    return [
        {
            "validation_id": row["validation_id"],
            "angle_nominal_deg": row["angle_nominal_deg"],
            "speaker": row["speaker"],
            "source_repetition": row["source_repetition"],
            "target_repetition": row["target_repetition"],
            "mean_prediction_sdr_db": row["mean_prediction_sdr_db"],
            "mean_corr": row["mean_corr"],
            "mean_nrmse": row["mean_nrmse"],
        }
        for row in filtered[:limit]
    ]


def _results_markdown(metrics: dict, outputs: Experiment02FigureOutputs) -> str:
    summary = metrics["summary_by_validation_type"]
    by_speaker = metrics["summary_by_validation_type_and_speaker"]
    lines = [
        "# Experiment 2 Reconvolution Validation",
        "",
        f"Session: `{metrics['session_id']}`",
        "",
        "The validation predicts the measured microphone sweep by convolving the captured electrical reference with the estimated BRIR. Same-trial validation is an optimistic upper bound because the IR and prediction target come from the same sweep. Cross-repetition validation is the stronger repeatability check because the IR from one repetition predicts the other repetition.",
        "",
        _calibration_markdown_sentence(metrics["microphone_calibration"]),
        "",
        f"Figure: `{outputs.reconvolution_png}`",
        "",
        "## Summary By Validation Type",
        "",
        "| Validation | Rows | Prediction SDR (dB), mean +/- SD | Median SDR (dB) | Correlation, mean +/- SD | NRMSE, mean +/- SD | Gain-corrected SDR (dB), mean +/- SD |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for validation_type in ("same_trial", "cross_repetition"):
        if validation_type not in summary:
            continue
        item = summary[validation_type]
        lines.append(
            f"| {_label(validation_type)} | {item['count']} | "
            f"{_fmt_mean_sd(item['prediction_sdr_db'])} | "
            f"{_fmt(item['prediction_sdr_db']['median'])} | "
            f"{_fmt_mean_sd(item['correlation'], digits=4)} | "
            f"{_fmt_mean_sd(item['nrmse'], digits=4)} | "
            f"{_fmt_mean_sd(item['gain_corrected_sdr_db'])} |"
        )

    lines.extend(
        [
            "",
            "## Summary By Speaker",
            "",
            "| Validation | Speaker | Rows | Prediction SDR (dB), mean +/- SD | Correlation, mean +/- SD | NRMSE, mean +/- SD |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for key in sorted(by_speaker):
        item = by_speaker[key]
        lines.append(
            f"| {_label(item['validation_type'])} | {item['speaker']} | {item['count']} | "
            f"{_fmt_mean_sd(item['prediction_sdr_db'])} | "
            f"{_fmt_mean_sd(item['correlation'], digits=4)} | "
            f"{_fmt_mean_sd(item['nrmse'], digits=4)} |"
        )

    lines.extend(
        [
            "",
            "## Worst Cross-Repetition Cases",
            "",
            "| Validation ID | Angle (deg) | Speaker | Source rep | Target rep | SDR (dB) | Corr | NRMSE |",
            "|---|---:|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in metrics["worst_cross_repetition"]:
        lines.append(
            f"| `{row['validation_id']}` | {_fmt(row['angle_nominal_deg'], digits=0)} | "
            f"{row['speaker']} | {_fmt(row['source_repetition'], digits=0)} | "
            f"{_fmt(row['target_repetition'], digits=0)} | "
            f"{_fmt(row['mean_prediction_sdr_db'])} | "
            f"{_fmt(row['mean_corr'], digits=4)} | {_fmt(row['mean_nrmse'], digits=4)} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Use cross-repetition metrics as the paper-facing validation of the measured BRIR set.",
            "- Same-trial metrics are useful as an upper bound for the deconvolution and alignment procedure.",
            "- Low-SDR cross-repetition cases identify angles or trials worth inspecting physically before using the BRIR bank for final benchmarks.",
            "- A stable cross-repetition correlation near 1.0 and prediction SDR above roughly 20 dB indicate that reconvolving offline speech with these BRIRs should reproduce the measured rig behavior well enough for the planned parameter sweeps.",
            "",
            "## Suggested Next Checks",
            "",
            "- Render predicted and residual WAVs for the worst cross-repetition rows with `brir-validate --write-wavs --overwrite` and listen to the residual.",
            "- Inspect the lowest-angle cases separately if they remain the worst; that pattern can indicate a small setup change between repetitions rather than a deconvolution failure.",
            "- In the paper, show the figure and one compact table with cross-repetition mean +/- SD; keep the same-trial numbers as a methodological sanity check.",
        ]
    )
    return "\n".join(lines)


def _microphone_calibration_summary(config: dict) -> dict:
    microphones = []
    for item in config.get("microphones", []):
        calibration_file = item.get("calibration_file")
        if not calibration_file:
            continue
        microphones.append(
            {
                "ear": item.get("ear"),
                "name": item.get("name"),
                "serial_number": item.get("serial_number"),
                "calibration_file": calibration_file,
                "correction": "inverse_magnitude_zero_phase",
            }
        )
    return {
        "enabled": bool(microphones),
        "microphones": microphones,
    }


def _calibration_markdown_sentence(calibration: dict) -> str:
    if not calibration.get("enabled"):
        return "Microphone factory calibration was not applied."
    parts = []
    for item in calibration.get("microphones", []):
        parts.append(
            f"{item.get('ear')} serial `{item.get('serial_number')}` from `{item.get('calibration_file')}`"
        )
    return (
        "Microphone factory magnitude calibration was applied as inverse zero-phase "
        "frequency-domain correction for " + "; ".join(parts) + "."
    )


def _write_reconvolution_figure(
    rows: list[dict],
    metrics: dict,
    outputs: Experiment02FigureOutputs,
) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "matplotlib is required for Experiment 2 reconvolution figures"
        ) from exc

    by_angle_type = defaultdict(list)
    by_angle_type_speaker = defaultdict(list)
    by_type = defaultdict(list)
    for row in rows:
        angle = int(row["angle_nominal_deg"])
        validation_type = row["validation_type"]
        by_angle_type[(angle, validation_type)].append(row)
        by_angle_type_speaker[(angle, validation_type, row["speaker"])].append(row)
        by_type[validation_type].append(row)

    angles = sorted({int(row["angle_nominal_deg"]) for row in rows})
    fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.0), constrained_layout=True)
    fig.suptitle("BRIR reconvolution validation", fontsize=13, fontweight="bold")

    colors = {"same_trial": "#666666", "cross_repetition": "#0072B2", "A": "#009E73", "B": "#D55E00"}
    labels = {"same_trial": "same trial", "cross_repetition": "cross repetition"}

    ax = axes[0, 0]
    for validation_type in ("same_trial", "cross_repetition"):
        y = [
            _mean_metric(by_angle_type.get((angle, validation_type), []), "mean_prediction_sdr_db")
            for angle in angles
        ]
        ax.plot(
            angles,
            y,
            marker="o",
            markersize=3.5,
            linewidth=1.6,
            color=colors[validation_type],
            label=labels[validation_type],
        )
    ax.set_title("a) Prediction quality by angle", loc="left", fontsize=11)
    ax.set_xlabel("Nominal platform angle (deg)")
    ax.set_ylabel("Prediction SDR (dB)")
    ax.set_xticks(range(0, 361, 60))
    ax.grid(True, color="#dddddd", linewidth=0.7)
    ax.legend(frameon=False, loc="lower right")

    ax = axes[0, 1]
    for speaker in ("A", "B"):
        y = [
            _mean_metric(
                by_angle_type_speaker.get((angle, "cross_repetition", speaker), []),
                "mean_prediction_sdr_db",
            )
            for angle in angles
        ]
        ax.plot(
            angles,
            y,
            marker="o",
            markersize=3.5,
            linewidth=1.6,
            color=colors[speaker],
            label=f"speaker {speaker}",
        )
    ax.set_title("b) Cross-repetition by speaker", loc="left", fontsize=11)
    ax.set_xlabel("Nominal platform angle (deg)")
    ax.set_ylabel("Prediction SDR (dB)")
    ax.set_xticks(range(0, 361, 60))
    ax.grid(True, color="#dddddd", linewidth=0.7)
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1, 0]
    y = [
        _mean_metric(by_angle_type.get((angle, "cross_repetition"), []), "mean_corr")
        for angle in angles
    ]
    ax.plot(angles, y, marker="o", markersize=3.5, linewidth=1.6, color="#0072B2")
    ax.set_title("c) Cross-repetition waveform correlation", loc="left", fontsize=11)
    ax.set_xlabel("Nominal platform angle (deg)")
    ax.set_ylabel("Correlation")
    ax.set_xticks(range(0, 361, 60))
    ax.set_ylim(max(0.94, min(value for value in y if value is not None) - 0.01), 1.001)
    ax.grid(True, color="#dddddd", linewidth=0.7)

    ax = axes[1, 1]
    datasets = [
        [
            row["mean_prediction_sdr_db"]
            for row in by_type.get(validation_type, [])
            if row.get("mean_prediction_sdr_db") is not None
        ]
        for validation_type in ("same_trial", "cross_repetition")
    ]
    try:
        box = ax.boxplot(
            datasets,
            tick_labels=["same\ntrial", "cross\nrepetition"],
            patch_artist=True,
            widths=0.55,
            showfliers=True,
        )
    except TypeError:
        box = ax.boxplot(
            datasets,
            labels=["same\ntrial", "cross\nrepetition"],
            patch_artist=True,
            widths=0.55,
            showfliers=True,
        )
    for patch, color in zip(box["boxes"], [colors["same_trial"], colors["cross_repetition"]]):
        patch.set_facecolor(color)
        patch.set_alpha(0.22)
        patch.set_edgecolor(color)
    for element in ("whiskers", "caps", "medians"):
        for artist in box[element]:
            artist.set_color("#333333")
    ax.set_title("d) SDR distribution", loc="left", fontsize=11)
    ax.set_ylabel("Prediction SDR (dB)")
    ax.grid(True, axis="y", color="#dddddd", linewidth=0.7)

    same = metrics["summary_by_validation_type"].get("same_trial", {})
    cross = metrics["summary_by_validation_type"].get("cross_repetition", {})
    note = (
        f"mean SDR\nsame: {_fmt(same.get('prediction_sdr_db', {}).get('mean'))} dB\n"
        f"cross: {_fmt(cross.get('prediction_sdr_db', {}).get('mean'))} dB"
    )
    ax.text(
        0.05,
        0.95,
        note,
        transform=ax.transAxes,
        va="top",
        fontsize=9,
        color="#333333",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": "#cccccc"},
    )
    outputs.reconvolution_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outputs.reconvolution_png, dpi=220)
    fig.savefig(outputs.reconvolution_svg)
    plt.close(fig)


def _mean_metric(rows: list[dict], field: str) -> float | None:
    values = [
        row.get(field)
        for row in rows
        if row.get(field) is not None and math.isfinite(float(row[field]))
    ]
    if not values:
        return None
    return float(mean(values))


def _ensure_can_write(outputs: Experiment02FigureOutputs, *, overwrite: bool) -> None:
    if overwrite:
        return
    for path in outputs.__dict__.values():
        if path.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {path}")


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    return float(text)


def _mean_ignore_none(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return float(mean(clean))


def _label(value: str) -> str:
    return value.replace("_", " ")


def _fmt(value: float | int | None, *, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def _fmt_mean_sd(stats: dict, *, digits: int = 2) -> str:
    return f"{_fmt(stats.get('mean'), digits=digits)} +/- {_fmt(stats.get('sd'), digits=digits)}"
