"""
SimulationComponents — aggregates all components built by SimulationBuilder.

This dataclass acts as the single interface between SimulationBuilder and
TwoPhaseSimulation._from_components(). Adding a new component requires only a
new field here; the _from_components() signature remains stable (OCP).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver
    from ..interfaces.levelset import ILevelSetAdvection, IReinitializer, ICurvatureCalculator
    from ..interfaces.ppe_solver import IPPESolver
    from ..ns_terms.predictor import Predictor
    from ..pressure.rhie_chow import RhieChowInterpolator
    from ..pressure.velocity_corrector import VelocityCorrector
    from ..pressure.ppe_rhs_gfm import PPERHSBuilderGFM
    from ..levelset.field_extender import FieldExtender
    from ..time_integration.cfl import CFLCalculator
    from ..simulation.boundary_condition import BoundaryConditionHandler
    from ..simulation.diagnostics import DiagnosticsReporter


@dataclass
class SimulationComponents:
    """All components assembled by SimulationBuilder.

    Passed as a single argument to TwoPhaseSimulation._from_components(),
    replacing the previous 15-parameter signature.
    """
    config: "SimulationConfig"
    backend: "Backend"
    grid: "Grid"
    eps: float
    ccd: "CCDSolver"
    ls_advect: "ILevelSetAdvection"
    ls_reinit: "IReinitializer"
    curvature_calc: "ICurvatureCalculator"
    predictor: "Predictor"
    ppe_solver: "IPPESolver"
    rhie_chow: "RhieChowInterpolator"
    vel_corrector: "VelocityCorrector"
    cfl_calc: "CFLCalculator"
    bc_handler: "BoundaryConditionHandler"
    diagnostics: "DiagnosticsReporter"
    # GFM pipeline (§8e sec:gfm + §7 sec:dccd_decoupling): None when CSF mode
    ppe_rhs_gfm: "Optional[PPERHSBuilderGFM]" = None
    # Extension PDE (Aslam 2004): smooth δp/p^n across Γ for CCD gradient
    field_extender: "Optional[FieldExtender]" = None
