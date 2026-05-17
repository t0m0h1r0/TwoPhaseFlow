# CHK-RA-CH14-VAR-061 - PhaseRegion Canonical Route Paper Reflection

Date: 2026-05-17

Scope: make the new PhaseRegion route the paper-facing canonical capillary
route and audit whether Chapters 12--13 require additional experiments after
the Chapters 1--11 theory update.

## Theory Reflection

The paper now treats the capillary owner as:

```text
R_h = (Omega_h, InterfaceAtlas)
Gamma_h = boundary Omega_h
q_h = Q_h(Omega_h)
E_h = sigma Perimeter(Omega_h)
```

`q` is a finite-volume measure and `phi`/graph/closed coordinates are charts or
gauges.  The old screened `q/phi` projection failure is preserved as negative
knowledge: exact all-cell `q` projection is not the canonical interface
reconstruction problem.

Updated paper sections:

- Chapters 1--3 orient the reader around PhaseRegion ownership, `q` as
  measure, and `phi` as gauge.
- Chapter 11 reframes the former active-geometry/q-primary section as
  PhaseRegion ownership plus fail-closed admission boundaries.
- Chapters 12--13 reframe U12/V11 as PhaseRegion force-admission gates, not
  physical benchmark successes.
- Chapter 14 uses the canonical `ch14_capillary.yaml` PhaseRegion graph route
  for the capillary wave and records the closed-chart oscillating-droplet
  few-step result while preserving the production runtime failure boundary.

## Ch12--Ch13 Audit

No additional Ch12--Ch13 NS re-experiment is required in this checkpoint.

Reason:

```text
The new PhaseRegion graph/closed results are reduced chart diagnostics.
They do not consume a PhaseRegion face force in production PPE/corrector.
force_admissible remains 0.
```

Therefore the existing V1--V10 pressure/velocity/NS experiments remain the
valid evidence for the current production solver.  The updated paper adds the
missing boundary: PhaseRegion chart diagnostics are not allowed to invalidate
or replace those NS experiments until a later force-admission gate changes
`force_admissible`.

Evidence already available on this branch:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
= PASS, steps=2560, t_over_T=1, force_admissible=0

make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_dry_run_adapter.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml'
= PASS, residual_l2=0, runtime_graph_q_linf=0

make cycle EXP=experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py
= PASS, steps=8, force_admissible=0

make test PYTEST_ARGS='-k ch14 -q'
= PASS, 17 passed, 890 deselected

make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py twophase/tests/test_phase_region_measure.py twophase/tests/test_phase_owner_map.py -q'
= PASS under the current broad make target, 872 passed, 35 skipped
```

## Ch14 Values Reflected

Capillary wave canonical YAML:

```text
experiment/ch14/config/ch14_capillary.yaml
```

One-period PhaseRegion graph result:

```text
steps                             = 2560
dt                                = 1.825897807156e-05
t_final                           = 4.674298386319e-02
t_over_T                          = 1
step_backend_gpu                  = 1
q_measurement_fast_column_integral= 1
max_amplitude_error               = 2.416836235604e-10
max_velocity_error                = 4.456387104473e-08
max_energy_drift                  = 1.505982113082e-06
max_residual_l2                   = 0
max_volume_drift                  = 5.421010862428e-20
mean_step_wall_seconds            = 3.516834525792e-03
max_step_wall_seconds             = 3.977783117443e-02
target_met                        = 1
force_admissible                  = 0
```

Oscillating droplet closed-chart few-step result:

```text
steps                             = 8
t_over_T                          = 1.517153366218e-03
max_amplitude_error               = 2.687954026026e-15
max_velocity_error                = 3.359899413812e-11
max_energy_drift                  = 3.225430493134e-11
max_residual_l2                   = 0
max_volume_drift                  = 5.428131902296e-13
force_admissible                  = 0
```

## Paper Figures

Copied into `paper/figures/`:

```text
ch14_phase_region_capillary_graph_steps.pdf
ch14_phase_region_oscillating_droplet_steps.pdf
```

## Boundary

This checkpoint is paper/wiki/artifact/figure reflection only.  It does not add
production pressure/velocity force consumption, does not weaken tolerances, and
does not reroute old production velocity/pressure snapshots into the new
PhaseRegion claim.

[SOLID-X] Paper/wiki/artifact/figure reflection only; no `src/twophase/`,
experiment code, physical parameter, CFL, damping, smoothing, tolerance
weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback,
production pressure/velocity coupling, main merge, branch deletion, worktree
removal, or origin push changed.
