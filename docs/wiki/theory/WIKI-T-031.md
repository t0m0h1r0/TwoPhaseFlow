# WIKI-T-031: Non-Uniform Grid CLS: Volume-Weighted Mass and Xi-Space Filter

## Summary

CLS advection and reinitialization on non-uniform (interface-fitted) grids
require three corrections to the uniform-grid algorithm:

1. **Volume-weighted mass integrals**: `M = sum(psi * dV)` where `dV = prod(h_ax)` per node
2. **Xi-space dissipative filter**: operate filter on `df/dxi`, then apply metric J = dxi/dx
3. **Per-cell volume array**: `Grid.cell_volumes()` provides the ndarray

## Theory

### Mass integral

On a collocated node-centered grid, the discrete mass integral is:

    M = sum_{i,j} psi_{i,j} * h_x(i) * h_y(j)

where `h_x(i)` is the per-node spacing.  On a uniform grid, `h_x = h_y = const`
and `M = h^2 * sum(psi)`, so `sum(psi)` suffices as a proxy.  On non-uniform grids,
the cell volume `dV_{i,j} = h_x(i) * h_y(j)` varies, and unweighted `sum(psi)` is
meaningless as a mass measure.

The interface-weighted mass correction becomes:

    delta_psi = ((M_old - M_new) / W) * w,   w = 4*psi*(1-psi),  W = sum(w * dV)

### Dissipative filter in computational space

The DCCD filter has transfer function:

    H(k_xi) = 1 - 4*eps_d * sin^2(k_xi / 2)

where `k_xi` is the wavenumber in computational (xi) space.  The 3-point stencil
`f'_{i+1} - 2f'_i + f'_{i-1}` realizes this transfer function when applied to
values at uniformly-spaced xi-nodes.

On non-uniform physical grids, the CCD solver computes `df/dxi` (xi-space)
internally, then applies the metric transform `df/dx = J * df/dxi`.  For the
filter to maintain its designed spectral response:

1. Obtain `df/dxi` via `ccd.differentiate(f, ax, apply_metric=False)`
2. Apply filter: `F_xi = df/dxi + eps_d * (df/dxi_{i+1} - 2*df/dxi_i + df/dxi_{i-1})`
3. Transform to physical space: `F = J * F_xi`

On uniform grids, `J = N/L` (constant) and this reduces to the original code.

### Grid rebuild: remap ψ directly (not φ)

When the non-uniform grid is rebuilt to track a moving interface:
1. Compute `phi` from `psi` (for grid generation only)
2. Rebuild grid from `phi` (update_from_levelset)
3. Interpolate `psi` directly (linear) from old grid to new grid
4. Apply small mass correction (< 0.005% residual)

**Critical insight**: the original approach (interpolate φ, then heaviside)
introduced 3–11% mass error through two nonlinear transforms (logit + sigmoid).
Direct ψ linear interpolation is monotone (no overshoot) and preserves
ψ ∈ [0,1] by construction.

| Remap method | mass_err | area_err |
|--------------|----------|----------|
| φ cubic + heaviside | 2.97e-2 | 7.15e-2 |
| ψ cubic + clip | 4.59e-3 | 1.10e-2 |
| **ψ linear + clip** | **5.12e-5** | **1.46e-2** |

Flux-form conservative remapping is unnecessary — ψ linear achieves
near-machine-epsilon mass conservation with post-hoc correction.

## Verification

Experiment: `exp11_22_zalesak_nonuniform.py`

| Grid | L2(phi) | area_err | mass_err |
|------|---------|----------|----------|
| Uniform | 1.05e-2 | 3.2e-4 | ~0 |
| Static alpha=2 (before fix) | 4.93e-2 | 5.4e-2 | 6.7e-2 |
| Static alpha=2 (after fix) | 4.50e-2 | 9.6e-2 | **1.2e-16** |
| Dynamic alpha=2 (ψ linear) | 3.74e-2 | 1.5e-2 | **5.1e-5** |
| Dynamic alpha=3 (ψ linear) | 3.72e-2 | 5.4e-2 | **1.5e-15** |

Static: mass conservation at machine epsilon.
Dynamic: mass conservation at ~10⁻⁵ (with ψ linear remap).

## Related

- WIKI-T-027: CLS mass correction theory
- WIKI-T-028: Unified DCCD reinitialization
- WIKI-E-001: CCD/DCCD spatial accuracy on non-uniform grids (GCL validation)
- Paper section 6: Interface-fitted grid generation
