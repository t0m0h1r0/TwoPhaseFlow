"""Physical-space non-uniform FMM used by ridge-eikonal reinitialization."""

from __future__ import annotations

import heapq

import numpy as np


class NonUniformFMM:
    """Physical-space Fast Marching Method on non-uniform grids."""

    def __init__(self, grid):
        self._grid = grid
        self._hx = np.asarray(grid.h[0]).astype(np.float64)
        self._hy = np.asarray(grid.h[1]).astype(np.float64)
        cx = np.asarray(grid.coords[0]).astype(np.float64)
        cy = np.asarray(grid.coords[1]).astype(np.float64)
        self._hx_fwd = np.diff(cx)
        self._hy_fwd = np.diff(cy)

    def update_grid(self, grid) -> None:
        self._grid = grid
        self._hx = np.asarray(grid.h[0]).astype(np.float64)
        self._hy = np.asarray(grid.h[1]).astype(np.float64)
        cx = np.asarray(grid.coords[0]).astype(np.float64)
        cy = np.asarray(grid.coords[1]).astype(np.float64)
        self._hx_fwd = np.diff(cx)
        self._hy_fwd = np.diff(cy)

    def solve(self, phi_np: np.ndarray, extra_seeds=None) -> np.ndarray:
        phi_np = np.ascontiguousarray(phi_np, dtype=np.float64)
        sgn = np.sign(phi_np)
        sgn = np.where(np.abs(phi_np) < 1e-10, 1.0, sgn)
        Nx, Ny = phi_np.shape

        INF = 1e30
        dist = np.full((Nx, Ny), INF, dtype=np.float64)
        frozen = np.zeros((Nx, Ny), dtype=bool)
        heap: list = []
        push_count = [0]

        def _push(i, j, d):
            if 0 <= i < Nx and 0 <= j < Ny and not frozen[i, j] and d < dist[i, j]:
                dist[i, j] = d
                heapq.heappush(heap, (d, push_count[0], i, j))
                push_count[0] += 1

        hx_fwd = self._hx_fwd
        hy_fwd = self._hy_fwd
        p, p1 = phi_np[:-1, :], phi_np[1:, :]
        mask = (p * p1) < 0.0
        if mask.any():
            ii, jj = np.where(mask)
            denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
            frac = np.abs(p[ii, jj]) / np.where(denom > 0.0, denom, 1.0)
            seg = hx_fwd[ii]
            d0 = frac * seg
            d1 = (1.0 - frac) * seg
            for k in range(len(ii)):
                _push(int(ii[k]), int(jj[k]), float(d0[k]))
                _push(int(ii[k]) + 1, int(jj[k]), float(d1[k]))

        p, p1 = phi_np[:, :-1], phi_np[:, 1:]
        mask = (p * p1) < 0.0
        if mask.any():
            ii, jj = np.where(mask)
            denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
            frac = np.abs(p[ii, jj]) / np.where(denom > 0.0, denom, 1.0)
            seg = hy_fwd[jj]
            d0 = frac * seg
            d1 = (1.0 - frac) * seg
            for k in range(len(ii)):
                _push(int(ii[k]), int(jj[k]), float(d0[k]))
                _push(int(ii[k]), int(jj[k]) + 1, float(d1[k]))

        if extra_seeds is not None:
            for i, j, d in extra_seeds:
                _push(int(i), int(j), float(d))

        if not heap:
            return phi_np

        hx = self._hx
        hy = self._hy
        while heap:
            d, _, i, j = heapq.heappop(heap)
            if frozen[i, j]:
                continue
            frozen[i, j] = True

            for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if not (0 <= ni < Nx and 0 <= nj < Ny) or frozen[ni, nj]:
                    continue

                a_x = INF
                h_x_step = hx[ni]
                if ni > 0 and frozen[ni - 1, nj]:
                    step = float(hx_fwd[ni - 1])
                    if dist[ni - 1, nj] < a_x:
                        a_x = dist[ni - 1, nj]
                        h_x_step = step
                if ni < Nx - 1 and frozen[ni + 1, nj]:
                    step = float(hx_fwd[ni])
                    if dist[ni + 1, nj] < a_x:
                        a_x = dist[ni + 1, nj]
                        h_x_step = step

                a_y = INF
                h_y_step = hy[nj]
                if nj > 0 and frozen[ni, nj - 1]:
                    step = float(hy_fwd[nj - 1])
                    if dist[ni, nj - 1] < a_y:
                        a_y = dist[ni, nj - 1]
                        h_y_step = step
                if nj < Ny - 1 and frozen[ni, nj + 1]:
                    step = float(hy_fwd[nj])
                    if dist[ni, nj + 1] < a_y:
                        a_y = dist[ni, nj + 1]
                        h_y_step = step

                if a_x >= INF and a_y >= INF:
                    continue
                if a_x >= INF:
                    d_new = a_y + h_y_step
                elif a_y >= INF:
                    d_new = a_x + h_x_step
                else:
                    inv_hx2 = 1.0 / (h_x_step * h_x_step)
                    inv_hy2 = 1.0 / (h_y_step * h_y_step)
                    denom = inv_hx2 + inv_hy2
                    D = denom - (a_x - a_y) ** 2 * inv_hx2 * inv_hy2
                    if D < 0.0:
                        d_new = min(a_x + h_x_step, a_y + h_y_step)
                    else:
                        d_new = (a_x * inv_hx2 + a_y * inv_hy2 + np.sqrt(D)) / denom

                _push(int(ni), int(nj), float(d_new))

        return sgn * dist
