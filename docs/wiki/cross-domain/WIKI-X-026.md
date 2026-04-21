---
ref_id: WIKI-X-026
title: "Stiffness-Based Time Integration Policy for Two-Phase UCCD6-NS (When Each Term Forces Implicit Treatment)"
domain: cross-domain
status: PROPOSED  # Diagnostic framework; per-operator Δt measurement pending
superseded_by: null
sources:
  - description: Internal research memo on stiffness diagnosis for two-phase NS time integration (2026-04-22)
depends_on:
  - "[[WIKI-X-023]]: UCCD6 Integration Design for Incompressible NS"
  - "[[WIKI-X-024]]: Balanced-Force Design for Two-Phase UCCD6-NS"
  - "[[WIKI-X-025]]: Time Integration Design for Two-Phase UCCD6-NS"
  - "[[WIKI-X-007]]: CFL Constraint Hierarchy and Stability Budget"
  - "[[WIKI-T-014]]: Capillary CFL Constraint"
consumers:
  - domain: experiment
    description: "Per-operator Δt measurement on ch13 (N=128 and N=256 non-uniform α=1.5)"
  - domain: future-impl
    description: "Matrix-free Krylov + AMG for PPE and CN-Helmholtz solvers (LU infeasible in 3D)"
  - domain: theory
    description: "Diagnostic link between stiffness source and observed BF-residual / κ chaos"
tags: [stiffness, time_integration, implicit_explicit, cfl, capillary, viscous, ppe, krylov, multigrid, diagnostic]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Stiffness-Based Time Integration Policy

## Thesis

> **Whether a term needs implicit time integration is determined entirely by
> the time-scale it imposes.  The smallest time-scale dominates. In the
> project's two-phase UCCD6-NS stack, the ranking is:**
>
> $$\Delta t_\sigma \;\lesssim\; \Delta t_\nu \;\lesssim\; \Delta t_{\text{adv}}$$
>
> **so capillary and viscous terms force implicit/semi-implicit treatment
> while the UCCD6 advection can remain explicit.**

This note supplies the *operator-wise diagnostic* that [WIKI-X-025](WIKI-X-025.md) uses implicitly.

## 1. Time-scale table

| Term | Scale | Source |
|---|---|---|
| advection | $\Delta t_{\text{adv}} \sim h / |\mathbf{u}|$ | hyperbolic CFL |
| viscosity | $\Delta t_\nu \sim h^2 / \nu$ | parabolic CFL |
| surface tension (stability) | $\Delta t_\sigma^{\text{BKZ}} \sim \sqrt{\rho h^3 / \sigma}$ | Brackbill–Kothe–Zemach (1992) |
| surface tension (resolution) | $\Delta t_{\text{cap}} \sim C_{\text{wave}}\,\Delta t_\sigma^{\text{BKZ}}$ | Denner–van Wachem (2015) — see [WIKI-X-025 §1](WIKI-X-025.md#1-why-capillary-δt-is-a-wave-resolution-constraint) |
| pressure | — (elliptic) | incompressibility constraint |

**Scaling verdict.** On refined grids $h \to 0$:

- advective bound decays as $h^{+1}$,
- viscous bound decays as $h^{+2}$,
- capillary bound decays as $h^{+3/2}$.

Viscous decay is the fastest, but in typical ch13 regimes (water–air, $\nu \sim 10^{-6}$, $\sigma \sim 10^{-1}$) the capillary prefactor dominates at $N = 128$; the viscous bound becomes ruling only at very high Re.

## 2. Per-term time-treatment verdict

| Term | Verdict | Rationale |
|---|---|---|
| advection (UCCD6) | **explicit** (AB2 / SSPRK3 / RK4) | CFL is the loosest; non-linear Jacobian not worth the cost |
| viscosity | **implicit** (CN / BE) | $h^2$ constraint — catastrophic on non-uniform grids |
| surface tension | **semi-implicit** at L2, **fully implicit** at L3 | BKZ removed; wave-resolution remains (see [WIKI-X-025 §1](WIKI-X-025.md#1-why-capillary-δt-is-a-wave-resolution-constraint)) |
| pressure | **elliptic solve** | constraint equation; no time derivative |

## 3. Non-uniform grid amplification

Under the project's non-uniform grid ($\alpha = 1.5$, CLS interface fitting), $h_{\min}$ at the interface can be $\ll h_{\max}$:

$$
\Delta t_\nu^{\text{actual}} \sim h_{\min}^2 / \nu \;\ll\; \Delta t_\nu^{\text{uniform}}.
$$

This is the single strongest argument for **Crank–Nicolson on the viscous term** in the project's discretisation. A viscous explicit step on the finest interface-fit cell would blow the global time-step by $(h_{\max}/h_{\min})^2 \sim 10^2$ – $10^3$.

## 4. Linear-solver implication (LU is infeasible in 3D)

Once three independent elliptic/Helmholtz inversions are required per step:

1. PPE: $\nabla \cdot (\rho^{-1} \nabla p) = \text{RHS}$
2. CN-Helmholtz on momentum: $(I - \tfrac{\Delta t}{2\rho}\mathcal{V}) \mathbf{u}^* = \text{RHS}$
3. Semi-implicit ST Laplace–Beltrami (optional, L2): small local system

Direct factorisation (LU) is untenable at $N^3$ scale — memory scales as $O(N^6)$ for 3-D Kronecker assemblies. The only viable path is:

- **PPE**: CG / BiCGStab + **AMG preconditioner** (Algebraic MultiGrid).
- **CN-Helmholtz**: matrix-free Krylov with CCD-local preconditioning.
- **Implicit ST (L3)**: Newton + Krylov (JFNK).

Cross-reference: [WIKI-X-005](WIKI-X-005.md), [WIKI-X-009](WIKI-X-009.md), and [WIKI-L-028](../code/WIKI-L-028.md) (IIM decomposition as a structured precursor to AMG in the project's CCD stack).

## 5. Diagnostic — the smallest-Δt rule

The diagnostic is mechanical:

1. Compute $\Delta t_{\text{adv}}$, $\Delta t_\nu$, $\Delta t_{\text{cap}}$ from the current state.
2. The smallest is the rate-limiter.
3. If it is $\Delta t_\nu$ or $\Delta t_{\text{cap}}$, *moving that term to implicit treatment* is the single biggest speedup.
4. If it is $\Delta t_{\text{adv}}$, you are well-posed explicitly — no implicit work needed.

On ch13 water–air at $N=128$: $\Delta t_{\text{cap}} \simeq 10^{-4}$, $\Delta t_\nu \simeq 10^{-2}$ (effective), $\Delta t_{\text{adv}} \simeq 10^{-3}$ — capillary dominates; implicit viscous is *still* worth it for non-uniform robustness.

## 6. Connection to observed failure modes

Empirical observations from ch13 runs — `bf_res` blow-up, $\kappa$ chaos, H-01 late-time growth — are compatible with *time-integration* stiffness on top of the BF-residual issue of [WIKI-X-024](WIKI-X-024.md). The sequence of hypotheses to test:

1. BF pair consistency (CSF ↔ $\nabla p$) — primary, per [WIKI-X-024](WIKI-X-024.md).
2. Capillary $\Delta t$ wave-resolution breach — measure $\omega_c \Delta t$ and verify $\le 0.3$.
3. Viscous explicit instability at interface-refined $h_{\min}$ — diagnose via energy-balance residual.
4. UCCD6 advection skew-symmetry breach under $\rho$ jump — cross-reference [WIKI-X-028](WIKI-X-028.md).

Items 2-4 are all "time-integration" failures, distinct from item 1 (spatial force balance).

## 7. Recommended policy (project default)

| Layer | Policy |
|---|---|
| Advection | explicit AB2 (L2) or SSPRK3 (L1 warm-up) |
| Viscous | Crank–Nicolson, matrix-free Krylov |
| Surface tension | semi-implicit linearised (Aland–Voigt 2019) at $t^{n+1/2}$ |
| Pressure | CG/BiCGStab + AMG precond. (or IIM-decomp + iterative Schur at ch13 scale) |
| Interface | (explicit CLS / FCCD transport) + τ-reinit (see [WIKI-X-027](WIKI-X-027.md)) |

This is the default policy for ch13 production. Level-3 (Radau IIA + JFNK) is reserved for stiff campaigns per [WIKI-X-025 §2.3](WIKI-X-025.md#23-level-3--stiff-regimes-future).

## References

- [WIKI-X-025](WIKI-X-025.md) — time-integration design (parent)
- [WIKI-X-024](WIKI-X-024.md) — balanced-force design
- [WIKI-X-023](WIKI-X-023.md) — UCCD6-NS operator
- [WIKI-X-028](WIKI-X-028.md) — conservative momentum form under $\rho$ jump
- [WIKI-X-027](WIKI-X-027.md) — reinitialisation semantics (pseudo-$\tau$)
- [WIKI-X-007](WIKI-X-007.md) — CFL constraint hierarchy
- [WIKI-X-005](WIKI-X-005.md), [WIKI-X-009](WIKI-X-009.md) — PPE solver policy
- [WIKI-T-014](../theory/WIKI-T-014.md) — capillary CFL theory
- Brackbill, Kothe & Zemach (1992) *JCP* **100** — BKZ stability bound.
- Denner & van Wachem (2015) *JCP* **285** — capillary wave resolution.
- Trottenberg, Oosterlee & Schüller (2001) *Multigrid* — AMG for elliptic PPE.
