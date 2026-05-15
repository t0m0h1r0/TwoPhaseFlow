# CHK-RA-CH14-AO-FASTVOL-057 - Future O(N) active-row PCG memory

## Scope

User direction: O(N) handling for AO-Fast PCG should be done separately and
remembered.

## Memory

The current block-resident PCG optimization is intentionally a full-cell
row-space acceleration for the N=32 capillary-wave route:

```text
row count = N_x * N_y = 1024
node image count for periodic N=32 = 33 * 33
```

The periodic `33 x 33` nodal image shape is not the Schur PCG row count; PCG
solves for cell-row multipliers `lambda_C`.  Therefore the current N=32 route
does use the single-block kernel.

However, the `1024` cap is a strict single-block CUDA limit and should not be
treated as the scalable AO-Fast design.  The future scalable design should
restore the Schur row space to compact active rows near the interface:

```text
|A_q| = O(N)  for a resolved 2D interface
```

instead of the current full-grid fixed row space:

```text
|C_h| = O(N^2)
```

## Required future design conditions

- Preserve the same Schur equation `S_A lambda_A = b_A`,
  `S_A = J_A J_A^T`.
- Do not broaden the single-block `1024` limit as a workaround.
- Build compact active support on the GPU without hidden `argwhere`/`unique`
  host synchronization in the hot path.
- Include periodic halo/support closure, especially for x-periodic capillary
  waves.
- Rebuild or invalidate compact support on the same metric/interface epoch as
  interface-tracking grid rebuilds.
- Keep nonuniform-grid metric dependence in the active `jq_local` rows.
- Add equivalence gates against the current full fixed-shape Schur path before
  using the compact route for production timing.

## SOLID / fidelity notes

- [SOLID-S] This is future design memory only; it does not change the current
  block PCG implementation.
- [SOLID-D] Future dispatch should depend on active support size and backend
  capability, not experiment names.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance change,
  solver fallback, grid-rebuild removal, nonuniform-grid removal, main merge, or
  branch deletion was introduced.
