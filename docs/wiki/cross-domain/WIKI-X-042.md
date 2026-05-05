---
ref_id: WIKI-X-042
title: "Paper Failure Taxonomy Maps Symptoms to Numerical Contracts"
domain: cross-domain
status: ACTIVE
superseded_by: null
tags: [failure_taxonomy, contracts, paper, balanced_force, ppe, cls]
sources:
  - path: paper/sections/01_introduction.tex
    description: "Four numerical difficulties and symptom mapping"
  - path: paper/sections/01b_classification_roadmap.tex
    description: "Method classification and three-pillar route"
  - path: paper/sections/02b_surface_tension.tex
    description: "CSF/BF mismatch taxonomy"
  - path: docs/wiki/cross-domain/WIKI-X-041.md
    description: "Curated active retrieval gate"
depends_on:
  - "[[WIKI-X-041]]"
  - "[[WIKI-T-105]]"
  - "[[WIKI-T-146]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Failure Taxonomy to Contracts

## Knowledge Card

The paper's introduction is not only motivation; it is a routing table from
observable failures to numerical contracts.

| Symptom family | Contract family |
|---|---|
| mass loss, smearing | conservative CLS transport, mapping, and reinitialization |
| inaccurate curvature or capillary drive | HFE/psi curvature and sign-consistent interface stress |
| checkerboard or projection leakage | face-space PPE, adjoint divergence/gradient, shared corrector |
| parasitic currents near density jumps | balanced-force locus, coefficient, and jump consistency |

The three-pillar solution follows this map: high-order compact derivatives,
phase-separated pressure/jump projection, and face-locus balanced-force
coupling.

## Consequences

- A failure label should name the violated contract, not just the module where
  the symptom appears.
- Verification should distinguish component order from coupled identity.
- Old wiki cards that describe a symptom remain useful only after routing
  through the current active contracts.
- ResearchArchitect reviews should begin by classifying the failure family
  before selecting experiments or implementation fixes.

## Paper-Derived Rule

Read chapters 1-13 as a contract graph: symptoms are evidence for violated
numerical invariants, not isolated implementation anecdotes.
