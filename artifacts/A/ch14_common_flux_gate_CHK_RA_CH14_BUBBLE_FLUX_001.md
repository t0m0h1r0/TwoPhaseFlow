# CHK-RA-CH14-BUBBLE-FLUX-001: common-flux remedy gate

## Question

The proposed remedy is to make the phase transport produce a certified mass
flux and to use that same flux as the mass part of the momentum update.  This
gate checks whether that idea restores the pure-transport energy theorem before
touching the production solver.

## Discrete theorem

For a positive density `rho` and momentum `m = rho u`, define

```text
E_h(rho,m) = sum_i 1/2 m_i^2 / rho_i.
```

For one-dimensional periodic advection with CFL `lambda in [0,1]`, the common
upwind update is

```text
rho_i^+ = (1-lambda) rho_i + lambda rho_{i-1},
m_i^+   = (1-lambda) m_i   + lambda m_{i-1}.
```

Because `m^2/rho` is a convex perspective function for `rho > 0`,

```text
E_h(rho^+,m^+) <= (1-lambda) E_h(rho,m)
               +  lambda    E_h(shift(rho,m))
               = E_h(rho,m).
```

Thus the common-flux scheme cannot create kinetic energy in pure transport.  If
`u` is spatially constant, `m = rho U` is transported by the same flux and the
energy reduces to `1/2 U^2 sum rho`; it is exactly conserved.

## Probe design

The script `artifacts/A/ch14_common_flux_gate.py` compares:

- `common_upwind_flux`: same conservative convex update for `rho` and `m`.
- `common_upwind_constant_velocity`: same update with uniform velocity.
- `density_upwind_velocity_current`: `rho` moved, `u` left on the old map.
- `density_upwind_velocity_imex`: `rho` moved, explicit velocity history.
- `density_upwind_momentum_lagged`: old `m` evaluated in moved `rho`.
- `momentum_upwind_density_current`: `m` moved, `rho` left on old map.
- `independent_opposite_fluxes`: `rho` and `m` moved by opposite flux maps.

It sweeps `N = 32, 64, 128, 256`, density ratios
`1, 10, 100, 833.3333333333334`, and CFL values
`0, 0.1, 0.25, 0.5, 0.9`.

Artifacts:

- CSV: `artifacts/A/ch14_common_flux_gate_CHK_RA_CH14_BUBBLE_FLUX_001/common_flux_gate.csv`
- Summary: `artifacts/A/ch14_common_flux_gate_CHK_RA_CH14_BUBBLE_FLUX_001/common_flux_gate_summary.json`
- Figure: `artifacts/A/ch14_common_flux_gate_CHK_RA_CH14_BUBBLE_FLUX_001/common_flux_gate.pdf`

## Results

Across all tested grids, density ratios, and CFL values:

```text
closed_max_relative_delta = +1.647826e-16
closed_min_relative_delta = -8.034254e-03
open_max_relative_delta   = +5.329980e-02
open_min_relative_delta   = -4.073115e-02
```

The positive closed maximum is roundoff.  The negative closed minimum is
expected upwind kinetic-energy dissipation from convex averaging.  The open
cases have no sign theorem; they can produce or remove energy depending on
phase alignment.

Representative case, `N=64`, density ratio `833.3333333333334`, CFL `0.5`:

```text
candidate                         (E1-E0)/E0       mass_delta   momentum_delta
common_upwind_constant_velocity   +0.000000e+00    +0.000e+00   +0.000e+00
common_upwind_flux                -2.032082e-03    +0.000e+00   +0.000e+00
density_upwind_velocity_current   +6.502360e-03    +0.000e+00   +1.055e+00
density_upwind_velocity_imex      +5.921945e-03    +0.000e+00   +2.544e-02
density_upwind_momentum_lagged    -6.313729e-03    +0.000e+00   +0.000e+00
momentum_upwind_density_current   +4.420524e-03    +0.000e+00   +0.000e+00
independent_opposite_fluxes       -1.419353e-02    +0.000e+00   +0.000e+00
```

Common-flux high-CFL sweep at `N=64`, CFL `0.9`:

```text
ratio 1       -7.070826e-04
ratio 10      -7.294867e-04
ratio 100     -7.334084e-04
ratio 833.333 -7.338207e-04
```

The common-flux theorem does not degrade at water-air density ratio.

## Interpretation

The proposed direction passes the cleanest mathematical gate:

1. When density and momentum share the same conservative mass flux, pure
   transport does not inject kinetic energy.
2. If the velocity is uniform, the same scheme preserves kinetic energy exactly
   because mass is conserved exactly.
3. The inconsistent variants reproduce the previously observed failure class:
   moving `rho`, `u`, and momentum history on different maps opens positive
   energy defects.

This verifies the remedy class, not yet the full production implementation.  A
production fix must still provide:

- a face mass flux extracted from the same FCCD phase transport that updates
  `psi`,
- conservative momentum fluxes using that exact mass flux,
- a consistent treatment of reinitialization/retraction for `rho u`,
- an IMEX/BDF2 history written either in conservative momentum variables or
  with a proven variable-mass G-stability estimate,
- fail-close diagnostics that reject positive pure-transport energy production
  outside the certified truncation budget.

Therefore the direction is promising for the actual problem, while damping,
CFL-only reduction, pressure masking, curvature smoothing, and density clipping
remain invalid remedies because they do not prove the common-flux theorem.
