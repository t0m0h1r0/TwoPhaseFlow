# WIKI-E-086 — Ch14 PhaseRegion Droplet YAML One-Period PASS

Use this card before citing the canonical reduced oscillating-droplet
PhaseRegion run from `experiment/ch14/config/ch14_oscillating_droplet.yaml`.

## Scope

The canonical droplet YAML now mirrors the capillary-wave PhaseRegion route:

```text
X(theta; A) -> q_l = Q_h(X)
q_g = |C| - q_l
PhaseRegionBatch(GAS_OUTSIDE closed radial chart)
E_h second-variation modal step
```

It is a reduced closed-chart PhaseRegion experiment.  It does not connect a
production face cochain to Navier--Stokes pressure projection, and
`force_admissible=0` remains part of the result.

## Evidence

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py ARGS='--config experiment/ch14/config/ch14_oscillating_droplet.yaml'
```

Result:

```text
steps = 3977
dt = 2.651764221323e-05
t_over_T = 9.999999999903e-01
max_amplitude_error = 2.503547743871e-10
max_velocity_error = 2.046056174314e-08
max_energy_drift = 6.240056085825e-07
max_residual_l2 = 0.000000000000e+00
max_volume_drift = 1.084202172486e-19
max_q_volume_closure_raw_abs = 1.822318492916e-07
max_q_volume_closure_closed_abs = 2.710505431214e-20
max_step_wall_seconds = 3.064271062613e-03
force_admissible = 0
```

The YAML-owned outputs include physical-time snapshots for `phi`, velocity,
pressure, and PhaseRegion `q_l/q_g`.

## Visual inference

The images show the expected Rayleigh--Lamb phase relation:

- horizontal deformation at `t/T=0`;
- near-circular shape and maximal velocity at `t/T=0.25`;
- vertical deformation and near-zero velocity at `t/T=0.50`;
- return to the initial deformation at `t/T=1.00`.

Pressure is small at the quarter period and largest near the turning point,
matching the linear oscillator phase.

## Failure knowledge

The raw P1 closed-radial gauge measurement is not an exact physical volume
owner.  Its total volume differs from the fixed closed-chart phase volume by
up to `1.822318492916e-07`.  The route therefore records the measurement as
`closed_radial_cell_integral_total_volume_closed`: the chart owns the
geometry, while the finite-volume measure is closed under the total phase
volume constraint before complementing to gas.

This is a state-ownership correction, not tolerance weakening, smoothing,
damping, or CFL retuning.

## Links

- Artifact: `artifacts/A/ch14_phase_region_droplet_yaml_one_period_CHK-RA-CH14-VAR-065.md`
- Config: `experiment/ch14/config/ch14_oscillating_droplet.yaml`
- Runner: `experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py`
