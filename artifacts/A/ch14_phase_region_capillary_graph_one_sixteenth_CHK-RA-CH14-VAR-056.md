# CHK-RA-CH14-VAR-056 - PhaseRegion Capillary Graph 1/16 Period Run

Date: 2026-05-17

Scope: run the reduced PhaseRegion capillary-wave graph route to one sixteenth
of the capillary-wave period on the GPU hot path.

## Setup

The experiment uses the existing reduced graph route:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
assemble_phase_region_measurement(...)
linearized E_h second-variation modal step
```

The target time is:

```text
t_final / T = 1/16 = 0.0625
```

The run used `steps=160` and `dt=T/(16*160)`:

```text
dt = 1.8258978071552653e-05
```

## Remote Experiment

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--use-gpu --steps 160 --dt 1.8258978071552653e-05'
```

Result: PASS.

```text
phase_region_graph_steps_admitted = 1
steps                             = 160
dt                                = 1.825897807155e-05
t_final                           = 2.921436491448e-03
t_over_T                          = 6.249999999998e-02
max_amplitude_error               = 7.543944039335e-12
max_velocity_error                = 5.298667758030e-09
max_energy_drift                  = 2.205460807437e-07
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 5.421010862428e-20
max_step_wall_seconds             = 3.927496820688e-02
target_met                        = 1
final_amplitude                   = 1.847758989583e-04
final_exact_amplitude             = 1.847759065023e-04
force_admissible                  = 0
```

The final normalized amplitude is approximately `0.9238795`, consistent with
`cos(pi/8)` at `T/16`.

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/data.npz
experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/phase_region_capillary_graph_steps.pdf
```

Rendered preview:

```text
/private/tmp/phase_region_capillary_graph_steps_one_sixteenth.png
```

## Boundary

This is still the reduced graph-chart PhaseRegion experiment, not the
production Navier--Stokes runtime route.  `force_admissible=0` remains correct.

[SOLID-X] Experiment execution/artifact/wiki/ledger only; no code, solver
algorithm, YAML physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback,
production graph/closed PhaseRegion face-force route, nodal `force_components`
route, T/8 runtime run, main merge, branch deletion, worktree removal, or
origin push changed.
