---
ref_id: WIKI-T-097
title: "Pressure Jump Must Match the Solved Unknown"
domain: theory
status: ACTIVE
superseded_by: null
tags: [pressure_jump, ppe, projection, pressure_increment, young_laplace]
sources:
  - path: paper/sections/09b_split_ppe.tex
    description: "Unknown-specific pressure-jump contract for full pressure vs pressure increment"
depends_on:
  - "[[WIKI-T-083]]"
  - "[[WIKI-T-096]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Pressure Jump Must Match the Unknown

## Knowledge Card

The pressure jump supplied to the PPE must correspond to the unknown being
solved.  If the unknown is full pressure, the jump is the current
Young--Laplace jump.  If the unknown is pressure increment, the jump is the
increment of the Young--Laplace jump.

Confusing these two cases either double-counts the capillary pressure or lets the
previous pressure freedom absorb and erase it.

## Consequences

- `p^{n+1}` PPE uses `j_gl^{n+1}`.
- `delta p` PPE uses `delta j_gl = j_gl^{n+1} - j_gl^n`.
- The symbol `j_gl` in jump-corrected gradients is contextual shorthand for the
  jump carried by the current projection unknown.
- Reprojection after regridding must not blindly inherit the previous jump.

## Paper-Derived Rule

Before assembling a pressure-jump PPE, name the projection unknown first; the
jump follows from that choice.
