# WIKI-E-026: xi-Space eps Validation — Advection and NS Benchmarks

**Related Theory**: WIKI-T-040
**Scripts**: exp11_35, exp11_36 (new), exp11_08/22/33, exp11_29, exp12_17/18 (updated)

## Summary

Validated `eps_g_cells` and `eps_xi_cells` across 8 experiment scripts
covering CLS advection (Zalesak, single vortex), grid remapping, and
NS-level static droplet tests. The xi-space grid density definition
(`eps_g_cells=4`) is a clear improvement; the xi-space Heaviside eps
(`eps_xi_cells=1.5`) has conditional benefits.

## New Experiments

### exp11_35: Zalesak disk xi-space eps comparison

5 cases at N=128, eps_ratio=0.5, T=2pi:

| Case              | L2(psi) | L2(phi) | area_err | mass_err |
|-------------------|---------|---------|----------|----------|
| uniform           | 8.00e-2 | 1.05e-2 | 3.18e-4  | 5.5e-15  |
| legacy a=2        | 1.47e-1 | 1.15e-2 | 3.53e-2  | 4.9e-15  |
| xi-gc4 a=2        | 8.92e-2 | 1.05e-2 | 1.15e-2  | 1.2e-16  |
| xi-gc4+xc1.5 a=2  | 9.94e-2 | 2.31e-2 | 2.02e-2  | 6.6e-15  |
| xi-gc4+xc1.5 a=3  | 1.01e-1 | 2.28e-2 | 2.29e-2  | 3.5e-16  |

**eps_g_cells=4 effect**: L2(psi) 0.147 -> 0.089 (40% reduction), area_err
3.5e-2 -> 1.2e-2, L2(phi) matches uniform level (1.05e-2).

**eps_xi_cells=1.5 at eps_ratio=0.5**: detrimental -- L2(phi) doubles to
2.3e-2. The Heaviside transition occupies only 0.75 cells in fine regions
(1.5 * 0.5 effective), under-resolving the profile.

### exp11_36: Single vortex xi-space eps comparison

5 cases at N=128, eps_ratio=1.5, T=8:

| Case              | L2(psi) | L2(phi) | area_err | mass_err |
|-------------------|---------|---------|----------|----------|
| uniform           | 1.75e-1 | 3.43e-2 | 7.17e-2  | 2.1e-15  |
| legacy a=2        | 2.37e-1 | 3.86e-2 | 1.19e-1  | 4.6e-15  |
| xi-gc4 a=2        | 2.21e-1 | 3.75e-2 | 1.08e-1  | 3.3e-15  |
| xi-gc4+xc1.5 a=2  | 2.16e-1 | 3.22e-2 | 1.07e-1  | 7.2e-15  |
| xi-gc4+xc1.5 a=3  | 2.33e-1 | 3.27e-2 | 1.23e-1  | 3.4e-15  |

**eps_g_cells=4 effect**: modest improvement (L2(psi) 0.237 -> 0.221).

**eps_xi_cells=1.5 at eps_ratio=1.5**: L2(phi) = 3.22e-2 **beats uniform**
(3.43e-2). The Heaviside has 1.5*1.5 = 2.25 effective cells in fine
regions, adequate for profile resolution.

## Updated Experiments

### exp11_22 (Zalesak, eps_g_cells=4 added)

| Case          | L2(phi) | area_err | mass_err |
|---------------|---------|----------|----------|
| uniform       | 1.054e-2 | 3.18e-4 | 5.5e-15  |
| non-uniform a=2 | 1.050e-2 | 1.15e-2 | 1.2e-16 |
| non-uniform a=3 | 1.040e-2 | 1.55e-2 | 5.2e-15 |

L2(phi) now uniform-equivalent for both a=2 and a=3. Previously (legacy
eps_g), L2(phi) was 1.15e-2 for a=2 -- now 1.05e-2.

### exp11_33 (Single vortex, eps_g_cells=4 added)

| Case          | L2(phi) | area_err | mass_err |
|---------------|---------|----------|----------|
| uniform       | 3.429e-2 | 7.17e-2 | 2.1e-15  |
| non-uniform a=2 | 3.746e-2 | 1.08e-1 | 3.3e-15 |
| non-uniform a=3 | 3.858e-2 | 1.21e-1 | 2.3e-15 |

### exp11_29 (NS grid rebuild, eps_g_cells=4 added)

N=32, 100 steps, static droplet:
- Uniform: mass_err=6.35e-6, max|u|=1.01e-2
- Non-uniform a=2: mass_err=6.74e-6, max|u|=7.80e-3
- Parasitic current reduced (0.78x), mass conservation comparable.

### exp12_17 (Static droplet, eps_g_cells=4 added)

N=48 stable results show non-uniform grid dramatically reduces parasitic
currents (5.59e-3 vs 4.36e-1, 78x improvement) and Laplace error
(4.00e-3 vs 2.37e-1). N=32 and N=64 uniform cases still blow up due to
insufficient resolution for CSF (known issue).

### exp12_18 (Local eps, eps_g_cells=4 + eps_xi_cells=1.5 on config C)

Config C (local eps + eps_xi_cells=1.5) shows increased parasitic currents
compared to Config B (fixed eps). At N=48: C has max|u|=5.93e-1 vs
B's 5.59e-3. The spatially varying eps interacts poorly with CSF curvature
computation -- the delta function mismatch between narrow-eps and broad-eps
regions creates spurious forces.

## Conclusions and Recommendations

1. **eps_g_cells=4 should be the default for all non-uniform grids**.
   Pure upside with no downside observed in any benchmark.

2. **eps_xi_cells=1.5 is beneficial only when eps_ratio >= 1.5**.
   At lower eps_ratio, the effective Heaviside width in fine cells
   drops below the CCD resolution limit.

3. **eps_xi_cells should NOT be used with CSF surface tension** at
   current maturity. The spatially varying eps creates delta function
   magnitude mismatches that amplify parasitic currents.

4. **Future work**: GFM surface tension (which avoids delta functions
   entirely) should be tested with eps_xi_cells -- the expected benefit
   (uniform xi-space resolution) should hold without CSF artifacts.
