#!/usr/bin/env python3
"""【10-5】GFM discontinuous interface pressure jump accuracy.

Tests:
(a) 1D pressure jump: Laplace pressure across flat interface
(b) 2D static droplet: Laplace pressure Δp = σκ = σ/R
(c) Comparison: CSF (smeared, ε-dependent) vs GFM (sharp interface)

Paper ref: §8e (GFM), §2b (CSF)
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig, FluidConfig, NumericsConfig, SolverConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.gfm import GFMCorrector
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "gfm"
OUT.mkdir(parents=True, exist_ok=True)


def laplace_1d(Ns=[32, 64, 128]):
    """1D-like Laplace pressure jump: flat interface, known Δp = σκ.

    Setup: 2D domain [0,1]², interface at x=0.5.
    Liquid (x<0.5): p = σκ, Gas (x>0.5): p = 0.
    For flat interface κ=0 → Δp=0 (trivial).
    Instead: use circular interface for nontrivial Laplace pressure.
    """
    backend = Backend(use_gpu=False)
    R = 0.25
    center = (0.5, 0.5)
    We = 1.0  # σ = ρ_l U² L / We, effectively σ=1 in non-dim
    kappa_exact = 1.0 / R  # = 4.0
    dp_exact = kappa_exact / We  # Laplace: Δp = σκ = κ/We (non-dim)

    results_gfm = []
    results_csf = []

    for N in Ns:
        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        eps = 1.5 / N
        h = 1.0 / N

        X, Y = grid.meshgrid()
        phi = R - np.sqrt((X - center[0])**2 + (Y - center[1])**2)
        psi = heaviside(np, phi, eps)

        # Curvature via CCD
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        # Density field: rho_l=1, rho_g=0.001 (ratio 1000)
        rho_l, rho_g = 1.0, 0.001
        rho = rho_g + (rho_l - rho_g) * psi

        # ── GFM approach ──
        gfm = GFMCorrector(backend, grid, We=We)
        b_gfm = gfm.compute_rhs_correction(phi, kappa, rho)

        # The GFM correction provides the pressure jump term in PPE RHS.
        # For a static droplet, the pressure field should satisfy:
        #   p_inside = dp_exact, p_outside = 0
        # Check the GFM RHS correction magnitude
        gfm_rhs_max = float(np.max(np.abs(b_gfm)))

        # Build the actual pressure via PPE solve with GFM
        # Use direct LU solver for accuracy
        fc = FluidConfig(We=We, rho_ratio=rho_g/rho_l)
        nc = NumericsConfig(bc_type="wall")
        sc = SolverConfig(ppe_solver_type="ccd_lu")
        config = SimulationConfig(grid=gc, fluid=fc, numerics=nc, solver=sc)

        from twophase.pressure.ppe_solver_lu import PPESolverLU
        ppe = PPESolverLU(backend, config, grid)

        # RHS = GFM correction only (no velocity divergence for static case)
        p_gfm = ppe.solve(b_gfm, rho, dt=1.0)

        # Measure Laplace pressure: p_inside - p_outside
        inside = phi > 2*h    # phi>0 inside circle (liquid)
        outside = phi < -2*h  # phi<0 outside circle (gas)
        if np.any(inside) and np.any(outside):
            p_in = float(np.mean(p_gfm[inside]))
            p_out = float(np.mean(p_gfm[outside]))
            dp_gfm = p_in - p_out
            err_gfm = abs(dp_gfm - dp_exact) / abs(dp_exact)
        else:
            dp_gfm = float("nan")
            err_gfm = float("nan")

        results_gfm.append({
            "N": N, "h": h, "dp": dp_gfm, "dp_exact": dp_exact,
            "rel_err": err_gfm, "rhs_max": gfm_rhs_max,
        })

        # ── CSF approach for comparison ──
        # CSF: surface tension as volume force f_σ = (1/We) κ ∇H
        # This doesn't directly give pressure, but the CSF-induced pressure
        # is obtained by solving PPE with CSF body force.
        # For simplicity, measure the CSF-equivalent pressure from:
        #   ∇p = (1/We) κ δ_ε(φ) n̂ → Δp ≈ (1/We) κ (integrated)
        from twophase.levelset.heaviside import delta as delta_fn
        delta_val = delta_fn(np, phi, eps)

        # CSF RHS: approximate as (1/We) * kappa * delta * gradient(phi)
        # For a static drop, ∇·(f_σ/ρ) gives the PPE source
        # Simplified: just measure the pressure field from CSF PPE
        # CSF volume force → PPE RHS contribution
        grad_psi_x = np.zeros_like(psi)
        grad_psi_y = np.zeros_like(psi)
        grad_psi_x[1:-1,:] = (psi[2:,:] - psi[:-2,:]) / (2*h)
        grad_psi_y[:,1:-1] = (psi[:,2:] - psi[:,:-2]) / (2*h)

        # CSF source: (1/We) * div((1/rho) * kappa * grad_psi)
        fx = kappa * grad_psi_x / (We * rho)
        fy = kappa * grad_psi_y / (We * rho)
        csf_rhs = np.zeros_like(psi)
        csf_rhs[1:-1,:] += (fx[2:,:] - fx[:-2,:]) / (2*h)
        csf_rhs[:,1:-1] += (fy[:,2:] - fy[:,:-2]) / (2*h)

        p_csf = ppe.solve(csf_rhs, rho, dt=1.0)

        if np.any(inside) and np.any(outside):
            p_in_csf = float(np.mean(p_csf[inside]))
            p_out_csf = float(np.mean(p_csf[outside]))
            dp_csf = p_in_csf - p_out_csf
            err_csf = abs(dp_csf - dp_exact) / abs(dp_exact)
        else:
            dp_csf = float("nan")
            err_csf = float("nan")

        results_csf.append({
            "N": N, "h": h, "dp": dp_csf, "dp_exact": dp_exact,
            "rel_err": err_csf,
        })

        print(f"  N={N:>4}: GFM Δp={dp_gfm:.4f} (err={err_gfm:.3e}), "
              f"CSF Δp={dp_csf:.4f} (err={err_csf:.3e}), exact={dp_exact:.4f}")

    # Slopes
    for res_list in [results_gfm, results_csf]:
        for i in range(1, len(res_list)):
            r0, r1 = res_list[i-1], res_list[i]
            log_h = np.log(r1["h"] / r0["h"])
            if r0["rel_err"] > 0 and r1["rel_err"] > 0:
                r1["slope"] = np.log(r1["rel_err"] / r0["rel_err"]) / log_h

    return results_gfm, results_csf


def epsilon_sensitivity():
    """CSF sensitivity to interface thickness ε."""
    backend = Backend(use_gpu=False)
    N = 128
    R = 0.25
    center = (0.5, 0.5)
    We = 1.0
    dp_exact = 1.0 / (R * We)

    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N

    X, Y = grid.meshgrid()
    phi = R - np.sqrt((X - center[0])**2 + (Y - center[1])**2)

    eps_factors = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    results = []

    for ef in eps_factors:
        eps = ef * h
        psi = heaviside(np, phi, eps)
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        rho_l, rho_g = 1.0, 0.001
        rho = rho_g + (rho_l - rho_g) * psi

        inside = phi > 3*h
        outside = phi < -3*h

        # Use CSF pressure estimate: integrate kappa across interface
        # Simple estimate: max curvature near interface
        near = np.abs(phi) < 3*h
        if np.any(near):
            kappa_mean = float(np.mean(kappa[near]))
        else:
            kappa_mean = 0.0

        dp_est = kappa_mean / We
        err = abs(dp_est - dp_exact) / abs(dp_exact)

        results.append({
            "eps_factor": ef, "eps": eps, "kappa_mean": kappa_mean,
            "dp_est": dp_est, "rel_err": err,
        })
        print(f"  ε={ef:.1f}h: κ_mean={kappa_mean:.4f}, Δp_est={dp_est:.4f}, "
              f"err={err:.3e}")

    return results


def plot_results(gfm_res, csf_res, eps_res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))

    # (a) GFM vs CSF convergence
    ax = axes[0]
    h_gfm = [r["h"] for r in gfm_res]
    h_csf = [r["h"] for r in csf_res]
    ax.loglog(h_gfm, [r["rel_err"] for r in gfm_res], "o-", label="GFM")
    ax.loglog(h_csf, [r["rel_err"] for r in csf_res], "s--", label="CSF")
    h_ref = np.array([h_gfm[0], h_gfm[-1]])
    for order in [1, 2]:
        e0 = gfm_res[0]["rel_err"]
        ax.loglog(h_ref, e0*(h_ref/h_ref[0])**order, ":", color="gray", alpha=0.4,
                  label=f"$O(h^{order})$")
    ax.set_xlabel("$h$"); ax.set_ylabel("Relative error in $\\Delta p$")
    ax.set_title("(a) Laplace pressure: GFM vs CSF")
    ax.legend(fontsize=7); ax.grid(True, which="both", alpha=0.3)

    # (b) CSF ε sensitivity
    ax = axes[1]
    ef = [r["eps_factor"] for r in eps_res]
    err = [r["rel_err"] for r in eps_res]
    ax.semilogy(ef, err, "o-")
    ax.set_xlabel(r"$\varepsilon / h$")
    ax.set_ylabel("Relative error in $\\Delta p$")
    ax.set_title(r"(b) CSF $\varepsilon$-sensitivity ($N=128$)")
    ax.grid(True, which="both", alpha=0.3)

    fig.tight_layout()
    fig.savefig(OUT / "gfm_pressure_jump.pdf", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'gfm_pressure_jump.pdf'}")


def save_tables(gfm_res, csf_res):
    with open(OUT / "table_gfm_vs_csf.tex", "w") as fp:
        fp.write("% GFM vs CSF Laplace pressure convergence\n")
        fp.write("\\begin{tabular}{rrrrrr}\n\\toprule\n")
        fp.write("$N$ & GFM $\\Delta p$ & GFM err & slope & CSF $\\Delta p$ & CSF err \\\\\n\\midrule\n")
        for rg, rc in zip(gfm_res, csf_res):
            sg = rg.get("slope", float("nan"))
            sg_s = f"{sg:.2f}" if not np.isnan(sg) else "---"
            fp.write(f"{rg['N']} & {rg['dp']:.4f} & {rg['rel_err']:.2e} & {sg_s} "
                     f"& {rc['dp']:.4f} & {rc['rel_err']:.2e} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")


def main():
    print("\n" + "="*80)
    print("  【10-5】GFM Pressure Jump Accuracy")
    print("="*80)

    print("\n--- (a) GFM vs CSF: Laplace pressure convergence ---")
    gfm_res, csf_res = laplace_1d()

    print("\n--- (b) CSF ε-sensitivity ---")
    eps_res = epsilon_sensitivity()

    save_tables(gfm_res, csf_res)
    plot_results(gfm_res, csf_res, eps_res)

    np.savez(OUT / "gfm_data.npz",
             gfm=gfm_res, csf=csf_res, eps_sensitivity=eps_res)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "gfm_data.npz", allow_pickle=True)
        plot_results(list(_d["gfm"]), list(_d["csf"]), list(_d["eps_sensitivity"]))
    else:
        main()
