---
id: WIKI-L-010
title: "PPE Solver Architecture: Factory Registry, Template Method, and Legacy Management"
status: ACTIVE
created: 2026-04-10
depends_on: [WIKI-L-009, WIKI-T-005, WIKI-T-012, WIKI-T-024]
---

# PPE Solver Architecture

## Active Solvers (production)

| Solver | Key | Method | Accuracy | Use Case |
|--------|-----|--------|----------|----------|
| PPESolverCCDLU | `ccd_lu` | CCD Kronecker + sparse LU (spsolve) | O(h^6) | Production default (PR-6 compliant) |
| PPESolverIIM | `iim` | CCD Kronecker + IIM interface correction | O(h^6) | Interface-capturing (experimental) |
| PPESolverIterative | `iterative` | Configurable {ccd,3pt} x {explicit,gs,adi} | varies | Research toolkit |

## Legacy Solvers (C2 retained, in `pressure/legacy/`)

| Solver | Key | Violation | Reason Kept |
|--------|-----|-----------|-------------|
| PPESolver | — | PR-1 (FVM O(h^2)) | BiCGSTAB reference |
| PPESolverLU | — | PR-1 (FVM O(h^2)) | Direct LU reference |
| PPESolverPseudoTime | `pseudotime` | PR-6 (LGMRES) | CCD+LGMRES baseline |
| PPESolverSweep | `sweep` | ADI O(h^4)/iter | Matrix-free reference |
| PPESolverDCOmega | `dc_omega` | ADI limitation | Under-relaxed ADI reference |

All legacy solvers emit `DeprecationWarning` when instantiated via factory.

## Factory Registry Pattern (`ppe_solver_factory.py`)

```python
_SOLVER_REGISTRY: Dict[str, Callable] = {}

def register_ppe_solver(name: str, factory_fn: Callable) -> None:
    _SOLVER_REGISTRY[name] = factory_fn

def create_ppe_solver(config, backend, grid, ccd=None, bc_spec=None) -> IPPESolver:
    factory_fn = _SOLVER_REGISTRY[config.solver.ppe_solver_type]
    return factory_fn(config, backend, grid, ccd, bc_spec)
```

**OCP compliance**: Adding a new solver requires only `register_ppe_solver("name", fn)` — no modification to factory code.

## Template Method: _CCDPPEBase

```
_CCDPPEBase(IPPESolver)
├── _build_1d_ccd_matrices()    # pre-computed once in __init__
├── _build_sparse_operator()    # Kronecker product L_CCD^rho
├── _assemble_pinned_system()   # operator + pin + RHS
├── solve()                     # template: assemble -> _solve_linear_system
├── compute_residual()          # diagnostic
└── _solve_linear_system()      # ABSTRACT — subclasses provide strategy
    ├── PPESolverCCDLU:         spsolve (direct LU)
    └── PPESolverPseudoTime:    LGMRES (legacy)
```

**Kronecker product assembly** (app:ccd_kronecker):
The 2D operator is built as `L = kron(I_y, Dx2) + kron(Dy2, I_x)` with variable-density product-rule terms. Pre-computed once; reused across time steps when density changes.

## Auxiliary Components

| Component | File | Role |
|-----------|------|------|
| PPEBuilder | `ppe_builder.py` | FVM matrix assembly (legacy solvers only) |
| RhieChowInterpolator | `rhie_chow.py` | Face velocity u*_RC = u* - (dt/rho) grad(p) + balanced-force |
| VelocityCorrector | `velocity_corrector.py` | u^{n+1} = u* - (dt/rho) grad(delta_p) via CCD |
| PPERHSBuilderGFM | `ppe_rhs_gfm.py` | GFM-corrected PPE RHS (alternative to Rhie-Chow) |
| GFMCorrector | `gfm.py` | Ghost Fluid Method pressure jump correction |
| DCCDPPEFilter | `dccd_ppe_filter.py` | DCCD-filtered divergence for GFM RHS |
