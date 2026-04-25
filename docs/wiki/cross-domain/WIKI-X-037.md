---
ref_id: WIKI-X-037
title: "ResearchArchitect Wiki Knowledge Atlas: Retrieval Map, Invariants, and Open Fronts"
domain: cross-domain
status: ACTIVE
superseded_by: null
sources:
  - path: docs/wiki/INDEX.md
    git_hash: 266d87c
    description: "Global inventory of 219 existing wiki entries"
  - path: docs/wiki/cross-domain/WIKI-X-022.md
    git_hash: 266d87c
    description: "N-robust BF-consistent full-stack role map"
  - path: docs/wiki/cross-domain/WIKI-X-029.md
    git_hash: 266d87c
    description: "Balanced-force CCD/FCCD design principles"
  - path: docs/wiki/cross-domain/WIKI-X-032.md
    git_hash: 266d87c
    description: "Complete one-step CLS + variable-density NS phase ordering"
  - path: docs/wiki/cross-domain/WIKI-X-033.md
    git_hash: 266d87c
    description: "Pure high-order FCCD two-phase DNS architecture"
  - path: docs/wiki/theory/WIKI-T-076.md
    git_hash: 266d87c
    description: "Projection-closure theorem for phase-separated FCCD"
  - path: docs/wiki/experiment/WIKI-E-032.md
    git_hash: 266d87c
    description: "ch13 projection-closure trial synthesis"
  - path: docs/wiki/code/WIKI-L-033.md
    git_hash: 266d87c
    description: "Clean integration contract for phase-separated FCCD projection closure"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-036]]"
  - "[[WIKI-T-046]]"
  - "[[WIKI-T-048]]"
  - "[[WIKI-T-060]]"
  - "[[WIKI-T-063]]"
  - "[[WIKI-T-065]]"
  - "[[WIKI-T-066]]"
  - "[[WIKI-T-069]]"
  - "[[WIKI-T-071]]"
  - "[[WIKI-T-076]]"
  - "[[WIKI-X-022]]"
  - "[[WIKI-X-029]]"
  - "[[WIKI-X-032]]"
  - "[[WIKI-X-033]]"
  - "[[WIKI-X-034]]"
  - "[[WIKI-X-035]]"
  - "[[WIKI-X-036]]"
  - "[[WIKI-E-027]]"
  - "[[WIKI-E-028]]"
  - "[[WIKI-E-030]]"
  - "[[WIKI-E-031]]"
  - "[[WIKI-E-032]]"
  - "[[WIKI-L-014]]"
  - "[[WIKI-L-015]]"
  - "[[WIKI-L-024]]"
  - "[[WIKI-L-025]]"
  - "[[WIKI-L-026]]"
  - "[[WIKI-L-031]]"
  - "[[WIKI-L-032]]"
  - "[[WIKI-L-033]]"
  - "[[WIKI-P-003]]"
  - "[[WIKI-P-005]]"
  - "[[WIKI-P-013]]"
consumers:
  - domain: cross-domain
    usage: "ResearchArchitect entry point for wiki retrieval and task routing"
  - domain: theory
    usage: "Start page for selecting the governing invariant before deriving new operators"
  - domain: code
    usage: "Implementation checklist before editing projection, interface, or GPU paths"
  - domain: experiment
    usage: "Diagnosis map for ch13 and future high-density-ratio validation"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-25
---

# WIKI-X-037 — ResearchArchitect Wiki Knowledge Atlas

## Scope

This entry is a retrieval map, not a new theory. It compiles the existing wiki
into a ResearchArchitect-friendly atlas so future tasks can jump to the right
source of truth without re-reading all entries.

Definitions remain in their original entries. This atlas only records:

1. the governing invariants,
2. the shortest retrieval path for common research questions,
3. resolved vs open fronts,
4. the code and experiment anchors that validate each chain.

## One-Sentence Project Thesis

The project is a high-order two-phase DNS stack whose real invariant is not
"use a high-order stencil everywhere" but:

```text
pressure solve, pressure correction, surface/interface force, density weighting,
and divergence witness must share the same discrete locus and coefficient space.
```

That thesis appears first as balanced force in [[WIKI-T-004]], becomes the
seven-principle CCD/FCCD design guide in [[WIKI-X-029]], and is now the concrete
phase-separated projection identity in [[WIKI-T-076]], [[WIKI-L-033]], and
[[WIKI-E-032]].

## Fast Retrieval Map

| Question | Start here | Then read | Why |
|---|---|---|---|
| What is the master invariant? | [[WIKI-T-004]] | [[WIKI-X-029]], [[WIKI-T-076]] | Balanced force evolves into same-operator `D_f A_f G_f` closure. |
| Why FCCD instead of node CCD or FVM? | [[WIKI-T-046]] | [[WIKI-T-063]], [[WIKI-T-069]], [[WIKI-X-033]] | FCCD supplies a common face-jet and face-locus operator language. |
| How is the interface represented? | [[WIKI-T-036]] | [[WIKI-T-048]], [[WIKI-L-025]], [[WIKI-E-028]] | `phi` carries metric structure; ridge/Eikonal handles topology and reinit. |
| How should one timestep be ordered? | [[WIKI-X-032]] | [[WIKI-T-065]], [[WIKI-T-066]] | Interface-first ordering fixes the geometry time level before NS forces. |
| What actually caused latest ch13 blowup? | [[WIKI-E-032]] | [[WIKI-T-076]], [[WIKI-L-032]], [[WIKI-L-033]] | PPE used phase-separated `A_f`; corrector used mixture `A_f`. |
| Where is the production code contract? | [[WIKI-L-033]] | [[WIKI-L-024]], [[WIKI-L-025]], [[WIKI-L-031]] | Clean merge imported only the minimal operator closure and tests. |
| What is still proposed or exploratory? | [[WIKI-X-033]] | [[WIKI-T-060]], [[WIKI-T-071]] | Pure FCCD, GPU-native projection, and face-canonical ownership remain design fronts. |
| How does this feed the paper? | [[WIKI-P-013]] | [[WIKI-P-003]], [[WIKI-P-005]] | SP-core rewrite maps the wiki stack into manuscript sections. |

## Dependency Lanes

| Lane | Principle | Design | Code | Evidence | Paper |
|---|---|---|---|---|---|
| Balanced force | [[WIKI-T-004]] | [[WIKI-X-029]], [[WIKI-T-063]], [[WIKI-T-076]] | [[WIKI-L-032]], [[WIKI-L-033]] | [[WIKI-E-031]], [[WIKI-E-032]] | [[WIKI-P-013]] |
| FCCD face-locus | [[WIKI-T-046]] | [[WIKI-T-069]], [[WIKI-X-033]] | [[WIKI-L-024]], [[WIKI-L-031]] | [[WIKI-E-030]], [[WIKI-E-032]] | [[WIKI-P-013]] |
| Interface geometry | [[WIKI-T-036]] | [[WIKI-T-048]] | [[WIKI-L-025]] | [[WIKI-E-027]], [[WIKI-E-028]] | [[WIKI-P-013]] |
| One-step NS/CLS | [[WIKI-T-065]] | [[WIKI-X-032]], [[WIKI-T-066]] | [[WIKI-L-014]] | [[WIKI-E-031]], [[WIKI-E-032]] | [[WIKI-P-005]] |
| GPU/performance | [[WIKI-T-060]] | [[WIKI-L-026]] | [[WIKI-L-015]] | ch11 GPU ledger history | [[WIKI-P-013]] |

## Current Stable Knowledge

### 1. Operator consistency outranks formal stencil order

The balanced-force chain fails when pressure gradient, surface tension, PPE
divergence, or density weighting are evaluated in different spaces. A lower-order
consistent pair can be more stable than a higher-order inconsistent pair. This
is the central lesson of [[WIKI-T-004]], [[WIKI-X-022]], and [[WIKI-X-029]].

### 2. FCCD is the face-language for the sharp-interface stack

FCCD is valuable because it makes face values, face gradients, and face curvature
inputs share a single primitive, not because it maximizes polynomial order in
isolation. The living role is the common face-jet contract in [[WIKI-T-046]] and
[[WIKI-T-069]], consumed by HFE, GFM, phase-separated PPE, and viscous interface
band assembly.

### 3. Projection closure is now a concrete algebraic test

The latest ch13 resolution reduces the failure to:

```text
PPE side:       D_f A_f^sep G_f p
corrector side: D_f A_f^mix G_f p
```

The clean fix is not a broader predictor rewrite. It is the equality of
`D_f`, `A_f`, and `G_f` across matrix-free PPE and velocity correction, including
non-uniform wall rows and phase-cut policy. See [[WIKI-T-076]], [[WIKI-L-033]],
and [[WIKI-E-032]].

### 4. Interface reinitialization has two separate duties

`phi` must be a signed-distance metric object, while ridge/Eikonal machinery
provides topology handling and reconstruction. For capillary cases, exact FMM
geometry alone is not enough; the epsilon budget affects PPE residuals. This is
the practical link between [[WIKI-T-048]], [[WIKI-E-027]], and [[WIKI-E-028]].

### 5. Clean production merges should import identities, not hypotheses

The successful ch13 closure followed the pattern in [[WIKI-L-033]]: identify the
smallest violated discrete identity, port only that identity, add operator-level
regression tests, then run one representative experiment. Exploratory modes,
YAML variants, and broad PoC branches stay outside main until separately
validated.

## Status Tiers

| Tier | Entries | How to use |
|---|---|---|
| Settled invariants | [[WIKI-T-004]], [[WIKI-X-029]], [[WIKI-T-076]], [[WIKI-L-033]], [[WIKI-E-032]] | Treat as mandatory constraints before changing projection or force paths. |
| Production code anchors | [[WIKI-L-014]], [[WIKI-L-024]], [[WIKI-L-025]], [[WIKI-L-032]], [[WIKI-L-033]] | Use to locate implementation contracts and regression tests. |
| Validated diagnostic history | [[WIKI-E-027]], [[WIKI-E-028]], [[WIKI-E-030]], [[WIKI-E-031]], [[WIKI-E-032]] | Use to avoid re-testing rejected hypotheses. |
| Active architecture direction | [[WIKI-X-022]], [[WIKI-X-032]], [[WIKI-X-033]], [[WIKI-X-034]], [[WIKI-X-035]], [[WIKI-X-036]] | Use for design route selection and paper-facing narrative. |
| Open performance/design fronts | [[WIKI-T-060]], [[WIKI-T-071]], [[WIKI-L-026]] | Use for future GPU and face-canonical work, not as settled production law. |

## Debugging Rules of Thumb

1. Before blaming time integration, test whether the projection applies the same
   `D_f A_f G_f` operator that the PPE solved.
2. Before changing buoyancy placement, verify whether buoyancy is exciting an
   existing projection defect or causing an independent imbalance.
3. Before adding a high-order stencil near the interface, identify whether the
   field is smooth across the stencil; otherwise use HFE/GFM/IIM-style one-sided
   protection.
4. Before judging reinitialization by mass conservation alone, check curvature,
   epsilon width, PPE residual, and capillary-wave response.
5. Before merging an exploratory CFD branch, reduce it to one algebraic identity
   plus regression tests.

## Open Fronts

| Front | Current anchor | Open question |
|---|---|---|
| Final ch13 physical verdict | [[WIKI-E-032]] | The early explosive failure is removed, but the documented `T=0.05` run is not yet a final benchmark verdict. |
| q-jump / pressure-jump closure | [[WIKI-X-033]], [[WIKI-E-032]] | q-jump is secondary to projection closure; its final production role still needs a clean post-closure gate. |
| Pure FCCD GFM rows | [[WIKI-X-033]], [[WIKI-T-063]] | Phase-separated PPE has the structural path, but GFM jump pressure jets remain the next closure stage. |
| FCCD x IIM composition | [[WIKI-X-022]] | Face-locus IIM analogues are not yet fully documented. |
| GPU-native FCCD projection | [[WIKI-T-060]], [[WIKI-L-026]] | FVM matrix-free GPU theory exists; the pure-FCCD equivalent is still a design front. |
| Sigma-positive reinit policy | [[WIKI-T-048]], [[WIKI-E-028]] | FMM exactness must be balanced against epsilon widening and capillary PPE residual stability. |

## ResearchArchitect Routing Heuristic

| Task symptom | Route first | Reason |
|---|---|---|
| New blowup, high density ratio, projection residual | [[WIKI-E-032]] | Latest accepted diagnostic pattern and rejected hypotheses. |
| New pressure/PPE/corrector design | [[WIKI-T-076]] | Operator identity is the non-negotiable starting theorem. |
| New interface/reinit design | [[WIKI-T-048]] | Separates topology, signed distance, and sigma-positive stability policy. |
| New FCCD/HFE/GFM feature | [[WIKI-T-046]] | Establishes common face-jet primitive and locus constraints. |
| Paper rewrite or reviewer question | [[WIKI-P-013]] | Maps SP-core theory into manuscript structure. |
| GPU optimization | [[WIKI-T-060]] | Separates mathematical operator from matrix representation and D2H/H2D hazards. |
