---
ref_id: WIKI-T-129
title: "Variable-Density PPE Is a Pressure-Increment Equation in IPC"
domain: theory
status: ACTIVE
superseded_by: null
tags: [ppe, ipc, variable_density, pressure_increment, projection]
sources:
  - path: paper/sections/08b_pressure.tex
    description: "Variable-density IPC derivation and pressure-increment PPE"
depends_on:
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-125]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# IPC Increment PPE

## Knowledge Card

The variable-density PPE in the paper is derived as an incremental pressure
correction equation.  The predictor includes the old pressure `p^n`, then the
projection solves for

```text
delta p = p^{n+1} - p^n
div( (1/rho^{n+1}) grad delta p ) = div u* / Delta t_proj
```

The pressure unknown in the elliptic solve is therefore tied to the projection
time width and to the already-updated density field.

## Consequences

- Mixing absolute-pressure and increment-pressure jump semantics is dangerous.
- The projection coefficient must use `rho^{n+1}` from the advanced interface.
- IPC lowers splitting error by carrying old pressure in the predictor.
- PPE diagnostics should report whether the stored pressure is absolute,
  correction, or post-update pressure.

## Paper-Derived Rule

In IPC, audit pressure-jump and output semantics against the solved unknown
`delta p`, not against a generic "pressure" label.
