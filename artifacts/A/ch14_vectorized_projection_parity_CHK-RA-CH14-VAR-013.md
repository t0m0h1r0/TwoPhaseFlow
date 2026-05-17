# CHK-RA-CH14-VAR-013 — q-manifold vectorized geometry parity

## Module

Stage 3 vectorized parity for the q-manifold projection helpers.

The patch does not add a runtime adapter.  It proves that closed radial chart
construction and polygon geometry/covectors behave the same with a leading
batch axis as they do for independent scalar charts.

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| independent charts `X_b(theta)` | leading batch axis on center/radius/vertices | `closed_radial_chart_from_modes` |
| `E[X_b]=sigma length(X_b)` | batched edge lengths | `closed_polygon_geometry.length` |
| `A[X_b]` | batched shoelace area | `closed_polygon_geometry.area` |
| `dE/dX_b` | batched polygon surface covector | `closed_polygon_geometry.surface_gradient` |
| `dA/dX_b` | batched polygon area covector | `closed_polygon_geometry.area_gradient` |
| parity gate | scalar-vs-batch equality | `test_closed_radial_chart_and_polygon_geometry_have_batched_scalar_parity` |

## Code Review

Findings after self-review: no blocking issues remain.

- The batch axis is a product space of independent closed charts; no coupling
  between batch entries was introduced.
- The patch does not change projection semantics, force construction,
  pressure/velocity coupling, YAML routing, T/8 runtime paths, nonlinear
  optimization, tolerances, smoothing, damping, CFL, rebuild policy, or solver
  family.
- `Q_h` remains CPU-only and single-chart in this module; runtime GPU admission
  still fails closed through the existing projection helpers.

## Theory Consistency

Vectorization is only an execution layout.  It does not change the owned state:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r = q_T - q_phys
```

For the closed radial chart, batch parity checks that each `Gamma_h` entry has
the same vertices, radius, surface length, area, `dE`, and `dA` as the scalar
chart evaluated alone.  This blocks an accidental scalar-only implementation
from being accepted before runtime admission.

## Validation

Remote-first test:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

The make target ran the remote suite:

```text
804 passed, 35 skipped
```

`git diff --check`: PASS.

## Next Gate

The next module may be the short runtime admission probe.  It must record
`ProjectionResult` and residual budgets before any capillary force construction
and must not run T/8.
