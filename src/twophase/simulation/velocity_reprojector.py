"""Velocity reprojection interface plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar
import numpy as np

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.interfaces import IPPESolver
    from .scheme_build_ctx import ReprojectorBuildCtx


def _device_array(arr, backend: "Backend"):
    """Return ``arr`` on the active backend device."""
    return backend.to_device(arr)


def _host_array(arr, backend: "Backend") -> np.ndarray:
    """Return ``arr`` as a NumPy array."""
    return np.asarray(backend.to_host(arr))


class IVelocityReprojector(ABC):
    """Abstract interface for velocity reprojection after grid rebuild."""

    _registry: ClassVar[dict[str, type["IVelocityReprojector"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                          = {}

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for name in getattr(cls, "scheme_names", ()):
            IVelocityReprojector._registry[name] = cls
        for alias, canonical in getattr(cls, "_scheme_aliases", {}).items():
            IVelocityReprojector._aliases[alias] = canonical

    @classmethod
    def from_scheme(cls, name: str, ctx: "ReprojectorBuildCtx") -> "IVelocityReprojector":
        """Instantiate the reprojector registered under *name*."""
        canonical = cls._aliases.get(name, name)
        klass = cls._registry.get(canonical)
        if klass is None:
            raise ValueError(
                f"Unknown reproject_mode {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return klass._build(canonical, ctx)

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
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Reproject velocity to satisfy ∇·u = 0 on remapped grid.

        Parameters
        ----------
        psi : ndarray  CLS field (1 = liquid, 0 = gas)
        u, v : ndarray  velocity components (remapped, may have divergence)
        ppe_solver : IPPESolver  PPE solver instance
        ccd : CCDSolver  CCD differentiation instance
        backend : Backend  array backend (CPU/GPU)
        rho_l, rho_g : float or None  densities (only used by variable-density modes)

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
    LegacyReprojector,
    VariableDensityReprojector,
)
from .velocity_reprojector_iim import ConsistentIIMReprojector

__all__ = [
    "IVelocityReprojector",
    "LegacyReprojector",
    "VariableDensityReprojector",
    "ConsistentGFMReprojectorLegacy",
    "ConsistentGFMReprojector",
    "ConsistentIIMReprojector",
]
