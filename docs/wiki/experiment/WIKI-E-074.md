---
ref_id: WIKI-E-074
title: "Ch14 PhaseRegion Face-Cochain Work Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, face_cochain, variational, pressure_range, no_t8]
sources:
  - path: artifacts/A/ch14_phase_region_face_cochain_work_oracle_CHK-RA-CH14-VAR-032.md
    description: "Face-cochain work oracle implementation and validation"
  - path: experiment/ch14/diagnose_phase_region_face_cochain_work_oracle.py
    description: "Endpoint face-cochain diagnostic script"
depends_on:
  - "[[WIKI-E-073]]"
  - "[[WIKI-T-177]]"
consumers:
  - domain: experiment
    usage: "Use before any runtime force dry-run, pressure/velocity coupling, micro-step, or T/8 probe"
  - domain: code
    usage: "Use before promoting PhaseRegion capillary force into production face cochains"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Face-Cochain Work Oracle PASS

## Knowledge Card

The endpoint face-cochain work gate now passes for the existing fixed-stratum
closed-interface Riesz diagnostic:

```text
T_h(u_f) = -D_f(psi_f u_f)
s_f = -M_f^{-1} T_h^T dE_h
dE_h[T_h(u_f)] + <s_f, u_f>_{M_f} = 0
```

The oracle also checks weighted pressure range/Hodge decomposition and a
nonuniform `periodic_wall` face-divergence adjoint identity.

## Validation

Remote command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_face_cochain_work_oracle.py
```

Result: PASS.

```text
self_fd_power_residual         = 1.678373246703e-08
self_riesz_residual           = 0.000000000000e+00
probe_fd_power_residual        = 1.678894666868e-08
probe_riesz_residual          = 6.674177881816e-17
hodge_divergence_linf         = 1.989519660128e-13
manufactured_range_hodge_l2   = 3.163533455825e-12
manufactured_range_recovery_linf = 1.057287590811e-11
nonuniform_adjoint_error      = 7.105427357601e-15
force_admissible              = 0.0
```

Visualization:

```text
experiment/ch14/results/diagnose_phase_region_face_cochain_work_oracle/phase_region_face_cochain_work_oracle.pdf
```

## Failed Probe Kept

A standalone smooth face velocity was tried first and rejected because symmetry
made the work nearly zero, which made relative residuals uninformative.  The
accepted probe mixes the surface acceleration with a smooth perturbation
without weakening tolerances.

## Boundary

This authorizes only a fixed-stratum endpoint face-cochain work oracle.  It
does not authorize runtime force coupling, pressure/velocity coupling,
nonlinear optimization, micro-stepping, or T/8.  The next physics gate is a
zero-step runtime force dry-run that reports face cochain, pressure
range/Hodge split, and work metrics while keeping `force_admissible = false`.
