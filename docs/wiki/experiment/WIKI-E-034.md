---
ref_id: WIKI-E-034
title: "Pressure Output Semantics in V-Series Verification"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [verification, pressure, pressure_jump, laplace_pressure, v_series, diagnostics]
sources:
  - path: paper/sections/13_verification.tex
    description: "Pressure-output interpretation for Neumann PPE and pressure-jump PPE paths"
depends_on:
  - "[[WIKI-P-014]]"
  - "[[WIKI-T-083]]"
  - "[[WIKI-E-033]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Pressure Output Semantics in V-Series Verification

## Knowledge Card

The V-series uses two pressure meanings depending on the PPE path.  In the
Neumann PPE path, the reported pressure is physical pressure and can be compared
directly against the Laplace pressure.  In the pressure-jump PPE path, the
Laplace jump is embedded in the interface coupling, so the reported pressure is
projection-corrected pressure, not physical absolute Laplace pressure.

## Consequences

- V3/V5/V8 pressure errors use physical Laplace-pressure comparison.
- V6/V9 pressure-jump diagnostics must not be read as absolute Laplace-pressure
  error.
- A pressure metric is only comparable across tests after checking the PPE path.
- Apparent pressure-output degradation can be a semantics mismatch rather than a
  solver failure.

## Paper-Derived Rule

Before judging any V-series pressure number, identify whether the pressure is a
physical-pressure output or a projection-corrected diagnostic.
