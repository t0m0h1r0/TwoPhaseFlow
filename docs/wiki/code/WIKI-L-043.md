---
ref_id: WIKI-L-043
title: "GPU Optimization Starts by Removing Hidden D2H/H2D Boundaries"
domain: code
status: ACTIVE
superseded_by: null
tags: [gpu, d2h, h2d, ao_fast, active_geometry, capillary, ch14]
sources:
  - path: artifacts/A/ch14_capillary_gpu_transfer_minimization_CHK-RA-CH14-AO-FASTVOL-051.md
    description: "Chapter 14 capillary active-geometry transfer minimization"
  - path: artifacts/A/ch14_gpu_scalar_transfer_batching_CHK-RA-CH14-AO-FASTVOL-052.md
    description: "Fail-close guard against single-scalar GPU transfers"
  - path: artifacts/A/ch14_gpu_geometry_schur_fusion_CHK-RA-CH14-AO-FASTVOL-055.md
    description: "Algebra-preserving AO-Fast geometry and Schur fusion"
  - path: artifacts/A/ch14_gpu_pcg_block_kernel_CHK-RA-CH14-AO-FASTVOL-056.md
    description: "Block-resident AO-Fast Schur PCG for N=32 capillary route"
depends_on:
  - "[[WIKI-L-038]]"
  - "[[WIKI-L-039]]"
  - "[[WIKI-X-050]]"
compiled_by: ResearchArchitect
compiled_at: 2026-05-13
---

# GPU Transfer Boundary Hygiene

## Knowledge Card

When optimizing a GPU numerical route, first search for hidden host/device
transfer boundaries before changing algorithmic knobs.  D2H and H2D can appear
as obvious `to_host`/`asnumpy` calls, but also as dynamic support discovery,
scalar extraction for control flow, repeated conversion of immutable coordinate
or metric arrays, and output/probe serialization.

The admissible first pass is:

- keep the governing discrete equation and tolerances unchanged;
- make loop-carried arrays backend-native and fixed-shape when possible;
- replace dynamic active-set discovery inside Krylov/DC loops with
  device-resident masks or predeclared supports;
- cache immutable grid coordinates, cell widths, and CCD metrics on the device
  per metric epoch;
- batch unavoidable scalar diagnostics into one transfer at explicit
  fail-close/reporting boundaries;
- leave remaining host boundaries named and justified.

For AO-Fast or active-geometry capillary routes, compactness must not be bought
by `argwhere`/`unique` inside the hot path if that forces the backend to know a
dynamic output length.  A fixed-shape masked Schur operator preserves the same
`J_A J_A^T` algebra and can avoid a synchronization boundary.  If the
fixed-shape route is still not faster, the conclusion is not "relax physics";
it is that the measured cost is dominated by another algebraic kernel, grid
rebuild, output, or problem-size occupancy limit.

After transfer boundaries are removed, inspect whether the GPU route is still
issuing many exact but tiny kernels.  The next admissible step is to fuse the
same discrete algebra, not to change the problem.  Examples from the Chapter 14
capillary route:

- if a line-search theorem only needs exact `Q_h(phi)`, evaluate a `Q_h`-only
  geometry packet instead of full `Q_h/S_h/J_q/dS_h`;
- if the candidate set is fixed, evaluate all candidates in one backend packet
  and choose the first accepted step with device masks;
- if a hot operator is exactly `J_A J_A^T`, implement the same P1 cell-node
  incidence sum directly or with a backend RawKernel, with all metric and
  nonuniform-grid dependence carried by `J_A`.
- if a Krylov row space fits in one CUDA block, move the fixed PCG recurrence
  and its reductions into one device loop.  This preserves the same
  preconditioned CG recurrence while eliminating Python-launched per-iteration
  Schur, dot, max, and update kernels.  Guard the optimization by row-space
  size; larger systems need a multi-block theory rather than accidental reuse.

## Consequences

- Do not retune CFL, tolerances, pressure routes, smoothing, or damping to make
  a GPU trace look better.
- Device caches must be invalidated on the same metric epoch that rebuilds
  coordinates and nonuniform metrics.
- Tests should forbid dynamic support discovery in fixed-shape GPU Schur paths.
- Tests should prove every fused algebraic path matches the unfused exact path:
  `Q_h`-only vs full geometry, batched candidates vs individual candidates, and
  fused Schur vs `J(J^T x)`.
- Raw Krylov kernels should be tested against the vector recurrence on the same
  backend before route-level timing is trusted.
- GPU runtime code should not keep a usable single-scalar transfer helper; even
  unavoidable scalar diagnostics should pass through a packet helper so future
  additions naturally batch synchronization.
- If unavoidable D2H remains, document the boundary: fail-close diagnostics,
  interface-tracking grid rebuild guards, and final output are different from
  inner Krylov or geometry kernels.
- Performance claims must include both correctness gates and wall-time/GPU-route
  evidence; a transfer cleanup with no speedup is still useful negative
  knowledge.

## Paper-Derived Rule

Optimize GPU routes by eliminating hidden transfer boundaries and preserving the
same discrete algebra first.  Treat physical retuning or solver weakening as a
bug, not as a performance optimization.
