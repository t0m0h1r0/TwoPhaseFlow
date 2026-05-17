---
ref_id: WIKI-L-064
title: "Ch14 PhaseRegion Force Admission Report PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, force_admission, adapter_report, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_admission_report_CHK-RA-CH14-VAR-038.md
    description: "Admission report implementation and validation"
  - path: src/twophase/coupling/phase_region_force_admission.py
    description: "Candidate, diagnostics, and report helper module"
depends_on:
  - "[[WIKI-L-063]]"
consumers:
  - domain: code
    usage: "Use before adding a zero-step adapter consumer for PhaseRegion force candidates"
  - domain: experiment
    usage: "Use before any runtime report/adaptor experiment around PhaseRegion force candidates"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force Admission Report PASS

## Knowledge Card

`PhaseRegionForceAdmissionReport` is the adapter-facing zero-step report for a
force candidate.  It requires:

```text
candidate.valid
diagnostics.valid
runtime_steps == 0
force_admissible == false
required scalar metrics present
```

Missing diagnostics or required metrics fail closed with a reason string.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
843 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
force_admissible = 0.0
```

## Boundary

This is still a scalar diagnostic/report contract.  It does not connect a
capillary force to pressure/velocity projection, nonlinear optimization,
micro-stepping, or T/8.
