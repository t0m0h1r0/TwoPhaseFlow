"""Base types and validation helpers for initial-condition shapes."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class ShapePrimitive(ABC):
    """Abstract base for signed-distance shape primitives."""

    @property
    @abstractmethod
    def interior_phase(self) -> str:
        """'liquid' or 'gas'."""

    @abstractmethod
    def sdf(self, *coords: np.ndarray) -> np.ndarray:
        """Return signed distance field φ (negative inside)."""


def validate_shape_phase(phase: str) -> None:
    """Validate the phase convention used by a shape primitive."""
    if phase not in ("liquid", "gas"):
        raise ValueError(
            f"interior_phase must be 'liquid' or 'gas', got '{phase}'."
        )
