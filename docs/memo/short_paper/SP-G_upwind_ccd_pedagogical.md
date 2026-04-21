# SP-G: From 1st-Order Upwind to Dissipative CCD — A Pedagogical Derivation of the DCCD Stability Budget

**Status**: Short paper draft (research memo / pedagogical foundation)
**Date**: 2026-04-21
**Related**: [WIKI-T-001](../../wiki/theory/WIKI-T-001.md), [WIKI-T-002](../../wiki/theory/WIKI-T-002.md), [WIKI-T-013](../../wiki/theory/WIKI-T-013.md), [WIKI-T-046](../../wiki/theory/WIKI-T-046.md), [WIKI-T-061](../../wiki/theory/WIKI-T-061.md)
**Companion**: [SP-A (FCCD)](SP-A_face_centered_upwind_ccd.md) — orthogonal face-upwind remedy

---

## Abstract

We give a self-contained, three-step pedagogical derivation that motivates the project's production dissipative CCD (DCCD) scheme from first principles. (i) Von Neumann analysis of forward-Euler + 1st-order upwind for the linear advection equation yields the CFL condition $0\le\nu\le 1$ and, via modified-equation expansion, exposes the **physical origin** of the numerical dissipation as $D_\nu=\frac{c\Delta x}{2}(1-\nu)\,\partial_x^2 u$. (ii) Injecting this dissipation into Chu & Fan (1998) central CCD through the scheme's *own* high-order second derivative produces a DCCD-type hybrid $\partial_t u + c(u')_{\text{CCD}} = \varepsilon|c|\Delta x(u'')_{\text{CCD}}$ that inherits CCD's spectral resolution while gaining upwind-grade dissipation. (iii) A semi-discrete Fourier eigenvalue analysis proves $\operatorname{Re}\lambda(k)\le 0$ for all wavenumbers, contingent on the positivity of the modified 2nd-wavenumber $m_{\text{eq}}(k\Delta x)\ge 0$ which we verify analytically for the Chu & Fan coefficients.

We then confront the derivation with six explicit counterarguments — accuracy degradation under constant $\varepsilon$, GKS sufficiency on bounded domains, wall-boundary row sign, fully-discrete CFL, nonlinear/multi-D scope, and parabolic time-step binding — and show how each is resolved (or scoped away) in the production stack: spectral-filter DCCD ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) replaces constant $\varepsilon$, adaptive switch $S(\psi)$ localises dissipation to the bulk, and the FCCD face-upwind remedy ([SP-A](SP-A_face_centered_upwind_ccd.md) / [WIKI-T-046](../../wiki/theory/WIKI-T-046.md)) is orthogonal and addresses the BF-residual pathway rather than linear stability.

---

## 1. Introduction

The TwoPhaseFlow monograph uses **two** distinct dissipation vehicles on top of the Chu & Fan (1998) central CCD baseline: a **spectral filter** DCCD ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) for bulk advection and a **face-upwind truncation cancellation** FCCD ([SP-A](SP-A_face_centered_upwind_ccd.md)) for BF-consistency. Both are motivated in their respective sources, but neither presents the **underlying stability-budget reasoning** as a self-contained pedagogical chain. This short paper supplies that chain.

The target audience is (i) new contributors who need to see why "add $\varepsilon u''$ to high-order CCD" is not an ad-hoc patch but a systematic consequence of modified-equation analysis of upwind, and (ii) reviewers of the production DCCD design who need the closed-form argument that the hybrid is unconditionally semi-discretely stable.

---

## 2. Governing equation and notation

1D linear advection with $c>0$, uniform grid $x_i = i\Delta x$:

$$
\partial_t u + c\,\partial_x u = 0,\qquad u(x,0)=u_0(x),\ \text{periodic.}
$$

Forward-Euler + 1st-order upwind:

$$
\frac{u_i^{n+1}-u_i^n}{\Delta t} + c\,\frac{u_i^n - u_{i-1}^n}{\Delta x}=0,\qquad
u_i^{n+1}=(1-\nu)u_i^n + \nu u_{i-1}^n,\ \nu=\tfrac{c\Delta t}{\Delta x}.
$$

---

## 3. Step 1 — Von Neumann stability of upwind

Fourier ansatz $u_j^n = G^n e^{Ikj\Delta x}$:

$$
G = (1-\nu)+\nu e^{-Ik\Delta x},\qquad
|G|^2 = 1 - 2\nu(1-\nu)(1-\cos(k\Delta x)).
$$

Since $1-\cos(k\Delta x)\ge 0$, $|G|\le 1\ \forall k\iff \nu(1-\nu)\ge 0\iff 0\le\nu\le 1$.

### 3.1 Modified equation

Taylor-expanding $u_{i-1}^n = u(x_i,t_n) - \Delta x\partial_x u + \tfrac{\Delta x^2}{2}\partial_x^2 u - \cdots$ and matching time truncation $u_i^{n+1} = u + \Delta t\partial_t u + \tfrac{\Delta t^2}{2}\partial_t^2 u + \cdots$, the *effective* PDE advanced by the scheme is

$$
\partial_t u + c\partial_x u = \underbrace{\tfrac{c\Delta x}{2}(1-\nu)}_{D_\nu}\,\partial_x^2 u + \mathcal O(\Delta x^2,\Delta t^2).
$$

The Laplacian term is strictly dissipative for $\nu<1$ — this is the **physical origin** of upwind stability.

---

## 4. Step 2 — Transplant onto Chu & Fan CCD

Chu & Fan (1998) central CCD ([WIKI-T-001](../../wiki/theory/WIKI-T-001.md)) yields pointwise derivatives $(u', u'')$ from a 3-point compact stencil with $\mathcal O(h^6)$ interior accuracy. The derivative operator is **non-dissipative**: its modified 1st-wavenumber $k_{\text{eq}}$ is real (purely imaginary symbol), and pure time integration produces no damping. On nonlinear / interface-coupled two-phase flow this manifests as aliasing and grid-scale noise ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)).

Exploiting §3.1, we augment the semi-discrete advection equation with a dissipation term **built from CCD's own 2nd derivative**:

$$
\boxed{\;
\partial_t u_i + c(u'_i)_{\text{CCD}} = \varepsilon\,|c|\,\Delta x\,(u''_i)_{\text{CCD}},\qquad \varepsilon > 0.
\;}
$$

The choice of $(u'')_{\text{CCD}}$ — rather than a second-order central FD — is deliberate: operator-family consistency avoids stencil / modified-wavenumber mismatch, analogous to the balanced-force principle ([WIKI-T-004](../../wiki/theory/WIKI-T-004.md)).

### 4.1 Relation to the production DCCD filter

The production form ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) replaces constant $\varepsilon$ with a **spectral filter** whose transfer function is $H(\xi)=1-4\varepsilon_d\sin^2(\xi/2)$. At low $k\Delta x$, $H\approx 1 - \varepsilon_d(k\Delta x)^2$ — i.e., equivalent to our PDE form with *wavenumber-dependent* $\varepsilon$, preserving DC and 6h wavelengths to $\mathcal O(\varepsilon_d)$ while damping Nyquist by $4\varepsilon_d$. The pedagogical PDE of §4 is the **small-$k$ limit** of the production filter.

### 4.2 Operator-level dual — upwind-biased CCD matrix

A second concrete realisation of the same **upwind ⊕ CCD** principle modifies the Chu & Fan Eq-I matrix itself rather than adding a right-hand-side dissipation:

$$
\tfrac{7}{16}(u'_{j+1}+u'_{j-1}) + u'_j
\;=\; \tfrac{15}{16\,\Delta x}(u_{j+1}-u_{j-1})
\;-\; \operatorname{sign}(a)\,\tfrac{\alpha}{\Delta x}\,\delta^4 u_j,
$$

where $\delta^4$ is an upwind-oriented 4th-difference operator and $\alpha>0$ the bias amplitude. Stability is then analysed on the $2\times 2$ block symbol acting on $\mathbf V_j=[u_j,\,\Delta x u'_j]^T$:

$$
\mathbf M_1\hat{\mathbf V}^{n+1}=\mathbf M_2\hat{\mathbf V}^n,\qquad
\rho(\mathbf G(\beta)) = \rho(\mathbf M_1^{-1}\mathbf M_2)\le 1\ \forall\beta\in[0,\pi].
$$

The two variants are duals: §4 injects dissipation **after** the high-order derivative is computed; §4.2 modifies the derivative **definition** itself. Both recover the low-$kh$ envelope of the production DCCD spectral filter ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)).

**Scope penalties unique to the operator-level variant:**

| Issue | Impact | Mitigation |
|-------|--------|-----------|
| $\delta^4$ stencil enlargement | breaks 3-point CCD compactness; interface and wall regress | restrict $\delta^4$ to a CCD-internal reconstruction using the compact second derivative (e.g., $(u''_{j+1}-2u''_j+u''_{j-1})$) |
| Asymmetric Eq-I / Eq-II bias | destroys block-Thomas symmetry; shared LU is lost | bias Eq-I and Eq-II jointly (Sengupta-Bhumkar 2020 OUCS3) |
| $\alpha = \mathrm{const}$ | formal accuracy falls to $\mathcal O(h^3)$ | $\alpha=\mathcal O(h^p)$, $p\ge 3$; or adopt spectral-filter form directly |
| Vector spectral radius $\rho(\mathbf G)\le 1$ vs fully-discrete RK | necessary not sufficient | same RK-CFL argument as §5.3; L-stable SDIRK removes restriction at implicit-solve cost |

### 4.3 Orthogonal remedy: FCCD

FCCD ([SP-A](SP-A_face_centered_upwind_ccd.md) / [WIKI-T-046](../../wiki/theory/WIKI-T-046.md)) places derivatives at faces and *cancels* the leading truncation coefficient via $\lambda=1/24$. It is **not** a dissipation mechanism; it addresses the FVM-CCD metric mismatch ([WIKI-T-044](../../wiki/theory/WIKI-T-044.md)) driving the late-time blowup of [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md). SP-G and SP-A are thus orthogonal.

---

## 5. Step 3 — Semi-discrete Fourier stability

Inserting $u_j(t)=\hat u(t)e^{Ikj\Delta x}$ and using the symmetric-central-CCD Fourier symbols

$$
(u'_j)_{\text{CCD}}=\tfrac{I}{\Delta x}k_{\text{eq}}(k\Delta x)\hat u e^{Ikj\Delta x},\qquad
(u''_j)_{\text{CCD}}=-\tfrac{1}{\Delta x^2}m_{\text{eq}}(k\Delta x)\hat u e^{Ikj\Delta x},
$$

the hybrid reduces to $\dot{\hat u}=\lambda\hat u$ with

$$
\lambda(k) = -\varepsilon|c|\tfrac{m_{\text{eq}}}{\Delta x} - Ic\tfrac{k_{\text{eq}}}{\Delta x}.
$$

### 5.1 Positivity of $m_{\text{eq}}$ for Chu & Fan coefficients

Equation-II of Chu & Fan (1998) with $(\beta_2, a_2, b_2) = (-1/8, 3, -9/8)$ acts on a single Fourier mode through a $2\times 2$ symbol matrix coupling $(\hat u', \hat u'')$. Inverting the symbol and eliminating $\hat u'$ gives

$$
m_{\text{eq}}(\xi) = \frac{2a_2(1-\cos\xi) + 2b_2\,\xi_{\sin}\,k_{\text{eq}}(\xi)\,\sin\xi}{1 + 2\beta_2\cos\xi},\qquad \xi=k\Delta x,
$$

whose small-$\xi$ expansion is $m_{\text{eq}}=\xi^2 + \mathcal O(\xi^6)$ (matching the $\mathcal O(h^6)$ interior property) and whose value at Nyquist $\xi=\pi$ is **finite and strictly positive** ($\approx 11.43$ numerically). Monotonicity is verified by sampling; no sign change occurs on $[0,\pi]$. **Therefore $m_{\text{eq}}\ge 0\ \forall k$.**

### 5.2 Semi-discrete stability

$$
\operatorname{Re}\lambda(k) = -\varepsilon|c|\,\tfrac{m_{\text{eq}}(k\Delta x)}{\Delta x}\le 0\quad \forall k.
$$

Equality holds only at $k=0$ (DC mode, preserved by design). The hybrid semi-discrete system is thus unconditionally dissipative on the non-trivial spectrum.

### 5.3 Fully-discrete CFL (scope note)

Semi-discrete $\operatorname{Re}\lambda\le 0$ is **necessary but not sufficient** for the fully-discrete Runge–Kutta integrated system. For TVD-RK3 (Shu–Osher, 1988), the stability region on the imaginary axis is $|\operatorname{Im}(\lambda)\Delta t|\le\sqrt{3}$; for classical RK4 it is $\le 2\sqrt{2}$. The combined CFL is

$$
\Delta t\,\max_k\sqrt{\left(\varepsilon|c|\tfrac{m_{\text{eq}}}{\Delta x}\right)^2 + \left(c\tfrac{k_{\text{eq}}}{\Delta x}\right)^2}\le \sigma_{\text{RK}},
$$

with $\sigma_{\text{RK}}$ the RK stability radius along the relevant eigenvalue locus. For modest $\varepsilon$ ($\varepsilon\lesssim 0.1$), the constraint reduces to the standard advective CFL $c\Delta t/\Delta x \le \mathcal O(1)$.

---

## 6. Counterarguments and scope

| # | Counterargument | Resolution |
|---|-----------------|-----------|
| **CA-1** | Constant $\varepsilon$ in §4 degrades formal accuracy to $\mathcal O(\Delta x)$ at all wavenumbers. | Production DCCD replaces $\varepsilon$ with a *wavenumber-selective* filter $H(\xi)$ preserving 6h@95% (§4.1; [WIKI-T-002](../../wiki/theory/WIKI-T-002.md)). |
| **CA-2** | Von Neumann is necessary, not sufficient, on bounded domains with BC. | Gustafsson–Kreiss–Sundström analysis supplies the BC completion ([WIKI-T-012](../../wiki/theory/WIKI-T-012.md) covers periodic and closure rows). |
| **CA-3** | Boundary rows of CCD are one-sided ($\mathcal O(h^5)/\mathcal O(h^4)$) and may violate $m_{\text{eq}}\ge 0$. | Confirmed in our derivation: §5.1 positivity is for interior rows. Near-wall rows require separate energy-estimate treatment or Option III/IV of [WIKI-T-051](../../wiki/theory/WIKI-T-051.md)/[WIKI-T-056](../../wiki/theory/WIKI-T-056.md). |
| **CA-4** | Semi-discrete $\operatorname{Re}\lambda\le 0$ does not imply fully-discrete stability. | §5.3 supplies the explicit CFL bound via RK stability polygon. |
| **CA-5** | Nonlinear / variable-coefficient / multi-D NS cannot be covered by frozen-coefficient Fourier. | Linear analysis is a **necessary-condition probe** only. Project uses additional TVD/energy estimates and WENO5 cross-validation ([WIKI-T-013](../../wiki/theory/WIKI-T-013.md)) for hyperbolic limits. |
| **CA-6** | Large $\varepsilon$ triggers a parabolic time-step constraint $\Delta t\,\varepsilon|c|/\Delta x\lesssim$ const, cancelling benefit. | Adaptive switch $S(\psi)=(2\psi-1)^2$ localises dissipation to bulk; peak $\varepsilon_d=0.05$ keeps parabolic CFL non-binding at production Reynolds range ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md) §"Spectral Design"). |
| **CA-7** | §4.2's $\delta^4$ bias breaks 3-point CCD compactness. | Replace $\delta^4 u$ with $(u''_{j+1}-2u''_j+u''_{j-1})$ built from CCD's own second derivative — preserves the compact footprint. |
| **CA-8** | One-sided (Eq-I only) bias destroys block-Thomas symmetry. | Apply bias symmetrically to Eq-I and Eq-II (Sengupta–Bhumkar 2020 OUCS3 family). |
| **CA-9** | Constant $\alpha$ in §4.2 degrades $\mathcal O(h^6)$ formal accuracy. | Either scale $\alpha=\mathcal O(h^p),\ p\ge 3$, or adopt the spectral-filter form (§4.1) which solves this automatically. |
| **CA-10** | Block-matrix spectral radius $\rho(\mathbf G)\le 1$ is not sufficient for full-discrete RK stability. | Same RK-CFL argument as §5.3; L-stable implicit time integrators (backward Euler, SDIRK) eliminate the constraint at implicit-solve cost. |

---

## 7. Relation to existing project artefacts

- **SP-A ([FCCD](SP-A_face_centered_upwind_ccd.md))**: orthogonal — face-upwind truncation cancellation, not dissipation. Addresses BF-residual (H-01) rather than linear stability.
- **WIKI-T-002 (DCCD filter)**: the production instantiation. SP-G derives the small-$k$ limit that T-002 then refines into a full spectral filter with adaptive control.
- **WIKI-T-013 (DCCD vs WENO5)**: provides empirical verification of the design choices laid out here; SP-G is the theoretical companion.
- **WIKI-T-046 (FCCD wiki)**: summarises SP-A; independent of this entry.

---

## 8. Conclusion

The three exercises considered — (i) Von Neumann stability of upwind, (ii) upwind-biased Chu & Fan CCD hybrid, (iii) semi-discrete Fourier stability of the hybrid — are **mathematically correct within their stated scope** and form a coherent chain from first-order upwind to the production DCCD scheme. The derivation is pedagogically illuminating: the **Laplacian dissipation of upwind** (revealed by modified-equation expansion) is transplanted onto the **high-order second derivative of CCD** (rather than a low-order FD) to unify stability and spectral resolution. Six counterarguments (CA-1..6) scope the result to (a) interior rows, (b) periodic / GKS-closed BC, (c) modest $\varepsilon$ regime, (d) RK-stability-compatible $\Delta t$, (e) linear / frozen-coefficient settings. All six are addressed elsewhere in the project, either by the production filter form (T-002) or by the orthogonal FCCD face-upwind remedy (SP-A).

No new code or experiment is generated by this short paper; its role is to close the **"why this shape"** documentation gap between the pedagogy of classical upwind analysis and the production DCCD / FCCD stack.

---

## 9. Two-point Hermite foundation (corrected coefficients)

An appendix section added to document the **2-point compact relations and 5th-order Hermite midpoint reconstruction** used for wall / upwind closure of the interior Chu&Fan CCD stack. Coefficients are verified against monomial exact-reproduction; anti-pattern coefficients that circulate in the literature are catalogued.

### 9.1 Unique 4th-order 2-point compact relation

With $\{u_{i-1}, u_i, u'_{i-1}, u'_i, u''_{i-1}, u''_i\}$ given, there is **one** independent 4th-order identity:

$$
u'_i + u'_{i-1} - \frac{h}{6}(u''_i - u''_{i-1}) = \frac{2}{h}(u_i - u_{i-1}) + \mathcal O(h^4).
$$

Any purported "Eq-II" in the same 2-point data (e.g., $\tfrac{h}{12}(u''_i\pm u''_{i-1}) = \tfrac{1}{h}(u_i-u_{i-1}) - \tfrac{1}{2}(u'_i+u'_{i-1})$) is a rearrangement, not an independent constraint — the 5-degree Hermite polynomial has 0 residual DoF once all 6 values are fixed.

### 9.2 Fifth-order Hermite midpoint reconstruction

Inverting the 6×6 Hermite interpolation matrix in (even, odd) block form gives:

$$
\begin{aligned}
u_{i-1/2} &= \tfrac{1}{2}(u_i + u_{i-1}) - \tfrac{5h}{32}(u'_i - u'_{i-1}) + \tfrac{h^2}{64}(u''_i + u''_{i-1}), \\[2pt]
u'_{i-1/2} &= \tfrac{15}{8h}(u_i - u_{i-1}) - \tfrac{7}{16}(u'_i + u'_{i-1}) + \tfrac{h}{32}(u''_i - u''_{i-1}), \\[2pt]
u''_{i-1/2} &= \tfrac{3}{2h}(u'_i - u'_{i-1}) - \tfrac{1}{4}(u''_i + u''_{i-1}).
\end{aligned}
$$

**Verified**: exact on $u\in\{1,x,\ldots,x^5\}$; leading residual $\mathcal O(h^6)$ for smooth $u$. (Representative monomial checks: $u=x^2\Rightarrow u_{i-1/2}=h^2/4$ exact; $u=x^5\Rightarrow u'_{i-1/2}=5(h/2)^4$ exact.)

### 9.3 Flux handoff to Riemann solvers

The midpoint state $(u^L, u^R)$ obtained from §9.2 with upwind-biased neighbour pairs feeds naturally into HLLC / Roe / LF Riemann solvers:

```
node CCD (T-001)  →  face state (§9.2)  →  Riemann solver  →  face flux F_{i-1/2}
                     [5-th order]         [upwind robust]     [conservative FV]
```

The pathway is orthogonal to the PDE-level dissipation variant (§4) and the operator-level bias variant (§4.2): CCD accuracy is preserved at nodes, upwind character is introduced only in the face-state selection, and the resulting stencil remains compact (3 cells per face).

### 9.4 Anti-pattern catalogue

| Quantity | Miswritten (common error) | Correct | Degraded order |
|----------|--------------------------|---------|----------------|
| 2-pt relation $\lambda h(u''_i-u''_{i-1})$ coefficient | $+1/10$ | $-1/6$ | $\mathcal O(h^4)\to\mathcal O(h^2)$ |
| $u_{i-1/2}$ first-derivative term | $-h/8$ | $-5h/32$ | $\mathcal O(h^6)\to\mathcal O(h^2)$ |
| $u_{i-1/2}$ second-derivative term | $+h^2/48$ | $+h^2/64$ | incompatible with $-h/8$ |
| $u'_{i-1/2}$ values term | $+3/(2h)$ | $+15/(8h)$ | $\mathcal O(h^6)\to\mathcal O(h^2)$ |
| $u''_{i-1/2}$ "$\tfrac{h}{4}(u''_i+u''_{i-1})$" | dimensionally ill-posed | $\tfrac{3}{2h}(u'_i-u'_{i-1})-\tfrac14(u''_i+u''_{i-1})$ | — |

These are the exact coefficient bugs uncovered during SP-G v1.1 review (2026-04-21); future re-derivations should monomial-verify before use.

---

## References

- Chu, P.C. & Fan, C. (1998). "A three-point combined compact difference scheme." *J. Comput. Phys.* **140**, 370–399.
- LeVeque, R.J. (2002). *Finite Volume Methods for Hyperbolic Problems*. Cambridge University Press. Chapters 8–9.
- Shu, C.-W. & Osher, S. (1988). "Efficient implementation of essentially non-oscillatory shock-capturing schemes." *J. Comput. Phys.* **77**, 439–471.
- Gustafsson, B., Kreiss, H.-O., Sundström, A. (1972). "Stability theory of difference approximations for mixed initial boundary value problems II." *Math. Comp.* **26**, 649–686.
- Lele, S.K. (1992). "Compact finite difference schemes with spectral-like resolution." *J. Comput. Phys.* **103**, 16–42.
- Sengupta, T.K. & Bhumkar, Y.G. (2020). *High Accuracy Computing Methods: Fluid Flows and Wave Phenomena*. Cambridge University Press. (OUCS3 family of upwind compact schemes.)
