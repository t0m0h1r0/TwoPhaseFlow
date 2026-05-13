---
ref_id: WIKI-L-044
title: "Post-Transfer GPU Acceleration Uses Finite-Stratum Fusion"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, performance, fusion, active_geometry, swept_flux, ppe, defect_correction, ch14]
sources:
  - path: artifacts/A/ch14_gpu_acceleration_theory_CHK-RA-CH14-AO-FASTVOL-058.md
    description: "Chapter 14 post-transfer GPU acceleration theory"
  - path: artifacts/A/ch14_active_geometry_rawkernel_fusion_CHK-RA-CH14-AO-FASTVOL-059.md
    description: "Implementation and validation of finite-stratum active-geometry fusion"
  - path: artifacts/A/ch14_swept_flux_rawkernel_fusion_CHK-RA-CH14-AO-FASTVOL-060.md
    description: "Implementation and validation of fail-closed swept-strip RawKernel fusion"
  - path: artifacts/A/ch14_fd_direct_explicit_spsm_plan_CHK-RA-CH14-AO-FASTVOL-061.md
    description: "Implementation and validation of explicit FD-direct SpSM solve-plan reuse"
  - path: src/twophase/geometry/active_kernels.py
    description: "Current active-geometry finite-stratum evaluator"
  - path: src/twophase/geometry/swept_flux.py
    description: "Current swept-volume face-flux evaluator"
  - path: src/twophase/ppe/defect_correction.py
    description: "Current pressure defect-correction orchestration"
depends_on:
  - "[[WIKI-L-038]]"
  - "[[WIKI-L-042]]"
  - "[[WIKI-L-043]]"
  - "[[WIKI-T-171]]"
  - "[[WIKI-X-050]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# Post-Transfer GPU Acceleration

## Knowledge Card

Once hidden D2H/H2D boundaries are no longer profile-dominant, the next GPU
optimization problem is work granularity.  For the Chapter 14 capillary route,
the hot work is not a different physical model hiding on the CPU; it is exact
active-geometry and swept-volume algebra expressed as many small Python/CuPy
operations plus repeated sparse analysis in defect-correction helpers.

Use this cost model:

```text
T_step = T_math + K_launch L_launch + K_sync L_sync
       + T_sparse_analysis + T_output + T_python_control.
```

After transfer cleanup, optimize by reducing `K_launch` and
`T_sparse_analysis`, while preserving the same discrete maps.

## Finite-Stratum Fusion Rule

Active geometry and swept-volume flux are finite-stratum maps.  On a regular P1
cell or swept face, a sign/case pattern selects a finite algebraic formula for
cut points, areas, lengths, derivatives, and fluxes.  Therefore they may be
fused into RawKernel or backend-native kernels if the fused code evaluates the
same case predicates and same metric-dependent formula.

Admissible fusion:

- active geometry:
  `G_K(phi_K, x_K, y_K) -> (q_K, s_K, Jq_K, dS_K, masks_K)`;
- swept flux:
  `H_f(state_f, displacement_f, metric_f) -> F_f`;
- Schur/PCG:
  unchanged fixed-iteration recurrence with device-side residual masks;
- sparse DC:
  exact factor/analysis reuse only as an explicit prepared-operator flow.

Inadmissible fusion:

- replacing nonuniform metrics by uniform-grid formulas;
- recomputing separate left/right fluxes for the same finite-volume face;
- using host `argwhere`/`unique` to discover compact supports inside the hot
  path;
- carrying a prepared sparse factor/solve plan across a metric, coefficient,
  boundary, or jump-context change;
- changing CFL, tolerances, damping, smoothing, or solver route to improve
  utilization.

## Priority

1. Fuse active-geometry refresh.  The unfused evaluator repeatedly computes
   `q/s/Jq/dS` through many helper kernels and is currently a top route cost.
   CHK-RA-CH14-AO-FASTVOL-059 implements this for CuPy float32/float64 inputs
   through a single RawKernel while retaining the unfused evaluator as fallback
   and parity oracle.
2. Fuse swept-volume face flux.  Treat flux as one conservative face cochain and
   scatter it with opposite signs to adjacent cells.  CHK-RA-CH14-AO-FASTVOL-060
   implements the low-risk part of this item: the local P1 liquid
   strip-intersection area is fused in a CuPy RawKernel, while the existing
   face-cochain assembly, velocity sign selection, donor-cell width selection,
   and periodic face identity remain unchanged.
3. Reuse defect-correction sparse analysis through explicit prepared solve
   plans, not through a hidden cache.  CHK-RA-CH14-AO-FASTVOL-061 implements
   the safe first slice: `PPESolverFDDirect.prepare_operator(rho)` factorizes
   the current low-order operator and, on GPU, attaches two cuSPARSE SpSM plans
   for the lower and upper triangular factors.  All correction RHS vectors in
   that prepared flow use those plans.  `update_grid`, `invalidate_cache`, or a
   new `prepare_operator(rho)` drops the prepared object; no global dictionary,
   fuzzy epoch match, or automatic cross-solver reuse is introduced.
4. Then scale AO-Fast PCG through compact active rows `|A_q| = O(N)` and
   multi-block device reductions.  Do not broaden the N=32 single-block trick
   into a false scalable design.

## Verification Gates

- Active geometry parity: old/new `q`, `s`, `Jq`, `dS`, masks, and row norms on
  uniform, nonuniform, periodic, wall, and near-interface cases.
- Swept flux parity: old/new face flux equality plus exact adjacent-cell
  cancellation.  GPU swept-strip fusion must fail closed on unsupported dtype,
  unsupported operand rank, compilation failure, or launch failure; do not use
  silent GPU-to-unfused fallback for production GPU routes.
- Sparse reuse safety: mutating grid coordinates, density, viscosity, boundary
  mode, or jump context must force a new prepared operator/solve-plan object.
  Repeated RHS solves through the same prepared object must not run
  `spSM_analysis` again.
- Route correctness: ch14 capillary 10-step and fractional-period gates remain
  finite and preserve the same scalar diagnostics within accepted FP tolerance.
- Performance: the targeted old hot function must disappear from the top
  cumulative profile; otherwise the patch is only negative knowledge.

## Rule

For post-transfer GPU work, fuse finite-stratum algebra and pass explicit
prepared solve flows forward when the discrete operator is already fixed.  Do
not manage sparse reuse as a hidden cache, and do not infer equality from a
nearly matching operator.  Do not change the physics, grid, convergence
contract, or YAML-owned numerical choices to obtain a prettier GPU trace.  When
a fused GPU kernel or prepared GPU solve plan is the selected production path,
make unsupported or failed GPU execution fail-close; keep unfused code as
CPU/oracle coverage, not as a hidden GPU escape hatch.
