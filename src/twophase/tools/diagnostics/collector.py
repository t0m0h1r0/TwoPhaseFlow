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
symmetry_error        parity-aware reflection error under x/y mirror. Each
                      sub-key is 0 for a 4-fold symmetric flow:
                        sym_psi_{y,x}  = ‖ψ − flip(ψ)‖∞ / max|ψ|   (ψ even)
                        sym_u_y        = ‖u − flip_y(u)‖∞ / max|u| (u even in y)
                        sym_u_x        = ‖u + flip_x(u)‖∞ / max|u| (u odd in x)
                        sym_v_y        = ‖v + flip_y(v)‖∞ / max|v| (v odd in y)
                        sym_v_x        = ‖v − flip_x(v)‖∞ / max|v| (v even in x)
                      (CHK-161 y-flip symmetry audit)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def _xp_of(arr):
    """Return the array namespace (numpy or cupy) matching ``arr``.

    Uses :func:`cupy.get_array_module` when cupy is available, else numpy.
    This lets :class:`DiagnosticCollector` stay constructor-compatible while
    operating natively on whichever backend the simulation chose.
    """
    try:
        import cupy
        return cupy.get_array_module(arr)
    except ImportError:
        return np


@dataclass
class DiagnosticRetainedGeometry:
    """Device-side geometry intentionally retained by the simulation procedure."""

    xp: object
    shape: tuple[int, ...]
    X: object
    Y: object
    rows: object | None
    cols: object | None
    y_mid: object


class DiagnosticCollector:
    """Accumulate per-step diagnostic metrics.

    Parameters
    ----------
    metrics : list of str
        Metric names to collect (from YAML ``diagnostics:`` list).
        ``kinetic_energy`` is always added automatically.
    X, Y : ndarray  grid coordinate arrays on the active backend
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
            "symmetry_error",
        ]
    )

    _SYM_SUBKEYS = (
        "sym_psi_y", "sym_psi_x",
        "sym_u_y", "sym_u_x",
        "sym_v_y", "sym_v_x",
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
        self._retained_geometry: DiagnosticRetainedGeometry | None = None

        # bubble_centroid expands into xc / yc / vc sub-series
        # symmetry_error expands into sym_{psi,u,v}_{y,x} sub-series (CHK-161)
        for m in list(self.metrics):
            if m == "bubble_centroid":
                for k in ("xc", "yc", "vc"):
                    self._data.setdefault(k, [])
            elif m == "symmetry_error":
                for k in self._SYM_SUBKEYS:
                    self._data.setdefault(k, [])
            else:
                self._data.setdefault(m, [])

    # ── public interface ──────────────────────────────────────────────────

    def retain_device_geometry(self, xp, X, Y, shape) -> None:
        """Retain geometry produced by grid construction/rebuild for diagnostics."""
        if "deformation" in self.metrics:
            rows, cols = _deformation_axes(xp, tuple(shape))
        else:
            rows = cols = None
        X_dev = xp.asarray(X)
        Y_dev = xp.asarray(Y)
        self._retained_geometry = DiagnosticRetainedGeometry(
            xp=xp,
            shape=tuple(shape),
            X=X_dev,
            Y=Y_dev,
            rows=rows,
            cols=cols,
            y_mid=xp.mean(Y_dev),
        )

    def needs_retained_geometry(self) -> bool:
        """Return whether any requested metric uses grid geometry fields."""
        return any(
            metric in self.metrics
            for metric in ("bubble_centroid", "deformation", "interface_amplitude")
        )

    def collect(
        self,
        t: float,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        p: np.ndarray,
        dV: np.ndarray | None = None,
    ) -> None:
        """Record diagnostics for the current timestep.

        Parameters
        ----------
        dV : ndarray or None
            Per-node control volumes.  When ``None``, falls back to
            scalar ``h**2`` (uniform grid).
        """
        xp = _xp_of(psi)
        if dV is None:
            dV = self.h ** 2
        elif _xp_of(dV) is not xp:
            dV = xp.asarray(dV)
        geometry = self._retained_geometry
        needs_geometry = self.needs_retained_geometry()
        if needs_geometry and (
            geometry is None
            or geometry.xp is not xp
            or geometry.shape != tuple(psi.shape)
        ):
            self.retain_device_geometry(xp, self.X, self.Y, psi.shape)
            geometry = self._retained_geometry
        X = geometry.X if geometry is not None else None
        Y = geometry.Y if geometry is not None else None
        need_volume = "volume_conservation" in self.metrics
        need_ke = "kinetic_energy" in self.metrics
        need_gas_mean = "mean_rise_velocity" in self.metrics
        need_gas_centroid = "bubble_centroid" in self.metrics

        scalar_names: list[str] = []
        scalar_values = []
        if need_volume:
            scalar_names.append("V")
            scalar_values.append(xp.sum(psi * dV))
        if need_ke:
            rho = self.rho_g + (self.rho_l - self.rho_g) * psi
            scalar_names.append("ke")
            scalar_values.append(0.5 * xp.sum(rho * (u ** 2 + v ** 2) * dV))
        if need_gas_mean or need_gas_centroid:
            gas = psi < 0.5
            scalar_names.extend(["gas_volume", "gas_x_sum", "gas_y_sum", "gas_v_sum"])
            scalar_values.extend([
                xp.sum(xp.where(gas, dV, 0.0)),
                xp.sum(xp.where(gas, X * dV, 0.0)),
                xp.sum(xp.where(gas, Y * dV, 0.0)),
                xp.sum(xp.where(gas, v * dV, 0.0)),
            ])
        scalars = {
            name: float(value)
            for name, value in zip(
                scalar_names,
                np.asarray(_to_host(xp.stack(scalar_values))) if scalar_values else [],
            )
        }

        if need_volume and self._V0 is None:
            self._V0 = max(scalars["V"], 1e-30)

        self.times.append(t)

        for m in self.metrics:
            if m == "volume_conservation":
                self._data[m].append(abs(scalars["V"] - self._V0) / self._V0)

            elif m == "kinetic_energy":
                self._data[m].append(scalars["ke"])

            elif m == "mean_rise_velocity":
                vol_gas = scalars["gas_volume"]
                v_sum = scalars["gas_v_sum"]
                vm = v_sum / vol_gas if vol_gas > 1e-12 else 0.0
                self._data[m].append(vm)

            elif m == "bubble_centroid":
                vol_gas = scalars["gas_volume"]
                x_sum = scalars["gas_x_sum"]
                y_sum = scalars["gas_y_sum"]
                v_sum = scalars["gas_v_sum"]
                if vol_gas > 1e-12:
                    xc = x_sum / vol_gas
                    yc = y_sum / vol_gas
                    vc = v_sum / vol_gas
                else:
                    xc = yc = vc = float("nan")
                self._data["xc"].append(xc)
                self._data["yc"].append(yc)
                self._data["vc"].append(vc)

            elif m == "deformation":
                self._data[m].append(_deformation(psi, geometry))

            elif m == "interface_amplitude":
                self._data[m].append(
                    _interface_amplitude(psi, geometry.Y, geometry.y_mid)
                )

            elif m == "symmetry_error":
                # CHK-161 parity-aware: each sub-key is 0 for 4-fold symmetric flow.
                # psi is scalar (even under both flips); u,v are vector components
                # with axis-specific parity (u odd under x-flip, v odd under y-flip).
                for key, value in zip(self._SYM_SUBKEYS, _symmetry_errors(psi, u, v)):
                    self._data[key].append(value)

            elif m == "laplace_pressure":
                if self.sigma > 0.0 and self.R > 0.0:
                    inside = psi > 0.5
                    outside = psi < 0.5
                    raw = xp.stack([
                        xp.sum(inside),
                        xp.sum(outside),
                        xp.sum(xp.where(inside, p, 0.0)),
                        xp.sum(xp.where(outside, p, 0.0)),
                    ])
                    n_in, n_out, p_in_sum, p_out_sum = [
                        float(x) for x in np.asarray(_to_host(raw))
                    ]
                    p_in = (
                        p_in_sum / n_in
                        if n_in > 0 else 0.0
                    )
                    p_out = (
                        p_out_sum / n_out
                        if n_out > 0 else 0.0
                    )
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

def _to_host(arr):
    """Return a numpy copy of ``arr`` regardless of its backend."""
    getter = getattr(arr, "get", None)
    if callable(getter):
        return getter()
    return np.asarray(arr)


def _deformation_axes(xp, shape: tuple[int, ...]):
    """Materialize index fields retained with diagnostic geometry."""
    NX, NY = shape
    rows = xp.arange(NX, dtype=xp.float64)[:, None] * xp.ones((1, NY), dtype=xp.float64)
    cols = xp.ones((NX, 1), dtype=xp.float64) * xp.arange(NY, dtype=xp.float64)[None, :]
    return rows, cols


def _deformation(psi, geometry: DiagnosticRetainedGeometry | None = None) -> float:
    """D = (L−B)/(L+B) from second moments of the ψ > 0.5 region.

    Fully device-resident: reuses the retained index fields created by the
    diagnostic procedure and batches the final scalars into one D2H transfer.
    """
    xp = _xp_of(psi)
    mask = psi > 0.5
    n_pts_dev = xp.sum(mask)
    if (
        geometry is not None
        and geometry.xp is xp
        and geometry.shape == tuple(psi.shape)
        and geometry.rows is not None
        and geometry.cols is not None
    ):
        rows = geometry.rows
        cols = geometry.cols
    else:
        rows, cols = _deformation_axes(xp, tuple(psi.shape))
    n_safe = xp.where(n_pts_dev > 0, n_pts_dev, 1.0)
    row_mean = xp.sum(xp.where(mask, rows, 0.0)) / n_safe
    col_mean = xp.sum(xp.where(mask, cols, 0.0)) / n_safe
    dy = xp.where(mask, rows - row_mean, 0.0)
    dx = xp.where(mask, cols - col_mean, 0.0)
    raw = xp.stack([
        n_pts_dev,
        xp.sum(dx * dx) / n_safe,
        xp.sum(dy * dy) / n_safe,
        xp.sum(dx * dy) / n_safe,
    ])
    stats = np.asarray(_to_host(raw))
    n_pts = float(stats[0])
    if n_pts < 1.0:
        return 0.0
    Ixx, Iyy, Ixy = float(stats[1]), float(stats[2]), float(stats[3])
    disc = max(0.0, 0.25 * (Ixx - Iyy) ** 2 + Ixy ** 2)
    eig1 = 0.5 * (Ixx + Iyy) + np.sqrt(disc)
    eig2 = 0.5 * (Ixx + Iyy) - np.sqrt(disc)
    L = np.sqrt(max(eig1, 1e-30))
    B = np.sqrt(max(eig2, 1e-30))
    return float((L - B) / (L + B)) if (L + B) > 1e-12 else 0.0


def _symmetry_error(field, axis: int, parity: int = +1) -> float:
    """Parity-aware reflection error — CHK-161.

    Returns ‖f − parity · flip_axis(f)‖∞ / (max|f| + 1e-30).
    parity=+1 → field expected even under the flip (scalar, or aligned component).
    parity=−1 → field expected odd under the flip (orthogonal vector component).
    A value of 0 means the expected symmetry is preserved.
    """
    xp = _xp_of(field)
    flipped = xp.flip(field, axis=axis)
    diff = float(xp.max(xp.abs(field - parity * flipped)))
    scale = float(xp.max(xp.abs(field))) + 1e-30
    return diff / scale


def _symmetry_errors(psi, u, v) -> tuple[float, float, float, float, float, float]:
    """Return all parity-aware reflection errors with one scalar transfer."""
    xp = _xp_of(psi)
    terms = (
        (psi, 1, +1),
        (psi, 0, +1),
        (u, 1, +1),
        (u, 0, -1),
        (v, 1, -1),
        (v, 0, +1),
    )
    raw = []
    for field, axis, parity in terms:
        flipped = xp.flip(field, axis=axis)
        raw.append(xp.max(xp.abs(field - parity * flipped)))
        raw.append(xp.max(xp.abs(field)))
    stats = np.asarray(_to_host(xp.stack(raw)))
    return tuple(
        float(stats[2 * i]) / (float(stats[2 * i + 1]) + 1e-30)
        for i in range(len(terms))
    )


def _interface_amplitude(psi, Y, y_mid) -> float:
    """Return max deviation of the first ψ=0.5 crossing in each column."""
    xp = _xp_of(psi)
    psi_dev = xp.asarray(psi)
    if psi_dev.shape[1] < 2:
        return 0.0
    Y_dev = xp.asarray(Y)
    below_left = psi_dev[:, :-1] - 0.5
    below_right = psi_dev[:, 1:] - 0.5
    crossings = below_left * below_right < 0.0
    has_crossing = xp.any(crossings, axis=1)
    first_crossing = xp.argmax(crossings, axis=1)
    rows = xp.arange(psi_dev.shape[0])
    psi0 = psi_dev[rows, first_crossing]
    psi1 = psi_dev[rows, first_crossing + 1]
    y0 = Y_dev[rows, first_crossing]
    y1 = Y_dev[rows, first_crossing + 1]
    denom = xp.where(has_crossing, psi1 - psi0, 1.0)
    frac = xp.where(has_crossing, (0.5 - psi0) / denom, 0.0)
    y_int = y0 + frac * (y1 - y0)
    amplitude = xp.max(
        xp.where(has_crossing, xp.abs(y_int - y_mid), 0.0)
    )
    return float(np.asarray(_to_host(amplitude)))
