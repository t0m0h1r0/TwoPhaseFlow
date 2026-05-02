# CHK-RA-DC-IMPL-001 — Chapter 7/9 DC implementation audit

Verdict: PASS AFTER FIX. Chapter 7 viscous Helmholtz DC and Chapter 9 PPE DC
now follow the paper's high-residual defect-correction contract on uniform and
nonuniform grids. The audit found one real implementation defect in periodic
nonuniform face metrics; it was fixed in `cee34e92`.

## Scope

- Branch: `ra-dc-implementation-audit-20260502`
- id_prefix: `RA-DC-IMPL`
- Classification: FULL-PIPELINE, ResearchArchitect implementation audit
- Paper evidence:
  `paper/sections/07_time_integration.tex`,
  `paper/sections/09b_split_ppe.tex`,
  `paper/sections/09d_defect_correction.tex`,
  `paper/sections/09e_ppe_bc.tex`,
  `paper/sections/09f_pressure_summary.tex`
- Code evidence:
  `src/twophase/simulation/viscous_predictors.py`,
  `src/twophase/simulation/viscous_helmholtz_dc.py`,
  `src/twophase/ppe/defect_correction.py`,
  `src/twophase/ppe/fd_direct.py`,
  `src/twophase/ppe/ppe_builder_helpers.py`,
  `src/twophase/ppe/fccd_matrixfree.py`,
  `src/twophase/ccd/fccd.py`,
  `src/twophase/coupling/interface_stress_closure.py`

## Paper Contract

The common DC contract in Chapter 7 is:

1. high system: `A_H x = b`;
2. residual/defect: `r = b - A_H x`;
3. correction equation: `A_L delta = r`;
4. update: `x <- x + omega delta`;
5. accuracy is judged by the high residual, not by the formal order of `A_L`.

For viscosity, Chapter 7 instantiates this as
`A_H = I - tau L_{nu,H}` and requires the low Helmholtz correction operator to
share `mu`, `rho`, boundary topology, and the interface-band structure.

For PPE, Chapter 9 instantiates this as `A_H = L_H` and `A_L = L_L`, with
CCD/FCCD high residual evaluation and low-order FD correction. For
phase-separated pressure-jump PPE, the nonuniform-grid contract is stronger:
PPE RHS and velocity correction must use the same face, same coefficient,
same local face distance `H_f`, and the same nonuniform divergence
`D_f^nu(alpha_f B_f)`.

## Implementation Audit

### Chapter 7 viscous Helmholtz DC

- `ImplicitBDF2ViscousPredictor.predict_bdf2()` builds the BDF2 affine RHS
  with `dt_effective = 2/3 dt`, matching the Helmholtz form.
- `ViscousHelmholtzDCSolver._residual_components()` evaluates the high residual
  through `ViscousTerm._evaluate()`, so the fixed point is the full high-order
  viscous operator rather than the low Helmholtz approximation.
- `_LowOrderViscousHelmholtzSolver` assembles `A_L` from the same `mu`, `rho`,
  Reynolds number, boundary topology, and physical grid coordinates.
- The nonuniform low-order stencil uses
  `2 mu_f / (Delta x_side (Delta x_left + Delta x_right))`, which is the
  second-order conservative variable-spacing diffusion form. This is the right
  low-order correction map for DC: it does not claim high spatial order, but it
  is a coefficient- and metric-consistent approximate inverse.

Conclusion: Chapter 7 implementation conforms. The implementation counts
`max_corrections` as residual-correction sweeps after an initial low-order
Helmholtz estimate; this is a sweep-count convention, not a fixed-point change.

### Chapter 9 PPE DC

- `PPESolverDefectCorrection.solve()` prepares the high operator, solves with a
  distinct lower-order base solver, then evaluates every outer defect as
  `rhs - operator.apply(pressure)`.
- The constructor rejects same-operator wrapping, enforcing the paper's
  `L_H` residual / `L_L` correction split.
- `PPESolverFDDirect` factors the low-order FD matrix once per outer DC solve
  and reuses it for all correction RHSs, matching the paper's fixed low-order
  correction map.
- Affine jump closure is applied once to the high-operator RHS, and the DC
  wrapper defers jump application inside the wrapped solvers so the known
  jump term is not double-counted.

Conclusion: Chapter 9 PPE DC conforms after the nonuniform periodic metric fix
below. As with viscosity, `max_corrections` is an implementation sweep-count
parameter around the low-order base estimate; residual monitoring remains on
the high operator.

## Nonuniform-Grid Finding

Finding: FAIL before `cee34e92`, PASS after fix.

The nonperiodic nonuniform path was correct:

- `PPEBuilder` used `a_f / (d_f dV_i)` for low-order FD rows.
- `PPESolverFCCDMatrixFree` used nodal control-volume widths for wall rows.
- `signed_pressure_jump_gradient()` used the physical face distance
  `grid.coords[axis][1:] - grid.coords[axis][:-1]` for `B_f`.

However, periodic nonuniform axes had two metric defects:

1. `FCCDSolver.face_divergence()` divided periodic nonuniform flux differences
   by the outgoing face width `H_i`, not the periodic nodal control-volume width
   `0.5(H_{i-1}+H_i)`.
2. `PPEBuilder` used a uniform `h=L/N` coefficient for the periodic wrap face,
   and used a nonperiodic half-cell volume at node 0.

This violated the Chapter 9 nonuniform requirement that the PPE and corrector
share the same physical face distance and nonuniform divergence. The fix:

- uses periodic nodal control-volume width in FCCD periodic nonuniform
  divergence;
- uses local wrap-face distance `H_{N-1}` and periodic nodal volumes in the
  low-order FD `L_L` wrap row;
- adds regression coverage for both high-order FCCD face divergence and the
  low-order FD matrix used by DC.

## Residual Risk

- Fully periodic nonuniform production routes existed in `experiment/ch14`, so
  this was not a dead code path.
- Existing broader remote `make test` currently fails for unrelated repository
  state, including missing ch13/ch14 config filenames and known non-DC
  stability tests. The two new targeted regression tests pass locally.
- No tested code was deleted. [SOLID-X] Project map path drift was found for
  viscous DC and corrected in `docs/01_PROJECT_MAP.md`.

## Validation

- PASS: `git diff --check`
- PASS: `cd src && /Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 -m pytest twophase/tests/test_fccd.py::test_periodic_nonuniform_face_divergence_uses_control_volume_width twophase/tests/test_fvm_matrixfree.py::test_ppe_builder_periodic_nonuniform_wrap_uses_control_volume_width -q`
- PASS result: `2 passed in 0.32s`

