---
ref_id: WIKI-E-060
title: "Pressure Oscillation RCA Must Separate Force Cochains from Plot Representatives"
domain: experiment
status: ACTIVE
tags: [pressure_oscillation, hodge_pressure, affine_jump, diagnostics]
sources:
  - path: paper/sections/13f_error_budget.tex
  - path: paper/sections/14_benchmarks.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# Pressure Oscillation RCA Must Separate Force Cochains from Plot Representatives

## Claim

Interface pressure oscillations are not one diagnosis.  The RCA must separately
test projection residual, face pressure acceleration, bulk phase pressure, and
the plotted scalar representative.

## Effective Knowledge

- After affine pressure-history face closure, the face acceleration and bulk
  pressure contrast stayed bounded in short N64 gates.
- After DC residual convergence, residual projection error was removed as the
  leading explanation.
- Hodge/bulk pressure representatives then became the correct way to inspect
  scalar output.

## Negative Knowledge

Raw nodal pressure plots in the diffuse band can remain visually oscillatory.
That image is not enough to claim that surface tension is physically wrong.

## Implication

Pressure RCA should be ordered: solve residual, inspect face cochains, inspect
bulk/Hodge representatives, and only then revisit curvature or variational
surface-energy closure.
