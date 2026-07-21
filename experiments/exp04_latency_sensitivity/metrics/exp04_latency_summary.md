# Experiment 4 Latency Sensitivity

This experiment uses measured mic-corrected BRIRs from Experiment 2 and offline monophonic LibriSpeech sources. The acoustic scene follows the physical head yaw trajectory, while the Gaussian attention gains use a delayed yaw trajectory.

Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is no longer used here.

## Outputs

- Detailed rows: `experiments/exp04_latency_sensitivity/processed/exp04_latency_results.csv`
- Condition summary: `experiments/exp04_latency_sensitivity/metrics/exp04_latency_summary_by_condition.csv`
- Heatmap figure: `experiments/exp04_latency_sensitivity/figures/exp04_latency_heatmaps.png`
- Transition figure: `experiments/exp04_latency_sensitivity/figures/exp04_gain_transition_traces.png`

## Dataset

- Speech pairs: 100
- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`
- The subset README states that 200 LibriSpeech dev-clean files were selected reproducibly with seed 2026.
- The default configuration uses 100 non-overlapping source pairs from those 200 files.

## Zero-Delay Baseline

| Velocity (deg/s) | Sigma (deg) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |
|---:|---:|---:|---:|
| 30 | 10 | 6.60 +/- 2.50 | 6.59 +/- 2.55 |
| 30 | 20 | 7.18 +/- 1.56 | 7.11 +/- 1.81 |
| 30 | 30 | 5.79 +/- 1.23 | 5.75 +/- 1.37 |
| 30 | 45 | 3.69 +/- 0.88 | 3.67 +/- 0.94 |
| 30 | 60 | 2.42 +/- 0.61 | 2.41 +/- 0.64 |
| 60 | 10 | 8.65 +/- 1.44 | 8.63 +/- 1.52 |
| 60 | 20 | 8.75 +/- 0.86 | 8.74 +/- 0.92 |
| 60 | 30 | 7.34 +/- 0.78 | 7.33 +/- 0.82 |
| 60 | 45 | 4.85 +/- 0.61 | 4.85 +/- 0.63 |
| 60 | 60 | 3.22 +/- 0.42 | 3.22 +/- 0.44 |
| 120 | 10 | 9.36 +/- 0.65 | 9.36 +/- 0.66 |
| 120 | 20 | 9.30 +/- 0.43 | 9.31 +/- 0.47 |
| 120 | 30 | 7.93 +/- 0.46 | 7.93 +/- 0.51 |
| 120 | 45 | 5.31 +/- 0.39 | 5.32 +/- 0.43 |
| 120 | 60 | 3.54 +/- 0.27 | 3.55 +/- 0.30 |

## TIR Loss Matrices

Values are mean dB loss relative to zero-delay control for the same velocity, sigma and speech pair.

### 30 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.08 | 0.16 | 0.33 | 0.67 | 1.03 | 1.43 | 1.88 |
| 20 | 0.00 | 0.11 | 0.23 | 0.47 | 0.99 | 1.56 | 2.17 | 2.83 |
| 30 | 0.00 | 0.11 | 0.22 | 0.45 | 0.93 | 1.44 | 1.98 | 2.53 |
| 45 | 0.00 | 0.07 | 0.15 | 0.30 | 0.61 | 0.94 | 1.28 | 1.64 |
| 60 | 0.00 | 0.05 | 0.10 | 0.19 | 0.40 | 0.61 | 0.83 | 1.06 |

### 60 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.07 | 0.14 | 0.28 | 0.60 | 0.98 | 1.49 | 2.18 |
| 20 | 0.00 | 0.10 | 0.21 | 0.44 | 0.99 | 1.67 | 2.45 | 3.31 |
| 30 | 0.00 | 0.11 | 0.23 | 0.47 | 1.03 | 1.65 | 2.32 | 3.01 |
| 45 | 0.00 | 0.08 | 0.16 | 0.32 | 0.69 | 1.09 | 1.52 | 1.96 |
| 60 | 0.00 | 0.05 | 0.10 | 0.21 | 0.45 | 0.70 | 0.98 | 1.26 |

### 120 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.06 | 0.12 | 0.25 | 0.67 | 1.52 | 2.73 | 3.90 |
| 20 | 0.00 | 0.11 | 0.23 | 0.53 | 1.35 | 2.38 | 3.44 | 4.44 |
| 30 | 0.00 | 0.13 | 0.27 | 0.59 | 1.35 | 2.19 | 3.02 | 3.82 |
| 45 | 0.00 | 0.09 | 0.19 | 0.40 | 0.88 | 1.40 | 1.93 | 2.45 |
| 60 | 0.00 | 0.06 | 0.12 | 0.25 | 0.55 | 0.89 | 1.23 | 1.58 |


## Gain Error RMS Matrices

Values are mean RMS source-gain error in dB relative to zero-delay control. These matrices isolate the control-model error and are the clearest view of the expected sigma-delay sensitivity.

### 30 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.06 | 0.13 | 0.25 | 0.50 | 0.75 | 0.99 | 1.22 |
| 20 | 0.00 | 0.05 | 0.10 | 0.20 | 0.40 | 0.59 | 0.79 | 0.98 |
| 30 | 0.00 | 0.04 | 0.08 | 0.16 | 0.31 | 0.47 | 0.63 | 0.78 |
| 45 | 0.00 | 0.03 | 0.05 | 0.10 | 0.21 | 0.31 | 0.42 | 0.52 |
| 60 | 0.00 | 0.02 | 0.03 | 0.07 | 0.14 | 0.21 | 0.28 | 0.34 |

### 60 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.10 | 0.20 | 0.40 | 0.79 | 1.16 | 1.50 | 1.81 |
| 20 | 0.00 | 0.08 | 0.16 | 0.32 | 0.63 | 0.94 | 1.23 | 1.51 |
| 30 | 0.00 | 0.06 | 0.13 | 0.25 | 0.50 | 0.75 | 0.99 | 1.22 |
| 45 | 0.00 | 0.04 | 0.08 | 0.17 | 0.33 | 0.50 | 0.66 | 0.81 |
| 60 | 0.00 | 0.03 | 0.06 | 0.11 | 0.22 | 0.33 | 0.44 | 0.54 |

### 120 deg/s

| Sigma (deg) | 0 ms | 10 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | 0.00 | 0.15 | 0.31 | 0.61 | 1.15 | 1.59 | 1.96 | 2.28 |
| 20 | 0.00 | 0.12 | 0.24 | 0.48 | 0.94 | 1.36 | 1.73 | 2.06 |
| 30 | 0.00 | 0.10 | 0.19 | 0.38 | 0.75 | 1.10 | 1.42 | 1.71 |
| 45 | 0.00 | 0.06 | 0.13 | 0.25 | 0.50 | 0.73 | 0.95 | 1.15 |
| 60 | 0.00 | 0.04 | 0.08 | 0.17 | 0.33 | 0.49 | 0.63 | 0.77 |


## Largest Latency Losses

| Velocity (deg/s) | Sigma (deg) | Delay (ms) | Angular lag (deg) | TIR loss (dB) | Gain error RMS (dB) | Transition lag (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 120 | 20 | 200 | 24.0 | 4.44 | 2.06 | 200.00 |
| 120 | 10 | 200 | 24.0 | 3.90 | 2.28 | 200.00 |
| 120 | 30 | 200 | 24.0 | 3.82 | 1.71 | 200.00 |
| 120 | 20 | 160 | 19.2 | 3.44 | 1.73 | 160.00 |
| 60 | 20 | 200 | 12.0 | 3.31 | 1.51 | 200.00 |
| 120 | 30 | 160 | 19.2 | 3.02 | 1.42 | 160.00 |
| 60 | 30 | 200 | 12.0 | 3.01 | 1.22 | 200.00 |
| 30 | 20 | 200 | 6.0 | 2.83 | 0.98 | 200.00 |
| 120 | 10 | 160 | 19.2 | 2.73 | 1.96 | 160.00 |
| 30 | 30 | 200 | 6.0 | 2.53 | 0.78 | 200.00 |

## Interpretation

- `tir_loss_vs_zero_delay_db` is computed relative to the same sigma, speech pair and trajectory with zero orientation delay.
- The post-switch window treats source B as the target after the head crosses the midline between the two loudspeakers.
- Delay is applied only to the control yaw used by the attention model; the audio signal itself is not delayed.
- The upper heatmap reports downstream audio impact. The lower heatmap reports gain-control error directly.
- Narrow sigma generally increases gain-control error for a given angular lag, but TIR loss can be non-monotonic because the zero-delay baseline and the post-switch acoustic mixture also depend on sigma.
