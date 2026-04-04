#!/usr/bin/env python3
"""【10-10】IPC time accuracy verification via Taylor-Green vortex decay.

Paper ref: §5b (AB2+IPC → O(Δt²)), §8.1 (IPC splitting error)

Taylor-Green vortex (2D, periodic, single-phase, constant ρ=1):
  u(x,y,t) =  sin(x) cos(y) exp(-2νt)
  v(x,y,t) = -cos(x) sin(y) exp(-2νt)
  p(x,y,t) = -(cos(2x) + cos(2y)) exp(-4νt) / 4

Standalone implementation of AB2+IPC projection method with spectral PPE solve.
Fix spatial resolution N=64 (periodic, spectral-accurate PPE), vary Δt.
Expected: O(Δt²) from AB2+IPC.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import time as _time
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver

OUT = pathlib.Path(__file__).resolve().parent / "results" / "ipc_time"
OUT.mkdir(parents=True, exist_ok=True)


# ── Taylor-Green vortex exact solution ───────────────────────────────────────

def tgv_exact(X, Y, t, nu):
    decay = np.exp(-2.0 * nu * t)
    u = np.sin(X) * np.cos(Y) * decay
    v = -np.cos(X) * np.sin(Y) * decay
    p = -(np.cos(2*X) + np.cos(2*Y)) * decay**2 / 4.0
    return u, v, p


# ── Spectral PPE solver (periodic, exact for constant ρ) ────────────────────

class SpectralPPE:
    """Solve ∇²p = f on periodic domain via FFT (spectrally accurate).

    Grid is (N+1)×(N+1) with last row/col duplicating first (periodic wrap).
    FFT operates on the N×N interior (indices 0..N-1).
    """

    def __init__(self, N, L):
        self.N = N
        self.L = L
        kx = np.fft.fftfreq(N, d=L/(2*np.pi*N))
        ky = np.fft.fftfreq(N, d=L/(2*np.pi*N))
        KX, KY = np.meshgrid(kx, ky, indexing='ij')
        self.ksq = KX**2 + KY**2
        self.ksq[0, 0] = 1.0

    def solve(self, rhs):
        # Extract N×N interior (strip periodic wrap nodes)
        rhs_int = rhs[:self.N, :self.N]
        rhs_hat = np.fft.fft2(rhs_int)
        p_hat = -rhs_hat / self.ksq
        p_hat[0, 0] = 0.0
        p_int = np.real(np.fft.ifft2(p_hat))
        # Reconstruct (N+1)×(N+1) with periodic wrap
        p = np.zeros((self.N+1, self.N+1))
        p[:self.N, :self.N] = p_int
        p[self.N, :] = p[0, :]
        p[:, self.N] = p[:, 0]
        return p


# ── CCD gradient and divergence (periodic, O(h⁶)) ───────────────────────────

def ccd_divergence(u, v, ccd, backend):
    """∇·u via CCD (periodic)."""
    xp = backend.xp
    du_dx, _ = ccd.differentiate(xp.asarray(u), axis=0)
    dv_dy, _ = ccd.differentiate(xp.asarray(v), axis=1)
    return np.asarray(backend.to_host(du_dx)) + np.asarray(backend.to_host(dv_dy))


def ccd_gradient(p, ccd, backend):
    """∇p via CCD (periodic)."""
    xp = backend.xp
    dp_dx, _ = ccd.differentiate(xp.asarray(p), axis=0)
    dp_dy, _ = ccd.differentiate(xp.asarray(p), axis=1)
    return np.asarray(backend.to_host(dp_dx)), np.asarray(backend.to_host(dp_dy))


def ccd_laplacian(f, ccd, backend):
    """∇²f via CCD (periodic)."""
    xp = backend.xp
    _, d2f_dx2 = ccd.differentiate(xp.asarray(f), axis=0)
    _, d2f_dy2 = ccd.differentiate(xp.asarray(f), axis=1)
    return np.asarray(backend.to_host(d2f_dx2)) + np.asarray(backend.to_host(d2f_dy2))


def ccd_convection(u, v, ccd, backend):
    """(u·∇)u convection terms via CCD."""
    xp = backend.xp
    du_dx, _ = ccd.differentiate(xp.asarray(u), axis=0)
    du_dy, _ = ccd.differentiate(xp.asarray(u), axis=1)
    dv_dx, _ = ccd.differentiate(xp.asarray(v), axis=0)
    dv_dy, _ = ccd.differentiate(xp.asarray(v), axis=1)

    du_dx = np.asarray(backend.to_host(du_dx))
    du_dy = np.asarray(backend.to_host(du_dy))
    dv_dx = np.asarray(backend.to_host(dv_dx))
    dv_dy = np.asarray(backend.to_host(dv_dy))

    conv_u = u * du_dx + v * du_dy
    conv_v = u * dv_dx + v * dv_dy
    return conv_u, conv_v


# ── AB2+IPC projection method ───────────────────────────────────────────────

class SpectralHelmholtz:
    """Solve (I - α∇²)u = f on periodic domain via FFT.

    Used for Crank-Nicolson viscous implicit step: α = dt*ν/2.
    """

    def __init__(self, N, L):
        self.N = N
        kx = np.fft.fftfreq(N, d=L/(2*np.pi*N))
        ky = np.fft.fftfreq(N, d=L/(2*np.pi*N))
        KX, KY = np.meshgrid(kx, ky, indexing='ij')
        self.ksq = KX**2 + KY**2

    def solve(self, rhs, alpha):
        """Solve (1 + α k²) û = f̂ in Fourier space."""
        rhs_int = rhs[:self.N, :self.N]
        rhs_hat = np.fft.fft2(rhs_int)
        u_hat = rhs_hat / (1.0 + alpha * self.ksq)
        u_int = np.real(np.fft.ifft2(u_hat))
        u = np.zeros((self.N+1, self.N+1))
        u[:self.N, :self.N] = u_int
        u[self.N, :] = u[0, :]
        u[:, self.N] = u[:, 0]
        return u


def run_ab2_ipc(N, L, nu, dt, n_steps, ccd, backend, ppe_solver, grid):
    """Run AB2+IPC projection method with Crank-Nicolson viscous.

    Time discretization (§5b, §9):
      Convection: AB2 extrapolation → O(Δt²)
      Viscous: Crank-Nicolson (implicit) → O(Δt²)
      IPC: -∇p^n in predictor + δp correction → O(Δt²) splitting
    """
    h = L / N
    X, Y = grid.meshgrid()

    helmholtz = SpectralHelmholtz(N, L)
    alpha_cn = dt * nu / 2.0  # CN implicit parameter

    # Initial conditions
    u, v, p = tgv_exact(X, Y, 0.0, nu)

    conv_u_prev = None
    conv_v_prev = None

    for step in range(n_steps):
        # Convection: (u·∇)u
        conv_u, conv_v = ccd_convection(u, v, ccd, backend)

        # AB2 extrapolation (forward Euler on first step)
        if conv_u_prev is not None:
            ab2_u = 1.5 * conv_u - 0.5 * conv_u_prev
            ab2_v = 1.5 * conv_v - 0.5 * conv_v_prev
        else:
            ab2_u = conv_u
            ab2_v = conv_v

        conv_u_prev = conv_u.copy()
        conv_v_prev = conv_v.copy()

        # Viscous term (explicit half): ν/2 ∇²u^n
        visc_u_n = nu * ccd_laplacian(u, ccd, backend)
        visc_v_n = nu * ccd_laplacian(v, ccd, backend)

        # IPC pressure gradient: -∇p^n
        dp_dx, dp_dy = ccd_gradient(p, ccd, backend)

        # Predictor RHS: u^n + Δt[-conv + ν/2·∇²u^n - ∇p^n]
        rhs_u = u + dt * (-ab2_u + 0.5 * visc_u_n - dp_dx)
        rhs_v = v + dt * (-ab2_v + 0.5 * visc_v_n - dp_dy)

        # CN implicit solve: (I - Δt·ν/2·∇²) u* = rhs
        u_star = helmholtz.solve(rhs_u, alpha_cn)
        v_star = helmholtz.solve(rhs_v, alpha_cn)

        # PPE: ∇²(δp) = (1/dt) ∇·u*
        div_star = ccd_divergence(u_star, v_star, ccd, backend)
        rhs_ppe = div_star / dt
        delta_p = ppe_solver.solve(rhs_ppe)

        # Corrector: u^{n+1} = u* - dt ∇(δp)
        ddp_dx, ddp_dy = ccd_gradient(delta_p, ccd, backend)
        u = u_star - dt * ddp_dx
        v = v_star - dt * ddp_dy

        # Update pressure: p^{n+1} = p^n + δp
        p = p + delta_p

    return u, v, p, X, Y


# ── Main experiment ──────────────────────────────────────────────────────────

def run_tgv_convergence(N=64, T_end=0.5, Re=100.0):
    backend = Backend(use_gpu=False)
    nu = 1.0 / Re
    L = 2.0 * np.pi

    gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="periodic")
    ppe_solver = SpectralPPE(N, L)

    n_steps_list = [5, 10, 20, 40, 80]
    results = []

    print(f"  N={N}, Re={Re}, ν={nu}, T_end={T_end}, L={L:.4f}")
    print(f"  {'n_steps':>8} {'Δt':>12} {'L2(u)':>12} {'L2(v)':>12} {'L2(vel)':>12} {'order':>8} {'time(s)':>8}")
    print("  " + "-" * 85)

    for n_steps in n_steps_list:
        dt = T_end / n_steps

        t0 = _time.perf_counter()
        u, v, p, X, Y = run_ab2_ipc(N, L, nu, dt, n_steps, ccd, backend, ppe_solver, grid)
        wall_time = _time.perf_counter() - t0

        u_exact, v_exact, _ = tgv_exact(X, Y, T_end, nu)
        err_u = np.sqrt(np.mean((u - u_exact)**2))
        err_v = np.sqrt(np.mean((v - v_exact)**2))
        err_vel = np.sqrt(err_u**2 + err_v**2)

        results.append({
            "n_steps": n_steps, "dt": dt,
            "err_u": err_u, "err_v": err_v, "err_vel": err_vel,
            "wall_time": wall_time,
        })

        slope_str = "---"
        if len(results) > 1:
            r0, r1 = results[-2], results[-1]
            if r0["err_vel"] > 0 and r1["err_vel"] > 0:
                s = np.log(r1["err_vel"] / r0["err_vel"]) / np.log(r1["dt"] / r0["dt"])
                slope_str = f"{s:.2f}"

        print(f"  {n_steps:>8} {dt:>12.5f} {err_u:>12.3e} {err_v:>12.3e} "
              f"{err_vel:>12.3e} {slope_str:>8} {wall_time:>7.1f}")

    return results


def save_latex_table(results):
    with open(OUT / "table_ipc_time_accuracy.tex", "w") as fp:
        fp.write("% Auto-generated by exp10_10_ipc_time_accuracy.py\n")
        fp.write("\\begin{tabular}{rrccc}\n\\toprule\n")
        fp.write("ステップ数 $n$ & $\\Delta t$ & $L_2(\\bu)$ & 収束次数 \\\\\n")
        fp.write("\\midrule\n")
        for i, r in enumerate(results):
            slope_str = "---"
            if i > 0:
                r0 = results[i-1]
                if r0["err_vel"] > 0 and r["err_vel"] > 0:
                    s = np.log(r["err_vel"] / r0["err_vel"]) / np.log(r["dt"] / r0["dt"])
                    slope_str = f"${s:.2f}$"
            fp.write(f"{r['n_steps']} & ${r['dt']:.4f}$ & ${r['err_vel']:.2e}$ & {slope_str} \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")
    print(f"\n  Saved: {OUT / 'table_ipc_time_accuracy.tex'}")


def save_plot(results):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=(6, 4.5))
    dts = [r["dt"] for r in results]
    errs = [r["err_vel"] for r in results]

    ax.loglog(dts, errs, "o-", label="$L_2$ velocity error", markersize=7)

    dt_ref = np.array([dts[0], dts[-1]])
    e0 = errs[0]
    for order, ls, lbl in [(1, ":", "$O(\\Delta t)$"), (2, "--", "$O(\\Delta t^2)$")]:
        ax.loglog(dt_ref, e0 * (dt_ref / dt_ref[0])**order, ls,
                  color="gray", alpha=0.5, label=lbl)

    ax.set_xlabel("$\\Delta t$")
    ax.set_ylabel("$L_2$ velocity error")
    ax.set_title("Taylor-Green vortex: AB2+IPC time accuracy (N=64)")
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(OUT / "ipc_time_accuracy.eps", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {OUT / 'ipc_time_accuracy.eps'}")


def main():
    print("\n" + "=" * 80)
    print("  【10-10】IPC Time Accuracy: Taylor-Green Vortex Decay")
    print("=" * 80 + "\n")

    results = run_tgv_convergence(N=64, T_end=0.5, Re=100.0)
    save_latex_table(results)
    save_plot(results)

    np.savez(OUT / "ipc_time_data.npz", results=results)
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "ipc_time_data.npz", allow_pickle=True)
        save_plot(list(_d["results"]))
    else:
        main()
