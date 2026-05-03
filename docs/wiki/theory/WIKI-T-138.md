---
ref_id: WIKI-T-138
title: "Jump-Corrected Nonuniform Faces Must Share H_f"
domain: theory
status: ACTIVE
superseded_by: null
tags: [pressure_jump, nonuniform_grid, face_contract, ppe, velocity_correction]
sources:
  - path: paper/sections/09f_pressure_summary.tex
    description: "Nonuniform jump-corrected face-gradient contract using shared H_f and face coefficients"
depends_on:
  - "[[WIKI-T-130]]"
  - "[[WIKI-T-131]]"
  - "[[WIKI-T-137]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# Shared H_f Jump Faces

## Knowledge Card

The nonuniform jump-corrected face gradient is a shared face-flux contract:

```text
G_Gamma,f^nu = G_f^nu - B_f^nu
B_f^nu       = s_f j_f / H_f
```

The same `H_f`, face coefficients, nonuniform divergence, and correction face
operator must be used in the PPE right-hand side and in the final velocity
correction.  Otherwise the jump term is inserted in one operator and removed by
another, leaving a balanced-force residual.

## Consequences

- The jump correction is not capillary-wave-specific; it applies to the same
  oriented pressure jump in droplets, bubbles, capillary waves, and RT cases.
- `H_f` is part of the pressure-jump operator, not a plotting or diagnostics
  detail.
- Nonuniform projection tests must check face-coefficient sharing, not only the
  algebraic sign of `j_f`.
- A correct pressure jump can still be wrong if PPE and correction faces use
  different geometry.

## Paper-Derived Rule

Treat `B_f = s_f j_f / H_f` as a face-local operator object that must be reused
unchanged by both PPE assembly and velocity correction.
