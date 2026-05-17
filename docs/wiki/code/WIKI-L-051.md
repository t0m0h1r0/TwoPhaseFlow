---
ref_id: WIKI-L-051
title: "Ch14 PhaseRegion InterfaceAtlas Schema PASS"
domain: code
status: ACTIVE
tags: [ch14, phase_region, interface_atlas, schema, validation, vectorization]
sources:
  - path: artifacts/A/ch14_phase_region_atlas_schema_CHK-RA-CH14-VAR-018.md
    description: "Module A implementation, review, theory check, and validation"
  - path: src/twophase/geometry/interface_atlas.py
    description: "PhaseRegionBatch and InterfaceAtlas schema implementation"
  - path: src/twophase/tests/test_phase_region_atlas.py
    description: "Schema validation and packed-layout tests"
depends_on:
  - "[[WIKI-L-050]]"
  - "[[WIKI-T-177]]"
consumers:
  - domain: code
    usage: "Use before implementing atlas Q_h, perimeter reductions, or admission"
  - domain: experiment
    usage: "Use before the closed bubble + top layer atlas smoke oracle"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion InterfaceAtlas Schema PASS

## Knowledge Card

Module A adds the owner schema:

```text
R_h = PhaseRegionBatch(InterfaceAtlas, dofs, vertices, active cells)
```

The implementation is validation-only.  It does not add `Q_h`, perimeter
reductions, residual splitting, runtime adapters, force coupling, or T/8.

The atlas is component-major and packed by batch.  Labels and offsets are
integer-valued, orientations are `+1/-1`, closed components cannot declare a
boundary attachment, and packed payload lengths must match their offsets.

## Validation

Command:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_atlas.py -q'
```

Result:

```text
809 passed, 35 skipped
```

## Next Gate

Use this card before building the closed bubble + top layer atlas smoke oracle.
That oracle may consume `PhaseRegionBatch`, but force coupling remains blocked
until `Q_h`, perimeter reductions, residual reports, and later `T_h^*` work
identities are proven separately.

