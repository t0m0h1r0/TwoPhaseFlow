# CHK-RA-CH4-IMPL-001 — Chapter 4 implementation fidelity audit

Date: 2026-05-02  
Worktree: `.claude/worktrees/ra-ch4-implementation-audit-20260502`  
Branch: `ra-ch4-implementation-audit-20260502`  
Holder: ResearchArchitect

## Verdict

PASS AFTER FIX.

The library now conforms to the Chapter 4 CCD-family description for the
audited implementation scope: base CCD, wall/periodic closure, DCCD
post-filter, UCCD6, FCCD, and the face-jet API. The only true library
divergence found was in DCCD filtering: the implementation used a fixed
coefficient and filtered wall/outflow boundary derivative nodes, whereas
Chapter 4 requires the adaptive switch
`eps_d(i)=eps_d,max*(2*psi_i-1)^2` and leaves non-periodic boundary derivative
nodes unfiltered. This was fixed.

## A3 Traceability

| Paper equation / statement | Discretisation invariant | Code path | Result |
|---|---|---|---|
| `eq:CCD_I`, `eq:CCD_II`, `eq:coef_CCD` | Chu--Fan coefficients `(7/16, 15/16, 1/16, -1/8, 3, -9/8)` | `src/twophase/ccd/ccd_solver.py`, `src/twophase/ccd/ccd_solver_helpers.py` | PASS |
| `eq:bc_left`, `eq:bcII_left`, appendix `eq:bcII_left_h4` | Eq-I one-sided closure; Eq-II six-point `O(h^4)` implementation default for `n_pts>=6`, `O(h^2)` fallback | `src/twophase/ccd/ccd_solver.py` | PASS; Chapter 4 prose clarified |
| `eq:dccd_filter_transfer`, `eq:adaptive_eps`, `alg:dccd` | DCCD transfer function with adaptive `S(psi)` and unfiltered wall/outflow boundary derivative nodes | `src/twophase/levelset/advection_dccd.py`, `src/twophase/levelset/advection_kernels.py`, `src/twophase/levelset/curvature.py`, `src/twophase/levelset/curvature_psi.py` | PASS AFTER FIX |
| `eq:uccd6_semidiscrete`, `eq:uccd6_symbol`, `eq:uccd6_energy_id` | `-a D1 - sigma |a| h^7 (D2)^4` with non-positive hyperviscosity symbol | `src/twophase/ccd/uccd6.py`, `src/twophase/ns_terms/uccd6_convection.py` | PASS |
| `eq:fccd_matrix_system`, `eq:face_value_formula`, `eq:face_grad_formula`, `eq:face_second_formula` | Face value/gradient/second-derivative jet from shared CCD `q=u''` | `src/twophase/ccd/fccd.py`, `src/twophase/ccd/fccd_helpers.py` | PASS |

## Findings and Fixes

### F1 — DCCD adaptive switch missing

Severity: MAJOR.  
Status: FIXED.

Paper §4 defines DCCD adaptive strength as
`eps_d(i)=eps_d,max*(2*psi_i-1)^2`, so filtering vanishes at the interface
`psi=0.5` and reaches the configured maximum in bulk. The previous
`DissipativeCCDAdvection` path passed a scalar `eps_d` to the fused stencil for
all nodes. Curvature DCCD helper paths likewise used the scalar coefficient.

Fix:

- Added `_dccd_adaptive_filter_stencil()` so the advection hot path evaluates
  the adaptive DCCD update in one fused CPU/GPU elementwise expression.
- Extended `_dccd_filter_nd()` with an optional `switch` argument for curvature
  derivative filters.
- Passed `S(psi)` from `CurvatureCalculator` and `CurvatureCalculatorPsi`.

### F2 — DCCD wall/outflow boundary nodes were filtered

Severity: MAJOR.  
Status: FIXED.

Paper `alg:dccd` states that periodic boundaries use wrap indices, while
wall/outflow boundary derivative nodes keep the pre-filtered CCD value. The
previous advection and curvature helper paths filtered boundary nodes through
ghost padding or one-sided neighbour weights.

Fix:

- `DissipativeCCDAdvection` restores the filtered derivative boundary nodes to
  the original CCD derivative for non-periodic axes.
- `_dccd_filter_nd()` leaves non-periodic boundary faces unchanged after the
  dimension-split filter pass.

### F3 — Chapter 4 boundary prose lagged the implemented Eq-II closure

Severity: PAPER CONSISTENCY.  
Status: FIXED IN PAPER.

The implementation and appendix use the six-point `O(h^4)` Eq-II boundary
closure when `n_pts>=6`, with the four-point `O(h^2)` formula retained as a
small-grid fallback. The Chapter 4 boundary overview still described
`O(h^2)` as the adopted Eq-II closure. The paper prose was clarified to state
that the `O(h^2)` analysis is the conservative minimal-closure bound, while the
implementation default is the appendix `O(h^4)` upgrade.

## GPU Optimisation Audit

PASS.

- The new DCCD advection adaptive update is a fused backend kernel via
  `backend.fuse`, so CuPy executes the switch and filter update without a host
  round trip.
- Boundary preservation uses device slicing assignments only.
- Curvature adaptive DCCD filtering keeps `switch` and filtered fields in
  `backend.xp`; no NumPy conversion or host scalarisation was introduced.
- Remote CuPy smoke on host `python` confirmed `Backend(use_gpu=True)`, CUDA
  output arrays for DCCD RHS and curvature filter helper, and exact zero errors
  for interface-switch and boundary-preservation checks.

## Validation

- `git diff --check`: PASS.
- Targeted local pytest:
  - `twophase/tests/test_ccd.py`
  - `twophase/tests/test_uccd6.py`
  - `twophase/tests/test_fccd.py`
  - DCCD adaptive/boundary targeted tests
  - Result: `48 passed in 12.41s`.
- Remote CuPy smoke:
  - `gpu True`
  - `cuda True True`
  - `errors 0.0 0.0 0.0`

## SOLID Audit

[SOLID-X] No production class boundary expansion beyond existing DCCD
responsibilities. The adaptive switch was implemented as a narrow kernel/helper
extension and injected through existing call sites. No tested implementation was
deleted; compatibility export of `_dccd_filter_stencil` remains intact.

