"""Godunov sweep for Eikonal redistancing.

Symbol mapping
--------------
``phi``    -> signed level-set field ``φ``
``sgn0``   -> sign of initial field ``sgn(φ₀)``
``dtau``   -> pseudo-time step ``Δτ``
``hx_fwd`` -> forward spacing in ``x``
``hx_bwd`` -> backward spacing in ``x``
``hy_fwd`` -> forward spacing in ``y``
``hy_bwd`` -> backward spacing in ``y``
"""

from __future__ import annotations


def godunov_sweep(
    xp,
    phi,
    sgn0,
    *,
    dtau: float,
    n_iter: int,
    hx_fwd,
    hx_bwd,
    hy_fwd,
    hy_bwd,
    zsp: bool,
    h_min: float,
    frozen_mask=None,
):
    """Run the first-order Godunov pseudo-time sweep."""
    inside = sgn0 > 0
    zsp_frozen = xp.abs(phi) < 0.5 * h_min if zsp else None
    if frozen_mask is not None:
        frozen = xp.asarray(frozen_mask)
        zsp_frozen = frozen if zsp_frozen is None else (zsp_frozen | frozen)

    for _ in range(n_iter):
        phi_x = xp.roll(phi, -1, axis=0)
        phi_xm = xp.roll(phi, 1, axis=0)
        phi_y = xp.roll(phi, -1, axis=1)
        phi_ym = xp.roll(phi, 1, axis=1)

        Dpx = (phi_x - phi) / hx_fwd
        Dmx = (phi - phi_xm) / hx_bwd
        Dpy = (phi_y - phi) / hy_fwd
        Dmy = (phi - phi_ym) / hy_bwd

        ax = xp.where(
            inside,
            xp.maximum(xp.maximum(Dmx, 0.0) ** 2, xp.minimum(Dpx, 0.0) ** 2),
            xp.maximum(xp.minimum(Dmx, 0.0) ** 2, xp.maximum(Dpx, 0.0) ** 2),
        )
        ay = xp.where(
            inside,
            xp.maximum(xp.maximum(Dmy, 0.0) ** 2, xp.minimum(Dpy, 0.0) ** 2),
            xp.maximum(xp.minimum(Dmy, 0.0) ** 2, xp.maximum(Dpy, 0.0) ** 2),
        )

        G = xp.sqrt(ax + ay + 1e-14) - 1.0
        phi_new = phi - dtau * sgn0 * G
        phi = xp.where(zsp_frozen, phi, phi_new) if zsp_frozen is not None else phi_new

    return phi
