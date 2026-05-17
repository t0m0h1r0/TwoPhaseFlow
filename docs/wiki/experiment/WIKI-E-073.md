---
ref_id: WIKI-E-073
title: "Ch14 PhaseRegion Force/Work Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, force_work, variational, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_force_work_oracle_CHK-RA-CH14-VAR-031.md
    description: "Force/work oracle implementation and validation"
  - path: experiment/ch14/diagnose_phase_region_force_work_oracle.py
    description: "Closed-chart force/work diagnostic script"
depends_on:
  - "[[WIKI-E-072]]"
  - "[[WIKI-E-067]]"
  - "[[WIKI-T-177]]"
consumers:
  - domain: experiment
    usage: "Use before any runtime force-coupling, pressure/velocity pairing, micro-step, or T/8 probe"
  - domain: code
    usage: "Use before promoting closed-chart capillary force into production runtime code"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Force/Work Oracle PASS

## Knowledge Card

The closed-chart PhaseRegion route now has a validated force/work oracle:

```text
E_h[X] = sigma L[X]
A_h[X] = polygon area
F_h = -(dE_h - beta dA_h)
beta = <dE_h, dA_h> / <dA_h, dA_h>
```

The oracle checks surface-energy and area covectors against central finite
differences, removes the pressure/volume reaction, verifies virtual work,
checks restoring sign and phase symmetry, and confirms a short constrained
force step decreases surface energy.

## Validation

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_force_work_oracle.py
```

Result: PASS.

```text
energy_drop          = 2.692519334579e-05
surface_fd_error     = 2.265180265582e-10
area_fd_error        = 1.333230803535e-09
area_free_fd_error   = 3.151302552240e-10
force_area_reaction  = 5.881796785734e-18
work_pairing_error   = 0.000000000000e+00
force_mode_action    = -6.800389270769e-01
sine_action_abs      = 6.938893903907e-18
restoring_error      = 0.000000000000e+00
force_admissible     = 0.0
```

Visualization:

```text
experiment/ch14/results/diagnose_phase_region_force_work_oracle/phase_region_force_work_oracle.pdf
```

## Boundary

This authorizes only a closed-chart variational force/work oracle.  It does
not authorize runtime force coupling, pressure/velocity coupling, nonlinear
optimization, micro-stepping, or T/8.  The next physics gate is to match this
interface force to the pressure/velocity or face-cochain work metric.
