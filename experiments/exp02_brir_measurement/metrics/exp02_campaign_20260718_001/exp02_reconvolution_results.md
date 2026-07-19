# Experiment 2 Reconvolution Validation

Session: `exp02_campaign_20260718_001`

The validation predicts the measured microphone sweep by convolving the captured electrical reference with the estimated BRIR. Same-trial validation is an optimistic upper bound because the IR and prediction target come from the same sweep. Cross-repetition validation is the stronger repeatability check because the IR from one repetition predicts the other repetition.

Figure: `experiments/exp02_brir_measurement/figures/exp02_campaign_20260718_001/exp02_reconvolution_validation.png`

## Summary By Validation Type

| Validation | Rows | Prediction SDR (dB), mean +/- SD | Median SDR (dB) | Correlation, mean +/- SD | NRMSE, mean +/- SD | Gain-corrected SDR (dB), mean +/- SD |
|---|---:|---:|---:|---:|---:|---:|
| same trial | 148 | 25.97 +/- 0.89 | 25.98 | 0.9987 +/- 0.0003 | 0.0507 +/- 0.0053 | 25.97 +/- 0.89 |
| cross repetition | 148 | 23.20 +/- 1.52 | 23.39 | 0.9974 +/- 0.0009 | 0.0704 +/- 0.0126 | 23.21 +/- 1.52 |

## Summary By Speaker

| Validation | Speaker | Rows | Prediction SDR (dB), mean +/- SD | Correlation, mean +/- SD | NRMSE, mean +/- SD |
|---|---|---:|---:|---:|---:|
| cross repetition | A | 74 | 23.21 +/- 1.37 | 0.9975 +/- 0.0009 | 0.0701 +/- 0.0114 |
| cross repetition | B | 74 | 23.20 +/- 1.67 | 0.9974 +/- 0.0010 | 0.0707 +/- 0.0138 |
| same trial | A | 74 | 25.99 +/- 0.93 | 0.9987 +/- 0.0003 | 0.0506 +/- 0.0055 |
| same trial | B | 74 | 25.95 +/- 0.85 | 0.9987 +/- 0.0003 | 0.0508 +/- 0.0051 |

## Worst Cross-Repetition Cases

| Validation ID | Angle (deg) | Speaker | Source rep | Target rep | SDR (dB) | Corr | NRMSE |
|---|---:|---|---:|---:|---:|---:|---:|
| `cross_repetition__brir_theta_190_spk_B_rep01__to__brir_theta_190_spk_B_rep02` | 190 | B | 1 | 2 | 19.55 | 0.9944 | 0.1055 |
| `cross_repetition__brir_theta_190_spk_B_rep02__to__brir_theta_190_spk_B_rep01` | 190 | B | 2 | 1 | 20.04 | 0.9950 | 0.0997 |
| `cross_repetition__brir_theta_160_spk_A_rep01__to__brir_theta_160_spk_A_rep02` | 160 | A | 1 | 2 | 20.13 | 0.9951 | 0.0985 |
| `cross_repetition__brir_theta_160_spk_A_rep02__to__brir_theta_160_spk_A_rep01` | 160 | A | 2 | 1 | 20.16 | 0.9952 | 0.0982 |
| `cross_repetition__brir_theta_130_spk_B_rep01__to__brir_theta_130_spk_B_rep02` | 130 | B | 1 | 2 | 20.25 | 0.9952 | 0.0974 |
| `cross_repetition__brir_theta_130_spk_B_rep02__to__brir_theta_130_spk_B_rep01` | 130 | B | 2 | 1 | 20.26 | 0.9953 | 0.0972 |
| `cross_repetition__brir_theta_220_spk_A_rep02__to__brir_theta_220_spk_A_rep01` | 220 | A | 2 | 1 | 20.40 | 0.9954 | 0.0958 |
| `cross_repetition__brir_theta_120_spk_A_rep02__to__brir_theta_120_spk_A_rep01` | 120 | A | 2 | 1 | 20.43 | 0.9954 | 0.0955 |
| `cross_repetition__brir_theta_120_spk_A_rep01__to__brir_theta_120_spk_A_rep02` | 120 | A | 1 | 2 | 20.50 | 0.9955 | 0.0947 |
| `cross_repetition__brir_theta_220_spk_A_rep01__to__brir_theta_220_spk_A_rep02` | 220 | A | 1 | 2 | 20.58 | 0.9956 | 0.0938 |

## Interpretation

- Use cross-repetition metrics as the paper-facing validation of the measured BRIR set.
- Same-trial metrics are useful as an upper bound for the deconvolution and alignment procedure.
- Low-SDR cross-repetition cases identify angles or trials worth inspecting physically before using the BRIR bank for final benchmarks.
- A stable cross-repetition correlation near 1.0 and prediction SDR above roughly 20 dB indicate that reconvolving offline speech with these BRIRs should reproduce the measured rig behavior well enough for the planned parameter sweeps.

## Suggested Next Checks

- Render predicted and residual WAVs for the worst cross-repetition rows with `brir-validate --write-wavs --overwrite` and listen to the residual.
- Inspect the lowest-angle cases separately if they remain the worst; that pattern can indicate a small setup change between repetitions rather than a deconvolution failure.
- In the paper, show the figure and one compact table with cross-repetition mean +/- SD; keep the same-trial numbers as a methodological sanity check.
