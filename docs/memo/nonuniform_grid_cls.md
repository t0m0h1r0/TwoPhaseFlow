# Non-Uniform Grid CLS Advection: Investigation and Fixes

Date: 2026-04-09

## Problem

CLS advection (`DissipativeCCDAdvection`) and reinitialization (`Reinitializer`)
fail on non-uniform (interface-fitted, `alpha_grid > 1`) grids:
mass_err = 6.7% on static non-uniform grid vs machine-epsilon on uniform.

## Root causes

Three uniform-grid assumptions identified:

### 1. Mass correction uses `sum(psi)` instead of `sum(psi * dV)`

Advection (advection.py:319-335) and reinitializer (reinitialize.py:128,143-147,161,199-201,209-215,262,290-294)
all compute mass as `xp.sum(q)`.  On non-uniform grids, the correct integral is
`sum(q * dV)` where `dV = prod(h_ax)` varies per node.

### 2. Dissipative filter operates in x-space

The 3-point filter `F_tilde = f' + eps_d * (f'_{i+1} - 2f'_i + f'_{i-1})` assumes
uniform spacing.  Its transfer function `H(k_xi) = 1 - 4*eps_d*sin^2(k_xi/2)` is
defined in computational (xi) space.  On non-uniform grids, the filter must operate
on xi-space derivatives, then apply the metric J = dxi/dx.

### 3. No per-cell volume array

`Grid.cell_volume()` returned a scalar (uniform approximation).
Needed: `Grid.cell_volumes()` returning an ndarray of shape `grid.shape`.

## Fixes applied

| File | Change |
|------|--------|
| `grid.py` | Added `cell_volumes()`: outer product of `h[ax]` arrays |
| `ccd_solver.py` | Added `apply_metric=True` parameter to `differentiate()` and `_differentiate_periodic()` |
| `advection.py` | Stored `_grid`; volume-weighted mass correction; xi-space filter branch for non-uniform |
| `reinitialize.py` | Volume-weighted mass in `_reinitialize_split/unified/dgr`; extracted `_filtered_divergence()` helper with xi-space branch; volume-weighted `volume_monitor()` |

## Results

### Static non-uniform grid (no rebuild), N=128, eps/h=0.5

| | L2(phi) | area_err | mass_err |
|---|---------|----------|----------|
| Uniform | 1.05e-2 | 3.2e-4 | 2.0e-15 |
| Before fix (alpha=2) | 4.93e-2 | 5.4e-2 | **6.7e-2** |
| After fix (alpha=2) | 4.50e-2 | 9.6e-2 | **1.2e-16** |

Static non-uniform: mass conservation restored to machine epsilon.
Shape accuracy degrades because the interface rotates away from the refined region.

### Dynamic grid rebuild (every 20 steps)

| Rebuild method | L2(phi) | area_err | mass_err |
|---|---------|----------|----------|
| Linear interp | 1.46e-2 | 1.1e-1 | 3.0e-2 |
| Cubic interp | **1.32e-2** | 6.8e-2 | 1.1e-1 |

Dynamic rebuild achieves near-uniform L2(phi) accuracy (1.32e-2 vs 1.05e-2)
but interpolation during grid remapping causes mass loss (3-11%).

## Known limitation: CN diffusion on non-uniform grids

The CN ADI sweep in `_cn_diffusion_axis` uses pre-factored Thomas coefficients
with uniform spacing `h = L/N`.  On non-uniform grids, the physical diffusion
`eps * d2psi/dx2 = eps * J^2 * d2psi/dxi2 + eps * J * dJ * dpsi/dxi` differs
from the uniform-spacing approximation.  This is documented but not yet fixed
(would require non-uniform Thomas tridiagonal coefficients).

## Conclusion

- **Static non-uniform grids** now work correctly for CLS: mass conservation at machine-epsilon level.
  Best use case: static/quasi-static interfaces (e.g., droplet simulations).
- **Dynamic grid rebuild** provides better interface resolution but introduces
  interpolation mass errors.  Requires conservative remapping (future work).
- **For rotating/advecting interfaces** (Zalesak, vortex): uniform grid + eps/h=0.5
  remains the best practical choice.
