---
ref_id: WIKI-E-054
title: "V8/V9/V10 Preserve Future Gates by Design"
domain: experiment
status: ACTIVE
superseded_by: null
tags: [chapter13, v8, v9, v10, nonuniform_grid, future_gate]
sources:
  - path: paper/sections/13e_nonuniform_ns.tex
    description: "Scope limits for V8 fixed nonuniform static droplet, V9 epsilon switch, and V10 CLS advection"
depends_on:
  - "[[WIKI-T-135]]"
  - "[[WIKI-E-042]]"
  - "[[WIKI-E-043]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-04
---

# V8/V9/V10 Scope Guards

## Knowledge Card

V8, V9, and V10 are deliberately scoped diagnostics that preserve future gates
instead of overclaiming current coverage.

Their scope is:

```text
V8  : fixed nonuniform static droplet
V9  : local-epsilon switch diagnostic under the later stack
V10 : fixed uniform-grid CLS strong-deformation advection
```

## Consequences

- V8 is not yet a moving-interface nonuniform production validation.
- V9 does not prove local epsilon is universally superior; nominal and local
  epsilon can coincide in the direct-psi/HFE path.
- V10 is not a nonuniform moving-interface NS-coupled benchmark.
- These experiments mark what remains to be gated rather than hiding the open
  validation boundary.

## Paper-Derived Rule

Read V8/V9/V10 as scoped diagnostic gates with explicit future work preserved,
not as blanket closure of nonuniform moving-interface validation.
