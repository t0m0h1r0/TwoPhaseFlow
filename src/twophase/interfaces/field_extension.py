"""
Abstract interface for field extension across interfaces.

DIP (Dependency Inversion): simulation components depend on this interface,
not on the concrete HermiteFieldExtension implementation.

Paper reference: §8.4 (HFE — Hermite Field Extension)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class IFieldExtension(ABC):
    """Interface for extending a scalar field across the interface Γ.

    Given a scalar field q defined on the source phase (φ < 0 by convention),
    produce q_ext that smoothly extends q into the target phase (φ ≥ 0)
    so that ∇q · n̂ = 0 in the extended region (Extension PDE steady state).

    Symbol mapping (paper → code):
        q           → field_data
        φ           → phi
        q_ext       → return value
        n̂           → computed internally from ∇φ/|∇φ|
    """

    @abstractmethod
    def extend(
        self,
        field_data: "array",
        phi: "array",
        source_sign: float,
    ) -> "array":
        """Extend field_data from the source phase across Γ.

        Parameters
        ----------
        field_data : array, shape grid.shape
            Scalar field to extend (e.g. pressure p^n or increment δp).
        phi : array, shape grid.shape
            Signed-distance function. |∇φ| ≈ 1 (SDF condition).
        source_sign : float
            Sign of φ in the source phase.
            -1.0 → source is liquid (φ < 0), extend into gas (φ ≥ 0).
            +1.0 → source is gas (φ > 0), extend into liquid (φ ≤ 0).

        Returns
        -------
        field_ext : array, same shape as field_data
            Extended field. Equals field_data in the source phase;
            smoothly extended in the target phase with O(h^6) accuracy.
        """
