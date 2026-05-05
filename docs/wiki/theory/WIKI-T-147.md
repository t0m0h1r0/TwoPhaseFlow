---
ref_id: WIKI-T-147
title: "IMEX-BDF2 Startup Is a State-Consistency Contract"
domain: theory
status: ACTIVE
superseded_by: null
tags: [imex_bdf2, ext2, startup, projection, time_integration]
sources:
  - path: paper/sections/07_time_integration.tex
    description: "BDF1 warmup and BDF2/EXT2 valid range"
  - path: paper/sections/11_full_algorithm.tex
    description: "One-step sequencing and projected-history storage"
  - path: paper/sections/appendix_e4_1_predictor_imex_bdf2.tex
    description: "Predictor IMEX-BDF2 details"
depends_on:
  - "[[WIKI-T-101]]"
  - "[[WIKI-T-125]]"
  - "[[WIKI-X-038]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-05
---

# IMEX-BDF2 Startup

## Knowledge Card

BDF2/EXT2 is a two-history method.  It is valid only after the solver has a
consistent projected history.  The first step must use a BDF1/backward-Euler
warmup, then store the projected state for subsequent EXT2 use.

The startup rule is part of the same causality contract as the main step:

```text
warmup with BDF1
project the velocity
store projected history
then enter BDF2/EXT2
```

The BDF1 startup error is accepted as a startup consistency cost; it is not a
license to seed BDF2 with unprojected or manufactured history.

## Consequences

- Time-order tests must identify whether the first step is included in the
  measured interval.
- History arrays must store projected velocities, not predictor velocities.
- The projection width `dt_proj = gamma dt` must remain consistent between PPE
  and corrector.
- Restart/checkpoint code has to restore enough projected history before
  resuming BDF2/EXT2.

## Paper-Derived Rule

Start IMEX-BDF2 through a projected BDF1 warmup; never fabricate the missing
history or seed it with `u*`.
