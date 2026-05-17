---
ref_id: WIKI-E-067
title: "Ch14 Closed Radial q-Manifold Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, oscillating_droplet, closed_radial_chart, q_manifold, residual_split, variational_geometry]
sources:
  - path: artifacts/A/ch14_closed_radial_q_manifold_oracle_CHK-RA-CH14-VAR-012.md
    description: "Closed radial implementation, review, theory check, and validation"
  - path: experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py
    description: "Closed radial q-manifold oracle with visualization"
  - path: src/twophase/geometry/q_manifold_projection.py
    description: "Closed radial F0 oracle projection and residual split"
depends_on:
  - "[[WIKI-L-048]]"
  - "[[WIKI-T-175]]"
  - "[[WIKI-E-066]]"
consumers:
  - domain: experiment
    usage: "Use before any runtime admission probe or T/8 oscillating-droplet run"
  - domain: code
    usage: "Use to preserve closed radial residual semantics when adding runtime adapters"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Closed Radial q-Manifold Oracle PASS

## Knowledge Card

The closed radial chart now passes the same ownership test as the graph chart:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r
```

The oracle validates polygon area, surface length, `dE`, `dA`, mode-2
restoring sign, and high-residual classification before any runtime/T/8
connection.

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_closed_q_manifold_projection_oracle.py
```

Result: PASS.  Key results:

- mode-2 restoring action: `-6.785140424220e-01`;
- mode-2 length finite-difference residual: `4.448704737925e-10`;
- mode-2 area finite-difference residual: `2.385941444416e-11`;
- high residual keeps the same admitted mode coefficient:
  `1.595993422919e-02`;
- remote suite after implementation: `803 passed, 35 skipped`.

## Practice

Do not run T/8 yet.  The next gate is a short runtime admission probe that
records `ProjectionResult` and residual budgets before any capillary force
construction.
