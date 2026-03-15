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
    from ..config import SimulationConfig


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

    def __init__(self, config: "SimulationConfig", backend: "Backend"):
        self.config = config
        self.backend = backend
        self.xp = backend.xp

        self.ndim = config.ndim
        self.N = tuple(config.N)
        self.L = tuple(config.L)

        # Build uniform grid (interface-fitted update happens separately)
        self.coords: list[np.ndarray] = []
        self.h: list[np.ndarray] = []
        for ax in range(self.ndim):
            c = np.linspace(0.0, config.L[ax], config.N[ax] + 1)
            self.coords.append(c)
            # h[ax] is length-N[ax] spacing (between consecutive nodes)
            # We store per-node spacing (averaged from both sides) for metrics
            dx = np.full(config.N[ax] + 1, config.L[ax] / config.N[ax])
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

    def update_from_levelset(self, phi_data: np.ndarray) -> None:
        """Rebuild interface-fitted grid given the signed-distance field φ.

        Only active when ``config.alpha_grid > 1.0``.
        Applies a minimum cell-width floor to avoid CCD ill-conditioning.

        Parameters
        ----------
        phi_data : array of shape ``self.shape``
        """
        alpha = self.config.alpha_grid
        if alpha <= 1.0:
            return  # uniform grid — nothing to do

        eps = self.config.epsilon_factor * float(np.min([
            self.config.L[ax] / self.config.N[ax] for ax in range(self.ndim)
        ]))
        dx_floor = self.config.dx_min_floor

        for ax in range(self.ndim):
            # 1-D marginal of φ along this axis (mean over other axes)
            axes_other = tuple(a for a in range(self.ndim) if a != ax)
            phi_1d = np.mean(self.backend.to_host(phi_data), axis=axes_other)

            # Grid density ω ∈ (0, 1]
            omega = np.exp(-alpha * (phi_1d / eps) ** 2)
            # Spacing proportional to 1 / ω (dense near interface)
            raw_dx = 1.0 / np.maximum(omega, 1e-12)
            # Enforce minimum cell width
            raw_dx = np.maximum(raw_dx, dx_floor)
            # Normalise so that sum(dx) = L[ax]
            raw_dx = raw_dx * (self.config.L[ax] / raw_dx.sum())

            # Integrate to get node coordinates
            coords_ax = np.zeros(self.config.N[ax] + 1)
            coords_ax[1:] = np.cumsum(raw_dx[:-1])  # N cells → N+1 nodes
            # Rescale to exactly [0, L[ax]]
            coords_ax = coords_ax * (self.config.L[ax] / coords_ax[-1])

            self.coords[ax] = coords_ax
            # Per-node spacing (average of left and right cell widths)
            cell_dx = np.diff(coords_ax)
            node_dx = np.empty(self.config.N[ax] + 1)
            node_dx[0] = cell_dx[0]
            node_dx[-1] = cell_dx[-1]
            node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
            self.h[ax] = node_dx

        self._build_metrics()

    # ── Private helpers ───────────────────────────────────────────────────

    def _build_metrics(self) -> None:
        """Compute CCD metrics J = ∂ξ/∂x and dJ/dξ for each axis.

        For a uniform grid J = 1/h (constant) and dJ/dξ = 0.
        For non-uniform grids J varies along the axis.

        The chain rule (§4.9) gives:
            ∂f/∂x  = J · (∂f/∂ξ)
            ∂²f/∂x² = J² · (∂²f/∂ξ²) + J · (dJ/dξ) · (∂f/∂ξ)
        """
        self.J: list[np.ndarray] = []
        self.dJ_dxi: list[np.ndarray] = []

        for ax in range(self.ndim):
            # ξ spacing in computational space is always 1/N[ax]
            dxi = 1.0 / self.N[ax]
            h = self.h[ax]  # physical spacing per node
            J_ax = dxi / h   # = ∂ξ/∂x = (1/N) / (dx)

            # dJ/dξ via central differences in ξ-space
            dJ = np.zeros_like(J_ax)
            dJ[1:-1] = (J_ax[2:] - J_ax[:-2]) / (2.0 * dxi)
            dJ[0] = (J_ax[1] - J_ax[0]) / dxi
            dJ[-1] = (J_ax[-1] - J_ax[-2]) / dxi

            self.J.append(J_ax)
            self.dJ_dxi.append(dJ)

    # ── Convenience ──────────────────────────────────────────────────────

    @property
    def uniform(self) -> bool:
        """True when the grid is uniform (alpha_grid ≤ 1)."""
        return self.config.alpha_grid <= 1.0

    def cell_volume(self) -> float:
        """Approximate uniform cell volume (product of mean spacings)."""
        return float(np.prod([L / N for L, N in zip(self.L, self.N)]))

    def __repr__(self) -> str:
        h_str = " × ".join(
            f"{self.L[ax]/self.N[ax]:.4g}" for ax in range(self.ndim)
        )
        return f"Grid(ndim={self.ndim}, N={self.N}, L={self.L}, h≈{h_str})"
