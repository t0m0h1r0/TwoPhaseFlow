---
ref_id: WIKI-E-068
title: "Ch14 q-Manifold Runtime Admission Snapshot Probe PASS"
domain: experiment
status: ACTIVE
tags: [ch14, q_manifold, runtime_admission, closed_radial_chart, residual_budget, no_t8]
sources:
  - path: artifacts/A/ch14_runtime_admission_probe_CHK-RA-CH14-VAR-014.md
    description: "Runtime-admission snapshot implementation, review, and validation"
  - path: experiment/ch14/diagnose_q_manifold_runtime_admission_probe.py
    description: "CPU-labeled Ch14 initial-condition admission probe"
depends_on:
  - "[[WIKI-E-067]]"
  - "[[WIKI-L-049]]"
consumers:
  - domain: experiment
    usage: "Use before force-coupling admission probes or any T/8 attempt"
  - domain: code
    usage: "Use to keep runtime q-manifold residual budgets visible before force construction"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 q-Manifold Runtime Admission Snapshot Probe PASS

## Knowledge Card

The Ch14 oscillating-droplet initial condition can now be turned into a
diagnostic `ProjectionResult` without running T/8:

```text
runtime-facing q_T snapshot -> Gamma*_closed_radial -> q_phys -> r
```

The residual budget is visible and nonzero, and force admission remains false.

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_q_manifold_runtime_admission_probe.py
```

Result: PASS.  Key metrics:

- `residual_l2 = 1.022474608009e-07`;
- `relative_l2 = 2.244971032800e-02`;
- `residual_area_abs = 1.726838710861e-07`;
- `mode_cos_2 = 4.977887457363e-04`;
- `compat_linf = 0.000000000000e+00`;
- `force_admissible = 0.0`.

## Usage

Use this card before any force-coupling or T/8 attempt.  It does not authorize
GPU runtime projection, capillary force construction, pressure coupling, or
treating the residual `r` as geometry.
