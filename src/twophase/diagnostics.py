"""Standard diagnostic metrics for two-phase NS experiments.

``DiagnosticCollector`` accumulates per-step metrics during a simulation run.
Each metric is identified by a string key (matching the ``diagnostics:`` list
in the YAML config).

Supported metrics
-----------------
volume_conservation   |ΔV| / V₀  (relative change in liquid volume)
kinetic_energy        ½ Σ ρ |u|² h²  (always collected; used for divergence check)
mean_rise_velocity    volume-averaged v of the gas phase
bubble_centroid       (xc, yc, vc) centroid of gas phase  → stores xc, yc, vc
deformation           D = (L−B)/(L+B) from second moments of ψ > 0.5 region
interface_amplitude   max vertical deviation of ψ = 0.5 isoline from domain centre
laplace_pressure      |Δp_sim − σ/R| / (σ/R)  (static-droplet only)
"""

from __future__ import annotations

import numpy as np


class DiagnosticCollector:
    """Accumulate per-step diagnostic metrics.

    Parameters
    ----------
    metrics : list of str
        Metric names to collect (from YAML ``diagnostics:`` list).
        ``kinetic_energy`` is always added automatically.
    X, Y : ndarray  grid coordinate arrays
    h : float       grid spacing
    rho_l, rho_g : float  densities (used for KE and phase masks)
    sigma : float   surface tension (for ``laplace_pressure``; optional)
    R : float       droplet radius  (for ``laplace_pressure``; optional)
    """

    SUPPORTED: frozenset[str] = frozenset(
        [
            "volume_conservation",
            "kinetic_energy",
            "mean_rise_velocity",
            "bubble_centroid",
            "deformation",
            "interface_amplitude",
            "laplace_pressure",
        ]
    )

    def __init__(
        self,
        metrics: list,
        X: np.ndarray,
        Y: np.ndarray,
        h: float,
        rho_l: float = 1.0,
        rho_g: float = 1.0,
        sigma: float = 0.0,
        R: float = 0.25,
    ) -> None:
        # Normalise: metrics may be strings or dicts with 'type' key
        self.metrics: list[str] = [
            m if isinstance(m, str) else m["type"] for m in metrics
        ]
        # kinetic_energy is always needed for the divergence guard
        if "kinetic_energy" not in self.metrics:
            self.metrics.append("kinetic_energy")

        self.X = X
        self.Y = Y
        self.h = h
        self.rho_l = rho_l
        self.rho_g = rho_g
        self.sigma = sigma
        self.R = R

        self.times: list[float] = []
        self._data: dict[str, list] = {}
        self._V0: float | None = None  # set on first collect()

        # bubble_centroid expands into xc / yc / vc sub-series
        for m in list(self.metrics):
            if m == "bubble_centroid":
                for k in ("xc", "yc", "vc"):
                    self._data.setdefault(k, [])
            else:
                self._data.setdefault(m, [])

    # ── public interface ──────────────────────────────────────────────────

    def collect(
        self,
        t: float,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        p: np.ndarray,
    ) -> None:
        """Record diagnostics for the current timestep."""
        h = self.h
        rho = self.rho_g + (self.rho_l - self.rho_g) * psi

        # Initialise reference volume on first call
        if self._V0 is None:
            self._V0 = max(float(np.sum(psi) * h ** 2), 1e-30)

        self.times.append(t)

        for m in self.metrics:
            if m == "volume_conservation":
                V = float(np.sum(psi) * h ** 2)
                self._data[m].append(abs(V - self._V0) / self._V0)

            elif m == "kinetic_energy":
                ke = 0.5 * float(np.sum(rho * (u ** 2 + v ** 2)) * h ** 2)
                self._data[m].append(ke)

            elif m == "mean_rise_velocity":
                gas = psi < 0.5
                vol_gas = float(np.sum(gas) * h ** 2)
                vm = (
                    float(np.sum(v[gas]) * h ** 2) / vol_gas
                    if vol_gas > 1e-12
                    else 0.0
                )
                self._data[m].append(vm)

            elif m == "bubble_centroid":
                gas = psi < 0.5
                vol_gas = float(np.sum(gas) * h ** 2)
                if vol_gas > 1e-12:
                    xc = float(np.sum(self.X[gas]) * h ** 2) / vol_gas
                    yc = float(np.sum(self.Y[gas]) * h ** 2) / vol_gas
                    vc = float(np.sum(v[gas]) * h ** 2) / vol_gas
                else:
                    xc = yc = vc = float("nan")
                self._data["xc"].append(xc)
                self._data["yc"].append(yc)
                self._data["vc"].append(vc)

            elif m == "deformation":
                self._data[m].append(_deformation(psi))

            elif m == "interface_amplitude":
                self._data[m].append(_interface_amplitude(psi, self.Y, h))

            elif m == "laplace_pressure":
                if self.sigma > 0.0 and self.R > 0.0:
                    inside = psi > 0.5
                    outside = psi < 0.5
                    p_in = float(np.mean(p[inside])) if np.any(inside) else 0.0
                    p_out = float(np.mean(p[outside])) if np.any(outside) else 0.0
                    dp_sim = p_in - p_out
                    dp_th = self.sigma / self.R
                    err = abs(dp_sim - dp_th) / dp_th if dp_th > 0 else 0.0
                    self._data[m].append(err)
                else:
                    self._data[m].append(0.0)

    def last(self, key: str, default: float = 0.0) -> float:
        """Return the most recently collected value for ``key``."""
        data = self._data.get(key, [])
        return float(data[-1]) if data else default

    def to_arrays(self) -> dict[str, np.ndarray]:
        """Convert accumulated lists to numpy arrays."""
        out: dict[str, np.ndarray] = {"times": np.array(self.times)}
        for k, vals in self._data.items():
            if vals:
                out[k] = np.array(vals)
        return out


# ── per-metric helpers ────────────────────────────────────────────────────────

def _deformation(psi: np.ndarray) -> float:
    """D = (L−B)/(L+B) from second moments of the ψ > 0.5 region."""
    mask = psi > 0.5
    if not np.any(mask):
        return 0.0
    idx = np.argwhere(mask)
    dy = idx[:, 0] - idx[:, 0].mean()
    dx = idx[:, 1] - idx[:, 1].mean()
    Ixx = float(np.mean(dx ** 2))
    Iyy = float(np.mean(dy ** 2))
    Ixy = float(np.mean(dx * dy))
    disc = max(0.0, 0.25 * (Ixx - Iyy) ** 2 + Ixy ** 2)
    eig1 = 0.5 * (Ixx + Iyy) + np.sqrt(disc)
    eig2 = 0.5 * (Ixx + Iyy) - np.sqrt(disc)
    L = np.sqrt(max(eig1, 1e-30))
    B = np.sqrt(max(eig2, 1e-30))
    return float((L - B) / (L + B)) if (L + B) > 1e-12 else 0.0


def _interface_amplitude(psi: np.ndarray, Y: np.ndarray, h: float) -> float:
    """Approximate amplitude of ψ = 0.5 isoline deviation from domain centre."""
    NY = psi.shape[1]
    y_mid = Y.mean()
    best = 0.0
    for i in range(psi.shape[0]):
        col = psi[i, :]
        for j in range(NY - 1):
            if (col[j] - 0.5) * (col[j + 1] - 0.5) < 0:
                frac = (0.5 - col[j]) / (col[j + 1] - col[j])
                y_int = Y[i, j] + frac * h
                best = max(best, abs(y_int - y_mid))
                break
    return best
