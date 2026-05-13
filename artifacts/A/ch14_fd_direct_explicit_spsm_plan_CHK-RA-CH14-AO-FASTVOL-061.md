# CHK-RA-CH14-AO-FASTVOL-061 - Explicit FD-direct SpSM solve-plan reuse

## Question

User asked whether WIKI-L-044 item #3 has side effects, requested an update only
if the theory supports it, and clarified that the design should not manage reuse
as a cache.  The selected design is therefore an explicit prepared solve flow:
`prepare_operator(rho)` creates the current low-order factor and its GPU
triangular solve plans; subsequent defect-correction RHS vectors use that
prepared object directly.

## Theory review

The pressure defect-correction contract is

```text
p^{k+1} = p^k + L_L^{-1}(r^k),  r^k = b - L_H(p^k),
```

where `L_L` is the pinned low-order conservative FD operator and `L_H` is the
selected high-order PPE operator.  Reusing work is exact only while `L_L` itself
is fixed.  If grid metrics, boundary topology, density coefficients, pin/gauge
choice, or jump context change, a previous factor or sparse analysis no longer
represents the same linear map and must not be used.

The safe first slice is narrower than an operator-epoch cache.  During a single
explicit call to `PPESolverFDDirect.prepare_operator(rho)`, the matrix triplets
are already fixed and `splu` has already produced exact triangular factors
`P_r L U P_c`.  cuSPARSE SpSM analysis depends on the sparse triangular factor,
operation flags, dtype, and RHS shape, but not on the numerical contents of a
later RHS vector.  Therefore the lower and upper SpSM analyses can be performed
once when that factor is prepared and then used for each vector RHS in the
defect-correction loop.

This is not a cache: there is no dictionary, approximate key, cross-solver
lookup, or silent hit/miss policy.  A new `prepare_operator(rho)` creates a new
prepared solve object.  `update_grid` and `invalidate_cache` drop the old object
with the factor.  Unsupported GPU conditions fail closed instead of falling back
to a slower or different production path.

## Hypotheses checked

| Hypothesis | Risk | Resolution |
|---|---|---|
| H1: Reusing analysis after grid or coefficient changes could solve the wrong operator. | Violates the PDE/discretization contract. | Avoided by scope: the plan is owned by the prepared factor object and is discarded with `_factor`; no independent epoch cache was added. |
| H2: A hidden cache could mask stale or wrong equality logic. | Hard-to-detect wrong reuse. | Avoided by design: reuse is the direct control flow from `prepare_operator` to `solve`, not a lookup. |
| H3: Batched or matrix RHSs could require a different dense descriptor analysis. | cuSPARSE descriptor mismatch or wrong result. | Fail-closed: the prepared plan supports only vector RHS shape `(n, 1)` and rejects higher-rank RHSs. |
| H4: Transposed or conjugate solves could need different triangular operation flags. | Wrong triangular solve. | Fail-closed: the prepared SuperLU flow supports only `trans='N'`, which is the current PPE/DC path. |
| H5: CSC triangular factors could be analysed with the wrong fill mode. | Lower/upper orientation error. | Addressed by matching CuPy's SpSM canonicalization: CSC factors are represented as transposed CSR-like factors with fill mode and transpose flag adjusted together. |
| H6: Repeated RHS solves might still re-run analysis internally. | No performance win. | Regression test checks `analysis_count == 2` after preparation and remains unchanged after a second RHS solve; cProfile confirms `spSM_analysis` calls drop sharply on the capillary route. |

## Implementation

- `src/twophase/ppe/fd_direct.py`
  - `PPESolverFDDirect.prepare_operator(rho)` still builds and factorizes the
    current low-order FD matrix.  On GPU only, the raw CuPy SuperLU factor is
    wrapped in `_PreparedCuPySuperLUSolve`.
  - `_PreparedCuPySuperLUSolve` prepares one lower and one upper
    `_PreparedCuPySpSMPlan` for vector RHSs.  Its `solve` method applies the
    same SuperLU permutations and triangular sequence as the CuPy factor solve.
  - `_PreparedCuPySpSMPlan` creates cuSPARSE dense/sparse descriptors, runs
    `spSM_analysis` once, and then uses `spSM_solve` for each RHS vector.
  - Unsupported GPU states fail closed: no SpSM support, non-CuPy RHS,
    non-vector RHS, unsupported transpose, unsupported sparse factor format, or
    unsupported dtype raises.
- `src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  - Added a real CuPy regression comparing the prepared solve flow against the
    raw CuPy SuperLU solve for two RHS vectors and verifying that analysis count
    is not increased by the second solve.

## Validation

- Local syntax:
  `python3 -m py_compile src/twophase/ppe/fd_direct.py src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  PASS.
- Whitespace:
  `git diff --check` PASS.
- Remote targeted prepared-plan gate:
  `pytest -q src/twophase/tests/test_geometric_runtime_gpu_gates.py::test_gpu_fd_direct_uses_explicit_spsm_solve_plan_for_same_factor`
  PASS (`1 passed`).
- Remote GPU gate file:
  `pytest -q src/twophase/tests/test_geometric_runtime_gpu_gates.py`
  PASS (`11 passed`).
- Remote full suite:
  `make test` PASS (`953 passed, 3 skipped`).
- Remote 10-step capillary cProfile:
  `experiment/ch14/diagnose_ao_stage_chain.py --config experiment/ch14/config/ch14_capillary.yaml --steps 10 --runner-initial-grid-rebuild --backend gpu`
  PASS.  Total cProfile time improved from CHK-060 `6.881 s` to `5.417 s`.
  `cupy_backends.cuda.libs.cusparse.spSM_analysis` dropped from `842` calls
  (`1.590 s`) after CHK-060 to `102` calls (`0.203 s`).  The remaining analysis
  calls correspond to new prepared factors, each with one lower and one upper
  plan, rather than per-RHS analysis.

## SOLID/A3

- [SOLID-S] The change is isolated to the FD-direct low-order solve path used by
  defect correction; high-order PPE, active geometry, swept flux, and YAML
  solver selection are unchanged.
- [SOLID-D] The wrapper depends on the backend's prepared CuPy factor and
  cuSPARSE capabilities rather than on experiment names or physical cases.
- [SOLID-X] No physical parameter, CFL, damping, smoothing, tolerance,
  iteration limit, solver route, YAML-owned numerical choice, nonuniform-grid
  contract, interface-tracking grid-rebuild contract, hidden sparse cache, main
  merge, or branch deletion changed.
