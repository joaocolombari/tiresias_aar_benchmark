# Experiment 5: Source Separator Requirements

Experiment 5 estimates the minimum source-separation quality required by the
head-orientation-driven attention pipeline.

It reuses the same measured BRIRs, source geometry, dynamic yaw trajectories,
sigma values, delay range and 100 LibriSpeech source pairs used in Experiment
4. The difference is that Experiment 5 emulates imperfect separated source
estimates through cross-source leakage and source-estimate delay.

## Question

How much source-estimate delay and residual leakage can the system tolerate
before the attention-guided enhancement loses most of the benefit obtained with
an ideal zero-delay separator?

## Physical And Signal Model

The source geometry is:

- source A: `-30 deg`;
- source B: `+30 deg`;
- measured binaural response from Experiment 2;
- monophonic attention model with one scalar gain per source.

For each source pair and trajectory:

```text
dry mono speech
  -> measured BRIR source image
  -> delayed source estimate
  -> cross-source leakage
  -> monophonic attention gain per source
  -> binaural output components
  -> TIR and SI-SDR metrics
```

The separator model is:

```text
xhat_a = delay(x_a) + kappa * delay(x_b)
xhat_b = delay(x_b) + kappa * delay(x_a)
```

with:

```text
kappa = 10 ** (-separator_sdr_db / 20)
```

`separator_sdr_db = inf` gives `kappa = 0`, representing an ideal no-leakage
separator. It is displayed as `inf` in figures and summary tables; it is not a
finite separator SDR greater than 20 dB.

## Relation To Experiment 4

Experiment 4 isolates orientation-control delay:

```text
gain(t) = attention_model(yaw(t - orientation_delay))
```

Experiment 5 isolates separator-output delay and leakage by default:

```text
orientation_delay_ms = 0
source_estimate_delay_ms = [0, 20, 40, 80, 120, 160, 200]
```

The primary delay values preserve the same 0-200 ms range used for the latency
analysis, so the two experiments can still be compared in the paper. The
source-delay figure uses STOI over that same 0-200 ms range. If needed,
`orientation_delay_ms` can be expanded in `config.yaml`, but the default run
keeps it fixed to avoid mixing two different latency effects.

## Required Inputs

- BRIRs from Experiment 2:
  `experiments/exp02_brir_measurement/processed/exp02_campaign_20260718_001/irs/`
- LibriSpeech subset:
  `datasets/librispeech_dev_clean_200_seed_2026/`

The default config uses 100 deterministic, non-overlapping source pairs from
the 200-file subset. This is the same pair selection as Experiment 4:

```yaml
pair_count: 100
pair_seed: 20260720
```

## Run

From the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m tiresias_benchmark experiment-run \
  --experiment 5 \
  --config experiments/exp05_separator_requirements/config.yaml
```

On machines without the project virtual environment, use:

```bash
PYTHONPATH=src python3 -m tiresias_benchmark experiment-run \
  --experiment 5 \
  --config experiments/exp05_separator_requirements/config.yaml
```

## Default Grid

```yaml
sigma_deg: [10, 20, 30, 45, 60]
source_estimate_delay_ms: [0, 20, 40, 80, 120, 160, 200]
separator_sdr_db: [inf, 20, 10, 5, 0]
angular_velocity_deg_s: [30, 60, 120]
```

With 100 speech pairs, this produces:

```text
3 velocities
x 5 sigma values
x 7 source-estimate delays
x 5 separator SDR values
x 100 speech pairs
= 52,500 detailed rows
```

The source-delay figure evaluates the same 0-200 ms delay range with STOI
against the same ideal source-overlay reference:

```yaml
figures:
  source_delay_metric: stoi_vs_ideal_output
  source_delay_plot_delay_ms: [0, 20, 40, 80, 120, 160, 200]
```

## Outputs

```text
processed/exp05_separator_results.csv
metrics/exp05_separator_summary_by_condition.csv
metrics/exp05_source_delay_plot_summary.csv
metrics/exp05_separator_requirements.csv
metrics/exp05_separator_summary.json
metrics/exp05_separator_summary.md
figures/exp05_separator_heatmaps.png
figures/exp05_separator_heatmaps.svg
figures/exp05_requirement_envelope.png
figures/exp05_requirement_envelope.svg
figures/exp05_source_delay_impact.png
figures/exp05_source_delay_impact.svg
```

## Metrics

The detailed CSV contains one row per speech pair and condition.

Important columns:

- `separator_sdr_db`: configured separator quality;
- `leakage_linear`: cross-source leakage coefficient `kappa`;
- `source_estimate_delay_ms`: delay applied to both source estimates;
- `tir_improvement_db`: output target-to-interference improvement;
- `tir_loss_vs_ideal_db`: loss relative to the ideal zero-delay separator;
- `tir_retention_fraction`: dimensionless fraction of ideal TIR improvement
  retained, calculated as `condition Delta TIR / ideal Delta TIR`;
- `si_sdr_loss_vs_ideal_db`: SI-SDR loss relative to the ideal separator;
- `component_si_sdr_loss_vs_ideal_db`: SI-SDR loss against the processed target
  component;
- `gain_error_rms_db`: orientation-control gain error. This is zero in the
  default run because `orientation_delay_ms` is fixed at zero.

## Requirement Criterion

The requirement table reports the lowest separator SDR that satisfies both:

```text
TIR retention >= 0.90
component SI-SDR loss <= 1.0 dB
```

These defaults can be changed under `requirements:` in `config.yaml`.
The component SI-SDR criterion compares the output against the processed target
component, so it evaluates separation quality without automatically rejecting a
condition merely because the separator output is delayed. The detailed CSV also
keeps `si_sdr_loss_vs_ideal_db`, which compares against the physical target
timing and is useful as a diagnostic latency-distortion measure.

## Figures

`exp05_separator_heatmaps` shows how much TIR improvement is lost as the
separator SDR is degraded from the ideal no-leakage condition. The x-axis is
separator SDR, the y-axis is sigma and each panel is one angular velocity. The
representative source-estimate delay is:

```yaml
representative_orientation_delay_ms: 0
representative_source_delay_ms: 0
```

`exp05_requirement_envelope` shows TIR retention fraction as separator SDR
degrades. The dashed horizontal line marks the 90% retention criterion. This is
the main figure for evaluating how separation degradation impacts final
enhancement. A value of `1.0` means the condition retained all TIR improvement
obtained with the ideal no-leakage separator; `0.9` means it retained 90% of
that ideal benefit.

`exp05_source_delay_impact` shows STOI loss for the representative
sigma. It uses the ideal source-overlay output as its reference, i.e.
live binaural scene plus zero-delay, no-leakage separator reinforcement
following the ideal head orientation. Each degraded condition keeps the live
scene unchanged and overlays the delayed/leaky separator estimate:

```text
output = live_scene + (gain - 1) * separated_estimate
```

The plot reports STOI loss relative to that ideal output. This intentionally
replaces the earlier physical-target SI-SDR diagnostic, which compared against a
different target and was overly sensitive to sample-level timing offsets.

If the requirement table reports `inf`, the finite separator SDR values tested
up to 20 dB did not satisfy the criterion, but the ideal no-leakage condition
did. If it reports `not_met`, even the no-leakage condition failed under that
delay and sigma.

## Interpretation Notes

- The attention model is still monophonic.
- Measured BRIRs provide the binaural source images.
- The same source gain is applied to both ears of a source image.
- Analytical ITD/ILD rendering is not used.
- TIR is mostly sensitive to leakage, not to a common delay applied to both
  separated estimates. The source-delay figure therefore uses STOI
  relative to the ideal overlay output to show how separator latency degrades
  the final enhanced scene.
- A condition marked `not_met` means even the ideal no-leakage separator did
  not satisfy the requirement under that source-estimate delay and sigma.
