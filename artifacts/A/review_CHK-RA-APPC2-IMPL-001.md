# CHK-RA-APPC2-IMPL-001 — Appendix C.2 Implementation Audit

Date: 2026-05-03
Branch: `ra-appc2-implementation-audit-20260503`
Verdict: PASS WITH PAPER CLARIFICATION

## Scope

- Paper: `paper/sections/appendix_ccd.tex`, `paper/sections/appendix_ccd_impl_s1.tex`, `paper/sections/appendix_ccd_impl_s4.tex`, with cross-checks against §4.6 FCCD, Appendix C.1 boundary coefficients, and §9 split-PPE/HFE.
- Library: `src/twophase/ccd/ccd_solver.py`, `src/twophase/ccd/ccd_solver_helpers.py`, `src/twophase/ccd/fccd.py`, and C.2-adjacent tests.
- Research memo: cubic Hermite face interpolation, split-phase PPE/GFM/HFE ghost closure, and no-slip one-sided compact wall closure with free `alpha`.
- Focus: paper-exact boundary handling, hidden-fallback rejection, periodic topology, interface-vs-domain-boundary separation, non-uniform metric consistency, and GPU residency.

## Findings

- Confirmed: Appendix C.2.1 describes ghost cells as an alternative implementation only. The library standard path is the boundary-scheme method, matching `CCDSolver(..., bc_type="wall")`; this is consistent with the paper and should not be replaced by ghost cells.
- Confirmed: Appendix C.2.2 periodic CCD is implemented as a `2N x 2N` block-circulant solve over unique nodes, with node `N` synchronized to node `0` after the solve.
- Confirmed: wall one-sided CCD is paper-exact: Equation-I uses the unique `alpha=3/2` `O(h^5)` closure, Equation-II uses the six-point `O(h^4)` formula, and axes with too few points are rejected rather than silently downgraded.
- Memo correction: the cubic Hermite face formula from endpoint values and first derivatives is a different face interpolant. It has compatible formal face order for smooth data, but it is not the paper’s FCCD operator, which is defined by the second-derivative cancellation `D1 u - D2 q`.
- Memo correction: split-phase PPE with Young--Laplace jumps and HFE/GFM ghost jets is an interface closure belonging to Chapter 9/11, not an Appendix C.2 domain-boundary ghost-cell replacement.
- Memo correction: choosing a free wall-closure `alpha` for stability would change the CCD boundary scheme and lower the paper-exact guarantee unless it reduces to `alpha=3/2`; no such fallback or retuning was introduced.

## Changes

- Added an Appendix C.2 scope warning to separate domain-boundary CCD ghost cells from FCCD face jets, split-PPE/HFE interface closure, and free-`alpha` one-sided wall formulas.
- Added direct CPU coverage for periodic CCD unique-node topology, image-node synchronization, and smooth derivative accuracy.
- Added GPU smoke coverage for periodic CCD differentiation staying on CuPy arrays and matching CPU within roundoff; retained existing periodic FCCD GPU smoke.

## A3 Traceability

- Equation: Appendix C.2 periodic equations `eq:ccd_periodic` and `eq:rhs_periodic`; Appendix C.1 boundary derivation `app:ccd_bc_derivation_I` / `app:ccd_bc_derivation_II_h4`; FCCD matrix equation `eq:fccd_matrix_system`.
- Discretization: periodic CCD uses wrapped `i±1 mod N` neighbors and a block-circulant LU; wall CCD uses the derived one-sided compact boundary rows; FCCD face gradient uses nodal CCD curvature `q`.
- Code: `build_ccd_axis_solver_periodic`, `differentiate_ccd_periodic`, `_boundary_coeffs_left`, `_boundary_coeffs_right`, `FCCD.face_gradient`, `FCCD.face_value`.
- Tests: `test_periodic_ccd_uses_unique_cyclic_nodes`, `test_ccd_periodic_differentiation_gpu_matches_cpu`, existing FCCD periodic convergence and GPU smoke tests.

## GPU / Non-Uniform Check

- Periodic CCD allocates the circulant matrix on `backend.xp` and uses `backend.linalg.lu_factor` / `lu_solve`, which route to `cupyx.scipy.linalg` on GPU.
- Periodic RHS construction uses `xp.roll`, `xp.empty`, and device arrays; the solve result and image-node copy remain backend-native.
- FCCD face kernels are fused and use per-face physical spacing broadcasts on non-uniform axes; periodic face divergence uses nodal control-volume widths.
- No CPU fallback was added. The only GPU tolerance change is a test tolerance for sub-`1e-12` second-derivative roundoff near analytic zeros.

## Validation

- `git diff --check` PASS.
- Remote targeted CPU pytest PASS: `test_wall_ccd_rejects_lower_order_eqii_fallback`, `test_periodic_ccd_uses_unique_cyclic_nodes`, `test_face_gradient_convergence_rate`, `test_upwind_face_value_taylor_hfe_order`.
- Remote GPU pytest PASS: `test_ccd_periodic_differentiation_gpu_matches_cpu`, `test_fccd_periodic_advection_rhs_gpu_matches_cpu`.
- Paper build PASS: `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` produced `paper/main.pdf` (241 pages).
- Note: an attempted `make test PYTEST_ARGS=<node paths>` expanded to the full remote suite because `remote.sh test` prepends `twophase/tests`; the C.2 target tests passed in that run before unrelated existing failures surfaced. It is not used as the acceptance signal for this CHK.

## SOLID-X

- [SOLID-X] No new violation found. The library algorithm boundary was not changed; tests were added at the existing CCD/FCCD test layer, and the paper note clarifies scope instead of adding runtime branching.
