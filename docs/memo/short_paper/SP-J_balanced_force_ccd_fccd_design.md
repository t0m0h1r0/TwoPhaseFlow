# SP-J: Balanced-Force Design for CCD/FCCD Two-Phase NS — Operator Consistency, PPE Adjoint Structure, and Staged IIM/GFM Integration

**Compiled**: 2026-04-22  
**Status**: STABLE (research memo)  
**Wiki entries**: WIKI-X-029 (design guide), WIKI-T-063 (PPE theory)  
**Depends on**: SP-A (FCCD), SP-C (FCCD matrix), SP-D (FCCD advection), WIKI-T-004 (BF condition), WIKI-T-021 (IIM-CCD)

---

## Abstract

Balanced-force (BF) accuracy in incompressible two-phase NS is determined not by differentiation order but by **discrete operator consistency**: the pressure gradient $G_h$, divergence $D_h$, surface tension $f_{\sigma,h}$, and density-weighting $\beta_f = (1/\rho)_f$ must all belong to the same discrete operator system and share the same evaluation location. This paper synthesises design principles for achieving BF in CCD/FCCD solvers: (1) seven operator-consistency principles, (2) a CCD-vs-FCCD comparison for the BF sub-system, (3) safety rules for DCCD filters in the BF path, (4) the adjoint PPE formulation for FCCD, (5) defect correction as a high-order/robust decoupling strategy, (6) staged GFM→IIM integration for the pressure jump, and (7) a critique of Rhie–Chow as a BF mechanism. The primary conclusion is that **a second-order face-flux BF sub-system outperforms a sixth-order inconsistent CCD one** for spurious-current metrics, and that FCCD's natural face-gradient output makes it the preferred operator for the BF path even if node-CCD is retained for advection and diffusion.

---

## 1 The Root Problem

The continuous BF condition

$$-\nabla p + \mathbf{f}_\sigma = \mathbf{0} \quad \text{(static droplet)}$$

must hold **discretely** to suppress parasitic currents:

$$-G_h p + f_{\sigma,h} \approx \mathbf{0}$$

Five failure modes prevent this in practice:

| Failure | Description |
|---------|-------------|
| F-1 | $G_h p$ and $f_{\sigma,h}$ evaluated at different locations |
| F-2 | PPE gradient $G_h$ differs from corrector gradient |
| F-3 | $D_h$ and $G_h$ are not discrete adjoints |
| F-4 | $\beta_f = (1/\rho)_f$ defined inconsistently across PPE / corrector / ST |
| F-5 | CCD stencil crosses interface discontinuity without jump correction |

All five are independent of differentiation order; all five occur in naive "apply high-order CCD to every quantity" implementations.

---

## 2 Seven Design Principles

### P-1 · Same location for $G_h p$ and $f_{\sigma,h}$

With staggered velocity on faces:

$$u^{n+1} = u^* + \Delta t\left(-\beta_f(G_h^{bf}p)_f + (f_\sigma)_f + \cdots\right)$$

Both $G_h^{bf}p$ and $f_\sigma$ must be face quantities. Node-CCD gradient interpolated to faces and surface tension computed via a different interpolation are **not** sufficient; the interpolation operators must themselves be adjoint-compatible.

### P-2 · Adjoint PPE: $D_h^{bf} = -(G_h^{bf})^*$

Build the PPE as

$$D_h^{bf}(\beta_f G_h^{bf} p) = \frac{1}{\Delta t}D_h^{bf}u^*$$

with $D_h^{bf} = -(G_h^{bf})^*$ under the discrete inner product. This makes the operator SPD (after null-space removal), enabling CG and guaranteeing that pressure correction subtracts the same gradient that the PPE solved for.

**Consequence for CHK-172**: fixing only the PPE RHS divergence while leaving the corrector on a different $G_h$ (observed in rising-bubble PoC) is insufficient. Full BF requires the same face gradient in both PPE assembly and velocity correction.

### P-3 · Route $f_\sigma$ through the same discrete geometry as $[p]_\Gamma$

Construct $f_\sigma$ so that it is algebraically equivalent to $G_h^{bf} p_\sigma$ for a capillary pressure field $p_\sigma$. Then the static balance

$$-G_h^{bf}p + G_h^{bf}p_\sigma = G_h^{bf}(p_\sigma - p) \approx \mathbf{0}$$

holds by the accuracy of the PPE solve, not by cancellation of two independently-discretised vectors.

### P-4 · Unify $\beta_f$ across all three paths

Variable-density PPE: $L_h p = -D_h^{bf}(\beta_f G_h^{bf} p)$

The same $\beta_f$ (e.g., harmonic average at face) must appear in:
- The PPE operator itself
- The velocity corrector $u^{n+1} = u^* - \Delta t\,\beta_f(G_h^{bf}p)_f$
- Surface-tension force normalisation

Mixing harmonic (PPE) and arithmetic (corrector) averages breaks BF under density ratios $\rho_l/\rho_g \gg 1$.

### P-5 · Do not apply raw CCD to curvature

$\kappa = \nabla\cdot(\nabla\psi/|\nabla\psi|)$ involves two differentiations of a field smooth only within $O(\varepsilon)$ of the interface. High-order CCD applied here amplifies small $|\nabla\psi|$ noise via the denominator and applies a wide stencil through an approximately constant bulk.

**Rule**: use CCD for $\nabla\psi$; compute $\kappa$ with an interface-limited smoother or second-order FD restricted to the thin-band. Curvature accuracy is a second-order effect on BF residual compared to operator location consistency.

### P-6 · Apply jump correction to interface-crossing stencils

CCD presupposes smooth fields. A static droplet with correct $\Delta p = \sigma\kappa$ but non-zero spurious current almost always indicates that interface-crossing CCD stencils are smearing the pressure jump. Required:

- GFM-style flux correction on interface-crossing faces (Phase 1)
- IIM compact row correction for higher order (Phase 3)

### P-7 · Maintain separate BF sub-system from bulk differentiators

| Task | Operator |
|------|----------|
| Advection, diffusion (bulk) | Node-CCD (high order, low dispersion) |
| PPE + corrector | $G_h^{bf}$, $D_h^{bf}$ (face, adjoint pair) |
| Surface tension | Same face slots as $G_h^{bf}$ |
| Curvature | Interface-limited smoother |

The BF sub-system does not need to be high-order; it needs to be internally consistent.

---

## 3 CCD vs FCCD for the BF Sub-System

### 3.1 Node-CCD (standard)

- Gradient at nodes; velocity at faces → P-1 violated unless face reconstruction added
- Adjoint pair $D_h = -G_h^*$ breaks at boundary rows → P-2 violated
- Compact stencil symmetric → spans interface without directional bias → P-6 harder
- **Strength**: 6th-order accuracy on smooth bulk; existing code assets

To make node-CCD BF-compatible, a separate face-gradient operator must be added anyway. This effectively means adding a face-operator layer — i.e., adopting Strategy B (§6) below.

### 3.2 FCCD (face-centered)

- Gradient naturally at face → P-1 satisfied natively
- $D_h^{bf}$ constructible as adjoint by design → P-2 achievable
- Directional bias available for interface-crossing stencils → P-6 easier
- **Weakness**: lower order than node-CCD on smooth bulk; boundary closure nontrivial

**Recommendation**: use FCCD for the BF sub-system (PPE + corrector + surface tension). Retain node-CCD for advection and diffusion.

---

## 4 DCCD Safety Rules

| Application | Safe? |
|-------------|-------|
| $\psi$ transport stabilisation (thin-band, uniform) | Conditionally yes |
| $\kappa$ pre-smoothing (weak, consistent filter) | Conditionally yes |
| $p_\sigma$ and $G_h p$ both filtered identically | Yes |
| Surface tension alone, pressure unfiltered | **No** |
| Pressure gradient alone, $f_\sigma$ unfiltered | **No** |
| Different DCCD on $\mathbf{n}$, $\kappa$, $\delta(\psi)$ | **No** |

Rule: if DCCD is applied to any BF-path quantity, it must be applied symmetrically to both sides of $-G_h p + f_\sigma$.

---

## 5 FCCD Face-Flux PPE: Adjoint Structure

### 5.1 Elliptic form

$$\boxed{D_h^{bf}\!\left(\beta_f\,G_h^{bf}\,p\right) = r, \qquad r = \frac{1}{\Delta t}D_h^{bf}\,u^*}$$

**Never** construct the operator by "choose any Laplacian and choose any gradient for the corrector separately." Always derive both from the same $G_h^{bf}$.

### 5.2 SPD and PCG

With $D_h^{bf} = -(G_h^{bf})^*$:

$$\langle p, A_h p\rangle = \langle G_h^{bf}p,\,\beta_f G_h^{bf}p\rangle \geq 0$$

Null space is the constant field (Neumann BCs). After removing it, $A_h$ is SPD and PCG is the primary solver.

**Fallback**: when IIM corrections or boundary closures break symmetry, use FGMRES with a low-order face-flux preconditioner.

### 5.3 Matrix-free matvec

Implement $y = A_h x = -D_h^{bf}(\beta_f G_h^{bf}x)$ as a function; pass via `LinearOperator` to the Krylov solver. This hides compact line-solve details (the FCCD face-gradient step requires solving a 1D system per row) and enables localised IIM modifications.

---

## 6 Defect Correction for High-Order FCCD PPE

Defect correction separates accuracy from robustness:

**Algorithm** (outer index $m$):

1. $r^{(m)} \leftarrow b - A_H p^{(m)}$ — evaluate residual with high-order FCCD operator
2. Solve $A_L \delta p = r^{(m)}$ — inner solve with low-order face-flux operator
3. $p^{(m+1)} \leftarrow p^{(m)} + \delta p$

| Operator | Purpose | Order |
|----------|---------|-------|
| $A_H = -D_h^{bf}(\beta_f G_h^{bf})$ | Residual (matvec) | FCCD (4th–6th) |
| $A_L = -D_2(\beta_f G_2)$ | Inner solve | 2nd face-flux |

**Critical**: $A_L$ must use the **same $\beta_f$, same BCs, and same jump conditions** as $A_H$. A plain Laplacian without $\beta_f$ fails as a preconditioner near the density jump and degrades convergence.

**Outer solver**: FGMRES (because inner solve is variable). Inner: PCG or AMG on $A_L$.

---

## 7 IIM/GFM Integration for $[p]_\Gamma = \sigma\kappa$

### 7.1 GFM correction (Phase 1–2, practical)

At face $f$ crossed by $\Gamma$:

$$(G_h^{bf}p)_f^{\rm corrected} = (G_h^{bf}p)_f - \frac{\sigma\kappa}{H_f}$$

This inserts the jump into the face flux without modifying the bulk stencil. The correction vector $c_\Gamma$ is updated each step when $\kappa$ is refreshed.

**Accuracy**: 2nd-order at the interface; adequate for Phase 1 validation and H-01 diagnostic.

### 7.2 IIM compact row correction (Phase 3, research)

For a compact FCCD relation $M_f \mathbf{g} = R_f \mathbf{p}$ at a row whose stencil crosses $\Gamma$:

$$M_f \mathbf{g} = R_f \mathbf{p} + c_\Gamma^{IIM}$$

where $c_\Gamma^{IIM}$ is derived from Taylor expansion of $[p]_\Gamma$, $[\beta\partial_n p]_\Gamma$. This maintains the compact structure to higher order at $\Gamma$.

### 7.3 Capillary-jump PPE (alternative)

Instead of CSF body force, embed $[p]_\Gamma = \sigma\kappa$ directly in the PPE via IIM:

$$D_h^{bf}(\beta_f G_h^{bf}\tilde p) = \frac{1}{\Delta t}D_h^{bf}u^*, \quad [\tilde p]_\Gamma = \sigma\kappa$$

In static equilibrium this is exact by construction. Dynamic problems require decomposing "dynamic pressure" from "capillary pressure" — feasible but requires careful design.

### 7.4 Staged roadmap

| Phase | Content | Spurious current |
|-------|---------|-----------------|
| 1 | Low-order $G_2$, $D_2$; GFM jump on crossing faces | $O(h)$ |
| 2 | FCCD $G_h^{bf}$, $D_h^{bf}$; GFM correction; defect correction outer | $O(h^2)$–$O(h^3)$ |
| 3 | IIM row correction for compact FCCD rows; high-order $\kappa$ via HFE | $O(h^3)$–$O(h^4)$ |

---

## 8 Rhie–Chow: Emergency Use Only

Rhie–Chow (RC) interpolation

$$u_f^{RC} = \bar{u}_f - \alpha(p_R - p_L)$$

is a checkerboard-suppression tool, not a BF mechanism:

- RC $G_h$ ≠ PPE $G_h$ → $-G_h p + f_\sigma = 0$ cannot hold exactly
- RC smears the jump $[p]_\Gamma = \sigma\kappa$ → amplifies spurious currents under density contrast
- RC introduces 1st-order local dissipation in regions where CCD provides 6th-order stencils

**Use case**: temporary stabiliser during debugging or coarse-grid initialisation only. Never in the production BF pressure-corrector path.

For RC background and the C/RC bracket improvement: see WIKI-T-017 and WIKI-T-025. Neither variant resolves the fundamental BF inconsistency.

---

## 9 Design Strategies Summary

### Strategy A — Full face-operator BF path (recommended)

Define $G_h^{bf}$ (FCCD or low-order face-flux), $D_h^{bf} = -(G_h^{bf})^*$, build PPE from their composition, place $f_\sigma$ in the same face slots, apply interface-limited smoother for $\kappa$. Achieves near-machine-precision BF on static droplet with constant $\kappa$.

### Strategy B — Node-CCD bulk + face-gradient BF layer (pragmatic)

Keep node-CCD for advection/diffusion; add a dedicated $G_h^{bf}$ used **only** for PPE assembly, pressure correction, and $f_\sigma$. The BF operator can be second-order. Minimises invasiveness while achieving BF consistency.

### Strategy C — Capillary-jump PPE (theoretically cleanest)

Embed $[p]_\Gamma = \sigma\kappa$ into the PPE via IIM; no CSF body force in momentum. Exact BF for static equilibrium by construction. Requires careful dynamic pressure decomposition.

---

## 10 Anti-Pattern Table

| Anti-pattern | Failure mode |
|--------------|-------------|
| High-order $G_h p$, low-order $f_\sigma$ | Different truncation; cancellation fails |
| $\kappa$ by full-stencil CCD | Noise amplification; interferes with BF gain |
| PPE $G_h$ ≠ corrector $G_h$ | Solves one equation, corrects with another |
| $f_\sigma$ at node, $G_h p$ at face | Location mismatch; non-cancelling forces |
| $\beta_f$ differs across PPE / corrector / ST | Variable-density BF broken at $\Gamma$ |
| Interface-crossing stencil unmodified | Jump contamination; spurious currents |
| RC in the BF pressure-corrector path | Artificial damping in cancellation; BF broken by construction |
| Asymmetric DCCD on BF path quantities | Asymmetric damping; cancellation fails |

---

## 11 Relation to Existing Architecture

| Issue | Location | Fix direction |
|-------|----------|--------------|
| PPE RHS / corrector gradient mismatch (CHK-172) | `ns_pipeline._solve_ppe` + `_fvm_pressure_grad` | Unify both to use same $G_h^{bf}$ |
| $\beta_f$ harmonic vs arithmetic inconsistency | `PPESolverFVMSpsolve` vs velocity corrector | Unify $\beta_f$ definition |
| GFM jump in crossing faces | `iim_solver.py` / `fvm_matrixfree.py` | Add $c_\Gamma$ to face flux |
| Krylov + preconditioner for FCCD PPE | `fvm_matrixfree.py` (WIKI-L-026) | Extend to FCCD $A_H$ + low-order $A_L$ |

---

## 12 One-Line Summary

> **BF is not about high order; it is about having pressure gradient, PPE, surface tension, and density weighting all live in the same discrete geometry and operator system.**
