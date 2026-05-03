---
ref_id: WIKI-T-086
title: "Mass Closure Has Two Spaces: psi-Localized Before, phi-Uniform After"
domain: theory
status: ACTIVE
superseded_by: null
tags: [cls, mass_correction, psi, phi, contact_line, newton_correction]
sources:
  - path: paper/sections/05b_cls_stages.tex
    description: "Stage B psi-space and Stage F phi-space mass closure"
  - path: paper/sections/05_reinitialization.tex
    description: "Eikonal/Ridge--Eikonal mass closure and contact-line masking"
depends_on:
  - "[[WIKI-T-081]]"
  - "[[WIKI-T-085]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Mass Closure Has Two Spaces

## Knowledge Card

CLS mass correction changes meaning depending on where it is applied.  Immediately
after conservative `psi` advection or remap, correction is `psi`-space and
interface-local, weighted by `psi(1-psi)`.  After redistancing, correction is
`phi`-space and acts as an approximately uniform signed-distance shift.

These two corrections are not interchangeable.

## Consequences

- Stage B correction should vanish in bulk `psi in {0,1}` regions.
- Stage F correction should shift the interface through `phi`, not resharpen
  `psi`.
- The `phi` correction is a Newton-type linearized closure of the mass integral.
- Strict closure requires residual monitoring and possible repetition.
- Wall-contact bands must mask the correction so contact seeds do not move.

## Paper-Derived Rule

Mass closure is not a scalar bookkeeping patch; it is a geometric operation whose
allowed form depends on the current representation.
