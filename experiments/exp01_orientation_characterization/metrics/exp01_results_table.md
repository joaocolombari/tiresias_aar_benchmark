# Experiment 1 Summary Tables

## Orientation

| Metric | Sign-corrected | Drift-corrected |
|---|---:|---:|
| MAE (deg) | 20.43 | 0.356 |
| RMSE (deg) | 23.74 | 0.473 |
| Bias (deg) | -20.43 | 0.000 |
| Max abs error (deg) | 51.48 | 2.043 |

## BLE Timing

| Run | Rate (Hz) | Mean interval (ms) | Interval P95 (ms) | Jitter P95 (ms) | Seq step mode | Packet loss vs modal step (%) |
|---|---:|---:|---:|---:|---:|---:|
| ascending | 40.81 | 24.50 | 37.52 | 17.56 | 2 | 0.000 |
| descending | 40.66 | 24.60 | 43.90 | 22.36 | 2 | 0.196 |
| randomized | 40.70 | 24.57 | 40.67 | 22.28 | 2 | 0.131 |

Packet loss is reported relative to the modal sequence-counter step. If the firmware sequence counter is expected to increment by one per notification, also inspect `packet_loss_percent_assuming_unit_seq` in `exp01_ble_summary.csv`.
