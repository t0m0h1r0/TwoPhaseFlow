#!/usr/bin/env python3
"""【10-3b】Generate missing LaTeX tables from exp10_3 curvature data.

Reads results/ch10_curvature/curvature_data.npz and generates:
  - table_sinusoidal.tex  (sinusoidal interface κ convergence, path B)
  - table_eps_eff.tex     (ε_eff diagnostic, requires new computation)

Also re-generates table_circle.tex for consistency.

Paper ref: §10.1 (tab:curvature_sinusoidal, tab:curvature_circle,
                   tab:curvature_eps_fixed, tab:eps_eff_diagnostic)
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.curvature import CurvatureCalculator
from twophase.levelset.heaviside import heaviside

OUT = pathlib.Path(__file__).resolve().parent / "results" / "curvature"
OUT.mkdir(parents=True, exist_ok=True)


# ── 3-path sinusoidal curvature test ─────────────────────────────────────────

def sinusoidal_3path(A=0.05):
    """Curvature of sinusoidal interface via 3 paths:
      A: φ direct (CCD on exact SDF)
      B: ψ→φ logit inversion→CCD (standard CurvatureCalculator)
      C: ψ direct (CCD on ψ derivatives, eq:curvature_psi_2d)
    """
    backend = Backend(use_gpu=False)
    xp = backend.xp
    Ns = [32, 64, 128, 256]

    results = {"A": [], "B": [], "C": []}

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        eps = 1.5 * h

        X, Y = grid.meshgrid()
        y_if = 0.5 + A * np.sin(2 * np.pi * X)
        phi = y_if - Y
        psi = heaviside(np, phi, eps)

        # Exact curvature
        fp = A * 2 * np.pi * np.cos(2 * np.pi * X)
        fpp = -A * (2 * np.pi)**2 * np.sin(2 * np.pi * X)
        kappa_exact = -fpp / (1 + fp**2)**1.5

        near = np.abs(phi) < 3 * h

        # Path A: φ direct (CCD on exact SDF)
        phi_x, phi_xx = ccd.differentiate(xp.asarray(phi), axis=0)
        phi_y, phi_yy = ccd.differentiate(xp.asarray(phi), axis=1)
        phi_x = np.asarray(backend.to_host(phi_x))
        phi_y = np.asarray(backend.to_host(phi_y))
        phi_xx = np.asarray(backend.to_host(phi_xx))
        phi_yy = np.asarray(backend.to_host(phi_yy))
        # Cross derivative
        phi_xy_dev, _ = ccd.differentiate(xp.asarray(phi_x), axis=1)
        phi_xy = np.asarray(backend.to_host(phi_xy_dev))
        grad_mag = np.sqrt(phi_x**2 + phi_y**2 + 1e-30)
        kappa_A = -(phi_y**2 * phi_xx - 2*phi_x*phi_y*phi_xy + phi_x**2 * phi_yy) / grad_mag**3

        # Path B: ψ→φ logit → CCD (standard)
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa_B = curv_calc.compute(psi)

        # Path C: ψ direct
        psi_x, psi_xx = ccd.differentiate(xp.asarray(psi), axis=0)
        psi_y, psi_yy = ccd.differentiate(xp.asarray(psi), axis=1)
        psi_x = np.asarray(backend.to_host(psi_x))
        psi_y = np.asarray(backend.to_host(psi_y))
        psi_xx = np.asarray(backend.to_host(psi_xx))
        psi_yy = np.asarray(backend.to_host(psi_yy))
        psi_xy_dev, _ = ccd.differentiate(xp.asarray(psi_x), axis=1)
        psi_xy = np.asarray(backend.to_host(psi_xy_dev))
        grad_psi_mag = np.sqrt(psi_x**2 + psi_y**2 + 1e-30)
        kappa_C = -(psi_y**2 * psi_xx - 2*psi_x*psi_y*psi_xy + psi_x**2 * psi_yy) / grad_psi_mag**3

        for label, kappa in [("A", kappa_A), ("B", kappa_B), ("C", kappa_C)]:
            kappa_np = np.asarray(kappa) if not isinstance(kappa, np.ndarray) else kappa
            if np.any(near):
                err = float(np.max(np.abs(kappa_np[near] - kappa_exact[near])))
            else:
                err = float("nan")
            results[label].append({"N": N, "h": h, "Li": err})

    # Slopes
    for label in results:
        for i in range(1, len(results[label])):
            r0, r1 = results[label][i-1], results[label][i]
            if r0["Li"] > 0 and r1["Li"] > 0:
                r1["Li_slope"] = np.log(r1["Li"] / r0["Li"]) / np.log(r1["h"] / r0["h"])

    return results


# ── ε_eff diagnostic ─────────────────────────────────────────────────────────

def eps_eff_diagnostic(R=0.25):
    """Compute ε_eff/ε for circle interface at multiple resolutions."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    Ns = [64, 128, 256]
    results = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = 1.0 / N
        eps = 1.5 * h

        X, Y = grid.meshgrid()
        phi = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
        psi = heaviside(np, phi, eps)

        # ε_eff = |∇ψ|⁻¹ · ψ(1-ψ)  (interface band)
        psi_x, _ = ccd.differentiate(xp.asarray(psi), axis=0)
        psi_y, _ = ccd.differentiate(xp.asarray(psi), axis=1)
        psi_x = np.asarray(backend.to_host(psi_x))
        psi_y = np.asarray(backend.to_host(psi_y))
        grad_psi = np.sqrt(psi_x**2 + psi_y**2 + 1e-30)

        psi_min = 0.01
        band = (psi > psi_min) & (psi < 1 - psi_min)
        n_pts = int(np.sum(band))

        if n_pts > 0:
            eps_eff = psi[band] * (1 - psi[band]) / grad_psi[band]
            ratio = eps_eff / eps
            results.append({
                "N": N, "n_pts": n_pts,
                "mean": float(np.mean(ratio)),
                "std": float(np.std(ratio)),
                "min": float(np.min(ratio)),
                "max": float(np.max(ratio)),
            })

    return results


# ── LaTeX table generation ───────────────────────────────────────────────────

def save_sinusoidal_table(results):
    with open(OUT / "table_sinusoidal.tex", "w") as fp:
        fp.write("% Auto-generated: sinusoidal curvature 3-path comparison\n")
        fp.write("\\begin{tabular}{rrrrrrr}\n\\toprule\n")
        fp.write("$N$ & A: $\\phi$ 直接 & 次数 & B: ロジット経由 & 次数 & C: $\\psi$ 直接 & 次数 \\\\\n")
        fp.write("\\midrule\n")
        for i in range(len(results["A"])):
            N = results["A"][i]["N"]
            row = f"${N}$"
            for label in ["A", "B", "C"]:
                e = results[label][i]["Li"]
                s = results[label][i].get("Li_slope", float("nan"))
                s_str = f"{s:.2f}" if not np.isnan(s) else "---"
                row += f" & ${e:.2e}$ & {s_str}"
            fp.write(row + " \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_sinusoidal.tex'}")


def save_eps_eff_table(results):
    with open(OUT / "table_eps_eff.tex", "w") as fp:
        fp.write("% Auto-generated: ε_eff diagnostic\n")
        fp.write("\\begin{tabular}{rrrrrr}\n\\toprule\n")
        fp.write("$N$ & 界面帯点数 & $\\varepsilon_{\\textup{eff}}/\\varepsilon$（平均） & 標準偏差 & 最小 & 最大 \\\\\n")
        fp.write("\\midrule\n")
        for r in results:
            fp.write(f"{r['N']} & {r['n_pts']} & {r['mean']:.6f} & "
                     f"${r['std']:.1e}$ & {r['min']:.4f} & {r['max']:.4f} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"  Saved: {OUT / 'table_eps_eff.tex'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-3b】Generate Missing Curvature LaTeX Tables")
    print("=" * 80)

    print("\n--- Sinusoidal 3-path curvature ---")
    sin_results = sinusoidal_3path()
    for label in ["A", "B", "C"]:
        print(f"  Path {label}:")
        for r in sin_results[label]:
            s = r.get("Li_slope", float("nan"))
            print(f"    N={r['N']:>4}: Li={r['Li']:.3e}  p={s:.2f}" if not np.isnan(s)
                  else f"    N={r['N']:>4}: Li={r['Li']:.3e}  p=---")

    print("\n--- ε_eff diagnostic ---")
    eps_results = eps_eff_diagnostic()
    for r in eps_results:
        print(f"  N={r['N']}: ε_eff/ε = {r['mean']:.6f} ± {r['std']:.1e}")

    save_sinusoidal_table(sin_results)
    save_eps_eff_table(eps_results)

    np.savez(OUT / "curvature_3path_data.npz",
             sinusoidal_3path=sin_results, eps_eff=eps_results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
