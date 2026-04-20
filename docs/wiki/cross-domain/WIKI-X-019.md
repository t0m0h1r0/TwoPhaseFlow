# WIKI-X-019: Topology-Freedom vs Metric-Rigidity — ξ/φ Role Separation as Design Principle

## Statement of the principle

An interface representation that simultaneously requires (a) topological freedom (support for coalescence and breakup) and (b) metric consistency (sharp-interface geometric accuracy) cannot be achieved with a single scalar field. The two requirements must be assigned to **two distinct fields with disjoint constraints**:

| Field | Role | Constraint | When it is in charge |
|---|---|---|---|
| $\xi_\text{ridge}$ | carries topological freedom | **violates Eikonal** (deliberately) | during and near topological transitions |
| $\phi$ | carries metric consistency | **satisfies Eikonal** via FMM/FSM | away from transitions; after ridge stabilisation |

This is the design principle underlying the SP-B ridge–Eikonal hybrid ([WIKI-T-047](../theory/WIKI-T-047.md) / [WIKI-T-048](../theory/WIKI-T-048.md)).

## Why a single field cannot do both

Suppose $\phi$ is forced to satisfy both. Then:

- Eikonal constraint ($|\nabla\phi| = 1$) forces level sets to be parallel offsets of the zero level set.
- Parallel offsets cannot develop extrema or saddles under smooth time evolution.
- Therefore the topology of the zero level set is **frozen**: coalescence and breakup are ill-posed.

Conversely, if $\phi$ is allowed to develop extrema, the SDF structure is lost, and sharp-interface operators (face-fixed flux evaluation, force computation) degrade.

This is an essentially categorical obstruction, not a numerical one. Phase-field methods resolve it by accepting a diffuse interface (weakening requirement (b)). Level-set reinitialisation resolves it by forbidding topological transitions between reinit calls (weakening requirement (a) to ad-hoc events).

The ξ/φ separation restores both requirements by decoupling them across two fields.

## Practical consequences

### A. Code architecture (future-impl)

If SP-B is adopted, two separate classes/modules are needed:

1. A **ξ-ridge manager**: maintains $\xi_\text{ridge}$, evolves it via advection–diffusion, extracts ridges, checks admissibility.
2. A **φ reconstructor**: takes an admissible $\Gamma$ and produces $\phi$ via FMM/FSM (existing `EikonalReinitializer` already provides FMM).

Transport of $\phi$ is done by the **existing** (or SP-A-upgraded) compact transport path; the ξ/φ separation does not alter transport.

### B. Wiki / documentation

Any new discussion of the interface field must state explicitly which role it is playing:

- If metric consistency is required → $\phi$ (SDF, Eikonal).
- If topology change is required → $\xi_\text{ridge}$ (Gaussian ridge, non-Eikonal).
- If both are required at different times → explicit handshake via ridge extraction + FMM (see [WIKI-T-048](../theory/WIKI-T-048.md) algorithmic flow).

### C. Parameter separation

- $\varepsilon$ (interface width): belongs to the $\phi$ / $\psi$ side.
- $\varepsilon_g$, $\alpha$ (grid density): [WIKI-T-038](../theory/WIKI-T-038.md), belongs to grid generation, orthogonal to both fields.
- $\sigma$ (Gaussian ridge width): **new parameter** for $\xi_\text{ridge}$; belongs to the topology side. Scaling rule with $\Delta x$ / Re / Ca is future work.

### D. Test-design implication

A single test case cannot validate both requirements simultaneously. Future test-suite design should separate:

- **Metric-only tests**: single-interface benchmarks (Zalesak disk, static droplet) — exercise the $\phi$ side.
- **Topology-only tests**: coalescence/pinch-off benchmarks ([WIKI-E-015](../experiment/WIKI-E-015.md) negative result) — exercise the $\xi_\text{ridge}$ side.
- **Hand-off tests**: two approaching droplets, saddle-crossing event — exercise the interface between the two sides, including $\varepsilon$-widening post-FMM.

## Relation to existing design decisions

This principle is consistent with — but strictly stronger than — the existing practice:

- [WIKI-T-036](../theory/WIKI-T-036.md) (phi-primary transport): already uses $\phi$ exclusively for metric consistency. SP-B extends this by saying $\phi$ **cannot** be responsible for topology change; a separate $\xi_\text{ridge}$ is required.
- [WIKI-T-042](../theory/WIKI-T-042.md) (Eikonal reinitialisation): the various reinit strategies are classified as "enforcing topological rigidity"; SP-B provides the escape hatch for transitions.
- [WIKI-T-007](../theory/WIKI-T-007.md) (CLS): the CLS field $\psi$ is smooth but does not provide topological freedom either — it is a reformulation of the level set, not of the underlying interface representation.

## Open design question

Whether a project-level interface manager should present the two fields as a **unified object** (with a `ξ_phase`/`φ_phase` state flag) or as **two separate objects** with an explicit hand-off is an API question for future implementation. The theory itself is indifferent to this choice.

## Cross-references

- Theory: [WIKI-T-047](../theory/WIKI-T-047.md), [WIKI-T-048](../theory/WIKI-T-048.md), [WIKI-T-049](../theory/WIKI-T-049.md) (notation), [WIKI-T-042](../theory/WIKI-T-042.md)
- Short paper: [SP-B full draft](../../memo/short_paper/SP-B_ridge_eikonal_hybrid.md)
- Companion principle (discretisation side): [WIKI-X-018](WIKI-X-018.md) (FCCD metric unification)
