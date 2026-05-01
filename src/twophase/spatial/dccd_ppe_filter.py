"""
DCCD PPE filter: explicit 3-point checkerboard suppression for PPE RHS.

Implements section 7 (sec:dccd_decoupling, Eq. dccd_filter_physical
and Eq. dccd_ppe_rhs) of the paper.

On a collocated grid, the 2*Delta_x checkerboard mode is invisible to
both central differences and CCD (H(pi) -> 0).  The standard remedy is
Rhie-Chow face-velocity interpolation.

When GFM is used (sec:gfm), CSF volume forces are removed from the
predictor, making Rhie-Chow's Balanced-Force extension unnecessary.
Instead, an explicit 3-point filter with epsilon_d = 1/4 is applied to
the predicted velocity u* before computing the CCD divergence for the
PPE RHS (Eq. dccd_ppe_rhs):

    u_tilde_i = u_i/2 + (u_{i-1} + u_{i+1})/4     (Eq. dccd_filter_physical)

This zeroes the 2*Delta_x Fourier mode exactly:

    H(pi; 1/4) = 1 - 4*(1/4)*sin^2(pi/2) = 0      (Eq. dccd_eps_checkerboard)

The filtered velocity is then used to compute the PPE RHS:

    q_h = (1/dt) * (D_x^(1) u_tilde* + D_y^(1) v_tilde*)  (Eq. dccd_ppe_rhs)

This filter is INDEPENDENT of the DCCD advection filter (epsilon_d = 0.05
in sec:dccd_filter_theory); it is a PPE-specific checkerboard removal step.

Symbol mapping (paper -> Python):
    u_tilde   -> vel_filtered    filtered velocity components
    D_x^(1)   -> ccd.differentiate(., ax)  CCD 1st derivative
    epsilon_d -> EPS_D = 0.25    checkerboard suppression strength
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from ..core.boundary import is_periodic_axis

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

# epsilon_d = 1/4 for complete 2*Delta_x mode removal (Eq. dccd_eps_checkerboard)
# Filter weights: center = 1 - 2*EPS_D = 0.5, neighbour = EPS_D = 0.25
EPS_D: float = 0.25


class DCCDPPEFilter:
    """Apply DCCD 3-point filter to velocity and compute CCD divergence.

    Parameters
    ----------
    backend : Backend
    grid    : Grid
    ccd     : CCDSolver — CCD D^{(1)} operator
    bc_type : str — 'wall' or 'periodic'
    """

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
        bc_type: str = "wall",
    ):
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.ccd = ccd
        self.bc_type = bc_type

    def filter_velocity(self, vel: List) -> List:
        """Apply epsilon_d=1/4 3-point filter to each velocity component.

        Implements Eq. dccd_filter_physical:
            u_tilde_i = u_i/2 + (u_{i-1} + u_{i+1})/4

        The filter is applied independently along EACH spatial axis for
        each velocity component, i.e. 1-D filtering per axis direction.

        Parameters
        ----------
        vel : list of arrays, one per velocity component

        Returns
        -------
        vel_filtered : list of filtered arrays
        """
        xp = self.xp
        filtered = []

        for comp in range(len(vel)):
            u = vel[comp]
            u_filt = xp.copy(u)

            # Apply 1-D filter along each spatial axis
            for ax in range(self.ndim):
                u_filt = self._filter_1d(u_filt, ax)

            filtered.append(u_filt)

        return filtered

    def _filter_1d(self, u, ax: int):
        """Apply 3-point filter along axis ax.

        u_tilde_i = (1/2)*u_i + (1/4)*(u_{i-1} + u_{i+1})

        Boundary treatment:
          - wall: Neumann (ghost = interior value) -> boundary nodes use
            one-sided stencil equivalent
          - periodic: wrap-around indexing
        """
        xp = self.xp
        N_ax = self.grid.N[ax]
        result = xp.copy(u)

        # Interior slices
        sl_c = [slice(None)] * self.ndim  # center: i
        sl_m = [slice(None)] * self.ndim  # minus:  i-1
        sl_p = [slice(None)] * self.ndim  # plus:   i+1

        sl_c[ax] = slice(1, N_ax)
        sl_m[ax] = slice(0, N_ax - 1)
        sl_p[ax] = slice(2, N_ax + 1)
        sl_c = tuple(sl_c)
        sl_m = tuple(sl_m)
        sl_p = tuple(sl_p)

        # Interior: u_tilde_i = (1-2*EPS_D)*u_i + EPS_D*(u_{i-1} + u_{i+1})
        w_c = 1.0 - 2.0 * EPS_D   # center weight = 0.5
        w_n = EPS_D               # neighbour weight = 0.25
        result[sl_c] = w_c * u[sl_c] + w_n * (u[sl_m] + u[sl_p])

        if is_periodic_axis(self.bc_type, ax, self.ndim):
            # Periodic wrap: first node uses last interior, last uses first
            sl_first = [slice(None)] * self.ndim
            sl_last = [slice(None)] * self.ndim
            sl_second = [slice(None)] * self.ndim
            sl_penult = [slice(None)] * self.ndim

            sl_first[ax] = 0
            sl_last[ax] = N_ax
            sl_second[ax] = 1
            sl_penult[ax] = N_ax - 1
            sl_first = tuple(sl_first)
            sl_last = tuple(sl_last)
            sl_second = tuple(sl_second)
            sl_penult = tuple(sl_penult)

            result[sl_first] = w_c * u[sl_first] + w_n * (u[sl_penult] + u[sl_second])
            result[sl_last] = result[sl_first]  # periodic image
        else:
            # Wall BC (Neumann ghost: u_{-1} = u_0, u_{N+1} = u_N)
            # Boundary node 0: u_tilde_0 = w_c*u_0 + w_n*(u_0 + u_1) = (w_c+w_n)*u_0 + w_n*u_1
            # Boundary node N: u_tilde_N = w_c*u_N + w_n*(u_{N-1} + u_N) = w_n*u_{N-1} + (w_c+w_n)*u_N
            # Note: with no-slip BC (u_0=0), u_tilde_0 = w_n*u_1 != 0.
            # This is acceptable: the CCD divergence + PPE Neumann BC
            # correctly handle the non-zero boundary contribution.
            sl_0 = [slice(None)] * self.ndim
            sl_1 = [slice(None)] * self.ndim
            sl_N = [slice(None)] * self.ndim
            sl_Nm1 = [slice(None)] * self.ndim

            sl_0[ax] = 0
            sl_1[ax] = 1
            sl_N[ax] = N_ax
            sl_Nm1[ax] = N_ax - 1
            sl_0 = tuple(sl_0)
            sl_1 = tuple(sl_1)
            sl_N = tuple(sl_N)
            sl_Nm1 = tuple(sl_Nm1)

            result[sl_0] = (w_c + w_n) * u[sl_0] + w_n * u[sl_1]
            result[sl_N] = w_n * u[sl_Nm1] + (w_c + w_n) * u[sl_N]

        return result

    def compute_filtered_divergence(
        self, vel: List, crc_dccd: bool = False,
    ) -> "array":
        """Filter velocity and compute CCD divergence.

        Implements Eq. dccd_ppe_rhs:
            q_h = D_x^(1) u_tilde* + D_y^(1) v_tilde*

        When ``crc_dccd=True``, applies C/RC-DCCD correction to reduce
        the DCCD filter dissipation error from O(ε_d h²) to O(ε_d h⁴)
        using the D²_CCD output that is already returned by differentiate()
        at zero extra CCD cost:

            q_h* = q_h − ε_d h² Σ_ax FD_ax(D²_CCD(ũ*_ax))

        Note: the 1/dt factor is NOT included; caller must apply it.

        Parameters
        ----------
        vel       : list of velocity component arrays (u*, v*, ...)
        crc_dccd  : bool — if True, apply C/RC-DCCD correction (default False)

        Returns
        -------
        div : array, shape ``grid.shape`` — divergence of filtered velocity
        """
        xp = self.xp
        vel_filt = self.filter_velocity(vel)

        div = xp.zeros_like(vel_filt[0])
        for ax in range(self.ndim):
            du_dax, d2u_dax = self.ccd.differentiate(vel_filt[ax], ax)
            div = div + du_dax

            if crc_dccd:
                # C/RC-DCCD: subtract ε_d h² · ∂/∂x_ax(D²_CCD(ũ*_ax))
                # using central FD of the already-computed d2.
                h = float(self.grid.L[ax] / self.grid.N[ax])
                d2_np = xp.asarray(d2u_dax)
                N_ax = self.grid.N[ax]

                def sl(idx, _ax=ax):
                    s = [slice(None)] * self.ndim
                    s[_ax] = idx
                    return tuple(s)

                if is_periodic_axis(self.bc_type, ax, self.ndim):
                    # Central FD with periodic wrap
                    d2_ip1 = xp.roll(d2_np, -1, axis=ax)
                    d2_im1 = xp.roll(d2_np,  1, axis=ax)
                else:
                    # Central FD; one-sided at boundaries
                    d2_ip1 = xp.zeros_like(d2_np)
                    d2_im1 = xp.zeros_like(d2_np)
                    inner = [slice(None)] * self.ndim
                    inner[ax] = slice(1, N_ax)
                    d2_ip1[tuple(inner)] = d2_np[sl(slice(2, N_ax + 1))]
                    d2_im1[tuple(inner)] = d2_np[sl(slice(0, N_ax - 1))]
                    # Boundaries: one-sided
                    d2_ip1[sl(0)] = d2_np[sl(1)]
                    d2_im1[sl(0)] = d2_np[sl(0)]
                    d2_ip1[sl(N_ax)] = d2_np[sl(N_ax)]
                    d2_im1[sl(N_ax)] = d2_np[sl(N_ax - 1)]

                dd2_dx = (d2_ip1 - d2_im1) / (2.0 * h)
                div = div - EPS_D * h**2 * dd2_dx

        return div
