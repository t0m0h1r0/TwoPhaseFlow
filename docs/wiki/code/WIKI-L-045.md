---
ref_id: WIKI-L-045
title: "AO-Fast GPU Efficiency Bottleneck Is Fixed-Loop Geometry Compatibility"
domain: code
status: ACTIVE
tags: [gpu, performance, ao_fast, active_geometry, pcg, defect_correction, synchronization, ch14]
sources:
  - path: docs/02_ACTIVE_LEDGER.md
    description: "CHK-RA-CH14-AO-FASTVOL-058--062 GPU profiling, finite-stratum fusion, SpSM plan reuse, and quarter-period reruns"
  - path: docs/wiki/code/WIKI-L-043.md
    description: "D2H/H2D boundary elimination policy"
  - path: docs/wiki/code/WIKI-L-044.md
    description: "Finite-stratum fusion and explicit sparse solve-plan reuse"
  - path: src/twophase/geometry/active_kernels.py
    description: "Fused active-geometry evaluator"
  - path: src/twophase/geometry/swept_flux.py
    description: "Fused swept-strip area evaluator"
  - path: src/twophase/ppe/fd_direct.py
    description: "Explicit prepared SpSM solve-plan reuse"
depends_on:
  - "[[WIKI-L-043]]"
  - "[[WIKI-L-044]]"
  - "[[WIKI-T-171]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-X-050]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# AO-Fast GPU Efficiency Bottleneck

## Knowledge Card

The capillary AO-Fast route is using the GPU, but low utilization after the
finite-stratum fusion work is mainly a work-granularity and fixed-iteration
geometry-compatibility problem.  It is not evidence that the main computation
has silently fallen back to CPU, and it must not be addressed by disabling
nonuniform grids, interface-following rebuilds, active geometry, or convergence
gates.

## Measurements

Minimal 40-step loop:

| Metric | Value |
|---|---:|
| wall time | `80.175 s` |
| CPU user time | `80.053 s` |
| CPU sys time | `0.216 s` |
| GPU utilization | min `5%`, avg `24.8%`, max `62%` |
| GPU memory | avg about `292 MB` |
| GPU power | avg about `138 W` |

Ten-step profile:

| Function / Stage | Time |
|---|---:|
| `_advance_geometric_phase_stage` / `_project_q_phi_compatibility_fixed_gpu` | `17.544 s` |
| `_residual_reducing_step_gpu` | `15.184 s` over `2560` calls |
| `refresh_active_volume_geometry_candidates_2d` | `13.637 s` |
| `_local_cut_areas` | `10.020 s` |
| PPE defect correction | `2.240 s` |
| split update | `1.348 s` |
| viscous stage | `0.850 s` |

The tested `active_geometry.solver.convergence.max_iterations` cap dominates
the cost for the N32 capillary route.  Short probes gave the same scalar state
for much smaller caps:

| `max_newton` cap | Wall time | Final `v_abs` | Final `compat` |
|---:|---:|---:|---:|
| 2 | `15.440 s` | `1.186564e-03` | `2.684872e-13` |
| 4 | `16.408 s` | same | same |
| 8 | `18.423 s` | same | same |
| 12 | `20.459 s` | same | same |
| 16 | `22.681 s` | same | same |
| 32 | `30.788 s` | same | same |
| 64 | `47.266 s` | same | same |

## Interpretation

The hot path is GPU algebra wrapped by too many small launches and a fixed
compatibility loop.  D2H/H2D transfer cleanup was necessary, but it is not the
dominant remaining issue.  The residual CPU time mostly represents Python
control and launch orchestration around device work.

Known remaining scalar synchronization points:

- defect-correction convergence summaries in `src/twophase/ppe/defect_correction.py`;
- reprojector diagnostic statistics in
  `src/twophase/projection/velocity_reprojector_basic.py`;
- capacity timestep scalar packets in
  `src/twophase/geometry/geometric_phase_runtime_gpu.py`.

These transfers should be batched when possible, but they are secondary to the
fixed-loop geometry-compatibility cost.

## Safe Optimization Policy

Allowed:

- replace fixed full compatibility loops with chunked fail-close convergence:
  run a small device chunk, transfer one residual/status packet, and continue
  only if the mathematical convergence gate requires it;
- keep `max_iterations` as a safety cap, but make YAML defaults reflect the
  smallest theory-validated cap for the production route after an integrated
  quarter-period check;
- fuse line-search and candidate geometry refresh when the fused kernel
  evaluates the exact same finite-stratum formulas;
- preallocate and explicitly pass scratch arrays through the route;
- batch scalar convergence/status transfers into one packet per outer chunk;
- keep diagnostic statistics optional or behind explicit profiling flags.

Forbidden:

- hiding a failed GPU kernel or solver behind a CPU fallback;
- disabling nonuniform metrics or interface-following rebuilds to improve a
  trace;
- reducing active-geometry accuracy, pressure convergence, or Hodge projection
  requirements without a new theorem;
- widening the single-block N32 PCG trick into a false scalable design;
- managing operator reuse as a hidden cache instead of an explicit prepared
  flow.

## Acceptance Gates

Before accepting further GPU changes on this route:

- prove the same nonuniform and rebuild-enabled capillary YAML still runs the
  fractional-period experiment;
- show the hot profile entry actually moved or shrank;
- report GPU utilization together with wall time, not utilization alone;
- verify scalar diagnostics: volume, kinetic energy, signed interface
  amplitude, `face_hodge_pre/post`, `ppe_rhs`, and compatibility;
- run exactness/parity tests for active geometry, swept flux, face Hodge
  reprojector, pressure-history coordinate, and DC convergence gating.
