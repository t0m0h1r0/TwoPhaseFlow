"""Helper utilities for `PPESolverFVMMatrixFree`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class FVMMatrixFreeMetrics:
    h_min: float
    d_face: list
    dv_node: list


@dataclass(frozen=True)
class FVMMatrixFreePreconditionerState:
    line_coeffs: list | None
    diag_inv: object | None


def build_fvm_grid_metrics(*, xp, grid, ndim: int) -> FVMMatrixFreeMetrics:
    h_min = min(
        float(np.min(np.diff(np.asarray(coord)))) for coord in grid.coords
    )
    d_face = []
    dv_node = []
    for axis in range(ndim):
        coords = np.asarray(grid.coords[axis], dtype=np.float64)
        d_axis = coords[1:] - coords[:-1]
        dv_axis = np.empty_like(coords)
        dv_axis[0] = d_axis[0] / 2.0
        dv_axis[-1] = d_axis[-1] / 2.0
        dv_axis[1:-1] = (coords[2:] - coords[:-2]) / 2.0

        face_shape = [1] * ndim
        node_shape = [1] * ndim
        face_shape[axis] = d_axis.size
        node_shape[axis] = dv_axis.size
        d_face.append(xp.asarray(d_axis.reshape(face_shape)))
        dv_node.append(xp.asarray(dv_axis.reshape(node_shape)))
    return FVMMatrixFreeMetrics(h_min=h_min, d_face=d_face, dv_node=dv_node)


def build_fvm_line_coeffs(
    *,
    xp,
    grid,
    ndim: int,
    d_face: list,
    dv_node: list,
    rho,
    axis: int,
):
    n_axis = grid.N[axis]

    lower = xp.zeros_like(rho)
    main = xp.zeros_like(rho)
    upper = xp.zeros_like(rho)

    rho_lo = rho[_sl(axis, 0, n_axis, ndim)]
    rho_hi = rho[_sl(axis, 1, n_axis + 1, ndim)]
    coeff_face = 2.0 / (rho_lo + rho_hi) / d_face[axis]

    upper[_sl(axis, 0, n_axis, ndim)] = (
        coeff_face / dv_node[axis][_sl(axis, 0, n_axis, ndim)]
    )
    lower[_sl(axis, 1, n_axis + 1, ndim)] = (
        coeff_face / dv_node[axis][_sl(axis, 1, n_axis + 1, ndim)]
    )
    main[...] = -(lower + upper)
    return lower, main, upper


def build_fvm_preconditioner_state(
    *,
    xp,
    operator_coeffs,
    preconditioner: str,
    c_tau: float,
    rho,
    h_min: float,
    pin_dof: int,
) -> FVMMatrixFreePreconditionerState:
    if preconditioner == "line_pcr":
        shift = 2.0 / (c_tau * rho * (h_min ** 2))
        return FVMMatrixFreePreconditionerState(
            line_coeffs=[
                (-lower, shift - main, -upper)
                for lower, main, upper in operator_coeffs
            ],
            diag_inv=None,
        )
    if preconditioner == "jacobi":
        diag = xp.zeros_like(rho)
        for _lower, main, _upper in operator_coeffs:
            diag += main
        diag.ravel()[pin_dof] = 1.0
        return FVMMatrixFreePreconditionerState(
            line_coeffs=None,
            diag_inv=1.0 / xp.where(xp.abs(diag) > 1e-30, diag, 1.0),
        )
    return FVMMatrixFreePreconditionerState(line_coeffs=None, diag_inv=None)


def _sl(axis: int, start: int, stop: int, ndim: int):
    slices = [slice(None)] * ndim
    slices[axis] = slice(start, stop)
    return tuple(slices)
