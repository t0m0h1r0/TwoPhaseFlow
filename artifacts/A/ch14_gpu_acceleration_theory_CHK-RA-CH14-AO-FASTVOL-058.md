# CHK-RA-CH14-AO-FASTVOL-058 - GPU acceleration theory for the ch14 capillary route

## Purpose

The current Chapter 14 active-geometry capillary-wave route is already mostly
device-resident.  The remaining slowdown is therefore not primarily a hidden
large D2H/H2D transfer problem.  The measured 10-step cProfile after the
block-PCG work showed:

- total: `25.705 s`
- `refresh_active_geometry_2d`: `9.489 s`
- swept-volume flux polygon/triangle cuts: `9.204 s`
- defect-correction solves: `3.050 s`
- `cupyx.scipy.sparse.linalg.solve`: `1.860 s`
- `cupy_backends.cuda.libs.cusparse.spSM_analysis`: `1.711 s`
- explicit `to_host`/`asnumpy` aggregate: about `0.076 s`

The acceleration theory must therefore target GPU work granularity and sparse
analysis/factor reuse while preserving the same physical and mathematical
discrete problem.

## Principle 0 - Do not buy speed by changing the equation

Admissible transformations preserve:

- the active-geometry capillary state space;
- nonuniform tensor-product grid metrics;
- interface-tracking grid rebuild epochs;
- the finite-stratum `q/phi` compatibility projection;
- the Schur equation `S_A lambda_A = b_A`, `S_A = J_A J_A^T`;
- FCCD/CCD pressure and viscous operators;
- YAML-owned physical parameters, tolerances, CFL, solver scheme, and initial
  state.

The following are not optimizations:

- lowering tolerances or iteration caps;
- changing CFL, smoothing, damping, or curvature caps;
- disabling nonuniform-grid fitting or interface-tracking rebuilds;
- replacing the route by a different pressure or surface-tension formulation;
- hiding dynamic active support construction behind host `argwhere`/`unique`.

## Cost model

For a fixed physical route, a GPU timestep has the schematic cost

```text
T_step = T_math + K_launch L_launch + K_sync L_sync
       + T_sparse_analysis + T_output + T_python_control.
```

After transfer cleanup, `K_launch L_launch` and `T_sparse_analysis` dominate.
For N=32 the arithmetic payload is too small to hide many Python-launched CuPy
elementwise kernels.  A single saturated CPU core is then a symptom of launch
or library orchestration, not proof that host multiprocessing will help.

Therefore the optimization target is:

```text
minimize kernel count and sparse analysis count
subject to exact equality with the existing discrete operators.
```

## Lemma 1 - Fixed-stratum active geometry is fusible

On a regular P1 active cell, the sign pattern of the four corner `phi` values
selects one of finitely many marching-squares strata.  Within a stratum:

- the cut-edge interpolation parameters are rational functions of corner
  `phi`;
- cut polygon vertices are affine functions of cell coordinates and those
  parameters;
- `Q_h`, `S_h`, `J_q`, and `dS_h` are finite sums of polygon area, segment
  length, and their chain-rule derivatives.

Hence the existing active geometry evaluation is a local map

```text
G_K: (phi_K, x_K, y_K) -> (q_K, s_K, Jq_K, dS_K, masks_K)
```

with finite case branching.  Replacing the current Python/CuPy composition by a
single RawKernel per active-cell packet preserves the algebra if:

- the same stratum predicates are used;
- nonuniform coordinates enter the kernel as the actual device coordinate
  arrays;
- near-zero sign margins still fail close or route to the already-tested safe
  path;
- parity tests compare all returned fields against the unfused evaluator.

This is the first acceleration target because the profile shows hundreds of
full geometry refreshes and tens of thousands of small helper calls.

## Lemma 2 - Swept-volume flux is a face cochain and is fusible

The geometric transport update is a finite-volume cochain update:

```text
q_K^{n+1} = q_K^n - sum_{f in boundary K} sigma_{Kf} F_f / |K|.
```

Correctness is attached to a single face flux `F_f`, not to the internal
triangulation used to compute it.  The current swept-flux code evaluates the
same spacetime polygon area by repeated strip and triangle clipping.  This is
again a finite case map:

```text
H_f: (q/phi edge state, face displacement, metric data) -> F_f.
```

A fused GPU implementation is admissible when it computes one canonical face
cochain value and scatters it with opposite signs to adjacent cells.  This
preserves conservation and periodic/wall closure.  The fused kernel must not
compute separate left/right fluxes for the same face, because that would break
the finite-volume cancellation identity.

This is the second acceleration target because swept flux currently spends
almost the same time as full active geometry refresh.

## Lemma 3 - Device-loop Krylov is exact when the recurrence is unchanged

The block PCG implementation already used this lemma for `32 x 32` cell-row
space.  The general rule is:

```text
fixed max iterations + device residual masks
```

can replace host-controlled early exit without changing the accepted recurrence,
provided that the mask freezes updates after the same convergence/floor
predicate.  For larger grids the single-block cap must not be widened blindly.
The scalable path is compact active support `|A_q| = O(N)` plus multi-block
device reductions or an equivalent backend primitive.

This work is lower priority than geometry and swept flux for the current N=32
route because PCG is no longer profile-dominant after CHK-056, but it remains
the correct future scaling theory.

## Lemma 4 - Sparse analysis/factor reuse is exact only by operator epoch

The low-order direct base solves in pressure/viscous defect correction use the
same mathematical operator during a valid metric/coefficient epoch.  Reusing
factorization, sparse analysis, or batched triangular solves is exact if and
only if the operator triplets are identical:

```text
epoch key = (metric epoch, boundary epoch, coefficient epoch, stencil id)
```

Approximate reuse across changed density, viscosity, grid coordinates, or jump
contexts is not admissible.  Exact reuse within an epoch is admissible and
should be preferred over rebuilding `splu`/cuSPARSE analysis for each caller.

Two safe acceleration directions follow:

- share cached low-order factors/analysis across PPE, external Hodge split,
  and viscous solves when their epoch key is identical;
- batch multiple RHS columns through the same factor/analysis.

The longer-term direction is a matrix-free GPU low-order preconditioner that
preserves the defect-correction operator relation instead of invoking sparse
direct analysis.

## Implementation ordering

1. Add a bounded route profiler that reports kernel-launch granularity,
   sparse-analysis calls, and D2H/H2D packet counts for the capillary route.
2. Replace active-geometry refresh helpers by a fused fixed-stratum kernel,
   gated by exact parity against `refresh_active_geometry_2d`.
3. Replace swept-volume polygon/triangle helper stacks by a fused face-cochain
   kernel, gated by conservation, CPU/GPU parity, and old/new flux equality.
4. Add operator-epoch factor/analysis sharing and RHS batching for DC callers.
5. Only after the above, revisit compact `O(N)` active-row PCG for larger grids.

## Validation gates

Each acceleration patch needs both an algebra gate and a route gate:

- Active geometry: old/new `q`, `s`, `Jq`, `dS`, masks, row norms equal within
  backend parity tolerance on uniform, nonuniform, periodic, wall, and
  near-interface cases.
- Swept flux: old/new face flux equal; adjacent-cell flux cancellation exact;
  boundedness/fail-close behavior unchanged.
- DC/PPE/viscous reuse: factors are reused only on identical epoch keys; a
  test mutating grid coordinates, density, viscosity, or boundary context must
  force invalidation.
- Route: 10-step ch14 capillary run remains finite and matches scalar
  diagnostics within accepted floating-point tolerance.
- Performance: profile must show the targeted old hot function is no longer in
  the top cumulative list; otherwise the patch is negative knowledge, not a
  success.

## Working conclusion

The shortest mathematically valid path to speed is:

```text
fuse finite-stratum geometry
-> fuse conservative swept face cochains
-> reuse/batch exact sparse analysis by epoch
-> scale compact active-row PCG.
```

This attacks the measured bottlenecks in order while keeping the paper route,
nonuniform grid, and interface-tracking rebuild semantics intact.
