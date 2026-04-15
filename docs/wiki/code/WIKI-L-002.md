---
ref_id: WIKI-L-002
title: "CCD/DCCD Differentiation Verification Scripts (Exp 11-1, 11-2, 11-4, 11-17)"
domain: L
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch11/exp11_01_ccd_convergence.py
    git_hash: e2a1b1b
    description: "CCD convergence: periodic/wall BC, uniform/non-uniform grid"
  - path: experiment/ch11/exp11_02_dccd_filter.py
    git_hash: e2a1b1b
    description: "DCCD filter transfer function and checkerboard suppression"
  - path: experiment/ch11/exp11_04_gcl_nonuniform.py
    git_hash: e2a1b1b
    description: "GCL compliance and non-uniform grid accuracy"
  - path: experiment/ch11/exp11_17_dccd_advection_1d.py
    git_hash: e2a1b1b
    description: "DCCD 1D advection benchmark: 5-scheme comparison"
consumers:
  - domain: E
    usage: "Mirrors [[WIKI-E-001]] — code-level implementation details"
  - domain: T
    usage: "Validates claims in [[WIKI-T-001]] and [[WIKI-T-002]]"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-002]]"
  - "[[WIKI-T-011]]"
  - "[[WIKI-T-013]]"
  - "[[WIKI-E-001]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-08
---

## Common Toolkit Pattern

All scripts follow the `twophase.experiment` convention:

1. `apply_style()` — matplotlib RC config
2. `OUT = experiment_dir(__file__)` — results colocated in `experiment/ch11/results/{name}/`
3. `experiment_argparser(title)` — provides `--plot-only` flag
4. `save_results(OUT / "data.npz", ...)` / `load_results(...)` — numpy persistence
5. `save_figure(fig, OUT / "name")` — PDF output

## Exp 11-1: CCD Convergence (`exp11_01_ccd_convergence.py`)

**Purpose**: Validate O(h^6) spatial accuracy of `CCDSolver.differentiate()`.

**Three sub-cases**:

| Case | Test function | BC | Grid | Key code |
|------|--------------|-----|------|----------|
| (a) | sin(2pi x)sin(2pi y) | periodic | uniform | `bc_type="periodic"`, full-domain error |
| (b) | exp(sin(pi x))exp(cos(pi y)) | wall | uniform | `bc_type="wall"`, `s=slice(2,-2)` trims boundary |
| (c) | Same as (b) | wall | non-uniform alpha=2 | `grid.update_from_levelset(phi, eps=0.05)` |

**Core API call**: `d1x, d2x = ccd.differentiate(f_exact, axis=0)` returns 1st and 2nd derivatives simultaneously.

**Convergence computation**: `compute_slopes()` calculates log-log slopes between successive N values.

## Exp 11-2: DCCD Filter (`exp11_02_dccd_filter.py`)

**Purpose**: Verify DCCD dissipative filter transfer function and Nyquist suppression.

**Two sub-cases**:

| Case | Test | Key implementation |
|------|------|--------------------|
| (a) | Transfer function H(xi; eps_d) | Analytical: `H = 1.0 - 4.0 * eps_d * sin(xi/2)**2` |
| (b) | Checkerboard (-1)^{i+j} suppression | Manual 2nd-order filter: `d1_f[1:-1] = d1_ccd[1:-1] + 0.25 * (d1_ccd[2:] - 2*d1_ccd[1:-1] + d1_ccd[:-2])` |

**Key detail**: The filter is applied post-CCD as explicit 3-point stencil, not inside `CCDSolver`. Periodic BC handled by wrapping: `d1_f[0] = ... + 0.25 * (d1_ccd[1] - 2*d1_ccd[0] + d1_ccd[-1])`.

## Exp 11-4: GCL Non-uniform (`exp11_04_gcl_nonuniform.py`)

**Purpose**: Verify CCD accuracy on interface-fitted non-uniform grids and GCL compliance.

**Two sub-cases**:

| Case | Test | Key implementation |
|------|------|--------------------|
| (a) | Convergence: alpha=1 vs alpha=2 | `GridConfig(alpha_grid=alpha)` + `grid.update_from_levelset(phi, eps=0.05)` |
| (b) | GCL: differentiate f=1 | Threshold: `1e3 * eps_mach ~ 2.2e-13` |

**Key detail**: Non-uniform grid uses `grid.update_from_levelset()` with circular interface SDF. The `h_eff` is computed as mean of `grid.h[ax]`.

## Exp 11-17: DCCD 1D Advection (`exp11_17_dccd_advection_1d.py`)

**Purpose**: Compare O2, CCD, DCCD advection quality on discontinuous/smooth profiles.

**Advection implementation**: Manual RK4 time integration with CCD spatial derivatives:

```
def advect_ccd(q0, ccd, grid, backend, N, dt, n_steps, eps_d=0.0):
    def rhs(q_in):
        d1, _ = ccd.differentiate(q_in, axis=0)
        flux = -1.0 * d1  # c=1
        if eps_d > 0:  # DCCD filter as post-process
            f[1:-1] = flux[1:-1] + eps_d * (flux[2:] - 2*flux[1:-1] + flux[:-2])
        return f
    # RK4 loop: k1, k2, k3, k4
```

**Three initial conditions**: square (discontinuous), triangle (C0), smooth (tanh). Measured via L2 error and Total Variation.

**Key result metrics**: `TV_ccd` vs `TV_dccd` quantifies dissipation; `L2_ccd` vs `L2_dccd` quantifies accuracy preservation.
