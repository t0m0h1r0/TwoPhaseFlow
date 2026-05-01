# CHK-RA-GPU-UTIL-003 — ch14 FD L_L factor reuse

## Trigger

User pointed out that using `FVM direct` as the defect-correction base solver
is not the paper-faithful low-order `L_L` correction path.  The target remains
the existing ch14 capillary YAML with `schedule=1`.

## Finding

The previous true-DC repair restored the outer algorithm (`L_H` residual plus
`L_L` correction), but configured `base_solver.discretization: fvm` /
`kind: direct`.  That path rebuilt and refactorized the low-order sparse
operator for the initial solve and every defect correction RHS.

Matrix-free `L_L` alternatives were tested and rejected for production:

- GMRES/Jacobi and GMRES/line-PCR were fast only when allowed to return
  inexact corrections, but left `div_u ≈ 1e-2`.
- Fixed line sweeps reached 7--14 s but left `div_u ≈ 4e-3` to `6e-3`, and
  stronger variants blew up.
- CG on `-L_L` was slower than the direct path and still inexact at the tested
  cap.

## Implementation

- Added `PPESolverFDDirect` as the FD `L_L` correction solver.
- The solver factors the pinned low-order FD matrix once in
  `prepare_operator(rho)` and reuses the factor for all RHSs inside one outer
  defect-correction solve.
- `PPESolverDefectCorrection` now calls `base_solver.prepare_operator(rho)`
  before the base solve when the base exposes it.
- ch14 capillary/rising-bubble/Rayleigh--Taylor YAMLs now use
  `base_solver.discretization: fd`, `kind: direct`.
- `fvm_direct` is rejected as a DC base solver; `fd_direct` is the paper
  low-order direct path.

## Validation

- `make test PYTEST_ARGS='-k defect_correction -q'` — 8 passed.
- ch14 capillary `schedule=1`, N=128, 12-step probe:
  - Previous true DC with `FVM direct`: `46.522 s`, `div_u≈5.8e-6`.
  - New `FD direct` factor reuse: `9.877 s`, `div_u≈5.8e-6`.
  - Speedup versus previous true DC: `4.71x`.
  - Speedup versus original 27.734 s schedule=1 baseline: `2.81x`.
- GPU monitor on the same probe with `TWOPHASE_USE_GPU=1`:
  - `real 9.56 s`
  - average GPU utilization `47.3%`
  - samples ≥50%: `40.0%`
  - samples ≥80%: `30.0%`
  - max memory `388 MiB`

## Conclusion

The original 80% average GPU utilization target is still not met at N=128, but
the paper-correct path is now faster than both the previous true-DC direct path
and the earlier GMRES-collapse timing, while retaining the direct `L_L` residual
quality.

[SOLID-X] no SOLID violation found; the new solver is an additive `IPPESolver`
implementation, and the DC wrapper depends only on the optional
`prepare_operator` capability.
