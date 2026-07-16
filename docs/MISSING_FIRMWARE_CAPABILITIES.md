# Missing Firmware Capabilities

The current benchmark remains compatible with the legacy 16-byte quaternion
stream, but the following measurements require firmware support to be available
in recorded CSV files:

- Monotonically increasing sequence number.
- Device timestamp attached near sensor acquisition time.
- Raw accelerometer and gyroscope samples in the orientation packet.
- Firmware-computed yaw for raw-vs-host yaw comparison.
- Calibration state, if calibration is moved into firmware later.

In the observed workspace copy, these fields are represented by the 64-byte
telemetry packet. On unmodified legacy firmware they cannot be inferred from
the BLE quaternion alone.
