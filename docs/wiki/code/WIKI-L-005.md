---
ref_id: WIKI-L-005
title: "PPE Solver Verification Scripts (Exp 11-9, 11-10, 11-11, 11-12, 11-13)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_9_dc_k_accuracy.py
    git_hash: e2a1b1b
    description: "Defect correction: iteration count k vs spatial accuracy"
  - path: experiment/ch11/exp11_10_dc_vs_fd.py
    git_hash: e2a1b1b
    description: "DC k=3 vs FD direct: accuracy-cost comparison"
  - path: experiment/ch11/exp11_11_ppe_neumann.py
    git_hash: e2a1b1b
    description: "PPE Neumann BC with gauge pinning and DC k=3"
  - path: experiment/ch11/exp11_12_varrho_ppe.py
    git_hash: e2a1b1b
    description: "Variable-density PPE: smooth density and interface-type jumps"
  - path: experiment/ch11/exp11_13_dc_omega_map.py
    git_hash: e2a1b1b
    description: "DC+LU omega-relaxation convergence map"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-004]] — code-level implementation details"
  - domain: T
    usage: "Validates claims in [[WIKI-T-005]], [[WIKI-T-015]], [[WIKI-T-024]]"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-015]]"
  - "[[WIKI-T-024]]"
  - "[[WIKI-E-004]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Shared Building Blocks

All 5 scripts share a common pattern for CCD-based Laplacian evaluation:

```python
def eval_LH(p, ccd, backend):
    Lp = zeros_like(p)
    for ax in range(2):
        _, d2p = ccd.differentiate(p, ax)
        Lp += d2p
    return Lp
```

FD Laplacian assembly: `build_fd_laplacian_dirichlet(N, h)` constructs standard 5-point stencil as `scipy.sparse.csr_matrix`.

**DC iteration template** (used in exp11_9, 11_10, 11_11):

```python
p = zeros_like(rhs)
for _ in range(k_dc):
    Lp = eval_LH(p, ccd, backend)    # CCD residual
    d = rhs - Lp                       # defect
    d[boundary] = 0                    # BC enforcement
    dp = spsolve(L_FD, d.ravel())      # FD correction
    p = p + dp
```

## Exp 11-9: DC k Accuracy (`exp11_9_dc_k_accuracy.py`)

**Purpose**: Show DC iteration count k controls spatial order: k=1→O(h^2), k=2→O(h^4), k>=3→O(h^7).

**Test problem**: 2D Poisson, p* = sin(pi x)sin(pi y), Dirichlet BC.

**Parameter sweep**: `Ns = [8, 16, 32, 64, 128]`, `Ks = [1, 2, 3, 5, 10]`.

**Key implementation**: `defect_correction(rhs, ccd, backend, L_L, k_max)` — generic DC solver with boundary enforcement at each iteration.

## Exp 11-10: DC vs FD (`exp11_10_dc_vs_fd.py`)

**Purpose**: Cost-accuracy tradeoff — DC k=3 achieves 4.9e7x better accuracy at 3.4x cost.

**Timing**: Uses `time.perf_counter()` to measure wall-clock time in ms for both FD direct (`spsolve` once) and DC k=3 (`eval_LH` + `spsolve` x3).

**Same test problem as exp11_9** but reports accuracy/cost ratio.

## Exp 11-11: PPE Neumann (`exp11_11_ppe_neumann.py`)

**Purpose**: Verify O(h^5) convergence with all-Neumann BC and gauge pinning.

**Neumann FD assembly**: `build_fd_neumann(N, h)` uses ghost-free one-sided stencils:

| Boundary | Stencil |
|----------|---------|
| coord=0 | `2/h^2 * p_{1}` (mirror) |
| coord=N | `2/h^2 * p_{N-1}` (mirror) |
| Interior | Standard 5-point |

**Gauge pinning**: `pin_gauge(L, rhs, pin_dof, pin_val)` sets row `pin_dof` to identity, RHS to `pin_val = p*(0,0)`.

**DC modification for Neumann**: Gauge pin applied to both FD matrix and DC defect at each iteration: `d_flat[pin_dof] = pin_val - p[pin_dof]`.

## Exp 11-12: Variable-Density PPE (`exp11_12_varrho_ppe.py`)

**Purpose**: Test CCD product-rule operator `div((1/rho) grad p)` with smooth density variation.

**Variable-coefficient CCD Laplacian**:

```python
def eval_LH_varrho(p, rho, ccd, backend):
    for ax in range(2):
        dp, d2p = ccd.differentiate(p, ax)
        drho, _ = ccd.differentiate(rho, ax)
        Lp += d2p / rho - (drho / rho**2) * dp
    return Lp
```

**Density parameterization**: `rho = 1 + A * sin(pi x) * cos(pi y)` with A=[0, 0.8, 0.98, 0.998] giving rho_max/rho_min ~ [1, 9, 99, 999].

**FD variable-coefficient assembly**: `build_fd_varrho(N, h, rho)` includes cross-derivative terms `drho/rho^2 * dp/dx`.

## Exp 11-13: DC Omega Map (`exp11_13_dc_omega_map.py`)

**Purpose**: Map convergence behavior of omega-relaxed DC across (omega, rho_ratio) parameter space.

**Omega-relaxed DC**: `p = p + omega * dp` (standard DC has omega=1).

**Parameter grid**: `omegas = [0.1, 0.2, 0.3, 0.5, 0.7, 0.83]`, `density_ratios = [1..1000]`, `N = [32, 64]`.

**Interface density**: Smoothed Heaviside `H = 0.5 * (1 + tanh(phi / 2eps))`, `rho = 1 + (rho_g - 1) * H`.

**Convergence status classification**:

| Status | Symbol | Condition |
|--------|--------|-----------|
| Converged | V | residual < 1e-8 |
| Diverged | X | residual > 1e20 or NaN |
| Stagnated | ~ | 10-iteration ratio > 0.99 |

**Output**: Heatmap (iterations to converge) + residual history curves. Key finding: `omega_max ~ 0.833`; divergence at high density ratio.
