"""
FCCD Convection term: −(u·∇)u via FCCDSolver primitives.

Drop-in replacement for ``ConvectionTerm`` ([convection.py](convection.py))
using the face-centered compact scheme of SP-D for 4th-order uniform
spatial accuracy. Two discretisation modes are offered:

    mode='node'  (Option C of SP-D §6)
        4th-order R_4 Hermite face→node reconstructor:
        (∂_xk u_j)_i = 1/2[d_{f_{i-1/2}} + d_{f_{i+1/2}}] − (H/16)(q_{i+1} − q_{i-1})
        multiplied at nodes by u^(k) and summed.  Shape + AB2 compatibility
        identical to ConvectionTerm.

    mode='flux'  (Option B of SP-D §7)
        Conservative single-face-value flux divergence:
        F_f = P_f(u^(k)·u^(j))
        (−(u·∇)u)_j = −Σ_k [F_{f_{i+1/2}} − F_{f_{i-1/2}}]/H_i
        Discretely momentum-conserving. This class implements the conservative
        Option-B path; the paper's skew-symmetric variant is not silently
        substituted.

Shares the FCCDSolver's pre-factored CCD block LU — no extra block solves.
CPU/GPU code path is unified via ``backend.xp``; q-sharing between components
reduces CCD calls from 2*ndim to ndim.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import IConvectionTerm

if TYPE_CHECKING:
    from ..ccd.fccd import FCCDSolver
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from .context import NSComputeContext
    from ..simulation.scheme_build_ctx import ConvectionBuildCtx


class FCCDConvectionTerm(IConvectionTerm):
    """FCCD-based −(u·∇)u convective acceleration.

    Parameters
    ----------
    backend : Backend
    fccd    : FCCDSolver
        Face-centered CCD solver (shares the nodal CCDSolver's LU).
    mode    : {'node', 'flux'}
        Discretisation: see module docstring.

    Notes
    -----
    Signature of :meth:`compute` matches
    :class:`twophase.ns_terms.convection.ConvectionTerm` so AB2 predictor
    and the SimulationBuilder pipeline accept either term transparently.
    """

    scheme_names     = ("fccd_flux", "fccd_nodal")
    _scheme_aliases  = {"fccd": "fccd_flux"}
    _modes = {"fccd_flux": "flux", "fccd_nodal": "node"}

    @classmethod
    def _build(cls, name: str, ctx: "ConvectionBuildCtx") -> "FCCDConvectionTerm":
        return cls(ctx.backend, ctx.fccd, mode=cls._modes[name])

    def __init__(
        self,
        backend: "Backend",
        fccd: "FCCDSolver",
        mode: str = "flux",
    ) -> None:
        if mode not in ("node", "flux"):
            raise ValueError(f"mode must be 'node' or 'flux', got {mode!r}")
        self.xp = backend.xp
        self._fccd = fccd
        self._mode = mode

    def compute(
        self,
        ctx_or_velocity,
        ccd: "CCDSolver | None" = None,
    ) -> List:
        """Return −(u·∇)u as a list of arrays (one per component).

        Supports both new (ctx) and legacy (velocity_components, ccd) signatures.

        Parameters
        ----------
        ctx_or_velocity : NSComputeContext or list
            Either NSComputeContext (new) or velocity_components list (legacy)
        ccd : CCDSolver | None
            Only used with legacy signature (ignored, kept for API parity)

        Returns
        -------
        list of ndim arrays (same shape as inputs).
        """
        # Dispatch based on argument type
        if isinstance(ctx_or_velocity, list):
            # Legacy signature: compute(velocity_components, ccd)
            velocity_components = ctx_or_velocity
        else:
            # New signature: compute(ctx)
            ctx = ctx_or_velocity
            velocity_components = ctx.velocity

        return self._fccd.advection_rhs(velocity_components, mode=self._mode)
