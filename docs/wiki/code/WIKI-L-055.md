---
ref_id: WIKI-L-055
title: "Ch14 Nonuniform Graph F0 Admission PASS"
domain: code
status: ACTIVE
tags: [ch14, graph_chart, q_manifold, nonuniform, f0_admission, oracle]
sources:
  - path: artifacts/A/ch14_nonuniform_graph_f0_admission_CHK-RA-CH14-VAR-024.md
    description: "Step 1 implementation, review, theory check, and validation"
  - path: src/twophase/geometry/interface_charts.py
    description: "Weighted low-mode graph F0 projection"
  - path: experiment/ch14/diagnose_q_manifold_projection_oracle.py
    description: "Uniform and real x-nonuniform graph oracle"
  - path: src/twophase/tests/test_q_manifold_projection.py
    description: "Nonuniform graph F0 regression"
depends_on:
  - "[[WIKI-E-070]]"
  - "[[WIKI-L-054]]"
  - "[[WIKI-L-048]]"
consumers:
  - domain: code
    usage: "Use before connecting graph F1 low-mode KKT to F0 admission"
  - domain: experiment
    usage: "Use before graph runtime dry-run probes"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Nonuniform Graph F0 Admission PASS

## Knowledge Card

`project_column_height_to_graph` is no longer uniform-x only.  It now interprets
column heights as P1 graph cell averages and solves a small weighted low-mode
system in chart space.  On nonuniform x-spacing the basis is centered in the
weighted metric and the constant term is corrected to preserve total volume.

This keeps the ownership order:

```text
Gamma_h owns eta*
q_phys = Q_h(Gamma_h)
r = q_T - q_phys
force_admissible = false
```

## Validation

Remote tests:

```text
819 passed, 35 skipped
```

Uniform oracle PASS:

- `dx_min = dx_max = 1.562500000000e-02`;
- clean `residual_l2 = 1.551195901319e-16`;
- high residual stays in `r`.

Real x-nonuniform oracle PASS:

- `dx_min = 1.000000000029e-06`;
- `dx_max = 1.737911003409e-02`;
- clean `residual_l2 = 1.668719229135e-16`;
- high-residual `eta_delta_linf = 3.330669073875e-16`.

## Boundary

This card removes the graph F0 nonuniform-spacing blocker only.  It does not
authorize F1 force coupling, pressure/velocity coupling, runtime adapters, or
T/8.
