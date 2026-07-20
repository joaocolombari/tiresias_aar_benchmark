from __future__ import annotations

import csv
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev

import numpy as np

from tiresias_benchmark.metrics.audio import si_sdr_db, tir_db, tir_improvement_db
from tiresias_benchmark.telemetry.replay import delayed_yaw_series


@dataclass(frozen=True)
class SpeechItem:
    sample_id: str
    path: Path
    speaker_id: str
    original_relative_path: str


@dataclass(frozen=True)
class SpeechPair:
    pair_id: str
    source_a: SpeechItem
    source_b: SpeechItem


@dataclass(frozen=True)
class Trajectory:
    name: str
    velocity_deg_s: float
    time_s: np.ndarray
    yaw_deg: np.ndarray
    switch_time_s: float
    rotation_start_s: float
    rotation_end_s: float


def run(config: dict) -> dict:
    outputs = config.get("outputs", {})
    processed_dir = Path(outputs.get("processed_dir", "experiments/exp04_latency_sensitivity/processed"))
    metrics_dir = Path(outputs.get("metrics_dir", "experiments/exp04_latency_sensitivity/metrics"))
    figures_dir = Path(outputs.get("figures_dir", "experiments/exp04_latency_sensitivity/figures"))
    overwrite = bool(outputs.get("overwrite", config.get("overwrite", False)))
    processed_csv = processed_dir / "exp04_latency_results.csv"
    summary_csv = metrics_dir / "exp04_latency_summary_by_condition.csv"
    summary_json = metrics_dir / "exp04_latency_summary.json"
    summary_md = metrics_dir / "exp04_latency_summary.md"
    heatmap_png = figures_dir / "exp04_latency_heatmaps.png"
    heatmap_svg = figures_dir / "exp04_latency_heatmaps.svg"
    trace_png = figures_dir / "exp04_gain_transition_traces.png"
    trace_svg = figures_dir / "exp04_gain_transition_traces.svg"
    _ensure_can_write(
        [processed_csv, summary_csv, summary_json, summary_md, heatmap_png, heatmap_svg, trace_png, trace_svg],
        overwrite=overwrite,
    )
    processed_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)

    speech_pairs = select_speech_pairs(config)
    brir_bank = load_brir_bank(config)
    rows, trace_rows = run_latency_grid(config, speech_pairs, brir_bank)
    summary_rows = summarize_latency_rows(rows)
    summary = {
        "experiment_id": config.get("experiment_id", "exp04_latency_sensitivity"),
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
            "latency_heatmaps_png": str(heatmap_png),
            "latency_heatmaps_svg": str(heatmap_svg),
            "gain_transition_traces_png": str(trace_png),
            "gain_transition_traces_svg": str(trace_svg),
        },
    }

    _write_csv(processed_csv, rows)
    _write_csv(summary_csv, summary_rows)
    summary_json.write_text(json.dumps(summary | {"condition_summary": summary_rows}, indent=2) + "\n")
    summary_md.write_text(_summary_markdown(summary, summary_rows) + "\n")
    write_latency_figures(summary_rows, trace_rows, heatmap_png, heatmap_svg, trace_png, trace_svg)
    return summary


def select_speech_pairs(config: dict) -> list[SpeechPair]:
    dataset = config["speech_dataset"]
    root = Path(dataset["root"])
    manifest_path = root / dataset.get("manifest", "manifest.csv")
    if not manifest_path.exists():
        raise FileNotFoundError(f"LibriSpeech subset manifest not found: {manifest_path}")
    with manifest_path.open(encoding="utf-8-sig", newline="") as file:
        items = [
            SpeechItem(
                sample_id=row["sample_id"],
                path=root / row["archive_path"],
                speaker_id=row.get("speaker_id", ""),
                original_relative_path=row.get("original_relative_path", ""),
            )
            for row in csv.DictReader(file)
        ]
    count = int(dataset.get("pair_count", 10))
    seed = int(dataset.get("pair_seed", 20260720))
    rng = random.Random(seed)
    rng.shuffle(items)
    pairs: list[SpeechPair] = []
    used: set[str] = set()
    for left in items:
        if left.sample_id in used:
            continue
        right = next(
            (
                item
                for item in items
                if item.sample_id not in used
                and item.sample_id != left.sample_id
                and item.speaker_id != left.speaker_id
            ),
            None,
        )
        if right is None:
            continue
        used.add(left.sample_id)
        used.add(right.sample_id)
        pairs.append(SpeechPair(pair_id=f"pair_{len(pairs) + 1:02d}", source_a=left, source_b=right))
        if len(pairs) >= count:
            break
    if len(pairs) < count:
        raise ValueError(f"could only create {len(pairs)} speech pairs from {manifest_path}")
    return pairs


def load_brir_bank(config: dict) -> dict[str, dict[int, np.ndarray]]:
    import soundfile as sf

    brir = config["brir"]
    root = Path(brir["root"])
    repetitions = [int(value) for value in brir.get("repetitions", [1, 2])]
    angles = [int(value) for value in brir.get("angles_deg", list(range(0, 360, 10)))]
    bank: dict[str, dict[int, np.ndarray]] = {"A": {}, "B": {}}
    sample_rates: set[int] = set()
    for speaker in ("A", "B"):
        for angle in angles:
            responses = []
            for repetition in repetitions:
                path = root / f"brir_theta_{angle:03d}_spk_{speaker}_rep{repetition:02d}_stereo.wav"
                if not path.exists():
                    raise FileNotFoundError(f"missing BRIR file: {path}")
                data, sample_rate = sf.read(path, dtype="float32", always_2d=True)
                sample_rates.add(int(sample_rate))
                responses.append(data[:, :2])
            bank[speaker][angle] = np.mean(np.stack(responses, axis=0), axis=0).astype(np.float32)
    if len(sample_rates) != 1:
        raise ValueError(f"BRIR sample rates differ: {sorted(sample_rates)}")
    bank["_sample_rate_hz"] = {"value": np.asarray([sample_rates.pop()], dtype=np.int32)}
    return bank


def run_latency_grid(
    config: dict,
    speech_pairs: list[SpeechPair],
    brir_bank: dict[str, dict[int, np.ndarray]],
) -> tuple[list[dict], list[dict]]:
    import soundfile as sf
    from scipy.signal import fftconvolve, resample_poly

    sample_rate = int(brir_bank["_sample_rate_hz"]["value"][0])
    sources = {item["name"]: float(item["azimuth_deg"]) for item in config["sources"]}
    source_a_angle = sources.get("source_a", -30.0)
    source_b_angle = sources.get("source_b", 30.0)
    duration_s = float(config.get("speech_duration_s", 6.0))
    target_samples = int(round(duration_s * sample_rate))
    control_rate = float(config.get("control_sample_rate_hz", 100.0))
    bmax_db = float(config.get("bmax_db", 10.0))
    post_window_s = float(config.get("post_switch_analysis_window_s", 1.0))
    rows: list[dict] = []
    trace_rows: list[dict] = []

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
                ideal_metrics = component_metrics(
                    acoustic_a,
                    acoustic_b,
                    ideal_gain_a_audio,
                    ideal_gain_b_audio,
                    sample_rate,
                    trajectory.switch_time_s,
                    post_window_s,
                )
                ideal_ratio_db = ideal_gain_b_db - ideal_gain_a_db
                ideal_transition_ms = transition_time_ms(
                    trajectory.time_s,
                    ideal_ratio_db,
                    trajectory.switch_time_s,
                )
                for delay_ms in config["orientation_delay_ms"]:
                    delay_f = float(delay_ms)
                    delayed_yaw = delayed_yaw_series(
                        trajectory.time_s,
                        trajectory.yaw_deg,
                        delay_f,
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
                    metrics = component_metrics(
                        acoustic_a,
                        acoustic_b,
                        gain_a_audio,
                        gain_b_audio,
                        sample_rate,
                        trajectory.switch_time_s,
                        post_window_s,
                    )
                    gain_error = np.concatenate(
                        [gain_a_db - ideal_gain_a_db, gain_b_db - ideal_gain_b_db]
                    )
                    ratio_db = gain_b_db - gain_a_db
                    delayed_transition_ms = transition_time_ms(
                        trajectory.time_s,
                        ratio_db,
                        trajectory.switch_time_s,
                    )
                    rows.append(
                        {
                            "pair_id": pair.pair_id,
                            "source_a_sample_id": pair.source_a.sample_id,
                            "source_b_sample_id": pair.source_b.sample_id,
                            "trajectory": trajectory.name,
                            "angular_velocity_deg_s": trajectory.velocity_deg_s,
                            "sigma_deg": sigma_f,
                            "orientation_delay_ms": delay_f,
                            "angular_velocity_delay_deg": trajectory.velocity_deg_s * delay_f / 1000.0,
                            "tir_improvement_db": metrics["tir_improvement_db"],
                            "tir_loss_vs_zero_delay_db": metrics["tir_improvement_db"]
                            - ideal_metrics["tir_improvement_db"],
                            "si_sdr_improvement_db": metrics["si_sdr_db"] - ideal_metrics["input_si_sdr_db"],
                            "si_sdr_loss_vs_zero_delay_db": metrics["si_sdr_db"]
                            - ideal_metrics["si_sdr_db"],
                            "gain_error_rms_db": float(np.sqrt(np.mean(gain_error**2))),
                            "gain_error_peak_abs_db": float(np.max(np.abs(gain_error))),
                            "transition_time_ms": delayed_transition_ms,
                            "transition_delay_vs_zero_ms": delayed_transition_ms - ideal_transition_ms,
                            "ideal_tir_improvement_db": ideal_metrics["tir_improvement_db"],
                            "input_tir_db": metrics["input_tir_db"],
                            "output_tir_db": metrics["output_tir_db"],
                            "input_si_sdr_db": metrics["input_si_sdr_db"],
                            "output_si_sdr_db": metrics["si_sdr_db"],
                        }
                    )
                    if (
                        pair == speech_pairs[0]
                        and sigma_f == float(config.get("trace_sigma_deg", 20.0))
                        and trajectory.velocity_deg_s
                        == float(config.get("trace_velocity_deg_s", max(config["angular_velocity_deg_s"])))
                        and delay_f in {float(item) for item in config.get("trace_delay_ms", [0, 80, 160, 200])}
                    ):
                        for time_s, ratio in zip(trajectory.time_s, ratio_db):
                            trace_rows.append(
                                {
                                    "time_from_switch_s": float(time_s - trajectory.switch_time_s),
                                    "orientation_delay_ms": delay_f,
                                    "gain_ratio_b_over_a_db": float(ratio),
                                    "sigma_deg": sigma_f,
                                    "angular_velocity_deg_s": trajectory.velocity_deg_s,
                                }
                            )
    return rows, trace_rows


def prepare_mono_speech(signal: np.ndarray, input_rate: int, output_rate: int, samples: int, resample_poly) -> np.ndarray:
    values = np.asarray(signal, dtype=np.float32)
    if values.ndim > 1:
        values = np.mean(values, axis=1)
    if int(input_rate) != int(output_rate):
        gcd = math.gcd(int(input_rate), int(output_rate))
        values = resample_poly(values, int(output_rate) // gcd, int(input_rate) // gcd).astype(np.float32)
    values = values - float(np.mean(values))
    rms = float(np.sqrt(np.mean(values.astype(np.float64) ** 2)))
    if rms > 0:
        values = values / rms
    if len(values) < samples:
        values = np.pad(values, (0, samples - len(values)))
    else:
        values = values[:samples]
    return values.astype(np.float32)


def convolve_speech_with_brir_bank(speech: np.ndarray, bank: dict[int, np.ndarray], samples: int, fftconvolve) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    for angle, ir in bank.items():
        left = fftconvolve(speech, ir[:, 0], mode="full")[:samples]
        right = fftconvolve(speech, ir[:, 1], mode="full")[:samples]
        out[int(angle)] = np.column_stack([left, right]).astype(np.float32)
    return out


def interpolate_brir_images(convolved_by_angle: dict[int, np.ndarray], yaw_deg: np.ndarray) -> np.ndarray:
    angles = sorted(convolved_by_angle)
    step = angles[1] - angles[0]
    normalized = np.mod(yaw_deg, 360.0)
    lower = (np.floor(normalized / step).astype(int) * step) % 360
    upper = (lower + step) % 360
    weight = (normalized - lower) / step
    weight = np.where(weight < 0, weight + 360.0 / step, weight)
    output = np.zeros_like(next(iter(convolved_by_angle.values())))
    for low_angle in angles:
        mask = lower == low_angle
        if not np.any(mask):
            continue
        high_angle = (low_angle + step) % 360
        w = weight[mask, None]
        output[mask] = (1.0 - w) * convolved_by_angle[low_angle][mask] + w * convolved_by_angle[high_angle][mask]
    return output.astype(np.float32)


def build_trajectories(config: dict) -> list[Trajectory]:
    control_rate = float(config.get("control_sample_rate_hz", 100.0))
    hold_before = float(config.get("hold_before_s", 1.0))
    hold_after = float(config.get("hold_after_s", 1.5))
    start = float(config.get("start_yaw_deg", -30.0))
    stop = float(config.get("stop_yaw_deg", 30.0))
    trajectories = []
    for velocity in config["angular_velocity_deg_s"]:
        velocity_f = float(velocity)
        rotation_duration = abs(stop - start) / velocity_f
        duration = hold_before + rotation_duration + hold_after
        time_s = np.arange(int(math.ceil(duration * control_rate)) + 1, dtype=np.float64) / control_rate
        yaw = np.empty_like(time_s)
        for index, time_value in enumerate(time_s):
            if time_value < hold_before:
                yaw[index] = start
            elif time_value > hold_before + rotation_duration:
                yaw[index] = stop
            else:
                progress = (time_value - hold_before) / rotation_duration
                yaw[index] = start + (stop - start) * minimum_jerk(progress)
        switch_index = int(np.argmin(np.abs(yaw)))
        trajectories.append(
            Trajectory(
                name=f"{int(round(velocity_f))}_deg_s",
                velocity_deg_s=velocity_f,
                time_s=time_s,
                yaw_deg=yaw,
                switch_time_s=float(time_s[switch_index]),
                rotation_start_s=hold_before,
                rotation_end_s=hold_before + rotation_duration,
            )
        )
    return trajectories


def minimum_jerk(progress: float) -> float:
    p = min(max(float(progress), 0.0), 1.0)
    return 10.0 * p**3 - 15.0 * p**4 + 6.0 * p**5


def attention_gain_db_series(
    yaw_deg: np.ndarray,
    source_a_angle_deg: float,
    source_b_angle_deg: float,
    sigma_deg: float,
    bmax_db: float,
) -> tuple[np.ndarray, np.ndarray]:
    angle_a = np.abs(circular_difference_deg(source_a_angle_deg, yaw_deg))
    angle_b = np.abs(circular_difference_deg(source_b_angle_deg, yaw_deg))
    gain_a = bmax_db * np.exp(-(angle_a**2) / (2.0 * sigma_deg**2))
    gain_b = bmax_db * np.exp(-(angle_b**2) / (2.0 * sigma_deg**2))
    return gain_a.astype(np.float64), gain_b.astype(np.float64)


def circular_difference_deg(measured_deg: float | np.ndarray, reference_deg: float | np.ndarray) -> np.ndarray:
    return (np.asarray(measured_deg) - np.asarray(reference_deg) + 180.0) % 360.0 - 180.0


def db_to_linear(db: np.ndarray) -> np.ndarray:
    return np.power(10.0, np.asarray(db, dtype=np.float64) / 20.0)


def component_metrics(
    acoustic_a: np.ndarray,
    acoustic_b: np.ndarray,
    gain_a: np.ndarray,
    gain_b: np.ndarray,
    sample_rate_hz: int,
    switch_time_s: float,
    window_s: float,
) -> dict[str, float]:
    start = int(round(switch_time_s * sample_rate_hz))
    stop = min(len(acoustic_a), start + int(round(window_s * sample_rate_hz)))
    if stop <= start:
        raise ValueError("empty post-switch analysis window")
    target_in = acoustic_b[start:stop]
    interferer_in = acoustic_a[start:stop]
    target_out = gain_b[start:stop, None] * target_in
    interferer_out = gain_a[start:stop, None] * interferer_in
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
        "si_sdr_db": float(mean(output_si_sdrs)),
    }


def transition_time_ms(time_s: np.ndarray, gain_ratio_db: np.ndarray, switch_time_s: float) -> float:
    post = time_s >= switch_time_s
    if not np.any(post):
        return float("nan")
    final_ratio = float(np.mean(gain_ratio_db[time_s >= max(time_s[-1] - 0.4, switch_time_s)]))
    threshold = 0.9 * final_ratio
    indices = np.where(post & (gain_ratio_db >= threshold))[0]
    if len(indices) == 0:
        return float("nan")
    return float(1000.0 * (time_s[int(indices[0])] - switch_time_s))


def summarize_latency_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for row in rows:
        key = (
            row["trajectory"],
            row["angular_velocity_deg_s"],
            row["sigma_deg"],
            row["orientation_delay_ms"],
            row["angular_velocity_delay_deg"],
        )
        grouped.setdefault(key, []).append(row)
    summary = []
    fields = [
        "tir_improvement_db",
        "tir_loss_vs_zero_delay_db",
        "si_sdr_improvement_db",
        "si_sdr_loss_vs_zero_delay_db",
        "gain_error_rms_db",
        "gain_error_peak_abs_db",
        "transition_time_ms",
        "transition_delay_vs_zero_ms",
    ]
    for key, values in sorted(grouped.items()):
        trajectory, velocity, sigma, delay, angular_delay = key
        item = {
            "trajectory": trajectory,
            "angular_velocity_deg_s": velocity,
            "sigma_deg": sigma,
            "orientation_delay_ms": delay,
            "angular_velocity_delay_deg": angular_delay,
            "pair_count": len(values),
        }
        for field in fields:
            stats = stats_for([row[field] for row in values])
            item[f"{field}_mean"] = stats["mean"]
            item[f"{field}_sd"] = stats["sd"]
            item[f"{field}_median"] = stats["median"]
        summary.append(item)
    return summary


def stats_for(values: list[float]) -> dict[str, float]:
    clean = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not clean:
        return {"mean": float("nan"), "sd": float("nan"), "median": float("nan")}
    return {
        "mean": float(mean(clean)),
        "sd": float(pstdev(clean) if len(clean) > 1 else 0.0),
        "median": float(median(clean)),
    }


def write_latency_figures(
    summary_rows: list[dict],
    trace_rows: list[dict],
    heatmap_png: Path,
    heatmap_svg: Path,
    trace_png: Path,
    trace_svg: Path,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    velocities = sorted({float(row["angular_velocity_deg_s"]) for row in summary_rows})
    delays = sorted({float(row["orientation_delay_ms"]) for row in summary_rows})
    sigmas = sorted({float(row["sigma_deg"]) for row in summary_rows})
    fig, axes = plt.subplots(2, len(velocities), figsize=(12.0, 6.1), constrained_layout=True)
    if len(velocities) == 1:
        axes = np.asarray(axes).reshape(2, 1)
    tir_vmax = max(0.1, max(-float(row["tir_loss_vs_zero_delay_db_mean"]) for row in summary_rows))
    gain_vmax = max(0.1, max(float(row["gain_error_rms_db_mean"]) for row in summary_rows))
    for column, velocity in enumerate(velocities):
        tir_grid = np.full((len(sigmas), len(delays)), np.nan)
        gain_grid = np.full((len(sigmas), len(delays)), np.nan)
        for row in summary_rows:
            if float(row["angular_velocity_deg_s"]) != velocity:
                continue
            i = sigmas.index(float(row["sigma_deg"]))
            j = delays.index(float(row["orientation_delay_ms"]))
            tir_grid[i, j] = -float(row["tir_loss_vs_zero_delay_db_mean"])
            gain_grid[i, j] = float(row["gain_error_rms_db_mean"])
        tir_ax = axes[0, column]
        gain_ax = axes[1, column]
        tir_image = tir_ax.imshow(tir_grid, origin="lower", aspect="auto", cmap="viridis", vmin=0.0, vmax=tir_vmax)
        gain_image = gain_ax.imshow(gain_grid, origin="lower", aspect="auto", cmap="magma", vmin=0.0, vmax=gain_vmax)
        for ax in (tir_ax, gain_ax):
            ax.set_xticks(range(len(delays)), [f"{d:.0f}" for d in delays])
            ax.set_yticks(range(len(sigmas)), [f"{s:.0f}" for s in sigmas])
            ax.set_xlabel("orientation delay (ms)")
        tir_ax.set_title(f"{velocity:.0f} deg/s", fontsize=11)
        if column == 0:
            tir_ax.set_ylabel("TIR loss\nsigma (deg)")
            gain_ax.set_ylabel("gain error RMS\nsigma (deg)")
    fig.suptitle("Experiment 4 latency sensitivity", fontsize=13, fontweight="bold")
    tir_cbar = fig.colorbar(tir_image, ax=list(axes[0, :]), shrink=0.86)
    tir_cbar.set_label("TIR loss vs zero-delay (dB)")
    gain_cbar = fig.colorbar(gain_image, ax=list(axes[1, :]), shrink=0.86)
    gain_cbar.set_label("gain error RMS (dB)")
    fig.savefig(heatmap_png, dpi=220)
    fig.savefig(heatmap_svg)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.0, 4.0), constrained_layout=True)
    for delay in sorted({float(row["orientation_delay_ms"]) for row in trace_rows}):
        rows = [row for row in trace_rows if float(row["orientation_delay_ms"]) == delay]
        ax.plot(
            [row["time_from_switch_s"] for row in rows],
            [row["gain_ratio_b_over_a_db"] for row in rows],
            linewidth=1.8,
            label=f"{delay:.0f} ms",
        )
    ax.axvline(0.0, color="#333333", linewidth=1.0, linestyle="--")
    ax.axhline(0.0, color="#999999", linewidth=0.8)
    ax.set_xlim(-0.6, 1.4)
    ax.set_xlabel("time from target switch (s)")
    ax.set_ylabel("gain ratio B/A (dB)")
    ax.set_title("Representative gain transition, sigma=20 deg, 120 deg/s", fontsize=12)
    ax.grid(True, color="#dddddd", linewidth=0.7)
    ax.legend(title="delay", frameon=False, ncol=2)
    fig.savefig(trace_png, dpi=220)
    fig.savefig(trace_svg)
    plt.close(fig)


def _summary_markdown(summary: dict, summary_rows: list[dict]) -> str:
    ordered_rows = _ordered_summary_rows(summary_rows)
    zero_rows = [row for row in ordered_rows if float(row["orientation_delay_ms"]) == 0.0]
    worst_rows = sorted(
        [row for row in ordered_rows if float(row["orientation_delay_ms"]) > 0.0],
        key=lambda row: float(row["tir_loss_vs_zero_delay_db_mean"]),
    )[:10]
    lines = [
        "# Experiment 4 Latency Sensitivity",
        "",
        "This experiment uses measured mic-corrected BRIRs from Experiment 2 and offline monophonic LibriSpeech sources. The acoustic scene follows the physical head yaw trajectory, while the Gaussian attention gains use a delayed yaw trajectory.",
        "",
        "Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is no longer used here.",
        "",
        "## Outputs",
        "",
        f"- Detailed rows: `{summary['processed_csv']}`",
        f"- Condition summary: `{summary['summary_csv']}`",
        f"- Heatmap figure: `{summary['figures']['latency_heatmaps_png']}`",
        f"- Transition figure: `{summary['figures']['gain_transition_traces_png']}`",
        "",
        "## Dataset",
        "",
        f"- Speech pairs: {summary['speech_pair_count']}",
        "- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`",
        "- The subset README states that 200 LibriSpeech dev-clean files were selected reproducibly with seed 2026.",
        "- The default configuration uses 100 non-overlapping source pairs from those 200 files.",
        "",
        "## Zero-Delay Baseline",
        "",
        "| Velocity (deg/s) | Sigma (deg) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |",
        "|---:|---:|---:|---:|",
    ]
    for row in zero_rows:
        lines.append(
            f"| {row['angular_velocity_deg_s']:.0f} | {row['sigma_deg']:.0f} | "
            f"{_fmt(row['tir_improvement_db_mean'])} +/- {_fmt(row['tir_improvement_db_sd'])} | "
            f"{_fmt(row['si_sdr_improvement_db_mean'])} +/- {_fmt(row['si_sdr_improvement_db_sd'])} |"
        )
    lines.extend(
        [
            "",
            "## TIR Loss Matrices",
            "",
            "Values are mean dB loss relative to zero-delay control for the same velocity, sigma and speech pair.",
            "",
        ]
    )
    lines.extend(_matrix_sections(ordered_rows, "tir_loss_vs_zero_delay_db_mean", invert_sign=True))
    lines.extend(
        [
            "",
            "## Gain Error RMS Matrices",
            "",
            "Values are mean RMS source-gain error in dB relative to zero-delay control. These matrices isolate the control-model error and are the clearest view of the expected sigma-delay sensitivity.",
            "",
        ]
    )
    lines.extend(_matrix_sections(ordered_rows, "gain_error_rms_db_mean", invert_sign=False))
    lines.extend(
        [
            "",
            "## Largest Latency Losses",
            "",
            "| Velocity (deg/s) | Sigma (deg) | Delay (ms) | Angular lag (deg) | TIR loss (dB) | Gain error RMS (dB) | Transition lag (ms) |",
            "|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in worst_rows:
        lines.append(
            f"| {row['angular_velocity_deg_s']:.0f} | {row['sigma_deg']:.0f} | "
            f"{row['orientation_delay_ms']:.0f} | {row['angular_velocity_delay_deg']:.1f} | "
            f"{_fmt(-row['tir_loss_vs_zero_delay_db_mean'])} | "
            f"{_fmt(row['gain_error_rms_db_mean'])} | "
            f"{_fmt(row['transition_delay_vs_zero_ms_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `tir_loss_vs_zero_delay_db` is computed relative to the same sigma, speech pair and trajectory with zero orientation delay.",
            "- The post-switch window treats source B as the target after the head crosses the midline between the two loudspeakers.",
            "- Delay is applied only to the control yaw used by the attention model; the audio signal itself is not delayed.",
            "- The upper heatmap reports downstream audio impact. The lower heatmap reports gain-control error directly.",
            "- Narrow sigma generally increases gain-control error for a given angular lag, but TIR loss can be non-monotonic because the zero-delay baseline and the post-switch acoustic mixture also depend on sigma.",
        ]
    )
    return "\n".join(lines)


def _ordered_summary_rows(summary_rows: list[dict]) -> list[dict]:
    return sorted(
        summary_rows,
        key=lambda row: (
            float(row["angular_velocity_deg_s"]),
            float(row["sigma_deg"]),
            float(row["orientation_delay_ms"]),
        ),
    )


def _matrix_sections(rows: list[dict], field: str, *, invert_sign: bool) -> list[str]:
    velocities = sorted({float(row["angular_velocity_deg_s"]) for row in rows})
    delays = sorted({float(row["orientation_delay_ms"]) for row in rows})
    sigmas = sorted({float(row["sigma_deg"]) for row in rows})
    by_key = {
        (
            float(row["angular_velocity_deg_s"]),
            float(row["sigma_deg"]),
            float(row["orientation_delay_ms"]),
        ): row
        for row in rows
    }
    lines: list[str] = []
    for velocity in velocities:
        lines.extend(
            [
                f"### {velocity:.0f} deg/s",
                "",
                "| Sigma (deg) | " + " | ".join(f"{delay:.0f} ms" for delay in delays) + " |",
                "|---:|" + "|".join("---:" for _ in delays) + "|",
            ]
        )
        for sigma in sigmas:
            values = []
            for delay in delays:
                row = by_key[(velocity, sigma, delay)]
                value = float(row[field])
                if invert_sign:
                    value = -value
                values.append(_fmt(value))
            lines.append(f"| {sigma:.0f} | " + " | ".join(values) + " |")
        lines.append("")
    return lines


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
        raise FileExistsError(f"refusing to overwrite existing Experiment 4 outputs:\n{sample}")


def _fmt(value: float) -> str:
    if value is None or not math.isfinite(float(value)):
        return "n/a"
    numeric = float(value)
    if abs(numeric) < 0.005:
        numeric = 0.0
    return f"{numeric:.2f}"
