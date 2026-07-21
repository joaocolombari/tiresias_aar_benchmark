from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import mean, median, pstdev

import numpy as np

from tiresias_benchmark.experiments.experiment_04 import (
    attention_gain_db_series,
    build_trajectories,
    convolve_speech_with_brir_bank,
    db_to_linear,
    delayed_yaw_series,
    interpolate_brir_images,
    load_brir_bank,
    prepare_mono_speech,
    select_speech_pairs,
)
from tiresias_benchmark.metrics.audio import si_sdr_db, stoi_score, tir_db, tir_improvement_db
from tiresias_benchmark.separation.leakage import (
    delay_signal_samples,
    leakage_coefficient_from_sdr_db,
)


def run(config: dict) -> dict:
    outputs = config.get("outputs", {})
    processed_dir = Path(outputs.get("processed_dir", "experiments/exp05_separator_requirements/processed"))
    metrics_dir = Path(outputs.get("metrics_dir", "experiments/exp05_separator_requirements/metrics"))
    figures_dir = Path(outputs.get("figures_dir", "experiments/exp05_separator_requirements/figures"))
    overwrite = bool(outputs.get("overwrite", config.get("overwrite", False)))

    processed_csv = processed_dir / "exp05_separator_results.csv"
    summary_csv = metrics_dir / "exp05_separator_summary_by_condition.csv"
    source_delay_plot_csv = metrics_dir / "exp05_source_delay_plot_summary.csv"
    requirements_csv = metrics_dir / "exp05_separator_requirements.csv"
    summary_json = metrics_dir / "exp05_separator_summary.json"
    summary_md = metrics_dir / "exp05_separator_summary.md"
    heatmap_png = figures_dir / "exp05_separator_heatmaps.png"
    heatmap_svg = figures_dir / "exp05_separator_heatmaps.svg"
    envelope_png = figures_dir / "exp05_requirement_envelope.png"
    envelope_svg = figures_dir / "exp05_requirement_envelope.svg"
    source_delay_png = figures_dir / "exp05_source_delay_impact.png"
    source_delay_svg = figures_dir / "exp05_source_delay_impact.svg"

    _ensure_can_write(
        [
            processed_csv,
            summary_csv,
            source_delay_plot_csv,
            requirements_csv,
            summary_json,
            summary_md,
            heatmap_png,
            heatmap_svg,
            envelope_png,
            envelope_svg,
            source_delay_png,
            source_delay_svg,
        ],
        overwrite=overwrite,
    )
    processed_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    speech_pairs = select_speech_pairs(config)
    brir_bank = load_brir_bank(config)
    rows = run_separator_grid(config, speech_pairs, brir_bank)
    summary_rows = summarize_separator_rows(rows)
    requirement_rows = compute_requirement_rows(summary_rows, config)
    source_delay_plot_rows = build_source_delay_plot_summary(config, speech_pairs, brir_bank)

    summary = {
        "experiment_id": config.get("experiment_id", "exp05_separator_requirements"),
        "source_angles_deg": [source["azimuth_deg"] for source in config["sources"]],
        "speech_pair_count": len(speech_pairs),
        "result_rows": len(rows),
        "summary_rows": len(summary_rows),
        "requirement_rows": len(requirement_rows),
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
        "source_delay_plot_csv": str(source_delay_plot_csv),
        "requirements_csv": str(requirements_csv),
        "summary_md": str(summary_md),
        "figures": {
            "separator_heatmaps_png": str(heatmap_png),
            "separator_heatmaps_svg": str(heatmap_svg),
            "requirement_envelope_png": str(envelope_png),
            "requirement_envelope_svg": str(envelope_svg),
            "source_delay_impact_png": str(source_delay_png),
            "source_delay_impact_svg": str(source_delay_svg),
        },
    }

    _write_csv(processed_csv, rows)
    _write_csv(summary_csv, summary_rows)
    _write_csv(source_delay_plot_csv, source_delay_plot_rows)
    _write_csv(requirements_csv, requirement_rows)
    summary_json.write_text(
        json.dumps(
            summary
            | {
                "condition_summary": summary_rows,
                "source_delay_plot_summary": source_delay_plot_rows,
                "requirements": requirement_rows,
            },
            indent=2,
        )
        + "\n"
    )
    summary_md.write_text(_summary_markdown(summary, summary_rows, requirement_rows, config) + "\n")
    write_separator_figures(
        summary_rows,
        requirement_rows,
        source_delay_plot_rows,
        config,
        heatmap_png,
        heatmap_svg,
        envelope_png,
        envelope_svg,
        source_delay_png,
        source_delay_svg,
    )
    return summary


def build_source_delay_plot_summary(
    config: dict,
    speech_pairs: list,
    brir_bank: dict[str, dict[int, np.ndarray]],
) -> list[dict]:
    figure_config = config.get("figures", {})
    metric = str(figure_config.get("source_delay_metric", "stoi_vs_ideal_output"))
    if metric == "stoi_vs_ideal_output":
        return run_source_delay_stoi_grid(config, speech_pairs, brir_bank)

    plot_delays = figure_config.get("source_delay_plot_delay_ms")
    if not plot_delays:
        return []
    plot_config = dict(config)
    plot_config["sigma_deg"] = [float(figure_config.get("representative_sigma_deg", 20.0))]
    plot_config["orientation_delay_ms"] = [
        float(figure_config.get("representative_orientation_delay_ms", 0.0))
    ]
    plot_config["source_estimate_delay_ms"] = [float(value) for value in plot_delays]
    rows = run_separator_grid(plot_config, speech_pairs, brir_bank)
    return summarize_separator_rows(rows)


def run_source_delay_stoi_grid(
    config: dict,
    speech_pairs: list,
    brir_bank: dict[str, dict[int, np.ndarray]],
) -> list[dict]:
    import soundfile as sf
    from scipy.signal import fftconvolve, resample_poly

    figure_config = config.get("figures", {})
    sample_rate = int(brir_bank["_sample_rate_hz"]["value"][0])
    sources = {item["name"]: float(item["azimuth_deg"]) for item in config["sources"]}
    source_a_angle = sources.get("source_a", -30.0)
    source_b_angle = sources.get("source_b", 30.0)
    duration_s = float(config.get("speech_duration_s", 6.0))
    target_samples = int(round(duration_s * sample_rate))
    bmax_db = float(config.get("bmax_db", 10.0))
    post_window_s = float(config.get("post_switch_analysis_window_s", 1.0))
    stoi_sample_rate = 10_000
    resample_gcd = math.gcd(sample_rate, stoi_sample_rate)
    stoi_up = stoi_sample_rate // resample_gcd
    stoi_down = sample_rate // resample_gcd
    representative_sigma = float(figure_config.get("representative_sigma_deg", 20.0))
    representative_orientation_delay = float(
        figure_config.get("representative_orientation_delay_ms", 0.0)
    )
    plot_delays = figure_config.get("source_delay_plot_delay_ms", config["source_estimate_delay_ms"])
    source_delays = [float(value) for value in plot_delays]
    separator_sdrs = list(config["separator_sdr_db"])
    rows: list[dict] = []

    for pair in speech_pairs:
        speech_a, fs_a = sf.read(pair.source_a.path, dtype="float32")
        speech_b, fs_b = sf.read(pair.source_b.path, dtype="float32")
        speech_a = prepare_mono_speech(speech_a, fs_a, sample_rate, target_samples, resample_poly)
        speech_b = prepare_mono_speech(speech_b, fs_b, sample_rate, target_samples, resample_poly)
        convolved_a = convolve_speech_with_brir_bank(speech_a, brir_bank["A"], target_samples, fftconvolve)
        convolved_b = convolve_speech_with_brir_bank(speech_b, brir_bank["B"], target_samples, fftconvolve)

        for trajectory in build_trajectories(config):
            t_audio = np.arange(target_samples, dtype=np.float64) / float(sample_rate)
            yaw_audio = np.interp(t_audio, trajectory.time_s, trajectory.yaw_deg)
            acoustic_a = interpolate_brir_images(convolved_a, yaw_audio)
            acoustic_b = interpolate_brir_images(convolved_b, yaw_audio)
            delayed_sources = {
                delay_ms: (
                    delay_signal_samples(acoustic_a, int(round(delay_ms * sample_rate / 1000.0))),
                    delay_signal_samples(acoustic_b, int(round(delay_ms * sample_rate / 1000.0))),
                )
                for delay_ms in source_delays
            }

            ideal_gain_a_db, ideal_gain_b_db = attention_gain_db_series(
                trajectory.yaw_deg,
                source_a_angle,
                source_b_angle,
                representative_sigma,
                bmax_db,
            )
            ideal_gain_a_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, ideal_gain_a_db))
            ideal_gain_b_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, ideal_gain_b_db))
            ideal_output = source_overlay_output_window(
                physical_a=acoustic_a,
                physical_b=acoustic_b,
                estimate_a=acoustic_a,
                estimate_b=acoustic_b,
                gain_a=ideal_gain_a_audio,
                gain_b=ideal_gain_b_audio,
                leakage=0.0,
                sample_rate_hz=sample_rate,
                switch_time_s=trajectory.switch_time_s,
                window_s=post_window_s,
            )
            ideal_output_stoi = resample_poly(ideal_output, stoi_up, stoi_down, axis=0)
            ideal_stoi = float(
                mean(
                    _bounded_stoi(
                        ideal_output_stoi[:, ear],
                        ideal_output_stoi[:, ear],
                        stoi_sample_rate,
                    )
                    for ear in (0, 1)
                )
            )

            delayed_yaw = delayed_yaw_series(
                trajectory.time_s,
                trajectory.yaw_deg,
                representative_orientation_delay,
                mode=str(config.get("delay_mode", "hold")),
            )
            gain_a_db, gain_b_db = attention_gain_db_series(
                delayed_yaw,
                source_a_angle,
                source_b_angle,
                representative_sigma,
                bmax_db,
            )
            gain_a_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, gain_a_db))
            gain_b_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, gain_b_db))

            for source_delay_ms in source_delays:
                estimate_a, estimate_b = delayed_sources[source_delay_ms]
                for separator_sdr in separator_sdrs:
                    leakage = leakage_coefficient_from_sdr_db(separator_sdr)
                    output = source_overlay_output_window(
                        physical_a=acoustic_a,
                        physical_b=acoustic_b,
                        estimate_a=estimate_a,
                        estimate_b=estimate_b,
                        gain_a=gain_a_audio,
                        gain_b=gain_b_audio,
                        leakage=leakage,
                        sample_rate_hz=sample_rate,
                        switch_time_s=trajectory.switch_time_s,
                        window_s=post_window_s,
                    )
                    output_stoi = resample_poly(output, stoi_up, stoi_down, axis=0)
                    scores = [
                        _bounded_stoi(
                            output_stoi[:, ear],
                            ideal_output_stoi[:, ear],
                            stoi_sample_rate,
                        )
                        for ear in (0, 1)
                    ]
                    score = float(mean(scores))
                    rows.append(
                        {
                            "pair_id": pair.pair_id,
                            "source_a_sample_id": pair.source_a.sample_id,
                            "source_b_sample_id": pair.source_b.sample_id,
                            "trajectory": trajectory.name,
                            "angular_velocity_deg_s": trajectory.velocity_deg_s,
                            "sigma_deg": representative_sigma,
                            "orientation_delay_ms": representative_orientation_delay,
                            "source_estimate_delay_ms": float(source_delay_ms),
                            "source_delay_angular_lag_deg": trajectory.velocity_deg_s
                            * float(source_delay_ms)
                            / 1000.0,
                            "separator_sdr_db": _sdr_value(separator_sdr),
                            "separator_sdr_label": _sdr_label(separator_sdr),
                            "leakage_linear": leakage,
                            "ideal_stoi_vs_ideal_output": ideal_stoi,
                            "stoi_vs_ideal_output": score,
                            "stoi_loss_vs_ideal_output": ideal_stoi - score,
                        }
                    )
    return summarize_source_delay_stoi_rows(rows)


def _bounded_stoi(estimate: np.ndarray, reference: np.ndarray, sample_rate_hz: int) -> float:
    return min(1.0, max(0.0, stoi_score(estimate, reference, sample_rate_hz)))


def run_separator_grid(
    config: dict,
    speech_pairs: list,
    brir_bank: dict[str, dict[int, np.ndarray]],
) -> list[dict]:
    import soundfile as sf
    from scipy.signal import fftconvolve, resample_poly

    sample_rate = int(brir_bank["_sample_rate_hz"]["value"][0])
    sources = {item["name"]: float(item["azimuth_deg"]) for item in config["sources"]}
    source_a_angle = sources.get("source_a", -30.0)
    source_b_angle = sources.get("source_b", 30.0)
    duration_s = float(config.get("speech_duration_s", 6.0))
    target_samples = int(round(duration_s * sample_rate))
    bmax_db = float(config.get("bmax_db", 10.0))
    post_window_s = float(config.get("post_switch_analysis_window_s", 1.0))
    orientation_delays = [float(value) for value in config.get("orientation_delay_ms", [0])]
    source_delays = [float(value) for value in config["source_estimate_delay_ms"]]
    separator_sdrs = list(config["separator_sdr_db"])
    rows: list[dict] = []

    for pair in speech_pairs:
        speech_a, fs_a = sf.read(pair.source_a.path, dtype="float32")
        speech_b, fs_b = sf.read(pair.source_b.path, dtype="float32")
        speech_a = prepare_mono_speech(speech_a, fs_a, sample_rate, target_samples, resample_poly)
        speech_b = prepare_mono_speech(speech_b, fs_b, sample_rate, target_samples, resample_poly)
        convolved_a = convolve_speech_with_brir_bank(speech_a, brir_bank["A"], target_samples, fftconvolve)
        convolved_b = convolve_speech_with_brir_bank(speech_b, brir_bank["B"], target_samples, fftconvolve)

        for trajectory in build_trajectories(config):
            t_audio = np.arange(target_samples, dtype=np.float64) / float(sample_rate)
            yaw_audio = np.interp(t_audio, trajectory.time_s, trajectory.yaw_deg)
            acoustic_a = interpolate_brir_images(convolved_a, yaw_audio)
            acoustic_b = interpolate_brir_images(convolved_b, yaw_audio)
            delayed_sources = {
                delay_ms: (
                    delay_signal_samples(acoustic_a, int(round(delay_ms * sample_rate / 1000.0))),
                    delay_signal_samples(acoustic_b, int(round(delay_ms * sample_rate / 1000.0))),
                )
                for delay_ms in source_delays
            }

            for sigma in config["sigma_deg"]:
                sigma_f = float(sigma)
                ideal_gain_a_db, ideal_gain_b_db = attention_gain_db_series(
                    trajectory.yaw_deg,
                    source_a_angle,
                    source_b_angle,
                    sigma_f,
                    bmax_db,
                )
                ideal_gain_a_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, ideal_gain_a_db))
                ideal_gain_b_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, ideal_gain_b_db))
                ideal_metrics = separator_component_metrics(
                    physical_a=acoustic_a,
                    physical_b=acoustic_b,
                    estimate_a=acoustic_a,
                    estimate_b=acoustic_b,
                    gain_a=ideal_gain_a_audio,
                    gain_b=ideal_gain_b_audio,
                    leakage=0.0,
                    sample_rate_hz=sample_rate,
                    switch_time_s=trajectory.switch_time_s,
                    window_s=post_window_s,
                )

                for orientation_delay_ms in orientation_delays:
                    delayed_yaw = delayed_yaw_series(
                        trajectory.time_s,
                        trajectory.yaw_deg,
                        orientation_delay_ms,
                        mode=str(config.get("delay_mode", "hold")),
                    )
                    gain_a_db, gain_b_db = attention_gain_db_series(
                        delayed_yaw,
                        source_a_angle,
                        source_b_angle,
                        sigma_f,
                        bmax_db,
                    )
                    gain_a_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, gain_a_db))
                    gain_b_audio = db_to_linear(np.interp(t_audio, trajectory.time_s, gain_b_db))
                    gain_error = np.concatenate(
                        [gain_a_db - ideal_gain_a_db, gain_b_db - ideal_gain_b_db]
                    )
                    for source_delay_ms in source_delays:
                        estimate_a, estimate_b = delayed_sources[source_delay_ms]
                        for separator_sdr in separator_sdrs:
                            leakage = leakage_coefficient_from_sdr_db(separator_sdr)
                            metrics = separator_component_metrics(
                                physical_a=acoustic_a,
                                physical_b=acoustic_b,
                                estimate_a=estimate_a,
                                estimate_b=estimate_b,
                                gain_a=gain_a_audio,
                                gain_b=gain_b_audio,
                                leakage=leakage,
                                sample_rate_hz=sample_rate,
                                switch_time_s=trajectory.switch_time_s,
                                window_s=post_window_s,
                            )
                            rows.append(
                                {
                                    "pair_id": pair.pair_id,
                                    "source_a_sample_id": pair.source_a.sample_id,
                                    "source_b_sample_id": pair.source_b.sample_id,
                                    "trajectory": trajectory.name,
                                    "angular_velocity_deg_s": trajectory.velocity_deg_s,
                                    "sigma_deg": sigma_f,
                                    "orientation_delay_ms": float(orientation_delay_ms),
                                    "source_estimate_delay_ms": float(source_delay_ms),
                                    "source_delay_angular_lag_deg": trajectory.velocity_deg_s
                                    * float(source_delay_ms)
                                    / 1000.0,
                                    "separator_sdr_db": _sdr_value(separator_sdr),
                                    "separator_sdr_label": _sdr_label(separator_sdr),
                                    "leakage_linear": leakage,
                                    "tir_improvement_db": metrics["tir_improvement_db"],
                                    "tir_loss_vs_ideal_db": metrics["tir_improvement_db"]
                                    - ideal_metrics["tir_improvement_db"],
                                    "tir_retention_fraction": _safe_ratio(
                                        metrics["tir_improvement_db"],
                                        ideal_metrics["tir_improvement_db"],
                                    ),
                                    "si_sdr_physical_improvement_db": metrics[
                                        "output_si_sdr_physical_target_db"
                                    ]
                                    - ideal_metrics["input_si_sdr_physical_target_db"],
                                    "si_sdr_loss_vs_ideal_db": metrics[
                                        "output_si_sdr_physical_target_db"
                                    ]
                                    - ideal_metrics["output_si_sdr_physical_target_db"],
                                    "component_si_sdr_loss_vs_ideal_db": metrics[
                                        "output_si_sdr_component_target_db"
                                    ]
                                    - ideal_metrics["output_si_sdr_component_target_db"],
                                    "gain_error_rms_db": float(np.sqrt(np.mean(gain_error**2))),
                                    "gain_error_peak_abs_db": float(np.max(np.abs(gain_error))),
                                    "ideal_tir_improvement_db": ideal_metrics["tir_improvement_db"],
                                    "input_tir_db": metrics["input_tir_db"],
                                    "output_tir_db": metrics["output_tir_db"],
                                    "input_si_sdr_physical_target_db": metrics[
                                        "input_si_sdr_physical_target_db"
                                    ],
                                    "output_si_sdr_physical_target_db": metrics[
                                        "output_si_sdr_physical_target_db"
                                    ],
                                    "output_si_sdr_component_target_db": metrics[
                                        "output_si_sdr_component_target_db"
                                    ],
                                }
                            )
    return rows


def separator_component_metrics(
    *,
    physical_a: np.ndarray,
    physical_b: np.ndarray,
    estimate_a: np.ndarray,
    estimate_b: np.ndarray,
    gain_a: np.ndarray,
    gain_b: np.ndarray,
    leakage: float,
    sample_rate_hz: int,
    switch_time_s: float,
    window_s: float,
) -> dict[str, float]:
    signals = separator_output_window(
        physical_a=physical_a,
        physical_b=physical_b,
        estimate_a=estimate_a,
        estimate_b=estimate_b,
        gain_a=gain_a,
        gain_b=gain_b,
        leakage=leakage,
        sample_rate_hz=sample_rate_hz,
        switch_time_s=switch_time_s,
        window_s=window_s,
    )
    target_in = signals["target_in"]
    interferer_in = signals["interferer_in"]
    target_out = signals["target_out"]
    interferer_out = signals["interferer_out"]
    output = signals["output"]
    input_mix = signals["input_mix"]

    tir_improvements = [
        tir_improvement_db(target_in[:, ear], interferer_in[:, ear], target_out[:, ear], interferer_out[:, ear])
        for ear in (0, 1)
    ]
    input_tirs = [tir_db(target_in[:, ear], interferer_in[:, ear]) for ear in (0, 1)]
    output_tirs = [tir_db(target_out[:, ear], interferer_out[:, ear]) for ear in (0, 1)]
    input_si_sdrs = [si_sdr_db(input_mix[:, ear], target_in[:, ear]) for ear in (0, 1)]
    output_si_sdr_physical = [si_sdr_db(output[:, ear], target_in[:, ear]) for ear in (0, 1)]
    output_si_sdr_component = [si_sdr_db(output[:, ear], target_out[:, ear]) for ear in (0, 1)]
    return {
        "tir_improvement_db": float(mean(tir_improvements)),
        "input_tir_db": float(mean(input_tirs)),
        "output_tir_db": float(mean(output_tirs)),
        "input_si_sdr_physical_target_db": float(mean(input_si_sdrs)),
        "output_si_sdr_physical_target_db": float(mean(output_si_sdr_physical)),
        "output_si_sdr_component_target_db": float(mean(output_si_sdr_component)),
    }


def separator_output_window(
    *,
    physical_a: np.ndarray,
    physical_b: np.ndarray,
    estimate_a: np.ndarray,
    estimate_b: np.ndarray,
    gain_a: np.ndarray,
    gain_b: np.ndarray,
    leakage: float,
    sample_rate_hz: int,
    switch_time_s: float,
    window_s: float,
) -> dict[str, np.ndarray]:
    start = int(round(switch_time_s * sample_rate_hz))
    stop = min(len(physical_a), start + int(round(window_s * sample_rate_hz)))
    if stop <= start:
        raise ValueError("empty post-switch analysis window")

    target_in = physical_b[start:stop]
    interferer_in = physical_a[start:stop]
    estimate_target = estimate_b[start:stop]
    estimate_interferer = estimate_a[start:stop]
    gain_target = gain_b[start:stop, None]
    gain_interferer = gain_a[start:stop, None]

    target_out = gain_target * estimate_target + gain_interferer * leakage * estimate_target
    interferer_out = gain_interferer * estimate_interferer + gain_target * leakage * estimate_interferer
    output = target_out + interferer_out
    input_mix = target_in + interferer_in
    return {
        "target_in": target_in,
        "interferer_in": interferer_in,
        "estimate_target": estimate_target,
        "estimate_interferer": estimate_interferer,
        "target_out": target_out,
        "interferer_out": interferer_out,
        "output": output,
        "input_mix": input_mix,
    }


def source_overlay_output_window(
    *,
    physical_a: np.ndarray,
    physical_b: np.ndarray,
    estimate_a: np.ndarray,
    estimate_b: np.ndarray,
    gain_a: np.ndarray,
    gain_b: np.ndarray,
    leakage: float,
    sample_rate_hz: int,
    switch_time_s: float,
    window_s: float,
) -> np.ndarray:
    start = int(round(switch_time_s * sample_rate_hz))
    stop = min(len(physical_a), start + int(round(window_s * sample_rate_hz)))
    if stop <= start:
        raise ValueError("empty post-switch analysis window")

    physical_a_window = physical_a[start:stop]
    physical_b_window = physical_b[start:stop]
    estimate_a_window = estimate_a[start:stop]
    estimate_b_window = estimate_b[start:stop]
    boost_a = gain_a[start:stop, None] - 1.0
    boost_b = gain_b[start:stop, None] - 1.0
    estimate_a_leaky = estimate_a_window + leakage * estimate_b_window
    estimate_b_leaky = estimate_b_window + leakage * estimate_a_window
    live_scene = physical_a_window + physical_b_window
    return live_scene + boost_a * estimate_a_leaky + boost_b * estimate_b_leaky


def summarize_separator_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row["trajectory"],
            row["angular_velocity_deg_s"],
            row["sigma_deg"],
            row["orientation_delay_ms"],
            row["source_estimate_delay_ms"],
            row["source_delay_angular_lag_deg"],
            row["separator_sdr_label"],
            row["separator_sdr_db"],
            row["leakage_linear"],
        )
        grouped.setdefault(key, []).append(row)
    fields = [
        "tir_improvement_db",
        "tir_loss_vs_ideal_db",
        "tir_retention_fraction",
        "si_sdr_physical_improvement_db",
        "si_sdr_loss_vs_ideal_db",
        "component_si_sdr_loss_vs_ideal_db",
        "gain_error_rms_db",
        "gain_error_peak_abs_db",
        "input_tir_db",
        "output_tir_db",
        "output_si_sdr_physical_target_db",
        "output_si_sdr_component_target_db",
    ]
    summary = []
    for key, values in sorted(grouped.items(), key=_summary_sort_key):
        (
            trajectory,
            velocity,
            sigma,
            orientation_delay,
            source_delay,
            source_delay_lag,
            separator_sdr_label,
            separator_sdr,
            leakage,
        ) = key
        item = {
            "trajectory": trajectory,
            "angular_velocity_deg_s": velocity,
            "sigma_deg": sigma,
            "orientation_delay_ms": orientation_delay,
            "source_estimate_delay_ms": source_delay,
            "source_delay_angular_lag_deg": source_delay_lag,
            "separator_sdr_db": separator_sdr,
            "separator_sdr_label": separator_sdr_label,
            "leakage_linear": leakage,
            "pair_count": len(values),
        }
        for field in fields:
            stats = _stats_for([row[field] for row in values])
            item[f"{field}_mean"] = stats["mean"]
            item[f"{field}_sd"] = stats["sd"]
            item[f"{field}_median"] = stats["median"]
        summary.append(item)
    return summary


def summarize_source_delay_stoi_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row["trajectory"],
            row["angular_velocity_deg_s"],
            row["sigma_deg"],
            row["orientation_delay_ms"],
            row["source_estimate_delay_ms"],
            row["source_delay_angular_lag_deg"],
            row["separator_sdr_label"],
            row["separator_sdr_db"],
            row["leakage_linear"],
        )
        grouped.setdefault(key, []).append(row)
    fields = [
        "ideal_stoi_vs_ideal_output",
        "stoi_vs_ideal_output",
        "stoi_loss_vs_ideal_output",
    ]
    summary = []
    for key, values in sorted(grouped.items(), key=_summary_sort_key):
        (
            trajectory,
            velocity,
            sigma,
            orientation_delay,
            source_delay,
            source_delay_lag,
            separator_sdr_label,
            separator_sdr,
            leakage,
        ) = key
        item = {
            "trajectory": trajectory,
            "angular_velocity_deg_s": velocity,
            "sigma_deg": sigma,
            "orientation_delay_ms": orientation_delay,
            "source_estimate_delay_ms": source_delay,
            "source_delay_angular_lag_deg": source_delay_lag,
            "separator_sdr_db": separator_sdr,
            "separator_sdr_label": separator_sdr_label,
            "leakage_linear": leakage,
            "pair_count": len(values),
        }
        for field in fields:
            stats = _stats_for([row[field] for row in values])
            item[f"{field}_mean"] = stats["mean"]
            item[f"{field}_sd"] = stats["sd"]
            item[f"{field}_median"] = stats["median"]
        summary.append(item)
    return summary


def compute_requirement_rows(summary_rows: list[dict], config: dict) -> list[dict]:
    requirement_config = config.get("requirements", {})
    retention = float(requirement_config.get("tir_retention_fraction", 0.90))
    si_sdr_metric = str(requirement_config.get("si_sdr_loss_metric", "component"))
    if si_sdr_metric == "physical":
        si_sdr_field = "si_sdr_loss_vs_ideal_db_mean"
        max_si_sdr_loss_db = float(requirement_config.get("max_si_sdr_loss_db", 1.0))
    else:
        si_sdr_field = "component_si_sdr_loss_vs_ideal_db_mean"
        max_si_sdr_loss_db = float(requirement_config.get("max_component_si_sdr_loss_db", 1.0))
    groups: dict[tuple, list[dict]] = {}
    for row in summary_rows:
        key = (
            row["trajectory"],
            row["angular_velocity_deg_s"],
            row["sigma_deg"],
            row["orientation_delay_ms"],
            row["source_estimate_delay_ms"],
            row["source_delay_angular_lag_deg"],
        )
        groups.setdefault(key, []).append(row)

    requirements = []
    for key, rows in sorted(groups.items()):
        (
            trajectory,
            velocity,
            sigma,
            orientation_delay,
            source_delay,
            source_delay_lag,
        ) = key
        sorted_rows = sorted(rows, key=lambda row: _sdr_sort_value(row["separator_sdr_label"]))
        finite_sdrs = [
            float(row["separator_sdr_label"])
            for row in sorted_rows
            if str(row["separator_sdr_label"]) != "inf"
        ]
        max_finite_sdr = max(finite_sdrs) if finite_sdrs else float("nan")
        acceptable = [
            row
            for row in sorted_rows
            if float(row["tir_retention_fraction_mean"]) >= retention
            and -float(row[si_sdr_field]) <= max_si_sdr_loss_db
        ]
        selected = acceptable[0] if acceptable else None
        best = sorted_rows[-1]
        selected_sdr_label = _requirement_label(selected, max_finite_sdr) if selected else "not_met"
        requirements.append(
            {
                "trajectory": trajectory,
                "angular_velocity_deg_s": velocity,
                "sigma_deg": sigma,
                "orientation_delay_ms": orientation_delay,
                "source_estimate_delay_ms": source_delay,
                "source_delay_angular_lag_deg": source_delay_lag,
                "tir_retention_threshold": retention,
                "si_sdr_loss_metric": si_sdr_metric,
                "max_si_sdr_loss_db": max_si_sdr_loss_db,
                "minimum_separator_sdr_db": selected_sdr_label,
                "minimum_separator_sdr_label": selected_sdr_label,
                "acceptable": selected is not None,
                "tir_retention_fraction_mean": selected["tir_retention_fraction_mean"]
                if selected
                else best["tir_retention_fraction_mean"],
                "tir_loss_vs_ideal_db_mean": selected["tir_loss_vs_ideal_db_mean"]
                if selected
                else best["tir_loss_vs_ideal_db_mean"],
                "si_sdr_loss_vs_ideal_db_mean": selected["si_sdr_loss_vs_ideal_db_mean"]
                if selected
                else best["si_sdr_loss_vs_ideal_db_mean"],
                "component_si_sdr_loss_vs_ideal_db_mean": selected[
                    "component_si_sdr_loss_vs_ideal_db_mean"
                ]
                if selected
                else best["component_si_sdr_loss_vs_ideal_db_mean"],
            }
        )
    return requirements


def write_separator_figures(
    summary_rows: list[dict],
    requirement_rows: list[dict],
    source_delay_plot_rows: list[dict],
    config: dict,
    heatmap_png: Path,
    heatmap_svg: Path,
    envelope_png: Path,
    envelope_svg: Path,
    source_delay_png: Path,
    source_delay_svg: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _configure_separator_plot_style(plt)

    representative_sigma = float(config.get("figures", {}).get("representative_sigma_deg", 20.0))
    representative_orientation_delay = float(config.get("figures", {}).get("representative_orientation_delay_ms", 0.0))
    representative_source_delay = float(config.get("figures", {}).get("representative_source_delay_ms", 0.0))
    velocities = sorted({float(row["angular_velocity_deg_s"]) for row in summary_rows})
    sdr_labels = sorted(
        {str(row["separator_sdr_label"]) for row in summary_rows},
        key=_sdr_sort_value,
    )
    sigmas = sorted({float(row["sigma_deg"]) for row in summary_rows})
    selected_rows = [
        row
        for row in summary_rows
        if float(row["source_estimate_delay_ms"]) == representative_source_delay
        and float(row["orientation_delay_ms"]) == representative_orientation_delay
    ]
    vmax = max(0.1, max(-float(row["tir_loss_vs_ideal_db_mean"]) for row in selected_rows))
    fig, axes = plt.subplots(1, len(velocities), figsize=(12.0, 4.0), constrained_layout=True)
    if len(velocities) == 1:
        axes = np.asarray([axes])
    image = None
    for index, velocity in enumerate(velocities):
        grid = np.full((len(sigmas), len(sdr_labels)), np.nan)
        for row in selected_rows:
            if float(row["angular_velocity_deg_s"]) != velocity:
                continue
            i = sigmas.index(float(row["sigma_deg"]))
            j = sdr_labels.index(str(row["separator_sdr_label"]))
            grid[i, j] = max(0.0, -float(row["tir_loss_vs_ideal_db_mean"]))
        ax = axes[index]
        image = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis", vmin=0.0, vmax=vmax)
        ax.set_title(f"{velocity:.0f} deg/s")
        ax.set_xticks(range(len(sdr_labels)), [_display_sdr_label(label) for label in sdr_labels])
        ax.set_yticks(range(len(sigmas)), [f"{sigma:.0f}" for sigma in sigmas])
        ax.set_xlabel("separator SDR (dB)")
        if index == 0:
            ax.set_ylabel("sigma (deg)")
    fig.suptitle(
        f"TIR loss from separator leakage, source delay={representative_source_delay:.0f} ms",
    )
    cbar = fig.colorbar(image, ax=list(axes), shrink=0.86)
    cbar.set_label("TIR loss vs ideal/no-leakage separator (dB)")
    fig.savefig(heatmap_png)
    fig.savefig(heatmap_svg)
    plt.close(fig)

    fig, axes = plt.subplots(1, len(velocities), figsize=(12.0, 4.0), constrained_layout=True)
    if len(velocities) == 1:
        axes = np.asarray([axes])
    x_positions = np.arange(len(sdr_labels), dtype=float)
    for index, velocity in enumerate(velocities):
        ax = axes[index]
        rows = [
            row
            for row in selected_rows
            if float(row["angular_velocity_deg_s"]) == velocity
        ]
        for sigma in sigmas:
            sigma_rows = sorted(
                [row for row in rows if float(row["sigma_deg"]) == sigma],
                key=lambda row: _sdr_sort_value(str(row["separator_sdr_label"])),
            )
            y = [min(max(float(row["tir_retention_fraction_mean"]), 0.0), 1.05) for row in sigma_rows]
            ax.plot(
                x_positions,
                y,
                marker="o",
                linewidth=1.7,
                markersize=3.4,
                label=f"{sigma:.0f} deg",
            )
        ax.axhline(0.90, color="#333333", linestyle="--", linewidth=1.0)
        ax.set_title(f"{velocity:.0f} deg/s")
        ax.set_xticks(x_positions, [_display_sdr_label(label) for label in sdr_labels])
        ax.set_ylim(0.0, 1.05)
        ax.set_xlabel("separator SDR (dB)")
        if index == 0:
            ax.set_ylabel("fraction of ideal Delta TIR retained")
        if index == len(velocities) - 1:
            ax.legend(title="sigma", frameon=False, fontsize=8)
    fig.suptitle("Fraction of ideal Delta TIR retained as separation improves")
    fig.savefig(envelope_png)
    fig.savefig(envelope_svg)
    plt.close(fig)

    source_delay_rows = source_delay_plot_rows or summary_rows
    source_delays = sorted({float(row["source_estimate_delay_ms"]) for row in source_delay_rows})
    representative_rows = [
        row
        for row in source_delay_rows
        if float(row["sigma_deg"]) == representative_sigma
        and float(row["orientation_delay_ms"]) == representative_orientation_delay
    ]
    if representative_rows and "stoi_loss_vs_ideal_output_mean" in representative_rows[0]:
        fig, axes = plt.subplots(1, len(velocities), figsize=(12.0, 3.8), constrained_layout=True)
        if len(velocities) == 1:
            axes = np.asarray([axes])
        plotted_stoi_losses: list[float] = []
        for column, velocity in enumerate(velocities):
            ax = axes[column]
            rows = [
                row
                for row in representative_rows
                if float(row["angular_velocity_deg_s"]) == velocity
            ]
            for sdr_label in sdr_labels:
                sdr_rows = sorted(
                    [row for row in rows if str(row["separator_sdr_label"]) == sdr_label],
                    key=lambda row: float(row["source_estimate_delay_ms"]),
                )
                if not sdr_rows:
                    continue
                x = [float(row["source_estimate_delay_ms"]) for row in sdr_rows]
                stoi_y = [max(0.0, float(row["stoi_loss_vs_ideal_output_mean"])) for row in sdr_rows]
                plotted_stoi_losses.extend(stoi_y)
                label = _display_sdr_label(sdr_label)
                ax.plot(
                    x,
                    stoi_y,
                    marker="o",
                    linewidth=1.7,
                    markersize=3.4,
                    label=label,
                )
            ax.set_title(f"{velocity:.0f} deg/s")
            ax.axhline(0.0, color="#555555", linestyle=":", linewidth=0.9)
            ax.set_xlabel("source-estimate delay (ms)")
            ax.set_xticks(source_delays, [f"{delay:.0f}" for delay in source_delays])
            ax.set_xlim(min(source_delays), max(source_delays))
            if column == 0:
                ax.set_ylabel("STOI loss vs ideal output")
            if column == len(velocities) - 1:
                ax.legend(title="separator SDR (dB)", frameon=False, fontsize=8)
        stoi_ymax = max(0.02, max(plotted_stoi_losses) * 1.12)
        for column in range(len(velocities)):
            axes[column].set_ylim(0.0, stoi_ymax)
        fig.suptitle(
            f"STOI degradation vs ideal source-overlay output, sigma={representative_sigma:.0f} deg",
        )
    else:
        main_source_delays = sorted(float(value) for value in config["source_estimate_delay_ms"])
        zoom_max_ms = float(config.get("figures", {}).get("source_delay_zoom_max_ms", 20.0))
        fig, axes = plt.subplots(2, len(velocities), figsize=(12.0, 6.1), constrained_layout=True)
        if len(velocities) == 1:
            axes = np.asarray(axes).reshape(2, 1)
        plotted_si_sdr_losses_full: list[float] = []
        plotted_si_sdr_losses_zoom: list[float] = []
        for column, velocity in enumerate(velocities):
            rows = [
                row
                for row in representative_rows
                if float(row["angular_velocity_deg_s"]) == velocity
            ]
            delay_baseline = {
                str(row["separator_sdr_label"]): {
                    "si_sdr": max(0.0, -float(row["si_sdr_loss_vs_ideal_db_mean"])),
                }
                for row in rows
                if float(row["source_estimate_delay_ms"]) == 0.0
            }
            for sdr_label in sdr_labels:
                sdr_rows = sorted(
                    [row for row in rows if str(row["separator_sdr_label"]) == sdr_label],
                    key=lambda row: float(row["source_estimate_delay_ms"]),
                )
                if not sdr_rows:
                    continue
                x = [float(row["source_estimate_delay_ms"]) for row in sdr_rows]
                baseline = delay_baseline[str(sdr_label)]
                physical_si_sdr_loss = [
                    max(0.0, max(0.0, -float(row["si_sdr_loss_vs_ideal_db_mean"])) - baseline["si_sdr"])
                    for row in sdr_rows
                ]
                full_pairs = [
                    (delay, loss)
                    for delay, loss in zip(x, physical_si_sdr_loss)
                    if delay in main_source_delays
                ]
                zoom_pairs = [
                    (delay, loss)
                    for delay, loss in zip(x, physical_si_sdr_loss)
                    if delay <= zoom_max_ms
                ]
                full_x = [item[0] for item in full_pairs]
                full_loss = [item[1] for item in full_pairs]
                zoom_x = [item[0] for item in zoom_pairs]
                zoom_loss = [item[1] for item in zoom_pairs]
                plotted_si_sdr_losses_full.extend(full_loss)
                plotted_si_sdr_losses_zoom.extend(zoom_loss)
                label = _display_sdr_label(sdr_label)
                axes[0, column].plot(
                    full_x,
                    full_loss,
                    marker="o",
                    linewidth=1.6,
                    markersize=3.0,
                    label=label,
                )
                axes[1, column].plot(
                    zoom_x,
                    zoom_loss,
                    marker="o",
                    linewidth=1.6,
                    markersize=3.0,
                    label=label,
                )
            axes[0, column].set_title(f"{velocity:.0f} deg/s")
            axes[0, column].axhline(0.0, color="#555555", linestyle=":", linewidth=0.9)
            for row_index in (0, 1):
                axes[row_index, column].set_xlabel("source-estimate delay (ms)")
            axes[0, column].set_xticks(
                main_source_delays,
                [f"{delay:.0f}" for delay in main_source_delays],
            )
            zoom_delays = [delay for delay in source_delays if delay <= zoom_max_ms]
            axes[1, column].set_xticks(zoom_delays, [f"{delay:.0f}" for delay in zoom_delays])
            if column == 0:
                axes[0, column].set_ylabel("physical SI-SDR loss (dB)")
                axes[1, column].set_ylabel("physical SI-SDR loss (dB)")
            if column == len(velocities) - 1:
                axes[0, column].legend(title="separator SDR (dB)", frameon=False, fontsize=8)
        si_sdr_ymax = max(0.1, max(plotted_si_sdr_losses_full) * 1.08)
        zoom_ymax = max(0.1, max(plotted_si_sdr_losses_zoom) * 1.08)
        for column in range(len(velocities)):
            axes[0, column].set_xlim(min(main_source_delays), max(main_source_delays))
            axes[0, column].set_ylim(0.0, si_sdr_ymax)
            axes[1, column].set_xlim(0.0, zoom_max_ms)
            axes[1, column].set_ylim(0.0, zoom_ymax)
        fig.suptitle(
            f"Physical SI-SDR loss from source-estimate delay, sigma={representative_sigma:.0f} deg",
        )
    fig.savefig(source_delay_png)
    fig.savefig(source_delay_svg)
    plt.close(fig)


def _configure_separator_plot_style(plt) -> None:
    try:
        import seaborn as sns

        sns.set_theme(context="paper", style="whitegrid", font="DejaVu Sans")
    except ImportError:
        try:
            plt.style.use("seaborn-v0_8-whitegrid")
        except OSError:
            plt.style.use("default")
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.6,
            "axes.titlesize": 9.6,
            "axes.labelsize": 8.8,
            "xtick.labelsize": 8.0,
            "ytick.labelsize": 8.0,
            "legend.fontsize": 7.6,
            "legend.title_fontsize": 7.8,
            "figure.titlesize": 12.0,
            "figure.dpi": 140,
            "savefig.dpi": 300,
            "axes.linewidth": 0.8,
            "grid.linewidth": 0.55,
            "svg.fonttype": "none",
        }
    )


def _summary_markdown(
    summary: dict,
    summary_rows: list[dict],
    requirement_rows: list[dict],
    config: dict,
) -> str:
    representative_sigma = float(config.get("figures", {}).get("representative_sigma_deg", 20.0))
    representative_orientation_delay = float(config.get("figures", {}).get("representative_orientation_delay_ms", 0.0))
    zero_rows = [
        row
        for row in summary_rows
        if float(row["source_estimate_delay_ms"]) == 0.0
        and float(row["orientation_delay_ms"]) == 0.0
        and str(row["separator_sdr_label"]) == "inf"
    ]
    zero_rows = sorted(
        zero_rows,
        key=lambda row: (float(row["angular_velocity_deg_s"]), float(row["sigma_deg"])),
    )
    worst_rows = sorted(summary_rows, key=lambda row: float(row["tir_loss_vs_ideal_db_mean"]))[:10]
    lines = [
        "# Experiment 5 Source Separator Requirements",
        "",
        "This experiment uses the same measured mic-corrected BRIRs, 100 LibriSpeech pairs, source geometry and dynamic yaw trajectories used by Experiment 4.",
        "",
        "The attention model remains monophonic: each source receives one scalar gain. Separator imperfections are emulated after binaural source-image synthesis by adding delayed cross-source leakage to the per-source estimates.",
        "",
        "Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is not used.",
        "",
        "## Outputs",
        "",
        f"- Detailed rows: `{summary['processed_csv']}`",
        f"- Condition summary: `{summary['summary_csv']}`",
        f"- Requirement table: `{summary['requirements_csv']}`",
        f"- Separator-degradation heatmap: `{summary['figures']['separator_heatmaps_png']}`",
        f"- TIR-retention curves: `{summary['figures']['requirement_envelope_png']}`",
        f"- Source-delay impact figure: `{summary['figures']['source_delay_impact_png']}`",
        "",
        "## Dataset",
        "",
        f"- Speech pairs: {summary['speech_pair_count']}",
        "- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`",
        "- The default configuration uses the same deterministic 100 non-overlapping pairs as Experiment 4.",
        "",
        "## Separator Model",
        "",
        "`xhat_a = delay(x_a) + kappa * delay(x_b)`",
        "",
        "`xhat_b = delay(x_b) + kappa * delay(x_a)`",
        "",
        "`kappa = 10 ** (-separator_sdr_db / 20)` for finite SDR values. `separator_sdr_db = inf` gives `kappa = 0`, meaning the ideal no-leakage separator. It is not a finite SDR greater than 20 dB.",
        "",
        "The detailed CSV preserves target and interference components through TIR and SI-SDR metrics. `source_estimate_delay_ms` is the separator-output delay axis. The source-delay figure uses STOI to compare a degraded source-overlay output against the ideal zero-delay, no-leakage source-overlay output.",
        "",
        "## Ideal Separator Baseline",
        "",
        "| Velocity (deg/s) | Sigma (deg) | TIR improvement (dB), mean +/- SD | Physical SI-SDR improvement (dB), mean +/- SD |",
        "|---:|---:|---:|---:|",
    ]
    for row in zero_rows:
        lines.append(
            f"| {row['angular_velocity_deg_s']:.0f} | {row['sigma_deg']:.0f} | "
            f"{_fmt(row['tir_improvement_db_mean'])} +/- {_fmt(row['tir_improvement_db_sd'])} | "
            f"{_fmt(row['si_sdr_physical_improvement_db_mean'])} +/- {_fmt(row['si_sdr_physical_improvement_db_sd'])} |"
        )
    lines.extend(
        [
            "",
            "## Representative TIR Loss Matrices",
            "",
            f"Mean dB loss relative to the ideal zero-delay, no-leakage separator, for `sigma={representative_sigma:.0f} deg` and `orientation_delay_ms={representative_orientation_delay:.0f}`.",
            "",
        ]
    )
    lines.extend(
        _separator_matrix_sections(
            summary_rows,
            sigma=representative_sigma,
            orientation_delay=representative_orientation_delay,
            field="tir_loss_vs_ideal_db_mean",
            invert_sign=True,
        )
    )
    lines.extend(
        [
            "",
            "## Requirement Envelope",
            "",
            "The table reports the lowest separator SDR that satisfies both criteria for each condition:",
            "",
            f"- TIR retention >= {float(config.get('requirements', {}).get('tir_retention_fraction', 0.90)):.2f} of the ideal condition, where `tir_retention_fraction = condition Delta TIR / ideal Delta TIR`;",
            f"- component SI-SDR loss <= {float(config.get('requirements', {}).get('max_component_si_sdr_loss_db', 1.0)):.2f} dB relative to the ideal condition.",
            "",
        ]
    )
    lines.extend(_requirement_sections(requirement_rows, representative_orientation_delay))
    lines.extend(
        [
            "",
            "## Largest Losses",
            "",
            "| Velocity (deg/s) | Sigma (deg) | Source delay (ms) | Separator SDR (dB) | Leakage | TIR loss (dB) | SI-SDR loss (dB) |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in worst_rows:
        lines.append(
            f"| {row['angular_velocity_deg_s']:.0f} | {row['sigma_deg']:.0f} | "
            f"{row['source_estimate_delay_ms']:.0f} | {_display_sdr_label(row['separator_sdr_label'])} | "
            f"{_fmt(row['leakage_linear'])} | {_fmt(-row['tir_loss_vs_ideal_db_mean'])} | "
            f"{_fmt(-row['si_sdr_loss_vs_ideal_db_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Experiment 4 isolates delayed orientation control. Experiment 5 isolates separator-output delay and leakage by default, with `orientation_delay_ms = 0`.",
            "- The main degradation axis in this experiment is separator SDR, not source-estimate delay. A common delay applied to both source estimates changes absolute timing, but it has little effect on TIR because target and interference are delayed together.",
        "- Increasing leakage raises the residual contribution of the non-target source inside each separated estimate.",
            "- Increasing source-estimate delay shifts the separator reinforcement relative to the live binaural scene.",
            "- The source-delay impact figure uses an overlay model: `output = live_scene + (gain - 1) * separated_estimate`, and compares each condition against the ideal zero-delay, no-leakage overlay using STOI.",
            "- TIR is intentionally not used in the source-delay panel because a common delay applied to both target and interference estimates can make finite-window TIR changes small and hard to interpret.",
            "- The requirement envelope is conservative because a condition must satisfy both TIR retention and component SI-SDR loss.",
        ]
    )
    return "\n".join(lines)


def _separator_matrix_sections(
    rows: list[dict],
    *,
    sigma: float,
    orientation_delay: float,
    field: str,
    invert_sign: bool,
) -> list[str]:
    selected = [
        row
        for row in rows
        if float(row["sigma_deg"]) == sigma and float(row["orientation_delay_ms"]) == orientation_delay
    ]
    velocities = sorted({float(row["angular_velocity_deg_s"]) for row in selected})
    source_delays = sorted({float(row["source_estimate_delay_ms"]) for row in selected})
    sdr_labels = sorted({str(row["separator_sdr_label"]) for row in selected}, key=_sdr_sort_value)
    by_key = {
        (
            float(row["angular_velocity_deg_s"]),
            str(row["separator_sdr_label"]),
            float(row["source_estimate_delay_ms"]),
        ): row
        for row in selected
    }
    lines: list[str] = []
    for velocity in velocities:
        lines.extend(
            [
                f"### {velocity:.0f} deg/s",
                "",
                "| Separator SDR (dB) | "
                + " | ".join(f"{delay:.0f} ms" for delay in source_delays)
                + " |",
                "|---:|" + "|".join("---:" for _ in source_delays) + "|",
            ]
        )
        for sdr_label in sdr_labels:
            values = []
            for delay in source_delays:
                value = float(by_key[(velocity, sdr_label, delay)][field])
                if invert_sign:
                    value = -value
                    value = max(0.0, value)
                values.append(_fmt(value))
            lines.append(f"| {_display_sdr_label(sdr_label)} | " + " | ".join(values) + " |")
        lines.append("")
    return lines


def _requirement_sections(rows: list[dict], orientation_delay: float) -> list[str]:
    selected = [row for row in rows if float(row["orientation_delay_ms"]) == orientation_delay]
    velocities = sorted({float(row["angular_velocity_deg_s"]) for row in selected})
    source_delays = sorted({float(row["source_estimate_delay_ms"]) for row in selected})
    sigmas = sorted({float(row["sigma_deg"]) for row in selected})
    by_key = {
        (
            float(row["angular_velocity_deg_s"]),
            float(row["sigma_deg"]),
            float(row["source_estimate_delay_ms"]),
        ): row
        for row in selected
    }
    lines: list[str] = []
    for velocity in velocities:
        lines.extend(
            [
                f"### {velocity:.0f} deg/s",
                "",
                "| Sigma (deg) | " + " | ".join(f"{delay:.0f} ms" for delay in source_delays) + " |",
                "|---:|" + "|".join("---:" for _ in source_delays) + "|",
            ]
        )
        for sigma in sigmas:
            labels = []
            for delay in source_delays:
                row = by_key[(velocity, sigma, delay)]
                labels.append(_display_sdr_label(str(row["minimum_separator_sdr_label"])))
            lines.append(f"| {sigma:.0f} | " + " | ".join(labels) + " |")
        lines.append("")
    return lines


def _summary_sort_key(item: tuple) -> tuple:
    key = item[0]
    _, velocity, sigma, orientation_delay, source_delay, _, sdr_label, *_ = key
    return (
        float(velocity),
        float(sigma),
        float(orientation_delay),
        float(source_delay),
        _sdr_sort_value(str(sdr_label)),
    )


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
        raise FileExistsError(f"refusing to overwrite existing Experiment 5 outputs:\n{sample}")


def _stats_for(values: list[float]) -> dict[str, float]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {"mean": float("nan"), "sd": float("nan"), "median": float("nan")}
    return {
        "mean": float(mean(clean)),
        "sd": float(pstdev(clean) if len(clean) > 1 else 0.0),
        "median": float(median(clean)),
    }


def _safe_ratio(numerator: float, denominator: float) -> float:
    if abs(float(denominator)) < 1e-9:
        return float("nan")
    return float(numerator) / float(denominator)


def _sdr_value(value: float | str) -> float | str:
    if isinstance(value, str) and value.lower() in {"inf", "infinity"}:
        return "inf"
    numeric = float(value)
    if math.isinf(numeric):
        return "inf"
    return numeric


def _sdr_label(value: float | str) -> str:
    if isinstance(value, str) and value.lower() in {"inf", "infinity"}:
        return "inf"
    numeric = float(value)
    if math.isinf(numeric):
        return "inf"
    return f"{numeric:g}"


def _sdr_sort_value(label: str) -> float:
    return float("inf") if str(label) in {"inf", "ideal"} else float(label)


def _display_sdr_label(label: str) -> str:
    return "inf" if str(label) in {"inf", "ideal"} else str(label)


def _requirement_plot_value(label: str) -> float:
    if label == "not_met":
        return 30.0
    if label.startswith(">"):
        return min(float(label[1:]) + 5.0, 25.0)
    if label in {"inf", "ideal"}:
        return 20.0
    return float(label)


def _requirement_label(row: dict | None, max_finite_sdr: float) -> str:
    if row is None:
        return "not_met"
    label = str(row["separator_sdr_label"])
    return label


def _fmt(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    numeric = float(value)
    if abs(numeric) < 0.005:
        numeric = 0.0
    return f"{numeric:.2f}"
