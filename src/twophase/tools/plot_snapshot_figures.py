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
    DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    DEFAULT_SPEED_CMAP,
    DEFAULT_VECTOR_CMAP,
    DEFAULT_VECTOR_COLOR,
    DEFAULT_VECTOR_OUTLINE_COLOR,
    draw_clean_velocity_arrows,
    positive_range,
)
from .pressure_representatives import phase_hodge_pressure_representative_diagnostics

DEFAULT_PRESSURE_HODGE_MAX_RELATIVE_RESIDUAL = 1.0e-2

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


def pressure_difference_field(pressure: np.ndarray, spec: dict) -> np.ndarray:
    """Return the gauge-fixed pressure field requested by a figure spec."""
    values = np.asarray(pressure, dtype=float)
    if "pressure_reference_value" in spec:
        return values - float(spec["pressure_reference_value"])
    reference = str(
        spec.get("pressure_reference", spec.get("reference", "raw"))
    ).strip().lower()
    if reference in {"raw", "none", "absolute"}:
        return values
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return values
    if reference in {"mean", "spatial_mean"}:
        return values - float(np.mean(finite))
    if reference == "median":
        return values - float(np.median(finite))
    raise ValueError(
        "pressure_reference must be 'raw', 'mean', 'spatial_mean', 'median', "
        "or a numeric pressure_reference_value"
    )


def pressure_plot_field(context: SnapshotPlotContext, spec: dict) -> np.ndarray:
    """Return the scalar pressure representation used for color plotting."""
    return pressure_difference_field(
        remap_snapshot_field(context, context.snap["p"]),
        spec,
    )


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
    diagnostics = phase_hodge_pressure_representative_diagnostics(
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
    max_relative_residual = spec.get(
        "max_relative_residual",
        DEFAULT_PRESSURE_HODGE_MAX_RELATIVE_RESIDUAL,
    )
    if (
        max_relative_residual is not None
        and diagnostics.face_relative_residual > float(max_relative_residual)
    ):
        raise ValueError(
            "pressure_hodge cannot represent the saved affine face cochain as "
            "a scalar pressure field: "
            f"relative same-phase gradient residual "
            f"{diagnostics.face_relative_residual:.6e} exceeds "
            f"{float(max_relative_residual):.6e} "
            f"(Linf residual {diagnostics.face_residual_linf:.6e}, "
            f"faces {diagnostics.used_face_count}). "
            "Use the stored scalar pressure field only as a gauge quantity, or "
            "plot a face-cochain residual diagnostic instead of labeling this "
            "Hodge projection as physical pressure."
        )
    return remap_snapshot_field(context, diagnostics.pressure)


def velocity_color_center(context: SnapshotPlotContext, spec: dict) -> tuple[float, float]:
    """Return the center used by signed radial velocity visualization."""
    center = spec.get("velocity_center", "phase_centroid")
    grid = context.cfg.grid
    if isinstance(center, (list, tuple)) and len(center) == 2:
        return float(center[0]), float(center[1])
    if center == "domain_center":
        return 0.5 * grid.LX, 0.5 * grid.LY
    if center != "phase_centroid":
        raise ValueError(
            "velocity_center must be 'phase_centroid', 'domain_center', or [x, y]"
        )

    Xg, Yg = np.meshgrid(context.X, context.Y, indexing="ij")
    weights = np.clip(np.asarray(context.psi, dtype=float), 0.0, 1.0)
    total = float(np.sum(weights))
    if total <= 1.0e-14:
        return 0.5 * grid.LX, 0.5 * grid.LY
    cx = float(np.sum(weights * Xg) / total)
    cy = float(np.sum(weights * Yg) / total)
    return cx, cy


def velocity_color_field(
    context: SnapshotPlotContext,
    u: np.ndarray,
    v: np.ndarray,
    spec: dict,
) -> tuple[np.ndarray, str]:
    """Return the scalar field used to color a velocity snapshot."""
    quantity = str(spec.get("color_quantity", "speed"))
    if quantity == "speed":
        return np.sqrt(u ** 2 + v ** 2), "|u|"
    if quantity == "u":
        return u, "$u_x$"
    if quantity == "v":
        return v, "$u_y$"
    if quantity == "radial":
        cx, cy = velocity_color_center(context, spec)
        Xg, Yg = np.meshgrid(context.X, context.Y, indexing="ij")
        rx = Xg - cx
        ry = Yg - cy
        radius = np.sqrt(rx ** 2 + ry ** 2)
        radius = np.maximum(radius, 1.0e-14)
        return (u * rx + v * ry) / radius, "$u_r$"
    raise ValueError("velocity color_quantity must be 'speed', 'u', 'v', or 'radial'")


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
        color_field, _ = velocity_color_field(context, u, v, spec)
        return color_field
    if field == "psi":
        return context.psi
    if field == "pressure":
        return pressure_plot_field(context, spec)
    if field == "pressure_hodge":
        return pressure_difference_field(pressure_hodge_field(context, spec), spec)
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
        speed_arrays = []
        for snap in snaps:
            context = build_snapshot_plot_context({"t_idx": 0}, {"snapshots": [snap]}, cfg)
            u = remap_snapshot_field(context, context.snap["u"])
            v = remap_snapshot_field(context, context.snap["v"])
            speed_arrays.append(np.sqrt(u ** 2 + v ** 2))
        _, speed_max = finite_min_max(speed_arrays)
        color_quantity = str(spec.get("color_quantity", "speed"))
        finite_values = np.concatenate(
            [np.asarray(array, dtype=float).ravel() for array in arrays]
        )
        if color_quantity == "speed":
            if "speed_vmax" not in spec:
                color_scale = str(spec.get("color_scale", spec.get("speed_scale", "max")))
                if color_scale == "max":
                    shared["speed_vmax"] = max(speed_max, 1.0e-14)
                elif color_scale == "robust":
                    shared["speed_vmax"] = positive_range(
                        finite_values,
                        percentile=float(spec.get("speed_vmax_percentile", 99.0)),
                        margin=float(spec.get("speed_vmax_margin", 1.05)),
                    )
                else:
                    raise ValueError(
                        "snapshot_series velocity color_scale must be 'max' or 'robust'"
                    )
        else:
            if "vmin" not in spec or "vmax" not in spec:
                color_scale = str(spec.get("color_scale", "robust"))
                if bool(spec.get("symmetric_scale", True)):
                    if color_scale == "max":
                        vmin, vmax = finite_min_max(arrays)
                        bound = max(abs(vmin), abs(vmax), 1.0e-14)
                    elif color_scale == "robust":
                        bound = positive_range(
                            finite_values,
                            percentile=float(spec.get("color_vmax_percentile", 99.0)),
                            margin=float(spec.get("color_vmax_margin", 1.05)),
                        )
                    else:
                        raise ValueError(
                            "snapshot_series velocity color_scale must be 'max' or 'robust'"
                        )
                    shared.setdefault("vmin", -bound)
                    shared.setdefault("vmax", bound)
                else:
                    vmin, vmax = finite_min_max(arrays)
                    shared.setdefault("vmin", vmin)
                    shared.setdefault("vmax", vmax)
            shared.setdefault("speed_vmax", max(speed_max, 1.0e-14))
        normalize = bool(spec.get("normalize_arrows", True))
        if not normalize and "quiver_scale" not in spec:
            arrow_fraction = float(spec.get("quiver_length_fraction", 0.04))
            shared["quiver_scale"] = max(
                speed_max / max(arrow_fraction, 1.0e-6), 1.0e-14
            )
        return shared

    if field in {"pressure", "pressure_hodge"}:
        if "vmin" not in spec or "vmax" not in spec:
            color_scale = str(spec.get("color_scale", "max")).strip().lower()
            if bool(spec.get("symmetric_scale", True)):
                finite_values = np.concatenate(
                    [np.asarray(array, dtype=float).ravel() for array in arrays]
                )
                if color_scale == "max":
                    vmin, vmax = finite_min_max(arrays)
                    bound = max(abs(vmin), abs(vmax), 1.0e-14)
                elif color_scale == "robust":
                    bound = positive_range(
                        finite_values,
                        percentile=float(spec.get("color_vmax_percentile", 99.0)),
                        margin=float(spec.get("color_vmax_margin", 1.05)),
                    )
                else:
                    raise ValueError(
                        "snapshot_series pressure color_scale must be 'max' or 'robust'"
                    )
                shared.setdefault("vmin", -bound)
                shared.setdefault("vmax", bound)
            else:
                vmin, vmax = finite_min_max(arrays)
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
    """Render a velocity snapshot with optional scalar field and quiver arrows."""
    context = build_snapshot_plot_context(spec, results, cfg)
    grid = cfg.grid
    u = remap_snapshot_field(context, context.snap["u"])
    v = remap_snapshot_field(context, context.snap["v"])
    speed = np.sqrt(u ** 2 + v ** 2)
    color_field, color_label = velocity_color_field(context, u, v, spec)
    title = spec.get("title", f"Velocity at t = {context.t_val:.3f}")
    show_field = bool(spec.get("show_field", True))
    cmap = spec.get("cmap", DEFAULT_SPEED_CMAP)
    vector_cmap = spec.get("vector_cmap", DEFAULT_VECTOR_CMAP)
    arrow_color = spec.get(
        "arrow_color", DEFAULT_VECTOR_COLOR if show_field else None
    )
    arrow_outline_color = spec.get("arrow_outline_color", DEFAULT_VECTOR_OUTLINE_COLOR)
    stride = int(spec.get("quiver_stride", 4))
    color_quantity = str(spec.get("color_quantity", "speed"))
    speed_vmax = spec.get("speed_vmax")
    if speed_vmax is None:
        speed_vmax = max(float(np.nanmax(speed)), 1.0e-14)
    if color_quantity == "speed":
        vmin = 0.0
        vmax = float(speed_vmax)
    else:
        vmin = spec.get("vmin")
        vmax = spec.get("vmax")
        if vmin is None or vmax is None:
            if bool(spec.get("symmetric_scale", True)):
                bound = positive_range(
                    color_field,
                    percentile=float(spec.get("color_vmax_percentile", 99.0)),
                    margin=float(spec.get("color_vmax_margin", 1.05)),
                )
                vmin = -bound
                vmax = bound
            else:
                vmin, vmax = finite_min_max([color_field])
    min_display_speed = spec.get("quiver_min_display_speed")
    if min_display_speed is None and "quiver_min_speed_fraction" in spec:
        min_display_speed = float(spec["quiver_min_speed_fraction"]) * float(speed_vmax)

    fig, ax = plt.subplots(figsize=(4, 4 * grid.LY / grid.LX))
    ax.set_facecolor(spec.get("background_color", "#eeeeee"))
    if show_field:
        im = ax.pcolormesh(
            context.X,
            context.Y,
            color_field.T,
            cmap=cmap,
            vmin=float(vmin),
            vmax=float(vmax),
            shading=spec.get("shading", "nearest"),
            alpha=float(spec.get("field_alpha", 1.0)),
        )
        if spec.get("colorbar", True):
            cb = fig.colorbar(
                im,
                ax=ax,
                label=spec.get("colorbar_label", color_label),
                fraction=0.046,
                pad=0.04,
            )
            cb.ax.tick_params(labelsize=8)
    if spec.get("contour", True):
        ax.contour(
            context.X, context.Y, context.psi.T, levels=[0.5], colors="k", linewidths=0.8
        )
    Xq, Yq = np.meshgrid(context.X, context.Y, indexing="ij")
    quiver = draw_clean_velocity_arrows(
        ax,
        Xq,
        Yq,
        u,
        v,
        stride=stride,
        normalize=bool(spec.get("normalize_arrows", True)),
        cmap=vector_cmap,
        color=arrow_color,
        outline_color=arrow_outline_color,
        color_vmin=0.0,
        color_vmax=float(speed_vmax),
        alpha=float(spec.get("arrow_alpha", 0.9)),
        outline_alpha=float(spec.get("arrow_outline_alpha", 0.75)),
        scale=float(spec.get("quiver_scale", 30.0)),
        width=float(spec.get("quiver_width", 0.003)),
        outline_width_factor=float(
            spec.get("quiver_outline_width_factor", DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR)
        ),
        min_display_speed=(
            None if min_display_speed is None else float(min_display_speed)
        ),
    )
    if not show_field and spec.get("colorbar", True):
        cb = fig.colorbar(
            quiver,
            ax=ax,
            label=spec.get("colorbar_label", "|u|"),
            fraction=0.046,
            pad=0.04,
        )
        cb.ax.tick_params(labelsize=8)
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
    p = pressure_plot_field(context, spec)
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
        fig.colorbar(im, ax=ax, label=spec.get("colorbar_label", "p"))
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
    hodge_pressure = pressure_difference_field(pressure_hodge_field(context, spec), spec)
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
        fig.colorbar(
            im,
            ax=ax,
            label=spec.get("colorbar_label", "p (phase Hodge representative)"),
        )
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
