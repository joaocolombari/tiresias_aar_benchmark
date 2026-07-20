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

Three complete runs are acquired as separate guided sessions by default:

- ascending: `0, 10, ..., 350, 360`;
- descending: `360, 350, ..., 10, 0`;
- randomized: all 36 unique orientations once with the configured random seed,
  followed by a final 360 deg closure measurement.

Default timing is 3 s settling, 10 s acquisition, 2 s discarded transient and
8 s analyzed stationary interval per position. Static drift can be measured
for 120 s at 0 deg before or after a guided session when explicitly requested.
The older all-in-one campaign remains available, but the separated procedure is
preferred so results can be inspected after each run.

Closure error is reported separately:

- ascending: circular difference between measured 360 deg and initial 0 deg;
- descending: circular difference between final 0 deg and initial 360 deg;
- randomized: circular difference between final 360 deg and the 0 deg
  measurement within the randomized run.

## Experiment 2: Binaural Response Measurement

Measure native BRIRs on the rotating mannequin rig using the Scarlett 18i8,
two Earthworks microphones and two Neumann monitors. REW is not used.

The measured geometry is:

- physical zero: mannequin facing the frontal reference;
- positive rotation: clockwise;
- Neumann A: -30 deg azimuth;
- Neumann B: +30 deg azimuth;
- distance: 1.0 m from the mannequin nose to each Neumann.

The physical campaign uses nominal platform positions:

`0, 10, 20, ..., 350, 360 deg`.

The 360 deg row is a closure measurement. It wraps to 0 deg for angular
comparison, but it remains a separate trial identity and separate file path.

For each angle, measure:

- speaker A, repetition 1;
- speaker B, repetition 1;
- speaker A, repetition 2;
- speaker B, repetition 2.

To reduce order bias, odd angle indices invert speaker order:

- even angle index: `A1, B1, A2, B2`;
- odd angle index: `B1, A1, B2, A2`.

The complete plan contains 37 angle blocks, 148 sweeps and 296 expected impulse
responses. Each sweep activates one speaker only. Scarlett output 3 carries an
exact copy of the active speaker drive and returns to the configured reference
input stream channel as the electrical reference.

The default acquisition machine is macOS using Core Audio and the Scarlett as a
full-duplex device. The experiment does not require Tiresias BLE telemetry.

Raw acquisition must preserve:

- Earthworks L;
- Earthworks R;
- electrical reference;
- callback timing/status;
- operator metadata and QC decision.

The raw audio path is float32 and unnormalized. The electrical reference is
used for deconvolution:

`H_ear[k] = Y_ear[k] * conj(R[k]) / (|R[k]|^2 + lambda[k])`.

Left and right IRs must share the same reference, origin, window and sample
rate. Do not peak-align, normalize, resample or time-shift the two ears
independently, because that would destroy ITD. Analytical ITD/ILD rendering is
bypassed when these measured BRIRs are used in later benchmarks.

## Experiment 3: Sigma Sensitivity

Use measured responses and offline monophonic speech. Vary `sigma_deg` while
keeping target identity independent from the head hemisphere. Apply one scalar
source gain to both ears of each source image.

## Experiment 4: Latency Sensitivity

Use the physical head orientation for the measured BRIR acoustic response and
the delayed head orientation for attention gain:

`gain(t) = attention_model(yaw(t - control_delay_ms))`.

The current geometry is source A at -30 deg and source B at +30 deg. Dry
monophonic LibriSpeech sources are convolved with the Experiment 2 BRIR bank;
negative yaw wraps to the corresponding 0-360 deg measured BRIR angle, so
-30 deg uses `theta_330` and +30 deg uses `theta_030`.

Do not model this as final-output audio delay. The audio scene follows the
physical yaw trajectory; only the control variable passed to the monophonic
Gaussian attention model is delayed.

## Experiment 5: Source Separator Requirements

Emulate leakage:

`xhat_a = x_a + kappa * x_b`

`xhat_b = x_b + kappa * x_a`

with `kappa = 10 ** (-separator_sdr_db / 20)`. Preserve target and interference
components for metrics.

## Experiment 6: Physical Validation

Compare simultaneous physical recording with the sum of isolated physical
recordings and the BRIR-based synthesized mixture.
