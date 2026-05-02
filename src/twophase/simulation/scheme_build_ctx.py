"""Per-category build-context dataclasses for scheme self-registration.

Each ``from_scheme()`` factory on an ABC receives one of these objects.
Each concrete class's ``_build(name, ctx)`` pulls only the fields it needs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import SimpleNamespace
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ccd.fccd import FCCDSolver
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec
    from ..ns_terms.viscous import ViscousTerm
    from ..ppe.iim.stencil_corrector import IIMStencilCorrector
    from ..levelset.reconstruction import HeavisideInterfaceReconstructor


@dataclass
class GradientBuildCtx:
    ccd_op: object            # pre-built CCDGradientOperator (shared across roles)
    fccd: "FCCDSolver | None"


@dataclass
class AdvectionBuildCtx:
    backend: "Backend"
    grid: "Grid"
    ccd: "CCDSolver"
    bc_type: str
    fccd: "FCCDSolver | None"


@dataclass
class ConvectionBuildCtx:
    backend: "Backend"
    ccd: "CCDSolver"
    grid: "Grid"
    fccd: "FCCDSolver | None"
    uccd6_sigma: float = 1.0e-3


@dataclass
class ReprojectorBuildCtx:
    iim_stencil_corrector: "IIMStencilCorrector | None" = None
    reconstruct_base: object = None


@dataclass
class SurfaceTensionBuildCtx:
    backend: "Backend"


@dataclass
class ViscousBuildCtx:
    backend: "Backend"
    re: float
    spatial_scheme: str = "ccd_bulk"
    viscous_term: "ViscousTerm | None" = None
    cn_mode: str = "picard"
    solver: str = "defect_correction"
    solver_tolerance: float = 1.0e-8
    solver_max_iterations: int = 80
    solver_restart: int = 40
    dc_max_iterations: int = 3
    dc_relaxation: float = 0.8


@dataclass
class PPEBuildCtx:
    backend: "Backend"
    grid: "Grid"
    bc_type: str
    bc_spec: "BoundarySpec | None" = None
    config: "SimpleNamespace | None" = None
    fccd: "FCCDSolver | None" = None
