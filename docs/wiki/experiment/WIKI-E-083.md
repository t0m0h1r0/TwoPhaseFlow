# WIKI-E-083 - Ch14 PhaseRegion Graph YAML One-Period PASS

## Claim

The corrected new-route capillary-wave YAML is
`config/ch14_capillary.yaml`, and it runs the
PhaseRegion graph route for one full period with GPU exact graph-column
measurement enabled.

## Evidence

Artifact:

```text
artifacts/A/ch14_phase_region_graph_yaml_one_period_CHK-RA-CH14-VAR-059.md
```

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
```

Result:

```text
phase_region_graph_steps_admitted = 1
steps                             = 2560
t_over_T                          = 1.000000000000e+00
step_backend_gpu                  = 1
q_measurement_fast_column_integral= 1
max_amplitude_error               = 2.416836235604e-10
max_velocity_error                = 4.456387104473e-08
max_energy_drift                  = 1.505982113082e-06
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 3.977783117443e-02
target_met                        = 1
force_admissible                  = 0
```

## Correction Note

WIKI-E-082 records a legacy production-runtime one-period run.  It is valid as
production-route evidence, but it is not the new PhaseRegion graph route.

## Boundary

This card authorizes only the reduced PhaseRegion graph route under the
canonical capillary filename.  It does not authorize production
pressure/velocity coupling.
