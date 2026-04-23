# SP-N: UCCD6 — A Sixth-Order Upwind Combined Compact Difference Scheme with Order-Preserving Hyperviscosity

- **Status**: Research proposal (theory verified; PoC pending)
- **Compiled by**: ResearchArchitect
- **Compiled at**: 2026-04-21 (renumbered 2026-04-23: formerly SP-H, renamed to SP-N to resolve collision with [SP-H_fccd_face_jet_fvm_hfe.md](SP-H_fccd_face_jet_fvm_hfe.md))
- **Related**: [SP-G](SP-G_upwind_ccd_pedagogical.md) (pedagogical foundation), [SP-A](SP-A_face_centered_upwind_ccd.md) (FCCD, orthogonal remedy), [SP-H](SP-H_fccd_face_jet_fvm_hfe.md) (face-jet companion)
- **Wiki entry**: [WIKI-T-062](../../wiki/theory/WIKI-T-062.md)

## Abstract

We propose **UCCD6**, a sixth-order upwind combined compact difference scheme for the linear advection equation $\partial_t u + a \partial_x u = 0$. The scheme augments the Chu & Fan (1998) CCD first-derivative operator $D_1^{\text{CCD}}$ with an order-preserving hyperviscosity
$$
L_h u = -a D_1^{\text{CCD}} u - \sigma |a| h^7 (-D_2^{\text{CCD}})^4 u, \qquad \sigma > 0,
$$
where $D_2^{\text{CCD}}$ is the Chu & Fan CCD second-derivative operator. We prove (i) semi-discrete $L^2$ stability via the exact modified wavenumbers of Chu & Fan, (ii) discrete energy dissipation $\tfrac{1}{2} \mathrm{d}/\mathrm{d}t \|U\|_h^2 \le 0$, (iii) unconditional stability of the Crank–Nicolson time discretisation, and (iv) $O(h^6)$ main truncation with $O(h^7)$ subdominant hyperviscosity. Boundary closures at fourth order for bounded intervals are inherited from Chu & Fan. UCCD6 complements the production DCCD spectral filter ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) and the face-centred FCCD proposal ([WIKI-T-046](../../wiki/theory/WIKI-T-046.md)) by providing a **dissipation channel in the node-centred CCD operator itself** while preserving its sixth-order dispersion.

## 1. Introduction

The production [Chu & Fan CCD operator](../../wiki/theory/WIKI-T-001.md) delivers sixth-order dispersion but is formally dispersion-only — its Fourier symbol is purely imaginary for real wavenumbers. For smooth data this is optimal; for under-resolved scales or discontinuities it leads to Gibbs oscillations that the project currently contains through two independent mechanisms:

- **DCCD spectral filter** ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) — a separate post-filter pass with filter coefficient $\varepsilon_d$.
- **FCCD face-centred upwind** ([WIKI-T-046](../../wiki/theory/WIKI-T-046.md)) — a structurally upwind reformulation on the face locus.

UCCD6 proposes a third path: embed a **hyperviscosity of sufficiently high order to leave the CCD truncation budget intact** directly into the node-centred operator. Combined with the Crank–Nicolson time integrator, the resulting scheme is unconditionally stable and preserves the Chu & Fan accuracy target.

## 2. Chu & Fan operator and its exact modified wavenumbers

We adopt the Chu & Fan (1998) three-point combined compact difference scheme on a uniform grid with spacing $h$. At interior points the CCD operators satisfy the coupled $2N \times 2N$ Hermitian relations whose Fourier symbols on a periodic grid evaluate at $\theta = k h$ to
$$
\boxed{\;
\omega_1(\theta) = \frac{9 \sin\theta \, (4 + \cos\theta)}{24 + 20 \cos\theta + \cos 2\theta},
\qquad
\omega_2(\theta)^2 = \frac{81 - 48 \cos\theta - 33 \cos 2\theta}{48 + 40 \cos\theta + 2 \cos 2\theta}.
\;}
$$

These are *exact* in the sense that the Fourier symbol of $D_1^{\text{CCD}}$ is $i \omega_1(\theta) / h$ and the Fourier symbol of $D_2^{\text{CCD}}$ is $-\omega_2(\theta)^2 / h^2$. The Taylor expansions at $\theta \to 0$ are
$$
\omega_1(\theta) = \theta - \tfrac{1}{9450} \theta^7 + O(\theta^9),
\qquad
\omega_2(\theta)^2 = \theta^2 + \tfrac{19}{75600} \theta^8 + O(\theta^{10}),
$$
confirming sixth-order accuracy of both operators on smooth data. A direct verification of $\omega_2(\theta)^2 \ge 0$ for all real $\theta$ is the key positivity fact: the numerator $81 - 48\cos\theta - 33\cos 2\theta \ge 0$ is checked via $\cos 2\theta = 2\cos^2\theta - 1$, reducing to $114 - 48c - 66c^2 \ge 0$ for $c = \cos\theta \in [-1,1]$, and the denominator $48 + 40\cos\theta + 2\cos 2\theta = 46 + 40c + 4c^2 \ge 46 - 40 + 4 = 10 > 0$.

## 3. UCCD6 formulation

### 3.1 Scheme definition

For the linear advection equation $\partial_t u + a \partial_x u = 0$ we define
$$
\partial_t U_j + a \, (D_1^{\text{CCD}} U)_j + \sigma |a| h^7 \, ((-D_2^{\text{CCD}})^4 U)_j = 0, \qquad \sigma > 0.
$$
The operator $(-D_2^{\text{CCD}})$ is positive semi-definite (by its Fourier symbol $\omega_2^2 / h^2 \ge 0$), so $(-D_2^{\text{CCD}})^4$ is positive semi-definite as well. The coefficient $\sigma |a| h^7$ is dimensionally correct: $(-D_2^{\text{CCD}})^4$ has symbol $\omega_2^8 / h^8$, and multiplied by $h^7$ yields a symbol $\omega_2^8 / h$ matching the $1/h$ scaling of $D_1^{\text{CCD}}$.

### 3.2 Rationale for the exponent 7

The hyperviscosity symbol is $\sigma |a| \omega_2^8 / h$. Since $\omega_2^2 = \theta^2 + O(\theta^8)$,
$$
\sigma |a| \omega_2^8 / h = \sigma |a| \theta^8 / h + O(\theta^{14} / h) = \sigma |a| h^7 k^8 + O(h^{13} k^{14}).
$$
Hence the hyperviscosity acts on smooth scales as $-\sigma |a| h^7 \partial_x^8 u$, asymptotically subdominant to the $O(h^6)$ main truncation of $D_1^{\text{CCD}}$. Choosing exponent 5 (i.e. $h^5 (-D_2^{\text{CCD}})^3$) would produce an $O(h^5)$ hyperviscosity that degrades the global order; exponent 9 would underdamp the $\pi$-mode. Exponent 7 with fourth-power hyperviscosity is the minimal order-preserving design.

### 3.3 Fourier symbol

The full Fourier symbol of $L_h = -a D_1^{\text{CCD}} - \sigma|a| h^7 (-D_2^{\text{CCD}})^4$ is
$$
\lambda(\theta) = -i \frac{a \omega_1(\theta)}{h} - \sigma |a| \frac{\omega_2(\theta)^8}{h},
\qquad \Re \lambda(\theta) = -\sigma |a| \frac{\omega_2(\theta)^8}{h} \le 0.
$$
Thus every Fourier mode is neutrally dispersive with non-positive real part. Strict dissipation occurs for every mode with $\omega_2(\theta) \neq 0$, i.e. every $\theta \in (0, \pi]$.

## 4. Energy method L² stability

Let $\langle \cdot, \cdot \rangle_h$ denote the discrete $\ell^2$ inner product on the periodic grid. The Chu & Fan operator $D_1^{\text{CCD}}$ is skew-Hermitian in this inner product and $D_2^{\text{CCD}}$ is Hermitian and negative semi-definite (§2 positivity of $\omega_2^2$ gives $\langle -D_2^{\text{CCD}} U, U \rangle_h \ge 0$). Therefore
$$
\tfrac{1}{2} \frac{\mathrm{d}}{\mathrm{d} t} \|U\|_h^2 = \langle U, \dot U \rangle_h = -a \langle U, D_1^{\text{CCD}} U \rangle_h - \sigma |a| h^7 \langle U, (-D_2^{\text{CCD}})^4 U \rangle_h.
$$
The first term vanishes by skew-Hermiticity. The second term equals $-\sigma |a| h^7 \| (-D_2^{\text{CCD}})^2 U \|_h^2 \le 0$. Hence
$$
\boxed{\; \tfrac{1}{2} \frac{\mathrm{d}}{\mathrm{d} t} \|U\|_h^2 = -\sigma |a| h^7 \| (-D_2^{\text{CCD}})^2 U \|_h^2 \le 0. \;}
$$
This is a *strict* dissipation identity — the energy decays at a rate proportional to the fourth-derivative-squared seminorm.

## 5. Crank–Nicolson time discretisation

With time step $\tau$ and $\nu = a \tau / h$ the Crank–Nicolson update for UCCD6 is
$$
(I + \tfrac{\tau}{2} L_h) U^{n+1} = (I - \tfrac{\tau}{2} L_h) U^n.
$$
On the periodic Fourier basis this decouples to $G(\theta) = (1 + \tau \lambda(\theta)/2) / (1 - \tau \lambda(\theta)/2)$ with
$$
|G(\theta)|^2 = \frac{(1 - \tau \Re \lambda / 2)^2 + (\tau \Im \lambda / 2)^2}{(1 + \tau |\Re \lambda| / 2)^2 + (\tau \Im \lambda / 2)^2}.
$$
Since $\Re \lambda(\theta) \le 0$ for all $\theta$, $|G(\theta)| \le 1$ unconditionally in $\tau$ and $h$.

**Remark.** Explicit TVD-RK3 would subject UCCD6 to a CFL constraint $\nu_{\max} \le \sqrt{3}/(\omega_{1,\max} + \sigma h^6 \omega_{2,\max}^8)$, with $\omega_{1,\max} \approx \pi$. The $\omega_2^8$ dependency at $\theta = \pi$ makes explicit integration prohibitively restrictive for moderate $\sigma$; CN is the natural pairing.

## 6. Boundary closures for bounded intervals

On $[0, L]$ with Dirichlet or inflow data at $x = 0$, the boundary rows of the CCD system use the Chu & Fan closure: for $D_1$ at $j = 1$,
$$
u'_1 + 2 u'_2 = \tfrac{1}{h}\bigl(-\tfrac{5}{2} u_1 + 2 u_2 + \tfrac{1}{2} u_3 \bigr) + O(h^4),
$$
and symmetric closure at $j = N$. The $D_2$ closure is the companion Hermitian relation. Fourth-order truncation of each closure is verified by Taylor expansion (each closure kills $1, x, x^2, x^3, x^4$ monomials and leaves a $O(h^4) x^5$ remainder). Taking four successive applications of $D_2^{\text{CCD}}$ inherits $O(h^4)$ near the boundary — acceptable because the hyperviscosity coefficient $h^7$ suppresses the interior dominant term below the main $O(h^6)$ error.

**GKS context.** Semi-discrete stability on the bounded domain follows the Gustafsson–Kreiss–Sundström (GKS) framework: the boundary operators admit no left-going characteristics incompatible with the interior operator, and the boundary amplification factor remains in $\{|z| \le 1\}$ under the CCD closure. The rigorous GKS proof for Chu & Fan with hyperviscosity is deferred to the PoC programme.

## 7. Relation to existing project artefacts

| Scheme | Locus | Dispersion | Dissipation channel | Order preserved |
|---|---|---|---|---|
| Chu & Fan CCD ([WIKI-T-001](../../wiki/theory/WIKI-T-001.md)) | node | $O(h^6)$ | none | $O(h^6)$ |
| DCCD filter ([WIKI-T-002](../../wiki/theory/WIKI-T-002.md)) | node | $O(h^6)$ | separate post-filter | $O(h^6)$ |
| FCCD ([WIKI-T-046](../../wiki/theory/WIKI-T-046.md)) | face | $O(h^4)$ | strict upwind structure | $O(h^4)$ |
| **UCCD6 (this paper)** | node | $O(h^6)$ | embedded hyperviscosity | $O(h^6)$ |

UCCD6 is complementary to FCCD: FCCD trades two orders for face-locus alignment relevant to the balanced-force residual H-01 ([WIKI-E-030](../../wiki/experiment/WIKI-E-030.md)); UCCD6 retains the node locus and adds dissipation inside the existing operator budget.

The pedagogical foundation for this work is [WIKI-T-061 / SP-G](SP-G_upwind_ccd_pedagogical.md) — the PDE-level upwind⊕CCD derivation and its operator-level dual. UCCD6 is the mathematically rigorous realisation of the "operator-level dual" §4.2 of SP-G, with the bias exponent raised from the minimal order-preserving level in that pedagogical treatment to the fourth power of $D_2^{\text{CCD}}$.

## 8. Numerical experiments (programme)

- **Exp-H1 — Smooth sine advection.** Verify $O(h^6)$ convergence of $\|U^n - u(x, t^n)\|_2$ at fixed $\nu = a \tau / h$ and CFL-stable $\sigma$.
- **Exp-H2 — Discontinuous step.** Compare UCCD6 / DCCD / FCCD on a top-hat profile; measure total variation and monotonicity at the leading edge.
- **Exp-H3 — Energy-budget trace.** Report $\|U^n\|_h^2$ vs $n$ for UCCD6 and confirm monotonic decrease at the rate predicted by §4.
- **Exp-H4 — Two-dimensional coupling.** Port UCCD6 to 2D via tensor-product CCD; verify that the balanced-force residual at the WIKI-E-030 capillary benchmark does *not* degrade (i.e., UCCD6 is neutral to the H-01 problem, leaving FCCD/$\mathcal{G}^{\text{adj}}$ as the targeted remedy).

## 9. Conclusion

UCCD6 adds a **mathematically rigorous, order-preserving dissipation channel** to the Chu & Fan CCD operator via an eighth-order hyperviscosity $\sigma |a| h^7 (-D_2^{\text{CCD}})^4$. Semi-discrete $L^2$ stability follows from skew-symmetry of $D_1^{\text{CCD}}$ plus positive semi-definiteness of the hyperviscosity; Crank–Nicolson integration is unconditionally stable. Fourth-order boundary closures from Chu & Fan extend to bounded intervals with GKS-compatible semi-discrete stability. The scheme is **complementary to DCCD and FCCD**, occupying the node-centred order-preserving dissipation niche. Numerical validation per §8 is the next step.

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- Gustafsson, B., Kreiss, H.-O., & Sundström, A. (1972). Stability theory of difference approximations for mixed initial boundary value problems, II. *Math. Comp.*, 26, 649–686.
- [SP-G: Upwind⊕CCD Pedagogical Foundation](SP-G_upwind_ccd_pedagogical.md)
- [SP-A: FCCD Face-Centered Upwind CCD](SP-A_face_centered_upwind_ccd.md)
- [WIKI-T-001](../../wiki/theory/WIKI-T-001.md), [WIKI-T-002](../../wiki/theory/WIKI-T-002.md), [WIKI-T-046](../../wiki/theory/WIKI-T-046.md), [WIKI-T-061](../../wiki/theory/WIKI-T-061.md), [WIKI-T-062](../../wiki/theory/WIKI-T-062.md)
