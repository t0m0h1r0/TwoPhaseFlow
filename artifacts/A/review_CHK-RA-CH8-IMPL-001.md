# CHK-RA-CH8-IMPL-001 — Chapter 8 Implementation Audit

Date: 2026-05-02
Branch: `ra-ch8-implementation-audit-20260502`
Verdict: PASS AFTER FIX

## Scope

- Paper: `paper/sections/08_collocate.tex`, `paper/sections/08b_pressure.tex`, `paper/sections/08c_bf_failure.tex`, `paper/sections/08d_bf_seven_principles.tex`, `paper/sections/08e_fccd_bf.tex`
- Library: `src/twophase/ppe/fccd_matrixfree.py`, `src/twophase/ppe/fccd_matrixfree_helpers.py`, `src/twophase/coupling/interface_stress_closure.py`, `src/twophase/simulation/divergence_ops.py`, `src/twophase/simulation/ns_step_services.py`, `src/twophase/simulation/ns_operator_stack.py`
- Focus: variable-density IPC PPE, P-1/P-2/P-4/P-6 Balanced--Force principles, FCCD face-flux projection, affine pressure-jump closure, non-uniform physical metrics, GPU hot path.

## Findings

- The standard Chapter 8 stack now enters the FCCD face subsystem through Chapter 7 defaults: FCCD PPE, phase-separated coefficient, affine jump, pressure-jump surface tension, and automatic face-flux projection when FCCD PPE is active.
- PPE assembly and velocity correction share the same face space: `PPESolverFCCDMatrixFree._apply_operator_core` applies `D_f[(1/rho)_f G_f p]`, and `FCCDDivergenceOperator.pressure_fluxes/project_faces` uses the same face gradient and coefficient path.
- The non-uniform wall path uses physical face spacing and nodal control-volume widths in both PPE and projection, so the adjoint face-pair remains metric-consistent instead of reverting to uniform-grid CCD.
- The affine pressure jump implements `G_Γ(p;j)=G(p)-B_Γj` with `j_gl=p_gas-p_liquid=-σ κ_lg`; PPE RHS and corrector both receive the same interface-stress context.
- Divergence found: `FCCDDivergenceOperator.pressure_fluxes` accepted only internal `"fccd"` but not the public `"fccd_flux"` scheme name, causing direct API callers to fall through to FVM face gradients. This silently changed the BF locus and violated P-1/P-2 and the no-fallback policy.
- Divergence found: invalid face-gradient, coefficient, or interface-coupling names could silently select a different projection path. These are now rejected explicitly.
- GPU issue found: CUDA memory-pool warning path referenced `sys.stderr` without importing `sys`; this is fixed so GPU setup remains fail-closed but diagnosable.

## Fixes

- Added explicit face-gradient canonicalization for FCCD projection: `"fccd"`, `"fccd_flux"`, and `"fccd_nodal"` all select the FCCD face-gradient path; unsupported names raise `ValueError`.
- Added explicit validation for FCCD projection coefficient and interface-coupling schemes, including rejection of `phase_density` with non-`none` interface coupling.
- Added FVM projection validation so the FVM corrector cannot silently accept a non-FVM face-gradient request.
- Added CPU tests for public `"fccd_flux"` PPE/projection equivalence and fail-closed option validation.
- Added GPU smoke coverage proving public `"fccd_flux"` pressure fluxes remain CuPy arrays.

## A3 Traceability

- Equation `eq:PPE_varrho` -> `PPESolverFCCDMatrixFree.apply/_apply_operator_core`: variable-density PPE as `D_f[(1/rho)_f G_f p]`.
- Principles P-1/P-2 -> `FCCDDivergenceOperator.pressure_fluxes/project_faces`: same face `G_f p` feeds PPE-consistent velocity correction.
- Principle P-4 / equation `eq:bf_beta_harmonic` -> `build_fccd_face_inverse_density` and `FCCDDivergenceOperator.pressure_fluxes`: shared `2/(rho_L+rho_R)` face coefficient.
- Principle P-6 / equation `eq:bf_p6_gfm` -> `signed_pressure_jump_gradient` and affine RHS/corrector wiring: pressure jump is injected into the same face-gradient footprint.

## Non-Uniform And GPU Check

- Non-uniform support is compliant: all audited Chapter 8 face operators use `grid.coords`-derived physical distances and node widths.
- GPU support is compliant: FCCD face gradients, coefficients, affine-jump gradients, and fused weighted-divergence kernels operate in the active backend namespace; no CPU fallback was added.
- Public `"fccd_flux"` projection now remains on device for CuPy inputs.

## Validation

- `git diff --check` — PASS.
- Remote CPU pytest — PASS: `test_fccd_projection_divergence_matches_ppe_operator_nonuniform_wall`.
- Remote CPU pytest — PASS: `test_fccd_projection_rejects_unknown_face_options`.
- Remote CPU pytest — PASS: `test_phase_separated_fccd_projection_matches_ppe_operator_nonuniform_wall`.
- Remote CPU pytest — PASS: `test_affine_jump_corrector_forwards_interface_context`.
- Remote CPU pytest — PASS: `test_affine_jump_pressure_stack_one_step_no_nan`.
- Remote GPU pytest — PASS: `test_fccd_pressure_flux_public_scheme_stays_on_gpu`.
- Remote GPU pytest — PASS: `test_fccd_matrixfree_phase_density_keeps_gpu_density_device`.
- Remote GPU pytest — PASS: `test_ch7_default_ns_stack_constructs_on_gpu`.

## SOLID-X

- [SOLID-X] No tested implementation was deleted.
- [SOLID-X] The patch narrows responsibilities at the API boundary by validating scheme contracts before projection work starts.
- [SOLID-X] No hidden fallback remains in the audited Chapter 8 face-projection option path.
