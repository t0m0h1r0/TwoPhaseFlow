"""Step-level diagnostics strategy (Null Object pattern).

Encapsulates optional per-step diagnostic recording in a cleaner interface than
scattered `if self._debug_diag:` branches throughout step().
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any


class IStepDiagnostics(ABC):
    """Abstract interface for step-level diagnostics recording."""

    @abstractmethod
    def record_kappa(self, kappa_max: float) -> None:
        """Record maximum curvature magnitude."""

    @abstractmethod
    def record_ppe_rhs(self, ppe_rhs_max: float) -> None:
        """Record maximum PPE RHS magnitude."""

    @abstractmethod
    def record_bf_residual(self, bf_residual_max: float) -> None:
        """Record maximum balanced-force residual."""

    @abstractmethod
    def record_div_u(self, div_u_max: float) -> None:
        """Record maximum velocity divergence."""

    @abstractmethod
    def record_ppe_stats(self, stats: Dict[str, float]) -> None:
        """Record optional PPE solver diagnostics."""

    @property
    @abstractmethod
    def last(self) -> Dict[str, float]:
        """Return dict of most recently recorded values."""


class NullStepDiagnostics(IStepDiagnostics):
    """No-op diagnostics (Null Object).

    Used when debug_diagnostics=False. All methods are no-ops.
    """

    def record_kappa(self, kappa_max: float) -> None:
        pass

    def record_ppe_rhs(self, ppe_rhs_max: float) -> None:
        pass

    def record_bf_residual(self, bf_residual_max: float) -> None:
        pass

    def record_div_u(self, div_u_max: float) -> None:
        pass

    def record_ppe_stats(self, stats: Dict[str, float]) -> None:
        pass

    @property
    def last(self) -> Dict[str, float]:
        return {}


class ActiveStepDiagnostics(IStepDiagnostics):
    """Active diagnostics recorder.

    Used when debug_diagnostics=True. Stores the most recent values.
    """

    def __init__(self):
        self._last: Dict[str, float] = {
            "kappa_max": 0.0,
            "ppe_rhs_max": 0.0,
            "bf_residual_max": 0.0,
            "div_u_max": 0.0,
        }

    def record_kappa(self, kappa_max: float) -> None:
        self._last["kappa_max"] = float(kappa_max)

    def record_ppe_rhs(self, ppe_rhs_max: float) -> None:
        self._last["ppe_rhs_max"] = float(ppe_rhs_max)

    def record_bf_residual(self, bf_residual_max: float) -> None:
        self._last["bf_residual_max"] = float(bf_residual_max)

    def record_div_u(self, div_u_max: float) -> None:
        self._last["div_u_max"] = float(div_u_max)

    def record_ppe_stats(self, stats: Dict[str, float]) -> None:
        for key, value in stats.items():
            self._last[str(key)] = float(value)

    @property
    def last(self) -> Dict[str, float]:
        return dict(self._last)
