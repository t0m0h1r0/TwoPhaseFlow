---
ref_id: WIKI-L-053
title: "Ch14 PhaseRegion Low-Mode KKT PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, admission, low_mode, kkt, fast_projection]
sources:
  - path: artifacts/A/ch14_phase_region_low_mode_kkt_CHK-RA-CH14-VAR-021.md
    description: "Module D implementation, review, theory check, and validation"
  - path: src/twophase/geometry/phase_region_admission.py
    description: "Low-mode F1 KKT helper"
  - path: src/twophase/tests/test_phase_region_admission.py
    description: "Low-mode KKT tests"
depends_on:
  - "[[WIKI-L-052]]"
  - "[[WIKI-L-050]]"
consumers:
  - domain: code
    usage: "Use before implementing chart-specific atlas F0/F1 admission"
  - domain: experiment
    usage: "Use before F1 atlas admission probes"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Low-Mode KKT PASS

## Knowledge Card

`solve_low_mode_kkt` implements the F1 fast-admission kernel:

```text
min_delta 1/2 ||J_Q delta - r||_W^2
          + 1/2 alpha delta^T H_E delta
subject to J_C delta = c
```

It solves only over admitted low modes, supports batched small systems, and
returns `force_admissible = false`.

## Validation

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_admission.py -q'
```

Result:

```text
817 passed, 35 skipped
```

## Usage

Use this as the F1 kernel after an F0 chart/moment proposal exists.  It does
not choose charts, construct `J_Q`, make all-cell q exact, run nonlinear
optimization, or authorize force coupling.

