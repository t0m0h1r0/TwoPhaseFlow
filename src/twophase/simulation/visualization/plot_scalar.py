"""
スカラー場の可視化モジュール。

2次元スカラー場（圧力、レベルセット、密度など）を
matplotlib を用いてプロットする関数を提供する。
シミュレーション本体には依存せず、numpy 配列と Grid オブジェクトのみを受け取る。
"""

from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.grid import Grid


def plot_scalar_field(
    data: np.ndarray,
    grid: "Grid",
    *,
    title: str = "",
    cmap: str = "RdBu_r",
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    colorbar_label: str = "",
    contour_levels: Optional[int] = None,
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
    figsize: Tuple[float, float] = (6, 5),
    dpi: int = 100,
) -> plt.Figure:
    """2次元スカラー場をカラーマップでプロットする。

    Parameters
    ----------
    data : array, shape ``grid.shape``  — プロットするスカラー場
    grid : Grid
    title : プロットタイトル
    cmap : カラーマップ名
    vmin, vmax : カラーバーの範囲（None の場合はデータから自動決定）
    colorbar_label : カラーバーのラベル
    contour_levels : 等高線の本数（None の場合は等高線なし）
    interface_psi : ψ フィールド（非 None の場合は界面の等値線 ψ=0.5 を描画）
    save_path : 保存先ファイルパス（None の場合は保存しない）
    ax : 既存の Axes（None の場合は新規作成）
    figsize : 図のサイズ
    dpi : 解像度

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    if grid.ndim != 2:
        raise NotImplementedError("現在は2次元のみサポートしています。")

    data_np = np.asarray(data)
    X, Y = grid.meshgrid()

    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    else:
        fig = ax.get_figure()

    im = ax.pcolormesh(X, Y, data_np, cmap=cmap, vmin=vmin, vmax=vmax,
                       shading="auto")
    fig.colorbar(im, ax=ax, label=colorbar_label)

    if contour_levels is not None and contour_levels > 0:
        ax.contour(X, Y, data_np, levels=contour_levels,
                   colors="k", linewidths=0.5, alpha=0.5)

    # 界面位置をψ=0.5の等値線で表示
    if interface_psi is not None:
        psi_np = np.asarray(interface_psi)
        ax.contour(X, Y, psi_np, levels=[0.5],
                   colors="white", linewidths=1.5, linestyles="--")

    ax.set_xlabel("x")
    ax.set_ylabel("y")
    ax.set_aspect("equal")
    if title:
        ax.set_title(title)

    if save_path is not None:
        fig.savefig(save_path, bbox_inches="tight", dpi=dpi)

    return fig


def plot_pressure(
    p: np.ndarray,
    grid: "Grid",
    *,
    title: str = "圧力場 p",
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """圧力場の可視化（便利ラッパー）。"""
    return plot_scalar_field(
        p, grid, title=title, cmap="RdBu_r",
        colorbar_label="p", interface_psi=interface_psi,
        save_path=save_path, ax=ax,
    )


def plot_level_set(
    psi: np.ndarray,
    grid: "Grid",
    *,
    title: str = "レベルセット ψ",
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """レベルセット関数 ψ の可視化（便利ラッパー）。界面（ψ=0.5）を白破線で描画する。"""
    return plot_scalar_field(
        psi, grid, title=title, cmap="bwr",
        vmin=0.0, vmax=1.0, colorbar_label="ψ",
        interface_psi=psi,
        save_path=save_path, ax=ax,
    )


def plot_density(
    rho: np.ndarray,
    grid: "Grid",
    *,
    title: str = "密度場 ρ",
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    ax: Optional[plt.Axes] = None,
) -> plt.Figure:
    """密度場の可視化（便利ラッパー）。"""
    return plot_scalar_field(
        rho, grid, title=title, cmap="Blues",
        colorbar_label="ρ", interface_psi=interface_psi,
        save_path=save_path, ax=ax,
    )


def plot_multi_field(
    fields: dict,
    grid: "Grid",
    *,
    interface_psi: Optional[np.ndarray] = None,
    save_path: Optional[str] = None,
    figsize: Optional[Tuple[float, float]] = None,
    dpi: int = 100,
) -> plt.Figure:
    """複数スカラー場を並べてプロットする。

    Parameters
    ----------
    fields : dict, キー=タイトル、値=(data, cmap, colorbar_label)
    grid   : Grid
    interface_psi : 界面表示用 ψ フィールド
    save_path : 保存先パス
    figsize : 図のサイズ（None の場合は自動）
    dpi : 解像度

    Returns
    -------
    fig : matplotlib.figure.Figure
    """
    n = len(fields)
    if figsize is None:
        figsize = (5 * n, 4.5)
    fig, axes = plt.subplots(1, n, figsize=figsize, dpi=dpi)
    if n == 1:
        axes = [axes]

    for ax, (title, (data, cmap, label)) in zip(axes, fields.items()):
        plot_scalar_field(
            data, grid, title=title, cmap=cmap,
            colorbar_label=label, interface_psi=interface_psi, ax=ax,
        )

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, bbox_inches="tight", dpi=dpi)
    return fig
