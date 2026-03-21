"""
Rhie-Chow face-velocity interpolation and divergence.

Implements §6.3 (Eq. 61) and §7.4 (Eq. 65) of the paper.

On a collocated grid the straightforward linear interpolation of
cell-centred velocities to faces decouples odd- and even-indexed
pressure nodes, producing the 2Δx ``checkerboard'' instability (§6.1).

The Rhie-Chow correction eliminates this by adding a face-level
pressure damping term (§6.3 Eq. 61):

    u_f = ū_f − Δt (1/ρ)_f^harm [(∇p)_f − (∇p)̄_f]

where:
  ū_f           = arithmetic average of u* at the two adjacent cells
  (∇p)_f        = direct face pressure gradient (p_{i+1}−p_i)/h
  (∇p)̄_f       = arithmetic average of cell-centred ∇p
  (1/ρ)_f^harm  = 2/(ρ_L + ρ_R)  (harmonic mean, §6.3)

The divergence computed from RC face velocities (not cell-centred
∇·u*) is used as the RHS of the PPE (§7.4 Eq. 65).

CRITICAL: using cell-centred ∇·u* in the PPE RHS causes checkerboard
repulsion.  Only the Rhie-Chow face-velocity divergence is correct.
"""

from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class RhieChowInterpolator:
    """Compute face velocities and Rhie-Chow divergence.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver — コンストラクタ注入（毎呼び出しでの引き渡し不要）
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver"):
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.ccd = ccd

    def face_velocity_divergence(
        self,
        vel_star: List,
        p: Any,
        rho: Any,
        dt: float,
    ) -> Any:
        """Compute ∇·u_RC (the Rhie-Chow face-velocity divergence).

        Parameters
        ----------
        vel_star : list of u* arrays
        p        : current pressure field (used for RC correction)
        rho      : density field
        dt       : time step

        Returns
        -------
        div_rc : divergence array, shape ``grid.shape``
        """
        xp = self.xp
        ndim = self.ndim
        ccd = self.ccd
        div_rc = xp.zeros_like(vel_star[0])

        for ax in range(ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            flux_faces = self._rc_flux_1d(vel_star[ax], p, rho, ccd, ax, dt, h)
            div_rc += self._flux_divergence_1d(flux_faces, ax, h)

        return div_rc

    # ── Per-axis face flux ────────────────────────────────────────────────

    def _rc_flux_1d(self, u_star, p, rho, ccd, axis: int, dt: float, h: float):
        """Compute face-normal velocity u_f (RC-corrected) along ``axis``.

        Face i+½ lies between cell-centres i and i+1.
        Returns array of shape with ``shape[axis] = N[axis]+1``
        (N[axis] internal faces + 2 boundary faces, but boundaries are
        handled by wall/periodic BC — set to 0 for walls).
        """
        xp = self.xp
        N_ax = self.grid.N[axis]
        shape = list(u_star.shape)
        shape[axis] = N_ax + 1   # one more face than cell along this axis
        flux = xp.zeros(shape)

        # Cell-centred pressure gradient via CCD
        dp_cell, _ = ccd.differentiate(p, axis)

        def sl(idx):
            s = [slice(None)] * len(u_star.shape)
            s[axis] = idx
            return tuple(s)

        # Internal faces 1 … N_ax  (face k lies between nodes k-1 and k)
        # face 0 is the left wall (no node to the left) → stays 0
        # face N_ax is between nodes N_ax-1 and N_ax (wall node) → computed below
        # Vectorised: L = nodes 0..N_ax-1, R = nodes 1..N_ax
        u_L = u_star[sl(slice(0, N_ax))]
        u_R = u_star[sl(slice(1, N_ax + 1))]
        rho_L = rho[sl(slice(0, N_ax))]
        rho_R = rho[sl(slice(1, N_ax + 1))]
        p_L = p[sl(slice(0, N_ax))]
        p_R = p[sl(slice(1, N_ax + 1))]
        dp_L = dp_cell[sl(slice(0, N_ax))]
        dp_R = dp_cell[sl(slice(1, N_ax + 1))]

        u_bar = 0.5 * (u_L + u_R)
        dp_face = (p_R - p_L) / h
        dp_bar = 0.5 * (dp_L + dp_R)
        inv_rho_harm = 2.0 / (rho_L + rho_R)   # harmonic mean of 1/ρ  (§6.3)

        flux[sl(slice(1, N_ax + 1))] = u_bar - dt * inv_rho_harm * (dp_face - dp_bar)

        # face 0 (left wall): no-penetration → u_f = 0 (already zero)
        # For periodic BC this would need wrapping (not implemented here)
        return flux

    # ── Flux divergence ───────────────────────────────────────────────────

    def _flux_divergence_1d(self, flux_faces, axis: int, h: float):
        """∇·F from face fluxes: (F_{i+1/2} − F_{i−1/2}) / h.

        flux_faces has shape[axis] = N_ax+1 (faces 0..N_ax).
        Face k lies between nodes k-1 and k.
        FVM divergence at node k: (flux[k+1] - flux[k]) / h, k = 0..N_ax-1.
        One trailing zero is appended for the extra boundary node N_ax.
        """
        xp = self.xp
        sl_hi = [slice(None)] * len(flux_faces.shape)
        sl_lo = [slice(None)] * len(flux_faces.shape)
        sl_hi[axis] = slice(1, None)     # faces 1 … N_ax   (right face of node k)
        sl_lo[axis] = slice(0, -1)       # faces 0 … N_ax-1 (left  face of node k)
        # Result has shape[axis] = N_ax; pad one zero at end for boundary node N_ax
        div_nodes = (flux_faces[tuple(sl_hi)] - flux_faces[tuple(sl_lo)]) / h

        shape_pad = list(flux_faces.shape)
        shape_pad[axis] = 1
        pad = xp.zeros(shape_pad)
        return xp.concatenate([div_nodes, pad], axis=axis)
