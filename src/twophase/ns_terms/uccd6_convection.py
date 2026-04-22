"""UCCD6 Convection term for NS momentum: skew-symmetric CCD + selective hyperviscosity.

Implements the NS-system extension of UCCD6 (WIKI-X-023, SP-H):

    [−(u·∇)u]_j  +  σ · max|u_k| · h_k^7 · (−D2^CCD)^4 u_j   (axis-wise)

- Advection part   : standard −u_k · (D1^CCD u_j)_k, matches ``ConvectionTerm``.
- Hyperviscosity   : positive semi-definite, O(h^7) subdominant dissipation on
  well-resolved modes, ~σ·max|u|/h at Nyquist. Analogous to a spectral LES
  filter embedded in the discrete operator.

Shares the existing nodal ``CCDSolver`` — no additional LU factorisation. All
array operations stay on ``backend.xp`` (no host round-trip), so CPU and GPU
paths are identical.

References
----------
- WIKI-X-023 (``docs/wiki/cross-domain/WIKI-X-023.md``): NS-level UCCD6 design.
- WIKI-T-062 (``docs/wiki/theory/WIKI-T-062.md``): 1-D UCCD6 operator.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import IConvectionTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import ConvectionBuildCtx


class UCCD6ConvectionTerm(IConvectionTerm):
    """UCCD6-stabilised −(u·∇)u convective acceleration.

    Parameters
    ----------
    backend : Backend
    grid : Grid
    ccd : CCDSolver
        Shared nodal CCDSolver (reuses the pre-factored block LU).
    sigma : float, default ``1.0e-3``
        Hyperviscosity coefficient. Stability limit under TVD-RK3 is
        σ ≲ √3 · h / (8500 · max|u|); choose σ = 1e-3 for typical
        CFL ~ 0.1 at N = 128 (well inside the safe region).

    Notes
    -----
    Signature of :meth:`compute` matches
    :class:`twophase.ns_terms.convection.ConvectionTerm` — drop-in compatible
    with the AB2 predictor and both simulation pipelines.
    """

    scheme_names = ("uccd6",)

    @classmethod
    def _build(cls, name: str, ctx: "ConvectionBuildCtx") -> "UCCD6ConvectionTerm":
        return cls(ctx.backend, ctx.grid, ctx.ccd, sigma=ctx.uccd6_sigma)

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        ccd: "CCDSolver",
        sigma: float = 1.0e-3,
    ) -> None:
        if sigma <= 0.0:
            raise ValueError(f"sigma must be > 0, got {sigma}")
        self.xp = backend.xp
        self._ccd = ccd
        self._grid = grid
        self._sigma = float(sigma)
        self._h7 = [
            (float(grid.L[ax]) / int(grid.N[ax])) ** 7
            for ax in range(grid.ndim)
        ]

    def compute(
        self,
        ctx_or_velocity,
        ccd: "CCDSolver | None" = None,
    ) -> List:
        """Return −(u·∇)u − σ·|u|·h^7·(−D2)^4 u per component.

        Parameters
        ----------
        ctx_or_velocity : NSComputeContext or list
        ccd : CCDSolver, optional (legacy signature)

        Returns
        -------
        list of ndim arrays, same shape as input velocity components.
        """
        if isinstance(ctx_or_velocity, list):
            velocity_components = ctx_or_velocity
        else:
            velocity_components = ctx_or_velocity.velocity

        xp = self.xp
        ndim = len(velocity_components)
        ccd_op = self._ccd
        result = []

        for j in range(ndim):
            u_j = velocity_components[j]
            acc = xp.zeros_like(u_j)
            for k in range(ndim):
                u_k = velocity_components[k]
                d1, d2 = ccd_op.differentiate(u_j, k)
                acc = acc - u_k * d1
                _, d4 = ccd_op.differentiate(d2, k)
                _, d6 = ccd_op.differentiate(d4, k)
                _, d8 = ccd_op.differentiate(d6, k)
                u_ref = xp.abs(u_k).max()  # device-side 0-d scalar
                coeff = self._sigma * self._h7[k]
                acc = acc - coeff * (u_ref * d8)
            result.append(acc)

        return result
