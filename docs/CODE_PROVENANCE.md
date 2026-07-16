# Code Provenance

## `src/tiresias_benchmark/orientation/quaternion.py`

- Based on: `desktop_application/yaw-walk-with-me/aar_core.py:9-81`.
- Symbols adapted: `quaternion_to_euler`, `euler_to_quaternion`,
  `quaternion_conjugate`, `quaternion_multiply`, `quat_rotate`,
  `source_relative_angle`.
- Relationship: preserves scalar-first `(qw, qx, qy, qz)` convention used by
  firmware BLE payload and host decoding.

## `src/tiresias_benchmark/orientation/calibration.py`

- Based on: `desktop_application/yaw-walk-with-me/main.py:190-217`.
- Symbols adapted: `tare_quaternion = quaternion_conjugate(q_raw)` and
  `quaternion_multiply(tare_quaternion, q_raw)`.
- Relationship: matches host-side calibration/taring, not a firmware feature.

## `src/tiresias_benchmark/attention/gaussian.py`

- Based on: `desktop_application/yaw-walk-with-me/aar_core.py:83-109`.
- Symbols adapted: `compute_attention`.
- Equations preserved: distance factor `ref_dist / max(distance, ref_dist)`,
  Gaussian `exp(-(angle**2)/(2*sigma**2))`, gain mapping
  `10 ** ((bmax_db * attention_norm) / 20)`.
- Relationship: consumes calibrated quaternion/yaw from telemetry and produces
  one scalar source gain per monophonic source.

## `src/tiresias_benchmark/telemetry/decoder.py`

- Based on: `desktop_application/yaw-walk-with-me/experiment_protocol.py:5-76`.
- Symbols adapted: `TELEMETRY_CHAR_UUID`, `LEGACY_QUATERNION_CHAR_UUID`,
  `decode_telemetry_packet`, `decode_legacy_quaternion`.
- Relationship: matches firmware GATT characteristics in
  `firmware/tiresias-workspace/tiresias-fw/src/services/bluetooth/modules/orientation/orientation.c:17-35`.

## `src/tiresias_benchmark/telemetry/logger.py`

- Based on: `desktop_application/yaw-walk-with-me/experiment_logging.py:6-92`.
- Symbols adapted: `OrientationLogger` field structure.
- Relationship: adds explicit unit suffixes and packet-loss/receive-interval
  fields for experiment 1.

## `src/tiresias_benchmark/acoustics/*`

- New research implementation.
- Relationship: replaces analytical ITD/ILD in the offline benchmark with
  measured orientation-dependent two-channel rig responses.

## `src/tiresias_benchmark/separation/leakage.py`

- New research implementation.
- Relationship: emulates imperfect monophonic source estimates without
  changing the attention model.

## `src/tiresias_benchmark/metrics/*`

- New research implementation.
- Relationship: computes the objective measures needed for firmware timing,
  angular tracking and offline acoustic benchmarks.
