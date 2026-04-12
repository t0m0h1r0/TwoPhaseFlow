# Extended Crank–Nicolson × CCD: Design Note for 4th-Order Time Integration of the Diffusion Operator

**Date**: 2026-04-12
**Status**: Design proposal (not yet implemented)
**Scope**: Semi-implicit viscous/diffusion step $u_t = \nu L u$ with $L = \nabla^2$ discretized by CCD
**Related**: [[WIKI-T-001]] (CCD), [[WIKI-T-003]] (IPC+AB2+CN projection), [[WIKI-T-023]] (surface tension semi-implicit), [[WIKI-T-012]] (CCD elliptic + Kronecker), [[WIKI-T-015]] (DC theory)

---

## 1. Problem

Crank–Nicolson (CN) is the current time integrator for the viscous term in the variable-density projection path ([[WIKI-T-003]]):

$$
\frac{u^{n+1}-u^n}{\Delta t} = \nu\,\tfrac{1}{2}\,(L u^{n+1} + L u^n)
\quad\Longleftrightarrow\quad
(I - \alpha L)\,u^{n+1} = (I + \alpha L)\,u^n,\;
\alpha = \tfrac{\nu\Delta t}{2}.
$$

CN is:
- **A-stable** (unconditionally stable for dissipative $L$),
- **2nd order** in $\Delta t$,
- **energy-preserving** on the linear problem (Galerkin-orthogonal update).

It is *structurally complete* but *only 2nd order*, while our spatial operator is CCD ([[WIKI-T-001]], $O(h^6)$). When the viscous term matters (boundary layers, capillary-viscous coupling), 2nd-order temporal error dominates the $O(h^6)$ space budget at any practical $\Delta t$. This note surveys extensions that raise CN to 4th order **without breaking A-stability or the energy structure**, and fixes the canonical coupling to CCD.

**Design principle.** *CN is too finished to modify internally. Strengthen it from the outside.*

---

## 2. Four Families of CN Extensions

### 2.1 Richardson-extrapolated CN (cheapest)

Run one step of $\Delta t$ to obtain $u_1$, two steps of $\Delta t/2$ to obtain $u_2$, then combine
$u^{n+1} = (4u_2 - u_1)/3$.

- **Order**: $O(\Delta t^4)$
- **A-stability**: effectively preserved (product of CN updates)
- **GPU**: ideal — two CN solves, matrix-free, no new operator
- **Cost**: ~2× one CN step

### 2.2 Padé-(2,2) CN (theoretically clean, 4th order)

CN is the Padé-(1,1) approximant of $e^z$ with $z = \nu\Delta t\,L$:
$R_{1,1}(z) = (1 + z/2)/(1 - z/2)$.
The Padé-(2,2) approximant is

$$
R_{2,2}(z) = \frac{1 + \tfrac{z}{2} + \tfrac{z^2}{12}}{1 - \tfrac{z}{2} + \tfrac{z^2}{12}}
$$

giving the one-step scheme

$$
\boxed{\;\Bigl(I - \tfrac{z}{2} + \tfrac{z^2}{12}\Bigr)\,u^{n+1} = \Bigl(I + \tfrac{z}{2} + \tfrac{z^2}{12}\Bigr)\,u^n,
\qquad z = \nu\Delta t\,L.\;}
$$

- **Order**: $O(\Delta t^4)$
- **A-stability**: yes (Padé-(2,2) is A-stable, not L-stable; see §4)
- **Energy**: near-structural (mirror symmetry of $R_{2,2}$)
- **Cost**: requires $L^2 u$ — this is the entire implementation question (§3)

### 2.3 Deferred-correction CN (flexible order)

Use CN as the preconditioner/predictor, then iterate a residual-correction:

$$
u^{(0)} = \mathrm{CN}(u^n),\qquad u^{(k+1)} = u^{(k)} + \mathrm{CN}^{-1}\!\bigl(r^{(k)}\bigr),
$$

where $r^{(k)}$ is an $O(\Delta t^{p})$-accurate residual built from multiple stage evaluations. One correction step raises order to 3–4; arbitrary order is reachable at constant stencil. GPU is ideal: one CN kernel reused.

- **Order**: tunable (1 correction ≈ 3rd–4th order depending on residual construction)
- **A-stability**: inherits from CN
- **Cost**: $\sim (1+k)\times$ CN; no new operator
- **Risk**: convergence management near stiff modes

### 2.4 $\theta$-method with mode-dependent damping

$$
\frac{u^{n+1}-u^n}{\Delta t} = \nu\bigl[\theta L u^{n+1} + (1-\theta) L u^n\bigr].
$$

$\theta=\tfrac12$ recovers CN; $\theta > \tfrac12$ adds controlled numerical dissipation at high wavenumbers. A spectrally-weighted $\theta(k)$ or $\theta(t)$ can suppress the small residual wiggle Padé-(2,2) shows near Nyquist (§4) without altering the low-mode fidelity. This is a **stabilizer**, not an order-raising device.

---

## 3. Coupling to CCD: the $L^2$ Question

CCD delivers $L u = D_2 u$ to $O(h^6)$ via a compact block-tridiagonal solve; the operator is never assembled. Every extension in §2 that raises order beyond CN needs $L^2$ applied somewhere — this is the crux of the CCD coupling.

There are two structurally different routes:

### 3.1 Route A — *Sequential application* (recommended)

Treat $L^2 u$ as $D_2(D_2 u)$: two CCD solves back-to-back.

```text
w  = D_2 u     # one CCD pass → O(h^6)
L2 = D_2 w     # second CCD pass → O(h^6)
```

- **Preserves CCD structure**: no stencil widening, boundary treatment unchanged,
  Kronecker assembly ([[WIKI-T-012]]) reusable.
- **Matrix-free / GPU-native**: reuses the cached CCD factorization
  (post CHK-119 `A_inv_dev @ rhs_flat`, see [[WIKI-L-015]]).
- **Structural drift**: sequential $D_2(D_2 u)$ differs from the "true" $L^2 u$
  at $O(h^6)$, so Padé-(2,2) accuracy degrades to $O(h^6 + \Delta t^4)$ — **not a loss**
  since the space floor is already $h^6$.
- **Symmetry caution**: if $D_2$ is not self-adjoint (CCD interior is close-to-symmetric but
  boundary stencils break strict symmetry), then $D_2(D_2 u) \ne D_2^{\mathsf T} D_2 u$ and
  discrete energy drift can appear. Fix: use the *same* CCD operator on both passes
  (no re-factorization, no alias to a re-initialized state) and symmetrize explicitly
  only if Lyapunov drift is observed in long runs.

### 3.2 Route B — *Composite $D_4$ operator* (research)

Build a direct fourth-derivative CCD stencil $D_4$ and apply it as a single solve.
Theoretical appeal: guaranteed self-adjoint and exact fourth-order Hermite collocation.
**Rejected for this project**: boundary treatment of compact $D_4$ is an open research
question, interaction with GFM jumps ([[WIKI-T-017]]) is unknown, and implementation cost
is high for no measurable gain over Route A.

---

## 4. Final Scheme: Padé-(2,2) CN × CCD (Route A)

$$
\underbrace{\bigl(I - \alpha D_2 + \beta\,D_2(D_2 \cdot)\bigr)}_{\mathcal{A}}\,u^{n+1}
 \;=\;
\underbrace{u^n + \alpha\,D_2 u^n + \beta\,D_2(D_2 u^n)}_{\text{rhs}},
\qquad
\alpha = \tfrac{\nu\Delta t}{2},\quad
\beta  = \tfrac{(\nu\Delta t)^2}{12}.
$$

### Matrix-free evaluation kernel

```python
def apply_A(u, D2, alpha, beta):
    w  = D2(u)          # CCD pass 1  (cached A_inv_dev @ rhs_flat)
    w2 = D2(w)          # CCD pass 2
    return u - alpha*w + beta*w2
```

### Linear solver

- **Symmetric case** (uniform grid, periodic/Dirichlet BC): conjugate gradient.
- **General case** (non-uniform grid, GFM jump, mixed BC): BiCGSTAB or GMRES with an
  FD preconditioner, mirroring [[WIKI-T-005]] / [[WIKI-T-015]] (DC-PPE) but for the
  viscous solve.
- **GPU kernel-fusion target**: fuse the two `D2` calls with the `u − αw + βw2` reduction
  into one CUDA stream; use shared memory for the intermediate $w$ where possible.

### Energy property

The continuous energy identity is $\tfrac{d}{dt}\|u\|^2 = -2\nu\|\nabla u\|^2$. For the
Padé-(2,2) scheme, multiplying by $u^n + u^{n+1}$ and using $D_2 \approx D_2^{\mathsf T}$
gives

$$
\|u^{n+1}\|^2 - \|u^n\|^2
 \;=\; -\,\nu\Delta t\,\bigl\langle(u^n + u^{n+1}),\, -D_2(u^n + u^{n+1})\bigr\rangle
 \;+\; \varepsilon_{\text{sym}},
$$

where $\varepsilon_{\text{sym}} = O(h^{\min(4,\,p_{\text{bdry}})})$ is the CCD
boundary-stencil asymmetry. On periodic BC it vanishes; on wall BC it is below the
spatial floor. Padé-(2,2) is **A-stable but not L-stable**: $R_{2,2}(\infty) = 1$,
so the scheme does not annihilate Nyquist modes. In practice this means a residual
high-$k$ wiggle may appear on marginally-resolved shear layers. Mitigation: apply the
existing CCD dissipative filter ([[WIKI-T-002]]) once per step, or inject $\theta(k)$
damping (§2.4) above a cutoff.

---

## 5. Spectrally-Optimized and Filtered Variants

Keeping the $(I - \alpha D_2 + \beta D_2^2)$ skeleton, treat $\beta$ as a free parameter:

$$
\beta = \beta^\star(\nu\Delta t,\,\text{target band})
\quad\text{chosen to minimize } \|R(z) - e^z\|_{L^\infty}\text{ over }z\in[-K_{\max},0].
$$

- $\beta = (\nu\Delta t)^2/12$ recovers Padé-(2,2).
- $\beta$ slightly smaller improves the high-$k$ contraction (quasi-L-stable) at the
  cost of 4th-order constant.
- A mode-dependent $\beta(k)$ (applied spectrally or via a short compact convolution)
  yields a **filtered Padé-CN**: near-optimal amplification factor, energy-bounded,
  still matrix-free on GPU.

This is the research-grade extension; the production recommendation is **fixed
$\beta = (\nu\Delta t)^2/12$ + optional [[WIKI-T-002]] filter on the residual wiggle**.

---

## 6. Recommendation for This Project

| Option                       | When to use                                                  | Verdict |
|------------------------------|--------------------------------------------------------------|---------|
| (A) Richardson-CN            | Drop-in 4th order, minimal code risk, CI validation          | **ship first** |
| (B) Padé-(2,2) CN × CCD      | Production target once Route A is verified against (A)        | **ship second** |
| (C) DC-CN (1 correction)     | Fallback if Padé-(2,2) wiggle is intolerable and §2.4 too crude | fallback |
| (D) Composite $D_4$          | Research only, out of scope                                  | reject |

**Step 1.** Implement (A) as a `RichardsonCNAdvance` wrapper around the existing CN
step — no new operator, no PR-5 risk. Use as the reference solution.

**Step 2.** Implement (B) as `Pade22CNAdvance` using the matrix-free kernel in §4,
BiCGSTAB + FD preconditioner, `A_inv_dev` cache reused from the CCD PPE path.
Verify 4th-order temporal convergence against (A) on a manufactured solution.
Add the [[WIKI-T-002]] filter hook for high-$k$ wiggle.

**Step 3.** Experiment proposal (next ExperimentRunner CHK):
`exp11_30_extended_cn_convergence` — manufactured viscous solution $u = e^{-\nu k^2 t}\sin(kx)\sin(ky)$,
methods $\{$CN, Richardson-CN, Padé-CN$\}$, grid $N\in\{32,64,128\}$, report temporal
convergence order and long-time energy drift. Baseline CN should give $O(\Delta t^2)$,
both extensions should give $O(\Delta t^4)$.

---

## 7. Open Questions

1. **BC symmetry**: does the CCD wall-BC stencil asymmetry contaminate $D_2(D_2 u)$
   enough to matter in the two-phase variable-density viscous step? Test with a
   non-periodic manufactured solution.
2. **GFM interaction**: the viscous term sees jump conditions at the interface ([[WIKI-T-017]]).
   Does sequential $D_2$ preserve the jump order, or does the inner $w = D_2 u$ need
   a GFM correction before the outer $D_2$?
3. **CFL budget**: Padé-(2,2) is A-stable for pure diffusion but the composite
   IPC+AB2+Padé-CN path needs a fresh stability budget ([[WIKI-X-007]]).
4. **$\beta^\star$**: empirical optimum for the actual two-phase $\nu$ ratio and grid
   — possibly $\beta$ slightly below the Padé value to gain L-stable-like behavior.

---

## 8. One-line Summary

*Padé-(2,2) CN delivers $O(\Delta t^4)$ with A-stability intact; coupling to CCD
reduces to "apply $D_2$ twice", and the cached `A_inv_dev` (CHK-119) makes it
cheap on GPU. Richardson-CN is the cheaper sibling that ships first.*

---

## Source

- User design notes, 2026-04-12 (two-stage: CN extensions survey + CCD coupling).
- CCD baseline: [[WIKI-T-001]], [[WIKI-T-011]], [[WIKI-T-012]]
- CN/projection baseline: [[WIKI-T-003]]
- GPU floor: CHK-119 `A_inv_dev` dense-inverse cache
- Filter hook: [[WIKI-T-002]], [[WIKI-T-019]]
