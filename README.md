# Tiresias AAR Benchmark

Minimal research repository for characterizing the Tiresias head-orientation-driven
monophonic attention model.

This repository is intentionally separate from the firmware and desktop demo
applications. It keeps only the research path needed for:

- BLE telemetry recording and CSV replay;
- scalar monophonic Gaussian attention gains;
- measured two-channel room transfer responses from the rotating rig;
- orientation delay and source-leakage emulation;
- objective metrics for orientation, telemetry, and audio experiments.

The measured binaural responses are used only in the offline benchmark renderer.
They replace the analytical ITD/ILD renderer in those experiments and are not
described as standardized HRTFs.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[ble,metrics]"
python -m unittest discover -s tests
```

BLE is optional. All experiment commands accept replay or offline data.

## CLI Examples

```bash
python -m tiresias_benchmark telemetry-record --output experiments/exp01_orientation_characterization/raw/session.csv
python -m tiresias_benchmark telemetry-replay --input experiments/exp01_orientation_characterization/raw/session.csv --delay-ms 80
python -m tiresias_benchmark sweep-generate --config configs/acquisition.yaml --output experiments/exp02_brir_measurement/raw/sweep.wav
python -m tiresias_benchmark experiment-run --experiment 1 --config experiments/exp01_orientation_characterization/config.yaml
python -m tiresias_benchmark experiment-run --experiment 4 --config experiments/exp04_latency_sensitivity/config.yaml
```

## Repository Layout

```text
src/tiresias_benchmark/
  telemetry/     BLE packet decoding, logging and replay
  orientation/   Quaternion convention, yaw extraction and tare calibration
  attention/     Monophonic Gaussian attention and simple baselines
  acoustics/     Sweeps, deconvolution, BRIR loading and rendering
  separation/    Leakage and source-estimate delay emulation
  metrics/       Orientation, telemetry, audio and transition metrics
  experiments/   Reproducible experiment entry points
```

See `docs/` for provenance, data schemas, protocol, limitations and migration notes.
