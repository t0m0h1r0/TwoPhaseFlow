# CHK-RA-CH14-VAR-054 - PhaseRegion Oscillating Droplet Few-Step Experiment

Date: 2026-05-17

Scope: answer whether the oscillating droplet also moves for a few steps on the
same new PhaseRegion route used by the capillary-wave graph experiment.

## Motivation

CHK-RA-CH14-VAR-053 moved the graph capillary-wave route for eight reduced
PhaseRegion-owned steps:

```text
eta -> q_l=Q_h(eta) -> q_g=|C|-q_l -> GAS_ABOVE graph PhaseRegionBatch
```

The matching closed-chart question is whether the droplet can advance with the
same ownership order:

```text
X(theta) -> q_l=Q_h(X) -> q_g=|C|-q_l -> GAS_OUTSIDE closed PhaseRegionBatch
```

without using the production Navier--Stokes runtime, pressure projection,
face-cochain consumer, damping, smoothing, CFL retuning, or a hidden fallback.

## Implemented Experiment

Added:

```text
experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py
```

The experiment reads `ch14_oscillating_droplet.yaml`, builds the same diagnostic
initial fitted grid, and owns the droplet as an area-preserving mode-2 closed
radial chart.  The reduced stepping equation is:

```text
E_h[X]     = sigma L_h[X]
K_h        = d^2 E_h / dA^2 at the circle, with fixed droplet area
omega0     = YAML Rayleigh-Lamb / Prosperetti reference frequency
M_mode     = K_h / omega0^2
M_mode A'' + K_h A = 0
```

The amplitude is advanced by velocity-Verlet.  At each time level, the
experiment rebuilds:

```text
X(A) -> q_l = Q_h(X(A))
q_g = |C| - q_l
PhaseRegionBatch(GAS_OUTSIDE closed radial)
assemble_phase_region_measurement(...)
```

and checks exact linear oscillator phase, energy drift, volume drift, and
PhaseRegion residuals.

## Remote Experiment

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py
```

Result: PASS.

```text
phase_region_droplet_steps_admitted = 1
steps                               = 8
dt                                  = 2.000000000000e-05
t_final                             = 1.600000000000e-04
t_over_T                            = 1.517153366218e-03
max_amplitude_error                 = 2.687954026026e-15
max_velocity_error                  = 3.359899413812e-11
max_energy_drift                    = 3.225430493134e-11
max_residual_l2                     = 0.000000000000e+00
max_volume_drift                    = 5.428131902296e-13
final_amplitude                     = 4.999772827646e-04
final_exact_amplitude               = 4.999772827673e-04
force_admissible                    = 0
```

Outputs:

```text
experiment/ch14/results/diagnose_phase_region_oscillating_droplet_steps/data.npz
experiment/ch14/results/diagnose_phase_region_oscillating_droplet_steps/phase_region_oscillating_droplet_steps.pdf
```

## Remote Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py twophase/tests/test_q_manifold_projection.py -q'
```

Result: PASS.  The current remote make target ran the suite under its
configured root:

```text
867 passed, 35 skipped
```

## Verdict

Yes: the oscillating droplet also moves for a few steps on the new
PhaseRegion-owned route at the reduced closed-chart level.

This is not a production Navier--Stokes runtime result.  The dynamic nonuniform
runtime droplet still has the known two-step face-history reprojection blocker,
and `force_admissible=0` remains correct until the graph/closed chart
face-cochain consumer is connected to pressure/velocity work gates and a
controlled micro-step updates solver-owned state.

[SOLID-X] Experiment stepper/artifact/wiki/ledger only; no solver algorithm,
YAML physical parameter, CFL, damping, smoothing, tolerance weakening, rebuild
skipping, FD/WENO/PPE fallback, hidden CPU fallback, production graph or closed
PhaseRegion face-force route, nodal `force_components` route, T/8 runtime run,
main merge, branch deletion, worktree removal, or origin push changed.
