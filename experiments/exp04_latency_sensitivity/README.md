# Experiment 4: Latency Sensitivity

This experiment evaluates how orientation-control delay affects the
head-orientation-driven monophonic attention model.

The acoustic scene uses the measured, microphone-corrected BRIRs from
Experiment 2. The analytical ITD/ILD renderer is not used. Each dry mono
LibriSpeech source is convolved with the measured BRIRs for the physical head
orientation, and the attention model applies one scalar source gain equally to
left and right ears.

## Current Geometry

The loudspeakers are fixed at:

- source A: `-30 deg`;
- source B: `+30 deg`.

Older planning notes mentioned `45 deg`; this experiment uses the updated
`30 deg` geometry.

Physical head yaw is simulated from `-30 deg` to `+30 deg`. The BRIR lookup uses
the normalized physical angle:

```text
physical_brir_angle_deg = yaw_deg mod 360
```

Therefore `-30 deg` uses the measured `theta_330` BRIRs and `+30 deg` uses
`theta_030`.

## Inputs

Required inputs:

- BRIRs from Experiment 2:
  `experiments/exp02_brir_measurement/processed/exp02_campaign_20260718_001/irs/`
- LibriSpeech subset:
  `datasets/librispeech_dev_clean_200_seed_2026/`

The LibriSpeech subset README states that 200 `dev-clean` files were selected
with seed `2026`. The current Exp04 config uses 100 deterministic source pairs
from this subset with seed `20260720`, avoiding same-speaker pairs when the
manifest contains enough speaker diversity.

## Run

From the repository root:

```bash
PYTHONPATH=src .venv/bin/python -m tiresias_benchmark experiment-run \
  --experiment 4 \
  --config experiments/exp04_latency_sensitivity/config.yaml
```

The config has `outputs.overwrite: true`, so rerunning regenerates the
processed tables, metrics and figures.

## Processing

For each speech pair and angular velocity:

1. Read two mono LibriSpeech files.
2. Resample to the BRIR sample rate.
3. Equalize dry speech RMS.
4. Convolve source A and source B with the measured stereo BRIRs for each
   measured head angle.
5. Generate a minimum-jerk head yaw trajectory from `-30 deg` to `+30 deg`.
6. Interpolate the pre-convolved BRIR images according to the physical yaw.
7. Compute ideal zero-delay Gaussian attention gains.
8. Compute delayed gains using:

   ```text
   gain(t) = attention_model(yaw(t - orientation_delay_ms))
   ```

9. Apply the same scalar source gain to both ears of each source image.
10. Compute post-switch metrics after the head crosses the midpoint between
    the sources.

The audio signal itself is not delayed. Only the control yaw used by the
attention model is delayed.

## Outputs

Detailed per-pair rows:

```text
processed/exp04_latency_results.csv
```

Aggregated condition rows:

```text
metrics/exp04_latency_summary_by_condition.csv
metrics/exp04_latency_summary.json
metrics/exp04_latency_summary.md
```

Figures:

```text
figures/exp04_latency_heatmaps.png
figures/exp04_latency_heatmaps.svg
figures/exp04_gain_transition_traces.png
figures/exp04_gain_transition_traces.svg
```

## Metrics

- `tir_improvement_db`: target-to-interferer ratio improvement in the
  post-switch analysis window, averaged across ears.
- `tir_loss_vs_zero_delay_db`: TIR change relative to the same speech pair,
  sigma and trajectory with zero orientation delay.
- `si_sdr_improvement_db`: SI-SDR relative to the acoustic target in the
  post-switch window.
- `gain_error_rms_db`: RMS source-gain error relative to zero-delay control.
- `gain_error_peak_abs_db`: peak absolute source-gain error.
- `transition_time_ms`: time after the target switch until B/A gain ratio
  reaches 90% of its final value.
- `transition_delay_vs_zero_ms`: transition-time increase relative to
  zero-delay control.

## Figure Interpretation

`exp04_latency_heatmaps` shows TIR loss versus zero-delay control. Loss grows
with larger delay, faster motion and narrower sigma. The relevant physical
quantity is also reported as:

```text
angular_velocity_delay_deg = angular_velocity_deg_s * delay_ms / 1000
```

`exp04_gain_transition_traces` shows a representative gain-ratio transition for
`sigma = 20 deg` and `120 deg/s`. It visualizes that the experiment is modelling
control-path latency rather than delaying the final audio waveform.
