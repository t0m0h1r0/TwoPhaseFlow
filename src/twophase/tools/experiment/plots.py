"""Reusable plotting primitives for experiment scripts.

All functions accept and return plain matplotlib objects so callers retain
full control over layout.  The goal is to eliminate copy-paste, not to hide
matplotlib behind an opaque API.

Typical usage::

    from twophase.tools.experiment.plots import (
        field_panel, convergence_loglog, time_history, latex_convergence_table,
    )
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.image import AxesImage


# ── 2-D field visualisation ───────────────────────────────────────────────────

def field_panel(
    ax: Axes,
    X: np.ndarray,
    Y: np.ndarray,
    field: np.ndarray,
    *,
    cmap: str = "RdBu_r",
    vlim: float | tuple[float, float] | None = None,
    contour_field: np.ndarray | None = None,
    contour_levels: Sequence[float] = (0.0,),
    contour_color: str = "k",
    contour_lw: float = 0.8,
    colorbar: bool = True,
    cb_label: str = "",
    annotation: str = "",
    title: str = "",
) -> AxesImage:
    """Draw a pcolormesh field with optional interface contour and annotation.

    Parameters
    ----------
    ax : Axes
        Target axes.
    X, Y : ndarray
        Coordinate arrays (meshgrid output).
    field : ndarray
        Scalar field to plot.
    cmap : str
        Colormap name.
    vlim : float or (vmin, vmax), optional
        Symmetric ``(-v, v)`` if scalar, explicit range if tuple.
        ``None`` → auto from data.
    contour_field : ndarray, optional
        Field for contour overlay (e.g. level-set φ).
    contour_levels : sequence of float
        Contour levels.
    colorbar : bool
        Attach a per-axes colorbar.
    annotation : str
        Text annotation in lower-left corner.
    title : str
        Axes title.

    Returns
    -------
    AxesImage
        The pcolormesh artist (useful for shared colorbars).
    """
    if vlim is None:
        vmin, vmax = None, None
    elif isinstance(vlim, (int, float)):
        vmin, vmax = -float(vlim), float(vlim)
    else:
        vmin, vmax = vlim

    im = ax.pcolormesh(X, Y, field, cmap=cmap, vmin=vmin, vmax=vmax, shading="auto")

    if contour_field is not None:
        ax.contour(
            X, Y, contour_field,
            levels=list(contour_levels), colors=contour_color, linewidths=contour_lw,
        )

    ax.set_aspect("equal")
    ax.tick_params(labelsize=7)

    if title:
        ax.set_title(title, fontsize=9, fontweight="bold")

    if colorbar:
        cb = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.ax.tick_params(labelsize=7)
        if cb_label:
            cb.set_label(cb_label, fontsize=8)

    if annotation:
        ax.text(
            0.02, 0.03, annotation,
            transform=ax.transAxes, fontsize=7, va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.8),
        )

    return im


# ── Convergence (log-log) ────────────────────────────────────────────────────

def convergence_loglog(
    ax: Axes,
    hs: Sequence[float],
    errors: dict[str, Sequence[float]],
    *,
    ref_orders: Sequence[int] = (2, 4, 6),
    xlabel: str = "$h$",
    ylabel: str = "Error",
    title: str = "",
) -> None:
    """Log-log convergence plot with reference slopes.

    Parameters
    ----------
    ax : Axes
        Target axes.
    hs : sequence of float
        Grid spacings (x-axis).
    errors : dict[str, sequence of float]
        ``{label: error_values}`` — each series is a line.
    ref_orders : sequence of int
        Reference slope orders to draw as dashed grey lines.
    """
    from .style import COLORS, MARKERS

    h_arr = np.asarray(hs, dtype=float)

    for i, (label, errs) in enumerate(errors.items()):
        c = COLORS[i % len(COLORS)]
        m = MARKERS[i % len(MARKERS)]
        ax.loglog(h_arr, errs, marker=m, color=c, label=label)

    # Reference slopes
    h_ref = np.array([h_arr[0], h_arr[-1]])
    for order in ref_orders:
        # anchor to the geometric mean of first series
        first_errs = list(errors.values())[0]
        e0 = float(first_errs[0])
        e_ref = e0 * (h_ref / h_ref[0]) ** order
        ax.loglog(h_ref, e_ref, "--", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=10)
    ax.legend(fontsize=7)
    ax.grid(True, which="both", alpha=0.3)


# ── Time history ──────────────────────────────────────────────────────────────

def time_history(
    ax: Axes,
    series: dict[str, tuple[np.ndarray, np.ndarray]],
    *,
    log_y: bool = True,
    xlabel: str = "$t$",
    ylabel: str = "",
    title: str = "",
) -> None:
    """Plot one or more time series.

    Parameters
    ----------
    series : dict[str, (t_array, y_array)]
        ``{label: (times, values)}``.
    log_y : bool
        Use semilogy scale.
    """
    from .style import COLORS

    for i, (label, (t, y)) in enumerate(series.items()):
        c = COLORS[i % len(COLORS)]
        if log_y:
            ax.semilogy(t, y, color=c, label=label)
        else:
            ax.plot(t, y, color=c, label=label)

    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title, fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(True, which="both" if log_y else "major", ls="--", alpha=0.4)


# ── LaTeX convergence table ──────────────────────────────────────────────────

def latex_convergence_table(
    path: str,
    results: Sequence[dict],
    columns: Sequence[str],
    *,
    title: str = "",
    N_key: str = "N",
) -> None:
    """Write a LaTeX convergence table with automatic slope computation.

    Parameters
    ----------
    path : str
        Output ``.tex`` file path.
    results : list of dict
        Each dict has ``N_key`` plus error columns.
    columns : list of str
        Error column keys to include (e.g. ``["d1x_L2", "d2x_Li"]``).
    title : str
        Comment at the top of the file.
    N_key : str
        Key for the grid resolution.
    """
    import pathlib

    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Compute slopes
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_h = np.log(float(r1.get("h", 1.0 / r1[N_key]))
                       / float(r0.get("h", 1.0 / r0[N_key])))
        if abs(log_h) < 1e-15:
            continue
        for col in columns:
            v0, v1 = float(r0.get(col, 0)), float(r1.get(col, 0))
            if v0 > 0 and v1 > 0:
                r1[f"{col}_slope"] = np.log(v1 / v0) / log_h

    col_spec = "r" + "rr" * len(columns)
    lines = [f"% {title}" if title else "% Auto-generated convergence table"]
    lines.append(f"\\begin{{tabular}}{{{col_spec}}}")
    lines.append("\\toprule")

    header = f"${N_key}$"
    for col in columns:
        nice = col.replace("_L2", " $L_2$").replace("_Li", r" $L_\infty$")
        header += f" & {nice} & slope"
    lines.append(header + r" \\")
    lines.append("\\midrule")

    for r in results:
        row = f"{r[N_key]}"
        for col in columns:
            val = float(r.get(col, 0))
            slope = r.get(f"{col}_slope", None)
            if slope is None or np.isnan(slope):
                row += f" & {val:.2e} & ---"
            else:
                row += f" & {val:.2e} & {slope:.2f}"
        lines.append(row + r" \\")

    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")

    p.write_text("\n".join(lines) + "\n")
    print(f"Saved table → {p}")


# ── Summary text box ─────────────────────────────────────────────────────────

def summary_text(
    fig: Figure,
    rows: Sequence[str],
    *,
    x: float = 0.01,
    y: float = 0.005,
) -> None:
    """Place a monospace summary table at the bottom of a figure."""
    fig.text(
        x, y, "\n".join(rows), fontsize=8,
        family="monospace", va="bottom",
        bbox=dict(boxstyle="round", fc="lightyellow", alpha=0.8),
    )
