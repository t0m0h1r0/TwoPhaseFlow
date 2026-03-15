"""
ベクトル場の可視化モジュール。

速度場・渦度場・流線など典型的な CFD ベクトル場の可視化関数を提供する。
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver


def plot_velocity(
    u: np.ndarray,
    v: np.ndarray,
    grid: "Grid",
    *,
    title: str = "速度場",
    speed_cmap: str = "viridis",
    quiver_stride: int = 4,
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
    quiver_stride : 矢印を描くサンプリング間隔（間引き）
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

    im = ax.pcolormesh(X, Y, speed, cmap=speed_cmap, shading="auto")
    fig.colorbar(im, ax=ax, label="|u|")

    # 矢印プロット（間引きしてすっきり表示）
    s = quiver_stride
    ax.quiver(X[::s, ::s], Y[::s, ::s],
              u_np[::s, ::s], v_np[::s, ::s],
              color="white", alpha=0.7, scale=None)

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
