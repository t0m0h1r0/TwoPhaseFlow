# SP-B: A Ridge–Eikonal Hybrid Framework for Interface Tracking with Continuous Topological Transitions

**Status**: Short paper draft (research memo)
**Date**: 2026-04-20
**Related**: [WIKI-T-007](../../wiki/theory/WIKI-T-007.md), [WIKI-T-036](../../wiki/theory/WIKI-T-036.md), [WIKI-T-042](../../wiki/theory/WIKI-T-042.md), [WIKI-X-014](../../wiki/cross-domain/WIKI-X-014.md)
**Companion paper**: [SP-A_face_centered_upwind_ccd.md](SP-A_face_centered_upwind_ccd.md)

---

## Notational convention (read first)

The symbol `ξ` is used in at least three distinct senses across this project. To avoid confusion, this paper adopts the following convention throughout and we will propose it as a project standard:

| Symbol | Meaning | Location of use |
|---|---|---|
| `ξ_idx` | Uniform computational-space coordinate (index space) used by the generalised-curvilinear CCD formulation | Existing `Grid` / `CCDSolver` / [WIKI-T-039](../../wiki/theory/WIKI-T-039.md) |
| `ω(φ)` | Gaussian *grid-density* function $\exp(-\alpha(\phi/\varepsilon_g)^2)$ controlling node spacing in the interface-fitted rebuild | [WIKI-T-038](../../wiki/theory/WIKI-T-038.md), [`Grid.update_from_levelset`](../../../src/twophase/core/grid.py) |
| `ξ_ridge` | **Proposed here**: auxiliary interface-representation scalar field, $\xi_\text{ridge}(x,t) = \sum_k \exp(-d_k^2/\sigma^2)$ | This paper |

A dedicated disambiguation entry is proposed as [WIKI-T-049](../../wiki/theory/WIKI-T-049.md).

---

## Abstract

We present a hybrid interface formulation that enables continuous topological transitions while preserving sharp-interface accuracy whenever the topology is fixed. The key idea is to decouple topological freedom from metric consistency by introducing a Gaussian-weighted auxiliary scalar field $\xi_\text{ridge}$, whose ridge set defines the interface. During topological evolution $\xi_\text{ridge}$ intentionally violates the Eikonal constraint, allowing ridge creation and annihilation corresponding to interface coalescence and breakup. Once a geometrically admissible ridge set emerges, a signed distance function $\phi$ is reconstructed as the unique viscosity solution of the Eikonal equation using Fast Marching (FMM) or Fast Sweeping (FSM) methods. The framework unifies interface tracking, ridge-based geometry, and Eikonal reconstruction within a single mathematically consistent workflow. A sketch of the uniqueness proof for $\phi$ is provided. We additionally record a caveat arising from the project’s own measurements ([WIKI-T-042](../../wiki/theory/WIKI-T-042.md), CHK-136–139): pure FMM reinitialisation degrades the volume-conservation budget for $\sigma > 0$ capillary-wave regimes and requires $\varepsilon$-widening. Any production deployment of this framework must explicitly reconcile with that constraint.

---

## 1. Introduction

Sharp interface-tracking methods offer superior geometric accuracy and stable evaluation of interfacial forces, but they assume the interface remains a single smooth manifold; topological transitions such as coalescence and breakup are consequently ill-posed unless explicit remeshing or event handling is introduced. Interface-capturing methods allow topology changes by representing the interface implicitly as a scalar field, but geometric sharpness and metric consistency are weakened.

The present work seeks a principled middle ground: topological transitions are enabled as **continuous time evolutions of an auxiliary scalar field**, while metric consistency is restored once the topology stabilises.

We follow the pattern of Osher–Sethian level sets but **replace the global Eikonal constraint on the primary field with a Gaussian-weighted representation whose ridge set — rather than a level set — defines the interface**. This change is the minimum deviation from classical level sets that admits continuous topology change while preserving the global signed-distance structure away from transition events.

---

## 2. Eikonal Constraint as Topological Rigidity

A signed distance function $\phi$ satisfies the Eikonal equation

$$
|\nabla \phi| = 1,
$$

which enforces that its level sets are parallel offsets of the zero level set. This property guarantees geometric robustness and uniqueness of the associated interface.

However, the Eikonal constraint also **suppresses local extrema and ridges**. As a consequence, the topology of the zero level set remains frozen under smooth time evolution. Reinitialisation procedures based on Fast Marching Method (FMM), Fast Sweeping Method (FSM), or the Godunov Hamilton–Jacobi discretisation (collectively the strategies catalogued in [WIKI-T-042](../../wiki/theory/WIKI-T-042.md)) may therefore be interpreted as **repeatedly enforcing topological rigidity**. From a geometric standpoint, the Eikonal constraint suppresses exactly the degrees of freedom required for interface merging or splitting — the same degrees of freedom that phase-field and conservative level-set methods recover only at the cost of interface smearing.

---

## 3. Gaussian-Weighted Auxiliary Field

To introduce topological freedom, we define the scalar field

$$
\xi_\text{ridge}(x,t) \;=\; \sum_k \exp\!\left(-\frac{d_k(x,t)^2}{\sigma^2}\right),
$$

where $d_k$ denotes the signed distance to each interface component $\Gamma_k$, and $\sigma$ controls the interaction length scale.

The field $\xi_\text{ridge}$ is **not** a distance function and **does not** satisfy the Eikonal equation. It admits local extrema and saddle points, which is what enables changes in connectivity. The temporal evolution of $\xi_\text{ridge}$ may be governed by an advection–diffusion equation,

$$
\partial_t \xi_\text{ridge} + \mathbf{u} \cdot \nabla \xi_\text{ridge} \;=\; \varepsilon \, \Delta \xi_\text{ridge},
$$

where a small diffusion term provides regularisation and facilitates smooth ridge interactions.

**Relation to existing project fields.** $\xi_\text{ridge}$ is orthogonal in concept to the grid-density Gaussian $\omega(\phi)$ ([WIKI-T-038](../../wiki/theory/WIKI-T-038.md)) despite notational similarity: $\omega$ controls grid spacing, while $\xi_\text{ridge}$ encodes the interface itself. It is also distinct from the existing `xi_sdf` reinitialisation mode ([`EikonalReinitializer._xi_sdf_phi`](../../../src/twophase/levelset/reinit_eikonal.py)): the latter computes an *exact Euclidean distance in index space* and is geometrically a signed distance — i.e., it satisfies an Eikonal relation and therefore cannot support topology change. `ξ_ridge` deliberately does the opposite.

---

## 4. Interface Definition via Ridges

The interface is defined as the **ridge set** of $\xi_\text{ridge}$. A point $x$ belongs to the interface $\Gamma$ if

$$
\nabla \xi_\text{ridge}(x) \;=\; 0, \qquad
\mathbf{n}^{\!\top} \nabla^2 \xi_\text{ridge}(x) \, \mathbf{n} \;<\; 0,
$$

where $\mathbf{n} = \nabla \xi_\text{ridge} / |\nabla \xi_\text{ridge}|$ is the normal direction.

This definition identifies points where $\xi_\text{ridge}$ attains a local maximum in the normal direction while remaining continuous along tangential directions — the scalar-field analogue of a crest line (or surface, in 3D). For an isolated interface, the ridge coincides with the geometric interface. When multiple interfaces interact, ridge merging and bifurcation occur smoothly, representing coalescence and breakup without discrete events.

The memo 1 of the original thread described this mechanism as a "computational-space reparameterisation event". We view it instead as a **continuous deformation of $\xi_\text{ridge}$** in the sense of Morse theory: coalescence corresponds to two ridge crests merging through a saddle, breakup to a ridge bifurcation, and both are one-parameter families of smooth fields. No discrete event or explicit remapping is required; a topological event is simply a time instant at which the Morse index of $\xi_\text{ridge}$ changes.

---

## 5. Uniqueness of the Reconstructed Distance Function

### 5.1 Problem statement

Once a ridge-defined interface $\Gamma$ has stabilised (see §6 for the stabilisation criterion), we reconstruct a signed distance function $\phi$ satisfying

$$
|\nabla \phi| = 1, \qquad \phi = 0 \text{ on } \Gamma.
$$

The question is whether $\phi$ is uniquely determined.

### 5.2 Geometric conditions

Uniqueness is guaranteed if the extracted ridge set $\Gamma$ satisfies:

1. **Geometric regularity** — $\Gamma$ is a closed, non-self-intersecting $(n-1)$-dimensional manifold.
2. **Unique closest-point projection** — for points in a neighbourhood of $\Gamma$, the nearest point on $\Gamma$ is unique.
3. **Normal consistency** — the normal direction inferred from $\xi_\text{ridge}$ is consistent across $\Gamma$.

These conditions are naturally enforced during ridge extraction by curvature bounds and a minimum-separation criterion.

### 5.3 Proof sketch

1. **Existence.** Since $\Gamma$ is closed, the distance to $\Gamma$ exists and is Lipschitz continuous.
2. **Local differentiability.** In regions where the closest-point projection $\pi$ onto $\Gamma$ is unique, $\phi$ is differentiable and
$$
\nabla \phi(x) \;=\; \mathbf{n}_\Gamma\bigl(\pi(x)\bigr).
$$
3. **Eikonal satisfaction.** Consequently, $|\nabla \phi| = 1$ almost everywhere.
4. **Uniqueness.** The Eikonal equation with boundary condition $\phi = 0$ on $\Gamma$ admits a unique viscosity solution by the comparison principle (see e.g. Crandall–Lions 1983 for the general theory).

Hence $\phi$ is uniquely defined once a geometrically admissible ridge set is identified.

---

## 6. Integration of FMM / FSM

Fast Marching and Fast Sweeping methods are used **exclusively for reconstructing $\phi$ from $\Gamma$**; they are never applied to $\xi_\text{ridge}$. The algorithmic flow is:

```
1. Evolve ξ_ridge  (topological freedom, non-Eikonal)
2. Extract ridge set Γ = {x | ∇ξ_ridge = 0, n · ∇²ξ_ridge · n < 0}
3. Check geometric admissibility of Γ (§5.2 conditions)
4. Reconstruct φ by solving |∇φ| = 1 with FMM/FSM, φ = 0 on Γ
5. Resume sharp interface tracking using φ (SP-A FCCD operator)
```

FMM is preferred in narrow-band reconstructions and on non-uniform grids; FSM is more effective for full-domain distance updates. In both cases, the resulting $\phi$ is the unique viscosity solution.

### 6.1 Project-specific caveat: CHK-138 σ > 0 failure

[WIKI-T-042](../../wiki/theory/WIKI-T-042.md) §CHK-138 records a finding that directly constrains this workflow: **FMM applied to a capillary-wave benchmark at $T=1$ produced a volume-conservation error of 8.2%, worse than the existing $\xi$-SDF non-iterative reinitialiser (1.46% at $T=2$)**. The diagnosed root cause was the interface-width parameter $\varepsilon$: under σ > 0 forcing, the PPE surface-tension residual scales as $\sigma \kappa / \varepsilon$, and FMM’s exact C¹ SDF leaves $\varepsilon$ at the nominal narrow-band value while operator-split methods broaden it to $\sim 1.4 \varepsilon$ by diffusion. The subsequent fix ([WIKI-X-016](../../wiki/cross-domain/WIKI-X-016.md), CHK-139) is an $\varepsilon_\text{scale} = 1.4$ modification applied only when σ > 0.

Any production deployment of the ridge–Eikonal workflow must therefore include the ε-widening step as an FMM post-processor, or provide an equivalent interface-width regularisation. The uniqueness result of §5 is unaffected — it bounds $\phi$, not the subsequent physical error budget.

---

## 7. Interaction with Face-Fixed Tracking (SP-A)

Once $\phi$ is reconstructed and the topology is fixed, the interface is snapped to cell faces and evolved using an ALE-style face-fixed formulation. Transport terms are discretised using the face-centred upwind operator developed in the companion short paper [SP-A](SP-A_face_centered_upwind_ccd.md), which provides fourth-order accuracy on the same face locus that the reconstructed $\phi$ inhabits. This ensures that the hand-off between the ridge phase (§3–§6) and the tracking phase does not introduce an additional interpolation error.

In the absence of topological transitions, the method therefore reduces to: (i) high-order face-centred CCD transport of $\phi$ via SP-A, plus (ii) occasional Eikonal re-projection via FMM to maintain metric consistency. This is a strict generalisation of the existing `phi_primary_transport` + `eikonal_xi` pipeline ([WIKI-T-036](../../wiki/theory/WIKI-T-036.md)) — it adds no cost away from transitions.

---

## 8. Discussion

The framework assigns distinct roles to two scalar fields:

| Field | Role | Constraint |
|---|---|---|
| $\xi_\text{ridge}$ | Enables continuous topology change | **Violates** Eikonal (intentional) |
| $\phi$ | Enforces metric consistency and accurate tracking | **Satisfies** Eikonal via FMM/FSM |

Topological transitions are handled during the evolution of $\xi_\text{ridge}$; geometric accuracy is restored through Eikonal reconstruction only after the topology becomes well-defined. This separation appears to be the minimum machinery needed: neither a pure tracking nor a pure capturing formulation admits this decomposition, and pure phase-field methods (which superficially appear to do so) pay the cost in the form of a diffuse interface that cannot be reconciled with sharp-interface tracking.

### Limitations

- **Parameter $\sigma$.** Too small suppresses transitions; too large diffuses geometry. A scaling with $\Delta x$, Re, and Ca is required (future work).
- **3D ridge extraction.** The 2D ridge-detection algorithms are relatively mature; robust Hessian-based 3D ridge surfaces are an open area.
- **Micro-physics.** The method does not resolve film rupture or contact-line dynamics; it provides a geometrically and numerically consistent macroscopic representation of topological change.
- **FMM σ > 0 caveat** (see §6.1): production use requires the ε-widening correction or an alternative interface-width regularisation.

---

## 9. Conclusions

We have proposed a ridge–Eikonal hybrid framework in which:

1. Topological transitions are represented as continuous ridge dynamics of a Gaussian-weighted auxiliary field $\xi_\text{ridge}$.
2. Interfaces are rigorously defined as ridge sets rather than level sets.
3. Metric consistency is restored by uniquely reconstructing a signed distance function $\phi$ through FMM/FSM.
4. The reconstructed $\phi$ is subsequently transported by the fourth-order face-centred operator of [SP-A](SP-A_face_centered_upwind_ccd.md), preserving sharp-interface accuracy away from transitions.

This separation of topological freedom and geometric rigidity provides a unified and mathematically consistent approach to interface tracking with coalescence and breakup. Its combination with SP-A defines a minimal research programme that, if validated numerically, would subsume both the late-blowup remediation required by [WIKI-E-030](../../wiki/experiment/WIKI-E-030.md) and the topology-change capability currently absent from the codebase.

### Future extensions

- 2D/3D numerical examples: droplet coalescence and pinch-off (reference benchmarks in [WIKI-E-015](../../wiki/experiment/WIKI-E-015.md) — currently recorded as a negative result).
- Scaling law for $\sigma$ in terms of $\Delta x$, Re, Ca.
- Quantitative comparison with phase-field sharp-interface limits.
- Comparison with classical level-set methods on the same benchmark.

---

## References

- Crandall, M. G., & Lions, P.-L. (1983). Viscosity solutions of Hamilton–Jacobi equations. *Transactions of the AMS*, 277, 1–42.
- Sethian, J. A. (1996). A Fast Marching Level Set Method for Monotonically Advancing Fronts. *Proc. Nat. Acad. Sci.*, 93(4), 1591–1595.
- Osher, S., & Sethian, J. A. (1988). Fronts propagating with curvature-dependent speed. *J. Comp. Phys.*, 79, 12–49.
- Project wiki: [WIKI-T-007](../../wiki/theory/WIKI-T-007.md) (CLS), [WIKI-T-036](../../wiki/theory/WIKI-T-036.md) (φ-primary transport), [WIKI-T-042](../../wiki/theory/WIKI-T-042.md) (Eikonal reinitialisation, CHK-136–139), [WIKI-X-014](../../wiki/cross-domain/WIKI-X-014.md) (non-uniform stability map), [WIKI-X-016](../../wiki/cross-domain/WIKI-X-016.md) (ε-scale propagation), [WIKI-E-015](../../wiki/experiment/WIKI-E-015.md) (coalescence benchmark negative result).
