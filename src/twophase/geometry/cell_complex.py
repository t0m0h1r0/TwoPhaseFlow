"""Metric cell complex for geometric phase volume.

Symbol mapping
--------------
``C_h`` -> cells of :class:`MetricCellComplex`
``|C|`` -> :attr:`MetricCellComplex.cell_measures`
``theta_C`` -> :meth:`MetricCellComplex.theta_view`
``q_C`` -> integrated liquid cell volume passed to ``theta_view``

SP-AO makes the integrated cell volume ``q_C=|C| theta_C`` the material owner.
This module only materializes the metric cell measures needed by the first
geometry gate; incidence and face Hodge operators land in later stages.
"""

from __future__ import annotations

from dataclasses import dataclass

from .gpu_runtime_guard import reject_device_value, reject_gpu_namespace


_CACHE_ATTR = "_twophase_metric_cell_complex_cache"


@dataclass(frozen=True)
class MetricCellComplex:
    """Physical cell measures for the current 2D grid geometry."""

    xp: object
    cell_measures: object
    x_edges: object
    y_edges: object

    @property
    def shape(self) -> tuple[int, int]:
        """Return the cell-complex shape, not the nodal array shape."""
        return tuple(int(v) for v in self.cell_measures.shape)

    @classmethod
    def from_grid(cls, grid) -> "MetricCellComplex":
        """Build physical 2D cell measures from grid node coordinates."""
        if grid.ndim != 2:
            raise ValueError("MetricCellComplex currently supports 2D grids")
        reject_gpu_namespace(grid.xp, context="MetricCellComplex.from_grid")
        cache_key = _grid_cache_key(grid)
        cached = getattr(grid, _CACHE_ATTR, None)
        if cached is not None and cached[0] == cache_key:
            return cached[1]
        xp = grid.xp
        x_edges = xp.asarray(grid.coords[0], dtype=float)
        y_edges = xp.asarray(grid.coords[1], dtype=float)
        _validate_finite(xp, x_edges, "x coordinates")
        _validate_finite(xp, y_edges, "y coordinates")
        dx = x_edges[1:] - x_edges[:-1]
        dy = y_edges[1:] - y_edges[:-1]
        if dx.shape[0] != grid.N[0] or dy.shape[0] != grid.N[1]:
            raise ValueError("grid coordinates do not match grid.N")
        if _scalar_bool(xp, xp.any(dx <= 0.0)) or _scalar_bool(xp, xp.any(dy <= 0.0)):
            raise ValueError("MetricCellComplex requires strictly increasing coordinates")
        cell_measures = dx[:, None] * dy[None, :]
        _validate_finite(xp, cell_measures, "cell measures")
        complex_h = cls(
            xp=xp,
            cell_measures=cell_measures,
            x_edges=x_edges,
            y_edges=y_edges,
        )
        try:
            setattr(grid, _CACHE_ATTR, (cache_key, complex_h))
        except Exception:
            pass
        return complex_h

    def theta_view(self, q):
        """Return normalized fractions ``theta_C=q_C/|C|``."""
        q_dev = self.xp.asarray(q)
        _validate_finite(self.xp, q_dev, "q")
        theta = q_dev / self.cell_measures
        _validate_finite(self.xp, theta, "theta")
        return theta


def _validate_finite(xp, value, name: str) -> None:
    if _scalar_bool(xp, xp.any(~xp.isfinite(value))):
        raise ValueError(f"{name} must be finite")


def _grid_cache_key(grid):
    coords = tuple(grid.coords)
    return (
        id(grid.xp),
        tuple(grid.N),
        tuple(_coord_cache_token(coord) for coord in coords),
    )


def _coord_cache_token(coord):
    return (
        id(coord),
        getattr(coord, "shape", None),
        getattr(coord, "dtype", None),
        float(coord[0]),
        float(coord[-1]),
        float(coord.sum() if hasattr(coord, "sum") else sum(coord)),
    )


def _scalar_bool(xp, value) -> bool:
    reject_device_value(value, context="MetricCellComplex scalar reduction")
    return bool(value)
