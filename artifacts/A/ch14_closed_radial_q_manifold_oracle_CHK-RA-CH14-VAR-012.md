# CHK-RA-CH14-VAR-012 — Closed radial q-manifold oracle implementation

## Module

Closed radial chart residual-classification module:

```text
q_T -> Gamma*_closed_radial -> q_phys = Q_h(Gamma*) -> r
```

Implemented files:

```text
src/twophase/geometry/interface_charts.py
src/twophase/geometry/q_manifold_projection.py
src/twophase/tests/test_q_manifold_projection.py
experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py
```

No runtime adapter was added.

## Equation -> Discretization -> Code

| Equation object | Discretization | Code |
|---|---|---|
| `X(theta)` | star-shaped radial vertices | `ClosedRadialChartState`, `closed_radial_chart_from_modes` |
| `E[X]=sigma length(X)` | polygon edge length | `closed_polygon_geometry` |
| `A[X]` | oriented polygon area | `closed_polygon_geometry` |
| `dE/dX_i` | `sigma(e_{i-1}/l_{i-1}-e_i/l_i)` | `surface_gradient` |
| `dA/dX_i` | polygon area vertex covector | `area_gradient` |
| `Q_h(X)` | radial gauge P1 finite-volume cut | `closed_radial_q_from_chart` |
| closed F0 approximation | total area + one angular moment | `project_closed_radial_mode_f0` |
| restoring sign | area-reaction-free mode action | `closed_mode_restoring_action` |

## Code Review

Findings after self-review: no blocking issues remain.

- Closed chart owns vertices/radius; `phi` is generated only as a measurement
  gauge for `Q_h`.
- `ProjectionResult` exposes `q_phys`, `residual`, `constraint_report`,
  `energy_report`, and `residual_report`.
- Runtime adapter, T/8, pressure/velocity coupling, nonlinear optimizer, YAML
  route, smoothing, damping, tolerance weakening, CFL retuning, rebuild
  skipping, FD/WENO/PPE fallback, and hidden CPU fallback remain absent.
- A stale module docstring saying graph-only was fixed during review.

## Theory Consistency

The closed route uses the same variational owner as the graph route:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r = q_T - q_phys
```

The module verifies the closed-chart geometric covectors before residual
classification:

- polygon area and `Q_h` area agree within the declared oracle tolerance;
- mode-2 length exceeds circle length;
- `dE` and `dA` match finite differences;
- area-reaction-free restoring action is negative for positive mode-2
  deformation;
- high cell residual does not change the admitted mode.

The closed F0 projection is explicitly oracle-grade: it uses total area and one
angular moment.  It is not yet a runtime admission path.

## Validation

Local quick checks:

```text
.venv/bin/python3 -m py_compile src/twophase/geometry/interface_charts.py src/twophase/geometry/q_manifold_projection.py src/twophase/tests/test_q_manifold_projection.py experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py
.venv/bin/python3 -m pytest src/twophase/tests/test_q_manifold_projection.py -q
```

Result:

```text
8 passed
```

Remote-first experiment:

```text
make cycle EXP=experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py
```

Result: PASS.  Key metrics:

| Case | `residual_l2` | `residual_area_abs` | `coeff_cos` | `restoring_action` | `length_fd` | `area_fd` |
|---|---:|---:|---:|---:|---:|---:|
| circle | `5.947161592805e-06` | `7.049408704009e-05` | `-1.004195860841e-17` | `4.979172847673e-17` | `1.188881892239e-15` | `6.938894874404e-10` |
| mode2 | `6.871317601138e-06` | `7.103854253199e-05` | `1.595993422919e-02` | `-6.785140424220e-01` | `4.448704737925e-10` | `2.385941444416e-11` |
| high_residual | `6.874523817625e-06` | `7.103854253200e-05` | `1.595993422919e-02` | `-6.785140424220e-01` | `6.653515516319e-10` | `2.536963417121e-10` |

The mode-2 length excess over the circle was:

```text
7.287909978938e-03
```

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

The make target ran the remote suite:

```text
803 passed, 35 skipped
```

`git diff --check`: PASS.

## Next Gate

The next module may be a short runtime admission probe that records
`ProjectionResult` diagnostics without running T/8.  If that probe cannot keep
the residual budget visible before force construction, runtime admission must
fail closed.
