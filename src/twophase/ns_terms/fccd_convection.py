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
        Conservative / skew-symmetric face flux divergence:
        F_f = 1/2[u^(k)_f · (∂_k u^(j))_f + (u^(k)·u^(j))_f]
        (−(u·∇)u)_j = −Σ_k [F_{f_{i+1/2}} − F_{f_{i-1/2}}]/H_i
        Discretely momentum-conserving; aliasing-suppressed. Required for
        the Option-B BF-preservation theorem when paired with face ∇p and CSF.

Shares the FCCDSolver's pre-factored CCD block LU — no extra block solves.
CPU/GPU code path is unified via ``backend.xp``; q-sharing between components
reduces CCD calls from 2*ndim to ndim.
"""

from __future__ import annotations
from typing import List, TYPE_CHECKING

from .interfaces import INSTerm

if TYPE_CHECKING:
    from ..ccd.fccd import FCCDSolver
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


class FCCDConvectionTerm(INSTerm):
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
        velocity_components: List,
        ccd: "CCDSolver | None" = None,
    ) -> List:
        """Return −(u·∇)u as a list of arrays (one per component).

        Parameters
        ----------
        velocity_components : list of ``ndim`` node-arrays with shape
            ``grid.shape``.
        ccd : CCDSolver | None
            Ignored; FCCDSolver carries its own internally-shared CCD.
            Accepted for API parity with ``ConvectionTerm.compute``.

        Returns
        -------
        list of ndim arrays (same shape as inputs).
        """
        return self._fccd.advection_rhs(velocity_components, mode=self._mode)
