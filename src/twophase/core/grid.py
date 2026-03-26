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
        """
        return np.meshgrid(*self.coords, indexing="ij")

    def update_from_levelset(
        self,
        phi_data: np.ndarray,
        eps: float,
        ccd=None,
    ) -> None:
        """Rebuild interface-fitted grid given the signed-distance field φ.

        Only active when ``grid_config.alpha_grid > 1.0``.

        Density function (§6 eq:grid_delta):
            ω(φ) = 1 + (α−1) · δ*(φ),  δ*(φ) = exp(−φ²/ε_g²) / (ε_g√π)
        where ε_g = eps_g_factor × ε.  ω ∈ [1, α]: interface dense, bulk coarse.

        Metric coefficients J = ∂ξ/∂x and ∂J/∂ξ are computed with CCD (O(h⁶))
        when ``ccd`` is provided (§6 Step 5, box:grid_jx_accuracy).  Falls back
        to O(h²) central differences when ``ccd`` is None.

        Parameters
        ----------
        phi_data : array of shape ``self.shape``
        eps      : interface half-width (ε = epsilon_factor × dx_min)
        ccd      : CCDSolver instance for O(h⁶) metric evaluation (optional)
        """
        alpha = self._gc.alpha_grid
        if alpha <= 1.0:
            return  # uniform grid — nothing to do

        dx_floor = self._gc.dx_min_floor
        # ε_g = eps_g_factor × ε  (§6: 推奨 ε_g ≈ 2–4 ε)
        eps_g = self._gc.eps_g_factor * eps

        for ax in range(self.ndim):
            # 1-D marginal of φ along this axis (minimum |φ| over other axes,
            # §6 2次元格子生成アルゴリズム: φ̄^x_i = min_j |φ^(0)_{i,j}|)
            axes_other = tuple(a for a in range(self.ndim) if a != ax)
            phi_host = np.abs(self.backend.to_host(phi_data))
            phi_1d = np.min(phi_host, axis=axes_other)

            # Paper §6 eq:grid_delta: ω = 1 + (α−1)·δ*(φ), δ* = Gaussian delta
            delta_star = np.exp(-(phi_1d ** 2) / (eps_g ** 2)) / (eps_g * np.sqrt(np.pi))
            omega = 1.0 + (alpha - 1.0) * delta_star   # ω ∈ [1, α] — always ≥ 1

            # Spacing proportional to 1/ω; enforce minimum cell width
            raw_dx = np.maximum(1.0 / omega, dx_floor)
            # Normalise so that cumulative sum spans [0, L[ax]]
            raw_dx = raw_dx * (self._gc.L[ax] / raw_dx.sum())

            # Cumulative integration: ステップ3–4 (§6 格子点生成アルゴリズム)
            coords_ax = np.zeros(self._gc.N[ax] + 1)
            coords_ax[1:] = np.cumsum(raw_dx[:-1])  # N cells → N+1 nodes
            coords_ax = coords_ax * (self._gc.L[ax] / coords_ax[-1])

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
        """Compute CCD metrics J = ∂ξ/∂x and dJ/dξ for each axis.

        For a uniform grid J = 1/h (constant) and dJ/dξ = 0.
        For non-uniform grids J varies along the axis.

        The chain rule (§4.9) gives:
            ∂f/∂x   = J · (∂f/∂ξ)
            ∂²f/∂x² = J² · (∂²f/∂ξ²) + J · (dJ/dξ) · (∂f/∂ξ)

        When ``ccd`` is provided and the grid is non-uniform, metrics are
        evaluated with CCD (O(h⁶)) via differentiate_raw(x_coords, axis)
        as required by §6 Step 5 and box:grid_jx_accuracy.  Without CCD
        (uniform grid or fallback) O(h²) central differences are used.

        Parameters
        ----------
        ccd : CCDSolver or None — O(h⁶) solver for metric computation
        """
        self.J: list[np.ndarray] = []
        self.dJ_dxi: list[np.ndarray] = []

        for ax in range(self.ndim):
            if ccd is not None and not self.uniform:
                # §6 Step 5: differentiate coordinate array x_i in ξ-space via CCD
                # differentiate_raw returns d/d(x_unif) where x_unif has spacing L/N.
                # For the domain convention used here (L=1 assumed by _apply_metric),
                # d1_raw ≈ dx_phys/dξ and J = ∂ξ/∂x_phys = 1/d1_raw.
                coords_ax = np.asarray(self.coords[ax])
                d1_raw, d2_raw = ccd.differentiate_raw(coords_ax, axis=ax)
                # J = ∂ξ/∂x_phys;  ∂J/∂ξ from implicit differentiation of J = 1/d1
                J_ax = 1.0 / d1_raw
                dJ_ax = -d2_raw / (d1_raw ** 2)
            else:
                # O(h²) central-difference fallback (uniform grid or no CCD)
                dxi = 1.0 / self.N[ax]
                h = self.h[ax]  # physical spacing per node
                J_ax = dxi / h   # = ∂ξ/∂x = (1/N) / (dx)

                dJ_ax = np.zeros_like(J_ax)
                dJ_ax[1:-1] = (J_ax[2:] - J_ax[:-2]) / (2.0 * dxi)
                dJ_ax[0] = (J_ax[1] - J_ax[0]) / dxi
                dJ_ax[-1] = (J_ax[-1] - J_ax[-2]) / dxi

            self.J.append(J_ax)
            self.dJ_dxi.append(dJ_ax)

    # ── Convenience ──────────────────────────────────────────────────────

    @property
    def uniform(self) -> bool:
        """True when the grid is uniform (alpha_grid ≤ 1)."""
        return self._gc.alpha_grid <= 1.0

    def cell_volume(self) -> float:
        """Approximate uniform cell volume (product of mean spacings)."""
        return float(np.prod([L / N for L, N in zip(self.L, self.N)]))

    def __repr__(self) -> str:
        h_str = " × ".join(
            f"{self.L[ax]/self.N[ax]:.4g}" for ax in range(self.ndim)
        )
        return f"Grid(ndim={self.ndim}, N={self.N}, L={self.L}, h≈{h_str})"
