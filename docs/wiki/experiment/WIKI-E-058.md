---
ref_id: WIKI-E-058
title: "N64 Alpha-2 Long Runs Need Short Projection and Geometry Gates First"
domain: experiment
status: ACTIVE
tags: [ch14, n64_alpha2, oscillating_droplet, short_gate]
sources:
  - path: experiment/ch14/config/ch14_oscillating_droplet.yaml
  - path: docs/memo/short_paper/SP-AC_ale_discrete_gradient_capillary_work.md
  - path: paper/sections/14_benchmarks.tex
  - path: docs/02_ACTIVE_LEDGER.md
---

# N64 Alpha-2 Long Runs Need Short Projection and Geometry Gates First

## Claim

A one-period N64 alpha-2 oscillating droplet run should be launched only after
short gates have separated projection residual, pressure representative,
volume drift, and deformation behavior.

## Effective Knowledge

- `T=0.25` and `T=1` gates with DC12 reached projection residual convergence,
  small volume drift, and bounded signed deformation.
- Snapshot cadence and pressure representative choice must be fixed before the
  long run, because post-hoc plots can otherwise misread raw pressure.
- The one-period run is expensive enough that every long launch should derive
  its temporary diagnostic config from the canonical oscillating-droplet YAML
  and inherit the last short-gate diagnostics. The result identity may keep a
  descriptive N64 alpha-2 name, but the variant YAML is not checked in.

## Negative Knowledge

The initial foreground one-period attempt consumed about two hours and reached
only early time.  Long execution without short gates wastes wall time and does
not clarify the physical failure mechanism.

## Implication

Treat short gates as part of the mathematical validation protocol, not as
performance shortcuts.
