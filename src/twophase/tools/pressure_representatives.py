"""Pressure representative reconstruction for plotting and diagnostics.

Symbol mapping
--------------
``ψ`` -> ``psi``
``a_f`` -> ``pressure_accel_faces``
``p_h`` -> returned Hodge pressure representative

A3 chain
--------
Paper equation : ``a_f = A_f(G_f p - B_f(j))`` in
``eq:affine_pressure_history_faces``.
Discretisation : recover a phase-wise scalar representative by projecting the
stored face cochain onto exact same-phase graph gradients, with one volume mean
gauge per phase.
Code : ``phase_hodge_pressure_representative`` solves the least-squares Hodge
problem for visualization only; it does not alter the momentum update.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse import linalg as sparse_linalg


def phase_hodge_pressure_representative(
    *,
    psi: np.ndarray,
    rho: np.ndarray,
    pressure: np.ndarray,
    pressure_accel_faces: list[np.ndarray],
    coords: list[np.ndarray],
    phase_threshold: float = 0.5,
) -> np.ndarray:
    """Return a phase-wise pressure representative from face cochains.

    The sharp-interface pressure is not single-valued on ``Γ``.  This helper
    reconstructs only the phase-wise scalar whose same-phase finite-volume
    gradients best match the stored affine face acceleration cochain.  Faces
    crossing the phase boundary are excluded; their jump lives in the affine
    cochain rather than in one nodal point value.
    """
    psi_arr = np.asarray(psi, dtype=float)
    rho_arr = np.asarray(rho, dtype=float)
    pressure_arr = np.asarray(pressure, dtype=float)
    if psi_arr.shape != pressure_arr.shape or rho_arr.shape != pressure_arr.shape:
        raise ValueError("psi, rho, and pressure must share the same node shape")
    if len(pressure_accel_faces) != psi_arr.ndim or len(coords) != psi_arr.ndim:
        raise ValueError("face cochains and coords must match psi dimensionality")

    phase_label = psi_arr >= float(phase_threshold)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    rhs: list[float] = []
    row_index = 0

    for axis, face_accel in enumerate(pressure_accel_faces):
        face_arr = np.asarray(face_accel, dtype=float)
        n_faces = psi_arr.shape[axis] - 1
        if face_arr.shape[axis] != n_faces:
            raise ValueError("face cochain shape is inconsistent with psi")

        for face_index in np.ndindex(face_arr.shape):
            lo_index = list(face_index)
            hi_index = list(face_index)
            hi_index[axis] += 1
            lo = tuple(lo_index)
            hi = tuple(hi_index)
            if phase_label[lo] != phase_label[hi]:
                continue
            rho_face_inverse = 2.0 / (rho_arr[lo] + rho_arr[hi])
            spacing = float(coords[axis][hi[axis]] - coords[axis][lo[axis]])
            if spacing <= 0.0:
                raise ValueError("coordinates must be strictly increasing")
            lo_col = np.ravel_multi_index(lo, psi_arr.shape)
            hi_col = np.ravel_multi_index(hi, psi_arr.shape)
            rows.extend([row_index, row_index])
            cols.extend([hi_col, lo_col])
            data.extend([1.0 / spacing, -1.0 / spacing])
            rhs.append(float(face_arr[face_index]) / rho_face_inverse)
            row_index += 1

    volume_weights = _node_volume_weights(coords, psi_arr.shape)
    for liquid_phase in (False, True):
        mask = phase_label == liquid_phase
        if not np.any(mask):
            continue
        weights = np.where(mask, volume_weights, 0.0)
        weight_sum = float(np.sum(weights))
        if weight_sum <= 0.0:
            continue
        phase_mean = float(np.sum(pressure_arr * weights) / weight_sum)
        scale = float(np.sqrt(np.count_nonzero(mask)))
        for flat_col, weight in enumerate(weights.ravel()):
            if weight == 0.0:
                continue
            rows.append(row_index)
            cols.append(flat_col)
            data.append(scale * float(weight) / weight_sum)
        rhs.append(scale * phase_mean)
        row_index += 1

    if row_index == 0:
        return pressure_arr.copy()

    matrix = sparse.coo_matrix(
        (data, (rows, cols)),
        shape=(row_index, pressure_arr.size),
    ).tocsr()
    solution = sparse_linalg.lsqr(matrix, np.asarray(rhs, dtype=float))[0]
    return solution.reshape(pressure_arr.shape)


def _node_volume_weights(coords: list[np.ndarray], shape: tuple[int, ...]) -> np.ndarray:
    weights = np.ones(shape, dtype=float)
    for axis, coord in enumerate(coords):
        coord_arr = np.asarray(coord, dtype=float)
        if coord_arr.size != shape[axis]:
            raise ValueError("coordinate length must match node count")
        widths = np.empty_like(coord_arr)
        if coord_arr.size == 1:
            widths[0] = 1.0
        else:
            face_widths = coord_arr[1:] - coord_arr[:-1]
            widths[0] = 0.5 * face_widths[0]
            widths[-1] = 0.5 * face_widths[-1]
            if coord_arr.size > 2:
                widths[1:-1] = 0.5 * (coord_arr[2:] - coord_arr[:-2])
        reshape = [1] * len(shape)
        reshape[axis] = coord_arr.size
        weights = weights * widths.reshape(reshape)
    return weights
