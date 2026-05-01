"""
PPE solver factory (OCP + DIP).

Creates IPPESolver instances based on SimulationConfig.ppe_solver_type.

Active solvers:
    - "fvm_iterative" : matrix-free FVM PPE + line-preconditioned GMRES
    - "fvm_direct"    : FVM PPE + sparse direct solve
    - "fd_direct"     : factorized FD L_L correction solve for DC
    - "iim"       : CCD Kronecker + IIM interface correction
    - "iterative" : configurable research toolkit ({ccd,3pt}x{explicit,gs,adi})
    - "ccd_lu"    : CCD Kronecker + direct LU, restricted reference path

To add a new solver: call register_ppe_solver(name, factory_fn).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Dict

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec
    from .interfaces import IPPESolver


# ── Solver registry (OCP: add solvers without modifying this file) ────────

_SOLVER_REGISTRY: Dict[str, Callable] = {}


def register_ppe_solver(name: str, factory_fn: Callable) -> None:
    """Register a PPE solver factory function.

    Parameters
    ----------
    name       : str — solver type key (used in config.solver.ppe_solver_type)
    factory_fn : callable(config, backend, grid, ccd, bc_spec) -> IPPESolver
    """
    _SOLVER_REGISTRY[name] = factory_fn


def _make_bc_spec(config, grid):
    """Auto-generate BoundarySpec from config + grid when not provided."""
    from ..core.boundary import BoundarySpec
    return BoundarySpec(
        bc_type=config.numerics.bc_type,
        shape=tuple(n + 1 for n in config.grid.N),
        N=config.grid.N,
    )


# ── Active solver registrations ───────────────────────────────────────────

def _create_ccd_lu(config, backend, grid, ccd, bc_spec):
    if not bool(getattr(config.solver, "allow_kronecker_lu", False)):
        raise ValueError(
            "ccd_lu is a restricted Kronecker-LU reference solver. "
            "Use ppe_solver_type='fvm_iterative' for normal runs, or set "
            "allow_kronecker_lu=True only for intentional component/reference use."
        )
    from .ccd_lu import PPESolverCCDLU
    return PPESolverCCDLU(backend, config, grid, ccd=ccd, bc_spec=bc_spec)


def _create_iim(config, backend, grid, ccd, bc_spec):
    from .iim_solver import PPESolverIIM
    return PPESolverIIM(backend, config, grid, ccd=ccd, bc_spec=bc_spec)


def _create_iterative(config, backend, grid, ccd, bc_spec):
    from .iterative import PPESolverIterative
    return PPESolverIterative(backend, config, grid, ccd=ccd, bc_spec=bc_spec)


def _create_fvm_spsolve(config, backend, grid, ccd, bc_spec):
    from .fvm_spsolve import PPESolverFVMSpsolve
    return PPESolverFVMSpsolve(backend, grid, bc_type=config.numerics.bc_type, bc_spec=bc_spec)


def _create_fvm_matrixfree(config, backend, grid, ccd, bc_spec):
    from .fvm_matrixfree import PPESolverFVMMatrixFree
    return PPESolverFVMMatrixFree(
        backend, config, grid, bc_type=config.numerics.bc_type, bc_spec=bc_spec
    )


def _create_fd_direct(config, backend, grid, ccd, bc_spec):
    from .fd_direct import PPESolverFDDirect
    return PPESolverFDDirect(backend, grid, bc_type=config.numerics.bc_type, bc_spec=bc_spec)


register_ppe_solver("ccd_lu", _create_ccd_lu)
register_ppe_solver("iim", _create_iim)
register_ppe_solver("iterative", _create_iterative)
register_ppe_solver("fvm_direct", _create_fvm_spsolve)
register_ppe_solver("fvm_spsolve", _create_fvm_spsolve)
register_ppe_solver("fvm_iterative", _create_fvm_matrixfree)
register_ppe_solver("fvm_matrixfree", _create_fvm_matrixfree)
register_ppe_solver("fd_direct", _create_fd_direct)


# ── Public factory function ───────────────────────────────────────────────

def create_ppe_solver(
    config: "SimulationConfig",
    backend: "Backend",
    grid: "Grid",
    ccd=None,
    bc_spec: "BoundarySpec | None" = None,
) -> "IPPESolver":
    """Create a PPE solver from config.solver.ppe_solver_type.

    Parameters
    ----------
    config  : SimulationConfig
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver (optional) — injected into CCD-based solvers
    bc_spec : BoundarySpec (optional) — auto-generated from config if None
    """
    if bc_spec is None:
        bc_spec = _make_bc_spec(config, grid)

    solver_type = config.solver.ppe_solver_type

    factory_fn = _SOLVER_REGISTRY.get(solver_type)
    if factory_fn is None:
        available = ", ".join(sorted(_SOLVER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown ppe_solver_type: '{solver_type}'. "
            f"Available: {available}"
        )

    return factory_fn(config, backend, grid, ccd, bc_spec)
