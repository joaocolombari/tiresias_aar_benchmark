# Data Schema

## Telemetry CSV

- `session_id`: string.
- `host_monotonic_timestamp_ns`: host monotonic receive time in ns.
- `receive_interval_ms`: interval from previous notification in ms.
- `packet_loss_count`: missing sequence numbers since previous packet.
- `device_timestamp_ms`: firmware uptime timestamp in ms, empty when unavailable.
- `seq`: firmware sequence number, empty when unavailable.
- `packet_format`: `legacy_quaternion` or `telemetry_v1`.
- `packet_version`: protocol version, empty for legacy packets.
- `ax_m_s2`, `ay_m_s2`, `az_m_s2`: accelerometer components.
- `gx_rad_s`, `gy_rad_s`, `gz_rad_s`: gyroscope components as interpreted by the firmware path.
- `qw`, `qx`, `qy`, `qz`: scalar-first quaternion.
- `yaw_deg`: firmware yaw in degrees, empty when unavailable.
- `calibrated_yaw_deg`: host-calibrated yaw in degrees.
- `sigma_deg`: active Gaussian sigma in degrees.
- `bmax_db`: maximum attention enhancement in dB.
- `audio_frame_index`: real-time audio frame index, empty for telemetry-only capture.
- `source_N_gain_linear`, `source_N_gain_db`: scalar monophonic source gain.

For Experiment 1 segmented orientation rows also use:

- `run_id`: run identifier.
- `run_type`: `ascending`, `descending` or `randomized`.
- `position_index`: position order within the run.
- `reference_angle_commanded_deg`: physical commanded platform position,
  preserving closure values such as 360.
- `reference_angle_normalized_deg`: commanded angle modulo 360.
- `is_closure_measurement`: true for the endpoint used only for closure error.

## BRIR Manifest CSV

- `head_yaw_deg`: rig head orientation in degrees.
- `source_name`: monophonic source/loudspeaker identifier.
- `source_azimuth_deg`: fixed loudspeaker azimuth in degrees.
- `left_ir_path`: path to left-ear measured response WAV.
- `right_ir_path`: path to right-ear measured response WAV.
- `sample_rate_hz`: response sample rate.

## Experiment 2 Plan CSV

- `trial_id`: stable trial name, e.g. `brir_theta_000_spk_A_rep01`.
- `condition_id`: condition identity before attempt numbering; currently equal
  to `trial_id`.
- `angle_sequence_index`: index from 0 through 36 in the physical campaign.
- `angle_nominal_deg`: physical platform label, preserving 360.
- `angle_wrapped_deg`: `angle_nominal_deg mod 360`; 360 maps to 0.
- `closure_measurement`: true only for nominal 360 rows.
- `speaker`: `A` or `B`.
- `repetition`: independent repetition number, 1 or 2.
- `expected_output_channel`: physical Scarlett output for the active speaker.
- `expected_reference_output_channel`: physical Scarlett output copied to the
  electrical reference input.
- `expected_input_channels`: logical raw input mapping for ear L, ear R and
  reference.
- `status`: campaign state; generated plans start as `planned`.
- `attempt_number`: planned first attempt number.
- `notes`: operator or campaign notes.

## Experiment 2 Raw Trial Files

The canonical raw audio file per attempt is `raw_input.wav`:

- WAV IEEE float32;
- three logical channels in fixed order `[ear_L, ear_R, electrical_reference]`;
- native stream sample rate, normally 48 kHz;
- no normalization, limiter, compression, independent L/R alignment or
  destructive filtering;
- includes pre-silence, sweep, post-silence and any documented zero padding.

`metadata.json` records the nominal physical angle, wrapped angle, speaker,
repetition, attempt, stream configuration, channel mapping, stimulus hash,
operator confirmations and QC decision.

`callback_timeline.csv` records one row per audio callback/block. At minimum it
should contain absolute frame index, frames in block, PortAudio status flags and
available host/device timing fields. Experiment 2 does not record BLE telemetry.

## Benchmark Result Tables

All angular fields use `_deg`, delays use `_ms`, sample rates use `_hz`, linear
gains use `_linear`, and logarithmic gains use `_db`.
