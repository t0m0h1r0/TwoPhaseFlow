---
ref_id: WIKI-L-048
title: "Ch14 Graph q-Manifold Helper Implementation PASS"
domain: code
status: ACTIVE
tags: [ch14, q_manifold, graph_chart, interface_configuration, residual_split, vectorization]
sources:
  - path: artifacts/A/ch14_graph_q_manifold_helpers_CHK-RA-CH14-VAR-011.md
    description: "Implementation, review, theory check, and validation record"
  - path: src/twophase/geometry/interface_charts.py
    description: "Graph chart state, mode projection, and surface energy helpers"
  - path: src/twophase/geometry/q_manifold_projection.py
    description: "Graph F0 q-manifold projection and residual split"
depends_on:
  - "[[WIKI-L-047]]"
  - "[[WIKI-T-175]]"
  - "[[WIKI-E-066]]"
consumers:
  - domain: code
    usage: "Use before extending q-manifold projection to closed radial charts or runtime adapters"
  - domain: experiment
    usage: "Use as the validated graph helper baseline for closed residual-classification work"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Graph q-Manifold Helper Implementation PASS

## Knowledge Card

The graph F0 helper module is implemented and validated:

```text
q_T -> Gamma*_graph -> q_phys = Q_h(Gamma*) -> r
```

It keeps `Gamma_h` as the owner and exposes `r` through `ProjectionResult`.
The existing graph oracle now consumes these helpers.

## Validation

- local targeted test: `5 passed`;
- remote `make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py`
  PASS;
- remote suite through `make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py -q'`
  PASS: `800 passed, 35 skipped`;
- high residual remains in `r` with `residual_l2=1.381067932005e-04` while
  `eta_delta_linf=7.216449660064e-16`.

## Practice

Use this module as the graph baseline.  Do not connect runtime/T/8 before the
closed radial chart proves the same residual classification.
