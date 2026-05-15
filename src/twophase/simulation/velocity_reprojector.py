"""Velocity reprojection interface plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar
import numpy as np

from ..core.registry import SchemeRegistryMixin

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.interfaces import IPPESolver


def _device_array(arr, backend: "Backend"):
    """Return ``arr`` on the active backend device."""
    return backend.to_device(arr)


def _host_array(arr, backend: "Backend") -> np.ndarray:
    """Return ``arr`` as a NumPy array."""
    return np.asarray(backend.to_host(arr))


class IVelocityReprojector(SchemeRegistryMixin, ABC):
    """Abstract interface for velocity reprojection after grid rebuild."""

    _registry: ClassVar[dict[str, type["IVelocityReprojector"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                          = {}
    _scheme_kind: ClassVar[str] = "reproject_mode"

    @abstractmethod
    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
        face_no_slip_boundary_state: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Reproject velocity to satisfy ∇·u = 0 on remapped grid.

        Parameters
        ----------
        psi : ndarray  CLS field (1 = liquid, 0 = gas)
        u, v : ndarray  velocity components (remapped, may have divergence)
        ppe_solver : IPPESolver  PPE solver instance
        ccd : CCDSolver  CCD differentiation instance
        backend : Backend  array backend (CPU/GPU)
        rho_l, rho_g : float or None  densities (only used by variable-density modes)
        div_op : optional  active face divergence/pressure-reaction complex
        ppe_runtime : optional  projection settings paired with ``ppe_solver``
        bc_type : str  boundary convention for face-state wall treatment
        face_no_slip_boundary_state : bool
            If true, face-native reprojectors must keep their transported face
            state in the no-slip constrained face space used by the main
            predictor/corrector route.

        Returns
        -------
        u_proj, v_proj : ndarray  divergence-free velocity
        """

    @property
    @abstractmethod
    def stats(self) -> dict[str, float]:
        """Return dict of reprojection statistics (calls, accepts, rejects, etc.)."""
from .velocity_reprojector_basic import (
    ConsistentGFMReprojector,
    ConsistentGFMReprojectorLegacy,
    FaceHodgeReprojector,
    LegacyReprojector,
    VariableDensityReprojector,
)

__all__ = [
    "IVelocityReprojector",
    "LegacyReprojector",
    "VariableDensityReprojector",
    "FaceHodgeReprojector",
    "ConsistentGFMReprojectorLegacy",
    "ConsistentGFMReprojector",
]
