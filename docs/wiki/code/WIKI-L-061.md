---
ref_id: WIKI-L-061
title: "Ch14 PhaseRegion Force-Admission Helpers PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, force_admission, face_metric, fixed_stratum, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_admission_helpers_CHK-RA-CH14-VAR-035.md
    description: "Force-admission helper implementation and validation"
  - path: src/twophase/coupling/phase_region_force_admission.py
    description: "Contract helper module"
depends_on:
  - "[[WIKI-L-060]]"
  - "[[WIKI-E-075]]"
consumers:
  - domain: code
    usage: "Use before building a zero-step PhaseRegionForceAdmission candidate object"
  - domain: experiment
    usage: "Use before refactoring runtime force dry-runs or adapter diagnostics"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force-Admission Helpers PASS

## Knowledge Card

The PhaseRegion force-adapter boundary now has contract-level helpers for the
two reusable pieces that must not be hidden in experiments:

```text
rho = rho_g + (rho_l-rho_g) psi
M_f = face_mass_components(grid, rho_node)
eps ||T_h(scale u_f)||_inf <= sign_fraction min|psi-0.5|
```

The helper rejects cell-density shaped `psi` for face metrics and returns
`valid=false` when the fixed-stratum sign margin is zero.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
834 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
self_fd_power_residual  = 2.481405282624e-07
probe_fd_power_residual = 2.481363539023e-07
force_admissible        = 0.0
```

## Boundary

This is not a production capillary force route.  It provides pure helper
contracts for a future zero-step candidate object.  Pressure/velocity coupling,
nonlinear optimization, micro-stepping, and T/8 remain outside this gate.
