"""Figure generation from YAML ``figures:`` spec.

:func:`generate_figures` iterates over the ``figures`` list in
:class:`~twophase.config_io.OutputCfg` and saves each figure as a PDF.

Supported figure types
----------------------
snapshot        ψ (or any named field) at a specific time index
time_series     one or more diagnostic metrics vs. time  (with optional
                analytical reference curve)
convergence     log-log error vs. grid spacing / step count
deformation_comparison
                deformation D(t) vs. Taylor (1932) analytical formula
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ── public entry point ────────────────────────────────────────────────────────

def generate_figures(cfg: "ExperimentConfig", results: dict, outdir: str | Path) -> None:
    """Generate and save all figures defined in ``cfg.output.figures``.

    Parameters
    ----------
    cfg : ExperimentConfig
    results : dict
        Return value of :func:`~twophase.ns_pipeline.run_simulation`.
    outdir : str or Path
        Directory where PDFs are written.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for spec in cfg.output.figures:
        fig_type = spec.get("type", "")
        try:
            fig = _make_figure(fig_type, spec, results, cfg)
            fname = spec.get("file", f"{fig_type}.pdf")
            fig.savefig(outdir / fname, bbox_inches="tight")
            plt.close(fig)
        except Exception as exc:
            print(f"[plot_factory] WARNING: failed to generate '{fig_type}': {exc}")


# ── dispatcher ────────────────────────────────────────────────────────────────

def _make_figure(
    fig_type: str,
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    if fig_type == "snapshot":
        return _snapshot(spec, results, cfg)
    if fig_type == "time_series":
        return _time_series(spec, results, cfg)
    if fig_type == "convergence":
        return _convergence(spec, results, cfg)
    if fig_type == "deformation_comparison":
        return _deformation_comparison(spec, results, cfg)
    if fig_type == "velocity_snapshot":
        return _velocity_snapshot(spec, results, cfg)
    if fig_type == "pressure_snapshot":
        return _pressure_snapshot(spec, results, cfg)
    raise ValueError(f"Unknown figure type '{fig_type}'.")


# ── snapshot ──────────────────────────────────────────────────────────────────

def _snapshot(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """ψ colour map at a given snapshot index.

    When the snapshot carries ``grid_coords`` (non-uniform grid), the field
    is remapped to a uniform plotting grid via ``remap_field_to_uniform``
    so that the visual geometry is correct.
    """
    snaps = results.get("snapshots", [])
    if not snaps:
        raise ValueError("No snapshots in results.")

    t_idx = int(spec.get("t_idx", -1))
    snap = snaps[t_idx]
    psi = snap["psi"]
    t_val = snap["t"]

    g = cfg.grid

    if "grid_coords" in snap:
        # Non-uniform grid: remap to uniform for visualization
        from ..core.grid_remap import remap_field_to_uniform
        from ..backend import Backend
        backend = Backend(use_gpu=False)
        psi, (X, Y), _ = remap_field_to_uniform(
            backend, psi, snap["grid_coords"],
            [g.LX, g.LY], clip_range=(0.0, 1.0),
        )
    else:
        # Uniform grid: linspace coordinates
        X = np.linspace(0, g.LX, g.NX + 1)
        Y = np.linspace(0, g.LY, g.NY + 1)

    title = spec.get("title", f"ψ at t = {t_val:.3f}")
    xlabel = spec.get("xlabel", "x")
    ylabel = spec.get("ylabel", "y")
    cmap = spec.get("cmap", "RdBu_r")
    vmin = spec.get("vmin", 0.0)
    vmax = spec.get("vmax", 1.0)

    fig, ax = plt.subplots(figsize=(4, 4 * g.LY / g.LX))
    im = ax.pcolormesh(X, Y, psi.T, cmap=cmap, vmin=vmin, vmax=vmax,
                       shading="nearest")
    if spec.get("contour", True):
        ax.contour(X, Y, psi.T, levels=[0.5], colors="k", linewidths=0.8)
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="ψ")
    ax.set_aspect("equal")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return fig


# ── velocity snapshot ────────────────────────────────────────────────────────

def _velocity_snapshot(
    spec: dict, results: dict, cfg: "ExperimentConfig"
) -> plt.Figure:
    """Speed colour map + quiver arrows + ψ=0.5 contour."""
    snaps = results.get("snapshots", [])
    if not snaps:
        raise ValueError("No snapshots in results.")

    t_idx = int(spec.get("t_idx", -1))
    snap = snaps[t_idx]
    psi, u, v = snap["psi"], snap["u"], snap["v"]
    t_val = snap["t"]
    g = cfg.grid

    if "grid_coords" in snap:
        from ..core.grid_remap import remap_field_to_uniform
        from ..backend import Backend
        backend = Backend(use_gpu=False)
        psi, (X, Y), remapper = remap_field_to_uniform(
            backend, psi, snap["grid_coords"],
            [g.LX, g.LY], clip_range=(0.0, 1.0),
        )
        u = np.asarray(remapper.remap(u))
        v = np.asarray(remapper.remap(v))
    else:
        X = np.linspace(0, g.LX, g.NX + 1)
        Y = np.linspace(0, g.LY, g.NY + 1)

    speed = np.sqrt(u ** 2 + v ** 2)
    title = spec.get("title", f"Velocity at t = {t_val:.3f}")
    cmap = spec.get("cmap", "viridis")
    stride = int(spec.get("quiver_stride", 4))

    fig, ax = plt.subplots(figsize=(4, 4 * g.LY / g.LX))
    im = ax.pcolormesh(X, Y, speed.T, cmap=cmap, shading="nearest")
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="|u|")
    if spec.get("contour", True):
        ax.contour(X, Y, psi.T, levels=[0.5], colors="k", linewidths=0.8)
    s = stride
    us, vs = u[::s, ::s].T, v[::s, ::s].T
    sp = np.sqrt(us ** 2 + vs ** 2)
    sp_safe = np.maximum(sp, 1e-14)
    ax.quiver(
        X[::s], Y[::s], us / sp_safe, vs / sp_safe,
        sp, cmap="hot", alpha=0.8,
        scale=30, width=0.003,
    )
    ax.set_aspect("equal")
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    ax.set_title(title)
    return fig


# ── pressure snapshot ────────────────────────────────────────────────────────

def _pressure_snapshot(
    spec: dict, results: dict, cfg: "ExperimentConfig"
) -> plt.Figure:
    """Pressure colour map + ψ=0.5 contour."""
    snaps = results.get("snapshots", [])
    if not snaps:
        raise ValueError("No snapshots in results.")

    t_idx = int(spec.get("t_idx", -1))
    snap = snaps[t_idx]
    psi, p = snap["psi"], snap["p"]
    t_val = snap["t"]
    g = cfg.grid

    if "grid_coords" in snap:
        from ..core.grid_remap import remap_field_to_uniform
        from ..backend import Backend
        backend = Backend(use_gpu=False)
        psi, (X, Y), remapper = remap_field_to_uniform(
            backend, psi, snap["grid_coords"],
            [g.LX, g.LY], clip_range=(0.0, 1.0),
        )
        p = np.asarray(remapper.remap(p))
    else:
        X = np.linspace(0, g.LX, g.NX + 1)
        Y = np.linspace(0, g.LY, g.NY + 1)

    title = spec.get("title", f"Pressure at t = {t_val:.3f}")
    cmap = spec.get("cmap", "RdBu_r")

    fig, ax = plt.subplots(figsize=(4, 4 * g.LY / g.LX))
    im = ax.pcolormesh(X, Y, p.T, cmap=cmap,
                       vmin=spec.get("vmin"), vmax=spec.get("vmax"),
                       shading="nearest")
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="p")
    if spec.get("contour", True):
        ax.contour(X, Y, psi.T, levels=[0.5], colors="k", linewidths=0.8)
    ax.set_aspect("equal")
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    ax.set_title(title)
    return fig


# ── time series ───────────────────────────────────────────────────────────────

def _time_series(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """Plot one or more diagnostic time series."""
    t = results.get("times", np.array([]))
    ys: list[str] = spec.get("y", [])
    labels: list[str] = spec.get("labels", ys)
    xlabel = spec.get("xlabel", "t")
    ylabel = spec.get("ylabel", "")
    title = spec.get("title", "")
    yscale = spec.get("yscale", "linear")

    fig, ax = plt.subplots(figsize=(6, 4))
    for key, lbl in zip(ys, labels):
        if key in results:
            ax.plot(t, results[key], label=lbl)

    # Optional: analytical reference
    ana = spec.get("analytical")
    if ana is not None:
        _add_analytical(ax, t, ana, cfg, results)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_yscale(yscale)
    if len(ys) > 1 or ana is not None:
        ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def _add_analytical(
    ax: plt.Axes,
    t: np.ndarray,
    ana: dict,
    cfg: "ExperimentConfig",
    results: dict,
) -> None:
    """Overlay an analytical reference curve."""
    formula = ana.get("formula", "")
    ph = cfg.physics

    if formula == "prosperetti":
        # D(t) = D0 * exp(-β t) * cos(ω0 t + φ0)
        omega0 = float(ana.get("omega0", 1.0))
        beta = float(ana.get("beta", 0.0))
        D0 = float(ana.get("D0", 0.05))
        y_ana = D0 * np.exp(-beta * t) * np.cos(omega0 * t)
        ax.plot(t, y_ana, "k--", label="Prosperetti (1981)")

    elif formula == "taylor":
        # D_theory = (19λ+16)/(16λ+16) × Ca  (Taylor 1932 small-Ca)
        Ca = float(ana.get("Ca", 0.0))
        lam = float(ana.get("lambda_mu", 1.0))
        D_th = (19 * lam + 16) / (16 * lam + 16) * Ca
        ax.axhline(D_th, color="k", linestyle="--",
                   label=f"Taylor (Ca={Ca:.1f}, λ={lam})")

    elif formula == "rt_exponential":
        # η(t) = η0 * exp(ω t) (linear RT growth)
        omega = float(ana.get("omega", 0.0))
        eta0 = float(ana.get("eta0", 0.05))
        y_ana = eta0 * np.exp(omega * t)
        ax.plot(t, y_ana, "k--", label=f"RT theory ω={omega:.3f}")


# ── convergence ───────────────────────────────────────────────────────────────

def _convergence(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """Log-log convergence plot: error vs. h (or N)."""
    h_vals = np.array(results.get("h_vals", []))
    err_keys: list[str] = spec.get("errors", ["error"])
    labels: list[str] = spec.get("labels", err_keys)
    xlabel = spec.get("xlabel", "h")
    ylabel = spec.get("ylabel", "error")
    title = spec.get("title", "Grid convergence")
    orders: list[int] = spec.get("orders", [2, 4])

    fig, ax = plt.subplots(figsize=(5, 4))
    for key, lbl in zip(err_keys, labels):
        if key in results:
            ax.loglog(h_vals, results[key], "o-", label=lbl)

    # Reference slope lines
    if h_vals.size > 1:
        h_ref = h_vals[-1]
        for p in orders:
            scale = float(results.get(err_keys[0], [1.0])[-1]) if err_keys[0] in results else 1.0
            y_ref = scale * (h_vals / h_ref) ** p
            ax.loglog(h_vals, y_ref, "k--", alpha=0.6, label=f"O(h^{p})")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    return fig


# ── deformation comparison ────────────────────────────────────────────────────

def _deformation_comparison(
    spec: dict, results: dict, cfg: "ExperimentConfig"
) -> plt.Figure:
    """D vs. t compared to Taylor (1932) for multiple Ca values."""
    t = results.get("times", np.array([]))
    Ca_vals: list[float] = spec.get("Ca_vals", [])
    lam = float(spec.get("lambda_mu", 1.0))
    xlabel = spec.get("xlabel", "t")
    ylabel = spec.get("ylabel", "Deformation D")
    title = spec.get("title", "Taylor deformation")

    fig, ax = plt.subplots(figsize=(6, 4))

    # Simulation curves: results["D_Ca{x.x}"] keys
    for Ca in Ca_vals:
        key = f"D_Ca{Ca:.1f}"
        if key in results:
            D_th = (19 * lam + 16) / (16 * lam + 16) * Ca
            ax.plot(t, results[key], label=f"Ca={Ca:.1f} (sim)")
            ax.axhline(D_th, linestyle="--", alpha=0.7,
                       label=f"Ca={Ca:.1f} (Taylor)")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    return fig
