"""
Abstract interfaces for level-set operators.

Based on OCP (Open/Closed Principle): enables swapping level-set operators.
Based on DIP (Dependency Inversion): TwoPhaseSimulation depends on these
interfaces, not on concrete classes.

Swapping implementations allows changing:
    - Time integration scheme (TVD-RK3 -> RK4)
    - Reinitialization algorithm
    - Curvature computation method
without modifying TwoPhaseSimulation itself.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


class ILevelSetAdvection(ABC):
    """Abstract interface for CLS field advection operators.

    Implementations:
        - LevelSetAdvection        (WENO5 + TVD-RK3, reference scheme)
        - DissipativeCCDAdvection  (DCCD + TVD-RK3, paper-primary §5)
    """

    @abstractmethod
    def advance(
        self,
        psi: "array",
        velocity_components: List,
        dt: float,
    ) -> "array":
        """Advect CLS field psi by time step dt.

        Parameters
        ----------
        psi                 : CLS field psi in [0, 1]
        velocity_components : velocity component list [u, v[, w]]
        dt                  : time step size

        Returns
        -------
        psi_new : advected CLS field
        """


class IReinitializer(ABC):
    """Abstract interface for CLS field reinitialization operators.

    Implementations:
        - Reinitializer      (DCCD + CN-ADI, paper §5c; methods: split/unified/dgr/hybrid)
        - ReinitializerWENO5 (WENO5 + TVD-RK3, legacy — DO NOT DELETE)
    """

    @abstractmethod
    def reinitialize(self, psi: "array") -> "array":
        """Reinitialize CLS field to equilibrium profile.

        Parameters
        ----------
        psi : post-advection CLS field psi

        Returns
        -------
        psi_new : reinitialized CLS field
        """


class ICurvatureCalculator(ABC):
    """Abstract interface for interface curvature computation.

    Implementations:
        - CurvatureCalculator    (phi-based, CCD O(h^6), §2.6 — legacy, DO NOT DELETE)
        - CurvatureCalculatorPsi (psi-direct, §3b — recommended)
    """

    @abstractmethod
    def compute(self, psi: "array") -> "array":
        """Compute interface curvature kappa from CLS field psi.

        Parameters
        ----------
        psi : CLS field psi in [0, 1]

        Returns
        -------
        kappa : interface curvature (same shape as psi)
        """
