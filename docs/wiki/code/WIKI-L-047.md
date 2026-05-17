---
ref_id: WIKI-L-047
title: "Ch14 q-Manifold Projection Implementation Contract"
domain: code
status: ACTIVE
tags: [ch14, q_manifold, implementation_contract, interface_configuration, vectorization, fail_close]
sources:
  - path: artifacts/A/ch14_q_manifold_projection_implementation_design_CHK-RA-CH14-VAR-010.md
    description: "Implementation design for fast q-manifold projection without code changes"
  - path: artifacts/A/ch14_fast_vectorized_manifold_projection_CHK-RA-CH14-VAR-009.md
    description: "Fast F0/F1/F2/F3 projection theory"
  - path: docs/wiki/theory/WIKI-T-175.md
    description: "Compiled fast vectorized manifold projection card"
depends_on:
  - "[[WIKI-T-175]]"
  - "[[WIKI-L-046]]"
consumers:
  - domain: code
    usage: "Use before writing q-manifold projection helpers, chart states, or runtime adapters"
  - domain: experiment
    usage: "Use before graph helper extraction and closed radial oracle implementation"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 q-Manifold Projection Implementation Contract

## Knowledge Card

Implementation must preserve the ownership order:

```text
Gamma_h owner -> q_phys = Q_h(Gamma_h) -> r = q_T - q_phys
```

The first code-bearing checkpoint should be graph helper extraction only.  It
must not add a runtime adapter, T/8 run, nonlinear optimizer, or hidden CPU
fallback.

## File Boundary

Future code should keep separate layers:

| Layer | Future location | Responsibility |
|---|---|---|
| chart | `src/twophase/geometry/interface_charts.py` | graph/closed chart states, energy, area |
| projection | `src/twophase/geometry/q_manifold_projection.py` | F0/F1 split and `ProjectionResult` |
| diagnostics | `src/twophase/diagnostics/q_manifold.py` | residual spectra and fail-close reports |
| runtime | later `simulation` adapter | consume a validated result only |

## Coding Gate

Before coding, the patch must answer:

- which chart owns `Gamma_h`;
- how `q_phys` is produced;
- how `r` is exposed;
- which constraints are exact;
- which backend boundary is allowed;
- which oracle blocks runtime admission.

Current `cut_geometry_2d` is CPU-only, so GPU runtime projection must fail
closed until a GPU-capable `Q_h` evaluator exists.
