---
ref_id: WIKI-L-059
title: "Ch14 Phase-Owner Map PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, runtime_admission, owner_map, q_measure]
sources:
  - path: artifacts/A/ch14_phase_owner_map_CHK-RA-CH14-VAR-029.md
    description: "Phase-owner map implementation, review, theory check, and validation"
  - path: src/twophase/geometry/phase_owner_map.py
    description: "Explicit finite-volume phase-owner conversion helper"
  - path: src/twophase/tests/test_phase_owner_map.py
    description: "Owner-map exact complement and fail-closed tests"
  - path: src/twophase/tests/test_phase_region_measure.py
    description: "PhaseRegion measurement complement test now uses owner map"
depends_on:
  - "[[WIKI-E-071]]"
  - "[[WIKI-L-052]]"
consumers:
  - domain: code
    usage: "Use before implementing a PhaseRegion runtime dry-run adapter"
  - domain: experiment
    usage: "Use before runtime admission probes that consume GeometricPhaseState.q"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 Phase-Owner Map PASS

## Knowledge Card

The liquid/gas owner mismatch is now represented by an explicit helper:

```text
runtime q_l = |Omega_l cap C|
PhaseRegion q_g = |C| - q_l
```

`map_cell_measure_to_phase_owner` returns `q_owner` with declared
`source_phase`, declared `owner_phase`, visible `complement_used`, volumes,
and capacity diagnostics.  Matching phases pass through without a hidden
complement.  Cross-phase conversion uses only the exact finite-volume
complement and fails closed on negative q, over-capacity q, invalid shapes,
invalid phase labels, or invalid tolerance.

The existing gas-owner PhaseRegion measurement test now obtains its gas target
through this owner map before calling `assemble_phase_region_measurement`.

## Validation

Remote test:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_owner_map.py twophase/tests/test_phase_region_measure.py -q'
```

Result:

```text
829 passed, 35 skipped
```

## Boundary

This unblocks the owner-map prerequisite for a runtime dry-run adapter.  It
does not authorize force coupling, pressure/velocity coupling, nonlinear
optimization, micro-stepping, or T/8.
