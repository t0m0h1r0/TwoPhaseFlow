---
ref_id: WIKI-E-079
title: "Ch14 PhaseRegion Oscillating Droplet Few-Step PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, oscillating_droplet, closed_chart, few_step, variational, exact_solution, visualization]
sources:
  - path: artifacts/A/ch14_phase_region_oscillating_droplet_steps_CHK-RA-CH14-VAR-054.md
    description: "Command log, metrics, and verdict for the few-step PhaseRegion closed-droplet experiment"
  - path: experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py
    description: "Reduced PhaseRegion closed-chart oscillating-droplet stepper"
  - path: experiment/ch14/results/diagnose_phase_region_oscillating_droplet_steps/data.npz
    description: "Remote few-step result data"
  - path: experiment/ch14/results/diagnose_phase_region_oscillating_droplet_steps/phase_region_oscillating_droplet_steps.pdf
    description: "Remote few-step visualization"
depends_on:
  - "[[WIKI-E-073]]"
  - "[[WIKI-E-076]]"
  - "[[WIKI-E-078]]"
consumers:
  - domain: experiment
    usage: "Use before claiming the closed-droplet PhaseRegion route has a dynamic reduced-step PASS"
  - domain: code
    usage: "Use before extending closed-chart reduced stepping to face-cochain pressure/velocity coupling"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Oscillating Droplet Few-Step PASS

## Knowledge Card

The closed-droplet route now matches the graph-route dynamic gate at the
reduced PhaseRegion chart level:

```text
X(A) -> q_l = Q_h(X(A))
q_g = |C| - q_l
PhaseRegionBatch(GAS_OUTSIDE closed radial)
E_h second variation -> modal mass and restoring force
```

The stepper uses an area-preserving mode-2 closed radial chart, the second
variation of the same discrete polygonal perimeter energy, and the Ch14 YAML
Rayleigh-Lamb/Prosperetti frequency as the exact linear oscillator reference.

## Evidence

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_oscillating_droplet_steps.py
```

Result:

```text
phase_region_droplet_steps_admitted = 1
steps                               = 8
dt                                  = 2.000000000000e-05
t_final                             = 1.600000000000e-04
t_over_T                            = 1.517153366218e-03
max_amplitude_error                 = 2.687954026026e-15
max_velocity_error                  = 3.359899413812e-11
max_energy_drift                    = 3.225430493134e-11
max_residual_l2                     = 0
max_volume_drift                    = 5.428131902296e-13
final_amplitude                     = 4.999772827646e-04
final_exact_amplitude               = 4.999772827673e-04
force_admissible                    = 0
```

Additional validation:

```text
make test PYTEST_ARGS='twophase/tests/test_phase_region_measure.py twophase/tests/test_q_manifold_projection.py -q'
```

The current remote make target ran the suite and passed with
`867 passed, 35 skipped`.

## Boundary

This is a reduced closed-chart dynamic experiment, not a production
Navier--Stokes capillary-force connection.  Keep `force_admissible=0` until
the closed and graph routes have a shared face-cochain pressure/velocity
consumer and a controlled micro-step that updates solver-owned state.

This PASS does not remove the known dynamic nonuniform droplet blocker from
WIKI-E-076: the production runtime still fails closed on the second step when
projection-native face history crosses a grid rebuild without an active
reprojector.
