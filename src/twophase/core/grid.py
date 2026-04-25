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
import math
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
        self._cell_volumes_cache = None

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
        eps: float,
        ccd=None,
    ) -> None:
        """Rebuild interface-fitted grid given the Heaviside field ψ.

        Only active when ``grid_config.alpha_grid > 1.0``.

        Internally converts ψ → φ via logit inversion, then applies the
        paper's Gaussian grid density (§6 eq:grid_delta):
            δ*(φ) = exp(−φ²/ε_g²) / (ε_g√π),  ε_g = eps_g_factor × ε
            ω = 1 + (α−1) · δ*(φ̄)

        Parameters
        ----------
        psi_data : array — Heaviside field ψ ∈ [0, 1]
        eps      : interface half-width ε
        ccd      : CCDSolver instance for O(h⁶) metric evaluation (optional)
        """
        from ..levelset.heaviside import invert_heaviside

        alpha = self._gc.alpha_grid
        if alpha <= 1.0:
            return  # uniform grid — nothing to do

        xp = self.backend.xp

        dx_floor = self._gc.dx_min_floor
        # eps_g: ξ空間セル数指定時は軸ごとに L[ax]/N[ax] ベース (WIKI-T-039 fix)
        eps_g_cells = self._gc.eps_g_cells
        eps_g_default = self._gc.eps_g_factor * eps if eps_g_cells is None else None

        # ψ → φ (logit inversion) on the active backend. We only materialise
        # the final 1-D per-axis coordinates on host for metric construction.
        phi = invert_heaviside(xp, xp.asarray(psi_data), eps)

        for ax in range(self.ndim):
            if eps_g_cells is not None:
                h_uniform = self._gc.L[ax] / self._gc.N[ax]
                eps_g = eps_g_cells * h_uniform
            else:
                eps_g = eps_g_default

            # 1-D marginal: min |φ| over other axes (§6 φ̄^x_i = min_j |φ_{i,j}|)
            axes_other = tuple(a for a in range(self.ndim) if a != ax)
            phi_1d = xp.min(xp.abs(phi), axis=axes_other)

            # §6 eq:grid_delta: bounded Gaussian indicator ∈ [0, 1]
            # NOTE: ディラックデルタ正規化因子 1/(ε_g√π) は除去する.
            # 正規化すると ピーク = 1/(ε_g√π) >> 1 となり ω >> α になる (unbounded bug).
            indicator_1d = xp.exp(-(phi_1d ** 2) / (eps_g ** 2))

            omega = 1.0 + (alpha - 1.0) * indicator_1d      # ω ∈ [1, α]

            # Node target widths proportional to 1/ω; enforce minimum cell width
            node_w = xp.maximum(1.0 / omega, dx_floor)  # (N+1,) node weights

            # Cell spacings: average adjacent node weights → symmetric for symmetric ω.
            # Using node_w[:-1] alone would drop the last node and break symmetry
            # (see §6 格子点生成アルゴリズム bug-fix note).
            dx_cells = 0.5 * (node_w[:-1] + node_w[1:])   # (N,) cell widths

            # Normalise so cumulative sum spans exactly [0, L[ax]]
            dx_cells = dx_cells * (self._gc.L[ax] / dx_cells.sum())

            # Cumulative integration: ステップ3–4 (§6 格子点生成アルゴリズム)
            coords_ax = xp.zeros(self._gc.N[ax] + 1, dtype=float)
            coords_ax[1:] = xp.cumsum(dx_cells)   # sum = L → no rescale needed
            coords_ax_h = np.asarray(self.backend.to_host(coords_ax))

            self.coords[ax] = coords_ax_h
            # Per-node spacing (average of left and right cell widths)
            cell_dx = np.diff(coords_ax_h)
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
        self._cell_volumes_cache = None

    # ── Convenience ──────────────────────────────────────────────────────

    @property
    def uniform(self) -> bool:
        """True when the grid is uniform (alpha_grid ≤ 1)."""
        return self._gc.alpha_grid <= 1.0

    def cell_volume(self) -> float:
        """Approximate uniform cell volume (product of mean spacings)."""
        return math.prod(L / N for L, N in zip(self.L, self.N))

    def cell_volumes(self):
        """Per-node control volumes on device, shape ``self.shape``."""
        if self._cell_volumes_cache is not None:
            return self._cell_volumes_cache
        xp = self.xp
        vol = xp.asarray(self.h[0])
        for ax in range(1, self.ndim):
            vol = xp.expand_dims(vol, axis=ax) * xp.asarray(self.h[ax])
        self._cell_volumes_cache = vol
        return vol

    def __repr__(self) -> str:
        h_str = " × ".join(
            f"{self.L[ax]/self.N[ax]:.4g}" for ax in range(self.ndim)
        )
        return f"Grid(ndim={self.ndim}, N={self.N}, L={self.L}, h≈{h_str})"
