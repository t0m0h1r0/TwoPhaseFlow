"""
ベクトル場の可視化モジュール。

速度場・渦度場・流線など典型的な CFD ベクトル場の可視化関数を提供する。
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple, TYPE_CHECKING

from .plot_fields import (
    DEFAULT_INTERFACE_COLOR,
    DEFAULT_QUIVER_SCALE,
    DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    DEFAULT_QUIVER_WIDTH,
    DEFAULT_SPEED_CMAP,
    DEFAULT_VECTOR_CMAP,
    DEFAULT_VECTOR_COLOR,
    DEFAULT_VECTOR_OUTLINE_COLOR,
    draw_clean_velocity_arrows,
    positive_range,
)

if TYPE_CHECKING:
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


def plot_velocity(
    u: np.ndarray,
    v: np.ndarray,
    grid: "Grid",
    *,
    title: str = "速度場",
    speed_cmap: str = DEFAULT_SPEED_CMAP,
    vector_cmap: str = DEFAULT_VECTOR_CMAP,
    vector_color: Optional[str] = DEFAULT_VECTOR_COLOR,
    vector_outline_color: Optional[str] = DEFAULT_VECTOR_OUTLINE_COLOR,
    vector_color_vmax: Optional[float] = None,
    quiver_stride: int = 4,
    normalize_arrows: bool = True,
    quiver_scale: float = DEFAULT_QUIVER_SCALE,
    quiver_width: float = DEFAULT_QUIVER_WIDTH,
    quiver_outline_width_factor: float = DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    quiver_min_display_speed: Optional[float] = None,
    speed_vmax: Optional[float] = None,
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[float, float] = (6, 5),
    dpi: int = 100,
) -> plt.Figure:
    """速度場を速度大きさのカラーマップ＋矢印で表示する。

    Parameters
    ----------
    u, v : x,y 方向速度成分、shape ``grid.shape``
    grid : Grid
    title : タイトル
    speed_cmap : 速度の大きさに使うカラーマップ
    vector_cmap : vector_color=None の場合に矢印を速度で着色するカラーマップ
    vector_color : 矢印本体色。None の場合は vector_cmap で速度着色
    vector_outline_color : 矢印の下敷き色。None の場合は下敷きなし
    quiver_stride : 矢印を描くサンプリング間隔（間引き）
    normalize_arrows : True の場合、矢印長は方向表示用に正規化
    speed_vmax : 速度背景の上限（None の場合は robust percentile）
    quiver_min_display_speed : これ以下の速度ベクトルは矢印表示しない
    interface_psi : 界面表示用 ψ フィールド
    save_path : 保存先パス
    ax : 既存の Axes
    figsize, dpi : 図サイズと解像度

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    if grid.ndim != 2:
        raise NotImplementedError("現在は2次元のみサポートしています。")

    u_np = np.asarray(u)
    v_np = np.asarray(v)
    speed = np.sqrt(u_np ** 2 + v_np ** 2)
    X, Y = grid.meshgrid()

    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    else:
        fig = ax.get_figure()

    vmax = speed_vmax if speed_vmax is not None else positive_range(speed)
    im = ax.pcolormesh(X, Y, speed, cmap=speed_cmap, vmin=0.0, vmax=vmax,
                       shading="auto")
    cb = fig.colorbar(im, ax=ax, label="|u|", fraction=0.046, pad=0.04)
    cb.ax.tick_params(labelsize=8)

    draw_clean_velocity_arrows(
        ax,
        np.asarray(X),
        np.asarray(Y),
        u_np,
        v_np,
        stride=quiver_stride,
        normalize=normalize_arrows,
        cmap=vector_cmap,
        color=vector_color,
        outline_color=vector_outline_color,
        color_vmax=vector_color_vmax,
        scale=quiver_scale,
        width=quiver_width,
        outline_width_factor=quiver_outline_width_factor,
        min_display_speed=quiver_min_display_speed,
    )

    if interface_psi is not None:
        ax.contour(X, Y, np.asarray(interface_psi), levels=[0.5],
                   colors=DEFAULT_INTERFACE_COLOR, linewidths=0.9)

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.set_title(title)

    if save_path is not None:
        fig.savefig(save_path, bbox_inches="tight", dpi=dpi)
    return fig


def compute_vorticity_2d(
    u: np.ndarray,
    v: np.ndarray,
    ccd: "CCDSolver",
) -> np.ndarray:
    """2次元渦度 ω = ∂v/∂x − ∂u/∂y を CCD で計算する。

    Parameters
    ----------
    u, v : 速度成分
    ccd  : CCDSolver（空間微分に使用）

    Returns
    -------
    omega : array, shape と同じ
    """
    dv_dx, _ = ccd.differentiate(v, 0)
    du_dy, _ = ccd.differentiate(u, 1)
    return dv_dx - du_dy


def plot_vorticity(
    u: np.ndarray,
    v: np.ndarray,
    grid: "Grid",
    ccd: "CCDSolver",
    *,
    title: str = "渦度 ω = ∂v/∂x − ∂u/∂y",
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[float, float] = (6, 5),
    dpi: int = 100,
) -> plt.Figure:
    """渦度場を可視化する。

    Parameters
    ----------
    u, v : 速度成分
    grid : Grid
    ccd  : CCDSolver（渦度計算に使用）
    title : タイトル
    interface_psi : 界面表示用 ψ
    save_path, ax, figsize, dpi : 表示・保存オプション

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    from .plot_scalar import plot_scalar_field

    omega = compute_vorticity_2d(np.asarray(u), np.asarray(v), ccd)
    return plot_scalar_field(
        omega, grid, title=title, cmap="seismic",
        colorbar_label="ω", interface_psi=interface_psi,
        save_path=save_path, ax=ax, figsize=figsize, dpi=dpi,
    )


def plot_streamlines(
    u: np.ndarray,
    v: np.ndarray,
    grid: "Grid",
    *,
    title: str = "流線",
    density: float = 1.0,
    color: str = "k",
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[float, float] = (6, 5),
    dpi: int = 100,
) -> plt.Figure:
    """流線を描画する。

    Parameters
    ----------
    u, v : 速度成分
    grid : Grid
    density : streamplot の密度パラメータ
    color : 流線の色
    その他 : plot_velocity と同じ

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    if grid.ndim != 2:
        raise NotImplementedError("現在は2次元のみサポートしています。")

    u_np = np.asarray(u).T  # streamplot は (y, x) 順序を期待
    v_np = np.asarray(v).T
    X, Y = grid.meshgrid()
    x1d = X[:, 0]
    y1d = Y[0, :]

    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    else:
        fig = ax.get_figure()

    ax.streamplot(x1d, y1d, u_np, v_np, density=density, color=color)

    if interface_psi is not None:
        ax.contour(X, Y, np.asarray(interface_psi), levels=[0.5],
                   colors="red", linewidths=1.5, linestyles="--")

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    ax.set_title(title)

    if save_path is not None:
        fig.savefig(save_path, bbox_inches="tight", dpi=dpi)
    return fig
