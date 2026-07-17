# Experiment 1: Orientation Characterization

Place the mannequin at known static yaw angles over a full revolution:

`0, 10, 20, ..., 350, 360 deg`.

The 36 directions from 0 deg through 350 deg are the unique spatial
orientations. The 360 deg endpoint is physically equivalent to 0 deg and is
preserved as a closure/repeatability measurement, but it is excluded from global
angular-error statistics.

## Runs

- Ascending: `0, 10, ..., 350, 360`.
- Descending: `360, 350, ..., 10, 0`.
- Randomized: all 36 unique directions exactly once using the configured seed,
  then a final 360 deg closure measurement.

The recommended acquisition workflow records these runs as three separate
guided sessions. This keeps each session short enough to inspect immediately
and limits the effect of long-run drift on operator decisions. The all-in-one
mode remains available for compatibility.

Each segmented row should store both:

- `reference_angle_commanded_deg`: physical commanded position, preserving 360.
- `reference_angle_normalized_deg`: commanded position modulo 360, so 360 maps
  to 0.

## Coordinate Transformation

The migrated host application's quaternion and yaw sign are preserved. The
comparison transformation is:

1. Physical platform command:
   `reference_angle_commanded_deg`.
2. Normalized reference:
   `reference_angle_normalized_deg = reference_angle_commanded_deg mod 360`.
3. Calibrated Tiresias yaw:
   `calibrated_yaw_deg`, in the host application's convention.
4. Normalized measured yaw:
   `measured_yaw_360_deg = calibrated_yaw_deg mod 360`.
5. Circular error:
   `error_deg = ((measured_yaw_360_deg - reference_angle_normalized_deg + 180) mod 360) - 180`.

The physical positive rotation direction is configured explicitly by
`coordinate_system.positive_rotation_direction`. The code does not infer or
change the BMI270/host yaw sign; it compares the recorded calibrated yaw after
the explicit modulo normalization above.

## Default Timing

- settling time: 3 s;
- acquisition time per position: 10 s;
- discarded transient after positioning: 2 s;
- analyzed stationary interval: 8 s;
- optional static drift before or after a guided session: 120 s each.

The output metrics are angular MAE, RMSE, bias, maximum error, drift, update
interval, packet loss and per-run closure error.
