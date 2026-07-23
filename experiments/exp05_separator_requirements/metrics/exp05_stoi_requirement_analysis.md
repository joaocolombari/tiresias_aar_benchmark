# Experiment 5 STOI Requirement Analysis

Criterion: mean STOI loss relative to the ideal zero-delay, no-leakage source-overlay output must be <= 0.05.

Scope: sigma=30 deg, orientation delay=0 ms, velocities 30/60/120 deg/s, source-estimate delays 0/20/40/80/120/160/200 ms.

This table is derived from `exp05_source_delay_plot_summary.csv`; no audio was reprocessed.

## Summary

- Tested combinations: 21
- Accepted combinations: 3
- Minimum SDR labels: {'5': 3, 'not_met': 18}

## Table

| Velocity (deg/s) | Source delay (ms) | Min SDR label | Acceptable | STOI loss |
|---:|---:|---:|:---:|---:|
| 30 | 0 | 5 | true | 0.029 |
| 30 | 20 | not_met | false | 0.246 |
| 30 | 40 | not_met | false | 0.354 |
| 30 | 80 | not_met | false | 0.440 |
| 30 | 120 | not_met | false | 0.497 |
| 30 | 160 | not_met | false | 0.516 |
| 30 | 200 | not_met | false | 0.521 |
| 60 | 0 | 5 | true | 0.041 |
| 60 | 20 | not_met | false | 0.266 |
| 60 | 40 | not_met | false | 0.389 |
| 60 | 80 | not_met | false | 0.488 |
| 60 | 120 | not_met | false | 0.549 |
| 60 | 160 | not_met | false | 0.572 |
| 60 | 200 | not_met | false | 0.569 |
| 120 | 0 | 5 | true | 0.044 |
| 120 | 20 | not_met | false | 0.276 |
| 120 | 40 | not_met | false | 0.403 |
| 120 | 80 | not_met | false | 0.510 |
| 120 | 120 | not_met | false | 0.574 |
| 120 | 160 | not_met | false | 0.591 |
| 120 | 200 | not_met | false | 0.582 |
