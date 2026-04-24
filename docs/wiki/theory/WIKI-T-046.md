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
  - domain: theory
    description: WIKI-T-053 (computable FCCD equations using existing CCD d2 output)
  - domain: theory
    description: WIKI-T-054 (matrix form, wall BC rows, periodic block-circulant)
tags: [ccd, compact_difference, upwind, face_centered, balanced_force, h01_remediation, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# FCCD: Face-Centered Upwind Combined Compact Difference

## Overview

FCCD is a **face-centred, upwind-limited reformulation of the Chu & Fan (1998) Combined Compact Difference** operator. Primary derivatives are evaluated at cell faces $x_{i-1/2}$ using only the two immediate upwind cell values $\{u_{i-1}, u_i\}$, and fourth-order spatial accuracy is obtained by algebraically cancelling the leading third-derivative truncation term via the coefficient $\lambda = 1/24$.

### Primary motivation: common face-jet primitive (R1)–(R4)

In the pure-FCCD design of the current paper (SP-M), FCCD supplies a single **face-jet primitive** $\mathcal{J}_f(u) = (u_f,\ u'_f,\ u''_f)$ at $\mathcal{O}(\Delta x^4)$ that is reused by four co-located operators of the two-phase solver:

| Role | Operator | Consumption |
|---|---|---|
| (R1) | HFE upwind advection | one-sided face values $u_f$ for $\psi$ (and $\phi$ on cubic-logit coords) |
| (R2) | GFM ghost-pressure jet | face-averaged $\llbracket p \rrbracket$, $\llbracket \partial_n p \rrbracket$ rows |
| (R3) | Phase-separated PPE $D_h^{bf} = -(G_h^{bf})^*$ | face-locus gradient $G_h^{bf}$ and its adjoint divergence |
| (R4) | Viscous stress-divergence interface band | face-locus $\nabla\cdot(\mu[\nabla\bm u + (\nabla\bm u)^\top])$ in the 3-layer Hermite band |

All four roles share the **same two-cell upwind footprint** and the same $\mathcal{O}(\Delta x^4)$ truncation, making "one primitive, four operators" the design statement of SP-A / SP-M.

The full derivation is in [SP-A](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md). This entry summarises the key equations and positions FCCD within the project’s existing CCD stack.

For the executable PoC equation set, see [WIKI-T-053](WIKI-T-053.md): it interprets the $u'''_f$ correction below as $(q_i-q_{i-1})/\Delta x$ with $q_i=(D_{\mathrm{CCD}}^{(2)}u)_i$, matching the paper's CCD derivation method and avoiding a new third-derivative unknown.

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

## Historical context: H-01 diagnosis

*Historical note — see paper appendix §B.4 for the archived case study.*

[WIKI-E-030](../experiment/WIKI-E-030.md) + [WIKI-T-045](WIKI-T-045.md) diagnosed an earlier-generation late blow-up as a mismatch between the FVM face gradient $\mathcal{G}^{\text{adj}}$ (used for velocity projection, [WIKI-T-044](WIKI-T-044.md)) and the node-centred CCD gradient (used for $\sigma \kappa \nabla \psi$). The BF residual measured at step 1 of Exp-1 was $|\text{BF}_\text{res}| \approx 884$, and FCCD on a shared face locus reduced it to the truncation order

$$
\text{BF}_\text{res}^{\text{FCCD}} \;=\; \mathcal{O}(\Delta x^4) \quad\text{vs.}\quad \text{earlier }\mathcal{O}(\Delta x^2).
$$

**Current status (SP-M).** Under the pure-FCCD design of the paper, the FVM auxiliary $\mathcal{G}^{\text{adj}}$ is retired entirely and the face-jet primitive supplies the pressure gradient directly; the metric inconsistency cannot arise structurally. H-01 is therefore preserved as a historical case study rather than as the primary motivation. The living motivation is the (R1)–(R4) common-primitive contract above. The original remediation action recorded in [ACTIVE_LEDGER](../../02_ACTIVE_LEDGER.md) CHK-152 is subsumed by the pure-FCCD adoption in the current paper.

## Open questions for PoC

1. **Non-uniform generalisation.** The derivation above is for uniform $\Delta x$. On non-uniform grids the cancellation coefficient $\lambda$ becomes a function of the local spacing ratio $h_R/h_L$; the algebra must be redone (see SP-A §6.3(1)).
2. **Wall BC.** CCD wall treatment ([WIKI-T-012](WIKI-T-012.md)) assumes node unknowns; a face-centred wall stencil is undocumented.
3. **PPE compatibility.** The pseudotime defect-correction PPE iteration ([WIKI-T-016](WIKI-T-016.md)) is node-centred; switching to FCCD shifts the primary unknown locus.

## PoC programme (SP-A §8)

- **PoC-1**: 1D $\mathcal{O}(\Delta x^4)$ convergence on smooth data.
- **PoC-2**: BF residual measurement on the WIKI-E-030 capillary benchmark — compare node-CCD / $\mathcal{G}^{\text{adj}}$ hybrid / FCCD unified.
- **PoC-3**: Non-uniform stretched-grid convergence with prescribed $h_R/h_L$.

## 後続展開 (CHK-154, 2026-04-20)

§6.3 の 3 つの caveat は以下で個別解決:

- **caveat 1 (非一様格子拡張)** → [WIKI-T-050](WIKI-T-050.md): face-position パラメータ $\theta = h_R / H$ の関数として cancellation coefficients $\mu(\theta), \lambda(\theta), \nu(\theta)$ を導出。$\theta = 1/2$ で $\mu = \nu = 0$, $\lambda = 1/24$ に退化し本文と整合。
- **caveat 2 (Wall BC)** → [WIKI-T-051](WIKI-T-051.md): 三案 (ghost-cell mirror / one-sided face / ψ-only) を比較し、Neumann 場 (ψ, φ, p) には Option III (ψ-only mirror) を推奨。既存 G^adj wall handling と完全等価。
- **caveat 3 (PPE 互換)** → 現行 `ns_pipeline._solve_ppe` は `spsolve` 直接ソルバ ([`ppe_builder.py`](../../../src/twophase/ppe/ppe_builder.py)) を使用しており、[WIKI-T-016](WIKI-T-016.md) で扱う pseudotime defect-correction iteration には依存しない。SP-A §6.3(3) の caveat は**現行コードでは非該当**。pseudotime DC 系統 (`_CCDPPEBase` / `PPEFactory`) は §11 component tests のみで使用 ([WIKI-X-009](../cross-domain/WIKI-X-009.md)); production NS pipeline では不要。pseudotime DC を将来再導入する場合は別途 caveat 解決が必要。

並行して即時修正パス [WIKI-T-052](WIKI-T-052.md) (R-1.5 — 既存 `_fvm_pressure_grad` を ψ にも流用、3 行編集 / [WIKI-L-023](../code/WIKI-L-023.md)) が提案された。R-1.5 = FCCD operator with $\mu \equiv \lambda \equiv 0$ に相当 ([WIKI-T-050](WIKI-T-050.md) §"Reduction to G^adj") のため、PoC 完了後の R-1 への移行は単一シンボル置換で完了する。Remediation map 全体は [WIKI-X-018](../cross-domain/WIKI-X-018.md) を参照。

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- [SP-A full draft](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md)
- [WIKI-T-044](WIKI-T-044.md), [WIKI-T-045](WIKI-T-045.md), [WIKI-T-050](WIKI-T-050.md), [WIKI-T-051](WIKI-T-051.md), [WIKI-T-052](WIKI-T-052.md), [WIKI-E-030](../experiment/WIKI-E-030.md), [WIKI-X-018](../cross-domain/WIKI-X-018.md), [WIKI-L-023](../code/WIKI-L-023.md)
