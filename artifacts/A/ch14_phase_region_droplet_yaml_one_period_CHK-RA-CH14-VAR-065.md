# CHK-RA-CH14-VAR-065 — PhaseRegion Droplet YAML One-Period Run

Date: 2026-05-17

## Claim

`experiment/ch14/config/ch14_oscillating_droplet.yaml` now owns the reduced
PhaseRegion closed-chart oscillating-droplet route, mirroring the canonical
capillary-wave YAML contract:

```text
X(theta; A) -> q_l = Q_h(X)
q_g = |C| - q_l
PhaseRegionBatch(GAS_OUTSIDE closed radial chart)
E_h second-variation modal step
```

The route is not connected to the production pressure/velocity force consumer;
`force_admissible=0` remains explicit.

## Run

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py ARGS='--config experiment/ch14/config/ch14_oscillating_droplet.yaml'
```

YAML-owned timing:

- `run.time.final = 0.105460663082`
- `run.time.cfl = 1.0`
- no fixed `dt`
- snapshot times: `0`, `T/4`, `T/2`, `3T/4`, `T`

Result:

```text
phase_region_droplet_steps_admitted = 1
steps = 3977
dt = 2.651764221323e-05
t_final = 1.054606630820e-01
t_over_T = 9.999999999903e-01
dt_cfl_limit = 2.652412244614e-05
max_amplitude_error = 2.503547743871e-10
max_velocity_error = 2.046056174314e-08
max_energy_drift = 6.240056085825e-07
max_residual_l2 = 0.000000000000e+00
max_volume_drift = 1.084202172486e-19
max_q_volume_closure_raw_abs = 1.822318492916e-07
max_q_volume_closure_closed_abs = 2.710505431214e-20
max_step_wall_seconds = 3.064271062613e-03
final_amplitude = 4.999999999999e-04
final_exact_amplitude = 5.000000000000e-04
force_admissible = 0
```

Outputs:

- `experiment/ch14/results/diagnose_phase_region_oscillating_droplet_steps/data.npz`
- `signed_deformation.pdf`
- `volume_drift.pdf`
- `kinetic_energy.pdf`
- `phase_region_oscillating_droplet_steps.pdf`
- `phase_region_oscillating_droplet_yaml_snapshots.pdf`
- YAML snapshot `phi_t*.pdf`, `velocity_t*.pdf`, `pressure_t*.pdf`

## Visual check

The YAML snapshot sequence shows the expected Rayleigh--Lamb mode-2 phase:

- `t/T=0`: horizontally elongated droplet.
- `t/T=0.25`: near-circular interface with maximal velocity and near-zero pressure.
- `t/T=0.50`: vertically elongated droplet with near-zero velocity and maximal pressure.
- `t/T=0.75`: near-circular interface with reversed velocity phase.
- `t/T=1.00`: return to the initial horizontal deformation.

## Important failure knowledge preserved

The raw P1 radial-gauge cell measurement does not exactly preserve the closed
chart's fixed phase volume.  The one-period run exposed a raw mismatch up to
`1.822318492916e-07` against the fixed closed-chart volume.  The accepted route
therefore uses
`closed_radial_cell_integral_total_volume_closed`: the chart still owns the
geometry, but the finite-volume measure is closed under the physical total
volume constraint before mapping `q_l -> q_g`.

This is not tolerance weakening and not smoothing/damping.  It is the
PhaseRegion primary contract applied to the cell measure: local P1 gauge volume
is a diagnostic approximation, while the owned phase region supplies the global
volume invariant.

## Validation

- `py_compile experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py`: PASS.
- `git diff --check`: PASS.
- Remote `make test ...`: PASS (`872 passed, 35 skipped`).
- Remote one-period `make cycle ...`: PASS.

[SOLID-X] No source-module SOLID violation found in the scoped diagnostic
route update.  The computation, YAML loading, figure generation, and
PhaseRegion measurement remain separated at function boundaries; no production
solver fallback, damping, smoothing, CFL retuning, rebuild skipping,
FD/WENO/PPE fallback, hidden CPU fallback, or force-consumer admission was
introduced.
