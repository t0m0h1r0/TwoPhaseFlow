---
ref_id: WIKI-T-046
title: "FCCD: Face-Centered Upwind Combined Compact Difference"
domain: theory
status: PROPOSED  # Research memo only; no code; PoC pending
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-A_face_centered_upwind_ccd.md
    description: Short paper defining FCCD and its link to H-01 remediation
depends_on:
  - "[[WIKI-T-001]]: CCD Method: Design Rationale and O(h^6) Compactness (baseline CCD)"
  - "[[WIKI-T-004]]: Balanced-Force Condition — same-operator requirement"
  - "[[WIKI-T-044]]: FVM-CCD Metric Inconsistency: G^adj Face-Average Gradient"
  - "[[WIKI-T-045]]: Late Blowup Hypothesis Catalog — H-01 PRIMARY"
  - "[[WIKI-E-030]]: Late blowup experiments (Exp-1..4)"
consumers:
  - domain: cross-domain
    description: WIKI-X-018 (H-01 remediation map — FCCD as candidate fix)
  - domain: future-impl
    description: Candidate replacement of CCDSolver when node-face hybrid path is chosen
tags: [ccd, compact_difference, upwind, face_centered, balanced_force, h01_remediation, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# FCCD: Face-Centered Upwind Combined Compact Difference

## Overview

FCCD is a **face-centred, upwind-limited reformulation of the Chu & Fan (1998) Combined Compact Difference** operator. Primary derivatives are evaluated at cell faces $x_{i-1/2}$ using only the two immediate upwind cell values $\{u_{i-1}, u_i\}$, and fourth-order spatial accuracy is obtained by algebraically cancelling the leading third-derivative truncation term via the coefficient $\lambda = 1/24$.

The full derivation is in [SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md). This entry summarises the key equations and positions FCCD within the project’s existing CCD stack.

## Key equations

With $f = i-1/2$, and using the Chu–Fan convention for the upwind first-difference expansion,

$$
\frac{u_i - u_{i-1}}{\Delta x} \;=\; u'_f + \frac{\Delta x^2}{24}\, u'''_f + \mathcal{O}(\Delta x^4).
$$

The FCCD operator is defined as

$$
D^{\text{FCCD}} u_f \;=\; \frac{u_i - u_{i-1}}{\Delta x} \;-\; \lambda\, \Delta x^2\, u'''_f,
$$

and setting $\lambda = 1/24$ yields

$$
D^{\text{FCCD}} u_f \;=\; u'_f + \mathcal{O}(\Delta x^4).
$$

## Comparison with the existing node-centred CCDSolver ([WIKI-T-001](WIKI-T-001.md))

| Aspect | Node-centred CCD | FCCD |
|---|---|---|
| Locus | cell nodes $x_i$ | cell faces $x_{i-1/2}$ |
| Stencil | $\{u_{i-1}, u_i, u_{i+1}\}$ (3-point) with boundary closure | $\{u_{i-1}, u_i\}$ (2-point, strictly upwind) |
| Order (uniform) | $\mathcal{O}(h^6)$ interior | $\mathcal{O}(h^4)$ |
| Matrix structure | $2N \times 2N$ block-tridiagonal | per-face local algebraic solve |
| Upwind causality | not strict (central relations) | strict by construction |
| Natural pairing | collocated pressure/velocity | staggered / face-fixed ALE |

**Accuracy trade-off.** FCCD sacrifices two orders relative to the O(h^6) interior CCD, but gains strict upwind causality and face-locus alignment. The latter is what matters for Balanced-Force consistency on non-uniform grids.

## Relation to H-01 (WIKI-E-030)

[WIKI-E-030](../experiment/WIKI-E-030.md) + [WIKI-T-045](WIKI-T-045.md) diagnosed the late blow-up as a mismatch between the FVM face gradient $\mathcal{G}^{\text{adj}}$ (used for velocity projection, [WIKI-T-044](WIKI-T-044.md)) and the node-centred CCD gradient (used for $\sigma \kappa \nabla \psi$). The BF residual measured at step 1 of Exp-1 was $|\text{BF}_\text{res}| \approx 884$.

FCCD places both gradients on the face locus, reducing the residual to the FCCD truncation order:

$$
\text{BF}_\text{res}^{\text{FCCD}} \;=\; \mathcal{O}(\Delta x^4) \quad\text{vs.}\quad \text{current }\mathcal{O}(\Delta x^2).
$$

This is the candidate remediation recorded as the open action in [ACTIVE_LEDGER](../../02_ACTIVE_LEDGER.md) CHK-152.

## Open questions for PoC

1. **Non-uniform generalisation.** The derivation above is for uniform $\Delta x$. On non-uniform grids the cancellation coefficient $\lambda$ becomes a function of the local spacing ratio $h_R/h_L$; the algebra must be redone (see SP-A §6.3(1)).
2. **Wall BC.** CCD wall treatment ([WIKI-T-012](WIKI-T-012.md)) assumes node unknowns; a face-centred wall stencil is undocumented.
3. **PPE compatibility.** The pseudotime defect-correction PPE iteration ([WIKI-T-016](WIKI-T-016.md)) is node-centred; switching to FCCD shifts the primary unknown locus.

## PoC programme (SP-A §8)

- **PoC-1**: 1D $\mathcal{O}(\Delta x^4)$ convergence on smooth data.
- **PoC-2**: BF residual measurement on the WIKI-E-030 capillary benchmark — compare node-CCD / $\mathcal{G}^{\text{adj}}$ hybrid / FCCD unified.
- **PoC-3**: Non-uniform stretched-grid convergence with prescribed $h_R/h_L$.

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- [SP-A full draft](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md)
- [WIKI-T-044](WIKI-T-044.md), [WIKI-T-045](WIKI-T-045.md), [WIKI-E-030](../experiment/WIKI-E-030.md), [WIKI-X-018](../cross-domain/WIKI-X-018.md)
