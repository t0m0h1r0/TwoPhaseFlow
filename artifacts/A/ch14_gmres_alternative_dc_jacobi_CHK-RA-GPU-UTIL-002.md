# CHK-RA-GPU-UTIL-002 — restore true grid-defect correction for ch14 PPE

## Question

Can the ch14 capillary `schedule=1` route replace GMRES with a grid-defect / defect-correction style method, or even a Jacobi solver, for speed?

User correction: if `solver.kind: defect_correction` is configured but the implementation collapses to the same FCCD GMRES solve, that is a paper-fidelity bug. The paper requires `L_H` residual evaluation and `L_L` correction solves.

## Current state

Before this fix, the existing YAML selected a defect-correction wrapper:

- `experiment/ch14/config/ch14_capillary.yaml`: `solver.kind: defect_correction`
- base solver: `method: gmres`
- preconditioner: `jacobi`

So Jacobi was present, but only as a GMRES preconditioner. It was not the outer solver.

The capillary route used the same FCCD matrix-free class as both base solver and target operator. Because the affine-jump path would otherwise solve the same operator repeatedly, `PPESolverDefectCorrection` collapsed this case into a single stricter base solve. Therefore, the hot path remained backend GMRES on the FCCD operator. This is no longer accepted.

## Jacobi as a standalone solver

Standalone Jacobi is still rejected for this route.

For a Poisson operator on an `N x N` grid, plain Jacobi has spectral radius approximately

`rho_J ~= cos(pi / N)`.

Estimated iterations:

| N | `rho_J` | iterations to `1e-6` | iterations to `1e-8` |
|---:|---:|---:|---:|
| 64 | 0.99879546 | 11,463 | 15,283 |
| 128 | 0.99969882 | 45,864 | 61,152 |
| 256 | 0.99992470 | 183,470 | 244,627 |

At `N=128`, the current capillary grid would need tens of thousands of stencil sweeps for solver-level accuracy. A 500-iteration Jacobi cap would mostly leave low-frequency pressure error intact. Weighted Jacobi improves smoothing of high-frequency error, but does not fix the low-frequency Poisson bottleneck without multigrid.

Using Jacobi alone may raise apparent GPU activity, but it would be slower and less accurate. That violates the speed objective and risks projection error.

## Grid-defect / defect-correction replacement

A true defect-correction method is theoretically admissible in the following form:

1. Evaluate residual with the production high-order operator `L_H`:
   `d^k = b - L_H p^k`.
2. Solve a lower-order correction equation accurately:
   `L_L delta p = d^k`.
3. Update with stable relaxation:
   `p^{k+1} = p^k + omega delta p`.

The paper's DC theory requires the final residual to be judged against `L_H`, and the relaxation must respect the spectral condition. The paper analysis gives `omega < 2/2.4 ~= 0.833`; `omega=1` is not safe for true `L_L`-based DC.

For the current capillary route this means:

- `L_H` is the FCCD matrix-free affine-jump operator.
- `L_L` is the lower-order FVM/FD direct operator.
- The DC wrapper must not collapse same-operator base/target pairs.
- Relaxation is set to `0.7`, below the paper stability bound `2/2.4 ~= 0.833`.
- Approximate Jacobi/ADI sweeps remain valid only as future preconditioner/smoother candidates, not as the production correction solve.

## Implementation decision

Implemented the paper-faithful route:

- The config parser now tracks a separate `ppe_dc_base_solver`.
- FCCD defect correction rejects `base_solver.discretization: fccd` / `kind: iterative` same-operator bases.
- `PPESolverDefectCorrection` rejects same-operator construction instead of silently collapsing.
- ch14 capillary/rising-bubble/Rayleigh--Taylor YAMLs now use:
  - target: FCCD matrix-free operator
  - base: `discretization: fvm`, `kind: direct`
  - relaxation: `0.7`
- ch14 README documents the `L_H`/`L_L` contract and the stability margin.

## Validation

- `make test PYTEST_ARGS='-k defect_correction -q'` — 7 passed.
- `make test PYTEST_ARGS='-k ch14_capillary_yaml_uses_true_low_order_defect_base -q'` — 1 passed.
- Smoke: temporary ch14 capillary N=32, `schedule=1`, true DC/FVM-direct base, 2 steps completed to `t=0.0100`.

## Speed implication

This change is correctness-first. It may not improve GPU utilization immediately because sparse direct `L_L` correction is less GPU-saturating than GMRES matvecs at small `N`. However, it restores the paper's algorithm. Future speed work should optimize the `L_L` correction path itself, for example with a GPU-resident line/PCR or multigrid preconditioner that still sits inside the true `L_H` residual / `L_L` correction contract.

[SOLID-X] no SOLID violation found; solver responsibilities remain split between config/runtime factory and PPE solver classes.
