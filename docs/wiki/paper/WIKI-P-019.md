---
ref_id: WIKI-P-019
title: "Chapter 14 Active-Geometry Capillary Benchmark Paper Contract"
domain: paper
status: ACTIVE
tags: [paper, chapter14, active_geometry_capillary, capillary_wave, benchmark, v11]
sources:
  - path: paper/sections/14_benchmarks.tex
    description: "Current Chapter 14 N32 one-period active-geometry capillary-wave benchmark"
  - path: paper/sections/13e2_ao_capillary_split_gate.tex
    description: "V11 integration gate connecting active-geometry capillary to physical benchmarks"
  - path: paper/sections/12u12_ao_capillary_split_gate.tex
    description: "U12 component pre-gate and overprojection counterexample"
  - path: docs/wiki/experiment/WIKI-E-063.md
    description: "Current U12/V11 experiment reading rule"
  - path: docs/wiki/cross-domain/WIKI-X-054.md
    description: "Session synthesis of final active-geometry capillary contracts"
depends_on:
  - "[[WIKI-P-018]]"
  - "[[WIKI-E-063]]"
  - "[[WIKI-X-054]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-T-173]]"
consumers:
  - domain: paper
    usage: "Use before editing Chapter 14 capillary-wave benchmark claims"
  - domain: experiment
    usage: "Use to separate U12/V11 gates from Chapter 14 physical benchmark evidence"
  - domain: code
    usage: "Use as the paper-facing acceptance boundary for active-geometry capillary route changes"
compiled_by: ResearchArchitect
compiled_at: 2026-05-16
---

# Chapter 14 Active-Geometry Capillary Benchmark Paper Contract

## Knowledge Card

Chapter 14 now contains a physical one-period capillary-wave benchmark for the
active-geometry capillary route.  The paper claim is deliberately narrower than
"the N32 waveform equals the continuum solution after one period."  The
finite-depth dispersion relation is the continuum phase clock; the numerical
claim is that the admitted active-geometry route produces restoring capillary
motion, bounded kinetic energy, regular fitted-grid geometry, and
roundoff-level q-volume conservation over one period.

## Paper Reading

The benchmark is valid only after the earlier gates are satisfied:

```text
U12: component/admission gate and full-pressure overprojection counterexample
V11: integration gate for graph HFE, face bridge, pressure history, moving
     face cochains, regular stratum, and DC convergence
Ch14: physical one-period benchmark using the admitted route
```

Do not move a Chapter 14 plot or number into the paper as a standalone proof of
the algorithm.  Chapter 14 is downstream of U12/V11.

## Current Published Values

The current N32 capillary-wave run uses the real-scale water--air parameters in
`paper/sections/14_benchmarks.tex`, with

```text
T = T_sigma = 0.046742983863 s
samples = 2585
initial signed amplitude = 2.002821e-4 m
quarter-period signed amplitude = 1.574613e-5 m
final signed amplitude = 1.590461e-4 m
final signed-amplitude ratio = 0.794
max kinetic energy = 8.2924e-6
final kinetic energy = 1.1434e-6
final volume drift = 1.4772e-14
max volume drift = 5.7192e-14
final dy_min = 3.9198e-4 m
```

The paper figures paired to these values are:

- `ch14_capillary_signed_interface_amplitude.pdf`;
- `ch14_capillary_kinetic_energy.pdf`;
- `ch14_capillary_volume_drift.pdf`;
- five `psi`, velocity, and pressure/Hodge-representative snapshots at
  `0`, `T/4`, `T/2`, `3T/4`, and `T`.

Pressure plots must use the Hodge/gauge representative reading described in
Chapter 14; raw absolute pressure color collapse is not the physical
observable.

## Wording Guardrails

Use these phrases or equivalents:

- finite-depth dispersion is a phase-time reference;
- q-owned graph surface energy and graph HFE jump;
- pressure-reaction component and Hodge-divided face bridge;
- projected face-cochain transport across moving-grid epochs;
- smooth pressure-history coordinate;
- DC residual convergence gate;
- one-period restoring/bounded/conservative benchmark.

Avoid these claims:

- exact N32 continuum waveform return;
- success of the full pressure-image split;
- generic P1 cut-cell surface work for a `column_height_graph` gauge;
- nodal velocity remap as projected face-cochain transport;
- pressure magnitude plots as absolute physical pressure;
- solver-family substitution, damping, smoothing, or CFL tuning as the
  explanation for the benchmark.

## Update Rule

If a future code change alters graph HFE, pressure-reaction space,
boundary-face space, affine low-order DC coefficients, moving-grid face
cochain transfer, or the capillary benchmark numbers, update this card,
[[WIKI-E-063]], [[WIKI-X-054]], and the Chapter 14 paper text together.
