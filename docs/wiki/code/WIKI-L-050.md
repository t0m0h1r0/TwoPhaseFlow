---
ref_id: WIKI-L-050
title: "Ch14 PhaseRegion InterfaceAtlas Implementation Design"
domain: code
status: ACTIVE
tags: [ch14, phase_region, interface_atlas, implementation_design, vectorization, fast_projection]
sources:
  - path: artifacts/A/ch14_phase_region_atlas_implementation_design_CHK-RA-CH14-VAR-017.md
    description: "No-code implementation design for vectorized PhaseRegion/InterfaceAtlas admission"
depends_on:
  - "[[WIKI-T-177]]"
  - "[[WIKI-T-176]]"
  - "[[WIKI-L-049]]"
consumers:
  - domain: code
    usage: "Use before adding PhaseRegion, InterfaceAtlas, or atlas projection code"
  - domain: experiment
    usage: "Use before the closed bubble + top layer atlas smoke oracle"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion InterfaceAtlas Implementation Design

## Knowledge Card

The next implementation must be `PhaseRegionBatch` primary:

```text
R_h = PhaseRegionBatch(components, charts, constraints, metric_epoch)
q_phys = Q_h(R_h)
r = q_T - q_phys
E_h = sigma sum_c perimeter(component_c)
```

The batch layout is component-major and packed-ragged: chart labels,
attachments, orientation, phase role, constraint policy, dof offsets, vertex
offsets, and active-cell offsets are arrays.  Dense `q_component[nc,nx,ny]`
arrays are allowed for small oracles; runtime-facing code should use
active-band sparse reductions.

## Fast Admission Policy

Do not make full nonlinear projection the runtime default.

Use this ladder:

1. `F0`: direct moment projection from `q_T` to low graph/closed/open chart
   modes, followed by exact total-volume correction.
2. `F1`: one small linearized KKT solve over admitted chart modes and declared
   constraints.
3. `F2`: one guarded low-mode correction only if residual and energy checks
   agree with the linear prediction.
4. `F3`: full nonlinear optimization only for oracle or fail-close diagnosis.

The residual `r` remains a reported non-geometric measure component.  It is not
converted into curvature or force.

## Next Gate

Build the closed bubble + top layer atlas smoke oracle before force coupling
or T/8.  It must visualize the components, `q_phys`, synthetic `q_T`, and `r`,
and must check topology, attachment, orientation, phase ownership, total volume,
perimeter sum, finite-difference covectors, and scalar-vs-batch parity.

