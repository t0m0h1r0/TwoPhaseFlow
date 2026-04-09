# WIKI-E-012: Non-Uniform Grid Zalesak: Volume-Weighted Fix Verification

## Experiment

`experiment/ch11/exp11_22_zalesak_nonuniform.py`

Zalesak slotted disk (1 revolution) on non-uniform interface-fitted grids.
N=128, eps/h=0.5, split reinit every 20 steps.

## Setup

Three configurations compared:
1. **Uniform** (alpha=1.0): baseline
2. **Static non-uniform** (alpha=2.0): grid fitted to initial interface, no rebuild
3. **Dynamic non-uniform** (alpha=2.0): grid rebuilt every 20 steps with phi interpolation

## Bug: Three uniform-grid assumptions broke CLS on non-uniform grids

### Before fix

| Grid | L2(phi) | area_err | mass_err |
|------|---------|----------|----------|
| Uniform | 1.05e-2 | 3.2e-4 | 2.0e-15 |
| Static alpha=2 | 4.93e-2 | 5.4e-2 | **6.7e-2** |

### Root causes and fixes

1. **Mass correction**: `sum(psi)` -> `sum(psi * dV)` (advection.py, reinitialize.py)
2. **Dissipative filter**: x-space stencil -> xi-space stencil + J transform (advection.py, reinitialize.py)
3. **Cell volumes**: added `Grid.cell_volumes()` returning per-node volume array (grid.py)
4. **CCD**: added `apply_metric=False` option to `differentiate()` (ccd_solver.py)

### After fix

| Grid | L2(phi) | area_err | mass_err |
|------|---------|----------|----------|
| Uniform | 1.05e-2 | 3.2e-4 | 2.0e-15 |
| Static alpha=2 | 4.50e-2 | 9.6e-2 | **1.2e-16** |
| Dynamic alpha=2 (linear) | 1.46e-2 | 1.1e-1 | 3.0e-2 |
| Dynamic alpha=2 (cubic) | 1.32e-2 | 6.8e-2 | 1.1e-1 |

## Key findings

1. **Static non-uniform**: mass restored to machine epsilon.
   Shape accuracy degrades because the interface moves to coarse region during rotation.

2. **Dynamic rebuild**: L2(phi) nearly matches uniform (1.32e-2 vs 1.05e-2),
   but grid remapping via interpolation introduces 3-11% mass errors.
   Cubic interpolation improves shape but worsens mass (Gibbs-like overshoots).

3. **Practical recommendation**: For advection-dominated tests (Zalesak, vortex),
   uniform grid + eps/h=0.5 is currently best.
   For static/quasi-static interfaces (droplet), non-uniform grids now work correctly.

## Remaining limitation

CN diffusion in reinitializer uses uniform Thomas coefficients.
Non-uniform grids need variable-coefficient tridiagonal solve (future work).

## Related

- WIKI-T-031: Theory behind the fixes
- WIKI-E-010: Zalesak DCCD damping study
- exp11_4: GCL validation on non-uniform grids
