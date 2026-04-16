"""Heaviside / interface reconstruction utilities.

Provides reusable reconstruction logic for:
  1) phi <-> psi conversions through regularized Heaviside
  2) phi clipping in phi-primary transport paths
  3) interface (phi=0) point reconstruction for diagnostics/visualization
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .heaviside import heaviside, invert_heaviside


@dataclass(frozen=True)
class ReconstructionConfig:
    """Configuration for heaviside/interface reconstruction."""

    eps: float
    eps_scale: float = 1.0
    clip_factor: float = 12.0

    @property
    def eps_effective(self) -> float:
        return float(self.eps_scale) * float(self.eps)


class HeavisideInterfaceReconstructor:
    """Library component for phi/psi/interface reconstruction."""

    def __init__(self, backend, config: ReconstructionConfig):
        self._backend = backend
        self._cfg = config
        self._eps_eff = max(1e-15, config.eps_effective)
        self._clip = max(2.0, float(config.clip_factor))

    @property
    def eps_effective(self) -> float:
        return self._eps_eff

    def psi_from_phi(self, phi: Any):
        xp = self._backend.xp
        return xp.asarray(heaviside(xp, xp.asarray(phi), self._eps_eff))

    def phi_from_psi(self, psi: Any):
        xp = self._backend.xp
        return xp.asarray(invert_heaviside(xp, xp.asarray(psi), self._eps_eff))

    def clip_phi(self, phi: Any):
        xp = self._backend.xp
        phi = xp.asarray(phi)
        lim = self._clip * self._eps_eff
        return xp.clip(phi, -lim, lim)

    def interface_points_from_phi(self, phi: Any, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Reconstruct interface points (phi=0) by edge-wise linear interpolation."""
        phi_h = np.asarray(self._backend.to_host(phi))
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        if phi_h.ndim != 2:
            raise ValueError("interface_points_from_phi currently supports 2D only.")

        nx, ny = phi_h.shape
        if x.size != nx or y.size != ny:
            raise ValueError("Coordinate sizes must match phi shape.")

        pts: list[tuple[float, float]] = []

        def _interp(v0: float, v1: float, a0: float, a1: float) -> float:
            den = (v1 - v0)
            if abs(den) < 1e-30:
                return 0.5 * (a0 + a1)
            t = -v0 / den
            t = max(0.0, min(1.0, t))
            return (1.0 - t) * a0 + t * a1

        def _cross_or_zero(v0: float, v1: float) -> bool:
            # Accept strict sign change and zero-touch edges.
            return (v0 * v1 < 0.0) or (abs(v0) <= 1e-14) or (abs(v1) <= 1e-14)

        for i in range(nx - 1):
            xi0, xi1 = x[i], x[i + 1]
            for j in range(ny - 1):
                yj0, yj1 = y[j], y[j + 1]
                p00 = phi_h[i, j]
                p10 = phi_h[i + 1, j]
                p01 = phi_h[i, j + 1]
                p11 = phi_h[i + 1, j + 1]

                if _cross_or_zero(p00, p10):
                    pts.append((_interp(p00, p10, xi0, xi1), yj0))
                if _cross_or_zero(p01, p11):
                    pts.append((_interp(p01, p11, xi0, xi1), yj1))
                if _cross_or_zero(p00, p01):
                    pts.append((xi0, _interp(p00, p01, yj0, yj1)))
                if _cross_or_zero(p10, p11):
                    pts.append((xi1, _interp(p10, p11, yj0, yj1)))

        if not pts:
            return np.empty((0, 2), dtype=float)
        return np.asarray(pts, dtype=float)

    def interface_points_from_psi(self, psi: Any, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        phi = self.phi_from_psi(psi)
        return self.interface_points_from_phi(phi, x, y)
