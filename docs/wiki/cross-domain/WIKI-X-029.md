---
ref_id: WIKI-X-029
title: "Balanced-Force Operator Consistency for CCD/FCCD: 7 Design Principles, DCCD Safety Rules, and Rhie-Chow Critique"
domain: cross-domain
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — BF/CCD/FCCD design consistency (2026-04-22)
  - description: "Francois et al. (2006). A balanced-force algorithm for continuous and sharp interfacial surface tension models. JCP 213(1), 141–173."
  - description: "Popinet, S. (2009). An accurate adaptive solver for surface-tension-driven interfacial flows. JCP 228(16), 5838–5866."
depends_on:
  - "[[WIKI-T-004]]: Balanced-Force Condition: Operator Consistency Principle"
  - "[[WIKI-T-046]]: FCCD: Face-Centered Upwind Combined Compact Difference"
  - "[[WIKI-X-024]]: Balanced-Force Design for Two-Phase UCCD6-NS"
  - "[[WIKI-X-022]]: N-Robust BF-Consistent Full-Stack Architecture"
  - "[[WIKI-T-017]]: FVM Reference Methods: PPE Face Coefficients, CSF Model, Rhie-Chow"
  - "[[WIKI-T-025]]: C/RC (CCD-Enhanced Rhie-Chow)"
  - "[[WIKI-T-021]]: IIM-CCD"
  - "[[WIKI-T-005]]: Defect Correction Method for PPE"
consumers:
  - domain: theory
    description: "WIKI-T-063: FCCD face-flux PPE adjoint design and defect correction"
  - domain: cross-domain
    description: "WIKI-X-024: extends BF principles to UCCD6 momentum convection"
  - domain: impl
    description: "H-01 remediation: choose face-gradient path in ns_pipeline pressure corrector"
tags: [balanced_force, ccd, fccd, operator_consistency, ppe, face_gradient, adjoint, dccd, rhie_chow, two_phase, design_guide]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Balanced-Force Operator Consistency for CCD/FCCD

## §1 The Core Principle

The discrete BF condition requires that pressure gradient and surface tension force **cancel to near machine precision** on a static droplet:

$$-G_h p + f_{\sigma,h} \approx 0$$

Achieving this is **not** a matter of raising differentiation order. It requires that $G_h$ (pressure gradient), $D_h$ (divergence in PPE), and $f_{\sigma,h}$ (surface tension) share:

1. The **same evaluation location** (face vs node)
2. The **same discrete operator system** (same stencil family)
3. The **same interpolation/weighting rules** for $\beta_f = (1/\rho)_f$

A high-order but inconsistent discretisation produces worse spurious currents than a low-order but consistent one.

---

## §2 Seven Design Principles

### P-1 · Evaluate $G_h p$ and $f_{\sigma,h}$ at the same location

If velocity lives on faces (staggered), then:
- PPE must produce a **face pressure gradient** $( G_h p )_f$
- Surface tension must be a **face force** $( f_\sigma )_f$

A node-centered CCD gradient for pressure combined with a separately interpolated face surface tension leaves a BF residual that persists even at rest.

**Implementation**: define $G_h^{bf}$ as a face operator; pass both terms through identical face slots in the momentum update

$$u^* = u^n + \Delta t \left(-\beta_f (G_h^{bf} p) + (f_\sigma)_f + \cdots\right)$$

### P-2 · Make $D_h$ and $G_h$ discrete adjoints

Build the PPE as

$$D_h^{bf}\!\left(\beta_f\, G_h^{bf} p\right) = r$$

where

$$D_h^{bf} = -(G_h^{bf})^*$$

with respect to the discrete inner product. This adjoint relation guarantees:

- PPE is SPD (up to a null-space constant), enabling CG solvers
- Pressure correction subtracts the **same** gradient that the PPE solved for
- No mismatch between "divergence-free enforcement" and "corrector subtraction"

In standard node-CCD the adjoint relation breaks at boundary rows and at face–node mappings, causing BF residuals near interfaces.

### P-3 · Route surface tension through the same discrete geometry as the pressure jump

The Laplace pressure jump satisfies $[p]_\Gamma = \sigma\kappa$. Rather than treating $f_\sigma = \sigma\kappa\nabla\psi$ as an independent body force, construct it so that it is algebraically equivalent to $G_h^{bf}\,p_\sigma$ where $p_\sigma$ is a capillary pressure field. This ensures the cancellation

$$-G_h^{bf}\,p + G_h^{bf}\,p_\sigma = G_h^{bf}(p_\sigma - p) \approx 0$$

is a property of the **same operator** acting on two nearby fields — a far stronger cancellation than forcing two differently-constructed vectors to sum to zero.

### P-4 · Unify $\beta_f = (1/\rho)_f$ across PPE, corrector, and surface-tension force

In variable-density flow the PPE operator is

$$L_h p = -D_h^{bf}\!\left(\beta_f\, G_h^{bf} p\right)$$

The same face mobility $\beta_f$ must appear in:
- The PPE operator itself
- The velocity corrector $u^{n+1} = u^* - \Delta t\,\beta_f\,(G_h^{bf}\,p)_f$
- The surface-tension face force normalization

Using harmonic average $\beta_f$ for PPE but arithmetic average for the corrector (a common shortcut) breaks BF and leads to growing residuals under density-ratio flows.

### P-5 · Do not apply raw high-order CCD to curvature

Curvature $\kappa = \nabla\cdot(\nabla\psi/|\nabla\psi|)$ requires two differentiations of a field that is smooth only within a few grid cells of the interface. Applying high-order CCD here:

- Amplifies small $|\nabla\psi|$ noise in the denominator
- Applies an unnecessarily wide stencil through a nearly-constant bulk field

**Practical rule**: use CCD for $\nabla\psi$; compute $\kappa$ with a **restricted, interface-limited smoother** or second-order FD. Curvature accuracy contributes less to BF residual than operator location consistency does.

### P-6 · Protect interface-crossing stencils from jump contamination

CCD presupposes smooth fields. Across the interface, $p$ has a jump, $\rho$ has a step change, and $\nabla u$ has a kink. A standard CCD stencil spanning the interface treats the discontinuity as a smooth local variation and generates artificial oscillations.

Required safeguards:
- **GFM-style jump correction**: modify face flux when the stencil crosses $\Gamma$
- **One-sided or ghost-fluid CCD** near $\Gamma$
- **IIM row correction** for compact operators (see §4 below)

A static droplet with correct $\Delta p = \sigma\kappa$ but nonzero spurious current almost always points to this failure mode.

### P-7 · Keep a dedicated BF sub-system separate from bulk differentiators

Recommended split:

| Task | Operator |
|------|----------|
| Advection, diffusion (bulk smooth) | Standard CCD |
| PPE pressure gradient | $G_h^{bf}$ face operator |
| PPE divergence | $D_h^{bf} = -(G_h^{bf})^*$ |
| Surface tension face force | Same face slots as $G_h^{bf}$ |
| Curvature $\kappa$ | Interface-limited smoother |

The BF path does **not** need to be high-order; it needs to be internally consistent. A second-order face-flux BF path outperforms a sixth-order inconsistent one on spurious-current metrics.

---

## §3 CCD vs FCCD for BF: Decision Table

| Criterion | Node-CCD (standard) | FCCD / face-operator |
|-----------|---------------------|----------------------|
| BF location match | Requires extra face-reconstruction step | Native: gradient lives on face |
| Adjoint $D_h = -G_h^*$ | Breaks at boundary rows unless patched | Constructible by design |
| Interface-crossing stencils | Symmetric stencil spans jump → oscillation risk | Directional weighting, easier to bias away from jump |
| Bulk smooth-field accuracy | 6th-order, low dispersion | Generally lower order (4th typical) |
| PPE $D(\beta G p)$ construction | Composition of node→face steps needed | Natural face-flux assembly |
| Implementation complexity for BF | High: extra face-gradient layer required | Moderate: natural but boundary closure nontrivial |

**Recommendation**: use FCCD (or an equivalent face-flux operator) exclusively for the BF sub-system (PPE + corrector + surface tension). Retain node-CCD for advection and diffusion in smooth bulk regions.

---

## §4 DCCD Safety Rules

Dissipative CCD filters introduce artificial damping. Rules for the BF path:

| Use case | Safety |
|----------|--------|
| $\psi$ transport stabilisation (interface thin-band) | Conditionally safe if applied uniformly |
| Pre-smoothing $\kappa$ before curvature computation | Conditionally safe with weak, consistent filter |
| Capillary pressure field before $G_h$ conversion | Safe **only if** same filter applied to pressure gradient |
| Surface tension alone (leaving pressure unfiltered) | **Unsafe** — breaks cancellation |
| Pressure gradient alone (leaving $f_\sigma$ unfiltered) | **Unsafe** — breaks cancellation |
| Normal $\mathbf{n}$, $\kappa$, $\delta(\psi)$ with different DCCD each | **Unsafe** — force magnitude/direction become inconsistent |

Rule: if DCCD is applied to any quantity entering the BF balance, it must be applied symmetrically to both sides of the balance $-G_h p + f_{\sigma,h}$.

---

## §5 Rhie–Chow in BF Context

Rhie–Chow (RC) interpolation adds an artificial pressure-coupling correction to face velocities to suppress checkerboard modes on collocated grids:

$$u_f^{RC} = \bar{u}_f - \alpha(p_R - p_L)$$

This is a **numerical stabiliser**, not a force-balance mechanism. In a BF context:

| Aspect | Consequence |
|--------|-------------|
| RC pressure gradient ≠ PPE $G_h$ | BF balance $-G_h p + f_\sigma = 0$ cannot hold exactly |
| RC smears jump across interface | $[p]_\Gamma = \sigma\kappa$ smearing → spurious current amplification |
| RC and high-order CCD conflict | RC introduces local first-order damping in regions where CCD provides 6th-order stencils |
| RC ≠ zero-divergence enforcement | RC corrects face velocity for PP-decoupling, not for projection consistency |

**Verdict**: RC may be used as a temporary stabiliser for debugging or coarse-grid initialisation. It must **not** be placed in the BF pressure-corrector path or combined with the surface-tension operator. The correct fix for face-velocity/pressure decoupling in a CCD/FCCD solver is to design $G_h^{bf}$ as a proper face operator with adjoint $D_h^{bf}$, not to add numerical viscosity.

Reference prior work: WIKI-T-017 §4 and WIKI-T-025 for the C/RC bracket correction approach (which improves RC accuracy but does not resolve the fundamental BF inconsistency).

---

## §6 Three Design Strategies (Practical Ranking)

### Strategy A — Full face-operator BF path (recommended)

1. Define $G_h^{bf}$ as face-centered gradient (FCCD or low-order face-flux)
2. Define $D_h^{bf} = -(G_h^{bf})^*$ for the same discrete inner product
3. Build PPE: $D_h^{bf}(\beta_f G_h^{bf} p) = r$
4. Surface tension: face force on same face slot
5. $\kappa$: interface-limited smoother (not raw CCD)
6. Jump: GFM correction on interface-crossing faces (→ IIM row correction later)

**BF quality**: near machine precision on static droplet with constant $\kappa$.

### Strategy B — Node-CCD bulk + face-gradient BF sub-system (pragmatic)

Keep existing node-CCD for advection and diffusion. Add a separate face-gradient operator $G_h^{bf}$ used only for:
- PPE assembly and pressure correction
- Surface tension face force

This minimises code changes while achieving BF consistency. The BF operator can be low-order (second-order face-centered FD) and still outperform the high-order inconsistent CCD path.

### Strategy C — Capillary-pressure-jump-based BF (theoretically cleanest)

Represent surface tension not as a body force but as a pressure jump source:
$$[p]_\Gamma = \sigma\kappa$$
Embed the jump directly into the PPE via GFM/IIM jump conditions. The pressure gradient then naturally absorbs the capillary contribution in equilibrium. Dynamic problems require careful decomposition of "dynamic pressure" vs "capillary pressure."

---

## §7 Anti-Patterns

| Anti-pattern | Why it fails |
|--------------|-------------|
| High-order pressure gradient but low-order $f_\sigma$ | Different truncation; cancellation fails |
| $\kappa$ by full-stencil CCD | Noise amplification overwhelms BF gain |
| PPE $G_h$ ≠ corrector $G_h$ | Solves one equation, corrects with another |
| $f_\sigma$ at node, $G_h p$ at face | Location mismatch; non-cancelling forces |
| $\beta_f$ definition differs across PPE/corrector/ST | Variable-density BF broken at density jumps |
| Interface-crossing CCD stencil unmodified | Jump contamination → spurious current |
| Rhie–Chow in the BF pressure path | Artificial damping in cancellation path; BF violated by construction |

---

## §8 Cross-References

| Entry | Relation |
|-------|----------|
| [[WIKI-T-004]] | Foundational BF operator consistency theorem |
| [[WIKI-T-046]] | FCCD definition and face-gradient derivation |
| [[WIKI-T-063]] | FCCD PPE adjoint structure, defect correction, IIM/GFM integration |
| [[WIKI-X-024]] | BF design applied to UCCD6 momentum convection |
| [[WIKI-X-022]] | Full-stack architecture with 10-method role map |
| [[WIKI-T-017]] | FVM PPE face coefficients and Rhie–Chow baseline |
| [[WIKI-T-025]] | C/RC bracket correction (high-order RC variant) |
| [[WIKI-T-021]] | IIM-CCD for sharp pressure jump |
| [[WIKI-T-005]] | Defect correction for PPE |
