"""Exact transport-adjoint helpers shared by variational force builders."""

from __future__ import annotations


def negative_face_divergence_adjoint(*, xp, fccd, nodal_covector, axis: int):
    """Return ``(-D_f)^T`` for ``FCCDSolver.face_divergence``."""
    covector = xp.moveaxis(xp.asarray(nodal_covector), axis, 0)
    n_faces = fccd.grid.N[axis]
    weights = fccd._weights[axis]
    if fccd._axis_periodic(axis):
        unique = xp.array(covector[:n_faces], copy=True)
        unique[0] = unique[0] + covector[n_faces]
        if weights["uniform"]:
            weighted = unique * weights["inv_H"]
        else:
            inv_width = fccd._broadcast_axis0(
                weights["inv_H_periodic_node"],
                unique.ndim,
            )
            weighted = unique * inv_width
        adjoint = xp.roll(weighted, -1, axis=0) - weighted
        return xp.moveaxis(adjoint, 0, axis)

    weighted = xp.zeros_like(covector)
    if weights["uniform"]:
        weighted[1:n_faces] = covector[1:n_faces] * weights["inv_H"]
    else:
        inv_width = fccd._broadcast_axis0(weights["inv_H_node"], covector.ndim)
        weighted[1:n_faces] = covector[1:n_faces] * inv_width
    adjoint = weighted[1:] - weighted[:-1]
    return xp.moveaxis(adjoint, 0, axis)
