"""Helper utilities for `PPEBuilder` assembly and RHS preparation."""

from __future__ import annotations

import numpy as np

from ..core.boundary import is_periodic_axis


def build_ppe_matrix_triplets(builder, rho) -> tuple:
    """Build the sparse PPE matrix COO triplets for the given density field."""
    xp = builder.xp
    n = builder.n_dof
    ndim = builder.ndim

    rho_arr = xp.asarray(rho)
    rho_flat = rho_arr.ravel()

    if not builder._face_indices_dev:
        for ax, (idx_L, idx_R) in builder._face_indices.items():
            builder._face_indices_dev[ax] = (xp.asarray(idx_L), xp.asarray(idx_R))

    data_list: list = []
    row_list: list = []
    col_list: list = []
    strides = [int(np.prod(builder.shape_field[ax + 1:])) for ax in range(ndim)]

    for ax in range(ndim):
        N_ax = builder.N[ax]
        idx_L_xp, idx_R_xp = builder._face_indices_dev[ax]

        rho_L = rho_flat[idx_L_xp]
        rho_R = rho_flat[idx_R_xp]
        a_f = 2.0 / (rho_L + rho_R)

        if not builder.grid.uniform:
            d_f_xp, dv_L_xp, dv_R_xp = _get_nonuniform_face_cache(
                builder,
                ax=ax,
                strides=strides,
            )
            coeff_for_L = a_f / d_f_xp / dv_L_xp
            coeff_for_R = a_f / d_f_xp / dv_R_xp
        else:
            coeff_for_L, coeff_for_R = _build_uniform_face_coefficients(
                builder,
                ax=ax,
                face_coeff=a_f,
                strides=strides,
            )

        data_list.extend([coeff_for_L, coeff_for_R, -coeff_for_L, -coeff_for_R])
        row_list.extend([idx_L_xp, idx_R_xp, idx_L_xp, idx_R_xp])
        col_list.extend([idx_R_xp, idx_L_xp, idx_L_xp, idx_R_xp])

        if is_periodic_axis(builder.bc_type, ax, builder.ndim):
            idx_wL, idx_wR = builder._wrap_face_indices[ax]
            rho_wL = rho_flat[xp.asarray(idx_wL)]
            rho_wR = rho_flat[xp.asarray(idx_wR)]
            a_w = 2.0 / (rho_wL + rho_wR)
            if not builder.grid.uniform:
                d_wrap, dv_wL, dv_wR = _get_nonuniform_wrap_cache(builder, ax=ax)
                coeff_wL = a_w / d_wrap / dv_wL
                coeff_wR = a_w / d_wrap / dv_wR
            else:
                h = float(builder.grid.L[ax] / N_ax)
                coeff_wL = coeff_wR = a_w / (h * h)
            idx_wL_xp = xp.asarray(idx_wL)
            idx_wR_xp = xp.asarray(idx_wR)
            data_list.extend([coeff_wL, coeff_wR, -coeff_wL, -coeff_wR])
            row_list.extend([idx_wL_xp, idx_wR_xp, idx_wL_xp, idx_wR_xp])
            col_list.extend([idx_wR_xp, idx_wL_xp, idx_wL_xp, idx_wR_xp])

    data = xp.concatenate(data_list)
    rows = xp.concatenate(row_list)
    cols = xp.concatenate(col_list)
    data, rows, cols = _apply_periodic_row_constraints(builder, data, rows, cols)
    data, rows, cols = _apply_pin_constraint(builder, data, rows, cols)
    return (data, rows, cols), (n, n)


def prepare_ppe_rhs_vector(builder, rhs_field):
    """Prepare the flat RHS vector for the PPE solve."""
    rhs_vec = np.asarray(builder.backend.to_host(rhs_field)).ravel().copy()
    rhs_vec[builder._pin_dof] = 0.0
    if builder._periodic_image_dofs is not None:
        rhs_vec[builder._periodic_image_dofs] = 0.0
    return rhs_vec


def build_ppe_index_arrays(builder) -> None:
    """Pre-compute the flat node indices of each face type."""
    import numpy as np_host

    builder._face_indices = {}
    shape = builder.shape_field

    for ax in range(builder.ndim):
        ranges = [np_host.arange(s) for s in shape]
        N_ax = builder.N[ax]

        if is_periodic_axis(builder.bc_type, ax, builder.ndim):
            ranges_L = [r.copy() for r in ranges]
            ranges_R = [r.copy() for r in ranges]
            ranges_L[ax] = np_host.arange(0, N_ax - 1)
            ranges_R[ax] = np_host.arange(1, N_ax)
        else:
            ranges_L = [r.copy() for r in ranges]
            ranges_R = [r.copy() for r in ranges]
            ranges_L[ax] = np_host.arange(0, N_ax)
            ranges_R[ax] = np_host.arange(1, N_ax + 1)

        grid_L = np_host.meshgrid(*ranges_L, indexing='ij')
        grid_R = np_host.meshgrid(*ranges_R, indexing='ij')
        idx_L = np_host.ravel_multi_index([g.ravel() for g in grid_L], shape)
        idx_R = np_host.ravel_multi_index([g.ravel() for g in grid_R], shape)
        builder._face_indices[ax] = (idx_L, idx_R)

    if not any(is_periodic_axis(builder.bc_type, ax, builder.ndim) for ax in range(builder.ndim)):
        builder._wrap_face_indices = {}
        builder._periodic_image_dofs = None
        builder._periodic_image_sources = None
        return

    builder._wrap_face_indices = {}
    image_to_source: dict[int, int] = {}

    for ax in range(builder.ndim):
        if not is_periodic_axis(builder.bc_type, ax, builder.ndim):
            continue
        N_ax = builder.N[ax]
        ranges = [np_host.arange(s) for s in shape]

        ranges_wL = [r.copy() for r in ranges]
        ranges_wR = [r.copy() for r in ranges]
        ranges_wL[ax] = np_host.array([N_ax - 1])
        ranges_wR[ax] = np_host.array([0])

        g_wL = np_host.meshgrid(*ranges_wL, indexing='ij')
        g_wR = np_host.meshgrid(*ranges_wR, indexing='ij')
        idx_wL = np_host.ravel_multi_index([g.ravel() for g in g_wL], shape)
        idx_wR = np_host.ravel_multi_index([g.ravel() for g in g_wR], shape)
        builder._wrap_face_indices[ax] = (idx_wL, idx_wR)

        ranges_img = [r.copy() for r in ranges]
        ranges_src = [r.copy() for r in ranges]
        ranges_img[ax] = np_host.array([N_ax])
        ranges_src[ax] = np_host.array([0])

        g_img = np_host.meshgrid(*ranges_img, indexing='ij')
        g_src = np_host.meshgrid(*ranges_src, indexing='ij')
        idx_img = np_host.ravel_multi_index([g.ravel() for g in g_img], shape)
        idx_src = np_host.ravel_multi_index([g.ravel() for g in g_src], shape)
        for im, sr in zip(idx_img.tolist(), idx_src.tolist()):
            if im not in image_to_source:
                image_to_source[im] = sr

    sorted_imgs = sorted(image_to_source.keys())
    builder._periodic_image_dofs = np_host.array(sorted_imgs, dtype=np_host.intp)
    builder._periodic_image_sources = np_host.array(
        [image_to_source[k] for k in sorted_imgs],
        dtype=np_host.intp,
    )


def _get_nonuniform_face_cache(builder, *, ax: int, strides: list[int]):
    xp = builder.xp
    cache_key = ('nonunif', ax)
    if cache_key not in builder._gpu_coeff_cache:
        coords = np.asarray(builder.grid.coords[ax])
        d_face = coords[1:] - coords[:-1]
        dv = np.empty(len(coords))
        if is_periodic_axis(builder.bc_type, ax, builder.ndim):
            dv[0] = 0.5 * (d_face[-1] + d_face[0])
            dv[-1] = dv[0]
        else:
            dv[0] = d_face[0] / 2.0
            dv[-1] = d_face[-1] / 2.0
        dv[1:-1] = (coords[2:] - coords[:-2]) / 2.0
        idx_L_h, idx_R_h = builder._face_indices[ax]
        stride = strides[ax]
        ax_idx_L = (idx_L_h // stride) % builder.shape_field[ax]
        ax_idx_R = (idx_R_h // stride) % builder.shape_field[ax]
        builder._gpu_coeff_cache[cache_key] = (
            xp.asarray(d_face[ax_idx_L]),
            xp.asarray(dv[ax_idx_L]),
            xp.asarray(dv[ax_idx_R]),
        )
    return builder._gpu_coeff_cache[cache_key]


def _get_nonuniform_wrap_cache(builder, *, ax: int):
    xp = builder.xp
    cache_key = ('nonunif_wrap', ax)
    if cache_key not in builder._gpu_coeff_cache:
        coords = np.asarray(builder.grid.coords[ax])
        d_face = coords[1:] - coords[:-1]
        d_wrap = d_face[-1]
        dv_left = 0.5 * (d_face[-2] + d_face[-1]) if len(d_face) > 1 else d_face[-1]
        dv_right = 0.5 * (d_face[-1] + d_face[0])
        builder._gpu_coeff_cache[cache_key] = (
            xp.asarray(d_wrap),
            xp.asarray(dv_left),
            xp.asarray(dv_right),
        )
    return builder._gpu_coeff_cache[cache_key]


def _build_uniform_face_coefficients(builder, *, ax: int, face_coeff, strides: list[int]):
    xp = builder.xp
    N_ax = builder.N[ax]
    h = float(builder.grid.L[ax] / N_ax)
    h2 = h * h
    coeff = face_coeff / h2

    if is_periodic_axis(builder.bc_type, ax, builder.ndim):
        return coeff, coeff

    cache_key = ('bc_mask', ax)
    if cache_key not in builder._gpu_coeff_cache:
        idx_L_h, idx_R_h = builder._face_indices[ax]
        stride = strides[ax]
        ax_idx_L = (idx_L_h // stride) % builder.shape_field[ax]
        ax_idx_R = (idx_R_h // stride) % builder.shape_field[ax]
        builder._gpu_coeff_cache[cache_key] = (
            builder.xp.asarray(ax_idx_L == 0),
            builder.xp.asarray(ax_idx_R == N_ax),
        )
    mask_L, mask_R = builder._gpu_coeff_cache[cache_key]
    return xp.where(mask_L, 2.0 * coeff, coeff), xp.where(mask_R, 2.0 * coeff, coeff)


def _apply_periodic_row_constraints(builder, data, rows, cols):
    if builder._periodic_image_dofs is None:
        return data, rows, cols
    xp = builder.xp
    img_dofs = builder._periodic_image_dofs
    src_dofs = builder._periodic_image_sources
    rows_h = np.asarray(builder.backend.to_host(rows))
    keep = xp.asarray(~np.isin(rows_h, img_dofs))
    data, rows, cols = data[keep], rows[keep], cols[keep]
    data = xp.concatenate([data, xp.ones(len(img_dofs)), -xp.ones(len(img_dofs))])
    rows = xp.concatenate([rows, xp.asarray(img_dofs), xp.asarray(img_dofs)])
    cols = xp.concatenate([cols, xp.asarray(img_dofs), xp.asarray(src_dofs)])
    return data, rows, cols


def _apply_pin_constraint(builder, data, rows, cols):
    xp = builder.xp
    pin = builder._pin_dof
    keep = rows != pin
    data = xp.concatenate([data[keep], xp.array([1.0])])
    rows = xp.concatenate([rows[keep], xp.array([pin], dtype=rows.dtype)])
    cols = xp.concatenate([cols[keep], xp.array([pin], dtype=cols.dtype)])
    return data, rows, cols
