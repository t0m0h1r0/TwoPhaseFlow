---
ref_id: WIKI-T-005
title: "Defect Correction Method for PPE"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/09b_defect_correction.tex
    git_hash: 7328bf1
    description: "DC algorithm, convergence theory, solver comparison"
  - path: paper/sections/09d_pressure_summary.tex
    git_hash: 7328bf1
    description: "Accuracy summary and design rationale"
consumers:
  - domain: L
    usage: "ppe_solver implements DC framework with k iterations"
  - domain: A
    usage: "DC is the adopted PPE solver; alternatives documented for comparison"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-004]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-07
---

## Core Principle: "Evaluate High, Solve Low"

Defect Correction (DC) combines:
- **L_H** (high-order operator): CCD O(h^6) for residual evaluation
- **L_L** (low-order operator): FD O(h^2) for the linear solve (cheap, well-conditioned)

### 3-Step Algorithm (per iteration)

1. **Defect**: r^(k) = q - L_H(p^(k))  [CCD evaluates residual]
2. **Correction**: L_L(delta_p) = r^(k)  [FD solves correction, LU direct]
3. **Update**: p^(k+1) = p^(k) + omega * delta_p  [relaxation]

## Convergence

- omega in (0, 0.833) for convergence
- k=1: O(h^2) accuracy (FD-equivalent — current implementation)
- k>=3: O(h^6) accuracy (CCD precision fully realized)

## Why k=1 Is Sufficient (Current Design)

The CSF surface tension model introduces O(h^2) error as the universal spatial bottleneck. Investing DC iterations to achieve O(h^6) PPE accuracy provides no observable improvement when CSF limits the overall system to O(h^2).

**Future**: When GFM replaces CSF, the O(h^2) bottleneck is removed, and k>=3 DC iterations become worthwhile.

## Solver Comparison

| Method | Accuracy | Cost | Status |
|--------|----------|------|--------|
| BiCGSTAB (FVM) | O(h^2) | O(N^1.5) iterative | Baseline |
| LGMRES + CCD Kronecker | O(h^6) | O(N^2) iterative | Debug only |
| Direct LU + CCD Kronecker | O(h^6) | O(N^3) direct | Debug only |
| **DC (adopted)** | **O(h^2) at k=1** | **O(N^1.5) per iter** | **Production** |

**Key advantage**: DC uses LU factorization of the FD operator (sparse, banded), which is O(N^1.5) and can be pre-factored once per time step. The CCD operator is only used for residual evaluation (matrix-free O(N) per evaluation).

## Critical Note

LGMRES must NEVER be used for PPE (see project feedback). Use DC (k>=1) + LU direct solve per this design.
