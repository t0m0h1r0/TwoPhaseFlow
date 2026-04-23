"""Distance-field helpers for Eikonal redistancing.

Symbol mapping
--------------
``phi_dev`` -> backend-native signed field ``φ``
``sgn``     -> sign field ``sgn(φ)``
``crossings`` -> zero-crossing coordinates in computational space
"""

from __future__ import annotations

import numpy as np


def xi_sdf_phi(xp, phi_dev):
    """Vectorized ξ-space signed-distance transform."""
    sgn = xp.sign(phi_dev)
    sgn = xp.where(sgn == 0, 1.0, sgn)
    Nx, Ny = phi_dev.shape

    crossing_parts = []

    px = phi_dev[:-1, :]
    px1 = phi_dev[1:, :]
    xi_mask = (px * px1) < 0.0
    if xp.any(xi_mask):
        ii, jj = xp.where(xi_mask)
        denom = xp.abs(px[ii, jj]) + xp.abs(px1[ii, jj])
        alpha = xp.abs(px[ii, jj]) / xp.where(denom > 0, denom, 1.0)
        crossing_parts.append(
            xp.stack(
                [
                    ii.astype(xp.float64) + alpha.astype(xp.float64),
                    jj.astype(xp.float64),
                ],
                axis=1,
            )
        )

    py = phi_dev[:, :-1]
    py1 = phi_dev[:, 1:]
    eta_mask = (py * py1) < 0.0
    if xp.any(eta_mask):
        ii, jj = xp.where(eta_mask)
        denom = xp.abs(py[ii, jj]) + xp.abs(py1[ii, jj])
        alpha = xp.abs(py[ii, jj]) / xp.where(denom > 0, denom, 1.0)
        crossing_parts.append(
            xp.stack(
                [
                    ii.astype(xp.float64),
                    jj.astype(xp.float64) + alpha.astype(xp.float64),
                ],
                axis=1,
            )
        )

    if not crossing_parts:
        return phi_dev

    crossings = xp.concatenate(crossing_parts, axis=0)
    I = xp.arange(Nx, dtype=xp.float64).reshape(-1, 1, 1)
    J = xp.arange(Ny, dtype=xp.float64).reshape(1, -1, 1)
    kx = crossings[:, 0].reshape(1, 1, -1)
    ky = crossings[:, 1].reshape(1, 1, -1)
    return sgn * xp.min(xp.sqrt((I - kx) ** 2 + (J - ky) ** 2), axis=2)


def xi_sdf_phi_cpu_legacy(xp, phi_dev):
    """DO NOT DELETE — CPU sequential baseline kept for regression parity."""
    phi_np = phi_dev.get() if hasattr(phi_dev, "get") else np.asarray(phi_dev)
    sgn = np.sign(phi_np)
    Nx, Ny = phi_np.shape

    crossing_list = []
    px = phi_np[:-1, :]
    px1 = phi_np[1:, :]
    xi_mask = (px * px1) < 0.0
    if xi_mask.any():
        ii, jj = np.where(xi_mask)
        denom = np.abs(px[ii, jj]) + np.abs(px1[ii, jj])
        alpha = np.abs(px[ii, jj]) / np.where(denom > 0, denom, 1.0)
        for index in range(len(ii)):
            crossing_list.append((float(ii[index]) + float(alpha[index]), float(jj[index])))

    py = phi_np[:, :-1]
    py1 = phi_np[:, 1:]
    eta_mask = (py * py1) < 0.0
    if eta_mask.any():
        ii, jj = np.where(eta_mask)
        denom = np.abs(py[ii, jj]) + np.abs(py1[ii, jj])
        alpha = np.abs(py[ii, jj]) / np.where(denom > 0, denom, 1.0)
        for index in range(len(ii)):
            crossing_list.append((float(ii[index]), float(jj[index]) + float(alpha[index])))

    if not crossing_list:
        return phi_dev
    crossings = np.array(crossing_list, dtype=np.float64)
    I = np.arange(Nx, dtype=np.float64).reshape(-1, 1, 1)
    J = np.arange(Ny, dtype=np.float64).reshape(1, -1, 1)
    kx = crossings[:, 0].reshape(1, 1, -1)
    ky = crossings[:, 1].reshape(1, 1, -1)
    phi_xi = sgn * np.min(np.sqrt((I - kx) ** 2 + (J - ky) ** 2), axis=2)
    return xp.asarray(phi_xi)


def fmm_phi(xp, phi_dev):
    """Fast Marching Method for a signed-distance field."""
    import heapq

    phi_np = phi_dev.get() if hasattr(phi_dev, "get") else np.asarray(phi_dev)
    sgn = np.sign(phi_np)
    sgn = np.where(np.abs(phi_np) < 1e-10, 1.0, sgn)
    Nx, Ny = phi_np.shape

    INF = 1e30
    dist = np.full((Nx, Ny), INF)
    frozen = np.zeros((Nx, Ny), dtype=bool)
    heap = []

    def push(i, j, d):
        if 0 <= i < Nx and 0 <= j < Ny and not frozen[i, j] and d < dist[i, j]:
            dist[i, j] = d
            heapq.heappush(heap, (d, i, j))

    for axis in range(2):
        p, p1 = (phi_np[:-1, :], phi_np[1:, :]) if axis == 0 else (phi_np[:, :-1], phi_np[:, 1:])
        mask = (p * p1) < 0.0
        if mask.any():
            ii, jj = np.where(mask)
            denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
            alpha = np.abs(p[ii, jj]) / np.where(denom > 0, denom, 1.0)
            for index in range(len(ii)):
                a = float(alpha[index])
                i0, j0 = int(ii[index]), int(jj[index])
                if axis == 0:
                    push(i0, j0, a)
                    push(i0 + 1, j0, 1.0 - a)
                else:
                    push(i0, j0, a)
                    push(i0, j0 + 1, 1.0 - a)

    if not heap:
        return phi_dev

    while heap:
        d, i, j = heapq.heappop(heap)
        if frozen[i, j]:
            continue
        frozen[i, j] = True

        for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
            if not (0 <= ni < Nx and 0 <= nj < Ny) or frozen[ni, nj]:
                continue

            ax = INF
            if ni > 0 and frozen[ni - 1, nj]:
                ax = min(ax, dist[ni - 1, nj])
            if ni < Nx - 1 and frozen[ni + 1, nj]:
                ax = min(ax, dist[ni + 1, nj])

            ay = INF
            if nj > 0 and frozen[ni, nj - 1]:
                ay = min(ay, dist[ni, nj - 1])
            if nj < Ny - 1 and frozen[ni, nj + 1]:
                ay = min(ay, dist[ni, nj + 1])

            if ax == INF and ay == INF:
                continue
            if ax == INF:
                d_new = ay + 1.0
            elif ay == INF:
                d_new = ax + 1.0
            else:
                diff = ax - ay
                d_new = min(ax, ay) + 1.0 if diff * diff >= 1.0 else 0.5 * (ax + ay + np.sqrt(2.0 - diff * diff))

            push(ni, nj, d_new)

    return xp.asarray(sgn * dist)
