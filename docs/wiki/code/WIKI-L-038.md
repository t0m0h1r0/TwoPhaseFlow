---
ref_id: WIKI-L-038
title: "GPU Utilization Work Must Preserve the Discrete Algebra"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, performance, fccd, ccd, gmres, algebra_preservation]
sources:
  - path: artifacts/A/ch14_capillary_schedule1_gpu_util_CHK-RA-GPU-UTIL-001.md
    description: "Schedule=1 GPU utilization RCA and optimization result"
depends_on:
  - "[[WIKI-L-015]]"
  - "[[WIKI-L-026]]"
  - "[[WIKI-T-117]]"
  - "[[WIKI-T-149]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# GPU Utilization and Algebra

## Knowledge Card

GPU utilization improvements are admissible when they change execution form
without changing the discrete equation.  For a fixed grid and wall closure, a
CCD derivative solve is a linear operator, so pre-expanding it into derivative
matrices can preserve the compact relation while reducing fragmented GPU work.

This is different from relaxing the grid schedule, PPE tolerance, jump
formulation, or convergence criterion.

## Consequences

- Diagnostics-off controls can falsify debug D2H as the dominant bottleneck.
- A faster `schedule=0` control is not admissible when the required benchmark
  semantics specify `schedule=1`.
- Reprojection PPE is a neutral divergence repair; interface jump/stress
  context must be cleared before that solve.
- Remaining utilization blockers should target fused matvecs or GPU-resident
  Krylov/preconditioner paths while preserving the same pressure equation and
  tolerances.

## Paper-Derived Rule

Optimize GPU execution by algebra-preserving transformations first; do not buy
utilization by changing the scientific route.
