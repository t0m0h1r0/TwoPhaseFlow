# CHK-RA-SRC-001 — `src/` Paper-Fidelity Audit

Date: 2026-04-30  
Branch: `ra-src-paper-audit-20260430`  
Worktree: `.claude/worktrees/ra-src-paper-audit-20260430`  
Scope: `src/twophase/` numerical implementation vs. paper sections and production experiment configs.

## Executive Summary

`src/` is not uniformly paper-exact by default, but the current §14/ch14 YAML stack largely selects the intended production operators explicitly.  The largest risks are not CCD/FCCD algebra; they are interface-stress sign consistency, HFE traceability, and configuration labels that overstate what the runtime actually builds.

Severity key:

- HIGH: likely changes physical result or invalidates paper claim if the path is used.
- MEDIUM: traceability/configuration gap or backend/combination risk.
- LOW: documentation-only or already fixed in this CHK.

## A3 Chain Snapshot

| Paper / design claim | Expected code path | Audit result |
|---|---|---|
| CCD derivatives with metric transform on non-uniform grids | `core/grid.py`, `core/metrics.py`, `ccd/ccd_solver_helpers.py` | PASS with caveat: metric naming is confusing, but implemented transform matches the stated chain rule. |
| FCCD face gradients and face values | `ccd/fccd.py`, `ccd/fccd_helpers.py` | PASS; one stale face-value doc coefficient was fixed from `H²/32` to `H²/16`. |
| UCCD6 momentum convection | `ccd/uccd6.py`, `ns_terms/uccd6_convection.py` | PASS for operator shape and hyperviscosity sign; NS extension uses axiswise `max|u_k|`, consistent with the implementation doc. |
| §14 production stack | ch14 YAMLs, `experiment/ch13/ch14_stack_common.py`, `simulation/config_*` | PARTIAL: explicit configs select FCCD/UCCD6/pressure-jump, but library defaults remain legacy/reduced. |
| Young--Laplace pressure jump `j_gl = p_gas - p_liquid = -σ κ_lg` | `simulation/interface_stress_closure.py`, `ppe/fccd_matrixfree_helpers.py` | MIXED: `affine_jump` is correct; legacy `jump_decomposition` composes the opposite sign for positive `κ_lg`. |
| HFE curvature / field extension | `hfe/field_extension.py`, `simulation/ns_scheme_bootstrap.py`, `levelset/curvature_filter.py` | FAIL for traceability: production “HFE” label currently builds a Laplacian interface filter, not `HermiteFieldExtension`; `HermiteFieldExtension` is uniform-grid only. |
| Non-uniform grid combinations | `core/grid.py`, `ccd/fccd_helpers.py`, V9 config | PARTIAL PASS: grid/FCCD/local-eps paths exist, but HFE and some GPU initial-condition paths are not fully combination-safe. |

## Findings

### HIGH-1 — `jump_decomposition` pressure-jump sign disagrees with paper

Paper contract:

- `paper/sections/09b_split_ppe.tex` defines `[p]Γ = j_gl = -σ κ_lg`.
- The same section states the legacy composition should be `p_legacy = p_tilde + j_gl(1-ψ)`.

Code:

- `src/twophase/simulation/interface_stress_closure.py` correctly builds `pressure_jump_gas_minus_liquid = -sigma * kappa_lg`.
- `src/twophase/ppe/fccd_matrixfree_helpers.py` legacy `jump_decomposition` returns `pressure + sigma * kappa * (1.0 - psi)`.

Impact:

- For the runtime droplet convention, `κ_lg ≈ +1/R`; gas-side pressure receives `+σκ`, while the paper’s `j_gl` requires `-σκ`.
- ch14 YAMLs use `affine_jump`, so the main ch14 configs appear protected.
- `experiment/ch13/ch14_stack_common.py` and `experiment/ch13/exp_V9_local_eps_nonuniform.py` still assert/use `jump_decomposition`, so V6/V9-style “§14 stack” diagnostics can exercise the sign-inverted route.

Recommended fix:

1. Change legacy `jump_decomposition` composition to use `j_gl = -sigma*kappa` or route it through `InterfaceStressContext`.
2. Update tests that currently assert gas-side `+σκ` legacy behavior.
3. Prefer `affine_jump` in all §14-stack helpers.

### HIGH-2 — `psi_direct_hfe` / “HFE curvature” is not actual Hermite Field Extension

Paper/config labels:

- V6/V9/ch14 text and comments describe “HFE curvature” with `psi_direct_hfe`.
- `simulation/config_constants.py` admits only `psi_direct_hfe` as curvature method.

Runtime:

- `simulation/ns_scheme_bootstrap.py` ignores the curvature method string and constructs `CurvatureCalculator(...)`.
- It also constructs `InterfaceLimitedFilter(...)` and binds it as `hfe`.
- `simulation/ns_step_services.py` computes `kappa_raw = curv.compute(psi)`, then `hfe.apply(kappa_raw, psi)`.
- `levelset/curvature_filter.py` implements `q* = q - C h² w(ψ)∇²q`, a curvature smoothing filter.

Actual HFE component:

- `hfe/field_extension.py` implements a Hermite tensor-product extension, but its class docstring says the grid is “2-D, uniform”.
- The implementation uses `hx = L/N`, `hy = L/N` and bracket indices by uniform-grid division.
- It is not wired into the current NS curvature path.

Impact:

- Paper claims that depend on Hermite field extension are not A3-traceable to the production runtime.
- Non-uniform-grid + HFE is not implemented in `HermiteFieldExtension`.
- Existing experiment labels overstate the active method.

Recommended fix:

1. Rename runtime `hfe` fields/comments if the intended production method is only interface-limited smoothing.
2. Or wire a real HFE curvature/extension implementation into the `psi_direct_hfe` option.
3. Add an explicit non-uniform-grid HFE design or mark HFE as uniform-grid-only in paper/configs.

### MEDIUM-1 — Default solver config is legacy/reduced, not paper §14 production

Defaults:

- `simulation/config_models.py` defaults to `advection_scheme="dissipative_ccd"`, `convection_scheme="ccd"`, `ppe_solver="fvm_iterative"`, `surface_tension_scheme="csf"`.
- `simulation/ns_solver_options.py` repeats the same legacy defaults.

Production configs:

- ch14 YAMLs explicitly select FCCD interface transport, UCCD6 convection, FCCD pressure gradient, `pressure_jump`, `fccd_iterative`, `phase_separated`, and `affine_jump`.
- ch13 helper configs select many of the same production operators, but currently keep `jump_decomposition`.

Impact:

- `TwoPhaseNSSolver()` / default config does not represent the paper stack.
- This is acceptable only if the paper’s claim is “the validated §14 YAML stack” rather than “library defaults”.

Recommended fix:

- Add a named `paper_ch14`/`production` preset and make docs explicitly say defaults are conservative legacy defaults.
- Or promote the production stack to defaults after sign/HFE issues are resolved.

### MEDIUM-2 — `ψ`/`φ` convention is split across paper, builder, helper docs, and tests

Paper:

- `paper/sections/03c_levelset_mapping.tex` defines `ψ = Hε(-φ)` and inverse `φ = ε ln((1-ψ)/ψ)`.
- `paper/sections/02c_nondim_curvature.tex` defines the φ-based curvature formula without the leading minus; a circle `φ=r-R` gives `κ_lg=+1/R`.

Runtime:

- `simulation/initial_conditions/builder.py` constructs `ψ = 1/(1+exp(φ_final/eps))`, matching `Hε(-φ_final)`.
- `levelset/heaviside.py` documents and implements `Hε(φ)=1/(1+exp(-φ/eps))`, with inverse `eps*ln(ψ/(1-ψ))`.
- `levelset/curvature.py` inverts the builder-produced `ψ` through the helper, reconstructs effectively `-φ_final`, and applies a leading-minus curvature formula.

Probe:

- A local CPU probe with `R=0.25` gave mean near-interface `κ≈4.012`, so the runtime builder + curvature path produces the paper-sign positive droplet curvature.

Impact:

- The production path appears numerically sign-correct by cancellation.
- Unit tests and helper docs still encode the opposite low-level convention, making A3 traceability fragile.

Recommended fix:

- Split helper names into `heaviside_increasing(phi)` and `cls_from_signed_distance(phi) = H(-phi)`, or update docs/tests so the sign convention is explicit at every call site.

### MEDIUM-3 — GPU initial-condition path is not fully `backend.xp` safe

Observed code:

- `core/grid.py` documents `meshgrid()` returns CuPy arrays on GPU.
- `simulation/initial_conditions/builder.py` passes those arrays into shape primitives.
- `simulation/initial_conditions/shape_primitives.py` uses direct `np.sqrt`, `np.maximum`, `np.arctan2`, `np.cos`, and `np.asarray` in several `sdf()` methods.

Impact:

- CuPy may dispatch some NumPy ufunc calls, but `np.asarray(cupy_array)` is a known unsafe path and can force/forbid host conversion.
- GPU smoke tests do not cover `InitialConditionBuilder` with GPU-grid coordinates.

Recommended fix:

- Convert every primitive SDF to `xp = _xp_like(coords[0])` and use `xp.sqrt`, `xp.maximum`, `xp.arctan2`, `xp.cos`, `xp.asarray`.
- Add a GPU-marked smoke test for `InitialConditionBuilder(...).build(gpu_grid, eps)`.

### LOW-1 — FCCD face-value doc coefficient was stale

Before this CHK:

- `FCCDSolver.face_value()` documented `-(H²/32)(q_lo+q_hi)`.
- `_face_value_kernel()` and `fccd_helpers.build_axis_weights()` implement `H²/16`.
- `SP-D_fccd_advection.md` derives the same `H²/16` coefficient.

Action:

- Fixed `src/twophase/ccd/fccd.py` docstring to `-(H²/16)(q_lo+q_hi)`.

## Non-Uniform Combination Verdict

Implemented and considered:

- Interface-fitted grid rebuild from `ψ` exists in `core/grid.py` for `alpha_grid > 1`.
- Metric reconstruction exists in `core/metrics.py` and CCD metric application exists in `ccd/ccd_solver_helpers.py`.
- FCCD uses per-face `H_i` weights in `ccd/fccd_helpers.py`, matching the cell-centered `θ=1/2`, `μ=0`, `λ=1/24` simplification in `paper/sections/10c_fccd_nonuniform.tex`.
- V9 exercises local epsilon + non-uniform grid + FCCD/UCCD6/pressure-jump configuration.

Not fully implemented or not safely covered:

- Actual `HermiteFieldExtension` is uniform-grid only and not wired into the production curvature path.
- ch13 V9 uses `jump_decomposition`, which has the pressure-jump sign issue above.
- GPU initial-condition shape SDFs are not consistently `xp`-native.

## SOLID / Architecture Audit

[SOLID-X] No new SOLID violations were introduced by this CHK.  The main architectural smell found is naming/contract drift: `hfe` runtime members and `psi_direct_hfe` configs point to a smoothing filter rather than the `hfe.HermiteFieldExtension` implementation.  This is primarily an A3 traceability and contract issue, not a class-responsibility change made here.

## Suggested Remediation Order

1. Fix pressure-jump sign by unifying `jump_decomposition` with `InterfaceStressContext`.
2. Decide whether `psi_direct_hfe` means real Hermite extension or interface-limited smoothing, then rename or implement accordingly.
3. Add a named paper-stack preset; stop relying on legacy defaults for paper claims.
4. Normalize `ψ`/`φ` helper docs/tests to the paper convention.
5. Make initial-condition SDF primitives `backend.xp` clean and add GPU smoke coverage.

## Validation Performed

- Static A3 audit across targeted `src/twophase/`, paper sections, and ch13/ch14 configs.
- Local CPU curvature sign probe for a circular droplet (`R=0.25`) returned mean interface `κ≈4.012`.
- No full remote experiment was run in this CHK.
