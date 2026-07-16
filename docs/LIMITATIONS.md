# Limitations

- Measured responses are custom rig responses, not standardized HRTFs or KEMAR
  measurements.
- The benchmark does not claim human perceptual validity.
- Legacy BLE packets do not provide sequence number, device timestamp or raw IMU
  values.
- BLE recording requires physical Tiresias hardware and the optional `bleak`
  dependency.
- STOI requires the optional `pystoi` dependency. PESQ is intentionally not a
  default dependency.
- The experiment modules are intentionally compact and auditable; large figure
  generation and manuscript-specific plotting should be layered on top.
