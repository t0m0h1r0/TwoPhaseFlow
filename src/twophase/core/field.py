"""
Scalar and vector field containers.

Thin wrappers that keep a data array together with its associated grid so
that all numerical routines operate on the same shape and spacing.

These classes carry no numerical logic — they are pure data holders.
"""

from __future__ import annotations
from typing import List, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from .grid import Grid


class ScalarField:
    """A scalar field on ``grid``.

    Attributes
    ----------
    data : xp.ndarray, shape ``grid.shape``
    grid : Grid
    """

    def __init__(self, grid: "Grid", backend: "Backend"):
        self.grid = grid
        self.backend = backend
        self.xp = backend.xp
        self.data = self.xp.zeros(grid.shape, dtype=float)

    def zeros_like(self) -> "ScalarField":
        """Return a zero-filled ScalarField on the same grid."""
        return ScalarField(self.grid, self.backend)

    def copy(self) -> "ScalarField":
        """Return a deep copy."""
        f = ScalarField(self.grid, self.backend)
        f.data = self.xp.copy(self.data)
        return f

    def __repr__(self) -> str:
        return f"ScalarField(shape={self.data.shape})"


class VectorField:
    """A vector field on ``grid`` with one component per spatial dimension.

    Attributes
    ----------
    components : list[ScalarField], length ``grid.ndim``
    """

    def __init__(self, grid: "Grid", backend: "Backend"):
        self.grid = grid
        self.backend = backend
        self.ndim = grid.ndim
        self.components: List[ScalarField] = [
            ScalarField(grid, backend) for _ in range(grid.ndim)
        ]

    # ── Component access shortcuts ────────────────────────────────────────

    @property
    def u(self) -> ScalarField:
        """x-component (axis 0)."""
        return self.components[0]

    @property
    def v(self) -> ScalarField:
        """y-component (axis 1)."""
        return self.components[1]

    @property
    def w(self) -> ScalarField:
        """z-component (axis 2) — only valid for 3-D grids."""
        assert self.ndim == 3, "w component only available for ndim=3"
        return self.components[2]

    # ── Utilities ─────────────────────────────────────────────────────────

    def zeros_like(self) -> "VectorField":
        return VectorField(self.grid, self.backend)

    def copy(self) -> "VectorField":
        vf = VectorField(self.grid, self.backend)
        for ax in range(self.ndim):
            vf.components[ax].data = self.backend.xp.copy(
                self.components[ax].data
            )
        return vf

    def __getitem__(self, ax: int):
        """``vel[ax]`` returns the data array for component ``ax``."""
        return self.components[ax].data

    def __setitem__(self, ax: int, value):
        self.components[ax].data = value

    def __repr__(self) -> str:
        s = self.components[0].data.shape
        return f"VectorField(ndim={self.ndim}, shape={s})"
