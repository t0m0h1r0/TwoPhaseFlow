# CHK-RA-CH14-AO-FASTVOL-059 - Active-geometry RawKernel fusion

## Scope

Implemented acceleration item #1 from WIKI-L-044: fuse the finite-stratum
active-geometry refresh used by the Chapter 14 active-geometry capillary route.

The public API remains `refresh_active_geometry_2d`.  On CuPy float32/float64
inputs it now dispatches to a single RawKernel that evaluates, per active cell:

- `q_A`
- `s_A`
- `case_code_A`
- `edge_mask_A`
- `lambda_edge_A`
- `cell_measure_A`
- `jq_local_A`
- `ds_local_A`
- `row_norm_A`
- `sign_margin_A`
- `finite_mask_A`
- `regular_mask_A`

The previous backend-native CuPy/NumPy composition is retained as
`_refresh_active_geometry_2d_unfused` and remains the fallback for CPU,
non-CuPy, unsupported dtype, and empty-support paths.

## Algebra preserved

The RawKernel implements the same finite-stratum map as the unfused evaluator:

```text
G_K(phi_K, x_K, y_K) -> (q_K, s_K, Jq_K, dS_K, masks_K)
```

The implementation preserves:

- the same four-corner P1 ordering;
- the same edge crossing predicate `value_lo * value_hi < 0`;
- the same case-code bit convention;
- the same special split handling for case `10`;
- the same polygon shoelace volume formula;
- the same segment-length formula;
- the same chain-rule derivatives for cut area and interface length;
- actual nonuniform coordinate arrays from `grid.device_coords`;
- the same finite/sign-margin regularity masks.

No tolerance, CFL, physical parameter, solver route, nonuniform-grid contract,
or interface-tracking grid-rebuild contract changed.

## Validation

- Remote GPU parity:
  `pytest twophase/tests/test_geometry_active_table.py::test_gpu_fused_active_geometry_matches_unfused_nonuniform_rows -q`
  PASS (`1 passed`).
- Remote targeted regression:
  `pytest twophase/tests/test_geometry_active_table.py` plus the previously
  failing GPU config/YAML gates PASS (`18 passed`).
- Remote full GPU suite:
  `make test` PASS (`951 passed, 3 skipped`).
- Remote 10-step cProfile on the same capillary diagnostic route:
  - before fusion: total `25.705 s`, `refresh_active_geometry_2d`/full geometry
    cost `9.489 s`, projection stage `11.064 s`;
  - after fusion: total `15.803 s`, `refresh_active_geometry_2d` Python-side
    cumulative `0.029 s`, RawKernel wrapper `0.027 s`, projection stage
    `2.146 s`.

## Remaining bottleneck

The active-geometry full refresh bottleneck moved out of the top profile.  The
dominant remaining route cost is now swept-volume flux:

```text
_construct_p1_swept_flux_gpu: 8.933 s
_local_triangle_cut_area:    8.586 s
```

This matches the WIKI-L-044 ordering: item #2 should fuse the conservative
swept face cochain next.

## SOLID/A3

- [SOLID-S] RawKernel fusion is isolated behind the existing
  `refresh_active_geometry_2d` API; the unfused implementation remains as a
  fallback and parity oracle.
- [SOLID-D] Dispatch depends on backend capability and dtype, not on experiment
  names.
- [SOLID-X] No source of physical truth, YAML-owned parameter, pressure route,
  or grid contract was moved into the kernel.
