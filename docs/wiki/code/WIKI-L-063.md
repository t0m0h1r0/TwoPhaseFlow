---
ref_id: WIKI-L-063
title: "Ch14 PhaseRegion Force Diagnostics Payload PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, force_admission, diagnostics, hodge, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_diagnostics_payload_CHK-RA-CH14-VAR-037.md
    description: "Diagnostic payload implementation and validation"
  - path: src/twophase/coupling/phase_region_force_admission.py
    description: "Candidate and diagnostics helper module"
depends_on:
  - "[[WIKI-L-062]]"
  - "[[WIKI-E-075]]"
consumers:
  - domain: code
    usage: "Use before building candidate-focused zero-step adapter diagnostics"
  - domain: experiment
    usage: "Use before refactoring runtime force dry-runs around PhaseRegionForceAdmission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force Diagnostics Payload PASS

## Knowledge Card

`PhaseRegionForceAdmission` now carries optional zero-step diagnostics:

```text
PhaseRegionForceDiagnostics
  self/probe fixed-stratum work checks
  weighted Hodge decomposition
  component-reaction residual
  scalar metrics
  diagnostics.valid / reason
```

The payload keeps `force_admissible=false` and fails closed for invalid
candidates.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
839 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
force_admissible = 0.0
```

## Boundary

This is still a zero-step diagnostic object.  It does not connect to
pressure/velocity projection, nonlinear optimization, micro-stepping, or T/8.
