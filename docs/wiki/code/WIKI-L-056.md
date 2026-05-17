---
ref_id: WIKI-L-056
title: "Ch14 Graph F1 Low-Mode KKT PASS"
domain: code
status: ACTIVE
tags: [ch14, graph_chart, q_manifold, f1_admission, low_mode_kkt, nonuniform]
sources:
  - path: artifacts/A/ch14_graph_f1_low_mode_kkt_CHK-RA-CH14-VAR-025.md
    description: "Step 2 implementation, rejected all-cell attempt, review, theory check, and validation"
  - path: src/twophase/geometry/q_manifold_projection.py
    description: "Graph F1 low-mode KKT helper"
  - path: src/twophase/geometry/phase_region_admission.py
    description: "Small KKT solver reused by graph F1"
  - path: experiment/ch14/diagnose_q_manifold_projection_oracle.py
    description: "F1 visual oracle"
depends_on:
  - "[[WIKI-L-055]]"
  - "[[WIKI-L-053]]"
consumers:
  - domain: code
    usage: "Use before extending F1 to other charts or atlas components"
  - domain: experiment
    usage: "Use before runtime dry-run probes that depend on graph admission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Graph F1 Low-Mode KKT PASS

## Knowledge Card

Graph F1 admission is connected to `solve_low_mode_kkt`, but only through
low graph column moments:

```text
F0 residual r_0
-> low moments M(r_0)
-> small KKT over graph mean/cos/sin coefficients
-> one mean-mode total-volume correction
```

The rejected all-cell KKT attempt is preserved as negative knowledge: it tried
to convert zero-column residual into geometry and was not accepted.

## Validation

Remote tests:

```text
821 passed, 35 skipped
```

Uniform oracle PASS:

- `f1_truncated residual_l2 = 2.467374203486e-15`;
- `f1_kkt predicted_residual_l2 = 3.567323256083e-30`.

Real x-nonuniform oracle PASS:

- `dx_min = 1.000000000029e-06`;
- `dx_max = 1.737911003409e-02`;
- `f1_truncated residual_l2 = 2.253064066250e-15`;
- `f1_kkt predicted_residual_l2 = 1.355281234324e-20`.

## Boundary

This authorizes graph F1 admission as an oracle/helper gate only.  It does not
authorize force coupling, pressure/velocity coupling, runtime adapters, or T/8.
