# CHK-RA-CH14-AO-FASTVOL-060 - Swept-strip RawKernel fusion

## Question

User asked whether WIKI-L-044 item #2 has side effects, and requested the update
only if theory says it is safe.  User also required fail-close rather than a
silent fallback.

## Theory review

The swept-volume transport contract is a face cochain contract:

```text
Phi_l(f) = sign(u_f) |P1-liquid donor polygon cap swept strip_f| / dt
```

The dangerous operation is changing how the face cochain is assembled, because
that can duplicate left/right face fluxes, break periodic face identity, or
replace nonuniform donor widths by uniform formulas.  Therefore the safe
fusion boundary is not the whole face-flux constructor.  The safe boundary is
the local finite-stratum map

```text
H_K^axis(phi_0..phi_3, x0,x1,y0,y1, lower,upper)
  = area(P1-liquid polygon in K intersect axis-aligned strip).
```

This map is independent for each cell/strip item once the caller has already
chosen donor side, velocity sign, and periodic closure.  Replacing only this
local map by an algebraically identical RawKernel preserves the external face
cochain assembly.

## Hypotheses checked

| Hypothesis | Risk | Resolution |
|---|---|---|
| H1: Fusion could compute separate left/right fluxes for one face. | Breaks finite-volume conservation. | Refuted by design: `_construct_p1_swept_flux_gpu` still owns one face array and unchanged sign/periodic assignment; only strip area evaluation is fused. |
| H2: Fusion could erase nonuniform metrics. | Wrong swept volume on fitted grids. | Refuted by implementation: RawKernel receives broadcasted `cell_x0/x1/y0/y1` from the existing coordinate arrays. |
| H3: Case-10 or zero-adjacent P1 cuts could change topology. | Wrong liquid polygon on ambiguous strata. | Refuted by parity gate: the GPU test includes random nonuniform geometry, forced case 10, zero-adjacent crossings, and all 16 square sign cases. |
| H4: Fallback could hide wrong GPU behavior. | Wrong kernel silently replaced by old path. | Addressed by fail-close: CuPy/GPU dispatch requires RawKernel; unsupported dtype, non-2D broadcast operands, compilation failure, or launch failure raises. CPU keeps the unfused evaluator as the oracle path. |
| H5: Full route could fail despite local parity. | Side effect outside local map. | Refuted by 10-step capillary stage-chain cProfile and full GPU test suite. |

## Implementation

- `src/twophase/geometry/swept_flux.py`
  - Added `_axis_aligned_strip_area_raw` and a cached CuPy RawKernel.
  - RawKernel evaluates one strip item per thread using the same strict square
    crossing predicate, the same case-code bit convention, the same case-10
    diagonal split, and the same inclusive triangle strip clipping as the
    unfused evaluator.
  - `_axis_aligned_strip_area` dispatches CuPy namespaces to RawKernel and
    raises on unsupported GPU conditions.  `_axis_aligned_strip_area_unfused`
    remains the CPU/oracle implementation, not a GPU fallback.
- `src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  - Added a CuPy parity gate against the unfused oracle for nonuniform
    coordinates, random cuts, forced ambiguous case 10, zero-adjacent cuts, both
    axes, and all 16 square sign cases.

## Validation

- Local syntax:
  `python3 -m py_compile src/twophase/geometry/swept_flux.py src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  PASS.
- Whitespace:
  `git diff --check` PASS.
- Remote targeted CuPy parity:
  `pytest -q src/twophase/tests/test_geometric_runtime_gpu_gates.py::test_gpu_swept_strip_raw_kernel_matches_unfused_nonuniform_geometry`
  PASS (`1 passed`).
- Remote full GPU suite:
  `make test` PASS (`952 passed, 3 skipped`).
- Remote 10-step capillary cProfile:
  `experiment/ch14/diagnose_ao_stage_chain.py --config experiment/ch14/config/ch14_capillary.yaml --steps 10 --runner-initial-grid-rebuild --backend gpu`
  PASS.  Total cProfile time improved from CHK-059 `15.803 s` to `6.881 s`.
  The old swept bottleneck (`_construct_p1_swept_flux_gpu` / `_local_triangle_cut_area`)
  no longer appears in the top cumulative profile; the next visible costs are
  PPE cuSPARSE analysis/solve and active q-candidate volume evaluation.

## SOLID/A3

- [SOLID-S] The kernel is scoped to the local swept-strip area map; face
  cochain assembly remains in the existing swept-flux constructor.
- [SOLID-D] Dispatch depends on backend capability and dtype, not experiment
  names or YAML routes.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance,
  solver route, YAML-owned numerical choice, nonuniform-grid contract,
  interface-tracking grid-rebuild contract, main merge, or branch deletion
  changed.
