# Experiment 1 Summary Tables

## Orientation Across Runs

| Metric | Sign-corrected, mean +/- SD | Drift-corrected, mean +/- SD |
|---|---:|---:|
| MAE (deg) | 20.43 +/- 5.752 | 0.356 +/- 0.104 |
| RMSE (deg) | 23.14 +/- 6.526 | 0.462 +/- 0.125 |
| Bias (deg) | -20.43 +/- 5.752 | 0.000 +/- 0.000 |
| Max abs error (deg) | 38.56 +/- 11.30 | 1.631 +/- 0.697 |
| Closure error (deg) | -25.34 +/- 11.98 | -0.273 +/- 1.240 |
| Drift slope (deg/min) | -2.856 +/- 0.395 | corrected by model |

## Orientation By Run

| Run | MAE sign-corrected (deg) | MAE drift-corrected (deg) | RMSE drift-corrected (deg) | Closure drift-corrected (deg) | Drift slope (deg/min) |
|---|---:|---:|---:|---:|---:|
| ascending | 17.42 | 0.361 | 0.476 | -1.704 | -2.444 |
| descending | 16.81 | 0.249 | 0.330 | 0.418 | -2.892 |
| randomized | 27.06 | 0.457 | 0.580 | 0.467 | -3.231 |

## BLE Timing Across Runs

| Metric | Mean +/- SD |
|---|---:|
| Effective notification rate (Hz) | 40.72 +/- 0.080 |
| Mean interval (ms) | 24.56 +/- 0.048 |
| Interval P95 (ms) | 40.70 +/- 3.188 |
| Interval P99 (ms) | 59.43 +/- 5.999 |
| Jitter P95 from median (ms) | 20.73 +/- 2.750 |
| Packet loss vs modal seq step (%) | 0.109 +/- 0.100 |

## BLE Timing By Run

| Run | Rate (Hz) | Mean interval (ms) | Interval P95 (ms) | Jitter P95 (ms) | Seq step mode | Packet loss vs modal step (%) |
|---|---:|---:|---:|---:|---:|---:|
| ascending | 40.81 | 24.50 | 37.52 | 17.56 | 2 | 0.000 |
| descending | 40.66 | 24.60 | 43.90 | 22.36 | 2 | 0.196 |
| randomized | 40.70 | 24.57 | 40.67 | 22.28 | 2 | 0.131 |

Packet loss is reported relative to the modal sequence-counter step. If the firmware sequence counter is expected to increment by one per notification, also inspect `packet_loss_percent_assuming_unit_seq` in `exp01_ble_summary.csv`.
