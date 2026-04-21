"""Surface tension force strategy (CSF vs Null).

Encapsulates the choice between:
- SurfaceTensionForce: applies balanced-force κ ∇ψ / σ
- NullSurfaceTensionForce: no-op (when σ = 0)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


class INSSurfaceTensionStrategy(ABC):
    """Abstract interface for surface tension force computation."""

    @abstractmethod
    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        grad_op=None,
    ) -> Tuple["array", "array"]:
        """Compute surface tension force components f_x, f_y.

        Parameters
        ----------
        kappa : ndarray  interface curvature (already filtered)
        psi : ndarray  Conservative Level Set field (1 = liquid, 0 = gas)
        sigma : float  surface tension coefficient (checked for σ > 0)
        ccd : CCDSolver  differentiation operator
        grad_op : IGradientOperator, optional
            R-1.5: If provided, use for FVM-consistent ∇ψ on non-uniform grids

        Returns
        -------
        f_x, f_y : ndarray  surface tension force per unit volume
        """


class SurfaceTensionForce(INSSurfaceTensionStrategy):
    """Balanced-force CSF: f = σ κ ∇ψ.

    Applied to the momentum equation; also added to PPE RHS for
    consistent balanced-force treatment.
    """

    def __init__(self, backend: "Backend") -> None:
        """

        Parameters
        ----------
        backend : Backend
        """
        self.xp = backend.xp

    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        grad_op=None,
    ) -> Tuple["array", "array"]:
        """Compute f = σ κ ∇ψ componentwise.

        R-1.5: If grad_op (FVM) provided, use for ∇ψ on non-uniform grids.
        """
        if sigma <= 0.0:
            return self.xp.zeros_like(kappa), self.xp.zeros_like(kappa)

        # R-1.5: Use grad_op (FVM) if available, else CCD
        if grad_op is not None:
            dpsi_dx = grad_op.gradient(psi, 0)
            dpsi_dy = grad_op.gradient(psi, 1)
        else:
            dpsi_dx, _ = ccd.differentiate(psi, 0)
            dpsi_dy, _ = ccd.differentiate(psi, 1)

        f_x = sigma * kappa * dpsi_dx
        f_y = sigma * kappa * dpsi_dy
        return f_x, f_y


class NullSurfaceTensionForce(INSSurfaceTensionStrategy):
    """No-op surface tension (Null Object pattern).

    Used when surface tension should be skipped entirely.
    """

    def __init__(self, backend: "Backend") -> None:
        self.xp = backend.xp

    def compute(
        self,
        kappa: "array",
        psi: "array",
        sigma: float,
        ccd: "CCDSolver",
        grad_op=None,
    ) -> Tuple["array", "array"]:
        """Return zero force fields."""
        return self.xp.zeros_like(kappa), self.xp.zeros_like(kappa)
