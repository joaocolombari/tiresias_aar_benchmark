# Migration Report

This repository was created as a new minimal research repository, not as a copy
of the desktop demonstration application.

## Source Repositories Inspected

- `desktop_application/yaw-walk-with-me/aar_core.py:9-134`
- `desktop_application/yaw-walk-with-me/main.py:36-54,135-181,190-230,241-272,312-313`
- `desktop_application/yaw-walk-with-me/experiment_protocol.py:5-76`
- `desktop_application/yaw-walk-with-me/experiment_logging.py:6-92`
- `firmware/tiresias-workspace/tiresias-fw/src/services/imu/imu.c:20-23,89-115,154-227`
- `firmware/tiresias-workspace/tiresias-fw/src/modules/head_tracking.c:23-45,116-213`
- `firmware/tiresias-workspace/tiresias-fw/src/services/bluetooth/modules/orientation/orientation.c:17-35,71-89,97-135,139-181`
- `firmware/tiresias-workspace/tiresias-fw/src/utils/zbus_common.h:113-157`

## What Was Migrated

- Scalar-first quaternion math from `aar_core.py`.
- First-packet tare calibration from `main.py::notification_handler`.
- BLE packet decoding for legacy 16-byte quaternion and observed 64-byte
  telemetry packets from `experiment_protocol.py`.
- CSV telemetry fields from `experiment_logging.py`, with explicit units.
- Monophonic Gaussian attention and gain mapping from `aar_core.py::compute_attention`.
- Optional analytical ITD/ILD is not migrated into the benchmark path; measured
  rig responses are the experimental renderer.

## What Was Not Migrated

- PyQtGraph visualization, STL model loading and UI loop.
- Sound-object animation and live demo assets.
- Real-time sounddevice output path.
- Firmware code.
- Experimental WAV files, logs or generated figures.

## Compatibility Decision

The benchmark accepts both packet formats:

- legacy `<ffff>` quaternion characteristic, 16 bytes;
- telemetry v1 `<BBHII11fBBHI>`, 64 bytes.

Missing sequence number, device timestamp and raw IMU values are represented as
empty CSV fields when legacy packets are used.
