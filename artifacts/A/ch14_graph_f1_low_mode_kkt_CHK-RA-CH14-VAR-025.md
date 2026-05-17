# CHK-RA-CH14-VAR-025 - Graph F1 low-mode KKT

Date: 2026-05-17

Scope: Step 2 implementation connecting the graph F0 admission path to the
existing small low-mode KKT solver.  This checkpoint updates graph q-manifold
helpers, tests, and the visualization oracle only.  It does not add force
coupling, pressure/velocity projection, runtime adapters, YAML routes, full
nonlinear optimization, hidden CPU fallback, long stepping, or T/8.

## Claim

Graph F1 admission is now connected as a small mode-space correction:

```text
F0: q_T -> eta_0, q_0 = Q_h(eta_0), r_0 = q_T - q_0
F1: low moments of r_0 -> solve_low_mode_kkt -> delta eta
```

The KKT system is built over low residual moments, not all cell residuals.  The
final graph mean receives a single total-volume correction after the KKT step.

## Rejected Intermediate Design

The first implementation attempt passed the full cell residual vector into the
KKT system.  Tests failed:

- a zero-column cell residual was partially converted into geometry;
- a large truncated low-mode residual behaved like a nonlinear reconstruction
  problem rather than a one-step F1 correction.

This was rejected.  The corrected design follows the theory:

```text
F1 reduces admitted low moments only.
Cell-scale residual remains diagnostic r.
Large corrections require F0/F2/F3 gates, not one hidden nonlinear solve.
```

## Equation -> Discretization -> Code

Equation:

```text
q_T = Q_h(eta_0) + r_0
find delta c over admitted graph modes
min_delta ||J_M delta - M(r_0)||^2
```

where `M` extracts low graph column moments.

Discretization:

```text
M(q)_0   = sum_i dx_i h_i(q)
M(q)_2m  = sum_i dx_i h_i(q) B_i^cos(m)
M(q)_2m+1= sum_i dx_i h_i(q) B_i^sin(m)
```

with P1 cell-average basis values:

```text
B_i = 0.5 * (basis(x_i) + basis(x_{i+1}))
```

`J_M` is a finite-difference low-moment Jacobian around the F0 chart.  The
unknown count is `1 + 2 * correction_max_mode`, not the cell count.

Code:

- `src/twophase/geometry/q_manifold_projection.py`
  - added `project_graph_q_f1_low_mode`;
  - builds low moment residuals and low moment Jacobians;
  - calls `solve_low_mode_kkt`;
  - applies a single mean-mode total-volume correction;
  - keeps `force_admissible=false` in diagnostics.
- `src/twophase/geometry/__init__.py`
  - exports `project_graph_q_f1_low_mode`.
- `src/twophase/tests/test_q_manifold_projection.py`
  - verifies F1 recovers a small truncated nonuniform low mode;
  - verifies zero-column residual does not change shape modes.
- `experiment/ch14/diagnose_q_manifold_projection_oracle.py`
  - adds the `f1_truncated` visual row and KKT summary.

## Review Notes

[SOLID-X] no violation found.  The KKT algebra stays in
`phase_region_admission.py`, graph measurement/residual splitting stays in
`q_manifold_projection.py`, and I/O/plotting stays in the experiment script.
No solver runtime or force path is coupled.

## Theory Consistency

The owner remains the graph chart:

```text
Gamma_h owns eta
q_phys = Q_h(Gamma_h)
r is diagnostic
F1 sees low moments of r, not all cell residuals
force_admissible = false
```

The failed all-cell KKT attempt confirms why F1 must not become a hidden
screened q/phi rebuild.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

Result:

```text
821 passed, 35 skipped
```

Uniform oracle:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Result: PASS.

- `alpha_grid = 1.000000000000e+00`;
- `dx_min = dx_max = 1.562500000000e-02`;
- `f1_truncated residual_l2 = 2.467374203486e-15`;
- `f1_truncated eta_delta_linf = 4.646283358056e-14`;
- `f1_kkt f0_residual_l2 = 1.656565818657e-05`;
- `f1_kkt predicted_residual_l2 = 3.567323256083e-30`;
- `f1_kkt correction_l2 = 1.999999999818e-04`.

Nonuniform oracle:

```text
make run EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py ARGS='--alpha-grid 2.0 --clean-tolerance 1.0e-12'
make pull
```

Result: PASS.

- `alpha_grid = 2.000000000000e+00`;
- `dx_min = 1.000000000029e-06`;
- `dx_max = 1.737911003409e-02`;
- `f1_truncated residual_l2 = 2.253064066250e-15`;
- `f1_truncated eta_delta_linf = 3.647082635894e-14`;
- `f1_kkt f0_residual_l2 = 1.685544056874e-05`;
- `f1_kkt predicted_residual_l2 = 1.355281234324e-20`;
- `f1_kkt correction_l2 = 2.002060321629e-04`.

Formatting and wiki validation were run before commit:

```text
git diff --check
docs/wiki WIKI count = 418
docs/wiki/code WIKI-L count = 56
targeted CHK/wiki/code scan = PASS
```
