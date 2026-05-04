---
ref_id: WIKI-T-141
title: "Delta t_disc Covers Residual Explicit Spectra, Not Projection or Viscous CFL"
domain: theory
status: ACTIVE
superseded_by: null
tags: [time_step, cfl, nonuniform_grid, defect_correction, viscous_implicit]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "Meaning of dt_disc in the synchronized time-step minimum"
depends_on:
  - "[[WIKI-T-103]]"
  - "[[WIKI-T-127]]"
  - "[[WIKI-T-135]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Discrete-Spectrum Time Cap

## Knowledge Card

The synchronized time step includes:

```text
Delta t_syn = min(dt_adv, dt_sigma, dt_buoy, dt_disc)
```

Here `dt_disc` is an auxiliary cap for residual explicit or extrapolated
spectral content, especially nonuniform-grid residuals.  It is not a PPE CFL,
and it is not the ordinary viscous stability limit when the viscous step is
handled by implicit BDF2 plus defect correction.

## Consequences

- Projection does not become explicit merely because `dt_disc` appears in the
  global minimum.
- The viscous CFL is removed from the explicit list by the implicit/DC viscous
  treatment.
- Nonuniform residuals can still require a conservative cap even when PPE and
  viscosity are implicit or elliptic.
- `dt_disc` should be interpreted as an operator-residual safety guard, not as
  a new physical wave-speed formula.

## Paper-Derived Rule

Use `dt_disc` only for explicit/extrapolated residual spectra; do not relabel
it as projection or viscous CFL.
