---
ref_id: WIKI-L-057
title: "Ch14 Exact Theory Unit Tests PASS"
domain: code
status: ACTIVE
tags: [ch14, q_manifold, phase_region, exact_tests, theory_consistency]
sources:
  - path: artifacts/A/ch14_exact_theory_unit_tests_CHK-RA-CH14-VAR-027.md
    description: "Exact-reference unit test artifact"
  - path: src/twophase/tests/test_q_manifold_projection.py
    description: "Graph and closed-polygon exact geometry tests"
  - path: src/twophase/tests/test_phase_region_admission.py
    description: "Closed-form KKT test"
  - path: src/twophase/tests/test_phase_region_measure.py
    description: "Gas-owner complement measurement test"
depends_on:
  - "[[WIKI-L-056]]"
  - "[[WIKI-E-071]]"
consumers:
  - domain: code
    usage: "Use before changing q-manifold, PhaseRegion measurement, or KKT admission tests"
  - domain: experiment
    usage: "Use before runtime dry-run or force-coupling probes"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Exact Theory Unit Tests PASS

## Knowledge Card

Ch14 q-manifold and PhaseRegion tests now include exact theoretical references:

```text
constant graph exact q
regular polygon exact area/length and radial variations
weighted regularized constrained KKT closed-form solve
gas-owner q_g = cell_area - q_l complement
```

These tests make theory consistency part of the unit gate, not only an oracle
or visual-inspection condition.

## Validation

Remote test:

```text
make test PYTEST_ARGS='twophase/tests/test_q_manifold_projection.py twophase/tests/test_phase_region_admission.py twophase/tests/test_phase_region_measure.py -q'
```

Result:

```text
825 passed, 35 skipped
```

## Boundary

This is test hardening only.  It does not authorize runtime adapters, force
coupling, pressure/velocity coupling, micro-stepping, or T/8.
