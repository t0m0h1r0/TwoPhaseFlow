---
ref_id: WIKI-T-050
title: "FCCD Non-Uniform Generalization: Cancellation Coefficients μ(r), λ(r)"
domain: theory
status: PROPOSED  # Theory derived; PoC pending (paired with WIKI-T-046)
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-A_face_centered_upwind_ccd.md
    description: SP-A §6.3(1) caveat — non-uniform generalization of λ
depends_on:
  - "[[WIKI-T-046]]: FCCD uniform-grid definition (λ = 1/24)"
  - "[[WIKI-T-044]]: G^adj face-average gradient — non-uniform face metric J_f"
  - "[[WIKI-T-039]]: ξ-Space CCD Metric Limitation — alternative ξ-coordinate route"
consumers:
  - domain: theory
    description: WIKI-T-051 (face-locus wall BC requires this metric framework)
  - domain: theory
    description: WIKI-T-053 (executable FCCD equations via CCD second-derivative closure)
  - domain: cross-domain
    description: WIKI-X-018 (R-1 FCCD candidate must satisfy non-uniform deployment)
  - domain: future-impl
    description: FCCD PoC §3 (stretched-grid convergence verification)
tags: [ccd, fccd, non_uniform, taylor_expansion, h01_remediation, cancellation_coefficient, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# FCCD Non-Uniform Generalization: Cancellation Coefficients μ(r), λ(r)

## Why this entry exists

[WIKI-T-046](WIKI-T-046.md) defined the Face-Centered Combined Compact Difference (FCCD) operator on a uniform grid with the single cancellation coefficient $\lambda = 1/24$. SP-A §6.3(1) flagged the non-uniform generalisation as an open caveat: when the face $f = i-1/2$ is no longer the geometric midpoint of the node pair $(x_{i-1}, x_i)$, the Taylor expansion picks up an additional $u''_f$ term and the third-derivative coefficient becomes a function of the local spacing ratio. This entry resolves the caveat by re-deriving the operator in the non-uniform setting.

## Local geometry

Let the face $f$ lie at position $x_f$ between nodes $x_{i-1}$ and $x_i$. Define

$$
h_L \;:=\; x_f - x_{i-1}, \qquad h_R \;:=\; x_i - x_f, \qquad H \;:=\; h_L + h_R \;=\; x_i - x_{i-1}.
$$

The non-dimensional face-position parameter is

$$
\theta \;:=\; \frac{h_R}{H} \in (0, 1), \qquad 1 - \theta \;=\; \frac{h_L}{H},
$$

with $\theta = 1/2$ recovering the symmetric (uniform-face) case. The companion ratio used below is $r := h_R/h_L = \theta/(1-\theta)$.

## Taylor expansion at the face

Expanding $u_{i-1}$ and $u_i$ about $x_f$,

$$
u_{i-1} \;=\; u_f - h_L u'_f + \tfrac{h_L^2}{2} u''_f - \tfrac{h_L^3}{6} u'''_f + \tfrac{h_L^4}{24} u''''_f - \cdots,
$$
$$
u_i \;=\; u_f + h_R u'_f + \tfrac{h_R^2}{2} u''_f + \tfrac{h_R^3}{6} u'''_f + \tfrac{h_R^4}{24} u''''_f + \cdots
$$

Subtracting and dividing by $H$:

$$
\frac{u_i - u_{i-1}}{H} \;=\; u'_f + \frac{h_R - h_L}{2}\, u''_f + \frac{h_R^3 + h_L^3}{6 H}\, u'''_f + \frac{h_R^4 - h_L^4}{24 H}\, u''''_f + \mathcal{O}(H^4).
$$

In the $\theta$-parametrisation:

$$
\boxed{\;
\frac{u_i - u_{i-1}}{H} \;=\; u'_f \;+\; \underbrace{H\!\left(\theta - \tfrac{1}{2}\right)}_{\mu(\theta)\,H} u''_f \;+\; \underbrace{\frac{H^2}{6}\bigl(1 - 3\theta(1-\theta)\bigr)}_{\lambda(\theta)\,H^2} u'''_f \;+\; \underbrace{\frac{H^3}{24}\bigl(\theta^2+(1-\theta)^2\bigr)\bigl(2\theta - 1\bigr)}_{\nu(\theta)\,H^3} u''''_f \;+\; \mathcal{O}(H^4).
\;}
$$

## Cancellation coefficients

The non-uniform FCCD operator is defined as

$$
D^{\mathrm{FCCD},\,\mathrm{nu}} u_f \;:=\; \frac{u_i - u_{i-1}}{H} \;-\; \mu(\theta)\, H\, \tilde u''_f \;-\; \lambda(\theta)\, H^2\, \tilde u'''_f,
$$

where $\tilde u''_f$ and $\tilde u'''_f$ are face-side estimates obtained from the Chu–Fan combined relations (see §"Combined-relation closure" below). Setting

$$
\boxed{\;
\mu(\theta) \;=\; \theta - \tfrac{1}{2},
\qquad
\lambda(\theta) \;=\; \tfrac{1 - 3\theta(1-\theta)}{6},
\;}
$$

cancels the leading $u''_f$ and $u'''_f$ truncation terms exactly, leaving

$$
D^{\mathrm{FCCD},\,\mathrm{nu}} u_f \;=\; u'_f \;+\; \nu(\theta)\, H^3\, u''''_f \;+\; \mathcal{O}(H^4).
$$

### Reduction to the uniform case

For $\theta = 1/2$ ($r = 1$, face is the geometric midpoint):

| Coefficient | $\theta = 1/2$ value | Comment |
|---|---|---|
| $\mu(1/2)$ | $0$ | no $u''_f$ correction needed (Chu–Fan symmetry) |
| $\lambda(1/2)$ | $\tfrac{1-3/4}{6} = \tfrac{1}{24}$ | recovers WIKI-T-046 result ✓ |
| $\nu(1/2)$ | $\tfrac{1}{24}\bigl(\tfrac{1}{4}+\tfrac{1}{4}\bigr)\cdot 0 = 0$ | $u''''_f$ coefficient vanishes by symmetry |

The vanishing of $\nu(1/2)$ on the uniform grid is the reason WIKI-T-046 reports $\mathcal{O}(H^4)$ accuracy; the symmetric face cancels the next-order term automatically.

### In terms of the spacing ratio $r = h_R / h_L$

$$
\mu(r) \;=\; \frac{r-1}{2(r+1)}, \qquad
\lambda(r) \;=\; \frac{1 - r + r^2}{6(1+r)^2}, \qquad
\nu(r) \;=\; \frac{(r-1)\bigl(1 + r^2\bigr)}{24(1+r)^3}.
$$

| $r$ | $\mu$ | $\lambda$ | $\nu$ | Comment |
|---|---|---|---|---|
| $1$ | $0$ | $1/24 \approx 0.0417$ | $0$ | uniform-face limit ✓ |
| $1.5$ | $0.10$ | $0.0467$ | $0.00541$ | mildly stretched |
| $2$ | $0.167$ | $0.0556$ | $0.0116$ | $h_R = 2 h_L$ |
| $4$ | $0.30$ | $0.105$ | $0.0531$ | strongly stretched |

The cancellation coefficients remain bounded for all $r > 0$; no divergence on stretched grids.

## Order of accuracy

| Grid | Cancellations active | Leading remainder |
|---|---|---|
| uniform face ($\theta = 1/2$) | $\lambda(1/2) = 1/24$ only ($\mu, \nu$ vanish) | $\mathcal{O}(H^4)$ |
| non-uniform face, two-coefficient cancellation | $\mu(\theta) + \lambda(\theta)$ | $\mathcal{O}(H^3)$ via $\nu(\theta) H^3 u''''_f$ |
| non-uniform face, three-coefficient cancellation | $\mu + \lambda + \nu$ (also subtract $\nu(\theta) H^3 \tilde u''''_f$) | $\mathcal{O}(H^4)$ |

**Practical note.** Two-coefficient cancellation suffices for the H-01 application: the existing CSF model error floor is $\mathcal{O}(H^2)$ ([WIKI-T-009](WIKI-T-009.md), [WIKI-T-017](WIKI-T-017.md)), and the BF residual reduction from current mixed-metric $\mathcal{O}(H^2)\cdot 0.77$ ([WIKI-T-044](WIKI-T-044.md) Table 2) to FCCD-unified $\mathcal{O}(H^3)$ is already a ≥ 1-order improvement. The third-order cancellation $\nu(\theta)$ may be skipped in the first PoC and added later if BF residuals on extreme stretching ($r \gg 4$) are unsatisfactory.

## Combined-relation closure

The FCCD operator above presupposes face-side estimates $\tilde u''_f$ and $\tilde u'''_f$. In Chu–Fan node-centred CCD these are coupled via a $2N \times 2N$ block-tridiagonal system. For face-centred FCCD, two implementation routes are available:

**PoC closure selected by [WIKI-T-053](WIKI-T-053.md).** The first implementation should not introduce a new $u'''$ unknown. Instead, solve the existing CCD system for the nodal second derivative $q_i=(D_{\mathrm{CCD}}^{(2)}u)_i$, then use

$$
\tilde u''_f = \theta q_{i-1} + (1-\theta)q_i,
\qquad
\tilde u'''_f = \frac{q_i-q_{i-1}}{H}.
$$

Substitution gives the executable operator

$$
D^{\mathrm{FCCD,nu}}u_f
= \frac{u_i-u_{i-1}}{H}
  - \mu(\theta)H\left[\theta q_{i-1}+(1-\theta)q_i\right]
  - \lambda(\theta)H(q_i-q_{i-1}).
$$

1. **Inherit from node-CCD.** Solve the existing CCD system at nodes, then interpolate $u''_n$ and $u'''_n$ to the face $x_f$ using a second-order one-sided or weighted average. This is the simplest route and preserves backward compatibility with [`CCDSolver`](../../../src/twophase/ccd/ccd_solver.py).

2. **Native face-CCD.** Re-derive the combined relations directly at faces, producing a $2M \times 2M$ system over the $M$ interior faces. This eliminates the node→face interpolation error but requires a new solver class. Recommended for production after the first PoC validates the cancellation algebra.

The non-uniform algebra above (μ, λ, ν) is **independent** of which closure is chosen — it characterises the truncation cancellation of the difference operator itself.

## Verification programme (pure-theory)

1. **Symbolic verification.** Substitute the boxed Taylor expansion into a symbolic algebra system (e.g. SymPy) and verify that
   $D^{\mathrm{FCCD},\,\mathrm{nu}} u_f - u'_f = \nu(\theta) H^3 u''''_f + \mathcal{O}(H^4)$
   for arbitrary $\theta$.
2. **Limit check.** Verify $\mu, \lambda, \nu$ recover the WIKI-T-046 values at $\theta = 1/2$.
3. **Monotonicity.** $\lambda(\theta)$ has a minimum at $\theta = 1/2$ and grows towards both endpoints — ensures no anomalous cancellation failure on either-sided stretching.

## Caveats and open issues

- **Multi-axis combination on 2-D non-uniform meshes.** When both axes are simultaneously stretched, the cancellation must be applied per-axis with the local $\theta_x$ and $\theta_y$. Whether cross-derivative truncation terms ($u_{xy}$, $u_{xxy}$) require additional cancellation is an open algebra problem.
- **Cell-by-cell coefficient evaluation cost.** Unlike the uniform-grid case (single global $\lambda$), every face carries its own $\mu, \lambda, \nu$ triple. Pre-computation of these into a face-indexed array is mandatory; per-step recomputation would be prohibitive.
- **Wall BC on face-locus operator.** Resolved separately in [WIKI-T-051](WIKI-T-051.md).
- **Pseudotime-PPE compatibility.** The current `ns_pipeline` uses a direct sparse PPE solver, not the pseudotime defect-correction iteration of WIKI-T-016. The SP-A §6.3(3) caveat is therefore not binding for current code; see WIKI-T-046 §"後続展開" for the cross-link.

## Relation to existing project mechanisms

- **vs. [WIKI-T-044](WIKI-T-044.md) G^adj.** G^adj uses the face metric $J_f = 1/d_f$ at $\mathcal{O}(H^2)$ accuracy and is consistent with the FVM Laplacian (projection consistency). FCCD non-uniform is a higher-order ($\mathcal{O}(H^3)$ or $\mathcal{O}(H^4)$) face operator that subsumes G^adj as a special case (see §"Reduction to G^adj" below).
- **vs. [WIKI-T-039](WIKI-T-039.md) ξ-CCD.** The ξ-coordinate approach maps the non-uniform physical grid to a uniform computational grid and applies node-centred CCD there. FCCD non-uniform stays in the physical-coordinate framework but pays the per-face coefficient cost. The two are complementary: ξ-CCD is preferable when the same metric is used everywhere; FCCD is preferable when only the corrector face gradient needs upgrading.

### Reduction to G^adj

Drop both cancellations ($\mu \equiv \lambda \equiv 0$):

$$
D^{(0)} u_f \;=\; \frac{u_i - u_{i-1}}{H} \;=\; \frac{u_i - u_{i-1}}{d_f^{(i-1)}},
$$

which is exactly the per-face one-sided difference used in `_fvm_pressure_grad` ([ns_pipeline.py L381–395](../../../src/twophase/simulation/ns_pipeline.py#L381)). The current G^adj is therefore the zeroth-order projection of FCCD onto the face locus; the cancellation cascade $\mu \to \lambda \to \nu$ is the order-by-order improvement.

This observation underwrites the immediate-deployment proposal R-1.5 in [WIKI-T-052](WIKI-T-052.md): even without the cancellation terms, applying $D^{(0)}$ uniformly to both $\nabla p$ and $\nabla \psi$ already produces a balanced-force-consistent operator pair — the metric mismatch documented in [WIKI-T-045](WIKI-T-045.md) is eliminated regardless of order.

## References

- Chu, P. C., & Fan, C. (1998). A three-point combined compact difference scheme. *J. Comp. Phys.*, 140(2), 370–399.
- [SP-A full draft](../../memo/short_paper/SP-A_face_centered_upwind_ccd.md) §6.3(1)
- [WIKI-T-046](WIKI-T-046.md), [WIKI-T-044](WIKI-T-044.md), [WIKI-T-039](WIKI-T-039.md), [WIKI-T-051](WIKI-T-051.md), [WIKI-T-052](WIKI-T-052.md), [WIKI-X-018](../cross-domain/WIKI-X-018.md)
