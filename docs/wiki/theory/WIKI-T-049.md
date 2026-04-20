---
ref_id: WIKI-T-049
title: "Notation Disambiguation: ξ_idx vs ξ_ridge vs ω(φ)"
domain: theory
status: REFERENCE  # Stable notation reference; no PoC needed
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-B_ridge_eikonal_hybrid.md
    description: Origin of ξ_ridge and the need for disambiguation
depends_on:
  - "[[WIKI-T-038]]: Gaussian Density Bandwidth — ω(φ) definition"
  - "[[WIKI-T-039]]: ξ-Space CCD Metric Limitation — ξ_idx definition"
  - "[[WIKI-T-040]]: xi-Space eps Definition — ω(φ) relation"
  - "[[WIKI-T-042]]: Eikonal Reinitialization — xi_sdf mode"
  - "[[WIKI-T-047]]: Gaussian-ξ Ridge Interface Representation — ξ_ridge definition"
consumers:
  - domain: all
    description: All future memos using ξ / ω / xi_sdf should cross-link here
tags: [notation, disambiguation, reference, ridge, grid_density, computational_coordinate]
compiled_by: Claude Opus 4.7
compiled_at: "2026-04-20"
---

# Notation Disambiguation: ξ_idx vs ξ_ridge vs ω(φ) vs xi_sdf

## Why this entry exists

The symbol `ξ` is used in **three distinct senses** across the TwoPhaseFlow project, and a fourth related quantity `xi_sdf` reuses the Latin spelling "xi". Historical context made each name locally reasonable, but the combined usage is confusing. This entry fixes the convention for all future writing.

## Canonical table

| Symbol | Kind | Definition | Satisfies Eikonal? | Introduced in |
|---|---|---|---|---|
| `ξ_idx` | computational coordinate | uniform index variable $\xi_i = i / N$ (0 ≤ ξ ≤ 1) | N/A (coordinate) | [`Grid`](../../../src/twophase/core/grid.py), [WIKI-T-039](WIKI-T-039.md) |
| `ω(φ)` | grid-density function | $\omega(\phi) = \exp\!\bigl(-\alpha (\phi/\varepsilon_g)^2\bigr)$ | N/A (scalar multiplier) | [WIKI-T-038](WIKI-T-038.md), [`Grid.update_from_levelset`](../../../src/twophase/core/grid.py) |
| `xi_sdf` | reinit mode | exact Euclidean distance in $\xi_\text{idx}$ space from each node to the nearest zero-crossing | **Yes** (exact geometric SDF) | [WIKI-T-042](WIKI-T-042.md), [`EikonalReinitializer._xi_sdf_phi`](../../../src/twophase/levelset/reinit_eikonal.py) |
| `ξ_ridge` | interface-representation scalar | $\xi_\text{ridge}(x,t) = \sum_k \exp(-d_k^2/\sigma^2)$ | **No (intentional)** | [WIKI-T-047](WIKI-T-047.md), [SP-B](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md) |

## Why the four are genuinely different

1. **ξ_idx is a coordinate**, not a field. It is the independent variable of the generalised-curvilinear formulation, and is evaluated at uniform intervals in index space. Every other symbol is a dependent field on the physical (or xi_idx) space.

2. **ω(φ) controls where grid nodes are placed**, not what the interface is. `Grid.update_from_levelset` uses `ω(φ)` as the density against which index-space coordinates are distributed; a Gaussian centred on the zero level set produces refinement near the interface. `ω` never appears in the interface definition or reinitialisation.

3. **xi_sdf is a reinit mode that produces a signed distance function** defined by nearest-zero-crossing Euclidean distance in ξ_idx space. It satisfies the Eikonal equation exactly by construction. It is a redistancer for the existing $\phi$ / $\psi$ CLS fields.

4. **ξ_ridge is an auxiliary interface field** whose ridge set *defines* the interface. It is orthogonal in concept to all three above: it replaces, rather than post-processes, the role of the level set. It deliberately violates the Eikonal constraint to admit topological transitions.

## Cross-checks

- **Gaussian of distance** appears in both `ω(φ)` and `ξ_ridge` with **different meaning**: in `ω`, the single Gaussian around the zero level set is a grid-density weight; in `ξ_ridge`, the sum of Gaussians around multiple interface components is the representation of the interface itself.
- **Metric consistency** is satisfied by `ξ_idx`, `xi_sdf`, and reconstructed `φ` (post-ridge). It is **not** satisfied by `ξ_ridge` (and it must not be, for topology change to be possible).
- **Directionality of the analogy**: `xi_sdf` is a geometric SDF (solution of Eikonal); `ξ_ridge` is an auxiliary field whose *ridge set* later feeds an Eikonal solve (see [WIKI-T-048](WIKI-T-048.md)).

## Proposed renaming for the codebase (future task)

If SP-B proceeds past PoC, the existing `xi_sdf` string literal in `EikonalReinitializer` should be renamed to `idx_euclidean_sdf` (or similar) to free the `ξ` symbol for the ridge field. This is a cosmetic change and not blocking any current work.

## References

- [WIKI-T-038](WIKI-T-038.md), [WIKI-T-039](WIKI-T-039.md), [WIKI-T-040](WIKI-T-040.md), [WIKI-T-042](WIKI-T-042.md), [WIKI-T-047](WIKI-T-047.md)
- [SP-B full draft](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md)
