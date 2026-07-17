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

Only one Neumann is active during a sweep. The inactive speaker output and
unused output 4 must be digital zero. The reference cable must be line-level
and must not receive phantom power.

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
