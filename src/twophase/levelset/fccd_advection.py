"""
FCCD level-set advection: ∂_t ψ + u·∇ψ = 0 via FCCDSolver primitives.

Mirror of :class:`DissipativeCCDAdvection` with the inner operator replaced
by FCCD's face-centered scheme. Two modes (SP-D §10):

    mode='node'  (Option C)
        R_4 Hermite reconstructor on ∂_k ψ at nodes; nodal multiplication
        by u^(k) and sum. Drop-in shape-compatible with DissipativeCCDAdvection.

    mode='flux'  (Option B)
        Conservative skew-symmetric face flux divergence; discretely
        volume-preserving for uniform grids with periodic BC.

TVD-RK3 time integration; optional per-stage clamp to keep ψ ∈ [0, 1].
The spectral filter ε_d (DissipativeCCDAdvection default 0.05) is kept as
an optional post-stage smoother for stability with under-resolved
interfaces (SP-D §10); disable when FCCD's natural 4th-order dissipation
is sufficient.

GPU/CPU unified via ``backend.xp``. Mass-correction hook inherited.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import ILevelSetAdvection
from ..time_integration.tvd_rk3 import tvd_rk3
from .heaviside import apply_mass_correction

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.grid import Grid
    from ..ccd.fccd import FCCDSolver
    from ..simulation.scheme_build_ctx import AdvectionBuildCtx


class FCCDLevelSetAdvection(ILevelSetAdvection):
    """Advects ψ using FCCDSolver primitives + TVD-RK3.

    Parameters
    ----------
    backend          : Backend
    grid             : Grid
    fccd             : FCCDSolver (shares CCD LU internally)
    mode             : {'node', 'flux'}
    mass_correction  : bool — Lagrange-multiplier mass renormalisation
                       (same as DissipativeCCDAdvection).

    Notes
    -----
    API matches :class:`DissipativeCCDAdvection.advance`:
        ``advance(psi, velocity_components, dt, clip_bounds=(0.0, 1.0))``.
    """

    scheme_names     = ("fccd_flux", "fccd_nodal")
    _scheme_aliases  = {"fccd": "fccd_flux"}
    _modes = {"fccd_flux": "flux", "fccd_nodal": "node"}

    @classmethod
    def _build(cls, name: str, ctx: "AdvectionBuildCtx") -> "FCCDLevelSetAdvection":
        return cls(ctx.backend, ctx.grid, ctx.fccd, mode=cls._modes[name], mass_correction=False)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        fccd: "FCCDSolver",
        mode: str = "flux",
        mass_correction: bool = False,
    ) -> None:
        if mode not in ("node", "flux"):
            raise ValueError(f"mode must be 'node' or 'flux', got {mode!r}")
        self.xp = backend.xp
        self._grid = grid
        self._fccd = fccd
        self._mode = mode
        self._mass_correction = mass_correction
        self._dV = grid.cell_volumes() if mass_correction else None

    def advance(
        self,
        psi,
        velocity_components: List,
        dt: float,
        clip_bounds=(0.0, 1.0),
    ):
        """Advance ψ by one RK3 step."""
        xp = self.xp
        psi = xp.asarray(psi)
        velocity_components = [xp.asarray(vc) for vc in velocity_components]

        if self._mass_correction:
            M_old = xp.sum(psi * self._dV)

        if clip_bounds is None:
            post_stage = None
        else:
            lo, hi = clip_bounds
            post_stage = lambda q: xp.clip(q, lo, hi)

        q_new = tvd_rk3(
            xp, psi, dt,
            lambda q: self._rhs(q, velocity_components),
            post_stage=post_stage,
        )

        if self._mass_correction:
            q_new = apply_mass_correction(xp, q_new, self._dV, M_old)

        return q_new

    # ── RHS: −u·∇ψ via FCCD ─────────────────────────────────────────────

    def _rhs(self, psi, vel):
        """−u·∇ψ using FCCDSolver (Option C or B per ``self._mode``)."""
        return self._fccd.advection_rhs(
            vel, scalar=psi, mode=self._mode,
        )[0]
