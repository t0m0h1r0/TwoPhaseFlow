"""Viscous predictor interface plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING, ClassVar

from ..core.registry import SchemeRegistryMixin

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


class IViscousPredictor(SchemeRegistryMixin, ABC):
    """Abstract interface for viscous predictor (advance velocity with viscous term)."""

    _registry: ClassVar[dict[str, type["IViscousPredictor"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                       = {}
    _scheme_kind: ClassVar[str] = "viscous time scheme"

    @abstractmethod
    def predict(
        self,
        u: "array",
        v: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
        intermediate_velocity_operator_transform: Callable[[list], None] | None = None,
        predictor_state_assembly: Callable[..., list] | None = None,
    ) -> tuple["array", "array"]:
        """Advance velocity with viscous + convection + optional buoyancy.

        Parameters
        ----------
        u, v : ndarray  velocity components
        conv_u, conv_v : ndarray  convection terms −(u·∇)u
        mu : ndarray  dynamic viscosity (scalar or field)
        rho : ndarray  density field
        dt : float  timestep
        ccd : CCDSolver  differentiation operator
        buoy_v : ndarray, optional  buoyancy term for v-component
        psi : ndarray, optional  Heaviside interface field for band switching

        Returns
        -------
        u_star, v_star : ndarray  predicted velocity
        """


from .viscous_predictors import (
    CNViscousPredictor,
    ExplicitViscousPredictor,
    ImplicitBDF2ViscousPredictor,
)

__all__ = [
    "IViscousPredictor",
    "ExplicitViscousPredictor",
    "CNViscousPredictor",
    "ImplicitBDF2ViscousPredictor",
]
