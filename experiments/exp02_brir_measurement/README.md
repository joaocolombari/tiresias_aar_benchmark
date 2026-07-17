# Experiment 2: Native BRIR Measurement

This experiment measures binaural room impulse responses (BRIRs) on the
Tiresias rotating mannequin rig. REW is not used. The intended acquisition path
is a native Python full-duplex stream that generates the sweep, drives one
studio monitor, records both Earthworks microphones, records an electrical
reference, logs Tiresias BLE telemetry and stores every raw attempt.

The measured responses are used later by the offline benchmark renderer. The
attention model remains monophonic: it computes one scalar gain per source. A
measured BRIR turns each mono source into left and right acoustic images. The
analytical ITD/ILD renderer is bypassed in the measured-BRIR benchmark.

## Physical Rig

Nominal routing:

| Port | Signal | Rule |
|---|---|---|
| Scarlett input 1 | Earthworks L | captured on every sweep |
| Scarlett input 2 | Earthworks R | captured on every sweep |
| Scarlett stream input 3 | electrical reference | loopback from output 3 |
| Scarlett output 1 | Neumann A | active only for speaker A trials |
| Scarlett output 2 | Neumann B | active only for speaker B trials |
| Scarlett output 3 | reference copy | exact copy of the active speaker drive |

Only one Neumann is active during a sweep. The inactive speaker channel and
unused output 4 must be digital zero. The reference cable must be a line-level
loop from output 3 to the configured reference input stream channel; phantom
power must not reach this connection.

On the observed Windows machine, PortAudio exposed the Scarlett as two
separate WDM-KS devices:

- input device: `Analogue 1 + 2 (wc4800_8214)`;
- output device: `Speakers (wr4800_8214)`;
- host API: `Windows WDM-KS`;
- opened stream: 4 inputs and 4 outputs at 48 kHz.

This is valid. The app opens one full-duplex stream with
`device=(input_device_index, output_device_index)` and
`channels=(4, 4)`. It does not open two independent streams.

The platform is measured at physical angles:

`0, 10, 20, ..., 350, 360 deg`.

The nominal 360 deg position is a closure measurement and is preserved as a
separate identity. It wraps to 0 deg for angular comparison, but its files,
trial IDs and metadata are never merged with the nominal 0 deg position.

## Planned Campaign

The default campaign has:

- 37 angle blocks;
- 2 speakers: A and B;
- 2 independent repetitions per speaker;
- 148 planned sweeps;
- 296 expected impulse responses, one left-ear and one right-ear IR per sweep.

Trial names are stable and include the nominal physical angle:

```text
brir_theta_000_spk_A_rep01
brir_theta_000_spk_B_rep01
brir_theta_360_spk_A_rep01
```

Derived IR names append the ear:

```text
brir_theta_000_spk_A_rep01_ear_L
brir_theta_000_spk_A_rep01_ear_R
```

The acquisition order alternates speaker order by angle index to reduce
systematic drift/order bias:

- even angle index: `A1, B1, A2, B2`;
- odd angle index: `B1, A1, B2, A2`.

## Data Flow

For each planned trial:

1. The operator positions and locks the rotating platform at the displayed
   nominal angle.
2. The app verifies the configured Scarlett full-duplex device and channel map.
3. A float32 exponential sine sweep is routed to the active Neumann.
4. Output 3 receives a bit-identical copy of the active speaker drive.
5. Inputs 1, 2 and 5 are recorded simultaneously in the same callback.
6. BLE notifications from Tiresias are logged with host monotonic timestamps.
7. Raw audio, BLE CSV, callback timeline and metadata are committed atomically.
8. Deconvolution uses the measured electrical reference as the input signal.
9. Two IRs are exported, one for each ear, without independent L/R
   normalization or peak alignment.
10. QC decides whether the attempt passes, fails or requires a repeated take.

The raw audio must remain IEEE float32 and unnormalized. No limiter, compressor,
normalization or destructive alignment is allowed in the raw path.

## File Layout

Official data should stay outside Git except for small manifests, plans,
metrics and figures. A session should use a structure equivalent to:

```text
experiments/exp02_brir_measurement/
  raw/
    <session_id>/
      config.snapshot.yaml
      campaign.json
      campaign_state.json
      campaign_journal.jsonl
      stimulus/
      calibration/
      sweeps/
        brir_theta_000_spk_A_rep01/
          attempt_01/
            metadata.json
            raw_input.wav
            callback_timeline.csv
            ble_notifications.csv
            qc.json
            checksums.sha256
  processed/
    <session_id>/
      ir/
        brir_theta_000_spk_A_rep01_ear_L.wav
        brir_theta_000_spk_A_rep01_ear_R.wav
      arrays/
      manifests/
  metrics/
    exp02_plan.csv
    <session_id>/
      qc_summary.csv
      ir_summary.csv
      ble_summary.csv
  figures/
    <session_id>/
```

Rejected attempts are retained. A new attempt uses a new `attempt_XX`
directory and never overwrites the rejected raw data.

## Current Benchmark Commands

The benchmark repository currently implements the campaign plan generator,
first-pass native Scarlett acquisition tests and the legacy single-file
deconvolution helper. The commands below are intended to produce raw artifacts
that can be consumed by the next processing stages.

Validate the planned campaign and write `metrics/exp02_plan.csv`:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 2 \
  --config experiments/exp02_brir_measurement/config.yaml
```

Expected summary:

```text
angle_blocks: 37
unique_spatial_orientations: 36
planned_trials: 148
expected_impulse_responses: 296
closure_trials: 4
first_trial_id: brir_theta_000_spk_A_rep01
last_trial_id: brir_theta_360_spk_B_rep02
```

The old `brir-process` command still works for a minimal config containing
`recorded_wav`, `reference_wav` and `output_ir_wav`. It is not the official
native acquisition pipeline for the campaign.

See also:

- `docs/HOW_TO_RUN_EXPERIMENT_02_PTBR.md`;
- `docs/EXPERIMENT_02_TROUBLESHOOTING_PTBR.md`;
- `docs/EXPERIMENT_02_QUICK_CHECKLIST_PTBR.md`.

Install acquisition dependencies on the Windows acquisition machine:

```bash
python -m pip install -e ".[acquisition,ble,metrics,dev]"
```

List PortAudio devices and candidate input/output pairs:

```bash
python -m tiresias_benchmark exp02-audio-list-devices
```

Run a zero-output full-duplex preflight:

First, probe stream sample formats. This emits only zeros and reports which
PortAudio dtype is accepted by the selected input/output pair:

```bash
python -m tiresias_benchmark exp02-audio-format-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_format_probe.json
```

Then run the full preflight:

```bash
python -m tiresias_benchmark exp02-audio-preflight \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_preflight.json
```

Run a simulated channel probe without hardware:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --simulate \
  --overwrite
```

Run a real low-level channel probe. This emits audio and therefore requires
`--armed`:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --session-id exp02_probe_YYYYMMDD \
  --armed
```

Record one real test sweep at 0 deg. This creates a trial attempt directory
under `raw/<session_id>/sweeps/`:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_YYYYMMDD \
  --armed
```

Each probe/test sweep writes:

```text
raw_input.wav
playback_output.wav
metadata.json
callback_timeline.csv
qc.json
```

`raw_input.wav` is the input to the next deconvolution step. It contains
`[ear_L, ear_R, electrical_reference]` as IEEE float32.

## Operator Procedure

1. Configure Focusrite Control so outputs 1, 2 and 3 are independent hardware
   outputs and direct monitoring is disabled.
2. Connect Earthworks L/R to inputs 1/2 and enable phantom power only for those
   microphone inputs.
3. Connect Scarlett output 3 to the configured reference input channel.
4. Start with monitor levels attenuated and run channel probes before any loud
   sweep.
5. Confirm that a probe on output 1 reaches Neumann A and not Neumann B.
6. Confirm that a probe on output 2 reaches Neumann B and not Neumann A.
7. Confirm that output 3 is captured on the configured reference input with
   high correlation and no clipping.
8. Record room noise and a low-level pilot at 0 deg.
9. Inspect raw peaks, reference SNR, IR shape, L/R polarity and BLE coverage.
10. Only then run the 148 official trials.

Do not move the platform during a trial. If the operator touches the rig,
cable tension changes, a monitor overloads or any channel clips, mark that
attempt invalid and repeat it as a new attempt.

## QC Gates

Minimum QC checks:

- exact frame count and expected channel count;
- finite float32 samples in all raw channels;
- no PortAudio overflow/underflow/xrun flags;
- no clipping in Earthworks or reference channels;
- sufficient pre-sweep noise margin;
- sufficient electrical-reference RMS and SNR;
- high loopback correlation with the generated sweep;
- one speaker active and the other speaker silent;
- plausible direct-arrival timing in both ears;
- ITD preserved by common L/R origin and no independent peak alignment;
- repeatability between rep01 and rep02;
- BLE packet count and gap report when BLE is available.

BLE is useful for relating the BRIR measurement to the Tiresias pose, but it is
not the acoustic timing reference. The electrical loopback is the timing
reference for deconvolution.

## Hardware-Dependent Items

These must be verified on the Windows acquisition machine:

- WDM-KS or ASIO device names and channel ordering returned by `sounddevice`;
- whether the stream channel indices match the physical Scarlett routing;
- Focusrite Control routing and absence of direct-monitor leakage;
- safe output level for the Neumanns and safe input level for the reference;
- Earthworks L/R physical symmetry and serial-number mapping;
- Tiresias BLE availability during the acoustic stream;
- room-noise floor and reverberation tail length.
