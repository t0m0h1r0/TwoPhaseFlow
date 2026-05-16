---
ref_id: WIKI-E-063
title: "U12/V11 Active-Geometry Capillary Split Gates"
domain: experiment
status: ACTIVE
tags: [active_geometry_capillary, capillary, fail_close, gpu, ch12, ch13, ch14]
sources:
  - path: paper/sections/12u12_ao_capillary_split_gate.tex
    description: "Current U12 active-geometry capillary pre-gate"
  - path: paper/sections/13e2_ao_capillary_split_gate.tex
    description: "Current V11 active-geometry capillary integration gate"
  - path: paper/sections/14_benchmarks.tex
    description: "Chapter 14 one-period capillary-wave benchmark connected to V11"
  - path: docs/wiki/cross-domain/WIKI-X-054.md
    description: "Session synthesis of final active-geometry capillary contracts"
  - path: artifacts/A/ch14_capillary_paper_refresh_CHK-RA-CODE-GPU-008.md
    description: "Latest one-period capillary paper refresh"
depends_on:
  - "[[WIKI-T-169]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-T-173]]"
  - "[[WIKI-X-054]]"
consumers:
  - domain: experiment
    usage: "Use before treating an active-geometry capillary run as a physical benchmark"
  - domain: paper
    usage: "Use for U12/V11 wording and for separating diagnostic gates from Chapter 14 physics claims"
  - domain: code
    usage: "Use as acceptance evidence for fail-close boundaries, graph-HFE admission, and one-period benchmark connection"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# U12/V11 Active-Geometry Capillary Split Gates

## Current Reading

The first U12/V11 AO-Fast split checks were negative/admission gates: they
proved that projecting the capillary covector onto the full pressure image can
erase non-static capillary-wave drive exactly.  That result is still important
negative knowledge, but it is no longer the final reading of the active route.

The current U12/V11 gate stack admits only the route that simultaneously
preserves:

```text
q-owned graph surface energy
  -> current graph HFE jump
  -> pressure-reaction component space R_p
  -> Hodge-divided projection-face bridge
  -> moving-grid projected face-cochain transport
  -> smooth pressure-history coordinate
  -> regular-stratum grid guard
  -> DC residual convergence gate.
```

Chapter 14 capillary-wave claims must be read through this gate stack.  The
old full-pressure-image cancellation is a counterexample, not the adopted
physical route.

## U12 Pre-Gate

U12 is a component gate.  It checks that the standard route is not polluted by
an overprojection or by a graph/gauge mismatch.

| Case | Observation | Reading |
|---|---|---|
| Flat interface | Exact split and component-volume Hodge diagnostic are both zero. | Static zero-drive condition passes. |
| N32 capillary wave | Full pressure-image split gives zero balanced drive; component-volume Hodge diagnostic is `2.1176`. | Full pressure image is an overprojection counterexample; non-staticity is detected. |
| N64 capillary wave | Full pressure-image split gives zero balanced drive; component-volume Hodge diagnostic is `2.3055`. | Same verdict under refinement. |
| Graph HFE jump | Nonuniform-x graph jump has `||j_gl^G||_inf=11.5323`, weighted mean `1.30e-16`, and negative crest jump. | Current graph HFE jump has the right conservation/sign contract. |
| HFE/history separation | Graph HFE jump is not stored as pressure-history coordinate; with `dt=1e-8`, spatial drive `1e-6` admits HFE even though increment norm is `1e-14`. | Admission is a spatial-drive contract, not a `dt`-scaled increment test. |
| Regular stratum | Nearly horizontal wave moves `y` by `2.50e-3` and leaves `x` displacement zero. | Interface retreat must not squeeze tangential grid widths. |
| Pending split boundary | Unaccepted approximate splits stop while retaining N32/N64 non-static drives `2.40e-5` / `2.32e-5`. | Unknown `R_p` is fail-closed, not silently accepted. |

## V11 Integration Gate

V11 connects U12 to the Chapter 13 integration grammar and Chapter 14 physical
benchmark.  It requires the U12 contracts plus the pressure-history and
moving-grid face-cochain contracts from [[WIKI-T-172]] and the capillary-wave
route from [[WIKI-T-173]].

The decisive 2026-05-16 addition is the one-period integration connection:
the N32 capillary wave reached

```text
T_sigma = 0.046742983863 s
samples = 2585
max volume drift = 5.7192e-14
final volume drift = 1.4772e-14
max kinetic energy = 8.2924e-6
final kinetic energy = 1.1434e-6
final signed-amplitude ratio = 0.794
final dy_min = 3.9198e-4 m
```

This result connects V11 to the physical benchmark, but it does not turn the
old full-pressure-image split into a success route.  The benchmark is evidence
for the active-geometry route only because the graph HFE, face bridge, moving
face-cochain, pressure-history, regular-stratum, and DC convergence gates are
all part of the same route.

## Experiment Reading Rule

Use this card as a filter:

- cite U12 for component/admission contracts and overprojection negative
  knowledge;
- cite V11 for integration acceptance boundaries;
- cite Chapter 14 only for the physical one-period capillary result after the
  U12/V11 gates are satisfied;
- do not cite `experiment/ch13/exp_V11_common_flux_admissibility.py` as an
  active-geometry capillary pass.

## Negative Knowledge

Do not use these as active-geometry capillary fixes:

- full pressure-image cancellation of a non-static wave;
- component-volume Hodge as a substitute for the final `R_p`;
- hidden PCG/DC/dense CPU fallback;
- accepting an unknown pressure-reaction split because a packet produces a
  finite number;
- carrying graph HFE jump as smooth pressure history;
- rebuilding projected face flow from nodal interpolation alone;
- disabling nonuniform grids, interface-following rebuilds, HFE, or DC
  convergence gates to make a run advance.
