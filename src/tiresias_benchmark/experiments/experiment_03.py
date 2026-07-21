from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev

import numpy as np

from tiresias_benchmark.experiments.experiment_04 import (
    attention_gain_db_series,
    convolve_speech_with_brir_bank,
    db_to_linear,
    interpolate_brir_images,
    load_brir_bank,
    prepare_mono_speech,
    select_speech_pairs,
)
from tiresias_benchmark.metrics.audio import si_sdr_db, tir_db, tir_improvement_db


def run(config: dict) -> dict:
    outputs = config.get("outputs", {})
    processed_dir = Path(outputs.get("processed_dir", "experiments/exp03_sigma_sensitivity/processed"))
    metrics_dir = Path(outputs.get("metrics_dir", "experiments/exp03_sigma_sensitivity/metrics"))
    figures_dir = Path(outputs.get("figures_dir", "experiments/exp03_sigma_sensitivity/figures"))
    overwrite = bool(outputs.get("overwrite", config.get("overwrite", False)))

    processed_csv = processed_dir / "exp03_sigma_results.csv"
    summary_csv = metrics_dir / "exp03_sigma_summary_by_condition.csv"
    summary_json = metrics_dir / "exp03_sigma_summary.json"
    summary_md = metrics_dir / "exp03_sigma_summary.md"
    heatmap_png = figures_dir / "exp03_sigma_tir_heatmaps.png"
    heatmap_svg = figures_dir / "exp03_sigma_tir_heatmaps.svg"
    curve_png = figures_dir / "exp03_sigma_gain_and_tir_curves.png"
    curve_svg = figures_dir / "exp03_sigma_gain_and_tir_curves.svg"

    _ensure_can_write(
        [processed_csv, summary_csv, summary_json, summary_md, heatmap_png, heatmap_svg, curve_png, curve_svg],
        overwrite=overwrite,
    )
    processed_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    speech_pairs = select_speech_pairs(config)
    brir_bank = load_brir_bank(config)
    rows = run_sigma_grid(config, speech_pairs, brir_bank)
    summary_rows = summarize_sigma_rows(rows)
    summary = {
        "experiment_id": config.get("experiment_id", "exp03_sigma_sensitivity"),
        "source_angles_deg": [source["azimuth_deg"] for source in config["sources"]],
        "speech_pair_count": len(speech_pairs),
        "result_rows": len(rows),
        "summary_rows": len(summary_rows),
        "speech_pairs": [
            {
                "pair_id": pair.pair_id,
                "source_a": pair.source_a.sample_id,
                "source_b": pair.source_b.sample_id,
                "speaker_a": pair.source_a.speaker_id,
                "speaker_b": pair.source_b.speaker_id,
            }
            for pair in speech_pairs
        ],
        "processed_csv": str(processed_csv),
        "summary_csv": str(summary_csv),
        "summary_md": str(summary_md),
        "figures": {
            "tir_heatmaps_png": str(heatmap_png),
            "tir_heatmaps_svg": str(heatmap_svg),
            "gain_and_tir_curves_png": str(curve_png),
            "gain_and_tir_curves_svg": str(curve_svg),
        },
    }

    _write_csv(processed_csv, rows)
    _write_csv(summary_csv, summary_rows)
    summary_json.write_text(json.dumps(summary | {"condition_summary": summary_rows}, indent=2) + "\n")
    summary_md.write_text(_summary_markdown(summary, summary_rows, config) + "\n")
    write_sigma_figures(summary_rows, config, heatmap_png, heatmap_svg, curve_png, curve_svg)
    return summary


def run_sigma_grid(config: dict, speech_pairs: list, brir_bank: dict[str, dict[int, np.ndarray]]) -> list[dict]:
    import soundfile as sf
    from scipy.signal import fftconvolve, resample_poly

    sample_rate = int(brir_bank["_sample_rate_hz"]["value"][0])
    sources = {item["name"]: float(item["azimuth_deg"]) for item in config["sources"]}
    source_a_angle = sources.get("source_a", -30.0)
    source_b_angle = sources.get("source_b", 30.0)
    duration_s = float(config.get("speech_duration_s", 6.0))
    target_samples = int(round(duration_s * sample_rate))
    bmax_db = float(config.get("bmax_db", 10.0))
    rows: list[dict] = []

    for pair in speech_pairs:
        speech_a, fs_a = sf.read(pair.source_a.path, dtype="float32")
        speech_b, fs_b = sf.read(pair.source_b.path, dtype="float32")
        speech_a = prepare_mono_speech(speech_a, fs_a, sample_rate, target_samples, resample_poly)
        speech_b = prepare_mono_speech(speech_b, fs_b, sample_rate, target_samples, resample_poly)
        convolved_a = convolve_speech_with_brir_bank(speech_a, brir_bank["A"], target_samples, fftconvolve)
        convolved_b = convolve_speech_with_brir_bank(speech_b, brir_bank["B"], target_samples, fftconvolve)

        for head_yaw in [float(value) for value in config["head_yaw_deg"]]:
            yaw_audio = np.full(target_samples, head_yaw, dtype=np.float64)
            acoustic_a = interpolate_brir_images(convolved_a, yaw_audio)
            acoustic_b = interpolate_brir_images(convolved_b, yaw_audio)
            for sigma in [float(value) for value in config["sigma_deg"]]:
                gain_a_db, gain_b_db = attention_gain_db_series(
                    np.asarray([head_yaw], dtype=np.float64),
                    source_a_angle,
                    source_b_angle,
                    sigma,
                    bmax_db,
                )
                gain_a_db_f = float(gain_a_db[0])
                gain_b_db_f = float(gain_b_db[0])
                gain_a = np.full(target_samples, db_to_linear(np.asarray([gain_a_db_f]))[0])
                gain_b = np.full(target_samples, db_to_linear(np.asarray([gain_b_db_f]))[0])
                for target in ("source_a", "source_b"):
                    metrics = static_target_metrics(
                        acoustic_a,
                        acoustic_b,
                        gain_a,
                        gain_b,
                        target=target,
                    )
                    target_angle = source_a_angle if target == "source_a" else source_b_angle
                    target_gain_db = gain_a_db_f if target == "source_a" else gain_b_db_f
                    interferer_gain_db = gain_b_db_f if target == "source_a" else gain_a_db_f
                    rows.append(
                        {
                            "pair_id": pair.pair_id,
                            "source_a_sample_id": pair.source_a.sample_id,
                            "source_b_sample_id": pair.source_b.sample_id,
                            "target_source": target,
                            "head_yaw_deg": head_yaw,
                            "target_angle_deg": target_angle,
                            "target_error_deg": abs(circular_difference_deg(head_yaw, target_angle)),
                            "sigma_deg": sigma,
                            "source_a_gain_db": gain_a_db_f,
                            "source_b_gain_db": gain_b_db_f,
                            "target_gain_db": target_gain_db,
                            "interferer_gain_db": interferer_gain_db,
                            "target_to_interferer_gain_db": target_gain_db - interferer_gain_db,
                            "tir_improvement_db": metrics["tir_improvement_db"],
                            "input_tir_db": metrics["input_tir_db"],
                            "output_tir_db": metrics["output_tir_db"],
                            "input_si_sdr_db": metrics["input_si_sdr_db"],
                            "output_si_sdr_db": metrics["output_si_sdr_db"],
                            "si_sdr_improvement_db": metrics["output_si_sdr_db"] - metrics["input_si_sdr_db"],
                        }
                    )
    return rows


def static_target_metrics(
    acoustic_a: np.ndarray,
    acoustic_b: np.ndarray,
    gain_a: np.ndarray,
    gain_b: np.ndarray,
    *,
    target: str,
) -> dict[str, float]:
    if target == "source_a":
        target_in = acoustic_a
        interferer_in = acoustic_b
        target_out = gain_a[:, None] * acoustic_a
        interferer_out = gain_b[:, None] * acoustic_b
    elif target == "source_b":
        target_in = acoustic_b
        interferer_in = acoustic_a
        target_out = gain_b[:, None] * acoustic_b
        interferer_out = gain_a[:, None] * acoustic_a
    else:
        raise ValueError(f"unknown target source: {target}")
    output = target_out + interferer_out
    input_mix = target_in + interferer_in
    tir_improvements = [
        tir_improvement_db(target_in[:, ear], interferer_in[:, ear], target_out[:, ear], interferer_out[:, ear])
        for ear in (0, 1)
    ]
    input_tirs = [tir_db(target_in[:, ear], interferer_in[:, ear]) for ear in (0, 1)]
    output_tirs = [tir_db(target_out[:, ear], interferer_out[:, ear]) for ear in (0, 1)]
    input_si_sdrs = [si_sdr_db(input_mix[:, ear], target_in[:, ear]) for ear in (0, 1)]
    output_si_sdrs = [si_sdr_db(output[:, ear], target_out[:, ear]) for ear in (0, 1)]
    return {
        "tir_improvement_db": float(mean(tir_improvements)),
        "input_tir_db": float(mean(input_tirs)),
        "output_tir_db": float(mean(output_tirs)),
        "input_si_sdr_db": float(mean(input_si_sdrs)),
        "output_si_sdr_db": float(mean(output_si_sdrs)),
    }


def summarize_sigma_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row["target_source"],
            row["head_yaw_deg"],
            row["target_angle_deg"],
            row["target_error_deg"],
            row["sigma_deg"],
            row["source_a_gain_db"],
            row["source_b_gain_db"],
            row["target_gain_db"],
            row["interferer_gain_db"],
            row["target_to_interferer_gain_db"],
        )
        grouped.setdefault(key, []).append(row)
    fields = [
        "tir_improvement_db",
        "input_tir_db",
        "output_tir_db",
        "input_si_sdr_db",
        "output_si_sdr_db",
        "si_sdr_improvement_db",
    ]
    summary = []
    for key, values in sorted(grouped.items(), key=_summary_sort_key):
        (
            target_source,
            head_yaw,
            target_angle,
            target_error,
            sigma,
            source_a_gain,
            source_b_gain,
            target_gain,
            interferer_gain,
            gain_ratio,
        ) = key
        row = {
            "target_source": target_source,
            "head_yaw_deg": head_yaw,
            "target_angle_deg": target_angle,
            "target_error_deg": target_error,
            "sigma_deg": sigma,
            "source_a_gain_db": source_a_gain,
            "source_b_gain_db": source_b_gain,
            "target_gain_db": target_gain,
            "interferer_gain_db": interferer_gain,
            "target_to_interferer_gain_db": gain_ratio,
            "pair_count": len(values),
        }
        for field in fields:
            stats = _stats_for([item[field] for item in values])
            row[f"{field}_mean"] = stats["mean"]
            row[f"{field}_sd"] = stats["sd"]
            row[f"{field}_median"] = stats["median"]
        summary.append(row)
    return summary


def write_sigma_figures(
    summary_rows: list[dict],
    config: dict,
    heatmap_png: Path,
    heatmap_svg: Path,
    curve_png: Path,
    curve_svg: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sigmas = sorted({float(row["sigma_deg"]) for row in summary_rows})
    head_yaws = sorted({float(row["head_yaw_deg"]) for row in summary_rows})
    targets = ["source_a", "source_b"]
    target_names = {"source_a": "target A (-30 deg)", "source_b": "target B (+30 deg)"}
    vmax = max(0.1, max(float(row["tir_improvement_db_mean"]) for row in summary_rows))
    vmin = min(0.0, min(float(row["tir_improvement_db_mean"]) for row in summary_rows))

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.3), constrained_layout=True)
    image = None
    for index, target in enumerate(targets):
        grid = np.full((len(sigmas), len(head_yaws)), np.nan)
        for row in summary_rows:
            if row["target_source"] != target:
                continue
            i = sigmas.index(float(row["sigma_deg"]))
            j = head_yaws.index(float(row["head_yaw_deg"]))
            grid[i, j] = float(row["tir_improvement_db_mean"])
        ax = axes[index]
        image = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis", vmin=vmin, vmax=vmax)
        ax.axvline(head_yaws.index(-30.0), color="#f7f7f7", linestyle="--", linewidth=0.9)
        ax.axvline(head_yaws.index(30.0), color="#f7f7f7", linestyle="--", linewidth=0.9)
        ax.set_title(target_names[target], fontsize=11)
        ax.set_xticks(range(0, len(head_yaws), 3), [f"{yaw:.0f}" for yaw in head_yaws[::3]])
        ax.set_yticks(range(len(sigmas)), [f"{sigma:.0f}" for sigma in sigmas])
        ax.set_xlabel("head yaw (deg)")
        if index == 0:
            ax.set_ylabel("sigma (deg)")
    cbar = fig.colorbar(image, ax=list(axes), shrink=0.86)
    cbar.set_label("TIR improvement (dB)")
    fig.suptitle("Experiment 3 sigma sensitivity with measured BRIRs", fontsize=13, fontweight="bold")
    fig.savefig(heatmap_png, dpi=220)
    fig.savefig(heatmap_svg)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.1), constrained_layout=True)
    rows_a = [row for row in summary_rows if row["target_source"] == "source_a"]
    for sigma in sigmas:
        rows = sorted(
            [row for row in rows_a if float(row["sigma_deg"]) == sigma],
            key=lambda row: float(row["head_yaw_deg"]) - float(row["target_angle_deg"]),
        )
        relative_yaw = [float(row["head_yaw_deg"]) - float(row["target_angle_deg"]) for row in rows]
        axes[0].plot(
            relative_yaw,
            [float(row["target_to_interferer_gain_db"]) for row in rows],
            marker="o",
            linewidth=1.7,
            markersize=3.3,
            label=f"{sigma:.0f} deg",
        )
        axes[1].plot(
            relative_yaw,
            [float(row["tir_improvement_db_mean"]) for row in rows],
            marker="o",
            linewidth=1.7,
            markersize=3.3,
            label=f"{sigma:.0f} deg",
        )
    for ax in axes:
        ax.axhline(0.0, color="#777777", linewidth=0.8)
        ax.axvline(0.0, color="#333333", linestyle="--", linewidth=0.9)
        ax.axvline(60.0, color="#999999", linestyle=":", linewidth=1.1)
    axes[0].set_ylabel("target/interferer gain (dB)")
    axes[1].set_ylabel("TIR improvement (dB)")
    for ax in axes:
        ax.set_xlabel("head yaw relative to target A (deg)")
        ax.grid(True, color="#dddddd", linewidth=0.7)
    axes[0].set_title("attention selectivity")
    axes[1].set_title("audio impact")
    axes[1].legend(title="sigma", frameon=False, fontsize=8)
    fig.suptitle("Sigma trade-off: focus width versus enhancement", fontsize=13, fontweight="bold")
    fig.savefig(curve_png, dpi=220)
    fig.savefig(curve_svg)
    plt.close(fig)


def _summary_markdown(summary: dict, summary_rows: list[dict], config: dict) -> str:
    target_rows = [
        row
        for row in summary_rows
        if abs(float(row["head_yaw_deg"]) - float(row["target_angle_deg"])) < 1e-9
    ]
    target_rows = sorted(target_rows, key=lambda row: (row["target_source"], float(row["sigma_deg"])))
    source_a_rows = [row for row in target_rows if row["target_source"] == "source_a"]
    source_b_rows = [row for row in target_rows if row["target_source"] == "source_b"]
    lines = [
        "# Experiment 3 Sigma Sensitivity",
        "",
        "This experiment uses measured mic-corrected BRIRs from Experiment 2 and the same 100 deterministic LibriSpeech pairs used in Experiments 4 and 5.",
        "",
        "The attention model remains monophonic: one scalar gain is computed per source and applied equally to both ears of that source image. Analytical ITD/ILD rendering is not used.",
        "",
        "Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is not used.",
        "",
        "## Outputs",
        "",
        f"- Detailed rows: `{summary['processed_csv']}`",
        f"- Condition summary: `{summary['summary_csv']}`",
        f"- TIR heatmap: `{summary['figures']['tir_heatmaps_png']}`",
        f"- Gain/TIR curves: `{summary['figures']['gain_and_tir_curves_png']}`",
        "",
        "## Dataset",
        "",
        f"- Speech pairs: {summary['speech_pair_count']}",
        "- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`",
        "- The default configuration uses the same deterministic 100 non-overlapping pairs as Experiment 4.",
        "",
        "## Method",
        "",
        "For every static head yaw, both target definitions are evaluated independently:",
        "",
        "- target A: source A is the desired source, regardless of head hemisphere;",
        "- target B: source B is the desired source, regardless of head hemisphere.",
        "",
        "This avoids defining the target from the same head angle that drives the attention gain.",
        "",
        "## Aligned-Target Baseline",
        "",
        "Values below are measured when the head yaw is aligned with the target source angle.",
        "",
        "### Target A",
        "",
    ]
    lines.extend(_target_table(source_a_rows))
    lines.extend(["", "### Target B", ""])
    lines.extend(_target_table(source_b_rows))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Smaller sigma produces stronger angular selectivity and larger target/interferer gain contrast near the attended source.",
            "- Larger sigma produces a wider attention field, reducing peak selectivity but making the gain less sensitive to angular error.",
            "- The heatmaps show the full static operating surface across head yaw and sigma for each independent target definition.",
            "- The curve figure shows the source-A case as signed head yaw relative to the target. The dashed vertical line marks the target direction and the dotted vertical line marks the interferer direction.",
        ]
    )
    return "\n".join(lines)


def circular_difference_deg(measured_deg: float | np.ndarray, reference_deg: float | np.ndarray) -> np.ndarray:
    return (np.asarray(measured_deg) - np.asarray(reference_deg) + 180.0) % 360.0 - 180.0


def _target_table(rows: list[dict]) -> list[str]:
    lines = [
        "| Sigma (deg) | Target gain (dB) | Interferer gain (dB) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |",
        "|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['sigma_deg']:.0f} | {_fmt(row['target_gain_db'])} | "
            f"{_fmt(row['interferer_gain_db'])} | "
            f"{_fmt(row['tir_improvement_db_mean'])} +/- {_fmt(row['tir_improvement_db_sd'])} | "
            f"{_fmt(row['si_sdr_improvement_db_mean'])} +/- {_fmt(row['si_sdr_improvement_db_sd'])} |"
        )
    return lines


def _summary_sort_key(item: tuple) -> tuple:
    (
        target_source,
        head_yaw,
        _target_angle,
        target_error,
        sigma,
        *_,
    ) = item[0]
    return (str(target_source), float(sigma), float(head_yaw), float(target_error))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows to write: {path}")
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _ensure_can_write(paths: list[Path], *, overwrite: bool) -> None:
    if overwrite:
        return
    existing = [path for path in paths if path.exists()]
    if existing:
        sample = "\n".join(str(path) for path in existing[:5])
        raise FileExistsError(f"refusing to overwrite existing Experiment 3 outputs:\n{sample}")


def _stats_for(values: list[float]) -> dict[str, float]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {"mean": float("nan"), "sd": float("nan"), "median": float("nan")}
    return {
        "mean": float(mean(clean)),
        "sd": float(pstdev(clean) if len(clean) > 1 else 0.0),
        "median": float(median(clean)),
    }


def _fmt(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    numeric = float(value)
    if abs(numeric) < 0.005:
        numeric = 0.0
    return f"{numeric:.2f}"
