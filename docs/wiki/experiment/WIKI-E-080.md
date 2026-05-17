# WIKI-E-080 - Ch14 PhaseRegion Capillary Graph 1/16 Period PASS

## Claim

The reduced PhaseRegion capillary-wave graph route runs to `T/16` on the GPU
hot path and stays aligned with the exact linear capillary-wave reference.

## Evidence

Artifact:

```text
artifacts/A/ch14_phase_region_capillary_graph_one_sixteenth_CHK-RA-CH14-VAR-056.md
```

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu --steps 160 --dt 1.8258978071552653e-05'
```

Result:

```text
phase_region_graph_steps_admitted = 1
t_over_T                          = 6.249999999998e-02
max_amplitude_error               = 7.543944039335e-12
max_velocity_error                = 5.298667758030e-09
max_energy_drift                  = 2.205460807437e-07
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 3.927496820688e-02
target_met                        = 1
force_admissible                  = 0
```

## Boundary

Use this card as evidence for the reduced graph-chart `T/16` run only.  It does
not authorize production Navier--Stokes runtime coupling, nodal
`force_components`, a closed-chart GPU hot path, or T/8 execution.
