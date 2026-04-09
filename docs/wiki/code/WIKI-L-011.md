---
id: WIKI-L-011
title: "CCD Solver Module: Block-Tridiagonal LU, Multi-Axis Design, and Backend Abstraction"
status: ACTIVE
created: 2026-04-10
depends_on: [WIKI-T-001, WIKI-T-011, WIKI-T-012]
---

# CCD Solver Module

## Overview (670 LOC, standalone)

The CCD module (`src/twophase/ccd/`) implements the 6th-order Combined Compact Difference scheme. It is the most reused component in the library — consumed by pressure, advection, curvature, reinitialization, Rhie-Chow, velocity corrector, and HFE.

## Architecture

```
ccd/
├── ccd_solver.py      # CCDSolver — public API (523 LOC)
└── block_tridiag.py   # BlockTridiagSolver — linear algebra (147 LOC)
```

### CCDSolver

```python
class CCDSolver:
    def __init__(self, grid, backend):
        # Pre-builds block-tridiag solvers for each axis
    
    def differentiate(self, f, axis, bc_left='wall', bc_right='wall',
                      apply_metric=True) -> Tuple[d1, d2]:
        # Returns (f', f'') simultaneously — 6th-order interior, 5th/4th boundary
```

**Key design decisions**:
- Returns both 1st and 2nd derivatives simultaneously (single block-tridiag solve)
- `apply_metric=True` transforms from xi-space to x-space for non-uniform grids
- Boundary scheme: O(h^5) for d1, O(h^4) for d2 (one-sided 4-point stencils)
- Periodic BC: block-circulant solver (separate code path)

### BlockTridiagSolver

Solves the 3x3 block tridiagonal system arising from the CCD formulation:

```
[B_i] [U_{i-1}]   [D_i] [U_i]   [C_i] [U_{i+1}]  =  [R_i]
```

where U_i = (f_i, f'_i, f''_i)^T. Uses block LU factorization — O(N) complexity.

## Reusability Assessment: 9/10

**Strengths**:
- Completely orthogonal to simulation domain (no physics knowledge)
- Clean separation: CCDSolver = policy, BlockTridiag = mechanism
- Comprehensive docstrings with paper equation citations

**Coupling**:
- Requires Grid object (for coords, L, N, J)
- Requires Backend.xp (numpy/cupy array namespace)
- No dependency on any simulation or physics module

## Usage Map

| Consumer | Method | Purpose |
|----------|--------|---------|
| Predictor | differentiate(u, ax) | Convection: u * du/dx |
| ViscousTerm | differentiate(u, ax) | d2u/dx2 for Laplacian |
| SurfaceTensionTerm | differentiate(psi, ax) | d(kappa * grad(H))/dx |
| CurvatureCalculatorPsi | differentiate(psi, ax) | d1, d2 for kappa formula |
| Reinitializer | differentiate(psi, ax) | Compression divergence + diffusion |
| DissipativeCCDAdvection | differentiate(flux, ax) | DCCD flux derivative |
| RhieChowInterpolator | differentiate(p, ax) | Pressure gradient at faces |
| VelocityCorrector | differentiate(delta_p, ax) | Pressure correction gradient |
| HermiteFieldExtension | differentiate(f, ax) | f, f', f'' for Hermite interpolation |
| _CCDPPEBase | differentiate(I, ax) | Kronecker matrix column extraction |
