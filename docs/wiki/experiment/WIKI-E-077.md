---
ref_id: WIKI-E-077
title: "Ch14 PhaseRegion Capillary Graph Dry-Run PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, capillary_wave, graph_chart, gas_above, dry_run, exact_measure, finite_difference]
sources:
  - path: artifacts/A/ch14_phase_region_capillary_graph_dry_run_CHK-RA-CH14-VAR-052.md
    description: "Command log, metrics, implementation scope, and verdict for the capillary graph PhaseRegion dry run"
  - path: experiment/ch14/diagnose_phase_region_capillary_graph_dry_run_adapter.py
    description: "Diagnostic adapter that maps Ch14 capillary-wave q_l to PhaseRegion GAS_ABOVE graph q_g"
  - path: src/twophase/tests/test_phase_region_measure.py
    description: "Nonuniform-grid exact complement and graph dE finite-difference unit test"
depends_on:
  - "[[WIKI-T-176]]"
  - "[[WIKI-T-177]]"
  - "[[WIKI-L-059]]"
  - "[[WIKI-E-072]]"
  - "[[WIKI-E-076]]"
consumers:
  - domain: experiment
    usage: "Use before claiming the PhaseRegion scheme treats capillary waves and droplets through one owner route"
  - domain: code
    usage: "Use before implementing the graph-chart counterpart of the PhaseRegion G0--G5 face-force path"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Capillary Graph Dry-Run PASS

## Knowledge Card

The capillary wave is now admitted through the PhaseRegion graph-owner route.
The Ch14 YAML graph is interpreted as liquid below the interface, then mapped
to the PhaseRegion gas owner by the exact finite-volume complement:

```text
q_g = |C| - q_l
Gamma_h = graph eta(x)
PhaseRegion component = GAS_ABOVE / GRAPH_PERIODIC / TOP
E_h = sigma * Perimeter(Gamma_h)
```

The dry run proves that the capillary wave is not only an old graph-runtime
special case.  It passes the same PhaseRegion measurement boundary as the
closed droplet dry-run adapters: explicit phase ownership, atlas component,
cell capacity checks, residual report, perimeter, and visible
`force_admissible=0`.

## Evidence

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_dry_run_adapter.py
```

Result:

```text
phase_region_graph_admitted = 1
complement_used             = 1
gas_target_volume           = 2.000000000000e-04
gas_physical_volume         = 2.000000000000e-04
residual_l2                 = 0.000000000000e+00
runtime_graph_q_linf        = 0.000000000000e+00
column_height_linf          = 4.510281037540e-17
dE_dmode_abs_error          = 4.758186900045e-12
force_sign_product          = -1.128342698667e-03
perimeter                   = 2.007772098404e-02
force_admissible            = 0
```

Unit validation added an explicitly nonuniform graph complement test in
`test_phase_region_measure.py`.  Remote validation with the corrected test
path completed with `867 passed, 35 skipped`.

## Boundary

This is not a production force-coupling PASS.  The result is an owner/admission
PASS for graph capillary waves:

```text
runtime q_l -> PhaseRegion q_g -> GAS_ABOVE graph atlas -> q/E/dE checks
```

The next unification gate is the graph-chart version of the G0--G5
pressure/velocity face-cochain path.  Until that exists, do not claim that the
generic PhaseRegion scheme has advanced capillary-wave runtime dynamics through
the same force consumer as the closed droplet chart.
