"""
simulation パッケージ。

TwoPhaseSimulation、SimulationBuilder、および補助クラスを提供する。

パッケージとして再エクスポートすることで、
    from twophase.simulation import TwoPhaseSimulation
    from twophase.simulation import SimulationBuilder
    from twophase.simulation import BoundaryConditionHandler
の全インポートパスが機能する。

推奨される構築方法:
    - デフォルト: ``TwoPhaseSimulation(config)`` （後方互換）
    - カスタム:   ``SimulationBuilder(config).with_ppe_solver(...).build()``
"""

from ._core import TwoPhaseSimulation
from .builder import SimulationBuilder
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter

__all__ = [
    "TwoPhaseSimulation",
    "SimulationBuilder",
    "BoundaryConditionHandler",
    "DiagnosticsReporter",
]
