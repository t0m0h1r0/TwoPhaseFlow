---
ref_id: WIKI-T-175
title: "Fast Vectorized Manifold Projection for Ch14 Capillary Charts"
domain: theory
status: ACTIVE
tags: [ch14, capillary_wave, oscillating_droplet, q_manifold, vectorization, nonlinear_optimization, interface_configuration]
sources:
  - path: artifacts/A/ch14_fast_vectorized_manifold_projection_CHK-RA-CH14-VAR-009.md
    description: "Fast projection hierarchy and vectorizable discretization design"
  - path: artifacts/A/ch14_q_manifold_projection_theory_CHK-RA-CH14-VAR-007.md
    description: "q-to-interface-manifold projection theory and graph validation metrics"
  - path: docs/wiki/experiment/WIKI-E-066.md
    description: "Graph q-manifold projection oracle PASS"
depends_on:
  - "[[WIKI-T-174]]"
  - "[[WIKI-E-066]]"
consumers:
  - domain: code
    usage: "Use before implementing graph/closed projection helpers or reviewing vectorized q-manifold code"
  - domain: experiment
    usage: "Use before closed-curve residual classification and before any T/8 runtime admission probe"
  - domain: theory
    usage: "Use to keep nonlinear optimization out of the default runtime route"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Fast Vectorized Manifold Projection for Ch14 Capillary Charts

## Knowledge Card

The q-manifold route should be runtime-fast by construction.  The owned state
is still `Gamma_h`; `q_T` is split into physical chart content and residual:

```text
q_T = Q_h(Gamma*) + r
```

The default projection should be a direct vectorized chart map, not a full
nonlinear solve:

```text
graph:        column volume -> eta modes -> Q_h(eta*) + r
closed curve: angular/radial moments -> radial modes -> Q_h(X*) + r
```

If direct moments leave low-mode residual content, allow one small linearized
KKT correction in admitted chart coefficients.  Full nonlinear minimization is
for oracle/fail-close analysis only.

## Runtime Ladder

| Level | Method | Role |
|---|---|---|
| F0 | direct chart moment projection | default runtime path |
| F1 | one low-mode linearized correction | rare near-chart correction |
| F2 | second step only if residual/energy improve | trust check |
| F3 | full nonlinear solve | oracle/fail-close only |

This avoids turning every cell component of `q_T` into geometry.  High cell
modes remain in `r` and must not feed capillary force.

## Vectorization Contract

Use batched arrays:

```text
coefficients: (batch, K)
graph eta:    (batch, nx)
curve X:      (batch, M, 2)
q/residual:   (batch, ny, nx)
active band:  (batch, ny, nx)
```

Prefer `backend.xp` operations: `roll`, `where`, `sum`, `matmul/einsum`, and
FFT/DCT when available.  Measure `Q_h` only on the active cut-cell band and
copy pure phase outside the band.

## Implementation Gate

Before any T/8 run:

- graph F0/F1 must preserve the already-passed low-mode/residual split;
- closed mode-2 radial oracle must pass energy, area, force-sign, and residual
  classification;
- vectorized batched helpers must match scalar oracle results;
- residual reports must remain visible in outputs.
