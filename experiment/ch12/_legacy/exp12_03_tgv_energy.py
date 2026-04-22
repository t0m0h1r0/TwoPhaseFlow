#!/usr/bin/env python3
"""[12-03] Taylor-Green vortex energy decay verification.

Validates: AB2 time integration + FFT PPE on periodic domain.

Setup
-----
  Domain [0, 2π]², periodic BC, ρ = 1, ν = 0.01
  u₀ =  cos(x)·sin(y),  v₀ = −sin(x)·cos(y)
  Exact: u(t) = u₀·exp(−2νt),  E_k(t) = π²·exp(−4νt)
  AB2 predictor + FFT pressure projection
  200 steps, dt = 0.01
  Grid: N = 32, 64, 128

Expected
--------
  - E_k tracks exact exponential decay
  - ||div(u)||_∞ ≈ machine precision (FFT PPE)
  - Energy error improves with spatial refinement

Output
------
  - E_k(t) vs exact
  - ||div(u)||_∞ history
  - Final E_k relative error vs N
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"

# -- Physical parameters -------------------------------------------------------
NU = 0.01
DT = 0.01
N_STEPS = 200
L_DOM = 2.0 * np.pi
CHECKPOINT_INTERVAL = 5   # record every 5 steps


# -- FFT PPE solver (periodic, constant density) -------------------------------

def fft_ppe(rhs, h, xp=np):
    """Solve ∇²p = rhs on periodic domain via FFT.

    Grid has (N+1)×(N+1) points with endpoint duplicating origin.
    FFT operates on N×N interior, result padded back.
    """
    rhs_int = rhs[:-1, :-1]  # N×N interior (exclude duplicate endpoint)
    N = rhs_int.shape[0]
    kx = xp.fft.fftfreq(N, d=h) * 2 * np.pi
    ky = xp.fft.fftfreq(N, d=h) * 2 * np.pi
    KX, KY = xp.meshgrid(kx, ky, indexing="ij")
    K2 = KX**2 + KY**2
    K2[0, 0] = 1.0
    p_hat = xp.fft.fft2(rhs_int) / (-K2)
    p_hat[0, 0] = 0.0
    p_int = xp.real(xp.fft.ifft2(p_hat))
    # Pad back to (N+1)×(N+1) with periodic wrapping
    p = xp.zeros_like(rhs)
    p[:-1, :-1] = p_int
    p[-1, :] = p[0, :]
    p[:, -1] = p[:, 0]
    return p


# -- Single-grid run -----------------------------------------------------------

def run(N):
    """Run TGV on N×N periodic grid, return energy/divergence history."""
    backend = Backend()
    xp = backend.xp
    h = L_DOM / N
    dt = DT

    gc = GridConfig(ndim=2, N=(N, N), L=(L_DOM, L_DOM))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")

    X, Y = grid.meshgrid()

    # Initial conditions (standard TGV)
    u = xp.sin(X) * xp.cos(Y)
    v = -xp.cos(X) * xp.sin(Y)

    # IPC: initialize pressure to exact TGV pressure
    p = -0.25 * (xp.cos(2 * X) + xp.cos(2 * Y))

    # Exact energy: E_k(t) = (1/2) ∫ |u|² dA
    # Over [0,2π]², E_total = ∫ 0.5*(sin²x cos²y + cos²x sin²y) dA = π²
    # So E_k(t) = π² exp(-4νt)
    def ek_exact(t):
        return np.pi**2 * np.exp(-4.0 * NU * t)

    # Kinetic energy / divergence — delegate to library
    from twophase.tools.diagnostics import kinetic_energy_periodic, divergence_linf

    def kinetic_energy(u, v):
        return kinetic_energy_periodic([u, v], h)

    def compute_div(u, v):
        from twophase.tools.diagnostics.field_diagnostics import _compute_divergence
        return _compute_divergence([u, v], ccd)

    # Compute nonlinear RHS:  N(u,v) = -(u·∇)u + ν∇²u
    def rhs_func(u, v):
        du_dx, d2u_dx2 = ccd.differentiate(u, 0)
        du_dy, d2u_dy2 = ccd.differentiate(u, 1)
        dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
        dv_dy, d2v_dy2 = ccd.differentiate(v, 1)

        adv_u = -(u * du_dx + v * du_dy)
        adv_v = -(u * dv_dx + v * dv_dy)
        diff_u = NU * (d2u_dx2 + d2u_dy2)
        diff_v = NU * (d2v_dx2 + d2v_dy2)

        return adv_u + diff_u, adv_v + diff_v

    # Records
    times = []
    ek_hist = []
    ek_ex_hist = []
    div_hist = []

    # Initial state
    t = 0.0
    ek0 = kinetic_energy(u, v)
    times.append(t)
    ek_hist.append(ek0)
    ek_ex_hist.append(ek_exact(t))
    div0 = compute_div(u, v)
    div_hist.append(float(xp.max(xp.abs(div0))))

    rhs_u_prev, rhs_v_prev = rhs_func(u, v)

    # Euler predictor for step 0 (IPC: include -∇p^n)
    dp_dx_n, _ = ccd.differentiate(p, 0)
    dp_dy_n, _ = ccd.differentiate(p, 1)
    u_star = u + dt * rhs_u_prev - dt * dp_dx_n
    v_star = v + dt * rhs_v_prev - dt * dp_dy_n

    # PPE for pressure correction
    div_star = compute_div(u_star, v_star)
    phi = fft_ppe(div_star / dt, h, xp)
    dphi_dx, _ = ccd.differentiate(phi, 0)
    dphi_dy, _ = ccd.differentiate(phi, 1)
    u = u_star - dt * dphi_dx
    v = v_star - dt * dphi_dy
    p = p + phi
    t += dt

    if True:
        times.append(t)
        ek_hist.append(kinetic_energy(u, v))
        ek_ex_hist.append(ek_exact(t))
        div_hist.append(float(xp.max(xp.abs(compute_div(u, v)))))

    rhs_u_curr, rhs_v_curr = rhs_func(u, v)

    # AB2 time stepping: steps 1..N_STEPS-1 (IPC)
    for step in range(1, N_STEPS):
        # IPC: pressure gradient from previous step
        dp_dx_n, _ = ccd.differentiate(p, 0)
        dp_dy_n, _ = ccd.differentiate(p, 1)

        # AB2 predictor with IPC
        u_star = u + dt * (1.5 * rhs_u_curr - 0.5 * rhs_u_prev) - dt * dp_dx_n
        v_star = v + dt * (1.5 * rhs_v_curr - 0.5 * rhs_v_prev) - dt * dp_dy_n

        # PPE for pressure correction
        div_star = compute_div(u_star, v_star)
        phi = fft_ppe(div_star / dt, h, xp)
        dphi_dx, _ = ccd.differentiate(phi, 0)
        dphi_dy, _ = ccd.differentiate(phi, 1)
        u = u_star - dt * dphi_dx
        v = v_star - dt * dphi_dy
        p = p + phi
        t += dt

        rhs_u_prev = rhs_u_curr
        rhs_v_prev = rhs_v_curr
        rhs_u_curr, rhs_v_curr = rhs_func(u, v)

        if (step + 1) % CHECKPOINT_INTERVAL == 0 or step == N_STEPS - 1:
            times.append(t)
            ek_hist.append(kinetic_energy(u, v))
            ek_ex_hist.append(ek_exact(t))
            div_hist.append(float(xp.max(xp.abs(compute_div(u, v)))))

        if np.isnan(float(xp.max(xp.abs(u)))) or float(xp.max(xp.abs(u))) > 1e6:
            print(f"    [N={N}] BLOWUP at step {step+1}")
            break

    times = np.array(times)
    ek_hist = np.array(ek_hist)
    ek_ex_hist = np.array(ek_ex_hist)
    div_hist = np.array(div_hist)

    ek_rel_err_final = abs(ek_hist[-1] - ek_ex_hist[-1]) / ek_ex_hist[-1]

    return {
        "N": N, "h": h, "dt": dt,
        "times": times,
        "ek_hist": ek_hist,
        "ek_ex_hist": ek_ex_hist,
        "div_hist": div_hist,
        "ek_rel_err_final": ek_rel_err_final,
        "n_checkpoints": len(times),
    }


# -- Plotting ------------------------------------------------------------------

def make_figures(results):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    # (a) Energy decay
    ax = axes[0]
    for i, r in enumerate(results):
        ax.plot(r["times"], r["ek_hist"], "-",
                color=COLORS[i % len(COLORS)], linewidth=1.2,
                label=f"N={r['N']}")
    # Exact (use finest grid times)
    t_ex = results[-1]["times"]
    ax.plot(t_ex, results[-1]["ek_ex_hist"], "k--", linewidth=1.5, label="Exact")
    ax.set_xlabel("$t$"); ax.set_ylabel("$E_k$")
    ax.set_title("(a) Kinetic energy decay"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (b) Divergence history
    ax = axes[1]
    for i, r in enumerate(results):
        ax.semilogy(r["times"], r["div_hist"], "-",
                    color=COLORS[i % len(COLORS)], linewidth=1.2,
                    label=f"N={r['N']}")
    ax.set_xlabel("$t$"); ax.set_ylabel(r"$\|\nabla \cdot \mathbf{u}\|_\infty$")
    ax.set_title("(b) Divergence"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)

    # (c) Final energy error vs N
    ax = axes[2]
    Ns = [r["N"] for r in results]
    hs = [r["h"] for r in results]
    errs = [r["ek_rel_err_final"] for r in results]
    ax.loglog(hs, errs, "o-", color=COLORS[0], linewidth=1.5, markersize=7,
              label=r"$|E_k - E_{k,\mathrm{exact}}|/E_{k,\mathrm{exact}}$")
    h_ref = np.array(hs)
    ax.loglog(h_ref, errs[0] * (h_ref / hs[0])**2, "k:", alpha=0.5,
              label=r"$O(h^2)$")
    ax.loglog(h_ref, errs[0] * (h_ref / hs[0])**4, "k--", alpha=0.4,
              label=r"$O(h^4)$")
    ax.set_xlabel("$h$"); ax.set_ylabel("$E_k$ relative error")
    ax.set_title("(c) Energy error convergence"); ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, which="both"); ax.invert_xaxis()

    fig.tight_layout()
    save_figure(fig, OUT / "tgv_energy")


# -- Table ---------------------------------------------------------------------

def print_table(results):
    print(f"\n{'='*72}")
    print("  [12-03] Taylor-Green Vortex Energy Decay")
    print(f"{'='*72}")
    print(f"  {'N':>5} | {'h':>10} | {'E_k final':>12} | {'E_k exact':>12} | "
          f"{'rel_err':>12} | {'max|div|':>12}")
    print("  " + "-" * 72)
    for r in results:
        print(f"  {r['N']:>5} | {r['h']:>10.5f} | {r['ek_hist'][-1]:>12.6f} | "
              f"{r['ek_ex_hist'][-1]:>12.6f} | {r['ek_rel_err_final']:>12.4e} | "
              f"{r['div_hist'][-1]:>12.4e}")

    print("\n  Convergence rates (E_k error):")
    for i in range(1, len(results)):
        r0, r1 = results[i - 1], results[i]
        log_h = np.log(r0["h"] / r1["h"])
        rate = np.log(r0["ek_rel_err_final"] / r1["ek_rel_err_final"]) / log_h if r1["ek_rel_err_final"] > 0 else float("nan")
        print(f"    N={r0['N']:>3}->{r1['N']:>3}:  rate={rate:+.2f}")


# -- Main ----------------------------------------------------------------------

def main():
    args = experiment_argparser("[12-03] TGV Energy").parse_args()

    if args.plot_only:
        data = load_results(NPZ)
        make_figures(data["results"])
        return

    Ns = [32, 64, 128]
    results = []

    for N in Ns:
        print(f"  Running N={N} ...")
        r = run(N)
        results.append(r)

    print_table(results)

    # Save
    save_data = {
        "results": [{k: v for k, v in r.items()
                      if k not in ("times", "ek_hist", "ek_ex_hist", "div_hist")}
                     for r in results],
    }
    for i, r in enumerate(results):
        save_data[f"times_{i}"] = r["times"]
        save_data[f"ek_hist_{i}"] = r["ek_hist"]
        save_data[f"ek_ex_hist_{i}"] = r["ek_ex_hist"]
        save_data[f"div_hist_{i}"] = r["div_hist"]
    save_results(NPZ, save_data)

    make_figures(results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    main()
