---
ref_id: WIKI-L-062
title: "Ch14 PhaseRegion Force-Admission Candidate PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, force_admission, candidate, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_admission_candidate_CHK-RA-CH14-VAR-036.md
    description: "Force-admission candidate implementation and validation"
  - path: src/twophase/coupling/phase_region_force_admission.py
    description: "Candidate builder and helper module"
depends_on:
  - "[[WIKI-L-061]]"
  - "[[WIKI-L-060]]"
consumers:
  - domain: code
    usage: "Use before adding diagnostic work/Hodge payloads or runtime adapter experiments"
  - domain: experiment
    usage: "Use before any zero-step adapter diagnostic around PhaseRegion force candidates"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force-Admission Candidate PASS

## Knowledge Card

`PhaseRegionForceAdmission` is now the explicit zero-step candidate object for
PhaseRegion runtime force work.  It gathers:

```text
owner_map
face_metric
closed-interface Riesz cochain
metrics
valid / reason
force_admissible = false
```

The builder fails closed when `runtime_steps != 0`, when the phase owner map is
invalid, when `psi` is cell-shaped instead of nodal, or when the closed
interface stratum is irregular.

## Validation

Remote tests:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_force_admission.py -q'
837 passed, 35 skipped
```

Runtime dry-run regression:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_runtime_force_dry_run.py
force_admissible = 0.0
```

## Boundary

This object is still not a production force path.  It separates "candidate was
built" from "force may be consumed".  Pressure/velocity coupling, nonlinear
optimization, micro-stepping, and T/8 remain outside this gate.
