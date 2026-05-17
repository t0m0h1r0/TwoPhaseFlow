# CHK-RA-CH14-VAR-046 - Runtime Force Dry-Run G0--G3 Metrics

Date: 2026-05-17

Scope: wire the validated pressure/velocity G0--G3 diagnostic gates into the
existing Chapter 14 PhaseRegion runtime force dry-run.  This checkpoint keeps
the dry-run zero-step and keeps `force_admissible=false`.  It does not expose a
runtime force, perform a micro-step, or run T/8.

## Implementation

Updated:

```text
experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

The dry-run now builds:

```text
G0 face-space report
G1 pressure-range report
G2 work-closure report
G3 explicit face-projection oracle report
```

using the same PhaseRegion admission candidate.  The pressure input for the
diagnostic gates is the Hodge range component from the existing force
diagnostics, so the dry-run proves the pressure/velocity gate algebra without
connecting to production PPE or the nodal `force_components` route.

## Key Metrics

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
```

Result: PASS.

```text
g0_valid                         = 1.000000000000e+00
boundary_residual_linf           = 0.000000000000e+00
surface_velocity_work            = 3.495281327147e-01
pressure_velocity_work           = 3.493905270806e-01
g1_valid                         = 1.000000000000e+00
pressure_hodge_weighted_l2       = 1.216174229615e-14
pressure_hodge_ratio             = 4.453077049833e-16
surface_hodge_weighted_l2        = 5.419985591685e-01
surface_hodge_ratio              = 1.984161596418e-02
g2_valid                         = 1.000000000000e+00
work_closure_residual            = 2.481405282624e-07
same_weight_surface_work_residual = 5.551115123126e-17
g3_valid                         = 1.000000000000e+00
projection_identity_linf         = 2.081668171172e-17
pressure_update_weighted_l2      = 2.731087326821e-03
surface_update_weighted_l2       = 2.731625086117e-03
projected_weighted_l2            = 1.279680161323e-02
force_admissible                 = 0.000000000000e+00
```

Existing force metrics remained consistent:

```text
self_fd_power_residual           = 2.481405282624e-07
self_riesz_residual              = 0.000000000000e+00
hodge_divergence_linf            = 1.083435563487e-09
reaction_residual_divergence_linf = 2.313299773959e-09
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/data.npz
experiment/ch14/results/diagnose_phase_region_runtime_force_dry_run/phase_region_runtime_force_dry_run.pdf
```

## Boundary

The dry-run still does not admit a force to runtime.  The next gate must decide
whether a production-adjacent adapter may expose a face force after checking
G0--G3 at runtime.  Micro-step and T/8 remain blocked.

[SOLID-X] Experiment diagnostic metrics only; no production force path,
runtime force route, YAML route, experiment physical parameter,
pressure/velocity coupling, runtime projection step, solver algorithm,
nonlinear optimizer implementation, GPU runtime path, CFL, damping, smoothing,
tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU
fallback, micro-step, T/8 runtime run, main merge, branch deletion, worktree
removal, or origin push changed.
