"""
Computational grid.

Implements Section 5 of the paper (interface-fitted / uniform collocated grid).

For the uniform case (``alpha_grid = 1.0``) the grid spacing is simply
``h[ax] = L[ax] / N[ax]`` and node coordinates are
``x[ax] = linspace(0, L[ax], N[ax]+1)``.

For the interface-fitted case (``alpha_grid > 1.0``) a smooth grid density
function ω(φ) = exp(−α·(φ/ε)²) concentrates nodes near the interface.
The physical coordinate is obtained by integrating a scaled spacing field
and renormalising to the domain length.  A minimum cell-width floor
``dx_min_floor`` prevents near-zero spacings that would make the CCD
system ill-conditioned (Known Issue #3 in the architecture document).

Key equations:
    Uniform:  Δx = L / N                                         (§5 baseline)
    Grid density: ω(φ) = exp(−α·(φ/ε)²)                         (§5 Eq.~grid)
    Metric:   J = ∂ξ/∂x  (used by CCD for non-uniform spacing)  (§4.9)
"""

from __future__ import annotations
import numpy as np
from typing import TYPE_CHECKING, Tuple

from .metrics import compute_metrics

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import GridConfig


class Grid:
    """Collocated Cartesian grid (2-D or 3-D).

    Attributes
    ----------
    ndim : int
    N : tuple[int, ...]  — number of cells per axis (nodes = N+1)
    L : tuple[float, ...] — domain lengths
    h : list[numpy.ndarray] — 1-D spacing arrays, shape (N[ax]+1,) each
    coords : list[numpy.ndarray] — node coordinate vectors, shape (N[ax]+1,)
    shape : tuple[int, ...] — (N[0]+1, N[1]+1[, N[2]+1])
    J : list[numpy.ndarray] — metric ∂ξ/∂x per axis (= 1/h for uniform)
    dJ_dxi : list[numpy.ndarray] — gradient of metric in ξ-space
    """

    def __init__(self, grid_config: "GridConfig", backend: "Backend"):
        self._gc = grid_config
        self.backend = backend
        self.xp = backend.xp

        self.ndim = grid_config.ndim
        self.N = tuple(grid_config.N)
        self.L = tuple(grid_config.L)

        # Build uniform grid (interface-fitted update happens separately)
        self.coords: list[np.ndarray] = []
        self.h: list[np.ndarray] = []
        for ax in range(self.ndim):
            c = np.linspace(0.0, grid_config.L[ax], grid_config.N[ax] + 1)
            self.coords.append(c)
            # h[ax] is length-N[ax] spacing (between consecutive nodes)
            # We store per-node spacing (averaged from both sides) for metrics
            dx = np.full(grid_config.N[ax] + 1, grid_config.L[ax] / grid_config.N[ax])
            self.h.append(dx)

        self.shape: tuple = tuple(n + 1 for n in self.N)

        # Metrics (identity for uniform grid)
        self._build_metrics()

    # ── Public interface ──────────────────────────────────────────────────

    def meshgrid(self) -> Tuple:
        """Return open meshgrid arrays in physical coordinates.

        2-D: returns (X, Y) each shape ``(N[0]+1, N[1]+1)``.
        3-D: returns (X, Y, Z) each shape ``(N[0]+1, N[1]+1, N[2]+1)``.

        Output arrays live on the backend device: NumPy on CPU backend,
        CuPy on GPU backend.  ``self.coords`` stays on host for the
        metric-building path; conversion happens only at this boundary.
        """
        xp = self.xp
        return xp.meshgrid(*[xp.asarray(c) for c in self.coords], indexing="ij")

    def update_from_levelset(
        self,
        psi_data: np.ndarray,
        eps: float = 0.0,
        ccd=None,
    ) -> None:
        """Rebuild interface-fitted grid given the Heaviside field ψ.

        Only active when ``grid_config.alpha_grid > 1.0``.

        Density function (ψ-based, replacing Gaussian δ*(φ)):
            indicator(ψ) = 4ψ(1−ψ) ∈ [0, 1]  — peaks at ψ=0.5, zero in bulk
            ω = 1 + (α−1) · max_j indicator(ψ_{·,j})

        This eliminates the need for signed-distance φ and the ε_g parameter.
        Bell width of ψ(1−ψ) ≈ 3.5ε (sech² profile), comparable to the former
        Gaussian δ*(ε_g=2ε) width of ≈ 3.3ε.

        Metric coefficients J = ∂ξ/∂x and ∂J/∂ξ are computed with CCD (O(h⁶))
        when ``ccd`` is provided.  Falls back to O(h²) central differences
        when ``ccd`` is None.

        Parameters
        ----------
        psi_data : array of shape ``self.shape`` — Heaviside field ψ ∈ [0, 1]
        eps      : unused (kept for call-site compatibility)
        ccd      : CCDSolver instance for O(h⁶) metric evaluation (optional)
        """
        alpha = self._gc.alpha_grid
        if alpha <= 1.0:
            return  # uniform grid — nothing to do

        dx_floor = self._gc.dx_min_floor

        for ax in range(self.ndim):
            # 1-D marginal: max ψ(1−ψ) over other axes → interface indicator
            axes_other = tuple(a for a in range(self.ndim) if a != ax)
            psi_host = np.asarray(self.backend.to_host(psi_data))
            indicator = psi_host * (1.0 - psi_host)         # peaks 0.25 at ψ=0.5
            indicator_1d = np.max(indicator, axis=axes_other) / 0.25  # [0, 1]

            omega = 1.0 + (alpha - 1.0) * indicator_1d      # ω ∈ [1, α]

            # Node target widths proportional to 1/ω; enforce minimum cell width
            node_w = np.maximum(1.0 / omega, dx_floor)  # (N+1,) node weights

            # Cell spacings: average adjacent node weights → symmetric for symmetric ω.
            # Using node_w[:-1] alone would drop the last node and break symmetry
            # (see §6 格子点生成アルゴリズム bug-fix note).
            dx_cells = 0.5 * (node_w[:-1] + node_w[1:])   # (N,) cell widths

            # Normalise so cumulative sum spans exactly [0, L[ax]]
            dx_cells = dx_cells * (self._gc.L[ax] / dx_cells.sum())

            # Cumulative integration: ステップ3–4 (§6 格子点生成アルゴリズム)
            coords_ax = np.zeros(self._gc.N[ax] + 1)
            coords_ax[1:] = np.cumsum(dx_cells)   # sum = L → no rescale needed

            self.coords[ax] = coords_ax
            # Per-node spacing (average of left and right cell widths)
            cell_dx = np.diff(coords_ax)
            node_dx = np.empty(self._gc.N[ax] + 1)
            node_dx[0] = cell_dx[0]
            node_dx[-1] = cell_dx[-1]
            node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
            self.h[ax] = node_dx

        self._build_metrics(ccd=ccd)

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_metrics(self, ccd=None) -> None:
        """Compute CCD metrics J = dxi/dx and dJ/dxi for each axis.

        Delegates to core.metrics.compute_metrics() (SRP extraction).
        """
        self.J, self.dJ_dxi = compute_metrics(
            self.coords, self.h, self.N, self.ndim, self.uniform, ccd,
        )

    # ── Convenience ──────────────────────────────────────────────────────

    @property
    def uniform(self) -> bool:
        """True when the grid is uniform (alpha_grid ≤ 1)."""
        return self._gc.alpha_grid <= 1.0

    def cell_volume(self) -> float:
        """Approximate uniform cell volume (product of mean spacings)."""
        return float(np.prod([L / N for L, N in zip(self.L, self.N)]))

    def cell_volumes(self) -> np.ndarray:
        """Per-node control volumes, shape ``self.shape``."""
        vol = self.h[0].copy()
        for ax in range(1, self.ndim):
            vol = np.expand_dims(vol, axis=ax) * self.h[ax]
        return vol

    def __repr__(self) -> str:
        h_str = " × ".join(
            f"{self.L[ax]/self.N[ax]:.4g}" for ax in range(self.ndim)
        )
        return f"Grid(ndim={self.ndim}, N={self.N}, L={self.L}, h≈{h_str})"
