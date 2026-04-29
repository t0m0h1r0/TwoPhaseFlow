#!/usr/bin/env python3
"""[V6] Density-ratio robustness with the §14 FCCD/UCCD6/HFE stack.

Paper ref: §13.4 (sec:varrho_dc_convergence, sec:interface_crossing).

V6 verifies the density-ratio axis with the same production-family operators
used in §14 and V9:

  - FCCD interface transport and pressure gradient,
  - UCCD6 momentum convection,
  - HFE curvature (psi_direct_hfe),
  - pressure-jump surface tension embedded in phase-separated FCCD PPE,
  - defect-correction PPE and face-flux projection.

This replaces the legacy reduced smoothed-density CSF/PPE sweep retained at
``experiment/ch13/legacy/exp_V6_density_ratio_convergence_legacy.py``.

Usage
-----
  make run EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
  make plot EXP=experiment/ch13/exp_V6_density_ratio_convergence.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from ch14_stack_common import ch14_circle_config, run_ch14_case
from twophase.simulation.visualization.plot_fields import field_with_contour
from twophase.tools.experiment import (
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 1.0
RHO_G = 1.0
MU_L = 1.0e-3
MU_G = 1.0e-4
RATIOS = (2.0, 10.0, 100.0, 833.0)
N_LIST = (24, 32)
N_STEPS = 8
CFL_MULTIPLIER = 0.50
DP_EXACT = SIGMA / R


def _case_config(N: int, ratio: float):
    return ch14_circle_config(
        N=N,
        out_dir=OUT,
        radius=R,
        center=CENTER,
        rho_l=ratio * RHO_G,
        rho_g=RHO_G,
        mu_l=MU_L,
        mu_g=MU_G,
        sigma=SIGMA,
        max_steps=N_STEPS,
        final_time=10.0,
        cfl=CFL_MULTIPLIER,
        reinit_every=20,
    )


def _run_one(N: int, ratio: float) -> dict:
    label = f"V6 N={N} rho={ratio:g}"
    out = run_ch14_case(
        cfg=_case_config(N, ratio),
        label=label,
        radius=R,
        center=CENTER,
    )
    out.update(
        {
            "N": N,
            "ratio": ratio,
            "rho_l": ratio * RHO_G,
            "rho_g": RHO_G,
            "dp_exact": DP_EXACT,
            "dp_correction_abs_ratio": abs(out["dp_final"]) / DP_EXACT
            if np.isfinite(out["dp_final"])
            else float("nan"),
        }
    )
    return out


FIELD_RATIOS = (2.0, 100.0, 833.0)
FIELD_N = N_LIST[-1]  # use the largest N for the field figure


def _extract_field(rows: list[dict]) -> dict:
    """Pick the FIELD_N row and pull X/Y/psi/speed for the field figure."""
    for row in rows:
        if int(row["N"]) == FIELD_N and not row.get("blew_up"):
            X = np.asarray(row["X"]); Y = np.asarray(row["Y"])
            return {
                "x1d": X[:, 0],
                "y1d": Y[0, :],
                "psi": np.asarray(row["psi"]),
                "speed": np.asarray(row["speed"]),
                "ratio": float(row["ratio"]),
                "u_inf_final": float(row["u_inf_final"]),
            }
    return {}


def run_all() -> dict:
    sweeps = {}
    field_panels: dict = {}
    for ratio in RATIOS:
        rows = []
        for N in N_LIST:
            print(f"[V6] N={N}, rho_l/rho_g={ratio:g}")
            rows.append(_run_one(N, ratio))
        sweeps[f"r{int(ratio)}"] = rows
        if ratio in FIELD_RATIOS:
            field_panels[f"field_r{int(ratio)}"] = _extract_field(rows)
    out = {
        "sweeps": sweeps,
        "meta": {
            "N_list": N_LIST,
            "ratios": RATIOS,
            "N_steps": N_STEPS,
            "cfl_multiplier": CFL_MULTIPLIER,
            "sigma": SIGMA,
            "R": R,
            "dp_exact": DP_EXACT,
        },
    }
    out.update(field_panels)
    return out


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_u, ax_v = axes
    sweeps = results["sweeps"]
    colors = {24: "C0", 32: "C1"}
    for N in N_LIST:
        rows = [sweeps[f"r{int(ratio)}"][N_LIST.index(N)] for ratio in RATIOS]
        ratios = np.array([r["ratio"] for r in rows])
        u_vals = np.array([r["u_inf_final"] for r in rows])
        vol_vals = np.array([r["volume_drift_final"] for r in rows])
        ax_u.semilogx(
            ratios,
            u_vals,
            "o-",
            color=colors.get(N, None),
            label=f"N={N}",
        )
        ax_v.semilogx(
            ratios,
            vol_vals,
            "s-",
            color=colors.get(N, None),
            label=f"N={N}",
        )
    ax_u.set_xlabel(r"$\rho_l/\rho_g$")
    ax_u.set_ylabel(r"$\|u\|_\infty$ at final step")
    ax_u.set_title("V6 §14 stack: density-ratio velocity")
    ax_u.legend(fontsize=8)
    ax_v.set_xlabel(r"$\rho_l/\rho_g$")
    ax_v.set_ylabel(r"$|\Delta V_\psi|/V_{\psi,0}$")
    ax_v.set_yscale("log")
    ax_v.set_title("V6 §14 stack: CLS volume drift")
    ax_v.legend(fontsize=8)
    save_figure(
        fig,
        OUT / "V6_density_ratio_convergence",
        also_to=PAPER_FIGURES / "ch13_v6_density_ratio",
    )


def make_density_ratio_field_figure(results: dict) -> None:
    """1×3 speed-field panel at ρ_l/ρ_g ∈ {2, 100, 833} (water-air).

    Each panel uses an individual vmax (speeds vary by orders of magnitude
    across density ratios; shared scale would erase low-ratio detail).
    """
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.6))
    panels_drawn = 0
    for ax, ratio in zip(axes, FIELD_RATIOS):
        panel = results.get(f"field_r{int(ratio)}")
        if not panel or "speed" not in panel:
            ax.set_visible(False)
            continue
        x1d = np.asarray(panel["x1d"])
        y1d = np.asarray(panel["y1d"])
        speed = np.asarray(panel["speed"])
        psi = np.asarray(panel["psi"])
        u_inf = float(panel.get("u_inf_final", np.max(speed)))
        suffix = " (water-air)" if int(ratio) == 833 else ""
        field_with_contour(
            ax, x1d, y1d, speed,
            cmap="magma", vmin=0.0,
            contour_field=psi, contour_level=0.5,
            contour_color="white", contour_lw=1.4,
            title=rf"$\rho_l/\rho_g = {int(ratio)}${suffix}" + "\n" + rf"$\|u\|_\infty = {u_inf:.2e}$",
            xlabel="$x$", ylabel="$y$",
        )
        panels_drawn += 1
    if panels_drawn == 0:
        plt.close(fig)
        return
    fig.suptitle(
        f"V6 §14 stack: speed magnitude after {N_STEPS} steps (N={FIELD_N})",
        fontsize=12,
    )
    fig.tight_layout(rect=(0, 0, 1.0, 0.94))
    save_figure(
        fig,
        OUT / "V6_density_ratio_fields",
        also_to=PAPER_FIGURES / "ch13_v6_density_ratio_fields",
    )


def print_summary(results: dict) -> None:
    print("V6 (§14 stack density-ratio robustness):")
    for key in ("r2", "r10", "r100", "r833"):
        rows = results["sweeps"].get(key, [])
        if not rows:
            continue
        print(f"  rho_l/rho_g={int(rows[0]['ratio'])}:")
        for row in rows:
            tag = (
                f"u_final={row['u_inf_final']:.3e}  "
                f"vol={row['volume_drift_final']:.3e}  "
                f"|dp_corr|/(sigma/R)={row['dp_correction_abs_ratio']:.3e}"
            )
            if row["blew_up"]:
                tag = f"BLEW UP: {row['error']}"
            print(f"    N={row['N']:>3}  steps={row['n_steps']:>2}  {tag}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    make_density_ratio_field_figure(results)
    print_summary(results)
    print(f"==> V6 outputs in {OUT}")


if __name__ == "__main__":
    main()
