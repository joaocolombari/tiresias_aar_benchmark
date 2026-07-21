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

`kappa = 10 ** (-separator_sdr_db / 20)` for finite SDR values. `separator_sdr_db = inf` gives `kappa = 0`, meaning the ideal no-leakage separator. It is not a finite SDR greater than 20 dB.

The detailed CSV preserves target and interference components through TIR and SI-SDR metrics. `source_estimate_delay_ms` is the separator-output delay axis. The source-delay figure uses STOI and SI-SDR to compare a degraded source-overlay output against the ideal zero-delay, no-leakage source-overlay output.

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

Mean dB loss relative to the ideal zero-delay, no-leakage separator, for `sigma=30 deg` and `orientation_delay_ms=0`.

### 30 deg/s

| Separator SDR (dB) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 5.79 | 5.77 | 5.77 | 5.78 | 5.76 | 5.76 | 5.84 |
| 5 | 4.21 | 4.19 | 4.19 | 4.20 | 4.17 | 4.16 | 4.23 |
| 10 | 2.85 | 2.83 | 2.82 | 2.82 | 2.78 | 2.76 | 2.83 |
| 20 | 1.10 | 1.08 | 1.06 | 1.06 | 1.00 | 0.97 | 1.03 |
| inf | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |

### 60 deg/s

| Separator SDR (dB) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7.35 | 7.33 | 7.34 | 7.37 | 7.43 | 7.48 | 7.41 |
| 5 | 5.39 | 5.38 | 5.38 | 5.42 | 5.47 | 5.53 | 5.45 |
| 10 | 3.67 | 3.67 | 3.68 | 3.73 | 3.78 | 3.82 | 3.74 |
| 20 | 1.44 | 1.44 | 1.46 | 1.52 | 1.56 | 1.61 | 1.52 |
| inf | 0.00 | 0.01 | 0.03 | 0.10 | 0.15 | 0.19 | 0.09 |

### 120 deg/s

| Separator SDR (dB) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 7.93 | 7.88 | 7.87 | 7.89 | 7.96 | 8.01 | 8.03 |
| 5 | 5.83 | 5.78 | 5.77 | 5.81 | 5.89 | 5.94 | 5.96 |
| 10 | 3.99 | 3.95 | 3.94 | 4.00 | 4.08 | 4.12 | 4.15 |
| 20 | 1.58 | 1.54 | 1.53 | 1.63 | 1.71 | 1.75 | 1.78 |
| inf | 0.00 | 0.00 | 0.00 | 0.09 | 0.17 | 0.21 | 0.24 |


## Requirement Envelope

The table reports the lowest separator SDR that satisfies both criteria for each condition:

- TIR retention >= 0.90 of the ideal condition, where `tir_retention_fraction = condition Delta TIR / ideal Delta TIR`;
- component SI-SDR loss <= 1.00 dB relative to the ideal condition.

### 30 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | inf | inf | inf | inf | inf | inf | inf |
| 20 | inf | inf | inf | inf | inf | inf | inf |
| 30 | inf | inf | inf | inf | inf | inf | inf |
| 45 | inf | inf | inf | inf | inf | inf | inf |
| 60 | inf | inf | inf | inf | not_met | not_met | not_met |

### 60 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | inf | inf | inf | inf | inf | inf | inf |
| 20 | inf | inf | inf | inf | inf | inf | inf |
| 30 | inf | inf | inf | inf | inf | inf | inf |
| 45 | inf | inf | inf | inf | inf | inf | inf |
| 60 | inf | inf | inf | inf | inf | inf | inf |

### 120 deg/s

| Sigma (deg) | 0 ms | 20 ms | 40 ms | 80 ms | 120 ms | 160 ms | 200 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 10 | inf | inf | inf | inf | inf | inf | inf |
| 20 | inf | inf | inf | inf | inf | inf | inf |
| 30 | inf | inf | inf | inf | inf | inf | inf |
| 45 | inf | inf | inf | inf | inf | inf | inf |
| 60 | inf | inf | inf | inf | inf | inf | inf |


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
- Increasing source-estimate delay shifts the separator reinforcement relative to the live binaural scene.
- The source-delay impact figure uses an overlay model: `output = live_scene + (gain - 1) * separated_estimate`, and compares each condition against the ideal zero-delay, no-leakage overlay using STOI and SI-SDR.
- TIR is intentionally not used in the source-delay panel because a common delay applied to both target and interference estimates can make finite-window TIR changes small and hard to interpret.
- The requirement envelope is conservative because a condition must satisfy both TIR retention and component SI-SDR loss.
