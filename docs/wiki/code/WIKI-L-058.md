---
ref_id: WIKI-L-058
title: "Ch14 Step 1 Nonuniform F0 Exact Test PASS"
domain: code
status: ACTIVE
tags: [ch14, graph_chart, q_manifold, nonuniform, f0_admission, exact_tests]
sources:
  - path: artifacts/A/ch14_step1_nonuniform_f0_exact_test_CHK-RA-CH14-VAR-028.md
    description: "Step 1 exact-reference test artifact"
  - path: src/twophase/tests/test_q_manifold_projection.py
    description: "Weighted P1 normal-equation reference and Step 1 test"
  - path: src/twophase/geometry/interface_charts.py
    description: "project_column_height_to_graph implementation under test"
depends_on:
  - "[[WIKI-L-055]]"
  - "[[WIKI-L-057]]"
consumers:
  - domain: code
    usage: "Use before changing nonuniform graph F0 admission or its tests"
  - domain: experiment
    usage: "Use before runtime dry-run probes that depend on Step 1 graph admission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Step 1 Nonuniform F0 Exact Test PASS

## Knowledge Card

Step 1 nonuniform graph F0 admission now has an exact algebraic unit test.  It
compares `project_column_height_to_graph` against an independent weighted P1
normal-equation reference:

```text
mean = <h>_dx
barB = <B_c>_dx
(B_c - barB)^T W (B_c - barB)c = (B_c - barB)^T W(h - mean)
eta_0 = mean - c dot barB
Q_h(eta)_i = eta_0 + B_c[i,:]c
```

The test checks returned mean, edge `eta`, cell-average `Q_h(eta)`,
cos/sin coefficients, residual orthogonality in the admitted low-mode basis,
and exact weighted-volume conservation on an intentionally irregular x-grid.

This is the Step 1 counterpart of the broader exact-theory test gate: it pins
the actual nonuniform F0 discretization rather than accepting only oracle PASS
metrics.

## Validation

Remote test:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'
```

Result:

```text
826 passed, 35 skipped
```

## Boundary

This is test hardening only.  It does not authorize runtime adapters, force
coupling, pressure/velocity coupling, nonlinear optimization, micro-stepping,
or T/8.
