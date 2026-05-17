# CHK-RA-CH14-VAR-024 - Nonuniform graph F0 admission

Date: 2026-05-17

Scope: Step 1 implementation for chart-specific graph F0 admission on
nonuniform x-spacing.  This checkpoint updates the graph q-manifold oracle and
helper only.  It does not add force coupling, pressure/velocity projection,
runtime adapters, YAML routes, nonlinear optimization, hidden CPU fallback,
long stepping, or T/8.

## Claim

The previous blocker:

```text
project_column_height_to_graph currently requires uniform x spacing
```

is removed for the graph F0 oracle.  The replacement is a vectorizable
low-mode chart solve:

```text
q_T -> column height h_i
h_i -> weighted P1 cell-average low-mode graph eta*
q_phys = Q_h(eta*)
r = q_T - q_phys
force_admissible = false
```

The solve is small in mode space.  It is not a cell-count nonlinear optimizer.

## Equation -> Discretization -> Code

Equation:

```text
Gamma_h = {(x, eta(x))}
q_phys = Q_h(Gamma_h)
q_T = q_phys + r
```

Discretization:

```text
eta_h(x) = c0 + sum_m a_m cos(2 pi m x) + b_m sin(2 pi m x)
h_i = cell-average eta_h over cell i
min_c sum_i dx_i |h_i(c) - h_i(q_T)|^2
```

The graph is represented by P1 edge nodes, so the cell-average basis is:

```text
B_i = 0.5 * (basis(x_i) + basis(x_{i+1}))
```

On nonuniform grids the basis columns are centered in the weighted metric and
the constant term is corrected so the total volume remains exact.

Code:

- `src/twophase/geometry/interface_charts.py`
  - `project_column_height_to_graph` now solves the weighted low-mode system
    for uniform and nonuniform x-spacing.
- `src/twophase/geometry/q_manifold_projection.py`
  - `project_graph_q_f0` continues to split `q_T` into `q_phys` and residual
    using the same public helper.
- `experiment/ch14/diagnose_q_manifold_projection_oracle.py`
  - accepts `--alpha-grid`;
  - creates a real x-nonuniform fitting probe when `alpha_grid > 1`;
  - reports `dx_min` and `dx_max`.
- `src/twophase/tests/test_q_manifold_projection.py`
  - adds a real nonuniform x-grid regression.

## Review Notes

[SOLID-X] no violation found.  The chart helper remains pure geometry, the
runtime measurement remains in `q_manifold_projection`, and experiment I/O
remains in the experiment script.  No solver runtime, YAML route, capillary
force, pressure projection, or hidden fallback was introduced.

## Theory Consistency

This is still `Gamma_h`/chart primary:

```text
Gamma_h owns eta*
q_phys = Q_h(Gamma_h)
r is diagnostic
force_admissible = false
```

The new nonuniform solve changes only the F0 chart metric.  It does not make
transported all-cell q exact and does not revive screened q/phi rebuild.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

Result:

```text
819 passed, 35 skipped
```

Uniform oracle:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Result: PASS.

- `alpha_grid = 1.000000000000e+00`;
- `dx_min = dx_max = 1.562500000000e-02`;
- clean `residual_l2 = 1.551195901319e-16`;
- low-mode `residual_l2 = 1.522510178620e-16`;
- high-residual `residual_l2 = 1.381067932005e-04`;
- high-residual `eta_delta_linf = 6.661338147751e-16`;
- all force sign products are negative.

Nonuniform oracle:

```text
make run EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py ARGS='--alpha-grid 2.0 --clean-tolerance 1.0e-12'
make pull
```

Result: PASS.

- `alpha_grid = 2.000000000000e+00`;
- `dx_min = 1.000000000029e-06`;
- `dx_max = 1.737911003409e-02`;
- clean `residual_l2 = 1.668719229135e-16`;
- low-mode `residual_l2 = 1.271831536946e-16`;
- high-residual `residual_l2 = 1.406772181622e-04`;
- high-residual `eta_delta_linf = 3.330669073875e-16`;
- all force sign products are negative.

Formatting and wiki validation were run before commit:

```text
git diff --check
rg --files docs/wiki -g 'WIKI-*.md' | wc -l = 417
rg --files docs/wiki/code -g 'WIKI-L-*.md' | wc -l = 55
```

Result: PASS.
