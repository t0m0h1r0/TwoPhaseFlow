---
ref_id: WIKI-L-037
title: "Backend Boundary Owns Host, Device, and Scalar Conversion"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, cupy, backend, host_device, scalar_boundary, diagnostics]
sources:
  - path: docs/memo/CHK-RA-SRC-005_src_architecture_plan_20260503.md
    description: "src architecture plan and backend boundary"
  - path: docs/memo/CHK-RA-SRC-MAJOR-ROUNDS-001_src_major_rounds.md
    description: "GPU hot-path and host-transfer audit"
depends_on:
  - "[[WIKI-L-015]]"
  - "[[WIKI-L-026]]"
  - "[[WIKI-L-035]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# Backend Boundary

## Knowledge Card

CPU/GPU namespace choice, host transfer, device detection, and Python scalar
conversion belong at the backend boundary.  Solver modules should not invent
ad hoc `xp`, `.get()`, `float(device_array)`, or host-conversion policy.

Diagnostics may eventually become host scalars, but reductions should remain
device-side until an explicit final scalar or serialization boundary.

## Consequences

- A Python `bool` predicate over device arrays is a synchronization point and
  must be guarded or kept outside GPU hot paths.
- Canonical host metadata should remain host metadata; converting it to device
  and immediately asking Python for a truth value adds avoidable sync.
- Production modules receive already-built dependencies from builders; hot
  paths should not perform construction or backend dispatch.
- GPU execution is a reproducibility/implementation contract, not a new
  scientific claim.

## Paper-Derived Rule

Put all host/device and scalar-conversion decisions behind `twophase.backend`
or an explicit diagnostic/output boundary.
