---
ref_id: WIKI-T-080
title: "Shared Face Locus Invariant: The Paper's Strongest Discrete Contract"
domain: theory
status: ACTIVE
superseded_by: null
tags: [balanced_force, fccd, face_locus, projection, hfe, pressure_jump]
sources:
  - path: paper/sections/06c_fccd_advection.tex
    description: "FCCD face-flux BF consistency theorem"
  - path: paper/sections/08d_bf_seven_principles.tex
    description: "Balanced--Force P-1..P-7"
  - path: paper/sections/08e_fccd_bf.tex
    description: "Face-jet BF subsystem"
  - path: paper/sections/09c_hfe.tex
    description: "HFE as one-sided field extension for phase-separated PPE"
  - path: paper/sections/11_full_algorithm.tex
    description: "One-step update requiring shared interface face geometry"
  - path: paper/sections/11d_pure_fccd_dns.tex
    description: "Pure FCCD DNS as the face-locus limiting route"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-X-029]]"
  - "[[WIKI-T-063]]"
  - "[[WIKI-T-069]]"
  - "[[WIKI-T-076]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Shared Face Locus Invariant

## Knowledge Card

The strongest discrete invariant in Chapters 1--13 is the shared face locus:

```text
pressure gradient, velocity correction, interface force,
pressure-jump correction, HFE data, and flux divergence
must be expressed on the same face-space geometry.
```

This is the operational form of Balanced--Force consistency in the current
paper.  It is more important than any isolated high-order claim.

## Consequences

- PPE and corrector must share the same face gradient/divergence language.
- Surface tension and pressure must cancel at the same discrete location.
- HFE must supply smooth one-sided data before CCD/FCCD consumes it.
- Jump correction belongs to the face flux, not to an unrelated nodal post-fix.
- Pure FCCD DNS is the limiting architecture where all major operators speak
  one face-jet language.

## Paper-Derived Rule

When a two-phase failure appears, check face-locus mismatch before checking
CFL, curvature caps, damping, or solver tolerances.
