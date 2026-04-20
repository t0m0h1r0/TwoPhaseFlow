# SP-A: A Face-Centered Upwind Combined Compact Difference Method for High-Order Interface-Resolved Transport

**Status**: Short paper draft (research memo)
**Date**: 2026-04-20
**Related**: [WIKI-T-001](../../wiki/theory/WIKI-T-001.md), [WIKI-T-044](../../wiki/theory/WIKI-T-044.md), [WIKI-T-045](../../wiki/theory/WIKI-T-045.md), [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md), [WIKI-X-012](../../wiki/cross-domain/WIKI-X-012.md)
**Companion paper**: [SP-B_ridge_eikonal_hybrid.md](SP-B_ridge_eikonal_hybrid.md)

---

## Abstract

Compact finite-difference schemes provide high-order accuracy with small stencils. Among them, the Combined Compact Difference (CCD) method of Chu and Fan (1998) achieves higher-order accuracy by combining multiple compact derivative relations without enlarging the stencil or sacrificing upwind structure. In this short paper we present a **face-centered, upwind-limited reformulation of CCD (FCCD)** tailored for interface-resolved transport on collocated or semi-collocated grids. The proposed operator places primary derivatives at cell faces, ensuring exact alignment between numerical fluxes, interface locations, and grid motion. Fourth-order spatial accuracy is obtained by introducing higher derivatives as auxiliary unknowns and combining them algebraically to cancel leading truncation-error terms. A minimal formulation is derived using only immediate upwind cell values, avoiding stencil enlargement while preserving strict upwind causality. We additionally examine the FCCD operator as a candidate remediation for the FVM–CCD metric inconsistency identified as the root cause of the late-time blow-up documented in [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) (hypothesis H-01, balanced-force residual from the G^adj / CCD pressure gradient mismatch).

---

## 1. Introduction

High-order numerical schemes for advective transport face an inherent tension between accuracy, stability, and geometric fidelity. Non-compact high-order schemes (e.g., WENO) achieve excellent accuracy in smooth regions, but their reliance on extended stencils inevitably degrades interface sharpness. Conversely, interface-tracking and face-fixed methods preserve geometry but are typically restricted to second-order accuracy.

The **Combined Compact Difference (CCD)** method introduced by Chu & Fan (1998) addresses this dilemma by achieving high-order accuracy through the *combination* of compact derivative relations rather than through stencil extension. The upwind structure of the base scheme is preserved, making CCD particularly suitable for hyperbolic problems.

The present work extends this philosophy by relocating the CCD formulation from cell centres to **cell faces**, which naturally serve as loci for numerical fluxes, interface positions, and grid motion in ALE and interface-resolved frameworks. The objective is to construct a **minimal, upwind, face-centred CCD (FCCD)** that attains fourth-order accuracy while retaining strict locality and geometric consistency.

A secondary motivation arises from the TwoPhaseFlow project’s own debugging history. [WIKI-T-044](../../wiki/theory/WIKI-T-044.md) documented a metric inconsistency between the FVM face-average gradient `G^adj` used in the non-uniform corrector and the node-centred CCD differentiation applied elsewhere; [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) and [WIKI-T-045](../../wiki/theory/WIKI-T-045.md) confirmed that this mismatch is the dominant structural driver of late-time blow-up under capillary forcing. The FCCD operator proposed below places the primary gradient on the same face locus as `G^adj`, offering a candidate unification.

---

## 2. Governing Equation and Grid Arrangement

For clarity we consider the one-dimensional linear advection equation

$$
\frac{\partial u}{\partial t} + a \frac{\partial u}{\partial x} = 0, \qquad a > 0,
$$

on a uniform grid with spacing $\Delta x$.

- Cell centres: $x_i$
- Cell faces: $x_{i-\tfrac12}$
- Upwind direction: left → right

The discrete cell values $u_i$ and $u_{i-1}$ are assumed known.

---

## 3. Design Principles of Face-Centred CCD

FCCD adheres to four principles:

1. **Upwind-limited formulation.** Only upwind information is used; no central or downwind coupling is introduced.
2. **Stencil non-enlargement.** The operator uses only $\{u_{i-1}, u_i\}$, avoiding $u_{i-2}$ or wider stencils.
3. **Combined compact structure.** Higher-order accuracy is achieved by introducing higher derivatives and combining them linearly, following Chu & Fan (1998).
4. **Face-centred primary quantities.** All derivatives relevant to transport are defined at faces, ensuring compatibility with interface-fixed flux evaluation.

---

## 4. Combined Compact Difference Formulation

### 4.1 Unknowns

Auxiliary derivatives are temporarily introduced:

$$
\mathbf{U} = \bigl(u'_i,\; u'''_i,\; u'_{i-1},\; u'''_{i-1},\; u'_f,\; u'''_f\bigr)^{\!\top}, \qquad f = i-\tfrac12.
$$

Cell-centred derivatives serve as intermediate quantities and are eliminated in the final operator.

### 4.2 Upwind Compact Relations at Cell Centres

For $a > 0$, the following one-sided compact relations are adopted:

$$
\frac{u_i - u_{i-1}}{\Delta x} = u'_i - \frac{\Delta x^2}{6} u'''_i + \mathcal{O}(\Delta x^4),
$$

$$
\frac{u_i - u_{i-1}}{\Delta x} = u'_{i-1} + \frac{\Delta x^2}{6} u'''_{i-1} + \mathcal{O}(\Delta x^4).
$$

These relations share the same discrete difference but represent different Taylor expansions about $x_i$ and $x_{i-1}$. Their simultaneous use constitutes the *combined* character of CCD.

### 4.3 Face–Cell Coupling Relations

By midpoint relations between cell centres and faces,

$$
u'_f = \tfrac12\!\left(u'_i + u'_{i-1}\right) + \mathcal{O}(\Delta x^2),
$$

$$
u'''_f = \tfrac12\!\left(u'''_i + u'''_{i-1}\right) + \mathcal{O}(\Delta x^2).
$$

### 4.4 Upwind First-Difference Expansion at the Face

The basic upwind difference admits the expansion

$$
\frac{u_i - u_{i-1}}{\Delta x} = u'_f + \frac{\Delta x^2}{24} u'''_f + \mathcal{O}(\Delta x^4).
$$

This relation forms the backbone of the scheme.

---

## 5. Construction of the FCCD Operator

Following Chu & Fan (1998), a **Combined Compact Difference operator** is defined as

$$
D^{\text{FCCD}} u_f = \frac{u_i - u_{i-1}}{\Delta x} - \lambda \, \Delta x^2 \, u'''_f .
$$

Substituting the Taylor expansion of §4.4 yields

$$
D^{\text{FCCD}} u_f = u'_f + \left(\frac{1}{24} - \lambda\right) \Delta x^2 u'''_f + \mathcal{O}(\Delta x^4).
$$

**Cancellation condition.** Setting

$$
\lambda = \frac{1}{24}
$$

eliminates the third-derivative truncation term exactly, giving

$$
D^{\text{FCCD}} u_f = u'_f + \mathcal{O}(\Delta x^4).
$$

Thus **fourth-order spatial accuracy** is achieved without enlarging the stencil or abandoning the upwind structure.

---

## 6. Balanced-Force / G^adj Consistency (Project-Specific)

> This section is specific to the TwoPhaseFlow project context. General-audience readers may skip to §7.

[WIKI-T-004](../../wiki/theory/WIKI-T-004.md) formulates the Balanced-Force (BF) consistency principle: the discrete pressure-gradient operator $\mathcal{G}p$ and the discrete surface-tension operator $\sigma \kappa \nabla \psi$ must act in the **same metric space** for the one-fluid Navier–Stokes formulation to admit a static solution under Young–Laplace forcing. Denote by

$$
\text{BF}_{\text{res}} := \left\| \mathcal{G} p_{\text{YL}} - \sigma \kappa \nabla \psi \right\|_\infty
$$

the balanced-force residual evaluated on the analytic Young–Laplace pressure jump. Under a collocated node-centred CCD arrangement on uniform grids, the two operators coincide to machine precision and $\text{BF}_{\text{res}} = 0$.

### 6.1 Source of the Mismatch on Non-Uniform Grids

When the grid becomes interface-fitted and non-uniform, the node-centred CCD gradient is no longer aligned with the finite-volume face gradient that governs mass conservation in the projection corrector. [WIKI-T-044](../../wiki/theory/WIKI-T-044.md) introduced the adjusted face-average operator

$$
\mathcal{G}^{\text{adj}} p := \frac{p_{i+1}-p_i}{d_f^{(i+1/2)}} \quad \text{evaluated at } x_{i+1/2},
$$

where $d_f$ is the locally adapted face spacing. The adoption of $\mathcal{G}^{\text{adj}}$ restores the velocity projection but leaves $\sigma \kappa \nabla \psi$ on the node-centred CCD locus, giving a residual

$$
\text{BF}_{\text{res}} \ \sim \ \mathcal{O}(\Delta x^2) \cdot \left|\tfrac{d}{dx}\log J\right|,
$$

where $J$ is the computational-space Jacobian. [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) Exp-1 measured $|\text{BF}_{\text{res}}| \approx 884$ at step 1 for the $\rho=833$ capillary benchmark — the structural source of the late-time blow-up (hypothesis **H-01** confirmed by Exp-2 where $\sigma=0$ yielded $T=20$ stability).

### 6.2 FCCD as Metric-Unifying Operator

The FCCD operator $D^{\text{FCCD}}$ evaluates the primary derivative at the face $f = i-\tfrac12$ using only $\{u_{i-1}, u_i\}$ — the same locus and the same data footprint as $\mathcal{G}^{\text{adj}}$. Applying FCCD uniformly to both the pressure gradient **and** the surface-tension gradient,

$$
\mathcal{G}p \;:=\; D^{\text{FCCD}} p, \qquad \nabla \psi \;:=\; D^{\text{FCCD}} \psi,
$$

places the two operators on a common metric space by construction. The BF residual then reduces to the FCCD truncation error, i.e.,

$$
\text{BF}_{\text{res}} \ = \ \mathcal{O}(\Delta x^4) \ \gg \ \text{current } \mathcal{O}(\Delta x^2).
$$

This is a candidate remediation for **H-01** and supersedes the currently open action item *"G^adj と σκ∇ψ の同一メトリクス空間統一"* recorded in [ACTIVE_LEDGER](../../02_ACTIVE_LEDGER.md) (CHK-152).

### 6.3 Caveats and PoC Requirements

Three points require numerical verification before adoption:

1. **Non-uniform generalisation.** §4–5 derives FCCD on a uniform grid. The non-uniform extension requires Taylor expansion about face $f$ with local spacings $(h_L, h_R)$; the cancellation coefficient $\lambda$ then becomes a function of the local spacing ratio $h_R/h_L$. The Chu–Fan combined structure should remain intact, but the algebra must be redone.
2. **Wall-BC behaviour.** The current CCD wall treatment ([WIKI-T-012](../../wiki/theory/WIKI-T-012.md)) assumes node-centred unknowns. A face-centred operator at the wall requires either a ghost-cell or one-sided face formulation.
3. **Pseudotime PPE compatibility.** The defect-correction pseudotime PPE solver ([WIKI-T-016](../../wiki/theory/WIKI-T-016.md)) currently iterates on a node-centred residual. Replacing $\mathcal{G}$ with $D^{\text{FCCD}}$ shifts the primary unknown locus and may require a reformulation of the DC iteration matrix.

These items define the FCCD-PoC programme (see §8).

---

## 7. Discussion

The proposed FCCD formulation preserves the defining characteristics of the Chu & Fan (1998) CCD:

- higher-order accuracy through derivative combination,
- compactness without stencil extension,
- strict upwind causality.

The key novelty lies in relocating the formulation to cell faces, which makes the method particularly suited for interface-resolved and ALE-type computations. Interfaces remain sharply located at faces, and high-order accuracy is obtained solely through algebraic cancellation of truncation errors.

Importantly, the absence of $u_{i-2}$ or wider stencils ensures robustness near boundaries, interfaces, and topological events, where stencil extension often becomes problematic. This compactness is a necessary condition for integration with the ridge-based framework developed in the companion short paper [SP-B](SP-B_ridge_eikonal_hybrid.md), which requires a high-order operator that does not cross ridge loci.

Relation to the project’s open H-01 action item is direct: if the non-uniform FCCD of §6.3(1) is available, the `G^adj` hack becomes a special case of FCCD at second order, and the Balanced-Force consistency is restored at fourth order.

---

## 8. Conclusions and Future Work

A face-centred, upwind Combined Compact Difference method has been formulated in strict accordance with the original CCD philosophy of Chu & Fan (1998). By introducing higher derivatives as auxiliary variables and combining compact relations at cell centres and faces, the method achieves fourth-order accuracy using only immediate upwind data. A project-specific analysis shows that FCCD is a candidate remediation for the FVM–CCD metric inconsistency diagnosed in [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md).

Natural next steps:

- **PoC-1 (1D)**: Verify $\mathcal{O}(\Delta x^4)$ convergence of $D^{\text{FCCD}}$ on smooth and discontinuous test data.
- **PoC-2 (BF residual)**: Measure $|\text{BF}_{\text{res}}|$ under the WIKI-E-030 capillary benchmark with (i) node-CCD, (ii) current `G^adj` hybrid, (iii) FCCD unified. Expectation: $\mathcal{O}(\Delta x^2) \to \mathcal{O}(\Delta x^4)$ reduction.
- **PoC-3 (Non-uniform)**: Derive and verify FCCD on a stretched grid with prescribed $h_R/h_L$.
- **Extensions**: 5th/6th-order FCCD (including $u^{(5)}$); extension to nonlinear conservation laws; transverse (2D) FCCD via dimensional splitting.

The PoC outcomes will determine whether the TwoPhaseFlow paper is revised in mode **α** (add §8b FCCD subsection only), **β** (rewrite §04/§08 collocated commitment as "node-face hybrid"), or **γ** (full pivot combined with SP-B ridge framework).

---

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *Journal of Computational Physics*, 140(2), 370–399.
- Project wiki: [WIKI-T-001](../../wiki/theory/WIKI-T-001.md) (CCD design rationale), [WIKI-T-004](../../wiki/theory/WIKI-T-004.md) (Balanced-Force principle), [WIKI-T-012](../../wiki/theory/WIKI-T-012.md) (CCD boundary treatment), [WIKI-T-016](../../wiki/theory/WIKI-T-016.md) (pseudotime PPE), [WIKI-T-044](../../wiki/theory/WIKI-T-044.md) (G^adj), [WIKI-T-045](../../wiki/theory/WIKI-T-045.md) (H-01 blow-up catalogue), [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) (blow-up root-cause experiments), [WIKI-X-012](../../wiki/cross-domain/WIKI-X-012.md) (CCD non-uniform instability).
