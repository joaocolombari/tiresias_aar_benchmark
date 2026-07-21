# Global Sigma Ranking

Score definition: target-side angular mean `Delta TIR` is computed per `pair_id` and sigma by integrating only the yaw region where the target is at least as close to the head direction as the interferer. `global_score_db` is the lower bound of the deterministic pair-bootstrap 95% CI.

| Rank | Sigma (deg) | Mean (dB) | Median (dB) | 95% CI (dB) | Score (dB) | P10 (dB) | Positive pairs | Practical tie |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 30 | 5.47 | 5.47 | [5.47, 5.47] | 5.47 | 5.47 | 100% | yes |
| 2 | 45 | 5.08 | 5.08 | [5.08, 5.08] | 5.08 | 5.08 | 100% | no |
| 3 | 20 | 4.77 | 4.77 | [4.77, 4.77] | 4.77 | 4.77 | 100% | no |
| 4 | 60 | 4.11 | 4.11 | [4.11, 4.11] | 4.11 | 4.11 | 100% | no |
| 5 | 10 | 2.77 | 2.77 | [2.77, 2.77] | 2.77 | 2.77 | 100% | no |
