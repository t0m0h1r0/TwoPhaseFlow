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
    speed_cmap: str = "YlOrRd",
    speed_vmax: Optional[float] = None,
    bg_alpha: float = 0.5,
    contour_field: Optional[np.ndarray] = None,
    contour_level: float = 0.0,
    contour_color: str = "r",
) -> None:
    """Quiver plot with speed-colored background."""
    speed = np.sqrt(u ** 2 + v ** 2)
    vmax = speed_vmax or max(float(speed.max()), 1e-10)
    ax.pcolormesh(x1d, y1d, speed.T, cmap=speed_cmap, vmin=0,
                  vmax=vmax, shading="auto", alpha=bg_alpha)
    s = stride
    ax.quiver(X[::s, ::s], Y[::s, ::s], u[::s, ::s], v[::s, ::s],
              color="k", alpha=0.8, scale=None)
    if contour_field is not None:
        ax.contour(x1d, y1d, contour_field.T, levels=[contour_level],
                   colors=contour_color, linewidths=1.5)
    ax.set_aspect("equal")


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
