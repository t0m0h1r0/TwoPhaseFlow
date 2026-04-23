"""
simulation パッケージ。

modern NS pipeline と legacy simulation stack を提供する。

パッケージとして再エクスポートすることで、
    from twophase.simulation import TwoPhaseNSSolver
    from twophase.simulation import NSSolverBuilder
    from twophase.simulation import TwoPhaseSimulation
    from twophase.simulation import SimulationBuilder
の全インポートパスが機能する。

推奨される構築方法:
    - modern NS pipeline: ``NSSolverBuilder(cfg).build()`` または
      ``TwoPhaseNSSolver.from_config(cfg)``
    - legacy split-step stack: ``SimulationBuilder(config).build()``
"""

from ._core import TwoPhaseSimulation
from .builder import SimulationBuilder
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter
from .legacy import TwoPhaseSimulationLegacy, SimulationBuilderLegacy
from .ns_pipeline import TwoPhaseNSSolver
from .ns_solver_builder import NSSolverBuilder
from .ns_step_state import NSStepRequest

__all__ = [
    "TwoPhaseNSSolver",
    "NSSolverBuilder",
    "NSStepRequest",
    "TwoPhaseSimulation",
    "TwoPhaseSimulationLegacy",
    "SimulationBuilder",
    "SimulationBuilderLegacy",
    "BoundaryConditionHandler",
    "DiagnosticsReporter",
]
