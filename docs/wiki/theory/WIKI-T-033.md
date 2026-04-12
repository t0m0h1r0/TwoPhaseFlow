---
ref_id: WIKI-T-033
title: "Extended Crank–Nicolson × CCD: 4th-Order Viscous Time Integration (Design)"
domain: T
status: PROPOSED
superseded_by: null
sources:
  - path: "docs/memo/extended_cn_ccd_design.md"
    git_hash: null
    description: "Design note: Richardson / Padé-(2,2) / DC CN extensions, CCD coupling via sequential D₂(D₂·), matrix-free GPU kernel, energy analysis"
consumers:
  - domain: L
    usage: "Future viscous solver upgrade (Pade22CNAdvance, RichardsonCNAdvance)"
  - domain: E
    usage: "Future experiment — exp11_30_extended_cn_convergence"
  - domain: A
    usage: "Paper §10 time integration — 4th-order viscous extension path"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-011]]"
  - "[[WIKI-T-012]]"
  - "[[WIKI-T-015]]"
  - "[[WIKI-T-017]]"
  - "[[WIKI-T-019]]"
  - "[[WIKI-T-023]]"
  - "[[WIKI-L-015]]"
  - "[[WIKI-X-007]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-12
---

## Problem

Crank–Nicolson for $u_t = \nu L u$, $L = \nabla^2$, is A-stable, energy-preserving, and
2nd-order ([[WIKI-T-003]]). Against a CCD spatial operator ([[WIKI-T-001]], $O(h^6)$)
the temporal error dominates for any practical $\Delta t$. Goal: raise CN to 4th order
**without breaking A-stability or the discrete energy identity**, and do so in a way
that reuses the existing CCD infrastructure on GPU ([[WIKI-L-015]], CHK-119 `A_inv_dev`).

## Design Principle

*CN is structurally complete; strengthen it from the outside, not the inside.*

## Four Candidate Families

| Family | Order | A-stable | GPU fit | Cost | Verdict |
|---|---|---|---|---|---|
| Richardson-CN ($u_{n+1} = (4u_{\Delta t/2} - u_{\Delta t})/3$) | $O(\Delta t^4)$ | yes | ideal — reuse CN kernel | ~2× CN | **ship first** |
| Padé-(2,2) CN ($R_{2,2}(z) = (1 + z/2 + z^2/12)/(1 - z/2 + z^2/12)$) | $O(\Delta t^4)$ | yes | good (needs $L^2$) | 1 solve/step, matrix-free | **ship second** |
| Deferred-Correction CN (predictor + residual iteration) | tunable 3–4 | inherited | ideal | $(1+k)\times$ CN | fallback |
| $\theta$-method ($\theta > 1/2$ or $\theta(k)$) | 2 (stabilizer) | yes | trivial | ~CN | mitigate, not extend |

Composite $D_4$ operator (direct fourth-derivative CCD stencil) rejected — compact
boundary treatment is open, interaction with GFM jumps ([[WIKI-T-017]]) unknown,
implementation cost not justified over sequential $D_2(D_2 \cdot)$.

## CCD Coupling — the $L^2$ Question

Padé-(2,2) and DC both need $L^2 u$ somewhere. Two routes:

- **Route A — sequential**: $L^2 u \approx D_2(D_2 u)$, two CCD solves back-to-back.
  Preserves CCD structure, no stencil widening, boundary treatment unchanged,
  Kronecker assembly ([[WIKI-T-012]]) reusable, cached `A_inv_dev` reused,
  matrix-free on GPU. Accuracy floor $O(h^6 + \Delta t^4)$ — no loss since space
  floor is already $h^6$. **Recommended.**
- **Route B — composite $D_4$**: build a direct fourth-derivative compact stencil.
  Self-adjoint and Hermite-exact, but boundary/GFM treatment is open research.
  **Rejected.**

## Proposed Scheme — Padé-(2,2) CN × CCD (Route A)

$$
\bigl(I - \alpha D_2 + \beta\,D_2(D_2 \cdot)\bigr)\,u^{n+1}
 = u^n + \alpha\,D_2 u^n + \beta\,D_2(D_2 u^n),
\quad \alpha = \tfrac{\nu\Delta t}{2},\;\beta = \tfrac{(\nu\Delta t)^2}{12}.
$$

Matrix-free evaluation kernel:

```python
def apply_A(u, D2, alpha, beta):
    w  = D2(u)           # CCD pass 1 — cached A_inv_dev @ rhs_flat
    w2 = D2(w)            # CCD pass 2
    return u - alpha*w + beta*w2
```

Linear solver: CG on uniform/periodic, BiCGSTAB or GMRES + FD preconditioner on
non-uniform/wall/GFM cases — mirrors [[WIKI-T-005]] / [[WIKI-T-015]] but for the
viscous solve.

## Energy Property

For periodic BC the CCD interior operator is symmetric; multiplying the Padé-(2,2)
update by $u^n + u^{n+1}$ yields the discrete identity

$$
\|u^{n+1}\|^2 - \|u^n\|^2 = -\nu\Delta t\,\bigl\langle u^n + u^{n+1},\,-D_2(u^n + u^{n+1})\bigr\rangle
 + \varepsilon_{\text{sym}},
$$

with $\varepsilon_{\text{sym}} = O(h^{\min(4,\,p_{\text{bdry}})})$ the CCD boundary
stencil asymmetry. On periodic BC, $\varepsilon_{\text{sym}} = 0$; on wall BC, it is
below the spatial floor.

**Important caveat.** Padé-(2,2) is A-stable but **not L-stable**:
$R_{2,2}(\infty) = 1$. Nyquist modes are not annihilated, so a residual high-$k$
wiggle may appear on marginally-resolved shear layers. Mitigations:

1. One pass of the dissipative CCD filter per step ([[WIKI-T-002]], [[WIKI-T-019]])
2. Mode-dependent $\theta(k)$ above a cutoff (§2.4 of source memo)
3. Spectrally-optimized $\beta^\star < (\nu\Delta t)^2/12$ trading 4th-order constant
   for quasi-L-stability

## Symmetry Caution

If the CCD wall-BC stencil is not strictly self-adjoint, $D_2(D_2 u) \ne D_2^{\mathsf T} D_2 u$
and discrete energy drift may accumulate. Required practice:
- reuse the **same** CCD operator on both passes (no re-factorization, no alias to a
  re-initialized state)
- symmetrize explicitly only if Lyapunov drift is observed in long runs

## Implementation Steps

1. **Step 1**: `RichardsonCNAdvance` — wrapper around existing CN, zero PR-5 risk,
   serves as reference solution.
2. **Step 2**: `Pade22CNAdvance` — matrix-free kernel above, BiCGSTAB + FD preconditioner,
   reuses CCD `A_inv_dev` cache. Verify 4th-order temporal convergence against Step 1.
   Add [[WIKI-T-002]] filter hook for high-$k$ wiggle.
3. **Step 3**: `exp11_30_extended_cn_convergence` — manufactured viscous solution
   $u = e^{-\nu k^2 t}\sin(kx)\sin(ky)$, methods $\{$CN, Richardson-CN, Padé-CN$\}$,
   $N \in \{32, 64, 128\}$, report temporal convergence order + long-time energy drift.
   Baseline CN → $O(\Delta t^2)$; both extensions → $O(\Delta t^4)$.

## Open Questions

1. CCD wall-BC stencil asymmetry impact on $D_2(D_2 u)$ for the variable-density
   viscous step
2. GFM jump preservation under sequential $D_2$ ([[WIKI-T-017]]) — may need
   correction between inner and outer passes
3. Composite IPC+AB2+Padé-CN stability budget ([[WIKI-X-007]]) — capillary CFL
   unchanged, but viscous step budget needs re-derivation
4. Empirical $\beta^\star$ for realistic two-phase $\nu$ ratio — trade-off between
   4th-order constant and high-$k$ contraction

## Status

**PROPOSED — not implemented.** Documented as design path for 4th-order viscous
time integration. Production-valuable once §11 spatial convergence saturates the
CN temporal floor, or for high-Reynolds regimes where the viscous step dominates
runtime.

## One-Line Summary

*Padé-(2,2) CN yields $O(\Delta t^4)$ with A-stability intact; CCD coupling reduces
to "apply $D_2$ twice", reusing the cached `A_inv_dev` (CHK-119). Richardson-CN is
the cheaper sibling that ships first.*
