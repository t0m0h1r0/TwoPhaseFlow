"""Active-row P1 geometry kernels for AO-Fast.

A3 chain:
  Equation: SP-AO defines active hard-volume rows
  ``Q_h(phi)_C=q_target_C`` on compact support ``A_q``.
  Discretization: each active row evaluates the same P1 marching-squares
  cut-cell volume, interface length, and local derivatives as the dense oracle,
  but only for explicitly supplied cell ids.
  Code: this module is backend-native active-row geometry.  It does not discover
  support from a full-grid mask and it is not a dense runtime fallback.

Symbol mapping
--------------
``A_q`` -> ``cell_ids_A``
``Q_h(phi)_A`` -> ``q_A``
``S_h(phi)_A`` -> ``s_A``
``J_q`` -> ``jq_local_A``
``dS_h`` -> ``ds_local_A``
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


_EDGE_CORNERS = ((0, 1), (1, 2), (2, 3), (3, 0))
_ACTIVE_GEOMETRY_RAW_KERNELS = {}


@dataclass(frozen=True)
class P1ActiveGeometry:
    """Backend-native P1 geometry evaluated only on compact active rows."""

    q_A: object
    s_A: object
    case_code_A: object
    edge_mask_A: object
    lambda_edge_A: object
    cell_measure_A: object
    jq_local_A: object
    ds_local_A: object
    row_norm_A: object
    sign_margin_A: object
    finite_mask_A: object
    regular_mask_A: object


@dataclass(frozen=True)
class P1ActiveVolumeGeometry:
    """Backend-native P1 cell volumes without surface/Jacobian work."""

    q_A: object
    case_code_A: object
    cell_measure_A: object


def active_cell_node_ids_2d(grid, cell_ids):
    """Return flattened Q1/P1 corner node ids for compact 2D cell ids."""
    xp = grid.xp
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if tuple(ids.shape[-1:]) != (2,):
        raise ValueError("cell_ids must have shape (n_active, 2)")
    i = ids[:, 0]
    j = ids[:, 1]
    n_y_nodes = int(grid.N[1]) + 1
    return xp.stack(
        (
            i * n_y_nodes + j,
            (i + 1) * n_y_nodes + j,
            (i + 1) * n_y_nodes + (j + 1),
            i * n_y_nodes + (j + 1),
        ),
        axis=-1,
    )


def refresh_active_geometry_2d(grid, phi, cell_ids, *, level: float = 0.0):
    """Evaluate active ``Q_h/S_h/J_q/dS_h`` rows for supplied cell ids.

    The caller owns support construction.  This function never calls
    ``where``/``nonzero`` over the full grid to discover active cells.
    """
    if grid.ndim != 2:
        raise ValueError("refresh_active_geometry_2d currently supports 2D grids")
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    raw = _refresh_active_geometry_2d_raw_if_available(
        grid,
        xp,
        phi_dev,
        ids,
        level=float(level),
    )
    if raw is not None:
        return raw
    return _refresh_active_geometry_2d_unfused(
        grid,
        xp,
        phi_dev,
        ids,
        level=float(level),
    )


def _refresh_active_geometry_2d_unfused(grid, xp, phi_dev, ids, *, level: float):
    values, points = _active_cell_corner_fields(xp, grid, phi_dev - float(level), ids)
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    q_A = _local_cut_areas(xp, values, points, crossings, case_code)
    s_A = _local_surface_lengths(xp, crossings, case_code)
    jq_local_A = _local_area_derivatives(xp, values, points, crossings, case_code)
    ds_local_A = _local_length_derivatives(xp, crossings, case_code)
    edge_mask_A = _edge_mask(xp, crossings)
    lambda_edge_A = xp.stack(tuple(crossing["theta"] for crossing in crossings), axis=-1)
    row_norm_A = xp.sum(jq_local_A * jq_local_A, axis=-1)
    abs_values = xp.stack(tuple(xp.abs(value) for value in values), axis=-1)
    finite_values = xp.stack(tuple(xp.isfinite(value) for value in values), axis=-1)
    finite_mask_A = xp.all(finite_values, axis=-1)
    sign_margin_A = xp.min(abs_values, axis=-1)
    regular_mask_A = finite_mask_A & (sign_margin_A > 0.0)
    return P1ActiveGeometry(
        q_A=q_A,
        s_A=s_A,
        case_code_A=case_code,
        edge_mask_A=edge_mask_A,
        lambda_edge_A=lambda_edge_A,
        cell_measure_A=cell_measure_A,
        jq_local_A=jq_local_A,
        ds_local_A=ds_local_A,
        row_norm_A=row_norm_A,
        sign_margin_A=sign_margin_A,
        finite_mask_A=finite_mask_A,
        regular_mask_A=regular_mask_A,
    )


def _refresh_active_geometry_2d_raw_if_available(
    grid,
    xp,
    phi_dev,
    ids,
    *,
    level: float,
):
    raw_kernel_type = getattr(xp, "RawKernel", None)
    if raw_kernel_type is None:
        return None
    n_active = int(ids.shape[0])
    if n_active == 0:
        return None
    dtype = np.dtype(phi_dev.dtype)
    if dtype not in (np.dtype("float32"), np.dtype("float64")):
        return None

    phi_c = xp.ascontiguousarray(phi_dev)
    ids_c = xp.ascontiguousarray(ids, dtype=xp.int64)
    x = xp.ascontiguousarray(_device_coord_1d(xp, grid, 0, dtype))
    y = xp.ascontiguousarray(_device_coord_1d(xp, grid, 1, dtype))
    q_A = xp.empty((n_active,), dtype=dtype)
    s_A = xp.empty((n_active,), dtype=dtype)
    case_code_A = xp.empty((n_active,), dtype=xp.uint8)
    edge_mask_A = xp.empty((n_active,), dtype=xp.uint8)
    lambda_edge_A = xp.empty((n_active, 4), dtype=dtype)
    cell_measure_A = xp.empty((n_active,), dtype=dtype)
    jq_local_A = xp.empty((n_active, 4), dtype=dtype)
    ds_local_A = xp.empty((n_active, 4), dtype=dtype)
    row_norm_A = xp.empty((n_active,), dtype=dtype)
    sign_margin_A = xp.empty((n_active,), dtype=dtype)
    finite_mask_A = xp.empty((n_active,), dtype=bool)
    regular_mask_A = xp.empty((n_active,), dtype=bool)

    threads = 128
    blocks = (n_active + threads - 1) // threads
    kernel = _active_geometry_raw_kernel(xp, dtype)
    kernel(
        (blocks,),
        (threads,),
        (
            phi_c,
            ids_c,
            x,
            y,
            q_A,
            s_A,
            case_code_A,
            edge_mask_A,
            lambda_edge_A,
            cell_measure_A,
            jq_local_A,
            ds_local_A,
            row_norm_A,
            sign_margin_A,
            finite_mask_A,
            regular_mask_A,
            np.int32(grid.N[0]),
            np.int32(grid.N[1]),
            np.int32(n_active),
            np.asarray(level, dtype=dtype),
        ),
    )
    return P1ActiveGeometry(
        q_A=q_A,
        s_A=s_A,
        case_code_A=case_code_A,
        edge_mask_A=edge_mask_A,
        lambda_edge_A=lambda_edge_A,
        cell_measure_A=cell_measure_A,
        jq_local_A=jq_local_A,
        ds_local_A=ds_local_A,
        row_norm_A=row_norm_A,
        sign_margin_A=sign_margin_A,
        finite_mask_A=finite_mask_A,
        regular_mask_A=regular_mask_A,
    )


def _active_geometry_raw_kernel(xp, dtype):
    key = (id(xp), np.dtype(dtype).name, "active_geometry")
    cached = _ACTIVE_GEOMETRY_RAW_KERNELS.get(key)
    if cached is not None:
        return cached
    scalar = "float" if np.dtype(dtype) == np.dtype("float32") else "double"
    finite_max = (
        "3.4028234663852886e38f"
        if np.dtype(dtype) == np.dtype("float32")
        else "1.7976931348623157e308"
    )
    code = r"""
__device__ __forceinline__ __SCALAR__ ag_abs(__SCALAR__ value) {
    return value < (__SCALAR__)0 ? -value : value;
}

__device__ __forceinline__ __SCALAR__ ag_min(__SCALAR__ left, __SCALAR__ right) {
    return left < right ? left : right;
}

__device__ __forceinline__ int ag_edge_lo(int edge) {
    return edge == 0 ? 0 : (edge == 1 ? 1 : (edge == 2 ? 2 : 3));
}

__device__ __forceinline__ int ag_edge_hi(int edge) {
    return edge == 0 ? 1 : (edge == 1 ? 2 : (edge == 2 ? 3 : 0));
}

__device__ __forceinline__ bool ag_inside(int case_code, int corner) {
    return (case_code & (1 << corner)) != 0;
}

__device__ __forceinline__ void ag_token_point(
    int kind,
    int index,
    const __SCALAR__* __restrict__ px,
    const __SCALAR__* __restrict__ py,
    const __SCALAR__* __restrict__ cx,
    const __SCALAR__* __restrict__ cy,
    __SCALAR__* out_x,
    __SCALAR__* out_y
) {
    if (kind == 0) {
        *out_x = px[index];
        *out_y = py[index];
    } else {
        *out_x = cx[index];
        *out_y = cy[index];
    }
}

__device__ __forceinline__ int ag_build_ring(
    int case_code,
    int ring,
    int* __restrict__ token_kind,
    int* __restrict__ token_index
) {
    if (case_code == 10) {
        if (ring == 0) {
            token_kind[0] = 0; token_index[0] = 1;
            token_kind[1] = 1; token_index[1] = 1;
            token_kind[2] = 1; token_index[2] = 0;
            return 3;
        }
        if (ring == 1) {
            token_kind[0] = 0; token_index[0] = 3;
            token_kind[1] = 1; token_index[1] = 3;
            token_kind[2] = 1; token_index[2] = 2;
            return 3;
        }
        return 0;
    }
    if (ring != 0) {
        return 0;
    }
    int count = 0;
    for (int edge = 0; edge < 4; ++edge) {
        int lo = ag_edge_lo(edge);
        int hi = ag_edge_hi(edge);
        bool inside_lo = ag_inside(case_code, lo);
        bool inside_hi = ag_inside(case_code, hi);
        if (inside_lo) {
            token_kind[count] = 0;
            token_index[count] = lo;
            ++count;
        }
        if (inside_lo != inside_hi) {
            token_kind[count] = 1;
            token_index[count] = edge;
            ++count;
        }
    }
    return count;
}

__device__ __forceinline__ void ag_add_crossing_derivative(
    int edge,
    __SCALAR__ scale_x,
    __SCALAR__ scale_y,
    __SCALAR__ sign,
    const __SCALAR__* __restrict__ values,
    const __SCALAR__* __restrict__ px,
    const __SCALAR__* __restrict__ py,
    const bool* __restrict__ edge_cross,
    __SCALAR__* __restrict__ local
) {
    int lo = ag_edge_lo(edge);
    int hi = ag_edge_hi(edge);
    __SCALAR__ denominator = values[hi] - values[lo];
    __SCALAR__ safe_denominator = edge_cross[edge] ? denominator : (__SCALAR__)1;
    __SCALAR__ denominator_sq = safe_denominator * safe_denominator;
    __SCALAR__ tangent_x = px[hi] - px[lo];
    __SCALAR__ tangent_y = py[hi] - py[lo];
    __SCALAR__ projected = scale_x * tangent_x + scale_y * tangent_y;
    local[lo] += sign * projected * (-values[hi] / denominator_sq);
    local[hi] += sign * projected * (values[lo] / denominator_sq);
}

__device__ __forceinline__ __SCALAR__ ag_segment_length(
    int left,
    int right,
    const __SCALAR__* __restrict__ cx,
    const __SCALAR__* __restrict__ cy
) {
    __SCALAR__ dx = cx[right] - cx[left];
    __SCALAR__ dy = cy[right] - cy[left];
    return sqrt(dx * dx + dy * dy);
}

__device__ __forceinline__ void ag_add_segment_length_derivative(
    int left,
    int right,
    const __SCALAR__* __restrict__ values,
    const __SCALAR__* __restrict__ px,
    const __SCALAR__* __restrict__ py,
    const __SCALAR__* __restrict__ cx,
    const __SCALAR__* __restrict__ cy,
    const bool* __restrict__ edge_cross,
    __SCALAR__* __restrict__ local
) {
    __SCALAR__ length = ag_segment_length(left, right, cx, cy);
    __SCALAR__ safe_length = length > (__SCALAR__)0 ? length : (__SCALAR__)1;
    __SCALAR__ tangent_x = (cx[right] - cx[left]) / safe_length;
    __SCALAR__ tangent_y = (cy[right] - cy[left]) / safe_length;
    ag_add_crossing_derivative(
        left, tangent_x, tangent_y, (__SCALAR__)-1,
        values, px, py, edge_cross, local
    );
    ag_add_crossing_derivative(
        right, tangent_x, tangent_y, (__SCALAR__)1,
        values, px, py, edge_cross, local
    );
}

extern "C" __global__
void refresh_active_geometry_2d_raw(
    const __SCALAR__* __restrict__ phi,
    const long long* __restrict__ ids,
    const __SCALAR__* __restrict__ x,
    const __SCALAR__* __restrict__ y,
    __SCALAR__* __restrict__ q,
    __SCALAR__* __restrict__ s,
    unsigned char* __restrict__ case_code_out,
    unsigned char* __restrict__ edge_mask_out,
    __SCALAR__* __restrict__ lambda_edge,
    __SCALAR__* __restrict__ cell_measure,
    __SCALAR__* __restrict__ jq_local,
    __SCALAR__* __restrict__ ds_local,
    __SCALAR__* __restrict__ row_norm,
    __SCALAR__* __restrict__ sign_margin,
    bool* __restrict__ finite_mask,
    bool* __restrict__ regular_mask,
    const int nx,
    const int ny,
    const int n_active,
    const __SCALAR__ level
) {
    int row = blockDim.x * blockIdx.x + threadIdx.x;
    if (row >= n_active) {
        return;
    }
    int i = (int)ids[2 * row + 0];
    int j = (int)ids[2 * row + 1];
    int ny_nodes = ny + 1;
    __SCALAR__ values[4];
    values[0] = phi[i * ny_nodes + j] - level;
    values[1] = phi[(i + 1) * ny_nodes + j] - level;
    values[2] = phi[(i + 1) * ny_nodes + (j + 1)] - level;
    values[3] = phi[i * ny_nodes + (j + 1)] - level;

    __SCALAR__ px[4];
    __SCALAR__ py[4];
    px[0] = x[i];     py[0] = y[j];
    px[1] = x[i + 1]; py[1] = y[j];
    px[2] = x[i + 1]; py[2] = y[j + 1];
    px[3] = x[i];     py[3] = y[j + 1];

    bool edge_cross[4];
    __SCALAR__ theta[4];
    __SCALAR__ cx[4];
    __SCALAR__ cy[4];
    unsigned char edge_bits = 0;
    for (int edge = 0; edge < 4; ++edge) {
        int lo = ag_edge_lo(edge);
        int hi = ag_edge_hi(edge);
        edge_cross[edge] = values[lo] * values[hi] < (__SCALAR__)0;
        __SCALAR__ denominator = values[hi] - values[lo];
        __SCALAR__ safe_denominator = edge_cross[edge] ? denominator : (__SCALAR__)1;
        theta[edge] = edge_cross[edge] ? -values[lo] / safe_denominator : (__SCALAR__)0;
        cx[edge] = px[lo] + theta[edge] * (px[hi] - px[lo]);
        cy[edge] = py[lo] + theta[edge] * (py[hi] - py[lo]);
        if (edge_cross[edge]) {
            edge_bits = (unsigned char)(edge_bits + (1 << edge));
        }
        lambda_edge[4 * row + edge] = theta[edge];
    }

    int case_code = 0;
    for (int corner = 0; corner < 4; ++corner) {
        if (values[corner] < (__SCALAR__)0) {
            case_code += (1 << corner);
        }
    }
    case_code_out[row] = (unsigned char)case_code;
    edge_mask_out[row] = edge_bits;
    cell_measure[row] = (px[1] - px[0]) * (py[2] - py[1]);

    __SCALAR__ local_q = (__SCALAR__)0;
    __SCALAR__ local_s = (__SCALAR__)0;
    __SCALAR__ jq[4] = {(__SCALAR__)0, (__SCALAR__)0, (__SCALAR__)0, (__SCALAR__)0};
    __SCALAR__ ds[4] = {(__SCALAR__)0, (__SCALAR__)0, (__SCALAR__)0, (__SCALAR__)0};

    for (int ring = 0; ring < 2; ++ring) {
        int token_kind[8];
        int token_index[8];
        int count = ag_build_ring(case_code, ring, token_kind, token_index);
        if (count < 3) {
            continue;
        }
        bool active = true;
        for (int token = 0; token < count; ++token) {
            if (token_kind[token] == 1) {
                active = active && edge_cross[token_index[token]];
            }
        }
        if (!active) {
            continue;
        }
        __SCALAR__ shoelace = (__SCALAR__)0;
        for (int token = 0; token < count; ++token) {
            int next = token + 1 == count ? 0 : token + 1;
            __SCALAR__ tx, ty, nxp, nyp;
            ag_token_point(
                token_kind[token], token_index[token],
                px, py, cx, cy, &tx, &ty
            );
            ag_token_point(
                token_kind[next], token_index[next],
                px, py, cx, cy, &nxp, &nyp
            );
            shoelace += tx * nyp - ty * nxp;
        }
        local_q += (__SCALAR__)0.5 * shoelace;

        for (int token = 0; token < count; ++token) {
            if (token_kind[token] != 1) {
                continue;
            }
            int prev = token == 0 ? count - 1 : token - 1;
            int next = token + 1 == count ? 0 : token + 1;
            __SCALAR__ prev_x, prev_y, next_x, next_y;
            ag_token_point(
                token_kind[prev], token_index[prev],
                px, py, cx, cy, &prev_x, &prev_y
            );
            ag_token_point(
                token_kind[next], token_index[next],
                px, py, cx, cy, &next_x, &next_y
            );
            __SCALAR__ covector_x = (__SCALAR__)0.5 * (next_y - prev_y);
            __SCALAR__ covector_y = (__SCALAR__)0.5 * (prev_x - next_x);
            ag_add_crossing_derivative(
                token_index[token],
                covector_x,
                covector_y,
                (__SCALAR__)1,
                values,
                px,
                py,
                edge_cross,
                jq
            );
        }
    }

    int crossing_edges[4];
    int crossing_count = 0;
    for (int edge = 0; edge < 4; ++edge) {
        int lo = ag_edge_lo(edge);
        int hi = ag_edge_hi(edge);
        if (ag_inside(case_code, lo) != ag_inside(case_code, hi)) {
            crossing_edges[crossing_count] = edge;
            ++crossing_count;
        }
    }
    bool active_length = crossing_count == 2 || crossing_count == 4;
    for (int index = 0; index < crossing_count; ++index) {
        active_length = active_length && edge_cross[crossing_edges[index]];
    }
    if (active_length) {
        local_s += ag_segment_length(crossing_edges[0], crossing_edges[1], cx, cy);
        ag_add_segment_length_derivative(
            crossing_edges[0], crossing_edges[1],
            values, px, py, cx, cy, edge_cross, ds
        );
        if (crossing_count == 4) {
            local_s += ag_segment_length(crossing_edges[2], crossing_edges[3], cx, cy);
            ag_add_segment_length_derivative(
                crossing_edges[2], crossing_edges[3],
                values, px, py, cx, cy, edge_cross, ds
            );
        }
    }

    q[row] = local_q;
    s[row] = local_s;
    __SCALAR__ norm = (__SCALAR__)0;
    for (int corner = 0; corner < 4; ++corner) {
        jq_local[4 * row + corner] = jq[corner];
        ds_local[4 * row + corner] = ds[corner];
        norm += jq[corner] * jq[corner];
    }
    row_norm[row] = norm;

    __SCALAR__ margin = ag_min(
        ag_min(ag_abs(values[0]), ag_abs(values[1])),
        ag_min(ag_abs(values[2]), ag_abs(values[3]))
    );
    bool finite = true;
    for (int corner = 0; corner < 4; ++corner) {
        finite = (
            finite
            && values[corner] == values[corner]
            && ag_abs(values[corner]) <= (__SCALAR__)__FINITE_MAX__
        );
    }
    sign_margin[row] = margin;
    finite_mask[row] = finite;
    regular_mask[row] = finite && margin > (__SCALAR__)0;
}
""".replace("__SCALAR__", scalar).replace("__FINITE_MAX__", finite_max)
    kernel = xp.RawKernel(code, "refresh_active_geometry_2d_raw")
    _ACTIVE_GEOMETRY_RAW_KERNELS[key] = kernel
    return kernel


def refresh_active_volume_geometry_2d(grid, phi, cell_ids, *, level: float = 0.0):
    """Evaluate only the active P1 cut-cell volumes ``Q_h(phi)_A``.

    This is the exact same marching-squares volume formula used by
    ``refresh_active_geometry_2d``.  It deliberately skips interface length and
    derivative tables for line-search stages where the discrete equation only
    asks whether the hard volume residual decreased.
    """
    if grid.ndim != 2:
        raise ValueError(
            "refresh_active_volume_geometry_2d currently supports 2D grids"
        )
    xp = grid.xp
    phi_dev = xp.asarray(phi)
    if tuple(phi_dev.shape) != (grid.N[0] + 1, grid.N[1] + 1):
        raise ValueError("phi shape must match the grid nodal shape")
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    values, points = _active_cell_corner_fields(xp, grid, phi_dev - float(level), ids)
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    return P1ActiveVolumeGeometry(
        q_A=_local_cut_areas(xp, values, points, crossings, case_code),
        case_code_A=case_code,
        cell_measure_A=cell_measure_A,
    )


def refresh_active_volume_geometry_candidates_2d(
    grid,
    phi_candidates,
    cell_ids,
    *,
    level: float = 0.0,
):
    """Evaluate exact ``Q_h`` for a fixed batch of candidate P1 gauges."""
    if grid.ndim != 2:
        raise ValueError(
            "refresh_active_volume_geometry_candidates_2d currently supports 2D grids"
        )
    xp = grid.xp
    phi_dev = xp.asarray(phi_candidates)
    expected_tail = (grid.N[0] + 1, grid.N[1] + 1)
    if phi_dev.ndim != 3 or tuple(phi_dev.shape[-2:]) != expected_tail:
        raise ValueError(
            "phi_candidates must have shape (n_candidates, "
            f"{expected_tail[0]}, {expected_tail[1]})"
        )
    ids = xp.asarray(cell_ids, dtype=xp.int64)
    if ids.ndim != 2 or ids.shape[1] != 2:
        raise ValueError("cell_ids must have shape (n_active, 2)")

    values, points = _active_cell_corner_fields_batched(
        xp,
        grid,
        phi_dev - float(level),
        ids,
    )
    cell_measure_A = _active_cell_measures_from_points(points)
    crossings = tuple(_edge_crossing(xp, values, points, edge) for edge in range(4))
    case_code = _case_field(xp, values)
    return P1ActiveVolumeGeometry(
        q_A=_local_cut_areas(xp, values, points, crossings, case_code),
        case_code_A=case_code,
        cell_measure_A=cell_measure_A,
    )


def _active_cell_corner_fields(xp, grid, phi, cell_ids):
    i = cell_ids[:, 0]
    j = cell_ids[:, 1]
    x = _device_coord_1d(xp, grid, 0, phi.dtype)
    y = _device_coord_1d(xp, grid, 1, phi.dtype)
    values = (
        phi[i, j],
        phi[i + 1, j],
        phi[i + 1, j + 1],
        phi[i, j + 1],
    )
    points = (
        (x[i], y[j]),
        (x[i + 1], y[j]),
        (x[i + 1], y[j + 1]),
        (x[i], y[j + 1]),
    )
    return values, points


def _active_cell_corner_fields_batched(xp, grid, phi, cell_ids):
    i = cell_ids[:, 0]
    j = cell_ids[:, 1]
    x = _device_coord_1d(xp, grid, 0, phi.dtype)
    y = _device_coord_1d(xp, grid, 1, phi.dtype)
    values = (
        phi[:, i, j],
        phi[:, i + 1, j],
        phi[:, i + 1, j + 1],
        phi[:, i, j + 1],
    )
    points = (
        (x[i], y[j]),
        (x[i + 1], y[j]),
        (x[i + 1], y[j + 1]),
        (x[i], y[j + 1]),
    )
    return values, points


def _device_coord_1d(xp, grid, axis: int, dtype):
    getter = getattr(grid, "device_coords", None)
    if callable(getter):
        return getter(axis, dtype=dtype)
    return xp.asarray(grid.coords[axis], dtype=dtype)


def _active_cell_measures_from_points(points):
    dx = points[1][0] - points[0][0]
    dy = points[2][1] - points[1][1]
    return dx * dy


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
    return {
        "mask": mask,
        "theta": theta,
        "x": x,
        "y": y,
        "lo": lo,
        "hi": hi,
        "values": values,
        "points": points,
    }


def _case_field(xp, values):
    inside = tuple(value < 0.0 for value in values)
    case_field = xp.zeros_like(values[0], dtype=xp.uint8)
    for corner, mask in enumerate(inside):
        case_field = case_field + mask.astype(xp.uint8) * (1 << corner)
    return case_field


def _edge_mask(xp, crossings):
    mask = xp.zeros_like(crossings[0]["theta"], dtype=xp.uint8)
    for edge, crossing in enumerate(crossings):
        mask = mask + crossing["mask"].astype(xp.uint8) * (1 << edge)
    return mask


def _local_cut_areas(xp, values, points, crossings, case_field):
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


def _local_surface_lengths(xp, crossings, case_field):
    local_length = xp.zeros_like(crossings[0]["theta"])
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


def _local_area_derivatives(xp, values, points, crossings, case_field):
    local = _local_zeros(xp, values)
    for case_id in range(16):
        for tokens in _liquid_polygon_rings(case_id):
            if len(tokens) < 3:
                continue
            active = case_field == case_id
            for kind, index in tokens:
                if kind == "edge":
                    active = active & crossings[index]["mask"]
            for index, token in enumerate(tokens):
                previous_token = tokens[(index - 1) % len(tokens)]
                next_token = tokens[(index + 1) % len(tokens)]
                _add_area_vertex_contribution(
                    xp,
                    local,
                    token,
                    previous_token,
                    next_token,
                    active,
                    points=points,
                    crossings=crossings,
                )
    return _stack_local(xp, local)


def _local_length_derivatives(xp, crossings, case_field):
    local = _local_zeros(xp, tuple(crossing["theta"] for crossing in crossings))
    for case_id in range(16):
        edges = _crossing_edges(case_id)
        if len(edges) not in {2, 4}:
            continue
        active = case_field == case_id
        for edge in edges:
            active = active & crossings[edge]["mask"]
        _add_segment_length_contribution(
            xp,
            local,
            crossings[edges[0]],
            crossings[edges[1]],
            active,
        )
        if len(edges) == 4:
            _add_segment_length_contribution(
                xp,
                local,
                crossings[edges[2]],
                crossings[edges[3]],
                active,
            )
    return _stack_local(xp, local)


def _add_area_vertex_contribution(
    xp,
    local,
    token,
    previous_token,
    next_token,
    active,
    *,
    points,
    crossings,
):
    if token[0] != "edge":
        return
    point_prev = _token_point(previous_token, points=points, crossings=crossings)
    point_next = _token_point(next_token, points=points, crossings=crossings)
    covector_x = 0.5 * (point_next[1] - point_prev[1])
    covector_y = 0.5 * (point_prev[0] - point_next[0])
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, crossings[token[1]]):
        contribution = covector_x * dx_dphi + covector_y * dy_dphi
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )


def _add_segment_length_contribution(xp, local, left, right, active):
    length = _segment_length(xp, left, right)
    safe_length = xp.where(length > 0.0, length, xp.ones_like(length))
    tangent_x = (right["x"] - left["x"]) / safe_length
    tangent_y = (right["y"] - left["y"]) / safe_length
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, left):
        contribution = -(tangent_x * dx_dphi + tangent_y * dy_dphi)
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )
    for corner, dx_dphi, dy_dphi in _crossing_derivatives(xp, right):
        contribution = tangent_x * dx_dphi + tangent_y * dy_dphi
        local[corner] = local[corner] + xp.where(
            active,
            contribution,
            xp.zeros_like(contribution),
        )


def _crossing_derivatives(xp, crossing):
    values = crossing["values"]
    points = crossing["points"]
    lo = crossing["lo"]
    hi = crossing["hi"]
    value_lo = values[lo]
    value_hi = values[hi]
    denominator = value_hi - value_lo
    safe_denominator = xp.where(
        crossing["mask"],
        denominator,
        xp.ones_like(denominator),
    )
    denominator_sq = safe_denominator * safe_denominator
    tangent_x = points[hi][0] - points[lo][0]
    tangent_y = points[hi][1] - points[lo][1]
    dtheta_lo = -value_hi / denominator_sq
    dtheta_hi = value_lo / denominator_sq
    return (
        (lo, tangent_x * dtheta_lo, tangent_y * dtheta_lo),
        (hi, tangent_x * dtheta_hi, tangent_y * dtheta_hi),
    )


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


def _local_zeros(xp, values):
    return [xp.zeros_like(values[0]) for _corner in range(4)]


def _stack_local(xp, local):
    return xp.stack(local, axis=-1)
