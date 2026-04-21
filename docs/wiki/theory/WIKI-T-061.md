---
ref_id: WIKI-T-061
title: "Upwind⊕CCD Pedagogical Foundation: Von Neumann Stability and Dissipative Hybrid Derivation"
domain: theory
status: ACTIVE
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-G_upwind_ccd_pedagogical.md
    description: "Von Neumann proof for upwind; upwind-biased Chu&Fan CCD hybrid; semi-discrete stability"
depends_on:
  - "[[WIKI-T-001]]: CCD Method (Chu&Fan 1998 baseline)"
  - "[[WIKI-T-002]]: Dissipative CCD Filter (production DCCD form)"
  - "[[WIKI-T-013]]: WENO5 vs DCCD Comparative Advection"
consumers:
  - domain: theory
    description: "Provides the von-Neumann foundation behind T-002 spectral-filter choice and T-046 FCCD face-upwind rationale"
  - domain: paper
    description: "Section-2 pedagogical derivation (stability budget → dissipation budget)"
tags: [stability, von_neumann, upwind, ccd, dccd, pedagogical, modified_equation]
compiled_by: ResearchArchitect
compiled_at: "2026-04-21"
---

# Upwind ⊕ CCD Pedagogical Foundation

## Purpose

Provide the **pedagogical / foundational derivation** of why a Chu & Fan (1998) CCD operator is *combined with upwind-biased dissipation* in the project's production DCCD stack ([WIKI-T-002](WIKI-T-002.md)). Formalises three classical exercises into project-coherent lemmas and exposes their scope boundaries. This entry **does not** introduce new numerics; it closes the "why this shape" gap that T-002 and T-046 both assume.

## §1 — Exercise 1: Von Neumann stability of 1st-order upwind

Scheme (forward Euler, $c>0$, uniform $\Delta x$):

$$
u_i^{n+1} = (1-\nu)u_i^n + \nu u_{i-1}^n, \qquad \nu = \frac{c\,\Delta t}{\Delta x}.
$$

Fourier mode $u_j^n = G^n e^{Ikj\Delta x}$ gives

$$
|G|^2 = 1 - 2\nu(1-\nu)(1-\cos(k\Delta x)).
$$

**Lemma 1 (CFL).** $|G|\le 1\ \forall k\iff 0\le\nu\le 1$.

**Modified-equation companion.** Taylor expansion of the upwind truncation yields an implicit dissipation $D_\nu=\tfrac{c\Delta x}{2}(1-\nu)$, so the scheme actually advances

$$
\partial_t u + c\,\partial_x u \;=\; D_\nu\,\partial_x^2 u + \mathcal O(\Delta x^2).
$$

The **second-derivative term** is the physically-grounded source of stability.

## §2 — Exercise 2: Upwind-biased Chu & Fan CCD (DCCD-type hybrid)

Chu & Fan (1998) central CCD ([WIKI-T-001](WIKI-T-001.md)) yields high-order but **non-dissipative** derivatives. Transplant the §1 modified-equation dissipation onto CCD's *own* high-order second derivative:

$$
\boxed{\;\partial_t u_i + c\,(u'_i)_{\text{CCD}} \;=\; \varepsilon\,|c|\,\Delta x\,(u''_i)_{\text{CCD}}\;}\qquad(\varepsilon>0).
$$

The left side carries spectral resolution; the right side provides controlled dissipation through **the same operator family** (avoiding stencil mismatch — mirrors the balanced-force principle of [WIKI-T-004](WIKI-T-004.md)).

### §2.1 — Relation to production forms
- **Spectral-filter DCCD ([WIKI-T-002](WIKI-T-002.md)):** equivalent low-wavenumber behaviour with $\varepsilon\sim\varepsilon_d$, but the transfer function $H(\xi)=1-4\varepsilon_d\sin^2(\xi/2)$ preserves DC and 6h wavelengths to $\mathcal O(\varepsilon_d)$ — superior to constant-$\varepsilon$ PDE form (see §4).
- **FCCD ([WIKI-T-046](WIKI-T-046.md)):** different remedy — cancels truncation at faces rather than injecting dissipation. Orthogonal to this entry.

## §2.2 — Operator-level variant: upwind-biased CCD matrix

A second realisation of the same **upwind ⊕ CCD** principle modifies the CCD **operator matrix itself** rather than adding a PDE-level dissipation. Starting from Chu & Fan's Eq-I with $\alpha_1=7/16,\ a_1=15/16$:

$$
\tfrac{7}{16}(u'_{j+1}+u'_{j-1}) + u'_j
\;=\; \tfrac{15}{16\,\Delta x}(u_{j+1}-u_{j-1})
\;-\; \operatorname{sign}(a)\,\tfrac{\alpha}{\Delta x}\,\delta^4 u_j.
$$

The bias term $-\operatorname{sign}(a)(\alpha/\Delta x)\,\delta^4 u_j$ injects odd-order truncation, breaking the symbol's symmetry and producing a non-zero real part in the semi-discrete eigenvalue. Stability of the resulting block-symbol $\mathbf M_1^{-1}\mathbf M_2$ acting on $\mathbf V_j = [u_j,\,\Delta x\,u'_j]^T$ follows from

$$
\rho(\mathbf G(\beta)) = \rho(\mathbf M_1^{-1}\mathbf M_2) \le 1,\qquad \forall\beta\in[0,\pi],
$$

provided $\alpha>0$ and the time-integrator stability region contains $\{\Delta t\cdot\lambda(\mathbf G-I)/\Delta t\}$.

### §2.2.1 — Relation to §2 PDE-level variant
The operator-level and PDE-level variants are dual: §2 injects dissipation *after* the high-order derivative is evaluated; §2.2 modifies the derivative *definition* itself. Both recover the small-$kh$ spectral envelope of the production DCCD filter ([WIKI-T-002](WIKI-T-002.md)).

### §2.2.2 — Scope penalties (new counterarguments)
- **CA-7 Stencil enlargement**: if $\delta^4 = (u_{j-2}-4u_{j-1}+6u_j-4u_{j+1}+u_{j+2})/\Delta x^4$ (standard central 4th diff), the compact 3-point footprint of CCD is broken ⇒ interface crossing and wall treatment both regress.
- **CA-8 Block-solver asymmetry**: biasing Eq-I but not Eq-II destroys the symmetric 2×2 block Thomas structure ([WIKI-T-001](WIKI-T-001.md)); solver complexity rises unless both equations are biased consistently.
- **CA-9 $\alpha$ scaling**: to preserve $\mathcal O(h^6)$ interior accuracy, $\alpha=\mathcal O(h^p)$ with $p\ge 3$ is required (since $\delta^4/\Delta x$ contributes $\mathcal O(h^3)$ at fixed $\alpha$).

## §3 — Exercise 3: Semi-discrete Fourier stability

For Chu & Fan central CCD the modified wavenumbers are real:

$$
(u'_j)_{\text{CCD}} = \tfrac{I}{\Delta x}k_{\text{eq}}\hat u,\qquad
(u''_j)_{\text{CCD}} = -\tfrac{1}{\Delta x^2}m_{\text{eq}}\hat u,
$$

with $m_{\text{eq}}(k\Delta x)\ge 0$ for all $k\Delta x\in[0,\pi]$ (verified below).

Substitution gives

$$
\frac{d\hat u}{dt} = \lambda\hat u,\qquad
\lambda = -\varepsilon|c|\frac{m_{\text{eq}}}{\Delta x} - Ic\frac{k_{\text{eq}}}{\Delta x}.
$$

**Lemma 2 (semi-discrete stability).** $\operatorname{Re}\lambda=-\varepsilon|c|m_{\text{eq}}/\Delta x\le 0$ for all $k$. Equality only at $m_{\text{eq}}=0$ (DC mode).

### §3.1 — $m_{\text{eq}}\ge 0$ for Chu & Fan coefficients
Central CCD Eq-II with $(\beta_2,a_2,b_2)=(-1/8,3,-9/8)$ is diagonalised by Fourier modes; symmetry of the compact operator matrix ⇒ real eigenvalues; small-$kh$ expansion gives $m_{\text{eq}}=(kh)^2+\mathcal O((kh)^6)$; monotone increase to $m_{\text{eq}}(\pi)\approx 11$ (numerical). **No sign change on $[0,\pi]$.**

## §4 — Counterarguments and scope boundary

| # | Claim in exercise | Scope limitation | Project-internal resolution |
|---|-------------------|------------------|-----------------------------|
| C1 | Von Neumann $\Rightarrow$ stable | necessary only; sufficient requires GKS on bounded domain + Kreiss condition for BC | [WIKI-T-012](WIKI-T-012.md) provides periodic/closure BC analysis |
| C2 | $\varepsilon\|c\|\Delta x\cdot u''$ is "artificial viscosity" | formal accuracy degrades to $\mathcal O(\Delta x)$ for $\varepsilon=\text{const}$ | production DCCD ([WIKI-T-002](WIKI-T-002.md)) uses spectral-filter form preserving 6h@95%; equivalent to $\varepsilon(k)\propto \sin^2(kh/2)$ |
| C3 | $m_{\text{eq}}\ge 0$ asserted | requires Chu & Fan-specific verification | §3.1 confirms analytically for central CCD; **does not** hold for one-sided boundary rows ⇒ near-wall care |
| C4 | Semi-discrete $\operatorname{Re}\lambda\le 0$ $\Rightarrow$ stable | fully-discrete stability needs $\Delta t\cdot\lambda$ inside RK stability region | TVD-RK3: $\|Im(\lambda)\Delta t\|\le\sqrt{3}$; with dissipation, viable CFL widens |
| C5 | 1D linear $c=\text{const}$ | nonlinear / variable-$c$ / multi-D needs frozen-coefficient + energy estimate | project uses global-LF splitting for WENO5 comparison ([WIKI-T-013](WIKI-T-013.md)) |
| C6 | Excessive $\varepsilon$ | parabolic CFL $\Delta t\cdot\varepsilon\|c\|/\Delta x\le$ const becomes binding | adaptive control via switch $S(\psi)=(2\psi-1)^2$ ([WIKI-T-002](WIKI-T-002.md)) localises dissipation to bulk, disables at interface |
| C7 | $\delta^4$ breaks 3-point compactness (§2.2) | stencil enlarges to 5 points; interface / wall regress | restrict $\delta^4$ to a CCD-internal reconstruction (e.g., $(u''_{j+1}-2u''_j+u''_{j-1})$ from CCD second derivative) — preserves compact footprint |
| C8 | One-sided bias breaks block-Thomas symmetry (§2.2) | solver complexity rises; no shared LU factorisation | bias Eq-I **and** Eq-II jointly, keeping the $2\times 2$ block structure (Sengupta-Bhumkar 2020 OUCS3 class) |
| C9 | $\alpha=\mathrm{const}$ degrades $\mathcal O(h^6)$ (§2.2) | formal order falls to $\mathcal O(h^3)$ | $\alpha=\mathcal O(h^p)$, $p\ge 3$; in production DCCD this is handled implicitly by the spectral filter form ([WIKI-T-002](WIKI-T-002.md)) |
| C10 | Block-matrix spectral radius $\rho\le 1$ is necessary, not sufficient, for fully-discrete RK | C4 generalises: explicit $\Delta t\cdot\rho(\mathbf G)$ must lie inside RK polygon | same RK-CFL argument as §5.3 of SP-G; L-stability of time integrator (backward Euler, SDIRK) removes the restriction at cost of implicit solve |

## §5 — Positioning within the project

```
         upwind stability (Ex.1, §1)
               │ modified-equation
               ▼
     dissipation = c·Δx·u_xx   ←   central CCD u''  (Ex.2, §2)
               │                   [WIKI-T-001]
               ▼
     DCCD-type PDE hybrid           →   spectral-filter production form
                                        [WIKI-T-002]   ← preferred in pipeline
               │
               ▼ (orthogonal)
     face-upwind truncation cancel  →  FCCD
                                        [WIKI-T-046]   ← BF-consistency path
```

This entry supplies the **stability-budget reasoning** used implicitly by T-002 and T-046 but not previously written down as a self-contained lemma chain.

## §6 — Two-point Hermite foundation (boundary / upwind closure)

At walls or when imposing strict upwind causality, the 3-point Chu&Fan interior rows must be replaced by **2-point** relations using only $\{i-1, i\}$ data. With 6 inputs $\{u_{i-1}, u_i, u'_{i-1}, u'_i, u''_{i-1}, u''_i\}$ the 5th-degree Hermite polynomial $P(x)$ is uniquely determined; every 2-point relation is a consequence of $P$.

### §6.1 Unique 4th-order 2-point compact relation

Taylor expansion around the midpoint $c = x_{i-1/2}$:

$$
u'_i + u'_{i-1} - \frac{h}{6}(u''_i - u''_{i-1}) \;=\; \frac{2}{h}(u_i - u_{i-1}) + \mathcal O(h^4).
$$

**Verified** by monomial match $u\in\{1,x,x^2,x^3\}$ (exact) and $u=x^4$ ($\mathcal O(h^4)$ residual). The coefficient $-1/6$ is the **unique** value yielding 4th order; any other coefficient (e.g., the commonly-miswritten $+h/10$) degrades to $\mathcal O(h^2)$.

> **Structural note.** With $(u, u', u'')$ specified at both points, the 5th-order Hermite polynomial has 0 residual degrees of freedom — §6.1 is the *only* independent 4th-order 2-point identity. Any purported "second 2-point equation" (e.g., $\tfrac{h}{12}(u''_i \pm u''_{i-1}) = \tfrac{1}{h}(u_i-u_{i-1}) - \tfrac12(u'_i+u'_{i-1})$) is a rearrangement of §6.1, not an independent constraint.

### §6.2 Fifth-order Hermite midpoint reconstruction

At the face $x_{i-1/2}$:

$$
\boxed{\begin{aligned}
u_{i-1/2} &= \tfrac{1}{2}(u_i + u_{i-1}) - \tfrac{5h}{32}(u'_i - u'_{i-1}) + \tfrac{h^2}{64}(u''_i + u''_{i-1}), \\[2pt]
u'_{i-1/2} &= \tfrac{15}{8h}(u_i - u_{i-1}) - \tfrac{7}{16}(u'_i + u'_{i-1}) + \tfrac{h}{32}(u''_i - u''_{i-1}), \\[2pt]
u''_{i-1/2} &= \tfrac{3}{2h}(u'_i - u'_{i-1}) - \tfrac{1}{4}(u''_i + u''_{i-1}).
\end{aligned}}
$$

Derivation: invert the 6×6 Hermite interpolation matrix in (even, odd) block form. **Verified exact on monomials $x^n,\ 0\le n\le 5$** (details: $u(h/2)=h^2/4$ for $u=x^2$ with $x_{i-1}=0,x_i=h$; $u'(h/2)=3h^2/4$ for $u=x^3$; $u''(h/2)=2$ for $u=x^2$). Leading truncation $\mathcal O(h^6)$ for smooth $u$.

### §6.3 Flux handoff to Riemann solver (conceptual pathway)

The face values $u_{i-1/2}, u'_{i-1/2}$ from §6.2 enable a hybrid high-order/upwind transport:

1. Compute $(u', u'')$ at nodes via interior Chu&Fan CCD ([WIKI-T-001](WIKI-T-001.md)).
2. Reconstruct $u_{i-1/2}^{L/R}$ using §6.2 with upwind-biased neighbours (e.g., $\{i-2, i-1\}$ and $\{i, i+1\}$).
3. Feed $(u^L, u^R)$ to a Riemann solver (HLLC, Roe, upwind LF) to obtain face flux $F_{i-1/2}$.
4. Update with conservative finite-volume: $\partial_t u_i = -(F_{i+1/2} - F_{i-1/2})/h$.

This pathway is **orthogonal** to the §2 (dissipation-injected) and §2.2 (operator-biased) variants: it retains CCD at nodes and introduces upwinding only through the face-state selection into the Riemann solver, preserving 5th-order interior accuracy while inheriting the robustness of upwind flux evaluation. Complementary to FCCD ([WIKI-T-046](WIKI-T-046.md)) which defines the face derivative directly rather than via state-reconstruction.

### §6.4 Common miswritten coefficients (anti-pattern catalogue)

| Quantity | Miswritten | Correct | Error if used |
|----------|-----------|---------|---------------|
| 2-pt Eq-A coefficient | $+h/10$ | $-h/6$ | $\tfrac{4}{15}h^2 u'''$ residual ⇒ $\mathcal O(h^2)$ |
| $u_{i-1/2}$ $u'$ term | $-h/8$ | $-5h/32$ | $\mathcal O(h^2)$ (cubic-Hermite level only) |
| $u_{i-1/2}$ $u''$ term | $+h^2/48$ | $+h^2/64$ | incompatible with $-h/8$ correction above |
| $u'_{i-1/2}$ $u$ term | $+3/(2h)$ | $+15/(8h)$ | $\mathcal O(h^2)$ |
| $u''_{i-1/2}$ alleged $\tfrac{h}{4}(u''_i+u''_{i-1})$ | — | $\tfrac{3}{2h}(u'_i-u'_{i-1})-\tfrac14(u''_i+u''_{i-1})$ | dimensional mismatch |

## References
- Chu, P.C. & Fan, C. (1998). "A three-point combined compact difference scheme." *J. Comput. Phys.* **140**, 370–399.
- LeVeque, R.J. (2002). *Finite Volume Methods for Hyperbolic Problems*. CUP. §8.3 (modified equation), §8.4 (upwind stability).
- Gustafsson, B., Kreiss, H.-O., Sundström, A. (1972). "Stability theory of difference approximations for mixed initial boundary value problems." *Math. Comp.* **26**, 649–686.
