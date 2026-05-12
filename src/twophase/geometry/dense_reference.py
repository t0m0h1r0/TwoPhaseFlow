"""Dense oracle geometry for SP-AO geometric cell fractions.

A3 chain:
  Equation: SP-AO defines ``Q_h(phi)_C`` as the P1 cut-cell liquid volume and
  ``S_h(phi)`` as the P1 interface measure on each metric cell.
  Discretization: marching-squares P1 cell polygons on the full cell complex.
  Code: this module evaluates the dense reference oracle only.

Symbol mapping
--------------
``C_h`` -> cells of :class:`MetricCellComplex`
``|C|`` -> :attr:`MetricCellComplex.cell_measures`
``phi`` -> continuous nodal gauge
``Q_h(phi)_C`` -> :attr:`P1CutGeometry.q`
``A_h(phi)_C`` -> :attr:`P1CutGeometry.theta`
``S_h(phi)`` -> :attr:`P1CutGeometry.surface_length`

This code is imported from the direct AO branch as an oracle/test reference.
It is not a production fallback, not an active AO-Fast kernel, and not a runtime
YAML activation path.
"""

from __future__ import annotations

from dataclasses import dataclass


_CACHE_ATTR = "_twophase_dense_reference_metric_cell_complex_cache"
_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))


@dataclass(frozen=True)
class MetricCellComplex:
    """Dense physical cell measures for the current 2D grid geometry."""

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
        """Build dense physical 2D cell measures from grid node coordinates."""
        if grid.ndim != 2:
            raise ValueError("MetricCellComplex currently supports 2D grids")
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


@dataclass(frozen=True)
class P1CutGeometry:
    """Dense P1 cut-cell volumes and surface lengths for one nodal gauge."""

    q: object
    theta: object
    surface_length: float
    cell_surface_lengths: object
    sign_margin: float


def cut_geometry_2d(grid, phi, *, level: float = 0.0) -> P1CutGeometry:
    """Return dense reference ``Q_h``, ``A_h``, and ``S_h`` for a 2D P1 trace."""
    if grid.ndim != 2:
        raise ValueError("cut_geometry_2d currently supports 2D grids")
    complex_h = MetricCellComplex.from_grid(grid)
    xp = complex_h.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")

    phi_rel = phi_dev - float(level)
    _validate_regular_values(xp, phi_rel)

    values, points = _cell_corner_fields(xp, grid, phi_rel, complex_h=complex_h)
    q_dev = _local_cut_areas(xp, values, points)
    length_dev = _local_surface_lengths(xp, values, points)
    sign_margin = _scalar_float(xp, xp.min(xp.abs(phi_rel)))
    return P1CutGeometry(
        q=q_dev,
        theta=complex_h.theta_view(q_dev),
        surface_length=_scalar_float(xp, xp.sum(length_dev)),
        cell_surface_lengths=length_dev,
        sign_margin=sign_margin,
    )


def _cell_corner_fields(xp, grid, phi, *, complex_h=None):
    if complex_h is None:
        x = xp.asarray(grid.coords[0], dtype=phi.dtype)
        y = xp.asarray(grid.coords[1], dtype=phi.dtype)
    else:
        x = _astype_like(complex_h.x_edges, phi)
        y = _astype_like(complex_h.y_edges, phi)
    x0 = x[:-1].reshape((-1, 1))
    x1 = x[1:].reshape((-1, 1))
    y0 = y[:-1].reshape((1, -1))
    y1 = y[1:].reshape((1, -1))
    values = (
        phi[:-1, :-1],
        phi[1:, :-1],
        phi[1:, 1:],
        phi[:-1, 1:],
    )
    points = (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
    )
    return values, points


def _astype_like(value, reference):
    if getattr(value, "dtype", None) == getattr(reference, "dtype", None):
        return value
    return value.astype(reference.dtype, copy=False)


def _validate_regular_values(xp, phi_rel) -> None:
    if _scalar_bool(xp, xp.any(~xp.isfinite(phi_rel))):
        raise ValueError("P1 cut geometry requires finite phi values")
    if _scalar_bool(xp, xp.any(phi_rel == 0.0)):
        raise ValueError("P1 cut geometry requires a regular sign stratum")


def _edge_crossing(xp, values, points, edge: int):
    lo, hi = _EDGE_CORNERS[edge]
    value_lo = values[lo]
    value_hi = values[hi]
    mask = value_lo * value_hi < 0.0
    denominator = value_hi - value_lo
    safe_denominator = xp.where(mask, denominator, xp.ones_like(denominator))
    theta = xp.where(mask, -value_lo / safe_denominator, 0.0)
    x = points[lo][0] + theta * (points[hi][0] - points[lo][0])
    y = points[lo][1] + theta * (points[hi][1] - points[lo][1])
    return {"mask": mask, "x": x, "y": y}


def _case_field(xp, values):
    inside = tuple(value < 0.0 for value in values)
    case_field = xp.zeros_like(values[0], dtype=xp.uint8)
    for corner, mask in enumerate(inside):
        case_field = case_field + mask.astype(xp.uint8) * (1 << corner)
    return case_field


def _local_cut_areas(xp, values, points):
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_field = _case_field(xp, values)
    local_area = xp.zeros_like(values[0])
    for case_id in range(16):
        for tokens in _liquid_polygon_rings(case_id):
            if len(tokens) < 3:
                continue
            active = case_field == case_id
            for kind, index in tokens:
                if kind == "edge":
                    active = active & crossings[index]["mask"]
            shoelace = xp.zeros_like(values[0])
            for token, next_token in zip(tokens, tokens[1:] + tokens[:1], strict=True):
                x, y = _token_point(token, points=points, crossings=crossings)
                next_x, next_y = _token_point(
                    next_token, points=points, crossings=crossings
                )
                shoelace = shoelace + x * next_y - y * next_x
            local_area = local_area + xp.where(
                active,
                0.5 * shoelace,
                xp.zeros_like(shoelace),
            )
    return local_area


def _local_surface_lengths(xp, values, points):
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_field = _case_field(xp, values)
    local_length = xp.zeros_like(values[0])
    for case_id in range(16):
        edges = _crossing_edges(case_id)
        if len(edges) not in {2, 4}:
            continue
        active = case_field == case_id
        for edge in edges:
            active = active & crossings[edge]["mask"]
        length = _segment_length(xp, crossings[edges[0]], crossings[edges[1]])
        if len(edges) == 4:
            length = length + _segment_length(xp, crossings[edges[2]], crossings[edges[3]])
        local_length = local_length + xp.where(active, length, xp.zeros_like(length))
    return local_length


def _liquid_polygon_rings(case_id: int):
    if case_id == 10:
        return (
            (("corner", 1), ("edge", 1), ("edge", 0)),
            (("corner", 3), ("edge", 3), ("edge", 2)),
        )
    tokens = _liquid_polygon_tokens(case_id)
    if not tokens:
        return ()
    return (tokens,)


def _liquid_polygon_tokens(case_id: int):
    inside = tuple(bool(case_id & (1 << corner)) for corner in range(4))
    tokens = []
    for edge, (lo, hi) in enumerate(_EDGE_CORNERS):
        if inside[lo]:
            tokens.append(("corner", lo))
        if inside[lo] != inside[hi]:
            tokens.append(("edge", edge))
    return tuple(tokens)


def _crossing_edges(case_id: int) -> tuple[int, ...]:
    inside = tuple(bool(case_id & (1 << corner)) for corner in range(4))
    return tuple(
        edge
        for edge, (lo, hi) in enumerate(_EDGE_CORNERS)
        if inside[lo] != inside[hi]
    )


def _token_point(token, *, points, crossings):
    kind, index = token
    if kind == "corner":
        return points[index][0], points[index][1]
    crossing = crossings[index]
    return crossing["x"], crossing["y"]


def _segment_length(xp, left, right):
    return xp.sqrt((right["x"] - left["x"]) ** 2 + (right["y"] - left["y"]) ** 2)


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


def _scalar_float(xp, value) -> float:
    if hasattr(value, "get"):
        value = value.get()
    return float(value)


def _scalar_bool(xp, value) -> bool:
    if hasattr(value, "get"):
        value = value.get()
    return bool(value)
