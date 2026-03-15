"""
simulation パッケージ。

TwoPhaseSimulation とその補助クラス（境界条件ハンドラ、診断レポータ）を提供する。

パッケージとして再エクスポートすることで、
    from twophase.simulation import TwoPhaseSimulation
    from twophase.simulation import BoundaryConditionHandler
の両方のインポートパスが機能する。
"""

from ._core import TwoPhaseSimulation
from .boundary_condition import BoundaryConditionHandler
from .diagnostics import DiagnosticsReporter

__all__ = [
    "TwoPhaseSimulation",
    "BoundaryConditionHandler",
    "DiagnosticsReporter",
]
