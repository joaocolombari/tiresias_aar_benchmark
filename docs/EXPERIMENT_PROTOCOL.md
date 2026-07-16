# Experiment Protocol

## Experiment 1: Orientation Characterization

Record telemetry at physical platform angles from 0 deg through 360 deg in
10 deg increments. The positions 0 deg through 350 deg are the 36 unique
spatial orientations. The 360 deg endpoint is preserved in raw and segmented
data as a closure measurement, but it is not counted as an independent
direction in global angular-error statistics.

The coordinate convention is configured, not inferred:

- `zero_direction_description` names the physical 0 deg reference.
- `positive_rotation_direction` is either `clockwise` or `counterclockwise`.
- `reference_angle_range_deg` is `[0, 360]`.
- `reference_angle_step_deg` is `10`.

The migrated application's quaternion convention and yaw sign are preserved.
The explicit comparison transformation is:

1. Physical command:
   `reference_angle_commanded_deg`.
2. Normalized physical reference:
   `reference_angle_normalized_deg = reference_angle_commanded_deg mod 360`.
3. Host calibrated yaw:
   `calibrated_yaw_deg`.
4. Normalized measured yaw:
   `measured_yaw_360_deg = calibrated_yaw_deg mod 360`.
5. Signed circular error:
   `error_deg = ((measured_yaw_360_deg - reference_angle_normalized_deg + 180) mod 360) - 180`.

This supports yaw represented as either `[-180, 180)` or `[0, 360)` and avoids
ordinary subtraction at the 0/360 discontinuity.

Three complete runs are acquired:

- ascending: `0, 10, ..., 350, 360`;
- descending: `360, 350, ..., 10, 0`;
- randomized: all 36 unique orientations once with the configured random seed,
  followed by a final 360 deg closure measurement.

Default timing is 3 s settling, 10 s acquisition, 2 s discarded transient and
8 s analyzed stationary interval per position. Static drift is measured for
120 s at 0 deg before and after the angular campaign.

Closure error is reported separately:

- ascending: circular difference between measured 360 deg and initial 0 deg;
- descending: circular difference between final 0 deg and initial 360 deg;
- randomized: circular difference between final 360 deg and the 0 deg
  measurement within the randomized run.

## Experiment 2: Binaural Response Measurement

Record exponential sweeps for each head angle, source and ear. Use electrical
playback-reference channels when available. Deconvolve with regularization,
trim around the direct-response peak and store one response per source, ear and
head angle.

## Experiment 3: Sigma Sensitivity

Use measured responses and offline monophonic speech. Vary `sigma_deg` while
keeping target identity independent from the head hemisphere. Apply one scalar
source gain to both ears of each source image.

## Experiment 4: Latency Sensitivity

Use the physical head orientation for the acoustic response and the delayed
head orientation for attention gain:

`gain(t) = attention_model(yaw(t - control_delay_ms))`.

Do not model this as final-output audio delay.

## Experiment 5: Source Separator Requirements

Emulate leakage:

`xhat_a = x_a + kappa * x_b`

`xhat_b = x_b + kappa * x_a`

with `kappa = 10 ** (-separator_sdr_db / 20)`. Preserve target and interference
components for metrics.

## Experiment 6: Physical Validation

Compare simultaneous physical recording with the sum of isolated physical
recordings and the BRIR-based synthesized mixture.
