# Experiment 2 Reconvolution Validation

Session: `exp02_campaign_20260718_001`

The validation predicts the measured microphone sweep by convolving the captured electrical reference with the estimated BRIR. Same-trial validation is an optimistic upper bound because the IR and prediction target come from the same sweep. Cross-repetition validation is the stronger repeatability check because the IR from one repetition predicts the other repetition.

Microphone factory magnitude calibration was applied as inverse zero-phase frequency-domain correction for L serial `23872AA` from `experiments/exp02_brir_measurement/calibration/LEFT_Earthworks_M23R_23872AA_ECF.txt`; R serial `23894AA` from `experiments/exp02_brir_measurement/calibration/RIGHT_Earthworks_M23R_23894AA_ECF.txt`.

Figure: `experiments/exp02_brir_measurement/figures/exp02_campaign_20260718_001/exp02_reconvolution_validation.png`

## Summary By Validation Type

| Validation | Rows | Prediction SDR (dB), mean +/- SD | Median SDR (dB) | Correlation, mean +/- SD | NRMSE, mean +/- SD | Gain-corrected SDR (dB), mean +/- SD |
|---|---:|---:|---:|---:|---:|---:|
| same trial | 148 | 25.91 +/- 0.89 | 25.92 | 0.9987 +/- 0.0003 | 0.0510 +/- 0.0053 | 25.91 +/- 0.89 |
| cross repetition | 148 | 23.23 +/- 1.51 | 23.41 | 0.9974 +/- 0.0009 | 0.0702 +/- 0.0125 | 23.23 +/- 1.51 |

## Summary By Speaker

| Validation | Speaker | Rows | Prediction SDR (dB), mean +/- SD | Correlation, mean +/- SD | NRMSE, mean +/- SD |
|---|---|---:|---:|---:|---:|
| cross repetition | A | 74 | 23.24 +/- 1.35 | 0.9975 +/- 0.0008 | 0.0699 +/- 0.0112 |
| cross repetition | B | 74 | 23.22 +/- 1.65 | 0.9974 +/- 0.0010 | 0.0704 +/- 0.0136 |
| same trial | A | 74 | 25.93 +/- 0.93 | 0.9987 +/- 0.0003 | 0.0510 +/- 0.0055 |
| same trial | B | 74 | 25.89 +/- 0.85 | 0.9987 +/- 0.0003 | 0.0511 +/- 0.0052 |

## Worst Cross-Repetition Cases

| Validation ID | Angle (deg) | Speaker | Source rep | Target rep | SDR (dB) | Corr | NRMSE |
|---|---:|---|---:|---:|---:|---:|---:|
| `cross_repetition__brir_theta_190_spk_B_rep01__to__brir_theta_190_spk_B_rep02` | 190 | B | 1 | 2 | 19.62 | 0.9945 | 0.1046 |
| `cross_repetition__brir_theta_190_spk_B_rep02__to__brir_theta_190_spk_B_rep01` | 190 | B | 2 | 1 | 20.12 | 0.9951 | 0.0988 |
| `cross_repetition__brir_theta_160_spk_A_rep01__to__brir_theta_160_spk_A_rep02` | 160 | A | 1 | 2 | 20.19 | 0.9952 | 0.0979 |
| `cross_repetition__brir_theta_160_spk_A_rep02__to__brir_theta_160_spk_A_rep01` | 160 | A | 2 | 1 | 20.21 | 0.9952 | 0.0976 |
| `cross_repetition__brir_theta_130_spk_B_rep01__to__brir_theta_130_spk_B_rep02` | 130 | B | 1 | 2 | 20.32 | 0.9953 | 0.0965 |
| `cross_repetition__brir_theta_130_spk_B_rep02__to__brir_theta_130_spk_B_rep01` | 130 | B | 2 | 1 | 20.34 | 0.9953 | 0.0963 |
| `cross_repetition__brir_theta_220_spk_A_rep02__to__brir_theta_220_spk_A_rep01` | 220 | A | 2 | 1 | 20.44 | 0.9954 | 0.0954 |
| `cross_repetition__brir_theta_120_spk_A_rep02__to__brir_theta_120_spk_A_rep01` | 120 | A | 2 | 1 | 20.49 | 0.9955 | 0.0948 |
| `cross_repetition__brir_theta_120_spk_A_rep01__to__brir_theta_120_spk_A_rep02` | 120 | A | 1 | 2 | 20.56 | 0.9955 | 0.0940 |
| `cross_repetition__brir_theta_220_spk_A_rep01__to__brir_theta_220_spk_A_rep02` | 220 | A | 1 | 2 | 20.63 | 0.9956 | 0.0933 |

## Interpretation

- Use cross-repetition metrics as the paper-facing validation of the measured BRIR set.
- Same-trial metrics are useful as an upper bound for the deconvolution and alignment procedure.
- Low-SDR cross-repetition cases identify angles or trials worth inspecting physically before using the BRIR bank for final benchmarks.
- A stable cross-repetition correlation near 1.0 and prediction SDR above roughly 20 dB indicate that reconvolving offline speech with these BRIRs should reproduce the measured rig behavior well enough for the planned parameter sweeps.

## Suggested Next Checks

- Render predicted and residual WAVs for the worst cross-repetition rows with `brir-validate --write-wavs --overwrite` and listen to the residual.
- Inspect the lowest-angle cases separately if they remain the worst; that pattern can indicate a small setup change between repetitions rather than a deconvolution failure.
- In the paper, show the figure and one compact table with cross-repetition mean +/- SD; keep the same-trial numbers as a methodological sanity check.
