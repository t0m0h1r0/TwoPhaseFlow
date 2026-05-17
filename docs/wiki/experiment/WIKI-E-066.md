---
ref_id: WIKI-E-066
title: "Ch14 q-Manifold Projection Graph Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, capillary_wave, q_manifold, interface_configuration, residual_split, graph_chart, negative_knowledge]
sources:
  - path: artifacts/A/ch14_q_manifold_projection_theory_CHK-RA-CH14-VAR-007.md
    description: "Theory artifact defining M_h, q_T=Q_h(Gamma*)+r, and validation metrics"
  - path: experiment/ch14/diagnose_q_manifold_projection_oracle.py
    description: "Graph q-to-interface-manifold projection oracle"
  - path: docs/wiki/experiment/WIKI-E-065.md
    description: "Validated interface-configuration graph capillary oracle"
depends_on:
  - "[[WIKI-E-065]]"
  - "[[WIKI-T-174]]"
consumers:
  - domain: experiment
    usage: "Use before closed-curve q-manifold projection or any runtime q_T residual probe"
  - domain: theory
    usage: "Use as evidence that graph low modes and non-geometric cell modes can be separated"
  - domain: code
    usage: "Use to avoid feeding off-manifold residual r into curvature or capillary force"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 q-Manifold Projection Graph Oracle PASS

## Knowledge Card

The first graph test of the decomposition

```text
q_T = Q_h(Gamma*) + r
```

passed.  In a low-mode graph chart, clean and representable low-mode `q_T`
project back to `Gamma*` with roundoff residual, while a zero-column
cell-scale perturbation remains in `r` without changing the smooth graph.

This supports the origin-reset theory that not every cell component of `q_T`
should become curvature-producing interface geometry.

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_projection_oracle.py
```

Result: PASS.  Outputs:

```text
experiment/ch14/results/diagnose_q_manifold_projection_oracle/data.npz
experiment/ch14/results/diagnose_q_manifold_projection_oracle/q_manifold_projection_oracle.pdf
```

Metrics:

| Case | `residual_l2` | `residual_column_linf` | `eta_delta_linf` | Verdict |
|---|---:|---:|---:|---|
| clean | `1.262190153575e-16` | `3.552713678801e-15` | `7.216449660064e-16` | on-manifold |
| low_mode | `1.578050209727e-16` | `3.552713678801e-15` | `4.440892098501e-16` | representable graph mode absorbed |
| high_residual | `1.381067932005e-04` | `3.553364200104e-15` | `7.216449660064e-16` | off-manifold cell residue isolated as `r` |

## Practice

- Treat `r` as a diagnostic residual, not as a capillary force source.
- Use this oracle before testing transported runtime `q_T`.
- The next gate is closed-curve chart residual classification; T/8 remains
  premature until that passes.
