"""Physical-space non-uniform FMM used by ridge-eikonal reinitialization."""

from __future__ import annotations

import heapq
from functools import lru_cache

import numpy as np


_GPU_FMM_KERNEL = r"""
extern "C" {
__device__ int fmm_less(double d_a, long long o_a, double d_b, long long o_b) {
    return (d_a < d_b) || ((d_a == d_b) && (o_a < o_b));
}

__device__ void fmm_heap_swap(
    double* heap_d,
    int* heap_idx,
    long long* heap_order,
    int a,
    int b
) {
    double td = heap_d[a];
    int ti = heap_idx[a];
    long long to = heap_order[a];
    heap_d[a] = heap_d[b];
    heap_idx[a] = heap_idx[b];
    heap_order[a] = heap_order[b];
    heap_d[b] = td;
    heap_idx[b] = ti;
    heap_order[b] = to;
}

__device__ void fmm_heap_push(
    double d,
    int idx,
    long long order,
    double* heap_d,
    int* heap_idx,
    long long* heap_order,
    int* heap_size,
    int heap_cap,
    int* status
) {
    if (*heap_size >= heap_cap) {
        status[0] = 1;
        return;
    }
    int pos = *heap_size;
    *heap_size = pos + 1;
    heap_d[pos] = d;
    heap_idx[pos] = idx;
    heap_order[pos] = order;
    while (pos > 0) {
        int parent = (pos - 1) >> 1;
        if (!fmm_less(heap_d[pos], heap_order[pos], heap_d[parent], heap_order[parent])) {
            break;
        }
        fmm_heap_swap(heap_d, heap_idx, heap_order, pos, parent);
        pos = parent;
    }
    if (*heap_size > status[1]) {
        status[1] = *heap_size;
    }
}

__device__ int fmm_heap_pop(
    double* out_d,
    int* out_idx,
    double* heap_d,
    int* heap_idx,
    long long* heap_order,
    int* heap_size
) {
    if (*heap_size <= 0) {
        return 0;
    }
    *out_d = heap_d[0];
    *out_idx = heap_idx[0];
    *heap_size = *heap_size - 1;
    if (*heap_size <= 0) {
        return 1;
    }
    heap_d[0] = heap_d[*heap_size];
    heap_idx[0] = heap_idx[*heap_size];
    heap_order[0] = heap_order[*heap_size];
    int pos = 0;
    while (true) {
        int left = 2 * pos + 1;
        int right = left + 1;
        int smallest = pos;
        if (
            left < *heap_size
            && fmm_less(heap_d[left], heap_order[left], heap_d[smallest], heap_order[smallest])
        ) {
            smallest = left;
        }
        if (
            right < *heap_size
            && fmm_less(heap_d[right], heap_order[right], heap_d[smallest], heap_order[smallest])
        ) {
            smallest = right;
        }
        if (smallest == pos) {
            break;
        }
        fmm_heap_swap(heap_d, heap_idx, heap_order, pos, smallest);
        pos = smallest;
    }
    return 1;
}

__device__ void fmm_push_if_better(
    int idx,
    double d,
    double* dist,
    unsigned char* frozen,
    double* heap_d,
    int* heap_idx,
    long long* heap_order,
    int* heap_size,
    int heap_cap,
    long long* push_order,
    int* status
) {
    if (!frozen[idx] && d < dist[idx]) {
        dist[idx] = d;
        fmm_heap_push(
            d,
            idx,
            *push_order,
            heap_d,
            heap_idx,
            heap_order,
            heap_size,
            heap_cap,
            status
        );
        *push_order = *push_order + 1;
    }
}

__global__ void nonuniform_fmm_exact_kernel(
    const double* phi,
    const unsigned char* ridge_mask,
    const double* hx_fwd,
    const double* hy_fwd,
    int nx,
    int ny,
    double h_min,
    int use_ridge_mask,
    const int* extra_i,
    const int* extra_j,
    const double* extra_d,
    int n_extra,
    double* dist,
    unsigned char* frozen,
    double* heap_d,
    int* heap_idx,
    long long* heap_order,
    int heap_cap,
    int* status
) {
    if (blockIdx.x != 0 || threadIdx.x != 0) {
        return;
    }

    const double INF = 1.0e30;
    const int n_total = nx * ny;
    int heap_size = 0;
    long long push_order = 0;
    status[0] = 0;
    status[1] = 0;

    for (int idx = 0; idx < n_total; ++idx) {
        dist[idx] = INF;
        frozen[idx] = 0;
    }

    for (int i = 0; i < nx - 1; ++i) {
        const double seg = hx_fwd[i];
        for (int j = 0; j < ny; ++j) {
            const int idx0 = i * ny + j;
            const int idx1 = (i + 1) * ny + j;
            const double p0 = phi[idx0];
            const double p1 = phi[idx1];
            if (p0 * p1 < 0.0) {
                const double denom = fabs(p0) + fabs(p1);
                const double frac = fabs(p0) / (denom > 0.0 ? denom : 1.0);
                fmm_push_if_better(
                    idx0,
                    frac * seg,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
                fmm_push_if_better(
                    idx1,
                    (1.0 - frac) * seg,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
            }
        }
    }

    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny - 1; ++j) {
            const int idx0 = i * ny + j;
            const int idx1 = i * ny + (j + 1);
            const double p0 = phi[idx0];
            const double p1 = phi[idx1];
            if (p0 * p1 < 0.0) {
                const double denom = fabs(p0) + fabs(p1);
                const double frac = fabs(p0) / (denom > 0.0 ? denom : 1.0);
                const double seg = hy_fwd[j];
                fmm_push_if_better(
                    idx0,
                    frac * seg,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
                fmm_push_if_better(
                    idx1,
                    (1.0 - frac) * seg,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
            }
        }
    }

    const double zero_tol = fmax(1.0e-12, 1.0e-10 * h_min);
    for (int i = 0; i < nx; ++i) {
        for (int j = 0; j < ny; ++j) {
            const int idx = i * ny + j;
            if (fabs(phi[idx]) <= zero_tol) {
                fmm_push_if_better(
                    idx,
                    0.0,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
            }
        }
    }

    if (use_ridge_mask) {
        for (int idx = 0; idx < n_total; ++idx) {
            if (ridge_mask[idx] && fabs(phi[idx]) < 0.5 * h_min) {
                fmm_push_if_better(
                    idx,
                    0.0,
                    dist,
                    frozen,
                    heap_d,
                    heap_idx,
                    heap_order,
                    &heap_size,
                    heap_cap,
                    &push_order,
                    status
                );
            }
        }
    }

    for (int k = 0; k < n_extra; ++k) {
        const int i = extra_i[k];
        const int j = extra_j[k];
        if (0 <= i && i < nx && 0 <= j && j < ny) {
            fmm_push_if_better(
                i * ny + j,
                extra_d[k],
                dist,
                frozen,
                heap_d,
                heap_idx,
                heap_order,
                &heap_size,
                heap_cap,
                &push_order,
                status
            );
        }
    }

    if (status[0] != 0) {
        return;
    }
    if (heap_size == 0) {
        for (int idx = 0; idx < n_total; ++idx) {
            dist[idx] = phi[idx];
        }
        return;
    }

    while (heap_size > 0) {
        double d = 0.0;
        int idx = 0;
        if (!fmm_heap_pop(&d, &idx, heap_d, heap_idx, heap_order, &heap_size)) {
            break;
        }
        if (frozen[idx]) {
            continue;
        }
        frozen[idx] = 1;
        const int i = idx / ny;
        const int j = idx - i * ny;

        for (int direction = 0; direction < 4; ++direction) {
            int ni = i;
            int nj = j;
            if (direction == 0) {
                ni = i - 1;
            } else if (direction == 1) {
                ni = i + 1;
            } else if (direction == 2) {
                nj = j - 1;
            } else {
                nj = j + 1;
            }
            if (!(0 <= ni && ni < nx && 0 <= nj && nj < ny)) {
                continue;
            }
            const int nidx = ni * ny + nj;
            if (frozen[nidx]) {
                continue;
            }

            double a_x = INF;
            double h_x_step = 1.0;
            if (ni > 0) {
                const int left = (ni - 1) * ny + nj;
                if (frozen[left] && dist[left] < a_x) {
                    a_x = dist[left];
                    h_x_step = hx_fwd[ni - 1];
                }
            }
            if (ni < nx - 1) {
                const int right = (ni + 1) * ny + nj;
                if (frozen[right] && dist[right] < a_x) {
                    a_x = dist[right];
                    h_x_step = hx_fwd[ni];
                }
            }

            double a_y = INF;
            double h_y_step = 1.0;
            if (nj > 0) {
                const int down = ni * ny + (nj - 1);
                if (frozen[down] && dist[down] < a_y) {
                    a_y = dist[down];
                    h_y_step = hy_fwd[nj - 1];
                }
            }
            if (nj < ny - 1) {
                const int up = ni * ny + (nj + 1);
                if (frozen[up] && dist[up] < a_y) {
                    a_y = dist[up];
                    h_y_step = hy_fwd[nj];
                }
            }

            double d_new = INF;
            if (a_x >= INF && a_y >= INF) {
                continue;
            } else if (a_x >= INF) {
                d_new = a_y + h_y_step;
            } else if (a_y >= INF) {
                d_new = a_x + h_x_step;
            } else {
                const double inv_hx2 = 1.0 / (h_x_step * h_x_step);
                const double inv_hy2 = 1.0 / (h_y_step * h_y_step);
                const double denom = inv_hx2 + inv_hy2;
                const double discr = denom - (a_x - a_y) * (a_x - a_y) * inv_hx2 * inv_hy2;
                if (discr < 0.0) {
                    const double dx_candidate = a_x + h_x_step;
                    const double dy_candidate = a_y + h_y_step;
                    d_new = dx_candidate < dy_candidate ? dx_candidate : dy_candidate;
                } else {
                    d_new = (
                        a_x * inv_hx2
                        + a_y * inv_hy2
                        + sqrt(discr)
                    ) / denom;
                }
            }
            fmm_push_if_better(
                nidx,
                d_new,
                dist,
                frozen,
                heap_d,
                heap_idx,
                heap_order,
                &heap_size,
                heap_cap,
                &push_order,
                status
            );
            if (status[0] != 0) {
                return;
            }
        }
    }

    for (int idx = 0; idx < n_total; ++idx) {
        const double p = phi[idx];
        const double sgn = fabs(p) < 1.0e-10 ? 1.0 : (p < 0.0 ? -1.0 : 1.0);
        dist[idx] = sgn * dist[idx];
    }
}
}
"""


@lru_cache(maxsize=1)
def _get_gpu_fmm_kernel(raw_kernel_factory):
    return raw_kernel_factory(_GPU_FMM_KERNEL, "nonuniform_fmm_exact_kernel")


class NonUniformFMM:
    """Physical-space Fast Marching Method on non-uniform grids."""

    def __init__(self, grid, backend=None):
        self._backend = backend
        self._xp = backend.xp if backend is not None else None
        self._grid = grid
        self._refresh_metrics(grid)

    def _refresh_metrics(self, grid) -> None:
        self._hx = np.asarray(grid.h[0]).astype(np.float64)
        self._hy = np.asarray(grid.h[1]).astype(np.float64)
        cx = np.asarray(grid.coords[0]).astype(np.float64)
        cy = np.asarray(grid.coords[1]).astype(np.float64)
        self._hx_fwd = np.diff(cx)
        self._hy_fwd = np.diff(cy)
        if self._backend is not None and self._backend.is_gpu():
            xp = self._xp
            self._hx_fwd_dev = xp.asarray(self._hx_fwd, dtype=xp.float64)
            self._hy_fwd_dev = xp.asarray(self._hy_fwd, dtype=xp.float64)

    def update_grid(self, grid) -> None:
        self._grid = grid
        self._refresh_metrics(grid)

    def solve(self, phi_np: np.ndarray, extra_seeds=None, ridge_mask=None, h_min=None) -> np.ndarray:
        if self._backend is not None and self._backend.is_gpu() and hasattr(phi_np, "device"):
            return self._solve_gpu(phi_np, extra_seeds=extra_seeds, ridge_mask=ridge_mask, h_min=h_min)

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
        if h_min is None:
            h_min = float(min(np.min(hx_fwd), np.min(hy_fwd)))
        zero_tol = max(1.0e-12, 1.0e-10 * float(h_min))
        zero_ii, zero_jj = np.where(np.abs(phi_np) <= zero_tol)
        for seed_idx in range(len(zero_ii)):
            _push(int(zero_ii[seed_idx]), int(zero_jj[seed_idx]), 0.0)

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

    def _solve_gpu(self, phi, *, extra_seeds=None, ridge_mask=None, h_min=None):
        """Solve the same accepted-set FMM update with all state on the GPU.

        This is not a pseudo-time or fixed-sweep approximation.  The CUDA
        kernel preserves the CPU FMM's global min-heap ordering and upwind
        accepted-neighbour quadratic update; the sequential dependency is
        executed inside a device kernel to avoid materialising the signed
        distance solve on the host.
        """
        xp = self._xp
        phi_dev = xp.ascontiguousarray(xp.asarray(phi), dtype=xp.float64)
        nx, ny = phi_dev.shape
        n_total = int(nx * ny)
        heap_cap = max(1024, 16 * n_total + 16)

        if ridge_mask is None:
            ridge_dev = xp.zeros(phi_dev.shape, dtype=xp.uint8)
            use_ridge = 0
        else:
            ridge_dev = xp.ascontiguousarray(xp.asarray(ridge_mask, dtype=xp.uint8))
            use_ridge = 1

        if extra_seeds:
            extra_i = xp.asarray([int(seed[0]) for seed in extra_seeds], dtype=xp.int32)
            extra_j = xp.asarray([int(seed[1]) for seed in extra_seeds], dtype=xp.int32)
            extra_d = xp.asarray([float(seed[2]) for seed in extra_seeds], dtype=xp.float64)
            n_extra = len(extra_seeds)
        else:
            extra_i = xp.zeros(1, dtype=xp.int32)
            extra_j = xp.zeros(1, dtype=xp.int32)
            extra_d = xp.zeros(1, dtype=xp.float64)
            n_extra = 0

        dist = xp.empty_like(phi_dev)
        frozen = xp.empty(n_total, dtype=xp.uint8)
        heap_d = xp.empty(heap_cap, dtype=xp.float64)
        heap_idx = xp.empty(heap_cap, dtype=xp.int32)
        heap_order = xp.empty(heap_cap, dtype=xp.int64)
        status = xp.zeros(2, dtype=xp.int32)

        kernel = _get_gpu_fmm_kernel(xp.RawKernel)
        kernel(
            (1,),
            (1,),
            (
                phi_dev,
                ridge_dev,
                self._hx_fwd_dev,
                self._hy_fwd_dev,
                np.int32(nx),
                np.int32(ny),
                np.float64(0.0 if h_min is None else h_min),
                np.int32(use_ridge),
                extra_i,
                extra_j,
                extra_d,
                np.int32(n_extra),
                dist,
                frozen,
                heap_d,
                heap_idx,
                heap_order,
                np.int32(heap_cap),
                status,
            ),
        )
        status_host = self._backend.to_host(status)
        if int(status_host[0]) != 0:
            raise RuntimeError(
                "GPU NonUniformFMM heap capacity exceeded "
                f"(cap={heap_cap}, peak={int(status_host[1])})."
            )
        return dist
