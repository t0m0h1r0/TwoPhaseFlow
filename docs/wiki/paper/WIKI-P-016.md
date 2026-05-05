---
ref_id: WIKI-P-016
title: "Appendices Are Proof Layers for Main-Text Contracts"
domain: paper
status: ACTIVE
superseded_by: null
tags: [paper, appendix, proof_layer, retrieval_map, contracts]
sources:
  - path: paper/sections/appendix_a_nondim_details.tex
    description: "Nondimensionalization support layer"
  - path: paper/sections/appendix_b_interface.tex
    description: "Interface and CLS support layer"
  - path: paper/sections/appendix_c_ccd.tex
    description: "CCD support layer"
  - path: paper/sections/appendix_d_advection_stability.tex
    description: "Advection and capillary stability support layer"
  - path: paper/sections/appendix_e_pressure_coupling.tex
    description: "Pressure/projection support layer"
  - path: paper/sections/appendix_f_bootstrap.tex
    description: "Initial-condition bootstrap support layer"
  - path: paper/sections/appendix_g_verification_details.tex
    description: "Verification-detail support layer"
depends_on:
  - "[[WIKI-P-015]]"
  - "[[WIKI-T-148]]"
  - "[[WIKI-T-149]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Appendix Proof Layers

## Knowledge Card

The appendices should be retrieved as proof layers for main-text contracts, not
as a second paper with independent policy.

| Appendix | Retrieval role |
|---|---|
| A | nondimensionalization and parameter consistency |
| B | interface representation, mapping, and curvature support |
| C | CCD algebra, boundary closure, and periodic closure support |
| D | advection and capillary stability support |
| E | pressure coupling, PPE, DC, and predictor support |
| F | initial-condition bootstrap support |
| G | verification detail support |

This reading prevents an appendix caveat from being used without the main-text
algorithmic context it qualifies.

## Consequences

- Appendix-derived wiki cards should name the main-text contract they support.
- Boundary, startup, and bootstrap caveats are operational constraints, not
  side notes.
- Proof detail should not override the active retrieval gate unless the paper
  main text has adopted the same contract.
- Reviews of chapters 1-13 should include appendix support only where it
  changes an executable or verification rule.

## Paper-Derived Rule

Index appendix knowledge by the main-text contract it proves, constrains, or
guards.
