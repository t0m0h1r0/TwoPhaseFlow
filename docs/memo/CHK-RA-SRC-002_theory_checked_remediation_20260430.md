# CHK-RA-SRC-002 — Theory-Checked Remediation

Date: 2026-04-30  
Branch: `ra-src-paper-audit-20260430`  
Scope: follow-up to `CHK-RA-SRC-001`, with each finding rechecked from theory rather than accepted from the paper text.

## Method

For each audit finding, the check was:

1. derive the sign/operator/backend invariant from continuum mechanics or numerical-analysis contract;
2. compare that invariant with code behavior;
3. patch only when the code/config contract, not merely the prose, was wrong.

## Theory Checks and Decisions

### T1 — Pressure-jump sign

Independent derivation:

- Let `n_lg` point from liquid to gas.
- For a static inviscid liquid droplet, the liquid pressure is higher than gas pressure by the Laplace pressure.
- With `κ_lg = div(n_lg) > 0` for a convex liquid droplet, this gives `p_l - p_g = σ κ_lg`.
- Therefore the gas-minus-liquid jump is `j_gl = p_g - p_l = -σ κ_lg`.

Decision:

- The paper’s sign is physically correct.
- The affine path already used `j_gl=-σ κ_lg`.
- The legacy `jump_decomposition` path was wrong because it composed `+σκ(1-ψ)` on the gas side.

Fix:

- `jump_decomposition` now stores and composes `pressure_jump_gas_minus_liquid = -σ κ_lg`.
- ch13 §14-stack helper paths now use `affine_jump`, matching the sharper face-gradient interface-stress operator.

### T2 — HFE vs direct-ψ filtered curvature

Independent derivation:

- Curvature can be computed from a monotone level-set map because the normalized normal direction and Hessian formula are invariant up to the known sign convention.
- Hermite field extension is a distinct operation: it extends a scalar field from one phase across Γ using Hermite data and closest points.
- A Laplacian update `q* = q - C h² w(ψ)∇²q` is smoothing, not Hermite extension.

Decision:

- The production runtime method is theoretically a direct-ψ curvature route plus interface-limited smoothing.
- Calling it `psi_direct_hfe` was not theoretically correct.
- The standalone `HermiteFieldExtension` remains valid only for uniform grids because it brackets points by `hx=Lx/Nx`, `hy=Ly/Ny`.

Fix:

- The canonical curvature config name is now `psi_direct_filtered`.
- `psi_direct_hfe` remains a legacy alias for config compatibility.
- Runtime members now expose `_curvature_filter`; `_hfe` remains only as a backward-compatible alias.
- `HermiteFieldExtension` rejects non-uniform grids until a metric-aware HFE exists.

### T3 — `ψ`/`φ` convention

Independent derivation:

- The increasing logistic helper is `Hε(s)=1/(1+exp(-s/ε))`.
- The liquid-inside CLS convention uses `ψ=Hε(-φ_lg)`.
- Therefore `Hε^{-1}(ψ)` returns `s=-φ_lg`, not `φ_lg`.

Decision:

- The runtime builder + curvature path is numerically sign-correct by explicit sign handling.
- The helper module documentation was ambiguous and could lead to incorrect call-site assumptions.

Fix:

- `levelset/heaviside.py` now documents the increasing helper and states that paper `φ_lg` is the negative of the helper inverse.

### T4 — GPU initial-condition SDFs

Independent invariant:

- `Grid.meshgrid()` returns backend-native arrays.
- Any shape SDF evaluated on those arrays must use the same array namespace; otherwise GPU execution can incur illegal host conversion or lose backend parity.

Decision:

- Direct `np.sqrt`, `np.maximum`, `np.arctan2`, `np.cos`, and `np.asarray` inside SDF methods violated the backend contract.

Fix:

- Shape primitives now dispatch through `_xp_like(coords[0])`.
- A GPU smoke test covers `InitialConditionBuilder` parity against CPU.

### T5 — Legacy defaults vs paper stack

Independent check:

- Defaults are not a physical equation; they are a software policy.
- The paper stack is a named operator combination, not logically forced as the library constructor default.

Decision:

- No theoretical code fix is required for defaults in this pass.
- The remaining policy choice is whether to add a named production preset or promote paper-stack defaults; that should be a separate behavioral decision.

## SOLID Audit

[SOLID-X] No new SOLID violation introduced.  The `_curvature_filter` rename reduces a naming-contract smell while keeping `_hfe` as a compatibility alias; tested HFE code is preserved and only guarded against unsupported non-uniform use.
