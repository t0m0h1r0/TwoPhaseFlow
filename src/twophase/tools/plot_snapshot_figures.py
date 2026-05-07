"""Snapshot-oriented figure renderers for YAML ``figures:`` specs.

Symbol mapping
--------------
``psi`` -> conservative level-set field ``ψ``
``u``   -> x-velocity
``v``   -> y-velocity
``p``   -> stored scalar pressure representative
``rho`` -> density ``ρ``
"""

from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from ..simulation.visualization.plot_fields import (
    DEFAULT_SPEED_CMAP,
    DEFAULT_VECTOR_CMAP,
    draw_clean_velocity_arrows,
    positive_range,
)
from .pressure_representatives import phase_hodge_pressure_representative

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


def finite_min_max(arrays: list[np.ndarray]) -> tuple[float, float]:
    """Return finite min/max over a snapshot series."""
    finite_parts = []
    for array in arrays:
        values = np.asarray(array, dtype=float)
        finite = values[np.isfinite(values)]
        if finite.size:
            finite_parts.append(finite)
    if not finite_parts:
        return 0.0, 1.0
    merged = np.concatenate(finite_parts)
    return float(np.min(merged)), float(np.max(merged))


def pressure_hodge_field(
    context: SnapshotPlotContext,
    spec: dict,
) -> np.ndarray:
    """Return the phase-wise Hodge pressure representative for one snapshot."""
    grid = context.cfg.grid
    if "pressure_accel_faces" not in context.snap:
        raise ValueError(
            "pressure_hodge requires pressure_accel_faces in saved snapshots; "
            "regenerate data with the current affine pressure-jump runner."
        )
    original_psi = np.asarray(context.snap["psi"])
    original_pressure = np.asarray(context.snap["p"])
    original_rho = np.asarray(context.snap.get("rho"))
    if original_rho.shape != original_pressure.shape:
        original_rho = (
            context.cfg.physics.rho_l * original_psi
            + context.cfg.physics.rho_g * (1.0 - original_psi)
        )
    coords = context.snap.get("grid_coords")
    if coords is None:
        coords = [
            np.linspace(0.0, grid.LX, grid.NX + 1),
            np.linspace(0.0, grid.LY, grid.NY + 1),
        ]
    hodge_native = phase_hodge_pressure_representative(
        psi=original_psi,
        rho=original_rho,
        pressure=original_pressure,
        pressure_accel_faces=[
            np.asarray(component)
            for component in context.snap["pressure_accel_faces"]
        ],
        coords=[np.asarray(coord) for coord in coords],
        phase_threshold=float(spec.get("phase_threshold", 0.5)),
    )
    return remap_snapshot_field(context, hodge_native)


def snapshot_series_field_array(
    field: str,
    snap: dict,
    cfg: "ExperimentConfig",
    spec: dict,
) -> np.ndarray:
    """Return the scalar array whose color axis is shared for a snapshot."""
    context = build_snapshot_plot_context({"t_idx": 0}, {"snapshots": [snap]}, cfg)
    if field == "velocity":
        u = remap_snapshot_field(context, context.snap["u"])
        v = remap_snapshot_field(context, context.snap["v"])
        return np.sqrt(u ** 2 + v ** 2)
    if field == "psi":
        return context.psi
    if field == "pressure":
        return remap_snapshot_field(context, context.snap["p"])
    if field == "pressure_hodge":
        return pressure_hodge_field(context, spec)
    if field == "density":
        rho = context.snap.get("rho")
        if rho is not None:
            return remap_snapshot_field(context, rho)
        return cfg.physics.rho_l * context.psi + cfg.physics.rho_g * (1.0 - context.psi)
    raise ValueError(f"snapshot_series: unknown field '{field}'")


def build_snapshot_series_shared_spec(
    field: str,
    spec: dict,
    snaps: list[dict],
    cfg: "ExperimentConfig",
) -> dict:
    """Build fixed color/quiver limits shared by all snapshots in a series."""
    if not bool(spec.get("shared_scale", True)):
        return {}

    arrays = [snapshot_series_field_array(field, snap, cfg, spec) for snap in snaps]
    shared: dict = {}

    if field == "velocity":
        if "speed_vmax" not in spec:
            _, speed_max = finite_min_max(arrays)
            shared["speed_vmax"] = max(speed_max, 1.0e-14)
        normalize = bool(spec.get("normalize_arrows", True))
        if not normalize and "quiver_scale" not in spec:
            arrow_fraction = float(spec.get("quiver_length_fraction", 0.04))
            speed_vmax = float(shared.get("speed_vmax", spec.get("speed_vmax", 1.0)))
            shared["quiver_scale"] = max(speed_vmax / max(arrow_fraction, 1.0e-6), 1.0e-14)
        return shared

    if field in {"pressure", "pressure_hodge"}:
        if "vmin" not in spec or "vmax" not in spec:
            vmin, vmax = finite_min_max(arrays)
            if bool(spec.get("symmetric_scale", True)):
                bound = max(abs(vmin), abs(vmax), 1.0e-14)
                shared.setdefault("vmin", -bound)
                shared.setdefault("vmax", bound)
            else:
                shared.setdefault("vmin", vmin)
                shared.setdefault("vmax", vmax)
        return shared

    if field == "psi":
        shared.setdefault("vmin", spec.get("vmin", 0.0))
        shared.setdefault("vmax", spec.get("vmax", 1.0))
        return shared

    if "vmin" not in spec or "vmax" not in spec:
        vmin, vmax = finite_min_max(arrays)
        shared.setdefault("vmin", vmin)
        shared.setdefault("vmax", vmax)
    return shared


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
    cmap = spec.get("cmap", DEFAULT_SPEED_CMAP)
    vector_cmap = spec.get("vector_cmap", DEFAULT_VECTOR_CMAP)
    stride = int(spec.get("quiver_stride", 4))
    speed_vmax = spec.get("speed_vmax")
    if speed_vmax is None:
        speed_vmax = positive_range(speed)

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(
        context.X,
        context.Y,
        speed.T,
        cmap=cmap,
        vmin=0.0,
        vmax=float(speed_vmax),
        shading="nearest",
    )
    if spec.get("colorbar", True):
        cb = fig.colorbar(im, ax=ax, label="|u|", fraction=0.046, pad=0.04)
        cb.ax.tick_params(labelsize=8)
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    Xq, Yq = np.meshgrid(context.X, context.Y, indexing="ij")
    draw_clean_velocity_arrows(
        ax,
        Xq,
        Yq,
        u,
        v,
        stride=stride,
        normalize=bool(spec.get("normalize_arrows", True)),
        cmap=vector_cmap,
        scale=float(spec.get("quiver_scale", 30.0)),
        width=float(spec.get("quiver_width", 0.003)),
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


def masked_bulk_pressure(*args, **kwargs) -> np.ndarray:
    """Retired compatibility hook for the former masked pressure plot.

    DO NOT DELETE (C2): this name was once tested and may appear in old local
    notebooks.  It is intentionally fail-closed because masking
    ``0.05 < psi < 0.95`` hides the pressure representative in the fitted
    interface region.  Use ``pressure_hodge_snapshot`` for production pressure
    visualization, or ``pressure_snapshot`` for the stored raw scalar.
    """
    raise ValueError(
        "masked_bulk_pressure is retired: interface-band pressure must not be "
        "hidden. Use pressure_hodge for the face-cochain representative."
    )


def pressure_bulk_snapshot(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Retired masked bulk-pressure renderer.

    DO NOT DELETE (C2): old local YAMLs may still name ``pressure_bulk``.
    The former implementation hid the fitted interface band; that is now a
    fail-closed configuration error rather than a fallback visualization.
    """
    raise ValueError(
        "pressure_bulk is retired because it hides interface-band pressure. "
        "Use snapshot_series field 'pressure_hodge' instead."
    )


def pressure_hodge_snapshot(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Render a phase-wise Hodge pressure representative from face cochains."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    hodge_pressure = pressure_hodge_field(context, spec)
    title = spec.get("title", f"Hodge pressure at t = {context.t_val:.3f}")
    cmap = spec.get("cmap", "RdBu_r")

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    im = ax.pcolormesh(
        context.X,
        context.Y,
        hodge_pressure.T,
        cmap=cmap,
        vmin=spec.get("vmin"),
        vmax=spec.get("vmax"),
        shading="nearest",
    )
    if spec.get("colorbar", True):
        fig.colorbar(im, ax=ax, label="p (phase Hodge representative)")
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
    def render_snapshot(
        renderer: Callable[[dict, dict, "ExperimentConfig"], plt.Figure],
        snap: dict,
        cfg: "ExperimentConfig",
        spec: dict | None = None,
    ) -> plt.Figure:
        local_spec = dict(spec or {})
        local_spec["t_idx"] = 0
        return renderer(local_spec, {"snapshots": [snap]}, cfg)

    return {
        "density": lambda snap, cfg, spec=None: render_snapshot(
            density_snapshot, snap, cfg, spec
        ),
        "velocity": lambda snap, cfg, spec=None: render_snapshot(
            velocity_snapshot, snap, cfg, spec
        ),
        "psi": lambda snap, cfg, spec=None: render_snapshot(snapshot, snap, cfg, spec),
        "pressure": lambda snap, cfg, spec=None: render_snapshot(
            pressure_snapshot, snap, cfg, spec
        ),
        "pressure_hodge": lambda snap, cfg, spec=None: render_snapshot(
            pressure_hodge_snapshot, snap, cfg, spec
        ),
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
    shared_spec = build_snapshot_series_shared_spec(field, spec, snaps, cfg)
    render_spec = {**spec, **shared_spec}

    for snap in snaps:
        t_val = snap["t"]
        fig = renderer(snap, cfg, render_spec)
        fig.savefig(outdir / f"{prefix}{t_val:.3f}.pdf", bbox_inches="tight")
        plt.close(fig)
