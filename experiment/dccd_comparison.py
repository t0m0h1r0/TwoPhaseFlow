"""
DCCD Comparison Experiment
==========================
Linear advection:  u_t + c * u_x = 0,  x in [0, 1), periodic BC.
RK4, CFL = 0.4, c = 1, N = 256, T = 1.0 (one full period).
Exact solution at T=1 = initial condition.

Schemes
-------
  O2    : 2nd-order central FD
  O4    : 4th-order central FD
  CCD   : 6th-order Combined Compact Difference (src/twophase/ccd/ccd_solver.py, periodic)
  DCCD  : CCD + 10th-order selective filter (d10) applied every RK4 step
  WENO5 : 5th-order Weighted ENO + global Lax-Friedrichs (src/twophase/levelset/advection.py)

Initial conditions (all supported on [0.3, 0.5] ⊂ [0, 1))
-----------------------------------------------------------
  square   : step discontinuity, u = 1 in [0.3, 0.5)
  triangle : piecewise-linear hat, peak 1 at x = 0.4 (C0, discontinuous derivative)
  tanh     : smooth square (tanh-smoothed), near-discontinuous steep profile

Filter
------
  D10 kernel: 11-point, k = [1,−10,45,−120,210,−252,210,−120,45,−10,1] / 1024
  Transfer:   (1 + α_f · L_k),  L_k = DFT(kernel)[k]
    L_0 = 0  (DC unaffected)  L_{N/2} = −1  (Nyquist reduced by factor 1−α_f)
  α_f = 0.4  →  Nyquist coefficient = 0.6 per step

Metrics
-------
  L2  = sqrt( mean( (u − u_exact)² ) )
  TV  = Σ_i | u_{i+1} − u_i |  (periodic wrap)

Output structure
----------------
  results/dccd_comparison/
    figures/
      01_square.png
      02_triangle.png
      03_tanh.png
      04_waveforms_panel.png   (3 × 1 waveform comparison)
      05_l2_summary.png        (grouped bar, all ICs)
      06_tv_summary.png        (grouped bar, all ICs)
    data/
      square_metrics.csv
      triangle_metrics.csv
      tanh_metrics.csv
      all_metrics.csv
    latex/
      table_l2.tex
      table_tv.tex
"""
from __future__ import annotations

import csv
import os
import sys
from collections import OrderedDict
from typing import Callable

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import _weno5_pos, _weno5_neg

# ─── output directories ───────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
_OUT  = os.path.join(_ROOT, "results", "dccd_comparison")
_FIG  = os.path.join(_OUT, "figures")
_DAT  = os.path.join(_OUT, "data")
_TEX  = os.path.join(_OUT, "latex")
for d in (_FIG, _DAT, _TEX):
    os.makedirs(d, exist_ok=True)

# ─── parameters ───────────────────────────────────────────────────────────────
N              = 256    # unique periodic nodes
C              = 1.0    # advection speed
T              = 1.0    # final time (one full period)
CFL            = 0.4
FILTER_ALPHA   = 0.4    # α_f ∈ (0, 0.5)
TANH_WIDTH     = 0.02   # σ for tanh-smoothed square pulse

# ─── CCDSolver stubs ──────────────────────────────────────────────────────────
class _Grid1D:
    ndim = 1
    uniform = True
    def __init__(self, n: int):
        self.N = (n,)
        self.L = (1.0,)

class _Backend:
    xp = np

_ccd_solver = CCDSolver(_Grid1D(N), _Backend(), bc_type="periodic")

# ─── d10 filter kernel ────────────────────────────────────────────────────────
_D10_KERNEL = np.array(
    [1, -10, 45, -120, 210, -252, 210, -120, 45, -10, 1], dtype=float
) / 1024.0
# DFT eigenvalue: L_0 = 0, L_{N/2} = -1  →  filter: 1 + α*L_k dissipates HF


# ─── grid ─────────────────────────────────────────────────────────────────────
X = np.arange(N) / N   # x_i = i/N, i = 0..N-1
H = 1.0 / N


# ═══════════════════════════════════════════════════════════════════════════════
# Initial conditions
# ═══════════════════════════════════════════════════════════════════════════════

def ic_square() -> np.ndarray:
    """Step discontinuity: u = 1 on [0.3, 0.5)."""
    u = np.zeros(N)
    u[(X >= 0.3) & (X < 0.5)] = 1.0
    return u

def ic_triangle() -> np.ndarray:
    """Hat function: peak 1 at x=0.4, zero at 0.3 and 0.5 (C0, corner singularity)."""
    u = np.zeros(N)
    mask_l = (X >= 0.3) & (X < 0.4)
    mask_r = (X >= 0.4) & (X < 0.5)
    u[mask_l] = (X[mask_l] - 0.3) / 0.1
    u[mask_r] = (0.5 - X[mask_r]) / 0.1
    return u

def ic_tanh() -> np.ndarray:
    """Smooth square: tanh-blended step profile (C∞, steep)."""
    # u ≈ 1 inside [0.3, 0.5], ≈ 0 outside; width σ = TANH_WIDTH
    return 0.5 * (np.tanh((X - 0.3) / TANH_WIDTH) - np.tanh((X - 0.5) / TANH_WIDTH))

# Registry: key → (label, ic_func, zoom_xlim, zoom_ylim)
ICS: OrderedDict[str, tuple] = OrderedDict([
    ("square",   ("Square Pulse (step)",      ic_square,   (0.15, 0.65), (-0.4, 1.4))),
    ("triangle", ("Triangle Pulse (C0 hat)",  ic_triangle, (0.15, 0.65), (-0.25, 1.25))),
    ("tanh",     ("Smooth Square (tanh)",     ic_tanh,     (0.15, 0.65), (-0.1, 1.1))),
])


# ═══════════════════════════════════════════════════════════════════════════════
# Derivative operators / RHS
# ═══════════════════════════════════════════════════════════════════════════════

def _rhs_o2(u: np.ndarray) -> np.ndarray:
    return -C * (np.roll(u, -1) - np.roll(u, 1)) / (2.0 * H)

def _rhs_o4(u: np.ndarray) -> np.ndarray:
    return -C * (-np.roll(u, -2) + 8*np.roll(u, -1)
                 - 8*np.roll(u, 1) + np.roll(u, 2)) / (12.0 * H)

def _rhs_ccd(u: np.ndarray) -> np.ndarray:
    u_ext = np.empty(N + 1)
    u_ext[:N] = u
    u_ext[N]  = u[0]        # periodic image
    d1, _ = _ccd_solver.differentiate(u_ext, axis=0)
    return -C * np.asarray(d1)[:N]

def _rhs_weno5(u: np.ndarray) -> np.ndarray:
    """WENO5 + global Lax-Friedrichs for u_t + c*u_x = 0 (periodic, N unique nodes).

    Uses _weno5_pos/_weno5_neg from src/twophase/levelset/advection.py.
    np.roll handles periodic wrapping without a duplicate endpoint node.
    """
    F     = C * u
    alpha = abs(C)  # global Lax-Friedrichs speed = 1.0

    # Positive split: F+[i] = (F[i] + alpha*u[i]) / 2
    # Stencil for face i+1/2 (positive): nodes i-2..i+2
    Fp_m2 = 0.5 * (np.roll(F,  2) + alpha * np.roll(u,  2))
    Fp_m1 = 0.5 * (np.roll(F,  1) + alpha * np.roll(u,  1))
    Fp_0  = 0.5 * (F              + alpha * u              )
    Fp_p1 = 0.5 * (np.roll(F, -1) + alpha * np.roll(u, -1))
    Fp_p2 = 0.5 * (np.roll(F, -2) + alpha * np.roll(u, -2))

    # Negative split: F-[i] = (F[i] - alpha*u[i]) / 2
    # Stencil for face i+1/2 (negative): nodes i-1..i+3
    Fm_m1 = 0.5 * (np.roll(F,  1) - alpha * np.roll(u,  1))
    Fm_0  = 0.5 * (F              - alpha * u              )
    Fm_p1 = 0.5 * (np.roll(F, -1) - alpha * np.roll(u, -1))
    Fm_p2 = 0.5 * (np.roll(F, -2) - alpha * np.roll(u, -2))
    Fm_p3 = 0.5 * (np.roll(F, -3) - alpha * np.roll(u, -3))

    flux = (_weno5_pos(np, Fp_m2, Fp_m1, Fp_0, Fp_p1, Fp_p2)
          + _weno5_neg(np, Fm_m1, Fm_0,  Fm_p1, Fm_p2, Fm_p3))

    # Divergence: (flux_{i+1/2} - flux_{i-1/2}) / H  (periodic)
    return -(flux - np.roll(flux, 1)) / H


def _d10_filter(u: np.ndarray) -> np.ndarray:
    """u + α_f · D10(u).  Dissipates HF modes: Nyquist → ×(1−α_f)."""
    d10 = sum(c * np.roll(u, 5 - j) for j, c in enumerate(_D10_KERNEL))
    return u + FILTER_ALPHA * d10

# Scheme registry: key → (label, rhs, post_step, color, linestyle, linewidth)
SCHEMES: OrderedDict[str, tuple] = OrderedDict([
    ("O2",    ("O2",    _rhs_o2,   None,        "#e06c75", "-",  1.2)),
    ("O4",    ("O4",    _rhs_o4,   None,        "#61afef", "-",  1.2)),
    ("CCD",   ("CCD",   _rhs_ccd,  None,        "#d19a66", "--", 1.5)),
    ("DCCD",  ("DCCD",  _rhs_ccd,  _d10_filter, "#98c379", "-",  1.8)),
    ("WENO5", ("WENO5", _rhs_weno5, None,       "#c678dd", "-.",  1.5)),
])


# ═══════════════════════════════════════════════════════════════════════════════
# Integrator
# ═══════════════════════════════════════════════════════════════════════════════

def rk4_step(u: np.ndarray, dt: float,
             rhs: Callable, post: Callable | None) -> np.ndarray:
    k1 = rhs(u)
    k2 = rhs(u + 0.5*dt*k1)
    k3 = rhs(u + 0.5*dt*k2)
    k4 = rhs(u +     dt*k3)
    u_new = u + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
    return post(u_new) if post is not None else u_new

def integrate(u0: np.ndarray, rhs: Callable, post: Callable | None) -> np.ndarray:
    dt = CFL * H / abs(C)
    n_steps = max(1, int(np.ceil(T / dt)))
    dt = T / n_steps
    u = u0.copy()
    for _ in range(n_steps):
        u = rk4_step(u, dt, rhs, post)
    return u


# ═══════════════════════════════════════════════════════════════════════════════
# Metrics
# ═══════════════════════════════════════════════════════════════════════════════

def l2_error(u: np.ndarray, ref: np.ndarray) -> float:
    return float(np.sqrt(np.mean((u - ref) ** 2)))

def total_variation(u: np.ndarray) -> float:
    return float(np.sum(np.abs(np.roll(u, -1) - u)))


# ═══════════════════════════════════════════════════════════════════════════════
# Run all experiments
# ═══════════════════════════════════════════════════════════════════════════════

def run_all() -> dict:
    """Returns results[ic_key][scheme_key] = (u_final, l2, tv)."""
    results: dict[str, dict[str, tuple]] = {}
    for ic_key, (ic_label, ic_fn, *_) in ICS.items():
        u0 = ic_fn()
        tv_exact = total_variation(u0)
        results[ic_key] = {"_exact": (u0, 0.0, tv_exact)}
        for sch_key, (_, rhs, post, *__) in SCHEMES.items():
            u_fin = integrate(u0, rhs, post)
            results[ic_key][sch_key] = (u_fin, l2_error(u_fin, u0), total_variation(u_fin))
        print(f"  [{ic_key}] done — "
              + "  ".join(f"{s}: L2={results[ic_key][s][1]:.2e}"
                          for s in SCHEMES))
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Plotting helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, xlabel="", ylabel="", title=""):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.grid(True, alpha=0.25, lw=0.6)


def _waveform_ax(ax, u0, results_ic, zoom_xlim, zoom_ylim):
    ax.plot(X, u0, "k--", lw=1.6, label="Exact", zorder=10)
    for sch_key, (label, _, __, color, ls, lw) in SCHEMES.items():
        u, *_ = results_ic[sch_key]
        ax.plot(X, u, color=color, ls=ls, lw=lw, label=label)
    ax.set_xlim(*zoom_xlim)
    ax.set_ylim(*zoom_ylim)
    _style_ax(ax, "x", "u", "")
    ax.legend(fontsize=8, loc="upper right", framealpha=0.8)


def _metrics_ax(ax, results_ic, metric_idx: int, ylabel: str,
                tv_exact: float | None = None):
    scheme_keys = list(SCHEMES.keys())
    n = len(scheme_keys)
    x_pos = np.arange(n)
    colors = [SCHEMES[s][3] for s in scheme_keys]
    vals = [results_ic[s][metric_idx] for s in scheme_keys]
    bars = ax.bar(x_pos, vals, color=colors, edgecolor="white", linewidth=0.5)
    if tv_exact is not None:
        ax.axhline(tv_exact, color="k", ls="--", lw=1.0, label=f"Exact TV={tv_exact:.3f}")
        ax.legend(fontsize=7)
    ax.set_yscale("log")
    ax.set_xticks(x_pos)
    ax.set_xticklabels(scheme_keys, fontsize=9)
    _style_ax(ax, "", ylabel, "")
    # value labels on bars
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, val * 1.15,
                f"{val:.1e}", ha="center", va="bottom", fontsize=6.5)


# ─── Figure per IC (2 panels: waveform + L2/TV bars) ─────────────────────────
def plot_ic_figure(ic_key: str, results: dict):
    ic_label, ic_fn, zoom_xlim, zoom_ylim = ICS[ic_key]
    u0 = ic_fn()
    tv_exact = total_variation(u0)
    res_ic = results[ic_key]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2),
                             gridspec_kw={"width_ratios": [2, 1, 1]})
    fig.suptitle(f"{ic_label}  |  N={N}, CFL={CFL}, T={T}, α_f={FILTER_ALPHA}",
                 fontsize=11, y=1.01)

    _waveform_ax(axes[0], u0, res_ic, zoom_xlim, zoom_ylim)
    _style_ax(axes[0], "x", "u", "Waveform (zoomed)")

    _metrics_ax(axes[1], res_ic, metric_idx=1, ylabel="L2 error")
    _style_ax(axes[1], "", "L2 error", "L2 Error")

    _metrics_ax(axes[2], res_ic, metric_idx=2, ylabel="TV",
                tv_exact=tv_exact)
    _style_ax(axes[2], "", "TV", "Total Variation")

    plt.tight_layout()
    out = os.path.join(_FIG, f"0{list(ICS).index(ic_key)+1}_{ic_key}.png")
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


# ─── Panel: 3 ICs × waveform (3 rows × 1 col) ────────────────────────────────
def plot_waveforms_panel(results: dict):
    n_ic = len(ICS)
    fig, axes = plt.subplots(1, n_ic, figsize=(5 * n_ic, 4.2))
    for ax, (ic_key, (ic_label, ic_fn, zoom_xlim, zoom_ylim)) in zip(axes, ICS.items()):
        u0 = ic_fn()
        _waveform_ax(ax, u0, results[ic_key], zoom_xlim, zoom_ylim)
        _style_ax(ax, "x", "u" if ax is axes[0] else "", ic_label)
        if ax is not axes[0]:
            ax.set_ylabel("")

    fig.suptitle(f"Waveform comparison  |  N={N}, CFL={CFL}, T={T}",
                 fontsize=11, y=1.02)
    # Shared legend (top of figure)
    handles, labels = axes[0].get_legend_handles_labels()
    for ax in axes:
        ax.get_legend().remove()
    fig.legend(handles, labels, loc="upper center", ncol=5, fontsize=9,
               bbox_to_anchor=(0.5, 1.0), framealpha=0.9)

    plt.tight_layout()
    out = os.path.join(_FIG, "04_waveforms_panel.png")
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


# ─── Summary bar charts (L2 and TV) ──────────────────────────────────────────
def plot_summary(results: dict, metric_idx: int, ylabel: str, fname: str,
                 title: str):
    """Grouped bar chart: x-axis = ICs, groups = schemes."""
    ic_keys     = list(ICS.keys())
    ic_labels   = [ICS[k][0] for k in ic_keys]
    scheme_keys = list(SCHEMES.keys())
    n_ics       = len(ic_keys)
    n_sch       = len(scheme_keys)

    x = np.arange(n_ics)
    group_w = 0.7
    bar_w   = group_w / n_sch

    fig, ax = plt.subplots(figsize=(8, 4.5))
    for i, sch_key in enumerate(scheme_keys):
        label, _, __, color, ls, _ = SCHEMES[sch_key]
        vals = [results[ic][sch_key][metric_idx] for ic in ic_keys]
        offset = (i - (n_sch - 1) / 2) * bar_w
        bars = ax.bar(x + offset, vals, bar_w, label=label,
                      color=color, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, val * 1.15,
                    f"{val:.1e}", ha="center", va="bottom", fontsize=6,
                    rotation=90)

    # TV exact reference lines (metric_idx == 2)
    if metric_idx == 2:
        for i, ic_key in enumerate(ic_keys):
            u0_tv = results[ic_key]["_exact"][2]
            ax.plot([x[i] - group_w/2, x[i] + group_w/2],
                    [u0_tv, u0_tv], "k--", lw=1.0)

    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(ic_labels, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(f"{title}  |  N={N}, CFL={CFL}, T={T}", fontsize=10)
    ax.legend(fontsize=9, loc="upper right", framealpha=0.8)
    _style_ax(ax, "", ylabel, f"{title}  |  N={N}, CFL={CFL}, T={T}")

    plt.tight_layout()
    out = os.path.join(_FIG, fname)
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# Data output (CSV + LaTeX)
# ═══════════════════════════════════════════════════════════════════════════════

def save_per_ic_csv(ic_key: str, results: dict):
    u0, _, tv_exact = results[ic_key]["_exact"]
    out = os.path.join(_DAT, f"{ic_key}_metrics.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scheme", "L2_error", "TV", "TV_exact", "TV_ratio"])
        for sch_key in SCHEMES:
            _, l2, tv = results[ic_key][sch_key]
            w.writerow([sch_key, f"{l2:.6e}", f"{tv:.6f}",
                        f"{tv_exact:.6f}", f"{tv/tv_exact:.4f}"])

def save_all_csv(results: dict):
    out = os.path.join(_DAT, "all_metrics.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ic", "scheme", "L2_error", "TV", "TV_exact", "TV_ratio"])
        for ic_key in ICS:
            _, _, tv_exact = results[ic_key]["_exact"]
            for sch_key in SCHEMES:
                _, l2, tv = results[ic_key][sch_key]
                w.writerow([ic_key, sch_key, f"{l2:.6e}", f"{tv:.6f}",
                            f"{tv_exact:.6f}", f"{tv/tv_exact:.4f}"])
    print(f"  [csv] {out}")


def save_latex_table(results: dict, metric_idx: int,
                     metric_name: str, fname: str, caption: str):
    """Generate booktabs-style LaTeX table."""
    scheme_keys = list(SCHEMES.keys())
    ic_keys     = list(ICS.keys())
    ic_labels   = [ICS[k][0].replace("&", r"\&") for k in ic_keys]

    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{" + caption + r"}",
        r"  \label{tab:dccd_" + metric_name.lower() + r"}",
        r"  \begin{tabular}{l" + "r" * len(scheme_keys) + r"}",
        r"    \toprule",
        r"    Initial Condition & " + " & ".join(scheme_keys) + r" \\",
        r"    \midrule",
    ]
    for ic_key, ic_label in zip(ic_keys, ic_labels):
        vals = []
        best_val = min(results[ic_key][s][metric_idx] for s in scheme_keys)
        for sch_key in scheme_keys:
            v = results[ic_key][sch_key][metric_idx]
            s = f"{v:.3e}"
            if abs(v - best_val) < 1e-15 * best_val or v == best_val:
                s = r"\textbf{" + s + r"}"
            vals.append(s)
        lines.append(f"    {ic_label} & " + " & ".join(vals) + r" \\")
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    out = os.path.join(_TEX, fname)
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [tex] {out}")


def print_console_table(results: dict):
    scheme_keys = list(SCHEMES.keys())
    for ic_key, (ic_label, *_) in ICS.items():
        _, _, tv_exact = results[ic_key]["_exact"]
        print(f"\n  {ic_label}")
        print(f"  {'Scheme':<8}  {'L2 Error':>12}  {'TV':>10}  {'TV/TV_exact':>12}")
        print("  " + "-" * 50)
        for sch_key in scheme_keys:
            _, l2, tv = results[ic_key][sch_key]
            print(f"  {sch_key:<8}  {l2:>12.4e}  {tv:>10.4f}  {tv/tv_exact:>12.4f}")
        print(f"  {'Exact':<8}  {'—':>12}  {tv_exact:>10.4f}  {'1.0000':>12}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("[DCCD] Running experiments …")
    results = run_all()
    print_console_table(results)

    print("\n[DCCD] Generating figures …")
    for ic_key in ICS:
        plot_ic_figure(ic_key, results)
    plot_waveforms_panel(results)
    plot_summary(results, metric_idx=1, ylabel="L2 error",
                 fname="05_l2_summary.png",  title="L2 Error Summary")
    plot_summary(results, metric_idx=2, ylabel="Total Variation",
                 fname="06_tv_summary.png",  title="Total Variation Summary")

    print("\n[DCCD] Saving data …")
    for ic_key in ICS:
        save_per_ic_csv(ic_key, results)
    save_all_csv(results)

    print("\n[DCCD] Generating LaTeX tables …")
    save_latex_table(
        results, metric_idx=1, metric_name="L2",
        fname="table_l2.tex",
        caption=fr"L2 errors after $T=1$ advection period. "
                fr"$N={N}$, CFL$={CFL}$, $\alpha_f={FILTER_ALPHA}$ (DCCD only). "
                fr"Bold = best per IC.",
    )
    save_latex_table(
        results, metric_idx=2, metric_name="TV",
        fname="table_tv.tex",
        caption=fr"Total variation after $T=1$ advection period. "
                fr"$N={N}$, CFL$={CFL}$, $\alpha_f={FILTER_ALPHA}$ (DCCD only). "
                fr"Bold = best per IC.",
    )

    print("\n[DCCD] Done. All outputs in results/dccd_comparison/")
