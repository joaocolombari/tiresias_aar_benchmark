# Experiment 2: BRIR Measurement

This experiment measures binaural room impulse responses for the mannequin
setup. It does not use BLE. The only goal is to capture the acoustic transfer
functions from each Neumann monitor to the two Earthworks microphones for every
head position.

The acquisition path is:

```text
exponential sine sweep
-> one Neumann monitor at a time
-> room/mannequin acoustics
-> Earthworks L/R
-> Scarlett/Core Audio
-> raw_input.wav
-> deconvolution with electrical reference
-> left/right BRIR files
```

The measured BRIRs are used later in the offline benchmark renderer. The
attention model remains monophonic and is not part of this acquisition.

## Physical Routing

Nominal routing on the Scarlett:

| Port | Signal | Rule |
|---|---|---|
| input 1 | Earthworks L | captured on every sweep |
| input 2 | Earthworks R | captured on every sweep |
| stream input 3 | electrical reference | loopback from output 3 |
| output 1 | Neumann A | active only for speaker A trials |
| output 2 | Neumann B | active only for speaker B trials |
| output 3 | reference copy | copy of the active speaker drive |

Measured campaign geometry:

- physical zero: mannequin facing the frontal reference;
- positive platform rotation: clockwise;
- Neumann A azimuth: `-30 deg`;
- Neumann B azimuth: `+30 deg`;
- Neumann distance: `1.0 m` from the mannequin nose.

Only one Neumann is active during a sweep. The inactive speaker output and
unused output 4 must be digital zero. The reference cable must be line-level
and must not receive phantom power.

The Scarlett must not monitor the electrical-reference path in real time.
Before acquisition, disable direct monitoring and remove physical inputs,
loopback/reference channels and alternate mixes from monitor/headphone outputs.
Line output 1 should receive only stream/DAW 1, line output 2 only stream/DAW 2,
and line output 3 only stream/DAW 3. Output 3 is a measurement reference, not an
audible monitor output.

It is expected that one physical Neumann appears in both Earthworks channels.
It is not acceptable for a single-speaker routing probe to drive both Neumanns.

## Platform Angles

Measure:

```text
0, 10, 20, ..., 350, 360 deg
```

The nominal 360 deg position is a closure measurement. It wraps to 0 deg for
angle comparison, but it remains a separate trial identity and file path.

## Planned Campaign

The complete campaign has:

- 37 angle blocks;
- 2 speakers: A and B;
- 2 independent repetitions per speaker;
- 148 planned sweeps;
- 296 expected impulse responses, one left-ear and one right-ear IR per sweep.

Trial names:

```text
brir_theta_000_spk_A_rep01
brir_theta_000_spk_B_rep01
brir_theta_360_spk_A_rep01
```

Derived IR names:

```text
brir_theta_000_spk_A_rep01_ear_L
brir_theta_000_spk_A_rep01_ear_R
```

The acquisition order alternates speaker order by angle index:

- even angle index: `A1, B1, A2, B2`;
- odd angle index: `B1, A1, B2, A2`.

## Mac Acquisition Config

The default config is macOS/Core Audio:

```yaml
preferred_host_api: "Core Audio"
input_device_name_contains: "Scarlett"
output_device_name_contains: "Scarlett"
open_input_channel_count: 4
open_output_channel_count: 4
stream_dtype: auto
stream_dtype_candidates: [float32]
storage_dtype: float32
```

If PortAudio lists the Scarlett under a different name, edit
`input_device_name_contains` and `output_device_name_contains`, or set them to
empty strings after confirming that the Scarlett is the only Core Audio device
with enough channels.

## Commands

Install:

```bash
python -m pip install -e ".[acquisition,metrics,dev]"
```

Generate/validate the plan:

```bash
python -m tiresias_benchmark experiment-run \
  --experiment 2 \
  --config experiments/exp02_brir_measurement/config.yaml
```

List Core Audio devices and candidate pairs:

```bash
python -m tiresias_benchmark exp02-audio-list-devices \
  --config experiments/exp02_brir_measurement/config.yaml
```

Probe supported stream formats:

```bash
python -m tiresias_benchmark exp02-audio-format-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output experiments/exp02_brir_measurement/metrics/audio_format_probe.json
```

Run full-duplex zero-output preflight:

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

Run a real low-level channel probe. This emits audio and requires `--armed`:

```bash
python -m tiresias_benchmark exp02-channel-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --session-id exp02_probe_YYYYMMDD \
  --armed
```

For physical routing diagnosis, use the output-isolation probe. It emits a tone
on exactly one stream output and records all open input channels:

```bash
python -m tiresias_benchmark exp02-output-probe \
  --config experiments/exp02_brir_measurement/config.yaml \
  --output-index 0 \
  --session-id exp02_route_check \
  --armed \
  --overwrite
```

Repeat for `--output-index 1` and `--output-index 2`.

Expected result:

- `output-index 0`: only Neumann A is audible;
- `output-index 1`: only Neumann B is audible;
- `output-index 2`: electrical reference only, no acoustic sound.

If `output-index 2` is audible through the monitors, the Scarlett is monitoring
the reference/loopback path and the routing must be fixed before BRIR
acquisition.

Record one pilot sweep:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id exp02_pilot_YYYYMMDD \
  --armed
```

## Official Campaign Procedure

Use a fresh session id for the official campaign, for example:

```bash
SESSION_ID=exp02_campaign_20260718_001
```

For official data:

- do not pass `--overwrite`;
- keep failed takes as later attempts;
- do not change gains, monitor volume, Focusrite routing, microphone positions
  or loudspeaker positions inside one session;
- if any physical setting changes, stop and start a new session id;
- check `qc.json` before moving the platform to the next angle.

The planned acquisition order is written to:

```text
experiments/exp02_brir_measurement/metrics/exp02_plan.csv
```

Each physical angle block has four sweeps. Even angle indices use:

```text
A1, B1, A2, B2
```

Odd angle indices use:

```text
B1, A1, B2, A2
```

The nominal `360 deg` block is a closure measurement and must remain stored as
`theta_360`; it must not be merged with `theta_000` during acquisition.

Example for an even-index angle block:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker A \
  --angle 0 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed

python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 2 \
  --session-id "$SESSION_ID" \
  --armed
```

Example for repeating a failed take without overwriting:

```bash
python -m tiresias_benchmark exp02-record-test-sweep \
  --config experiments/exp02_brir_measurement/config.yaml \
  --speaker B \
  --angle 0 \
  --repetition 1 \
  --session-id "$SESSION_ID" \
  --attempt 2 \
  --armed
```

Only move to the next angle after checking the four `qc.json` files for the
current block.

## Deconvolution

After acquisition, process a full session with:

```bash
python -m tiresias_benchmark brir-process \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001
```

Use `--overwrite` only to regenerate already processed BRIR outputs, never for
official raw acquisition attempts.

The processor reads `raw_input.wav` as:

```text
[ear_L, ear_R, electrical_reference]
```

It deconvolves both ears against the electrical reference and applies one common
left/right IR window. This preserves measured ITD; the two ears are not
independently peak-aligned.

Outputs:

```text
processed/<SESSION_ID>/irs/
processed/<SESSION_ID>/metadata/
metrics/<SESSION_ID>/brir_processing_summary.csv
metrics/<SESSION_ID>/brir_processing_summary.json
```

Each trial produces two individual ear responses and one stereo response:

```text
brir_theta_000_spk_A_rep01_ear_L.wav
brir_theta_000_spk_A_rep01_ear_R.wav
brir_theta_000_spk_A_rep01_stereo.wav
```

The processing summary reports `itd_ms`, `ild_db`, RMS levels,
`loopback_lag_ms` and `loopback_correlation`.

Note: acquisition `qc.json` may report `low_reference_correlation` because the
acquisition QC uses zero-lag correlation. For processing validation, use the
lag-compensated loopback fields in `brir_processing_summary.csv`.

## Reconvolution Validation

Validate the estimated BRIRs by reconvolving the captured electrical reference
with the estimated IRs and comparing the predicted microphones against the
experimental `raw_input.wav`:

```bash
python -m tiresias_benchmark brir-validate \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001 \
  --mode both
```

Modes:

- `same`: estimate and predict the same trial;
- `cross`: use rep01 to predict rep02 and rep02 to predict rep01;
- `both`: run both validations.

`same` is an optimistic reconstruction check. `cross` is the more useful
repeatability check for future convolution-based simulations.

Outputs:

```text
metrics/<SESSION_ID>/brir_validation_summary.csv
metrics/<SESSION_ID>/brir_validation_summary.json
```

The summary reports prediction SDR, correlation, normalized RMS error, residual
RMS and optional gain-corrected SDR for each ear and for the ear average.

To also write predicted and residual WAV files:

```bash
python -m tiresias_benchmark brir-validate \
  --config experiments/exp02_brir_measurement/config.yaml \
  --session-id exp02_campaign_20260718_001 \
  --mode both \
  --write-wavs
```

## Trial Artifacts

Each probe/test sweep writes:

```text
raw_input.wav
playback_output.wav
metadata.json
callback_timeline.csv
qc.json
```

`raw_input.wav` contains three float32 channels:

```text
[ear_L, ear_R, electrical_reference]
```

This is the input to deconvolution and later BRIR export.

## QC Gates

Minimum checks:

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
- repeatability between rep01 and rep02.

The electrical reference is the timing reference for deconvolution.
