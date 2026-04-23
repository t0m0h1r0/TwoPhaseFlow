"""Time-series and comparison figure renderers for YAML ``figures:`` specs."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

if TYPE_CHECKING:
    from ..simulation.config_models import ExperimentConfig


def time_series(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """Plot one or more diagnostic time series."""
    t = results.get("times", np.array([]))
    ys: list[str] = spec.get("y", [])
    labels: list[str] = spec.get("labels", ys)

    fig, ax = plt.subplots(figsize=(6, 4))
    for key, lbl in zip(ys, labels):
        if key in results:
            ax.plot(t, results[key], label=lbl)

    analytical = spec.get("analytical")
    if analytical is not None:
        add_analytical(ax, t, analytical, cfg, results)

    ax.set_xlabel(spec.get("xlabel", "t"))
    ax.set_ylabel(spec.get("ylabel", ""))
    ax.set_title(spec.get("title", ""))
    ax.set_yscale(spec.get("yscale", "linear"))
    if len(ys) > 1 or analytical is not None:
        ax.legend()
    ax.grid(True, alpha=0.3)
    return fig


def add_analytical(
    ax: plt.Axes,
    t: np.ndarray,
    analytical: dict,
    cfg: "ExperimentConfig",
    results: dict,
) -> None:
    """Overlay an analytical reference curve."""
    formula = analytical.get("formula", "")
    if formula == "prosperetti":
        omega0 = float(analytical.get("omega0", 1.0))
        beta = float(analytical.get("beta", 0.0))
        D0 = float(analytical.get("D0", 0.05))
        ax.plot(t, D0 * np.exp(-beta * t) * np.cos(omega0 * t), "k--", label="Prosperetti (1981)")
    elif formula == "taylor":
        Ca = float(analytical.get("Ca", 0.0))
        lam = float(analytical.get("lambda_mu", 1.0))
        D_th = (19 * lam + 16) / (16 * lam + 16) * Ca
        ax.axhline(D_th, color="k", linestyle="--", label=f"Taylor (Ca={Ca:.1f}, λ={lam})")
    elif formula == "rt_exponential":
        omega = float(analytical.get("omega", 0.0))
        eta0 = float(analytical.get("eta0", 0.05))
        ax.plot(t, eta0 * np.exp(omega * t), "k--", label=f"RT theory ω={omega:.3f}")


def convergence(spec: dict, results: dict, cfg: "ExperimentConfig") -> plt.Figure:
    """Log-log convergence plot: error vs. spacing."""
    h_vals = np.array(results.get("h_vals", []))
    err_keys: list[str] = spec.get("errors", ["error"])
    labels: list[str] = spec.get("labels", err_keys)

    fig, ax = plt.subplots(figsize=(5, 4))
    for key, lbl in zip(err_keys, labels):
        if key in results:
            ax.loglog(h_vals, results[key], "o-", label=lbl)

    if h_vals.size > 1:
        h_ref = h_vals[-1]
        for p in spec.get("orders", [2, 4]):
            scale = (
                float(results.get(err_keys[0], [1.0])[-1])
                if err_keys[0] in results
                else 1.0
            )
            ax.loglog(h_vals, scale * (h_vals / h_ref) ** p, "k--", alpha=0.6, label=f"O(h^{p})")

    ax.set_xlabel(spec.get("xlabel", "h"))
    ax.set_ylabel(spec.get("ylabel", "error"))
    ax.set_title(spec.get("title", "Grid convergence"))
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    return fig


def deformation_comparison(
    spec: dict,
    results: dict,
    cfg: "ExperimentConfig",
) -> plt.Figure:
    """Plot deformation compared with Taylor (1932)."""
    t = results.get("times", np.array([]))
    Ca_vals: list[float] = spec.get("Ca_vals", [])
    lam = float(spec.get("lambda_mu", 1.0))

    fig, ax = plt.subplots(figsize=(6, 4))
    for Ca in Ca_vals:
        key = f"D_Ca{Ca:.1f}"
        if key in results:
            D_th = (19 * lam + 16) / (16 * lam + 16) * Ca
            ax.plot(t, results[key], label=f"Ca={Ca:.1f} (sim)")
            ax.axhline(D_th, linestyle="--", alpha=0.7, label=f"Ca={Ca:.1f} (Taylor)")

    ax.set_xlabel(spec.get("xlabel", "t"))
    ax.set_ylabel(spec.get("ylabel", "Deformation D"))
    ax.set_title(spec.get("title", "Taylor deformation"))
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    return fig
