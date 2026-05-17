---
ref_id: WIKI-E-069
title: "Ch14 PhaseRegion Atlas Smoke Oracle PASS"
domain: experiment
status: ACTIVE
tags: [ch14, phase_region, interface_atlas, smoke_oracle, visualization, no_force]
sources:
  - path: artifacts/A/ch14_phase_region_atlas_smoke_oracle_CHK-RA-CH14-VAR-019.md
    description: "Module B smoke-oracle implementation, review, theory check, and validation"
  - path: experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py
    description: "Closed bubble plus top-layer PhaseRegion atlas oracle"
depends_on:
  - "[[WIKI-L-051]]"
  - "[[WIKI-L-050]]"
  - "[[WIKI-T-177]]"
consumers:
  - domain: experiment
    usage: "Use before atlas admission, runtime snapshot adapters, or force-coupling probes"
  - domain: code
    usage: "Use before implementing atlas Q_h/perimeter reductions beyond the smoke oracle"
compiled_by: ResearchArchitect
compiled_at: 2026-05-17
---

# Ch14 PhaseRegion Atlas Smoke Oracle PASS

## Knowledge Card

The first multi-component atlas oracle now passes:

```text
Omega_g = Omega_bubble union Omega_layer
R_h = closed radial bubble + graph top layer
q_T = q_phys + r
force_admissible = 0
```

This validates topology, attachment, orientation, phase ownership, packed atlas
schema use, component q measures, total-volume-neutral residual splitting,
perimeter summation, finite-difference perimeter covectors, and visualization.

## Validation

Command:

```text
make cycle EXP=experiment/ch14/diagnose_phase_region_atlas_smoke_oracle.py
```

Result: PASS.  Key metrics:

- `total_volume = 2.652951873059e-01`;
- `target_volume = 2.652951873059e-01`;
- `residual_volume_abs = 1.058791184068e-22`;
- `residual_l2 = 1.321657093465e-06`;
- `total_perimeter = 1.773762526835e+00`;
- `bubble_fd_residual = 1.828148743499e-11`;
- `layer_fd_residual = 1.110222637694e-09`;
- `force_admissible = 0.0`.

The visualization is written to:

```text
experiment/ch14/results/diagnose_phase_region_atlas_smoke_oracle/phase_region_atlas_smoke_oracle.pdf
```

## Usage

This card permits the next atlas-admission design step.  It still does not
authorize force coupling, pressure/velocity coupling, GPU runtime projection,
or any T/8 run.

