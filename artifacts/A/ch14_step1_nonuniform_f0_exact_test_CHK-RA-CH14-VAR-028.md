# CHK-RA-CH14-VAR-028 - Step 1 nonuniform F0 exact test

Date: 2026-05-17

Scope: add an exact-theory unit test for the Step 1 nonuniform graph F0
admission helper.  This checkpoint changes tests only.  It does not add a
runtime adapter, force coupling, pressure/velocity coupling, nonlinear
optimization, long stepping, or T/8.

## Motivation

After the broader exact-theory test gate, the user asked for the same style of
test on Step 1.  Step 1 is the weighted nonuniform graph F0 admission:

```text
column height h_i
-> low-mode graph chart eta(x)
-> P1 cell averages Q_h(eta)
```

The previous Step 1 oracle demonstrated PASS behavior on uniform and fitted
nonuniform grids.  This checkpoint adds a closed-form algebraic reference so
the unit test checks the equation actually solved by
`project_column_height_to_graph`.

## Exact Reference

For nonuniform cell widths `dx_i`, sampled column heights `h_i`, and graph
edge basis functions `B_e`, the code treats the reconstructed graph as a P1
chart.  Cell averages use

```text
B_c[i,m] = 0.5 * (B_e[i,m] + B_e[i+1,m]).
```

The exact low-mode projection is:

```text
mean = sum_i dx_i h_i / sum_i dx_i
barB_m = sum_i dx_i B_c[i,m] / sum_i dx_i
(B_c - barB)^T W (B_c - barB) c = (B_c - barB)^T W (h - mean)
eta_0 = mean - c dot barB
eta_edges = eta_0 + B_e c
Q_h(eta)_i = eta_0 + B_c[i,:] c
```

where `W=diag(dx_i)`.  This is a small dense normal-equation reference in
chart space, not an all-cell q projection and not a nonlinear optimizer.

## Added Test

`test_step1_nonuniform_graph_f0_matches_exact_weighted_normal_equations` now
uses an intentionally irregular x-grid and a height field containing admitted
low modes plus one excluded high mode.  The test verifies:

- returned weighted mean;
- edge graph values `eta`;
- P1 cell averages `Q_h(eta)`;
- cos/sin low-mode coefficients;
- weighted residual orthogonality against admitted cell-average basis columns;
- exact total-volume preservation.

This makes the Step 1 test detect sign, basis-centering, nonuniform-weight,
and volume-correction mistakes directly.

## Equation -> Discretization -> Code

| Equation | Discretization | Code |
|---|---|---|
| `Gamma_h` graph chart owns `eta` | P1 edge values over nonuniform x edges | `project_column_height_to_graph` |
| `q_phys = Q_h(Gamma_h)` | column P1 cell averages weighted by `dx_i` | `_exact_weighted_p1_projection` reference and `result_cell_average` assertion |
| F0 low-mode projection | centered weighted normal equations in admitted cos/sin modes | coefficient and residual-orthogonality assertions |
| volume conservation | `sum_i dx_i Q_h(eta)_i = sum_i dx_i h_i` | final weighted-volume assertion |

## Code Review

[SOLID-X] no violation.  The patch touches only
`src/twophase/tests/test_q_manifold_projection.py`.  No production helper,
runtime path, plotting path, experiment YAML, solver route, GPU path,
capillary force route, pressure/velocity coupling, or nonlinear optimizer was
modified.

## Theory Consistency

The test preserves the current ownership ladder:

```text
Gamma_h owns eta
q_phys = Q_h(Gamma_h)
r = q_T - q_phys remains diagnostic
force_admissible = false
```

It intentionally checks the Step 1 fast path as a low-mode graph admission
problem.  It does not turn all transported q components into geometry.

## Validation

Remote test:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

Result:

```text
826 passed, 35 skipped
```

Formatting and wiki validation:

```text
git diff --check = PASS
docs/wiki WIKI count = 421
docs/wiki/code WIKI-L count = 58
targeted CHK/wiki/test scan = PASS
```
