---
ref_id: WIKI-T-103
title: "Time-Step Limits Are Per-Term: Capillary Is Physical, PPE Is Projective"
domain: theory
status: ACTIVE
superseded_by: null
tags: [time_step, cfl, capillary, projection, viscosity, imex_bdf2]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Per-term timestep constraints and capillary/viscous/PPE classification"
  - path: paper/sections/11c_dccd_bootstrap.tex
    description: "Full-algorithm timestep control"
depends_on:
  - "[[WIKI-T-014]]"
  - "[[WIKI-T-083]]"
  - "[[WIKI-T-102]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Time-Step Limit Taxonomy

## Knowledge Card

The paper separates time-step restrictions by origin.  Advective limits come from
the explicit/extrapolated advection operator.  Capillary limits are physical
interface-wave resolution limits.  Viscous CFL is removed for the fully implicit
BDF2 viscous block.  PPE projection is not itself an explicit CFL source.

`Delta t_disc` is reserved for extra explicit residual spectra on non-uniform or
extrapolated paths; absent such eigenvalue evidence, it is treated as inactive.

## Consequences

- Capillary CFL survives even when surface tension is handled as a PPE jump.
- Capillary CFL belongs to physical validation, not to the algebraic PPE closure.
- Viscous A-stability removes only pure viscous diffusion limits.
- Projection/PPE errors should not be diagnosed as CFL limits unless an explicit
  growth mechanism is identified.
- Non-uniform metric/extrapolation limits need their own spectral evidence.

## Paper-Derived Rule

When reducing `dt`, name the limiting term; do not use "CFL" as a generic
stability bucket.
