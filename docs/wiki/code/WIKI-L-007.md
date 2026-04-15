---
ref_id: WIKI-L-007
title: "Rhie-Chow & Young-Laplace Pipeline Scripts (Exp 11-5, 11-16)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_05_rc_bracket.py
    git_hash: e2a1b1b
    description: "Rhie-Chow bracket: standard O(h^2) vs C/RC O(h^4)"
  - path: experiment/ch11/exp11_16_young_laplace.py
    git_hash: e2a1b1b
    description: "Young-Laplace static droplet: CSF + CCD-PPE end-to-end"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-006]] and [[WIKI-E-007]] — code-level implementation details"
  - domain: T
    usage: "Validates claims in [[WIKI-T-004]] and [[WIKI-T-025]]"
depends_on:
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-025]]"
  - "[[WIKI-T-008]]"
  - "[[WIKI-E-006]]"
  - "[[WIKI-E-007]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Exp 11-5: RC Bracket (`exp11_05_rc_bracket.py`)

**Purpose**: Demonstrate C/RC bracket improves face pressure gradient from O(h^2) to O(h^4).

**Test problem**: p = cos(2pi x)cos(2pi y), periodic BC, N=[16,32,64,128].

**Two bracket formulas**:

| Bracket | Formula | Order |
|---------|---------|-------|
| Standard RC | `(p[i+1] - p[i]) / h` | O(h^2) |
| C/RC | `(p[i+1] - p[i]) / h - h/24 * (p''[i+1] - p''[i])` | O(h^4) |

**Key implementation**: C/RC uses `d2p_dx2` from `ccd.differentiate()` to apply Richardson correction:

```python
dp_crc = (p[1:] - p[:-1]) / h - h / 24.0 * (d2p_dx2[1:] - d2p_dx2[:-1])
```

**Exact face gradient**: Evaluated at `x_face = X[:-1] + h/2` analytically.

## Exp 11-16: Young-Laplace (`exp11_16_young_laplace.py`)

**Purpose**: End-to-end CSF pipeline validation — static droplet pressure jump.

**Pipeline steps**:

| Step | Operation | Code |
|------|-----------|------|
| 1 | Level-set | `phi = R - sqrt((X-0.5)^2 + (Y-0.5)^2)` |
| 2 | Smoothed Heaviside | `psi = heaviside(np, phi, eps)` with `eps = 1.5*h` |
| 3 | Curvature | `CurvatureCalculator(backend, ccd, eps).compute(psi)` |
| 4 | Pressure jump | `kappa_mean` at near-interface band (`abs(phi) < 3*h`) |

**Physical parameters**: R=0.25, We=1, `kappa_exact = 1/R = 4.0`, `Dp_exact = kappa/We = 4.0`.

**Density**: `rho_l/rho_g = 1000` (parameter in docstring; simplified in implementation to curvature-only test).

**Key simplification**: This script measures `kappa_mean` at the interface as a proxy for pressure jump, rather than solving the full PPE. The pressure jump `Dp = kappa` holds for We=1.

**Measured quantities**: `Dp_measured = kappa_mean`, `rel_err = |Dp - Dp_exact| / Dp_exact`.

**Grid sizes**: N=[32, 64, 128].
