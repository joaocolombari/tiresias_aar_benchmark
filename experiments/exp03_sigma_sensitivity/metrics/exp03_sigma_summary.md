# Experiment 3 Sigma Sensitivity

This experiment uses measured mic-corrected BRIRs from Experiment 2 and the same 100 deterministic LibriSpeech pairs used in Experiments 4 and 5.

The attention model remains monophonic: one scalar gain is computed per source and applied equally to both ears of that source image. Analytical ITD/ILD rendering is not used.

Source azimuths are `-30 deg` and `+30 deg`; the earlier `45 deg` protocol is not used.

## Outputs

- Detailed rows: `experiments/exp03_sigma_sensitivity/processed/exp03_sigma_results.csv`
- Condition summary: `experiments/exp03_sigma_sensitivity/metrics/exp03_sigma_summary_by_condition.csv`
- TIR heatmap: `experiments/exp03_sigma_sensitivity/figures/exp03_sigma_tir_heatmaps.png`
- Gain/TIR curves: `experiments/exp03_sigma_sensitivity/figures/exp03_sigma_gain_and_tir_curves.png`

## Dataset

- Speech pairs: 100
- Dataset: `datasets/librispeech_dev_clean_200_seed_2026`
- The default configuration uses the same deterministic 100 non-overlapping pairs as Experiment 4.

## Method

For every static head yaw, both target definitions are evaluated independently:

- target A: source A is the desired source, regardless of head hemisphere;
- target B: source B is the desired source, regardless of head hemisphere.

This avoids defining the target from the same head angle that drives the attention gain.

## Aligned-Target Baseline

Values below are measured when the head yaw is aligned with the target source angle.

### Target A

| Sigma (deg) | Target gain (dB) | Interferer gain (dB) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |
|---:|---:|---:|---:|---:|
| 10 | 10.00 | 0.00 | 10.00 +/- 0.00 | 10.00 +/- 0.06 |
| 20 | 10.00 | 0.11 | 9.89 +/- 0.00 | 9.89 +/- 0.06 |
| 30 | 10.00 | 1.35 | 8.65 +/- 0.00 | 8.65 +/- 0.06 |
| 45 | 10.00 | 4.11 | 5.89 +/- 0.00 | 5.89 +/- 0.04 |
| 60 | 10.00 | 6.07 | 3.93 +/- 0.00 | 3.93 +/- 0.03 |

### Target B

| Sigma (deg) | Target gain (dB) | Interferer gain (dB) | TIR improvement (dB), mean +/- SD | SI-SDR improvement (dB), mean +/- SD |
|---:|---:|---:|---:|---:|
| 10 | 10.00 | 0.00 | 10.00 +/- 0.00 | 10.00 +/- 0.08 |
| 20 | 10.00 | 0.11 | 9.89 +/- 0.00 | 9.89 +/- 0.08 |
| 30 | 10.00 | 1.35 | 8.65 +/- 0.00 | 8.65 +/- 0.07 |
| 45 | 10.00 | 4.11 | 5.89 +/- 0.00 | 5.89 +/- 0.06 |
| 60 | 10.00 | 6.07 | 3.93 +/- 0.00 | 3.93 +/- 0.04 |

## Interpretation

- Smaller sigma produces stronger angular selectivity and larger target/interferer gain contrast near the attended source.
- Larger sigma produces a wider attention field, reducing peak selectivity but making the gain less sensitive to angular error.
- The heatmaps show the full static operating surface across head yaw and sigma for each independent target definition.
- The curve figure shows the source-A case as signed head yaw relative to the target. The dashed vertical line marks the target direction and the dotted vertical line marks the interferer direction.
