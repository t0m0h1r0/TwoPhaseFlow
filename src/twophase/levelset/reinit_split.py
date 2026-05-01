"""
Operator-split reinitialization: compression (FE) + diffusion (CN-ADI).

Implements the scheme from §5c (alg:cls_reinit_dccd).
"""

from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple

from .interfaces import IReinitializer
from .heaviside import apply_mass_correction
from .reinit_ops import (
    compute_dtau, dccd_compression_div, cn_diffusion_axis, build_cn_factors,
)
from ..core.boundary import sync_periodic_image_nodes

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class SplitReinitializer(IReinitializer):
    """Operator-split reinitialization: compression (FE) + diffusion (CN-ADI).

    Parameters
    ----------
    backend, grid, ccd, eps, n_steps, bc, eps_d_comp, mass_correction

    Notes
    -----
    **y-flip symmetry (CHK-168, CHK-169)**

    After the CHK-168 ``safe_grad`` floor fix, a single inner iteration
    (``n_steps=1``) is y-flip equivariant to ULP on any grid. However,
    composing ``n_steps=4`` (default) reintroduces O(1e-7) y-flip
    asymmetry per reinit call because the backward-parabolic compression
    term ``∇·[ψ(1-ψ)n̂]`` amplifies y-ODD grid-scale modes by a
    per-iter factor of ~700 (ASM-122-A). This is Lyapunov chaos intrinsic
    to the scheme, not a bug — the same amplification is observed on
    α=1 uniform and α=2 stretched grids.

    **For y-flip-symmetric long-time simulations** (e.g. capillary-wave
    benchmarks with T ≫ τ_reinit), prefer ``method='ridge_eikonal'``
    in the :class:`Reinitializer` facade. Ridge-Eikonal is ULP
    y-flip equivariant after CHK-167 and does not carry the
    Lyapunov chaos issue (no backward-parabolic compression).
    """

    def __init__(self, backend: "Backend", grid, ccd: "CCDSolver",
                 eps: float, n_steps: int = 4, bc: str = 'zero',
                 eps_d_comp: float = 0.05,
                 mass_correction: bool = True):
        self.xp = backend.xp
        self.grid = grid
        self.ccd = ccd
        self.eps = eps
        self.n_steps = n_steps
        self._bc = bc
        self._eps_d_comp = float(eps_d_comp)
        self._mass_correction = mass_correction
        # Use actual minimum spacing per axis for CN diffusion coefficient.
        # On uniform grids min(h[ax]) == L[ax]/N[ax], preserving bit-exactness.
        self._h = [float(grid.h[ax].min()) for ax in range(grid.ndim)]
        self.dtau = compute_dtau(grid, eps)

        self._cn_factors: List[Tuple] = []
        for ax in range(grid.ndim):
            self._cn_factors.append(
                build_cn_factors(grid, eps, self.dtau, ax, backend))

        self._dV = grid.cell_volumes()

    def reinitialize(self, psi):
        xp = self.xp
        # Ensure psi is on the correct device (no-op on CPU).
        q = xp.asarray(psi).copy()
        sync_periodic_image_nodes(q, self._bc)
        dV = self._dV
        M_old = xp.sum(q * dV)

        for _ in range(self.n_steps):
            div_comp = dccd_compression_div(
                xp, q, self.ccd, self.grid, self._bc, self._eps_d_comp,
            )
            q_star = xp.clip(q - self.dtau * div_comp, 0.0, 1.0)
            sync_periodic_image_nodes(q_star, self._bc)

            q_new = q_star
            for ax in range(self.grid.ndim):
                q_new = cn_diffusion_axis(
                    xp, q_new, ax, self.eps, self.dtau,
                    self._h[ax], self._cn_factors[ax],
                )
                sync_periodic_image_nodes(q_new, self._bc)
            q = xp.clip(q_new, 0.0, 1.0)
            sync_periodic_image_nodes(q, self._bc)

        if self._mass_correction:
            q = apply_mass_correction(xp, q, dV, M_old)
            sync_periodic_image_nodes(q, self._bc)

        return q
