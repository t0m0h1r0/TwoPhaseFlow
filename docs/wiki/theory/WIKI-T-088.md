---
ref_id: WIKI-T-088
title: "FCCD Telescoping Conservation: Shared Face Flux Before Clamp"
domain: theory
status: ACTIVE
superseded_by: null
tags: [fccd, cls, face_flux, conservation, telescoping, clamp]
sources:
  - path: paper/sections/06b_advection.tex
    description: "FCCD face-flux advection and telescoping conservation argument"
depends_on:
  - "[[WIKI-T-080]]"
  - "[[WIKI-T-085]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# FCCD Telescoping Conservation

## Knowledge Card

FCCD stabilizes CLS advection by changing the locus of differentiation.  Instead
of differentiating a kinked `psi u` field at nodes, it reconstructs a shared face
flux and takes a face-flux difference.

The conservation mechanism is telescoping: the same face value is consumed by
the two neighboring cells, so the domain sum closes through boundary fluxes
before value limiting.

## Consequences

- The conserved object is the shared face flux, not a nodal derivative.
- Periodic and flux-consistent boundaries close the pre-clamp mass balance.
- Non-periodic and non-uniform cases still require the same-face sharing
  contract for conservation to hold.
- Clamp/value limiting can break exact telescoping and must be followed by the
  appropriate mass-closure stage.
- FCCD's stabilization is structural, not a high-wavenumber filter.

## Paper-Derived Rule

For CLS transport, first ask whether each interface flux exists once per face;
only then ask how accurately it was reconstructed.
