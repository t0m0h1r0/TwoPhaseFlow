---
ref_id: WIKI-L-003
title: "Curvature & Hermite Field Extension Scripts (Exp 11-3, 11-7)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_03_curvature_3path.py
    git_hash: e2a1b1b
    description: "Curvature computation: circle and sinusoidal interface, CCD vs CD2"
  - path: experiment/ch11/exp11_07_hfe_convergence.py
    git_hash: e2a1b1b
    description: "Hermite Field Extension: 1D and 2D, upwind vs closest-point"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-002]] — code-level implementation details"
  - domain: T
    usage: "Validates claims in [[WIKI-T-008]] and [[WIKI-T-018]]"
depends_on:
  - "[[WIKI-T-008]]"
  - "[[WIKI-T-018]]"
  - "[[WIKI-T-020]]"
  - "[[WIKI-E-002]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-3: Curvature Three-Path (`exp11_03_curvature_3path.py`)

**Purpose**: Compare CCD-based vs CD2-based curvature computation on two interface geometries.

**API usage**:

| Component | CCD path | CD2 path |
|-----------|----------|----------|
| Derivatives | `CurvatureCalculator(backend, ccd, eps).compute(psi)` | Manual 2nd-order FD stencils |
| Input | psi (smoothed Heaviside) | phi (signed distance) |
| Smoothing | Built into CurvatureCalculator | Manual `1e-12` regularization in grad_mag |

**CD2 reference implementation** (inline, not from library):

```python
phi_xx[1:-1] = (phi[2:] - 2*phi[1:-1] + phi[:-2]) / h**2
kappa = -(phi_y**2 * phi_xx - 2*phi_x*phi_y*phi_xy + phi_x**2 * phi_yy) / grad_mag**3
```

**Two sub-cases**:

| Case | Interface | Exact kappa | Near-interface band |
|------|-----------|-------------|---------------------|
| (a) | Circle R=0.25 | 1/R = 4.0 | `abs(phi) < 3*h` |
| (b) | y = 0.5 + 0.05*sin(2pi x) | `-f'' / (1+f'^2)^{3/2}` | `abs(phi) < 3*h` |

**Key detail**: Error measured only in near-interface band (`abs(phi) < 3*h`), not globally.

## Exp 11-7: HFE Convergence (`exp11_07_hfe_convergence.py`)

**Purpose**: Compare upwind O(h^1) vs Hermite O(h^6) field extension across interface.

**API usage**:

| Method | Class | Import |
|--------|-------|--------|
| Upwind | `FieldExtender(backend, grid, ccd, n_ext=5, method="upwind")` | `twophase.levelset.field_extender` |
| Hermite | `ClosestPointExtender(backend, grid, ccd)` | `twophase.levelset.closest_point_extender` |

Both called via `.extend(q, phi)` → returns extended field.

**Two sub-cases**:

| Case | Geometry | Source field | Exact extension | Measurement band |
|------|----------|-------------|-----------------|------------------|
| (a) 1D | phi = x - 0.5 | q = 1 + cos(pi x) | q_ext = q(0.5) = 1.0 | 0.52 <= x <= 0.55 |
| (b) 2D | Circle R=0.25 | q = cos(pi x)cos(pi y) | q(x_Gamma) via closest-point projection | 0 < phi <= 3h |

**2D exact extension computation**: Uses closest-point projection `x_Gamma = x - phi * n_hat` where `n_hat = (x - 0.5, y - 0.5) / r`.

**Error handling**: Both extension methods wrapped in try/except — graceful `nan` on import failure.
