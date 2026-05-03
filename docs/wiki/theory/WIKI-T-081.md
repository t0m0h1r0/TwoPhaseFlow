---
ref_id: WIKI-T-081
title: "Wall Contact Topology Invariant for CLS Transport"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, wall_boundary, contact_line, topology, reinitialization, mass_correction]
sources:
  - path: paper/sections/03b_cls_transport.tex
    description: "CLS transport conservation and wall-contact topology invariant"
depends_on:
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-027]]"
  - "[[WIKI-T-078]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Wall Contact Topology Invariant for CLS Transport

## Knowledge Card

For a stationary no-slip wall, CLS transport preserves more than volume.  In the
absence of an explicit slip, contact-line, or contact-angle model, the phase
intervals on the wall and the existing wall contact roots are fixed topological
data.

This does not mean the smoothed wall value `psi_w` must be numerically frozen.
The value may vary while remaining on the same phase side.  What must not
change is the sign topology of `psi_w - 1/2` on the wall.

## Consequences

- Reinitialization must not create a new wall contact point.
- Mass correction must not move prescribed contact-line roots.
- Grid reconstruction must preserve wall phase intervals unless a contact model
  explicitly changes them.
- Periodic boundaries do not carry this wall-contact invariant.

## Paper-Derived Rule

Treat wall contact roots as pinned geometric boundary data, not as disposable
side effects of CLS smoothing or volume correction.
