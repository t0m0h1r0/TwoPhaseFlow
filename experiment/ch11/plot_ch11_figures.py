#!/usr/bin/env python3
"""Generate publication-quality PDF figures for Chapter 11.

Reads pre-computed NPZ data where available; recomputes inline otherwise.
Outputs to paper/figures/.

Figures:
  1. ch11_tgv_energy.pdf          — §11.2 TGV energy conservation
  2. ch11_tgv_temporal.pdf        — §11.3a temporal convergence
  3. ch11_kovasznay_convergence.pdf — §11.3b Kovasznay spatial convergence
  4. ch11_highre_dccd.pdf          — §11.4 double shear layer CCD vs DCCD
"""

import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Global style
# ---------------------------------------------------------------------------
plt.rcParams.update({
    "text.usetex": False,
    "font.family": "serif",
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 11,
    "legend.fontsize": 9,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "lines.linewidth": 1.4,
    "lines.markersize": 5,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "axes.grid": True,
    "grid.alpha": 0.35,
    "grid.linestyle": "--",
    "grid.color": "#cccccc",
})

COLORS = {"blue": "#1f77b4", "red": "#d62728", "green": "#2ca02c",
          "gray": "#7f7f7f", "orange": "#ff7f0e"}

RESULTS = ROOT / "results"
FIGOUT = ROOT / "paper" / "figures"
FIGOUT.mkdir(parents=True, exist_ok=True)


# ===================================================================
# Figure 1: TGV energy conservation (§11.2)
# ===================================================================
def fig_tgv_energy():
    npz = RESULTS / "ch11_tgv_energy" / "tgv_energy_data.npz"
    if npz.exists():
        d = np.load(npz)
        times, Ek_num, Ek_ex, div_inf = d["times"], d["Ek_numerical"], d["Ek_exact"], d["div_inf"]
    else:
        print("  [recompute] running TGV energy experiment ...")
        sys.path.insert(0, str(ROOT / "experiment" / "ch10"))
        from exp11_3_tgv_energy import run_tgv_energy
        times, Ek_num, Ek_ex, div_inf = run_tgv_energy(N=64, T_end=2.0, Re=100.0, dt=0.01)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    # Left: energy
    ax1.plot(times, Ek_num, "-", color=COLORS["blue"], label="Numerical $E_k$")
    ax1.plot(times, Ek_ex, "--", color=COLORS["red"], label=r"Analytical $E_k(0)\,e^{-4\nu t}$")
    ax1.set_xlabel("$t$")
    ax1.set_ylabel("$E_k$")
    ax1.set_title("(a) Kinetic energy decay")
    ax1.legend(loc="upper right")

    # Right: divergence
    ax2.semilogy(times, div_inf, "-", color=COLORS["green"], linewidth=1.0)
    ax2.axhline(1e-10, color=COLORS["red"], ls="--", alpha=0.6, label="$10^{-10}$ tolerance")
    ax2.set_xlabel("$t$")
    ax2.set_ylabel(r"$\|\nabla \cdot \mathbf{u}\|_\infty$")
    ax2.set_title("(b) Divergence-free constraint")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    out = FIGOUT / "ch11_tgv_energy.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK  {out}")


# ===================================================================
# Figure 2: Temporal convergence (§11.3a)
# ===================================================================
def fig_tgv_temporal():
    npz = RESULTS / "ch11_tgv_temporal" / "tgv_temporal_data.npz"
    if npz.exists():
        results = list(np.load(npz, allow_pickle=True)["results"])
    else:
        print("  [recompute] running TGV temporal experiment ...")
        sys.path.insert(0, str(ROOT / "experiment" / "ch10"))
        from exp11_4_tgv_temporal import main as _run
        _run()
        results = list(np.load(npz, allow_pickle=True)["results"])

    dts = np.array([r["dt"] for r in results])
    errs_u = np.array([r["err_vel"] for r in results])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(dts, errs_u, "o-", color=COLORS["blue"], label=r"$L^\infty$ velocity error")

    # O(dt^2) reference slope
    dt_ref = np.array([dts[0], dts[-1]])
    e0 = errs_u[0]
    ref2 = e0 * (dt_ref / dt_ref[0]) ** 2
    ax.loglog(dt_ref, ref2, "--", color=COLORS["gray"], alpha=0.7, label=r"$O(\Delta t^2)$")
    # annotate slope
    xm = np.sqrt(dt_ref[0] * dt_ref[-1])
    ym = e0 * (xm / dt_ref[0]) ** 2
    ax.annotate("slope 2", xy=(xm, ym), fontsize=9, color=COLORS["gray"],
                ha="left", va="bottom")

    ax.set_xlabel(r"$\Delta t$")
    ax.set_ylabel(r"$L^\infty$ error")
    ax.set_title("Temporal convergence (TGV, $N=64$, $Re=100$)")
    ax.legend(loc="lower right")

    fig.tight_layout()
    out = FIGOUT / "ch11_tgv_temporal.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK  {out}")


# ===================================================================
# Figure 3: Kovasznay spatial convergence (§11.3b)
# ===================================================================
def fig_kovasznay():
    npz = RESULTS / "ch11_kovasznay" / "kovasznay_data.npz"
    if npz.exists():
        results = list(np.load(npz, allow_pickle=True)["results"])
    else:
        print("  [recompute] running Kovasznay experiment ...")
        from exp11_5_kovasznay import main as _run
        _run()
        results = list(np.load(npz, allow_pickle=True)["results"])

    Ns = np.array([r["N"] for r in results], dtype=float)
    hs = 1.0 / Ns
    res_vel = np.array([r["res_vel"] for r in results])
    res_div = np.array([r["res_div"] for r in results])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.loglog(Ns, res_vel, "o-", color=COLORS["blue"], label="NS residual $\\|R\\|_\\infty$")
    ax.loglog(Ns, res_div, "s-", color=COLORS["red"], label=r"Div residual $\|\nabla\cdot\mathbf{u}\|_\infty$")

    # Reference slopes (note: x-axis is N, slope on h means negative slope on N)
    N_ref = np.array([Ns[0], Ns[-1]])
    # O(h^4) => O(N^{-4})
    ref4 = res_vel[0] * (N_ref / N_ref[0]) ** (-4)
    ax.loglog(N_ref, ref4, "--", color=COLORS["gray"], alpha=0.6, label="$O(h^4)$")
    # O(h^6) => O(N^{-6})
    ref6 = res_div[0] * (N_ref / N_ref[0]) ** (-6)
    ax.loglog(N_ref, ref6, ":", color=COLORS["gray"], alpha=0.6, label="$O(h^6)$")

    # Compute and annotate actual slopes
    for arr, name, yoff in [(res_vel, "vel", 1.5), (res_div, "div", 1.5)]:
        slope = np.polyfit(np.log(hs), np.log(arr), 1)[0]
        ax.annotate(f"slope {slope:.1f}", xy=(Ns[-1], arr[-1]),
                    xytext=(10, 5 * yoff), textcoords="offset points",
                    fontsize=8, color=COLORS["gray"])

    ax.set_xlabel("$N$")
    ax.set_ylabel("Residual $L^\\infty$")
    ax.set_title("Kovasznay spatial convergence ($Re=40$)")
    ax.legend(loc="upper right")

    fig.tight_layout()
    out = FIGOUT / "ch11_kovasznay_convergence.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK  {out}")


# ===================================================================
# Figure 4: Double shear layer CCD vs DCCD (§11.4)
# ===================================================================
def fig_highre_dccd():
    # No NPZ saved by the experiment script — must recompute
    print("  [recompute] running double shear layer (CCD + DCCD) ...")
    sys.path.insert(0, str(ROOT / "experiment" / "ch10"))
    sys.path.insert(0, str(ROOT / "experiment" / "ch11"))
    from exp11_6_highre_dccd import run_shear_layer

    N = 64
    Re = 1000.0
    T_end = 0.5
    dt = 0.002

    r_ccd = run_shear_layer(N, Re, T_end, dt, eps_d=0.0, label="CCD")
    r_dccd = run_shear_layer(N, Re, T_end, dt, eps_d=0.05, label="DCCD")

    n_steps = int(T_end / dt)
    t_arr_ccd = np.arange(1, len(r_ccd["Ek_history"]) + 1) * dt
    t_arr_dccd = np.arange(1, len(r_dccd["Ek_history"]) + 1) * dt

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(t_arr_ccd, r_ccd["Ek_history"], "-", color=COLORS["blue"],
            label=r"CCD ($\varepsilon_d=0$)")
    ax.plot(t_arr_dccd, r_dccd["Ek_history"], "--", color=COLORS["red"],
            label=r"DCCD ($\varepsilon_d=0.05$)")
    ax.set_xlabel("$t$")
    ax.set_ylabel("$E_k$")
    ax.set_title(f"Double shear layer ($N={N}$, $Re={int(Re)}$)")
    ax.legend(loc="best")

    # Mark blowup if any
    if r_ccd["blowup"]:
        ax.annotate("CCD blowup", xy=(t_arr_ccd[-1], r_ccd["Ek_history"][-1]),
                    fontsize=9, color=COLORS["blue"], ha="right")
    if r_dccd["blowup"]:
        ax.annotate("DCCD blowup", xy=(t_arr_dccd[-1], r_dccd["Ek_history"][-1]),
                    fontsize=9, color=COLORS["red"], ha="right")

    fig.tight_layout()
    out = FIGOUT / "ch11_highre_dccd.pdf"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"  OK  {out}")


# ===================================================================
# Main
# ===================================================================
def main():
    print("\n=== Generating Chapter 11 figures ===\n")
    fig_tgv_energy()
    fig_tgv_temporal()
    fig_kovasznay()
    fig_highre_dccd()
    print(f"\nAll figures saved to {FIGOUT}\n")


if __name__ == "__main__":
    main()
