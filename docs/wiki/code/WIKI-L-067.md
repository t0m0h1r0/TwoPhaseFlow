---
ref_id: WIKI-L-067
title: "Ch14 Pressure/Velocity Work-Gate Design"
domain: code
status: ACTIVE
tags: [ch14, phase_region, pressure_velocity, work_gate, no_t8]
sources:
  - path: artifacts/A/ch14_pressure_velocity_work_gate_design_CHK-RA-CH14-VAR-041.md
    description: "Pressure/velocity work-gate design before force consumption"
depends_on:
  - "[[WIKI-L-066]]"
consumers:
  - domain: code
    usage: "Use before implementing any pressure/velocity work-gate oracle"
  - domain: experiment
    usage: "Use before any micro-step or T/8 runtime probe"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Pressure/Velocity Work-Gate Design

## Knowledge Card

The PhaseRegion cochain is already a face object:

```text
s_f = -M_f^{-1} T_h^* dE_h
```

Existing `FCCDDivergenceOperator.project_faces(..., force_components=...)`
treats force input as nodal components and calls `face_fluxes(...)`.  Therefore
passing `s_f` there is forbidden.

## Next Gate

Implement a diagnostic-only work gate that proves:

```text
shape(s_f) == shape(u_f) == shape(p_f)
same boundary_face_space
same face mass metric M_f
same FCCD divergence/pressure face space
```

Only after that may a zero-step face-level projection oracle use
`apply_pressure_projection(u_faces, p_faces, s_faces, dt)`.

## Boundary

No pressure/velocity coupling, production force route, micro-step, or T/8 is
authorized by this card.
