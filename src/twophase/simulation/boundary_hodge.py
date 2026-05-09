"""Boundary-constrained face Hodge helpers.

A3 mapping:
  Equation: project face velocity ``f`` to the wall trace constraint
  ``C_w f = 0`` in the transported face-mass metric.
  Discretization: ``C_w`` is the boundary trace of the same face-to-node
  reconstruction used by the FCCD/FVM divergence corrector; ``C_w^T`` is its
  exact array adjoint.  The Schur operator
  ``C_w M_f^{-1} C_w^T`` is applied matrix-free.
  Code: ``project_wall_trace`` solves the wall Schur system by CG using only
  backend array operations, so the GPU path never assembles a dense matrix.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..core.boundary import boundary_axes, is_all_periodic, is_periodic_axis
from .face_projection import axis_slice, reconstruct_nodes_from_faces


@dataclass(frozen=True)
class BoundaryHodgeProjection:
    """Result of a metric wall-trace projection on face components."""

    face_components: list
    diagnostics: dict[str, float]


def _to_float(xp, value) -> float:
    arr = xp.asarray(value)
    getter = getattr(arr, "get", None)
    if callable(getter):
        arr = getter()
    return float(arr)


def _linf(xp, arr) -> float:
    if getattr(arr, "size", 0) == 0:
        return 0.0
    return _to_float(xp, xp.max(xp.abs(arr)))


def _dot_float(xp, left, right) -> float:
    if getattr(left, "size", 0) == 0:
        return 0.0
    return _to_float(xp, xp.vdot(left, right).real)


def _wall_node_mask(xp, grid, bc_type: str):
    """Return unique nodal wall-trace DOFs for the boundary topology."""
    mask = xp.zeros(grid.shape, dtype=bool)
    axes = boundary_axes(bc_type, grid.ndim)
    for axis, kind in enumerate(axes):
        if kind != "wall":
            continue
        n_cells = grid.N[axis]
        mask[axis_slice(grid.ndim, axis, 0, 1)] = True
        mask[axis_slice(grid.ndim, axis, n_cells, n_cells + 1)] = True
    for axis, kind in enumerate(axes):
        if kind == "periodic":
            n_cells = grid.N[axis]
            mask[axis_slice(grid.ndim, axis, n_cells, n_cells + 1)] = False
    return mask


def _wall_trace_count(xp, mask) -> int:
    return int(_to_float(xp, xp.sum(mask)))


def wall_trace_from_faces(xp, grid, face_components: list, bc_type: str):
    """Evaluate ``C_w f`` from face components using production reconstruction."""
    if is_all_periodic(bc_type, grid.ndim):
        return xp.zeros((0,), dtype=face_components[0].dtype)
    nodal_components = reconstruct_nodes_from_faces(
        xp,
        grid,
        face_components,
        bc_type=bc_type,
    )
    mask = _wall_node_mask(xp, grid, bc_type)
    traces = [component[mask].reshape(-1) for component in nodal_components]
    return xp.concatenate(traces) if traces else xp.zeros((0,), dtype=face_components[0].dtype)


def _reconstruct_adjoint_component(xp, grid, nodal_adjoint, axis: int, bc_type: str):
    """Apply the adjoint of ``reconstruct_nodes_from_faces`` for one component."""
    ndim = grid.ndim
    n_cells = grid.N[axis]
    face_shape = list(grid.shape)
    face_shape[axis] = n_cells
    face_adjoint = xp.zeros(tuple(face_shape), dtype=nodal_adjoint.dtype)
    if is_periodic_axis(bc_type, axis, ndim):
        source = nodal_adjoint[axis_slice(ndim, axis, 0, n_cells)].copy()
        source[axis_slice(ndim, axis, 0, 1)] = (
            source[axis_slice(ndim, axis, 0, 1)]
            + nodal_adjoint[axis_slice(ndim, axis, n_cells, n_cells + 1)]
        )
        face_adjoint = 0.5 * source + 0.5 * xp.roll(source, shift=-1, axis=axis)
        return face_adjoint

    face_adjoint[axis_slice(ndim, axis, 0, 1)] = (
        face_adjoint[axis_slice(ndim, axis, 0, 1)]
        + nodal_adjoint[axis_slice(ndim, axis, 0, 1)]
    )
    face_adjoint[axis_slice(ndim, axis, n_cells - 1, n_cells)] = (
        face_adjoint[axis_slice(ndim, axis, n_cells - 1, n_cells)]
        + nodal_adjoint[axis_slice(ndim, axis, n_cells, n_cells + 1)]
    )
    if n_cells > 1:
        interior = nodal_adjoint[axis_slice(ndim, axis, 1, n_cells)]
        face_adjoint[axis_slice(ndim, axis, 0, n_cells - 1)] = (
            face_adjoint[axis_slice(ndim, axis, 0, n_cells - 1)] + 0.5 * interior
        )
        face_adjoint[axis_slice(ndim, axis, 1, n_cells)] = (
            face_adjoint[axis_slice(ndim, axis, 1, n_cells)] + 0.5 * interior
        )
    return face_adjoint


def wall_trace_adjoint(xp, grid, trace_covector, bc_type: str, dtype=None) -> list:
    """Apply ``C_w^T`` to a flattened wall-trace covector."""
    trace_covector = xp.asarray(trace_covector, dtype=dtype)
    ndim = grid.ndim
    mask = _wall_node_mask(xp, grid, bc_type)
    count = _wall_trace_count(xp, mask)
    expected = ndim * count
    if int(trace_covector.size) != expected:
        raise ValueError(
            f"wall trace covector size {trace_covector.size} != expected {expected}"
        )
    face_components = []
    for axis in range(ndim):
        nodal = xp.zeros(grid.shape, dtype=trace_covector.dtype)
        if count:
            start = axis * count
            nodal[mask] = trace_covector[start : start + count]
        face_components.append(
            _reconstruct_adjoint_component(xp, grid, nodal, axis, bc_type)
        )
    return face_components


def _face_density_components(xp, fccd, rho, grid) -> list:
    rho_nodal = xp.asarray(rho)
    if fccd is not None and hasattr(fccd, "face_value"):
        return [fccd.face_value(rho_nodal, axis=axis) for axis in range(grid.ndim)]
    faces = []
    for axis in range(grid.ndim):
        n_cells = grid.N[axis]
        lo = rho_nodal[axis_slice(grid.ndim, axis, 0, n_cells)]
        hi = rho_nodal[axis_slice(grid.ndim, axis, 1, n_cells + 1)]
        faces.append(0.5 * (lo + hi))
    return faces


def _apply_inverse_face_mass(xp, covectors: list, face_density_components: list) -> list:
    corrections = []
    for covector, density in zip(covectors, face_density_components):
        density_min = _to_float(xp, xp.min(density))
        if density_min <= 0.0:
            raise ValueError(
                "boundary Hodge transported_face_mass requires positive face density, "
                f"got min={density_min:.6e}"
            )
        corrections.append(covector / density)
    return corrections


def _cg_solve(xp, apply_operator, rhs, *, tolerance: float, max_iterations: int):
    x = xp.zeros_like(rhs)
    r = rhs - apply_operator(x)
    p = r.copy()
    rhs_norm = max(_to_float(xp, xp.linalg.norm(rhs)), 1.0)
    rs_old = _dot_float(xp, r, r)
    residual = rs_old ** 0.5
    if residual <= tolerance * rhs_norm:
        return x, 0, residual, True
    converged = False
    iterations = 0
    for iterations in range(1, max_iterations + 1):
        Ap = apply_operator(p)
        denom = _dot_float(xp, p, Ap)
        if denom <= 0.0:
            break
        alpha = rs_old / denom
        x = x + alpha * p
        r = r - alpha * Ap
        rs_new = _dot_float(xp, r, r)
        residual = rs_new ** 0.5
        if residual <= tolerance * rhs_norm:
            converged = True
            break
        beta = rs_new / rs_old if rs_old > 0.0 else 0.0
        p = r + beta * p
        rs_old = rs_new
    return x, iterations, residual, converged


def project_wall_trace(
    *,
    xp,
    grid,
    fccd,
    face_components: list,
    rho,
    bc_type: str,
    tolerance: float = 1.0e-10,
    max_iterations: int = 80,
) -> BoundaryHodgeProjection:
    """Project face velocity onto the no-slip wall trace in face-mass metric."""
    if is_all_periodic(bc_type, grid.ndim):
        return BoundaryHodgeProjection(
            face_components=face_components,
            diagnostics={
                "boundary_hodge_active": 0.0,
                "boundary_hodge_wall_initial_linf": 0.0,
                "boundary_hodge_wall_linf": 0.0,
                "boundary_hodge_cg_iterations": 0.0,
                "boundary_hodge_cg_residual": 0.0,
                "boundary_hodge_cg_converged": 1.0,
                "boundary_hodge_correction_linf": 0.0,
            },
        )
    trace = wall_trace_from_faces(xp, grid, face_components, bc_type)
    trace_linf = _linf(xp, trace)
    if trace.size == 0 or trace_linf <= tolerance:
        return BoundaryHodgeProjection(
            face_components=face_components,
            diagnostics={
                "boundary_hodge_active": 1.0,
                "boundary_hodge_wall_initial_linf": trace_linf,
                "boundary_hodge_wall_linf": trace_linf,
                "boundary_hodge_cg_iterations": 0.0,
                "boundary_hodge_cg_residual": 0.0,
                "boundary_hodge_cg_converged": 1.0,
                "boundary_hodge_correction_linf": 0.0,
            },
        )
    face_density_components = _face_density_components(xp, fccd, rho, grid)

    def schur(trace_covector):
        face_covectors = wall_trace_adjoint(
            xp,
            grid,
            trace_covector,
            bc_type,
            dtype=trace.dtype,
        )
        correction = _apply_inverse_face_mass(xp, face_covectors, face_density_components)
        return wall_trace_from_faces(xp, grid, correction, bc_type)

    multiplier, iterations, residual, converged = _cg_solve(
        xp,
        schur,
        trace,
        tolerance=float(tolerance),
        max_iterations=int(max_iterations),
    )
    face_covectors = wall_trace_adjoint(
        xp,
        grid,
        multiplier,
        bc_type,
        dtype=trace.dtype,
    )
    correction = _apply_inverse_face_mass(xp, face_covectors, face_density_components)
    corrected = [
        face_component - corr for face_component, corr in zip(face_components, correction)
    ]
    final_trace = wall_trace_from_faces(xp, grid, corrected, bc_type)
    final_trace_linf = _linf(xp, final_trace)
    correction_linf = max((_linf(xp, corr) for corr in correction), default=0.0)
    constraint_converged = converged or final_trace_linf <= 10.0 * float(tolerance)
    diagnostics = {
        "boundary_hodge_active": 1.0,
        "boundary_hodge_wall_initial_linf": trace_linf,
        "boundary_hodge_wall_linf": final_trace_linf,
        "boundary_hodge_cg_iterations": float(iterations),
        "boundary_hodge_cg_residual": float(residual),
        "boundary_hodge_cg_converged": 1.0 if constraint_converged else 0.0,
        "boundary_hodge_correction_linf": correction_linf,
    }
    return BoundaryHodgeProjection(face_components=corrected, diagnostics=diagnostics)
