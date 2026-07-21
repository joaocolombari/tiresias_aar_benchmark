# Experiment 5 Source Separator Requirements

This experiment uses the same measured mic-corrected BRIRs, 100 LibriSpeech pairs, source geometry and dynamic yaw trajectories used by Experiment 4.

The attention model remains monophonic: each source receives one scalar gain. Separator imperfections are emulated after binaural source-image synthesis by adding delayed cross-source leakage to the per-source estimates.

Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is not used.

## Outputs

- Detailed rows: `experiments/exp05_separator_requirements/processed/exp05_separator_results.csv`
- Condition summary: `experiments/exp05_separator_requirements/metrics/exp05_separator_summary_by_condition.csv`
- Requirement table: `experiments/exp05_separator_requirements/metrics/exp05_separator_requirements.csv`
- Separator-degradation heatmap: `experiments/exp05_separator_requirements/figures/exp05_separator_heatmaps.png`
- TIR-retention curves: `experiments/exp05_separator_requirements/figures/exp05_requirement_envelope.png`
- Source-delay impact figure: `experiments/exp05_separator_requirements/figures/exp05_source_delay_impact.png`

## Dataset

- Speech pairs: 100
- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`
- The default configuration uses the same deterministic 100 non-overlapping pairs as Experiment 4.

## Separator Model

`xhat_a = delay(x_a) + kappa * delay(x_b)`

`xhat_b = delay(x_b) + kappa * delay(x_a)`

`kappa = 10 ** (-separator_sdr_db / 20)` for finite SDR values. `separator_sdr_db = inf` gives `kappa = 0`, meaning the ideal no-leakage separator. Figures display this condition as `ideal`; it is not a finite SDR greater than 20 dB.

The detailed CSV preserves target and interference components through TIR and SI-SDR metrics. `source_estimate_delay_ms` is the separator-output delay axis and uses the same delay values as Experiment 4.

## Ideal Separator Baseline

| Velocity (deg/s) | Sigma (deg) | TIR improvement (dB), mean +/- SD | Physical SI-SDR improvement (dB), mean +/- SD |
|---:|---:|---:|---:|
| 30 | 10 | 6.60 +/- 2.50 | 2.76 +/- 6.25 |
| 30 | 20 | 7.18 +/- 1.56 | 4.97 +/- 5.31 |
| 30 | 30 | 5.79 +/- 1.23 | 4.73 +/- 4.06 |
| 30 | 45 | 3.69 +/- 0.88 | 3.22 +/- 2.62 |
| 30 | 60 | 2.42 +/- 0.61 | 2.16 +/- 1.70 |
| 60 | 10 | 8.65 +/- 1.44 | 6.25 +/- 2.55 |
| 60 | 20 | 8.75 +/- 0.86 | 7.69 +/- 1.54 |
| 60 | 30 | 7.34 +/- 0.78 | 7.02 +/- 0.99 |
| 60 | 45 | 4.85 +/- 0.61 | 4.79 +/- 0.66 |
| 60 | 60 | 3.22 +/- 0.42 | 3.21 +/- 0.45 |
| 120 | 10 | 9.36 +/- 0.65 | 7.53 +/- 2.35 |
| 120 | 20 | 9.30 +/- 0.43 | 8.51 +/- 1.44 |
| 120 | 30 | 7.93 +/- 0.46 | 7.67 +/- 0.83 |
| 120 | 45 | 5.31 +/- 0.39 | 5.27 +/- 0.47 |
| 120 | 60 | 3.54 +/- 0.27 | 3.53 +/- 0.31 |

## Representative TIR Loss Matrices

Mean dB loss relative to the ideal zero-delay, no-leakage separator, for `sigma=20 deg` and `orientation_delay_ms=0`.

### 30 deg/s

| Separator setting | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7.18 | 7.17 | 7.16 | 7.18 | 7.19 | 7.22 | 7.30 |
| 5 | 5.26 | 5.24 | 5.23 | 5.25 | 5.25 | 5.27 | 5.34 |
| 10 | 3.59 | 3.57 | 3.55 | 3.56 | 3.55 | 3.56 | 3.63 |
| 20 | 1.40 | 1.38 | 1.36 | 1.37 | 1.34 | 1.33 | 1.38 |
| ideal | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

### 60 deg/s

| Separator setting | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 8.80 | 8.78 | 8.78 | 8.81 | 8.85 | 8.90 | 8.84 |
| 5 | 6.50 | 6.49 | 6.49 | 6.52 | 6.56 | 6.61 | 6.54 |
| 10 | 4.48 | 4.47 | 4.47 | 4.51 | 4.55 | 4.59 | 4.52 |
| 20 | 1.79 | 1.78 | 1.79 | 1.84 | 1.88 | 1.92 | 1.84 |
| ideal | 0.00 | 0.00 | 0.02 | 0.08 | 0.11 | 0.15 | 0.06 |

### 120 deg/s

| Separator setting | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 9.33 | 9.27 | 9.24 | 9.25 | 9.31 | 9.36 | 9.39 |
| 5 | 6.91 | 6.86 | 6.83 | 6.86 | 6.91 | 6.97 | 7.00 |
| 10 | 4.78 | 4.72 | 4.71 | 4.74 | 4.81 | 4.86 | 4.89 |
| 20 | 1.92 | 1.87 | 1.86 | 1.92 | 1.99 | 2.04 | 2.07 |
| ideal | 0.00 | 0.00 | 0.00 | 0.04 | 0.11 | 0.15 | 0.19 |


## Requirement Envelope

The table reports the lowest separator setting that satisfies both criteria for each condition:

- TIR retention >= 0.90 of the ideal condition, where `tir_retention_fraction = condition Delta TIR / ideal Delta TIR`;
- component SI-SDR loss <= 1.00 dB relative to the ideal condition.

### 30 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 20 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 30 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 45 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 60 | ideal | ideal | ideal | ideal | not_met | not_met | not_met |

### 60 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 20 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 30 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 45 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 60 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |

### 120 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 20 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 30 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 45 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |
| 60 | ideal | ideal | ideal | ideal | ideal | ideal | ideal |


## Largest Losses

| Velocity (deg/s) | Sigma (deg) | Source delay (ms) | Separator SDR (dB) | Leakage | TIR loss (dB) | SI-SDR loss (dB) |
|---:|---:|---:|---:|---:|---:|---:|
| 120 | 10 | 200 | 0 | 1.00 | 9.40 | 40.26 |
| 120 | 10 | 0 | 0 | 1.00 | 9.40 | 7.87 |
| 120 | 20 | 200 | 0 | 1.00 | 9.39 | 41.62 |
| 120 | 10 | 160 | 0 | 1.00 | 9.37 | 40.31 |
| 120 | 20 | 160 | 0 | 1.00 | 9.36 | 41.04 |
| 120 | 10 | 20 | 0 | 1.00 | 9.34 | 33.89 |
| 120 | 10 | 120 | 0 | 1.00 | 9.33 | 39.58 |
| 120 | 20 | 0 | 0 | 1.00 | 9.33 | 8.60 |
| 120 | 10 | 40 | 0 | 1.00 | 9.31 | 33.07 |
| 120 | 10 | 80 | 0 | 1.00 | 9.31 | 37.50 |

## Interpretation

- Experiment 4 isolates delayed orientation control. Experiment 5 isolates separator-output delay and leakage by default, with `orientation_delay_ms = 0`.
- The main degradation axis in this experiment is separator SDR, not source-estimate delay. A common delay applied to both source estimates changes absolute timing, but it has little effect on TIR because target and interference are delayed together.
- Increasing leakage raises the residual contribution of the non-target source inside each separated estimate.
- Increasing source-estimate delay shifts both separated source images relative to the physical target reference; this is mainly visible in the physical-target SI-SDR diagnostic columns.
- The source-delay impact figure separates these effects: the upper row shows the signed TIR-loss change relative to the 0 ms source-delay case, while the lower row shows the additional latency penalty against the non-delayed physical target.
- The signed TIR-loss change can be slightly negative because source delay is applied to target and interference together and the metric is evaluated in a finite post-switch window.
- The requirement envelope is conservative because a condition must satisfy both TIR retention and component SI-SDR loss.
