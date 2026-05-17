---
ref_id: WIKI-E-078
title: "Ch14 PhaseRegion Capillary Graph Few-Step PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, capillary_wave, graph_chart, few_step, variational, exact_solution, visualization]
sources:
  - path: artifacts/A/ch14_phase_region_capillary_graph_steps_CHK-RA-CH14-VAR-053.md
    description: "Command log, metrics, failed nonlinear-force attempt, and verdict for the few-step PhaseRegion graph experiment"
  - path: experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
    description: "Reduced PhaseRegion graph-chart capillary-wave stepper"
  - path: experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/data.npz
    description: "Remote few-step result data"
  - path: experiment/ch14/results/diagnose_phase_region_capillary_graph_steps/phase_region_capillary_graph_steps.pdf
    description: "Remote few-step visualization"
depends_on:
  - "[[WIKI-E-077]]"
  - "[[WIKI-T-176]]"
  - "[[WIKI-T-177]]"
consumers:
  - domain: experiment
    usage: "Use before extending the graph route from reduced PhaseRegion stepping to face-cochain pressure/velocity coupling"
  - domain: code
    usage: "Use before implementing graph-chart G0--G5 force admission"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Capillary Graph Few-Step PASS

## Knowledge Card

The PhaseRegion graph route now moves for a few capillary-wave steps.  The
state owner is still the graph/phase region, not a rebuilt `phi`:

```text
eta -> q_l = Q_h(eta)
q_g = |C| - q_l
PhaseRegionBatch(GAS_ABOVE graph)
E_h second variation -> modal mass and restoring force
```

The accepted few-step gate is deliberately linearized.  A first trial using
the full nonlinear perimeter derivative while comparing to the linear
capillary-wave exact solution failed the velocity reference check.  That was a
theory mismatch, not a tolerance problem: finite-amplitude nonlinear perimeter
induces a small nonlinear frequency shift.  The committed experiment uses
`K_h=d^2E_h/dA^2` from the same discrete graph energy, then compares to the
rigid-wall two-layer exact linear capillary wave.

## Evidence

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_capillary_graph_steps.py
```

Result:

```text
phase_region_graph_steps_admitted = 1
steps                             = 8
dt                                = 2.000000000000e-05
t_final                           = 1.600000000000e-04
t_over_T                          = 3.422973605371e-03
max_amplitude_error               = 2.785727377941e-14
max_velocity_error                = 3.482433087558e-10
max_energy_drift                  = 8.356546623106e-10
max_residual_l2                   = 0.000000000000e+00
max_volume_drift                  = 2.710505431214e-20
final_amplitude                   = 1.999537458869e-04
final_exact_amplitude             = 1.999537459147e-04
force_admissible                  = 0
```

Additional validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py -q'
```

The current remote make target ran the suite and passed with
`867 passed, 35 skipped`.

## Boundary

This is a reduced graph-chart dynamic experiment, not a production
Navier--Stokes capillary-force connection.  Keep `force_admissible=0` until the
graph-chart route has the same face-cochain pressure/velocity gates as the
closed chart:

```text
PhaseRegion graph dE
-> transport-adjoint face cochain
-> G0--G5 face-space/work/projection gates
-> controlled runtime micro-step
```

Do not use this PASS as evidence that T/8 runtime or dynamic nonuniform grid
history is solved.
