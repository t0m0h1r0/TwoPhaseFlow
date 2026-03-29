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

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver", bc_type: str = "wall"):
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.ccd = ccd
        self.bc_type = bc_type

    def face_velocity_divergence(
        self,
        vel_star: List,
        p: Any,
        rho: Any,
        dt: float,
        kappa: Any = None,
        psi: Any = None,
        we: float = None,
    ) -> Any:
        """Compute ∇·u_RC (the Rhie-Chow face-velocity divergence).

        Parameters
        ----------
        vel_star : list of u* arrays
        p        : current pressure field (used for RC correction)
        rho      : density field
        dt       : time step
        kappa    : curvature field (optional; enables Balanced-Force RC extension)
        psi      : CLS field ψ   (optional; enables Balanced-Force RC extension)
        we       : Weber number  (optional; enables Balanced-Force RC extension)

        When ``kappa``, ``psi``, and ``we`` are all provided the face velocity
        uses the Balanced-Force extended form (eq:rc-face-balanced, §7.3.2):

            u_f = ū_f − Δt (1/ρ)_f^harm
                  [(∇p)_f − (∇p̄)_f − ((f_σ)_f − (f̄_σ)_f)]

        where (f_σ)_f is the face surface-tension force and (f̄_σ)_f is the
        arithmetic average of CCD cell-centred surface-tension forces.
        This eliminates the O(h²) Balanced-Force mismatch in the Rhie-Chow
        bracket at equilibrium, reducing parasitic-current drivers for
        surface-tension-dominated problems (We ≪ 1).

        Returns
        -------
        div_rc : divergence array, shape ``grid.shape``
        """
        xp = self.xp
        ndim = self.ndim
        ccd = self.ccd
        div_rc = xp.zeros_like(vel_star[0])

        bf_enabled = (kappa is not None) and (psi is not None) and (we is not None)

        for ax in range(ndim):
            h = float(self.grid.L[ax] / self.grid.N[ax])
            flux_faces = self._rc_flux_1d(
                vel_star[ax], p, rho, ccd, ax, dt, h,
                kappa=kappa if bf_enabled else None,
                psi=psi if bf_enabled else None,
                we=we if bf_enabled else None,
            )
            div_rc += self._flux_divergence_1d(flux_faces, ax, h, self.bc_type)

        return div_rc

    # ── Per-axis face flux ────────────────────────────────────────────────

    def _rc_flux_1d(
        self, u_star, p, rho, ccd, axis: int, dt: float, h: float,
        kappa=None, psi=None, we=None,
    ):
        """Compute face-normal velocity u_f (RC-corrected) along ``axis``.

        Face i+½ lies between cell-centres i and i+1.
        Returns array of shape with ``shape[axis] = N[axis]+1``
        (N[axis] internal faces + 2 boundary faces, but boundaries are
        handled by wall/periodic BC — set to 0 for walls).

        When ``kappa``, ``psi``, ``we`` are provided the Balanced-Force
        extension (eq:rc-face-balanced, §7.3.2) is applied: the surface-
        tension correction term is subtracted from the RC bracket so that
        the bracket vanishes exactly at mechanical equilibrium.
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

        # Wall BC: CCD Neumann sets dp_cell[0]=0 and dp_cell[N]=0 (∂p/∂n=0).
        # Using these zero values in dp_bar at wall-adjacent faces gives an
        # O(1) spurious RC correction (dp_face - dp_bar ≠ 0 for any non-trivial p).
        # Fix: replace boundary-node dp_cell with one-sided differences so that
        # dp_face - dp_bar = O(h) for smooth p — consistent with interior faces O(h²).
        if self.bc_type == 'wall':
            dp_cell = xp.copy(dp_cell)
            # Left wall: node 0 → forward one-sided  (p[1]−p[0])/h
            dp_cell[sl(0)] = (p[sl(1)] - p[sl(0)]) / h
            # Right wall: node N_ax → backward one-sided  (p[N]−p[N−1])/h
            dp_cell[sl(N_ax)] = (p[sl(N_ax)] - p[sl(N_ax - 1)]) / h

        # Balanced-Force RC extension (eq:rc-face-balanced, §7.3.2):
        # Cell-centred surface-tension force via CCD — same operator as pressure
        # gradient to ensure cancellation at equilibrium.
        bf_enabled = (kappa is not None) and (psi is not None) and (we is not None)
        if bf_enabled:
            dpsi_cell, _ = ccd.differentiate(psi, axis)
            f_sigma_cell = kappa * dpsi_cell / we   # (κ/We) D^(1)_CCD ψ

            if self.bc_type == 'wall':
                # Apply same boundary fix as dp_cell: replace CCD boundary values
                # with one-sided differences so the bracket correction is O(h).
                f_sigma_cell = xp.copy(f_sigma_cell)
                kappa_0 = kappa[sl(0)]
                kappa_N = kappa[sl(N_ax)]
                f_sigma_cell[sl(0)] = kappa_0 * (psi[sl(1)] - psi[sl(0)]) / (h * we)
                f_sigma_cell[sl(N_ax)] = kappa_N * (psi[sl(N_ax)] - psi[sl(N_ax - 1)]) / (h * we)

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

        if bf_enabled:
            # Face surface-tension force: κ_f = arith. mean, direct diff for ψ
            kappa_L = kappa[sl(slice(0, N_ax))]
            kappa_R = kappa[sl(slice(1, N_ax + 1))]
            psi_L   = psi[sl(slice(0, N_ax))]
            psi_R   = psi[sl(slice(1, N_ax + 1))]
            fs_L    = f_sigma_cell[sl(slice(0, N_ax))]
            fs_R    = f_sigma_cell[sl(slice(1, N_ax + 1))]

            kappa_face   = 0.5 * (kappa_L + kappa_R)
            f_sigma_face = kappa_face * (psi_R - psi_L) / (h * we)   # direct diff
            f_sigma_bar  = 0.5 * (fs_L + fs_R)                        # CCD mean

            rc_bracket = (dp_face - dp_bar) - (f_sigma_face - f_sigma_bar)
        else:
            rc_bracket = dp_face - dp_bar

        flux[sl(slice(1, N_ax + 1))] = u_bar - dt * inv_rho_harm * rc_bracket

        # face 0: left boundary
        if self.bc_type == 'periodic':
            # Periodic wrap: left node = N_ax (last node), right node = 0
            u_L0 = u_star[sl(N_ax)]
            u_R0 = u_star[sl(0)]
            rho_L0 = rho[sl(N_ax)]
            rho_R0 = rho[sl(0)]
            p_L0 = p[sl(N_ax)]
            p_R0 = p[sl(0)]
            dp_L0 = dp_cell[sl(N_ax)]
            dp_R0 = dp_cell[sl(0)]
            u_bar_0 = 0.5 * (u_L0 + u_R0)
            dp_face_0 = (p_R0 - p_L0) / h
            dp_bar_0 = 0.5 * (dp_L0 + dp_R0)
            inv_rho_harm_0 = 2.0 / (rho_L0 + rho_R0)

            if bf_enabled:
                kappa_L0    = kappa[sl(N_ax)]
                kappa_R0    = kappa[sl(0)]
                psi_L0      = psi[sl(N_ax)]
                psi_R0      = psi[sl(0)]
                fs_L0       = f_sigma_cell[sl(N_ax)]
                fs_R0       = f_sigma_cell[sl(0)]
                kappa_face0  = 0.5 * (kappa_L0 + kappa_R0)
                f_sigma_face0 = kappa_face0 * (psi_R0 - psi_L0) / (h * we)
                f_sigma_bar0  = 0.5 * (fs_L0 + fs_R0)
                rc_bracket_0  = (dp_face_0 - dp_bar_0) - (f_sigma_face0 - f_sigma_bar0)
            else:
                rc_bracket_0 = dp_face_0 - dp_bar_0

            flux[sl(0)] = u_bar_0 - dt * inv_rho_harm_0 * rc_bracket_0
        # else: wall BC — face 0 stays 0 (no-penetration, already initialised)
        return flux

    # ── Flux divergence ───────────────────────────────────────────────────

    def _flux_divergence_1d(self, flux_faces, axis: int, h: float, bc_type: str = "wall"):
        """∇·F from face fluxes: (F_{i+1/2} − F_{i−1/2}) / h.

        flux_faces has shape[axis] = N_ax+1 (faces 0..N_ax).
        Face k lies between nodes k-1 and k.
        FVM divergence at node k: (flux[k+1] - flux[k]) / h, k = 0..N_ax-1.

        Wall BC:     node N_ax divergence padded to 0 (boundary node, no-penetration).
        Periodic BC: node N_ax divergence = (flux[0] - flux[N_ax]) / h
                     (face 0 is the periodic wrap-around face).
        """
        xp = self.xp
        sl_hi = [slice(None)] * len(flux_faces.shape)
        sl_lo = [slice(None)] * len(flux_faces.shape)
        sl_hi[axis] = slice(1, None)     # faces 1 … N_ax   (right face of node k)
        sl_lo[axis] = slice(0, -1)       # faces 0 … N_ax-1 (left  face of node k)
        # Divergence at nodes 0 … N_ax-1
        div_nodes = (flux_faces[tuple(sl_hi)] - flux_faces[tuple(sl_lo)]) / h

        if bc_type == 'periodic':
            # Node N_ax: right face = face 0 (periodic wrap), left face = face N_ax
            sl_f0 = [slice(None)] * len(flux_faces.shape)
            sl_fN = [slice(None)] * len(flux_faces.shape)
            sl_f0[axis] = slice(0, 1)   # face 0
            sl_fN[axis] = slice(-1, None)  # face N_ax
            div_Nax = (flux_faces[tuple(sl_f0)] - flux_faces[tuple(sl_fN)]) / h
            return xp.concatenate([div_nodes, div_Nax], axis=axis)
        else:
            # Right-wall node N_ax: the wall boundary face (face N_ax+1) is not
            # stored in the flux array but is implicitly 0 (no-penetration).
            # FVM divergence: div[N_ax] = (face[N_ax+1] - face[N_ax]) / h
            #                           = (0 - flux[N_ax]) / h
            #                           = -flux[N_ax] / h
            # Padding with 0 (treating flux[N_ax] as a wall face) was incorrect;
            # flux[N_ax] is an interior face between nodes N_ax-1 and N_ax.
            sl_last = [slice(None)] * len(flux_faces.shape)
            sl_last[axis] = slice(-1, None)   # face N_ax
            div_Nax = -flux_faces[tuple(sl_last)] / h
            return xp.concatenate([div_nodes, div_Nax], axis=axis)
