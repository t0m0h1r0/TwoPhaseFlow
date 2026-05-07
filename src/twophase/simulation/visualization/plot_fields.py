"""Multi-panel 2D field visualization helpers.

Thin wrappers around matplotlib for the common viz-script pattern:
  pcolormesh(x1d, y1d, field.T) + contour overlay + aspect equal

All functions operate on plain Axes for maximum composability.
Designed for experiment/ch12/viz_ch12_*.py scripts.
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from typing import Optional, Sequence

DEFAULT_SPEED_CMAP = "viridis"
DEFAULT_VECTOR_CMAP = "hot"
DEFAULT_VECTOR_COLOR = "#111827"
DEFAULT_VECTOR_OUTLINE_COLOR = "#ffffff"
DEFAULT_INTERFACE_COLOR = "k"
DEFAULT_QUIVER_SCALE = 30.0
DEFAULT_QUIVER_WIDTH = 0.003
DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR = 2.2


def field_with_contour(
    ax: Axes,
    x1d: np.ndarray,
    y1d: np.ndarray,
    field: np.ndarray,
    *,
    cmap: str = "RdBu_r",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    contour_field: Optional[np.ndarray] = None,
    contour_level: float = 0.5,
    contour_color: str = "k",
    contour_lw: float = 1.2,
    contour_ls: str = "-",
    title: str = "",
    xlabel: str = "$x$",
    ylabel: str = "",
    xlim: Optional[tuple] = None,
    ylim: Optional[tuple] = None,
) -> AxesImage:
    """Pcolormesh of field(x,y) with optional interface contour overlay.

    Parameters
    ----------
    field : (Nx, Ny) — transposed internally for pcolormesh.
    contour_field : same shape as field; contour at contour_level.

    Returns
    -------
    AxesImage — for shared colorbars via fig.colorbar(im, ax=...).
    """
    im = ax.pcolormesh(x1d, y1d, field.T, cmap=cmap,
                       vmin=vmin, vmax=vmax, shading="auto")
    if contour_field is not None:
        ax.contour(x1d, y1d, contour_field.T, levels=[contour_level],
                   colors=contour_color, linewidths=contour_lw,
                   linestyles=contour_ls)
    if title:
        ax.set_title(title, fontsize=11)
    ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=11)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    return im


def streamlines_colored(
    ax: Axes,
    x1d: np.ndarray,
    y1d: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    *,
    cmap: str = "viridis",
    density: float = 1.5,
    linewidth: float = 1.0,
    arrowsize: float = 1.0,
    contour_field: Optional[np.ndarray] = None,
    contour_level: float = 0.5,
    contour_color: str = "r",
    contour_lw: float = 1.5,
    bg_color: str = "#f8f8f8",
    min_speed: float = 1e-10,
) -> None:
    """Streamplot colored by velocity magnitude.

    u, v shape: (Nx, Ny) — transposed internally.
    Skips streamplot if max speed < min_speed.
    """
    speed = np.sqrt(u ** 2 + v ** 2)
    if float(np.max(np.abs(u))) > min_speed:
        ax.streamplot(x1d, y1d, u.T, v.T,
                      color=speed.T, cmap=cmap,
                      density=density, linewidth=linewidth,
                      arrowsize=arrowsize)
    if contour_field is not None:
        ax.contour(x1d, y1d, contour_field.T, levels=[contour_level],
                   colors=contour_color, linewidths=contour_lw)
    ax.set_aspect("equal")
    ax.set_facecolor(bg_color)


def velocity_arrows(
    ax: Axes,
    X: np.ndarray,
    Y: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    x1d: np.ndarray,
    y1d: np.ndarray,
    *,
    stride: int = 4,
    speed_cmap: str = DEFAULT_SPEED_CMAP,
    vector_cmap: str = DEFAULT_VECTOR_CMAP,
    vector_color: Optional[str] = DEFAULT_VECTOR_COLOR,
    vector_outline_color: Optional[str] = DEFAULT_VECTOR_OUTLINE_COLOR,
    speed_vmax: Optional[float] = None,
    bg_alpha: float = 0.5,
    normalize_arrows: bool = True,
    quiver_scale: float = DEFAULT_QUIVER_SCALE,
    quiver_width: float = DEFAULT_QUIVER_WIDTH,
    quiver_outline_width_factor: float = DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    quiver_min_display_speed: Optional[float] = None,
    contour_field: Optional[np.ndarray] = None,
    contour_level: float = 0.0,
    contour_color: str = DEFAULT_INTERFACE_COLOR,
) -> None:
    """Quiver plot with speed-colored background.

    The default matches the clean diagnostic figures used for ch14: a calm
    scalar speed background plus arrows colored by local speed.  Arrow lengths
    are normalized by default so direction remains readable when the velocity
    magnitude spans orders of magnitude.
    """
    speed = np.sqrt(u ** 2 + v ** 2)
    vmax = speed_vmax or positive_range(speed)
    ax.pcolormesh(x1d, y1d, speed.T, cmap=speed_cmap, vmin=0,
                  vmax=vmax, shading="auto", alpha=bg_alpha)
    draw_clean_velocity_arrows(
        ax,
        X,
        Y,
        u,
        v,
        stride=stride,
        normalize=normalize_arrows,
        cmap=vector_cmap,
        color=vector_color,
        outline_color=vector_outline_color,
        scale=quiver_scale,
        width=quiver_width,
        outline_width_factor=quiver_outline_width_factor,
        min_display_speed=quiver_min_display_speed,
    )
    if contour_field is not None:
        ax.contour(x1d, y1d, contour_field.T, levels=[contour_level],
                   colors=contour_color, linewidths=1.5)
    ax.set_aspect("equal")


def draw_clean_velocity_arrows(
    ax: Axes,
    X: np.ndarray,
    Y: np.ndarray,
    u: np.ndarray,
    v: np.ndarray,
    *,
    stride: int = 4,
    normalize: bool = True,
    cmap: str = DEFAULT_VECTOR_CMAP,
    color: Optional[str] = DEFAULT_VECTOR_COLOR,
    outline_color: Optional[str] = DEFAULT_VECTOR_OUTLINE_COLOR,
    alpha: float = 0.85,
    outline_alpha: float = 0.75,
    scale: float = DEFAULT_QUIVER_SCALE,
    width: float = DEFAULT_QUIVER_WIDTH,
    outline_width_factor: float = DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    headwidth: float = 3.6,
    headlength: float = 4.8,
    headaxislength: float = 4.2,
    min_speed: float = 1.0e-14,
    min_display_speed: Optional[float] = None,
):
    """Draw sparse velocity arrows with ch14 diagnostic styling.

    Symbol mapping
    --------------
    ``u, v`` : nodal velocity components on the same 2-D grid as ``X, Y``.

    Returns
    -------
    matplotlib.quiver.Quiver
        The quiver artist, useful for tests or caller-managed legends.
    """
    stride = max(int(stride), 1)
    Xs = np.asarray(X)[::stride, ::stride]
    Ys = np.asarray(Y)[::stride, ::stride]
    us = np.asarray(u)[::stride, ::stride]
    vs = np.asarray(v)[::stride, ::stride]
    speed = np.sqrt(us ** 2 + vs ** 2)
    if min_display_speed is not None:
        visible = speed > max(float(min_display_speed), min_speed)
        Xs = Xs[visible]
        Ys = Ys[visible]
        us = us[visible]
        vs = vs[visible]
        speed = speed[visible]
    if normalize:
        denom = np.maximum(speed, min_speed)
        uq = us / denom
        vq = vs / denom
        scale_arg = scale
    else:
        uq = us
        vq = vs
        scale_arg = scale
    common_kwargs = dict(
        scale=scale_arg,
        headwidth=headwidth,
        headlength=headlength,
        headaxislength=headaxislength,
        pivot="middle",
    )
    if outline_color is not None:
        ax.quiver(
            Xs,
            Ys,
            uq,
            vq,
            color=outline_color,
            alpha=outline_alpha,
            width=width * outline_width_factor,
            zorder=3.0,
            **common_kwargs,
        )
    if color is not None:
        return ax.quiver(
            Xs,
            Ys,
            uq,
            vq,
            color=color,
            alpha=alpha,
            width=width,
            zorder=3.1,
            **common_kwargs,
        )
    return ax.quiver(
        Xs,
        Ys,
        uq,
        vq,
        speed,
        cmap=cmap,
        alpha=alpha,
        scale=scale_arg,
        width=width,
        headwidth=headwidth,
        headlength=headlength,
        headaxislength=headaxislength,
        pivot="middle",
        zorder=3.1,
    )


def positive_range(
    array: np.ndarray,
    *,
    percentile: float = 99.0,
    margin: float = 1.05,
    floor: float = 1.0e-14,
) -> float:
    """Compute a robust positive color limit for magnitude fields."""
    values = np.asarray(array, dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return floor
    vmax = float(np.percentile(np.abs(finite), percentile)) * margin
    return max(vmax, floor)


def symmetric_range(
    arrays: Sequence[np.ndarray],
    *,
    percentile: float = 98,
    margin: float = 1.05,
    floor: float = 1e-10,
) -> float:
    """Compute symmetric vmax from concatenated arrays.

    Returns vmax such that the colorbar range is (-vmax, vmax).
    """
    all_vals = np.concatenate([a.ravel() for a in arrays])
    vmax = float(np.percentile(np.abs(all_vals), percentile)) * margin
    return max(vmax, floor)
