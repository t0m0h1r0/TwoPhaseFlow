"""Snapshot-oriented figure renderers for YAML ``figures:`` specs.

Symbol mapping
--------------
``psi`` -> conservative level-set field ``ψ``
``u``   -> x-velocity
``v``   -> y-velocity
``p``   -> pressure
``rho`` -> density ``ρ``
"""

from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from ..simulation.config_models import ExperimentConfig


@dataclass(frozen=True)
class SnapshotPlotContext:
    snap: dict
    X: np.ndarray
    Y: np.ndarray
    psi: np.ndarray
    cfg: "ExperimentConfig"
    t_val: float
    remapper: object | None = None


def build_snapshot_plot_context(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> SnapshotPlotContext:
    """Build a normalized plotting context for one snapshot figure."""
    snaps = results.get("snapshots", [])
    if not snaps:
        raise ValueError("No snapshots in results.")

    t_idx = int(spec.get("t_idx", -1))
    snap = snaps[t_idx]
    psi = snap["psi"]
    t_val = snap["t"]
    grid = cfg.grid

    if "grid_coords" in snap:
        from ..backend import Backend
        from ..core.grid_remap import remap_field_to_uniform

        backend = Backend(use_gpu=False)
        psi, (X, Y), remapper = remap_field_to_uniform(
            backend,
            psi,
            snap["grid_coords"],
            [grid.LX, grid.LY],
            clip_range=(0.0, 1.0),
        )
        return SnapshotPlotContext(
            snap=snap,
            X=X,
            Y=Y,
            psi=psi,
            cfg=cfg,
            t_val=t_val,
            remapper=remapper,
        )

    X = np.linspace(0, grid.LX, grid.NX + 1)
    Y = np.linspace(0, grid.LY, grid.NY + 1)
    return SnapshotPlotContext(
        snap=snap,
        X=X,
        Y=Y,
        psi=psi,
        cfg=cfg,
        t_val=t_val,
        remapper=None,
    )


def remap_snapshot_field(context: SnapshotPlotContext, field) -> np.ndarray:
    """Return a host plotting array for one snapshot field."""
    if context.remapper is None:
        return np.asarray(field)
    return np.asarray(context.remapper.remap(field))


def snapshot(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """Render a scalar ``ψ`` snapshot."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    title = spec.get("title", f"ψ at t = {context.t_val:.3f}")
    xlabel = spec.get("xlabel", "x")
    ylabel = spec.get("ylabel", "y")
    cmap = spec.get("cmap", "RdBu_r")
    vmin = spec.get("vmin", 0.0)
    vmax = spec.get("vmax", 1.0)

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(
        context.X,
        context.Y,
        context.psi.T,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        shading="nearest",
    )
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="ψ")
    ax.set_aspect("equal")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    return fig


def velocity_snapshot(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Render speed color map with quiver arrows."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    u = remap_snapshot_field(context, context.snap["u"])
    v = remap_snapshot_field(context, context.snap["v"])
    speed = np.sqrt(u ** 2 + v ** 2)
    title = spec.get("title", f"Velocity at t = {context.t_val:.3f}")
    cmap = spec.get("cmap", "viridis")
    stride = int(spec.get("quiver_stride", 4))

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(context.X, context.Y, speed.T, cmap=cmap, shading="nearest")
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="|u|")
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    us = u[::stride, ::stride].T
    vs = v[::stride, ::stride].T
    sp = np.sqrt(us ** 2 + vs ** 2)
    sp_safe = np.maximum(sp, 1e-14)
    ax.quiver(
        context.X[::stride],
        context.Y[::stride],
        us / sp_safe,
        vs / sp_safe,
        sp,
        cmap="hot",
        alpha=0.8,
        scale=30,
        width=0.003,
    )
    ax.set_aspect("equal")
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    ax.set_title(title)
    return fig


def pressure_snapshot(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Render pressure color map with interface contour."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    p = remap_snapshot_field(context, context.snap["p"])
    title = spec.get("title", f"Pressure at t = {context.t_val:.3f}")
    cmap = spec.get("cmap", "RdBu_r")

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(
        context.X,
        context.Y,
        p.T,
        cmap=cmap,
        vmin=spec.get("vmin"),
        vmax=spec.get("vmax"),
        shading="nearest",
    )
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="p")
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    ax.set_aspect("equal")
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    ax.set_title(title)
    return fig


def density_snapshot(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Render density color map with interface contour."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    rho = context.snap.get("rho")
    if rho is not None:
        rho = remap_snapshot_field(context, rho)
    else:
        rho = cfg.physics.rho_l * context.psi + cfg.physics.rho_g * (1.0 - context.psi)

    title = spec.get("title", f"Density at t = {context.t_val:.3f}")
    cmap = spec.get("cmap", "RdBu")
    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(
        context.X,
        context.Y,
        rho.T,
        cmap=cmap,
        vmin=spec.get("vmin"),
        vmax=spec.get("vmax"),
        shading="nearest",
    )
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="ρ")
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    ax.set_aspect("equal")
    ax.set_xlabel(spec.get("xlabel", "x"))
    ax.set_ylabel(spec.get("ylabel", "y"))
    ax.set_title(title)
    return fig


def build_snapshot_series_renderers() -> dict[str, Callable]:
    """Return the renderer registry for ``snapshot_series`` figures."""
    return {
        "density": lambda snap, cfg: density_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg),
        "velocity": lambda snap, cfg: velocity_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg),
        "psi": lambda snap, cfg: snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg),
        "pressure": lambda snap, cfg: pressure_snapshot({"t_idx": 0}, {"snapshots": [snap]}, cfg),
    }


def snapshot_series(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
    outdir: Path,
) -> None:
    """Save one PDF per snapshot for the requested field."""
    snaps = results.get("snapshots", [])
    if not snaps:
        raise ValueError("No snapshots in results.")

    field = spec.get("field", "density")
    prefix = spec.get("file_prefix", f"{field}_t")
    renderers = build_snapshot_series_renderers()
    renderer = renderers.get(field)
    if renderer is None:
        raise ValueError(
            f"snapshot_series: unknown field '{field}'. Choose from {list(renderers)}"
        )

    for snap in snaps:
        t_val = snap["t"]
        fig = renderer(snap, cfg)
        fig.savefig(outdir / f"{prefix}{t_val:.3f}.pdf", bbox_inches="tight")
        plt.close(fig)
