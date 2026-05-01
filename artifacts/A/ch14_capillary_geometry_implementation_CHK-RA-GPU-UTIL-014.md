# CHK-RA-GPU-UTIL-014 — Wall-compatible capillary geometry implementation

Date: 2026-05-01

## Theory

For gravity-free capillary flow in a stationary no-slip box, the discrete
operator must approximate

```text
d/dt [ KE + sigma |Gamma| ] <= 0
```

up to time-discretization error.  At a no-slip wall without an explicit
wetting/contact-line law, the contact root is a constrained endpoint.  The wall
reaction balances endpoint traction; the endpoint is not a source of bulk
capillary work.

Therefore the pressure jump must be assembled from one interface geometry:

```text
wall phase topology + contact roots
  -> interior-limit wall-contact curvature
  -> cut-face Young--Laplace jump
  -> same face operator in PPE RHS and corrector
```

This rejects curvature-cap tuning, smoothing, or relaxing the wall topology as
root fixes.

## Implementation

- `CurvatureCalculatorPsi` is now the runtime curvature path, matching the
  production `psi_direct_filtered` YAML contract.
- `apply_wall_compatible_curvature` applies a GPU-vectorized no-slip wall
  closure: wall-normal closure layers use the interior limiting curvature
  (`partial_n kappa_lg = 0`) and off-interface values remain zero.
- `build_young_laplace_interface_stress_context` now marks Young--Laplace
  contexts for cut-face quadrature.
- `signed_pressure_jump_gradient` evaluates `kappa_lg` at the `psi=1/2`
  face cut before forming `j_gl=-sigma kappa_lg`; explicit pressure-jump
  contexts keep the legacy nodal-average behavior.
- The PPE affine-jump path and the velocity corrector both consume the same
  updated context, so the capillary work operator is geometrically consistent.

GPU notes: the wall closure and cut-face interpolation stay in `backend.xp`;
there is no device-to-host transfer in the hot path, and only axis-level Python
loops are used.

## Verification

- Remote unit test:
  `make test PYTEST_ARGS="-k young_laplace_jump_uses_cut_face_curvature_quadrature"`
  PASS.
- Remote unit test:
  `make test PYTEST_ARGS="-k wall_compatible_curvature_uses_interior_limit"`
  PASS.
- Remote unit test:
  `make test PYTEST_ARGS="-k pipeline_uses_psi_direct_curvature_runtime"`
  PASS.
- Initial N=32/T=25 diagnostic: `CurvatureCalculatorPsi`; initial interface-band
  max curvature is `1.5776` before wall closure and `1.5731` after wall closure,
  instead of the prior wall-local `O(10^2)` spike.
- Remote GPU N=32/T=1: PASS; first diagnostic `kappa_max=1.754e+00`, not the
  cap `5.0`.
- Remote GPU N=32/T=25: PASS to `t=25.0` in 3159 steps.  Final/maximum
  diagnostics:
  - `KE`: final/max `8.9139e-03` / `8.9139e-03`
  - `div_u_max`: final/max `5.8914e-05` / `4.3866e-04`
  - `bf_residual_max`: final/max `37.45` / `113.16`
  - `ppe_rhs_max`: final/max `5.94` / `11.18`
  - `volume_drift`: final/max `1.3958e-02` / `1.3958e-02`

Compared with the previous BLOWUP at `t=22.4868` (`KE max≈1.5e6`,
`div_u_max≈2.24`, `bf_residual_max≈2.58e8`), the capillary-energy failure is
removed for the existing N=32/T=25 capillary-wave YAML.

## SOLID audit

[SOLID-X] The new wall/cut-face capillary logic is isolated in
`twophase.coupling.capillary_geometry` and the existing affine-jump context.
No solver, PPE, or reinitialization module receives ad-hoc wall special cases.
Legacy curvature code is preserved unchanged as the C2 diagnostic baseline.
