---
ref_id: WIKI-L-054
title: "Ch14 PhaseRegion Boundary and Nonuniform Audit PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, boundary, nonuniform, audit, fail_closed]
sources:
  - path: artifacts/A/ch14_phase_region_boundary_nonuniform_audit_CHK-RA-CH14-VAR-022.md
    description: "Boundary/nonuniform audit, fixes, theory check, and validation"
  - path: src/twophase/geometry/interface_atlas.py
    description: "Boundary attachment validation"
  - path: src/twophase/geometry/phase_region_measure.py
    description: "Component q physical measure validation"
  - path: src/twophase/geometry/phase_region_admission.py
    description: "Low-mode KKT fail-closed validation"
  - path: experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py
    description: "Uniform and alpha_grid=2 smoke oracle"
depends_on:
  - "[[WIKI-L-053]]"
  - "[[WIKI-E-069]]"
consumers:
  - domain: code
    usage: "Use before chart-specific nonuniform F0/F1 admission"
  - domain: experiment
    usage: "Use before boundary/nonuniform atlas admission probes"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Boundary and Nonuniform Audit PASS

## Knowledge Card

The audit hardened three fail-closed boundaries:

- graph/open components must declare boundary attachment;
- component q must be a physical cell measure before reduction;
- low-mode KKT systems must be nonsingular and use symmetric PSD energy
  Hessians.

The atlas smoke oracle now accepts `--alpha-grid` and passes at `alpha_grid=2`.

## Validation

Remote tests:

```text
818 passed, 35 skipped
```

Smoke oracles:

- `alpha_grid=1.0`: PASS;
- `alpha_grid=2.0`: PASS;
- `force_admissible = 0.0` in both.

## Residual Risk

This does not make `project_column_height_to_graph` nonuniform-ready.  That
helper still requires uniform x spacing and must not be used as nonuniform
atlas F0 admission.

