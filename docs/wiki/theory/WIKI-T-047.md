---
ref_id: WIKI-T-047
title: "Gaussian-ξ Ridge Interface Representation"
domain: theory
status: PROPOSED  # Research memo only; no code; PoC pending
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-B_ridge_eikonal_hybrid.md
    description: Short paper defining ξ_ridge and ridge-based interface
depends_on:
  - "[[WIKI-T-007]]: CLS Transport, Reinitialization, and Mass Conservation (baseline)"
  - "[[WIKI-T-036]]: Phi-Primary Transport — existing SDF-transport analogue"
  - "[[WIKI-T-049]]: Notation Disambiguation (ξ_idx vs ξ_ridge vs ω(φ))"
consumers:
  - domain: theory
    description: WIKI-T-048 (ridge-Eikonal hybrid reconstruction, uniqueness)
  - domain: cross-domain
    description: WIKI-X-019 (topology-freedom / metric-rigidity role separation)
tags: [interface_representation, ridge, morse_theory, topology, gaussian, auxiliary_field, research_proposal]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# Gaussian-ξ Ridge Interface Representation

## Overview

An auxiliary scalar field

$$
\xi_\text{ridge}(x,t) \;=\; \sum_k \exp\!\left(-\frac{d_k(x,t)^2}{\sigma^2}\right),
$$

representing interfaces not as the zero level set of a signed distance function, but as the **ridge set**

$$
\Gamma \;=\; \left\{ x \;\middle|\; \nabla \xi_\text{ridge}(x) = 0,\; \mathbf{n}^{\!\top} \nabla^2 \xi_\text{ridge}(x)\,\mathbf{n} < 0 \right\}, \qquad \mathbf{n} = \nabla\xi_\text{ridge}/|\nabla\xi_\text{ridge}|.
$$

Unlike the Eikonal-constrained $\phi$, $\xi_\text{ridge}$ admits local extrema and saddle points. Topological transitions — coalescence and breakup — manifest as continuous deformations of $\xi_\text{ridge}$ in the sense of Morse theory: ridge merging through a saddle corresponds to coalescence; ridge bifurcation corresponds to breakup. **No discrete event or explicit remapping is required.**

## Why not a level set?

The Eikonal constraint $|\nabla \phi| = 1$ forces the level sets of $\phi$ to be parallel offsets of the zero level set. In particular, $\phi$ cannot develop local extrema, and therefore the **topology of the zero level set is frozen under smooth time evolution**. This is the "topological rigidity" of Eikonal reinitialisation (a reinterpretation of FMM/FSM/Godunov catalogued in [WIKI-T-042](WIKI-T-042.md)).

$\xi_\text{ridge}$ deliberately violates the Eikonal constraint to recover the degrees of freedom needed for topology change, while leaving metric consistency to a separate reconstructed $\phi$ (see [WIKI-T-048](WIKI-T-048.md)).

## Time evolution

$\xi_\text{ridge}$ is evolved by an advection–diffusion equation:

$$
\partial_t \xi_\text{ridge} + \mathbf{u}\cdot\nabla \xi_\text{ridge} \;=\; \varepsilon\, \Delta \xi_\text{ridge},
$$

where a small diffusion $\varepsilon$ regularises ridge interactions.

## Parameter $\sigma$

Controls the interaction length. **Too small** suppresses topology change (ridges never meet). **Too large** diffuses geometry. A scaling with $\Delta x$, Re, and Ca is future work. Initial guidance: $\sigma \sim 2\text{--}4\,\Delta x_\text{face}$ for the isolated-interface regime, wider near transitions.

## Comparison with existing project fields

| Field | Origin | Eikonal? | Admits topology change? |
|---|---|---|---|
| $\phi$ (SDF) | [WIKI-T-036](WIKI-T-036.md), phi-primary transport | Yes | No (by design) |
| $\psi$ (CLS tanh) | [WIKI-T-007](WIKI-T-007.md) | implicit via $\phi$ | No |
| `xi_sdf` ([`_xi_sdf_phi`](../../../src/twophase/levelset/reinit_eikonal.py)) | index-space Euclidean SDF, [WIKI-T-042](WIKI-T-042.md) | Yes (exact) | No |
| $\omega(\phi)$ grid-density Gaussian | [WIKI-T-038](WIKI-T-038.md) | N/A (not an interface field) | N/A |
| $\xi_\text{ridge}$ | **This entry** | **No (intentional)** | **Yes** |

**Warning on notation.** The symbol `ξ` is used in the existing codebase for the uniform computational coordinate and by `EikonalReinitializer(xi_sdf=True)` for an exact Euclidean-distance reinit mode; both are metric-consistent scalars. $\xi_\text{ridge}$ is a different object. See [WIKI-T-049](WIKI-T-049.md) for the full disambiguation.

## Algorithmic flow (summary; full in [WIKI-T-048](WIKI-T-048.md))

```
1. Evolve ξ_ridge  (advection–diffusion; non-Eikonal)
2. Extract ridge set Γ
3. Check geometric admissibility of Γ
4. Reconstruct φ on Γ via FMM / FSM  (Eikonal, unique viscosity solution)
5. Resume sharp-interface tracking using φ
```

## References

- [SP-B full draft](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md)
- Morse theory background: Milnor (1963), *Morse Theory* (Princeton University Press).
- Ridge detection in scalar fields: Eberly (1996), *Ridges in Image and Data Analysis* (Kluwer).
- [WIKI-T-042](WIKI-T-042.md), [WIKI-T-048](WIKI-T-048.md), [WIKI-T-049](WIKI-T-049.md), [WIKI-X-019](../cross-domain/WIKI-X-019.md)
