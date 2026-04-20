---
ref_id: WIKI-T-048
title: "Ridge–Eikonal Hybrid Reconstruction: Uniqueness and FMM Coupling"
domain: theory
status: PROPOSED  # Research memo only; no code; PoC pending
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-B_ridge_eikonal_hybrid.md
    description: Short paper — §5 uniqueness proof sketch, §6 FMM/FSM integration
depends_on:
  - "[[WIKI-T-042]]: Eikonal-Based Unified Reinitialization — FMM/FSM catalogue; CHK-138 σ>0 failure mode"
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation"
  - "[[WIKI-T-036]]: Phi-Primary Transport (post-reconstruction transport)"
  - "[[WIKI-X-016]]: Reinit ε-Scale Propagation Path (σ>0 dispatch)"
consumers:
  - domain: cross-domain
    description: WIKI-X-019 (ξ/φ role separation as design principle)
  - domain: future-impl
    description: Ridge extraction + FMM coupling PoC
tags: [ridge, eikonal, fmm, fsm, uniqueness, viscosity_solution, topology_transition, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# Ridge–Eikonal Hybrid Reconstruction: Uniqueness and FMM Coupling

## Overview

The ridge-based interface $\Gamma$ of [WIKI-T-047](WIKI-T-047.md) is a geometric set; it does not carry a signed-distance structure. To resume high-order sharp-interface tracking, a signed distance $\phi$ must be reconstructed from $\Gamma$ as the unique viscosity solution of the Eikonal problem

$$
|\nabla \phi| = 1, \qquad \phi = 0 \text{ on } \Gamma.
$$

This entry records (i) the conditions under which $\phi$ is unique, (ii) the FMM/FSM algorithmic coupling, and (iii) a project-specific caveat inherited from [WIKI-T-042](WIKI-T-042.md) CHK-138 regarding σ > 0 failure.

## Uniqueness conditions

$\phi$ is uniquely determined whenever $\Gamma$ satisfies:

1. **Geometric regularity** — $\Gamma$ is a closed, non-self-intersecting $(n-1)$-dimensional manifold.
2. **Unique closest-point projection** — for points in a neighbourhood of $\Gamma$, the nearest point on $\Gamma$ is unique.
3. **Normal consistency** — the normal direction inferred from $\xi_\text{ridge}$ agrees with the geometric normal of $\Gamma$ across the whole of $\Gamma$.

These conditions are enforced during ridge extraction by curvature bounds and minimum-separation tests (see [WIKI-T-047](WIKI-T-047.md) §4 for the extraction criterion).

## Proof sketch

1. **Existence.** Since $\Gamma$ is closed, $d(x, \Gamma) := \inf_{y \in \Gamma} \|x-y\|$ exists and is Lipschitz. Setting $\phi(x) = \operatorname{sgn}(x) \cdot d(x, \Gamma)$ (sign determined by the ridge normal) gives a Lipschitz candidate.
2. **Local differentiability.** In the tubular neighbourhood where the closest-point projection $\pi(x)$ is unique, $\phi$ is differentiable with
$$
\nabla \phi(x) \;=\; \mathbf{n}_\Gamma(\pi(x)).
$$
3. **Eikonal satisfaction.** $|\nabla \phi| = |\mathbf{n}_\Gamma| = 1$ almost everywhere.
4. **Uniqueness.** The Eikonal equation with boundary condition $\phi = 0$ on $\Gamma$ admits a unique viscosity solution by the Crandall–Lions comparison principle (1983).

## Algorithmic coupling

```
Step 1  Evolve ξ_ridge  (non-Eikonal advection-diffusion)
Step 2  Extract Γ = ridge set  (Hessian-based detection)
Step 3  Admissibility test  (curvature bounds, separation ≥ σ/2, orientability)
Step 4  Reconstruct φ on Γ  (FMM narrow-band or FSM full-domain)
Step 5  Hand off to high-order tracking  (FCCD transport of φ — see [[WIKI-T-046]])
```

**FMM vs FSM choice.** FMM is a Dijkstra-style narrow-band solver; best for localised updates. FSM is Gauss–Seidel-style, converging after 2ⁿ sweeps in $n$ dimensions; better for full-domain updates on uniform grids. The existing `EikonalReinitializer(fmm=True)` ([`reinit_eikonal.py`](../../../src/twophase/levelset/reinit_eikonal.py)) already implements FMM; an FSM path does not currently exist.

## Project-specific caveat: CHK-138 σ > 0 failure

[WIKI-T-042](WIKI-T-042.md) §CHK-138 recorded that **FMM applied to the capillary-wave benchmark ($\sigma > 0$) at $T=1$ yielded a volume-conservation error of 8.2%**, worse than the non-iterative `xi_sdf` reinitialiser (1.46% at $T=2$), despite FMM’s lower $\phi_{xx}$ noise (2.83 vs 3.93). The diagnosed mechanism: the PPE surface-tension residual scales as $\sigma\kappa/\varepsilon$, and FMM’s exact C¹ SDF leaves $\varepsilon$ at the nominal narrow-band value; operator-split reinitialisers broaden $\varepsilon \to \sim 1.4\varepsilon$ by diffusion, which stabilises the PPE residual.

**Implication for the hybrid.** The uniqueness result above bounds $\phi$ to machine precision on the ridge set; it does *not* address the PPE residual budget. Any production deployment of the ridge–Eikonal workflow must therefore include one of:

- **$\varepsilon$-widening** (CHK-139 / [WIKI-X-016](../cross-domain/WIKI-X-016.md)): apply $\varepsilon_\text{scale} = 1.4$ to the reconstructed $\phi$ when σ > 0.
- **Post-hoc Gaussian blur** of $\phi$ within a prescribed bandwidth.
- **FSM with relaxed termination** (if the reduced noise of FMM is not needed, FSM may tolerate the wider $\varepsilon$ naturally).

The third option is unverified and requires a separate PoC (SP-B §8 future extensions).

## PoC programme (SP-B §6.1)

- **PoC-R1**: Ridge extraction on a static two-disk configuration (2D); verify admissibility as $\sigma$ decreases.
- **PoC-R2**: Coalescence dynamics — two approaching disks; track ridge-merge event at saddle.
- **PoC-R3**: Ridge → FMM reconstruction; measure $|\phi_\text{reconstructed} - \phi_\text{analytic}|$ on a known analytic ridge.
- **PoC-R4**: Full hybrid on capillary-wave benchmark with $\varepsilon_\text{scale} = 1.4$ applied after reconstruction; compare VolCons vs existing `eikonal_xi` baseline.

## References

- Crandall, M. G., & Lions, P.-L. (1983). Viscosity solutions of Hamilton–Jacobi equations. *Trans. AMS*, 277, 1–42.
- Sethian, J. A. (1996). *Level Set Methods and Fast Marching Methods* (Cambridge).
- Zhao, H. (2005). A fast sweeping method for Eikonal equations. *Math. Comp.*, 74, 603–627.
- [SP-B full draft](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md)
- [WIKI-T-042](WIKI-T-042.md), [WIKI-T-047](WIKI-T-047.md), [WIKI-X-016](../cross-domain/WIKI-X-016.md), [WIKI-X-019](../cross-domain/WIKI-X-019.md)
