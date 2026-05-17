# CHK-RA-CH14-VAR-014 — q-manifold runtime admission snapshot probe

## Module

Short runtime-admission snapshot probe for the Ch14 oscillating-droplet input:

```text
runtime-facing q_T snapshot -> Gamma*_closed_radial -> q_phys -> r
```

Implemented file:

```text
experiment/ch14/diagnose_q_manifold_runtime_admission_probe.py
```

This module does not advance the Navier-Stokes runtime, assemble surface
tension, invoke pressure projection, or run T/8.  It records whether the
residual budget is visible before any force construction.

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| Ch14 material droplet `Gamma` | YAML ellipse initial object | `_ellipse_from_config`, `_ellipse_phi` |
| fitted runtime grid metric | configured `alpha_grid` monitor with CCD metric | `_grid_from_config`, `Grid.update_from_levelset(..., ccd=CCDSolver(...))` |
| runtime-facing `q_T` | `GeometricPhaseState.from_phi(...).q` | `_phase_state_on_admission_grid` |
| q-manifold split | `q_T=Q_h(Gamma*)+r` | `project_closed_radial_mode_f0` |
| admission report | visible residual and force gate | saved `metrics`, PDF, `force_admissible=0` |

## Code Review

Findings after self-review: no blocking issues remain.

- The probe is experiment-only and uses `twophase.tools.experiment` for output,
  plot-only reload, NPZ persistence, and PDF saving.
- The first implementation mistake passed `bc_type` to `GridConfig`; this was
  corrected to use `grid.set_boundary_type`.
- Nonuniform grid rebuild initially failed closed because no `CCDSolver` was
  supplied for metrics.  The fix was to use the same CCD metric builder,
  not a low-order metric substitution.
- No runtime adapter, force coupling, pressure/velocity path, YAML production
  route, nonlinear optimizer, smoothing, damping, tolerance weakening, CFL
  retuning, rebuild skipping, FD/WENO/PPE fallback, hidden CPU fallback, or
  T/8 path was added.

## Theory Consistency

The probe keeps the ownership order:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r = q_T - q_phys
```

Here `q_T` is a CPU-labeled diagnostic snapshot of the canonical Ch14 initial
ellipse on the configured fitted-grid metric.  The projection creates a
closed-radial `ProjectionResult`; the observed residual is not converted into
geometry or force.  Because this is not a GPU-capable production `Q_h`, force
admission remains explicitly false.

## Validation

Remote-first experiment:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_runtime_admission_probe.py
```

Result: PASS.  Key metrics:

| Metric | Value |
|---|---:|
| `residual_l2` | `1.022474608009e-07` |
| `relative_l2` | `2.244971032800e-02` |
| `residual_area_abs` | `1.726838710861e-07` |
| `mode_cos_2` | `4.977887457363e-04` |
| `compat_linf` | `0.000000000000e+00` |
| `force_admissible` | `0.0` |

Generated outputs:

```text
experiment/ch14/results/diagnose_q_manifold_runtime_admission_probe/data.npz
experiment/ch14/results/diagnose_q_manifold_runtime_admission_probe/q_manifold_runtime_admission_probe.pdf
```

`git diff --check`: PASS.

## Next Gate

The next module may design a force-coupling admission contract, but it must not
run T/8.  The residual budget above is visible and nonzero, so any force route
must decide how `r` remains diagnostic before constructing acceleration.
