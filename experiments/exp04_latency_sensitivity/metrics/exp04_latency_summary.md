# Experiment 4 Latency Sensitivity

This experiment uses measured mic-corrected BRIRs from Experiment 2 and offline monophonic LibriSpeech sources. The acoustic scene follows the physical head yaw trajectory, while the Gaussian attention gains use a delayed yaw trajectory.

Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is no longer used here.

## Outputs

- Detailed rows: `experiments/exp04_latency_sensitivity/processed/exp04_latency_results.csv`
- Condition summary: `experiments/exp04_latency_sensitivity/metrics/exp04_latency_summary_by_condition.csv`
- Heatmap figure: `experiments/exp04_latency_sensitivity/figures/exp04_latency_heatmaps.png`
- Transition figure: `experiments/exp04_latency_sensitivity/figures/exp04_gain_transition_traces.png`

## Dataset

- Speech pairs: 10
- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`
- The subset README states that 200 LibriSpeech dev-clean files were selected reproducibly with seed 2026.

## Zero-Delay Baseline

| Velocity (deg/s) | Sigma (deg) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |
|---:|---:|---:|---:|
| 120 | 10 | 9.55 +/- 0.39 | 9.59 +/- 0.41 |
| 120 | 20 | 9.49 +/- 0.24 | 9.53 +/- 0.28 |
| 120 | 30 | 8.23 +/- 0.18 | 8.27 +/- 0.24 |
| 120 | 45 | 5.58 +/- 0.13 | 5.62 +/- 0.18 |
| 120 | 60 | 3.73 +/- 0.09 | 3.76 +/- 0.12 |
| 30 | 10 | 7.64 +/- 1.07 | 7.60 +/- 1.08 |
| 30 | 20 | 7.78 +/- 0.64 | 7.74 +/- 0.64 |
| 30 | 30 | 6.02 +/- 0.64 | 5.99 +/- 0.63 |
| 30 | 45 | 3.75 +/- 0.52 | 3.73 +/- 0.52 |
| 30 | 60 | 2.44 +/- 0.38 | 2.42 +/- 0.38 |
| 60 | 10 | 8.85 +/- 1.16 | 8.86 +/- 1.14 |
| 60 | 20 | 8.85 +/- 0.66 | 8.87 +/- 0.64 |
| 60 | 30 | 7.41 +/- 0.44 | 7.42 +/- 0.44 |
| 60 | 45 | 4.90 +/- 0.33 | 4.90 +/- 0.34 |
| 60 | 60 | 3.26 +/- 0.23 | 3.26 +/- 0.24 |

## Largest Latency Losses

| Velocity (deg/s) | Sigma (deg) | Delay (ms) | Angular lag (deg) | TIR loss (dB) | Gain error RMS (dB) | Transition lag (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 60 | 20 | 200 | 12.0 | 3.07 | 1.51 | 200.00 |
| 60 | 30 | 200 | 12.0 | 2.88 | 1.22 | 200.00 |
| 30 | 20 | 200 | 6.0 | 2.74 | 0.98 | 200.00 |
| 120 | 20 | 200 | 24.0 | 2.60 | 2.06 | 200.00 |
| 30 | 30 | 200 | 6.0 | 2.46 | 0.78 | 200.00 |
| 120 | 30 | 200 | 24.0 | 2.41 | 1.71 | 200.00 |
| 60 | 20 | 160 | 9.6 | 2.25 | 1.23 | 160.00 |
| 120 | 10 | 200 | 24.0 | 2.23 | 2.28 | 200.00 |
| 60 | 30 | 160 | 9.6 | 2.22 | 0.99 | 160.00 |
| 30 | 20 | 160 | 4.8 | 2.07 | 0.79 | 160.00 |

## Interpretation

- `tir_loss_vs_zero_delay_db` is computed relative to the same sigma, speech pair and trajectory with zero orientation delay.
- The post-switch window treats source B as the target after the head crosses the midline between the two loudspeakers.
- Delay is applied only to the control yaw used by the attention model; the audio signal itself is not delayed.
- The heatmap should be read as a design envelope: smaller sigma and faster motion make a given delay correspond to a larger effective angular error.
