# CHK-RA-CH14-VAR-021 - PhaseRegion low-mode KKT module

Date: 2026-05-17

Scope: Module D implementation.  This checkpoint adds the small F1 low-mode
KKT correction solver for future PhaseRegion admission.  It does not choose
charts, build `J_Q` from cells, run nonlinear optimization, reconstruct `phi`,
build force coupling, project pressure/velocity, add runtime adapters, or run
T/8.

## Implemented files

- `src/twophase/geometry/phase_region_admission.py`
- `src/twophase/geometry/__init__.py`
- `src/twophase/tests/test_phase_region_admission.py`

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| low-mode correction `delta` | admitted chart-mode vector | `delta` |
| `J_Q delta ~= r` | weighted residual moment fit | `jacobian_q`, `residual`, `weights` |
| energy regularization | optional mode-space Hessian | `energy_hessian`, `energy_weight` |
| declared constraints | small linear constraints | `constraint_jacobian`, `constraint_rhs` |
| F1 solve | batched small KKT system | `solve_low_mode_kkt` |
| force gate | blocked | `force_admissible=False` |

## Coding result

The module introduces:

- `LowModeKKTResult`;
- `solve_low_mode_kkt`.

The solver accepts unbatched or batched systems and solves:

```text
min_delta 1/2 ||J_Q delta - r||_W^2
          + 1/2 alpha delta^T H_E delta
subject to J_C delta = c
```

It returns the correction, optional multipliers, predicted residual, residual
norm, constraint residual, objective, and `force_admissible=False`.

## Code review

Review finding fixed before acceptance:

- Hessian and constraint shape validation could have fallen through to NumPy
  broadcasting exceptions.  The solver now fails closed with
  `AtlasValidationError` and also requires symmetric energy Hessians.

No C1/SOLID issue found.  The module is a pure linear algebra helper and has no
I/O, plotting, runtime config dependency, force path, pressure/velocity
coupling, or chart measurement responsibility.

## Theory consistency

This is the F1 rung from the VAR-017 admission ladder:

```text
F0 proposes low modes
F1 solves a small KKT system over those modes
```

The unknown dimension is the admitted mode count, not the number of cells.  The
solver does not make all-cell `q` exact and does not turn residual `r` into
geometry.  Full nonlinear optimization remains oracle/fail-close only.

## Tests

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_admission.py -q'
```

The project make target ran the remote suite and passed:

```text
817 passed, 35 skipped
```

Targeted checks cover:

- unconstrained least squares recovery;
- exact declared constraint enforcement;
- energy regularization shrinking correction magnitude;
- batched KKT solves;
- fail-closed invalid weights;
- fail-closed negative energy weight;
- fail-closed missing constraint RHS;
- fail-closed bad Hessian shape and nonsymmetric Hessian;
- fail-closed bad constraint Jacobian shape.

