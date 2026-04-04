#!/usr/bin/env python3
"""【12-3】GFM static droplet benchmark (Laplace pressure + parasitic currents).

Paper ref: §12.2 (sec:val_static_drop)

Validates the GFM-integrated NS solver on a static droplet at high density
ratios (ρ_l/ρ_g = 10, 100, 1000).  Unlike §11.4a (smoothed Heaviside, ρ ≤ 5),
this uses the production GFM pipeline:
  - GFMCorrector:  pressure jump [p] = σκ/We at interface
  - DCCDPPEFilter:  checkerboard suppression (ε_d = 1/4)
  - ClosestPointExtender:  O(h⁶) Hermite field extension

§11.5 proved smoothed Heaviside diverges for ρ ≥ 10.  This experiment
demonstrates that GFM restores stability and convergence at ρ = 1000.

Setup
-----
  Static droplet: R=0.25, [0,1]², wall BC, gravity=0
  ρ_l/ρ_g = 10, 100, 1000
  We = 1  (Laplace jump = σ/R = 4.0 in dimensionless units)
  Grid: N = 32, 64, 128
  200 steps per run

Output
------
  - Parasitic current ||u||_∞ vs N  (convergence rate)
  - Laplace pressure error vs N
  - Density-ratio independence of accuracy
  - Figure: convergence + density sweep
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np

OUT = pathlib.Path(__file__).resolve().parent / "results" / "gfm_droplet"
OUT.mkdir(parents=True, exist_ok=True)


def run_gfm_droplet(N, rho_ratio_inv, We=1.0, n_steps=200):
    """Run GFM static droplet via SimulationBuilder.

    Parameters
    ----------
    rho_ratio_inv : float
        ρ_l / ρ_g  (e.g. 1000).  Config uses ρ_g / ρ_l.
    """
    from twophase.config import (
        SimulationConfig, GridConfig, FluidConfig,
        NumericsConfig, SolverConfig,
    )
    from twophase.simulation.builder import SimulationBuilder
    from twophase.initial_conditions import InitialConditionBuilder, Circle

    rho_ratio = 1.0 / rho_ratio_inv  # ρ_g / ρ_l

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)),
        fluid=FluidConfig(
            Re=100.0,
            Fr=1.0e10,          # no gravity
            We=We,
            rho_ratio=rho_ratio,
            mu_ratio=0.01,
        ),
        numerics=NumericsConfig(
            epsilon_factor=1.5,
            reinit_steps=4,
            cfl_number=0.25,
            t_end=100.0,        # won't reach — we control steps manually
            bc_type="wall",
            advection_scheme="dissipative_ccd",
            surface_tension_model="gfm",
            extension_method="hermite",
        ),
        solver=SolverConfig(ppe_solver_type="sweep"),  # 欠陥補正法 (§8d)
        use_gpu=False,
    )

    sim = SimulationBuilder(cfg).build()
    xp = sim.backend.xp

    # Initialize static droplet
    psi_init = (
        InitialConditionBuilder(background_phase='gas')
        .add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase='liquid'))
        .build(sim.grid, sim.eps)
    )
    sim.psi.data = sim.backend.to_device(psi_init)

    # Update material properties and curvature from initial ψ
    sim._update_properties()
    sim._update_curvature()

    h = 1.0 / N
    R = 0.25
    # Laplace jump: Δp = σ/(R·We).  In nondimensional form with σ=1: Δp = 1/(R·We)
    dp_exact = 1.0 / (R * We)

    u_max_history = []
    dp_history = []

    for step in range(n_steps):
        dt = cfg.numerics.cfl_number * h  # conservative fixed dt
        try:
            sim.step_forward(dt)
        except Exception as e:
            print(f"    [N={N}, ρ={rho_ratio_inv}] Exception at step {step+1}: {e}")
            break

        # Diagnostics
        vel_components = [np.asarray(sim.backend.to_host(sim.velocity[ax]))
                          for ax in range(2)]
        vel_mag = np.sqrt(vel_components[0]**2 + vel_components[1]**2)
        u_max = float(np.max(vel_mag))
        u_max_history.append(u_max)

        # Laplace pressure
        phi = np.asarray(sim.backend.to_host(sim.phi.data))
        p = np.asarray(sim.backend.to_host(sim.pressure.data))
        inside  = phi > 3 * h
        outside = phi < -3 * h
        if np.any(inside) and np.any(outside):
            dp_meas = float(np.mean(p[inside]) - np.mean(p[outside]))
        else:
            dp_meas = float('nan')
        dp_history.append(dp_meas)

        if np.isnan(u_max) or u_max > 1e6:
            print(f"    [N={N}, ρ={rho_ratio_inv}] BLOWUP at step {step+1}")
            break

    dp_final = dp_history[-1] if dp_history else float('nan')
    dp_err = abs(dp_final - dp_exact) / dp_exact if not np.isnan(dp_final) else float('nan')
    u_peak = max(u_max_history) if u_max_history else float('nan')

    return {
        "N": N, "h": h,
        "rho_ratio": rho_ratio_inv,
        "u_max_peak": u_peak,
        "u_max_final": u_max_history[-1] if u_max_history else float('nan'),
        "dp_meas": dp_final,
        "dp_exact": dp_exact,
        "dp_rel_err": dp_err,
        "n_steps": len(u_max_history),
        "stable": len(u_max_history) == n_steps and not np.isnan(u_peak),
    }


def make_figures(results_by_rho):
    """Generate GFM droplet benchmark figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # ── Left: Parasitic current vs N for each ρ ──
    ax = axes[0]
    markers = ['o', 's', '^']
    colors = ['b', 'g', 'r']
    for i, (rho, results) in enumerate(sorted(results_by_rho.items())):
        Ns = [r["N"] for r in results if r["stable"]]
        u_peaks = [r["u_max_peak"] for r in results if r["stable"]]
        if Ns:
            ax.loglog(Ns, u_peaks, f'{colors[i]}{markers[i]}-', linewidth=1.5,
                      markersize=8, label=f"$\\rho_l/\\rho_g = {rho:.0f}$")
    # Reference slope
    ns_ref = np.array([32, 128])
    ax.loglog(ns_ref, 1e-3 * (32 / ns_ref)**2, 'k--', alpha=0.4, label="$O(h^2)$")
    ax.set_xlabel("$N$", fontsize=12)
    ax.set_ylabel("$\\|\\mathbf{u}_{\\mathrm{para}}\\|_\\infty$", fontsize=12)
    ax.set_title("GFM: Parasitic Current Convergence", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, which="both")

    # ── Right: Laplace pressure error vs N ──
    ax = axes[1]
    for i, (rho, results) in enumerate(sorted(results_by_rho.items())):
        Ns = [r["N"] for r in results if r["stable"]]
        dp_errs = [r["dp_rel_err"] for r in results if r["stable"]]
        if Ns:
            ax.loglog(Ns, dp_errs, f'{colors[i]}{markers[i]}-', linewidth=1.5,
                      markersize=8, label=f"$\\rho_l/\\rho_g = {rho:.0f}$")
    ax.loglog(ns_ref, 0.1 * (32 / ns_ref)**2, 'k--', alpha=0.4, label="$O(h^2)$")
    ax.set_xlabel("$N$", fontsize=12)
    ax.set_ylabel("$\\Delta p$ relative error", fontsize=12)
    ax.set_title("GFM: Laplace Pressure Convergence", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, which="both")

    plt.tight_layout()
    fig.savefig(OUT / "gfm_droplet_convergence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved: {OUT / 'gfm_droplet_convergence.png'}")


def main():
    print("\n" + "=" * 80)
    print("  【12-3】GFM Static Droplet Benchmark (§12.2)")
    print("=" * 80 + "\n")

    density_ratios = [10, 100, 1000]
    Ns = [32, 64, 128]
    n_steps = 200

    results_by_rho = {}

    for dr in density_ratios:
        print(f"\n--- ρ_l/ρ_g = {dr} ---")
        print(f"  {'N':>5} | {'||u||∞_peak':>12} | {'Δp_err':>10} | "
              f"{'steps':>6} | {'stable':>7}")
        print("  " + "-" * 55)

        results = []
        for N in Ns:
            r = run_gfm_droplet(N, rho_ratio_inv=float(dr), n_steps=n_steps)
            results.append(r)
            stable_str = "YES" if r["stable"] else "NO"
            print(f"  {N:>5} | {r['u_max_peak']:>12.4e} | "
                  f"{r['dp_rel_err']:>9.2%} | {r['n_steps']:>6} | {stable_str:>7}")

        results_by_rho[dr] = results

        # Convergence rates
        for i in range(1, len(results)):
            r0, r1 = results[i-1], results[i]
            if r0["stable"] and r1["stable"] and r0["dp_rel_err"] > 0 and r1["dp_rel_err"] > 0:
                rate = np.log(r0["dp_rel_err"] / r1["dp_rel_err"]) / np.log(r0["h"] / r1["h"])
                print(f"    Δp rate N={r0['N']}→{r1['N']}: {rate:.2f}")

    make_figures(results_by_rho)

    # Save LaTeX table
    with open(OUT / "table_gfm_droplet.tex", "w") as fp:
        fp.write("% Auto-generated by exp12_3_gfm_static_droplet.py\n")
        fp.write("\\begin{tabular}{rrcccc}\n\\toprule\n")
        fp.write("$\\rho_l/\\rho_g$ & $N$ & "
                 "$\\|\\bu_{\\mathrm{para}}\\|_\\infty$ & "
                 "$\\Delta p$ 相対誤差 & 収束次数 & 安定 \\\\\n")
        fp.write("\\midrule\n")
        for dr in density_ratios:
            for i, r in enumerate(results_by_rho[dr]):
                rate_str = "---"
                if i > 0:
                    r0 = results_by_rho[dr][i-1]
                    if r0["stable"] and r["stable"] and r0["dp_rel_err"] > 0 and r["dp_rel_err"] > 0:
                        rate = np.log(r0["dp_rel_err"] / r["dp_rel_err"]) / np.log(r0["h"] / r["h"])
                        rate_str = f"${rate:.2f}$"
                stable = "○" if r["stable"] else "×"
                fp.write(f"{dr} & {r['N']} & "
                         f"${r['u_max_peak']:.2e}$ & "
                         f"${r['dp_rel_err']:.2e}$ & {rate_str} & {stable} \\\\\n")
            if dr != density_ratios[-1]:
                fp.write("\\midrule\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_gfm_droplet.tex'}")

    np.savez(OUT / "gfm_droplet_data.npz",
             results_by_rho={str(k): v for k, v in results_by_rho.items()})
    print(f"  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "gfm_droplet_data.npz", allow_pickle=True)
        _rbr = _d["results_by_rho"].item()
        # Convert string keys back to int
        _results_by_rho = {int(k): list(v) for k, v in _rbr.items()}
        make_figures(_results_by_rho)
    else:
        main()
