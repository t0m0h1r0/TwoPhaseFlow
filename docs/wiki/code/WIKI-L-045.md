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
  - path: artifacts/A/ch14_capillary_face_bridge_unit_rca_CHK-RA-CH14-AO-FASTVOL-064.md
    description: "RCA for capillary-wave visual breakage from AO face bridge unit mismatch"
  - path: src/twophase/geometry/active_kernels.py
    description: "Fused active-geometry evaluator"
  - path: src/twophase/geometry/swept_flux.py
    description: "Fused swept-strip area evaluator"
  - path: src/twophase/ppe/fd_direct.py
    description: "Explicit prepared SpSM solve-plan reuse"
  - path: src/twophase/simulation/geometric_phase_runtime_gpu.py
    description: "AO compatibility projection fail-close early-stop after exact residual certification"
  - path: experiment/ch14/diagnose_ao_stage_chain.py
    description: "Stage timing and optional nvidia-smi GPU utilization probe for the capillary AO route"
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

2026-05-14 follow-up after restoring the one-time face-Hodge bridge:
`_project_q_phi_compatibility_fixed_gpu` now checks the exact active
`q-Q_h(phi)` residual at the start of each Newton sweep with one batched scalar
packet.  If the residual already satisfies the configured absolute/relative
contract, it stops before Schur solve, line-search candidate geometry, and
another full geometry refresh.  This is result-preserving: the old device
predicate `active_newton = residual_linf > residual_tolerance` already made
the update a no-op in exactly the same state; the optimization only avoids
computing the no-op.

Thirty-step stage-chain diagnostic, same N32 nonuniform/rebuild-enabled
capillary route:

| Metric | Before | After |
|---|---:|---:|
| command wall time | `82.364 s` | `11.731 s` |
| speedup | — | `7.0x` |
| summed step wall time | — | `8.384 s` |
| mean step wall time | — | `0.279 s` |
| mean surface/capillary stage time | dominant via compatibility loop | `4.78e-4 s` |
| mean predictor stage time | — | `0.180 s` |
| mean pressure stage time | — | `0.069 s` |
| mean GPU utilization with 0.2 s sampling | about `25%` in earlier profile | `42.6%` |
| max GPU utilization | `62%` | `59%` |
| max AO compatibility residual | — | `8.10e-14` |
| max Young--Laplace normal residual | — | `9.81e-14` |
| max velocity-divergence diagnostic | — | `7.84e-14` |

Quick verification command:

```bash
make run EXP=experiment/ch14/diagnose_ao_stage_chain.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 30 --runner-initial-grid-rebuild --prepare-grid-each-step --backend gpu --summary-only'
```

Add `--gpu-sampling-interval 0.2` to report utilization and power.  Use the
summary output for fast regression checks, and the full CSV when localising a
stage regression.

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

After the fail-close early-stop, the compatibility loop is no longer the
dominant N32 cost.  Remaining utilization below 100% is not by itself evidence
of CPU fallback: the route still has small-grid GPU work, pressure/predictor
launch granularity, and small active Schur solves.  For the checked-in N32
capillary wave, optimizing for wall time and exact residual certificates is
more meaningful than trying to raise utilization by adding work.  Larger grids
or future multiblock/O(N) Schur solvers are the appropriate path for saturating
more SMs without changing the numerical method.

Visual breakage after optimization is not automatically a stability or solver
iteration problem.  First re-check the dimensional contract at every bridge
between active geometry and the NS projection lattice.  In particular,
`GeometricRuntimeCapillaryApplicationState.predictor_face_acceleration` and
`predictor_face_increment` are already geometric-face-Hodge-divided samples
`M_G^{-1} r_sigma` and `dt M_G^{-1} r_sigma`; they are not integrated
face-volume cochains.  The projection bridge must interpolate them with
nonuniform metric weights but must not divide by face length again.  A second
division by `dx` or `dy` is an O(1/h) amplification and can look like a broken
velocity direction, frozen interface, or exploding pressure plot on the fitted
N32 capillary grid.

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
- stop a Newton compatibility sweep immediately after an exact residual packet
  certifies `residual_linf <= residual_tolerance`; this removes only work that
  would have been masked by `active_newton=false`;
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
