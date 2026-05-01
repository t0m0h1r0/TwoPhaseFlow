r"""Capillary geometry closures shared by curvature and pressure jumps.

Symbol mapping
--------------
``ψ`` -> ``psi``
``κ_Γ`` -> ``kappa_lg``
``\partial\Omega_w`` -> stationary no-slip wall boundary
``\partial_n κ_Γ=0`` -> ``wall_normal_layers`` interior-limit closure

A3 chain
--------
paper/sections/03b_cls_transport.tex: wall phase-topology invariant
  -> paper/sections/11_full_algorithm.tex: wall-contact curvature caveat
  -> stationary-wall endpoint force is a constraint reaction
  -> use the interior limiting interface curvature in wall-normal closure layers
  -> ``apply_wall_compatible_curvature``
"""

from __future__ import annotations

from ..core.boundary import is_wall_axis


def apply_wall_compatible_curvature(
    *,
    xp,
    grid,
    psi,
    kappa_lg,
    bc_type: str,
    psi_min: float | None,
    wall_normal_layers: int = 2,
):
    """Return wall-compatible capillary curvature on the backend device.

    For a stationary no-slip wall with no explicit wetting/contact-line law, the
    wall contact root is a constrained endpoint.  The wall reaction balances the
    endpoint traction, so the Young--Laplace pressure jump must use the
    one-sided interior limit of ``κ_Γ`` rather than a bulk nodal boundary
    stencil.  The discrete closure is the neutral ghost-geometry condition
    ``∂_n κ_Γ=0`` over the wall-normal closure layers.

    The implementation is GPU-friendly: all arrays remain in ``xp`` and only a
    small loop over coordinate axes is performed; each assignment is a device
    slice operation for CuPy backends.
    """
    if wall_normal_layers <= 0:
        return kappa_lg
    if getattr(grid, "ndim", 0) < 1:
        return kappa_lg
    if not any(is_wall_axis(bc_type, axis, grid.ndim) for axis in range(grid.ndim)):
        return kappa_lg

    psi_arr = xp.asarray(psi)
    kappa = xp.copy(xp.asarray(kappa_lg))
    layers = int(wall_normal_layers)
    for axis in range(grid.ndim):
        if not is_wall_axis(bc_type, axis, grid.ndim):
            continue
        n_cells = int(grid.N[axis])
        if n_cells < 2 * layers:
            continue

        left_src = [slice(None)] * grid.ndim
        left_dst = [slice(None)] * grid.ndim
        left_src[axis] = layers
        left_dst[axis] = slice(0, layers)
        kappa[tuple(left_dst)] = xp.expand_dims(kappa[tuple(left_src)], axis=axis)

        right_src = [slice(None)] * grid.ndim
        right_dst = [slice(None)] * grid.ndim
        right_src[axis] = n_cells - layers
        right_dst[axis] = slice(n_cells - layers + 1, n_cells + 1)
        kappa[tuple(right_dst)] = xp.expand_dims(kappa[tuple(right_src)], axis=axis)

    if psi_min is None or psi_min <= 0.0:
        return kappa
    band = (psi_arr > psi_min) & (psi_arr < 1.0 - psi_min)
    return xp.where(band, kappa, 0.0)
