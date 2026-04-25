"""Pressure-gradient and divergence interfaces plus compatibility exports."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import ClassVar

from ..core.registry import SchemeRegistryMixin


class IGradientOperator(SchemeRegistryMixin, ABC):
    """Abstract interface for computing pressure gradient ∇p."""

    _registry: ClassVar[dict[str, type["IGradientOperator"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                       = {}
    _scheme_kind: ClassVar[str] = "gradient scheme"

    @abstractmethod
    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute gradient of pressure along axis.

        Parameters
        ----------
        p : ndarray  pressure field
        axis : int  coordinate axis (0 for x, 1 for y[, 2 for z])

        Returns
        -------
        dp_daxis : ndarray  pressure gradient along axis
        """


class IDivergenceOperator(ABC):
    """Abstract interface for computing vector divergence."""

    @abstractmethod
    def divergence(self, components: list["array"]) -> "array":
        """Compute ``sum_i d components[i] / dx_i``."""

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """Apply face-flux projection if supported by this divergence strategy."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support face-flux projection"
        )

    def project_faces(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """Return corrected face fluxes if supported by this strategy."""
        raise NotImplementedError(
            f"{type(self).__name__} does not expose projected face fluxes"
        )

    def reconstruct_nodes(self, face_components: list["array"]) -> list["array"]:
        """Reconstruct nodal velocities from face fluxes if supported."""
        raise NotImplementedError(
            f"{type(self).__name__} does not reconstruct nodal velocities"
        )

    def divergence_from_faces(self, face_components: list["array"]) -> "array":
        """Compute divergence directly from face fluxes if supported."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support face-flux divergence"
        )


from .divergence_ops import (
    CCDDivergenceOperator,
    FCCDDivergenceOperator,
    FVMDivergenceOperator,
)
from .gradient_ops import (
    CCDGradientOperator,
    FCCDGradientOperator,
    FVMGradientOperator,
)

__all__ = [
    "IGradientOperator",
    "IDivergenceOperator",
    "CCDGradientOperator",
    "FCCDGradientOperator",
    "FVMGradientOperator",
    "CCDDivergenceOperator",
    "FVMDivergenceOperator",
    "FCCDDivergenceOperator",
]
