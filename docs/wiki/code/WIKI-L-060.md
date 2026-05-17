---
ref_id: WIKI-L-060
title: "Ch14 PhaseRegion Force Adapter Boundary Design"
domain: code
status: ACTIVE
tags: [ch14, phase_region, force_adapter, runtime_boundary, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_adapter_design_CHK-RA-CH14-VAR-034.md
    description: "Production-adjacent force adapter boundary design"
depends_on:
  - "[[WIKI-L-059]]"
  - "[[WIKI-E-075]]"
  - "[[WIKI-E-074]]"
consumers:
  - domain: code
    usage: "Use before writing any PhaseRegion runtime force adapter helper"
  - domain: experiment
    usage: "Use before any pressure/velocity coupling, micro-step, or T/8 probe"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force Adapter Boundary Design

## Knowledge Card

The future PhaseRegion force adapter must be a candidate builder, not a hidden
runtime force route.  It may collect the zero-step runtime ingredients:

```text
q_g = |C| - q_l
psi = H(-phi)
M_f from nodal runtime density
s_f = -M_f^{-1} T_h^T dE_h
```

but it must keep `force_admissible = false` until a later pressure/velocity
consumer proves it uses the same discrete metric and work pairing.

## Required Candidate Boundary

The safe object is:

```text
PhaseRegionForceAdmission
  owner_map
  psi_chart
  face_weight_components
  ClosedInterfaceRieszCochain
  VirtualWorkCheck diagnostics
  Hodge / reaction diagnostics
  metrics
  force_admissible = false
```

It must report runtime steps, compatibility residual, boundary/grid metadata,
face shapes, and whether the phase-owner complement was used.

## Nonuniform and Boundary Rule

Do not assume uniform `h`.  The adapter must derive cell areas, face measures,
and FCCD weights from the runtime grid.  Periodic/wall cases are chart
differences under the same variational identity, not separate special theories.

## Next Code Gate

The next permitted code unit is a small contract helper with tests for:

```text
q_l -> q_g exact complement
nodal-density face metric values and shapes
cell-density metric misuse failing closed
fixed-stratum velocity scaling inside sign margin
```

The existing runtime force dry-run must remain PASS.  Pressure/velocity
coupling, nonlinear optimization, micro-stepping, and T/8 remain forbidden.
