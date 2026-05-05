"""FCCD face-native capillary geometry for pressure-jump closures.

A3 chain:
  Young--Laplace law ``j_gl=-σ κ_lg``
    -> compact implicit curvature evaluated on the pressure-jump face
    -> cut-face curvature ``κ_f`` from CCD derivative traces
    -> affine pressure-jump face gradient ``B_Γ(j_f)``.

This module deliberately computes curvature on the cut faces that receive the
pressure jump, using CCD derivative traces from the same compact-operator
family as FCCD.  It is not a smoothing or curvature cap; it is the geometric
Young--Laplace input evaluated at the same ``ψ=1/2`` jump location.
"""

from __future__ import annotations

from ..core.boundary import is_periodic_axis


def implicit_face_curvatures_2d(
    *,
    xp,
    grid,
    psi,
    fccd,
    phase_threshold: float = 0.5,
):
    r"""Return FCCD implicit-interface curvature evaluated at cut faces.

    A3 chain:
      ``κ = -∇·(∇ψ/|∇ψ|)``
        -> build nodal compact derivatives with CCD
        -> trace those derivatives to the cut location ``ψ=1/2``
        -> evaluate ``κ_f`` on the same cut face used by ``B_Γ(j)``.

    All array algebra uses ``xp`` and no global contour sort, host-side polygon
    assembly, or non-compact derivative operator is used.
    """
    if grid.ndim != 2:
        raise ValueError("implicit_face_curvatures_2d supports 2-D grids only")
    if fccd is None:
        raise ValueError("implicit_face_curvatures_2d requires an FCCDSolver")

    psi = xp.asarray(psi)
    ccd = fccd._ccd
    psi_x, psi_xx = ccd.differentiate(psi, 0)
    psi_y, psi_yy = ccd.differentiate(psi, 1)
    psi_xy_from_x, _ = ccd.differentiate(psi_x, 1)
    psi_yx_from_y, _ = ccd.differentiate(psi_y, 0)
    psi_xy = 0.5 * (psi_xy_from_x + psi_yx_from_y)

    def face_trace_data(axis: int):
        psi_lo, psi_hi = face_pair(psi, axis)
        cut_face = (psi_lo < phase_threshold) != (psi_hi < phase_threshold)
        dpsi = psi_hi - psi_lo
        denominator = xp.where(cut_face, dpsi, xp.ones_like(dpsi))
        theta = xp.where(
            cut_face,
            (phase_threshold - psi_lo) / denominator,
            xp.zeros_like(dpsi),
        )
        return cut_face, theta

    def face_pair(field, axis: int):
        moved = xp.moveaxis(xp.asarray(field), axis, 0)
        if is_periodic_axis(fccd.bc_type, axis, grid.ndim):
            unique = moved[: grid.N[axis]]
            lo = unique
            hi = xp.roll(unique, -1, axis=0)
        else:
            lo = moved[:-1]
            hi = moved[1:]
        return xp.moveaxis(lo, 0, axis), xp.moveaxis(hi, 0, axis)

    def face_trace(field, axis: int, theta):
        lo, hi = face_pair(field, axis)
        return (1.0 - theta) * lo + theta * hi

    face_curvatures = []
    for axis in range(2):
        cut_face, theta = face_trace_data(axis)
        px = face_trace(psi_x, axis, theta)
        py = face_trace(psi_y, axis, theta)
        pxx = face_trace(psi_xx, axis, theta)
        pyy = face_trace(psi_yy, axis, theta)
        pxy = face_trace(psi_xy, axis, theta)
        grad_sq = px * px + py * py
        numerator = py * py * pxx - 2.0 * px * py * pxy + px * px * pyy
        denominator = grad_sq * xp.sqrt(grad_sq)
        denominator = xp.where(cut_face, denominator, xp.ones_like(denominator))
        kappa = -numerator / denominator
        face_curvatures.append(xp.where(cut_face, kappa, xp.zeros_like(kappa)))

    return tuple(face_curvatures)
