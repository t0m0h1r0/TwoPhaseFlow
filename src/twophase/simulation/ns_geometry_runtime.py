"""Geometry/bootstrap helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..backend import Backend
from ..ccd.ccd_solver import CCDSolver
from ..config import GridConfig
from ..core.grid import Grid


@dataclass(frozen=True)
class NSGeometryRuntimeState:
    NX: int
    NY: int
    LX: float
    LY: float
    bc_type: str
    alpha_grid: float
    eps_factor: float
    eps_xi_cells: float | None
    use_local_eps: bool
    h: float
    eps: float
    backend: Backend
    grid: Grid
    ccd: CCDSolver


def build_ns_geometry_runtime(options) -> NSGeometryRuntimeState:
    alpha_grid = float(options.alpha_grid)
    eps_factor = float(options.eps_factor)
    eps_xi_cells = options.eps_xi_cells
    use_local_eps = bool(options.use_local_eps) or (options.eps_xi_cells is not None)
    h = options.LX / options.NX
    eps = eps_factor * h

    backend = Backend(use_gpu=options.use_gpu)
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(options.NX, options.NY),
            L=(options.LX, options.LY),
            alpha_grid=options.alpha_grid,
            eps_g_factor=options.eps_g_factor,
            eps_g_cells=options.eps_g_cells,
            dx_min_floor=options.dx_min_floor,
        ),
        backend,
    )
    ccd = CCDSolver(grid, backend, bc_type=options.bc_type)
    return NSGeometryRuntimeState(
        NX=options.NX,
        NY=options.NY,
        LX=options.LX,
        LY=options.LY,
        bc_type=options.bc_type,
        alpha_grid=alpha_grid,
        eps_factor=eps_factor,
        eps_xi_cells=eps_xi_cells,
        use_local_eps=use_local_eps,
        h=h,
        eps=eps,
        backend=backend,
        grid=grid,
        ccd=ccd,
    )
