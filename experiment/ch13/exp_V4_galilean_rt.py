#!/usr/bin/env python3
"""[V4] Galilean invariance + Rayleigh-Taylor growth rate — Tier B.

Paper ref: §13.3 (sec:galilean_invariance, sec:coupling_limitations).

Two sub-tests:

  (A) Galilean residual scale. A static droplet (R=0.25, sigma>0) is run
      twice on the same fixed Eulerian wall grid: baseline U=(0,0) and
      offset U=(0.1,0). This is a reduced residual-scale check for the
      BF + split-PPE + CSF/PPE loop under wall BC and pinned pressure gauge,
      not an exact periodic Galilean-invariance proof.

  (B) Rayleigh-Taylor (RT) linear growth. Heavy fluid on top of light fluid
      with a single-mode perturbation y_int(x, 0) = y0 + A0 * cos(2*pi*m*x/Lx).
      Linear theory (Chandrasekhar 1961, inviscid):
        gamma_theory = sqrt(g * k * A_t),  A_t = (rho_l - rho_g)/(rho_l + rho_g),
        k = 2*pi*m/Lx.
      We measure gamma_num by least-squares fit to log(A(t)) over the linear
      regime (t in [0, 2/gamma]) and compare. Pass: |gamma_num/gamma_theory - 1| < 0.10.

Setup
-----
  (A) [0,1]^2 wall BC, N=64, R=0.25, ρ_l/ρ_g=10, σ=1, We=10,
      U_offset=(0.1, 0.0), dt=0.20h, 50 steps.
  (B) [0,1] x [0,2] wall-side BC (top/bottom = wall, left/right = wall),
      N=(64, 128), ρ_l/ρ_g=5, σ=0, μ small (Re_g ~ 1000),
      g=1.0 in -y, mode m=2, A0=0.005.

Note: interface advection in (A) is disabled because the droplet is static;
in (B) the reduced RT diagnostic still uses a first-order φ update and is
therefore reported only as a conditional setting check. Production interface
transport is exercised by V10 with FCCD/TVD-RK3, matching the ch14 stack.

Usage
-----
  python experiment/ch13/exp_V4_galilean_rt.py
  python experiment/ch13/exp_V4_galilean_rt.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
)
from twophase.tools.experiment.gpu import sparse_solve_2d

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


def _solve_ppe(rhs, rho, ppe_builder, backend):
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = [backend.to_device(a) for a in triplet]
    A = backend.sparse.csr_matrix((data, (rows, cols)), shape=A_shape)
    xp = backend.xp
    rhs_flat = xp.asarray(rhs).ravel().copy()
    rhs_flat[ppe_builder._pin_dof] = 0.0
    return sparse_solve_2d(backend, A, rhs_flat).reshape(rho.shape)


def _ccd_grad(field, ccd, axis, backend):
    d1, _ = ccd.differentiate(field, axis)
    return np.asarray(backend.to_host(d1))


def _wall_bc(arr) -> None:
    arr[0, :] = 0.0; arr[-1, :] = 0.0
    arr[:, 0] = 0.0; arr[:, -1] = 0.0


# ── (A) Galilean invariance ──────────────────────────────────────────────────

def run_V4a() -> dict:
    """Translation-stability test: static droplet with uniform offset velocity
    U_frame on wall BC. The interior velocity perturbation about U_frame
    should remain small (Galilean invariance of the BF/CSF/PPE pipeline).
    Wall BC is used because periodic-mode PPE on near-singular RHS (uniform
    initial velocity ⇒ rhs ≈ 0) is numerically unstable; the test validates
    the local Galilean property in the bulk."""
    backend = Backend(use_gpu=False)
    xp = backend.xp
    N = 64
    h = 1.0 / N
    eps = 1.5 * h
    U_frame = np.array([0.0, 0.0])  # ablated for stability — see test (B)
    n_steps = 50

    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    curv_calc = CurvatureCalculator(backend, ccd, eps)

    R = 0.25; SIGMA = 1.0; WE = 10.0
    rho_l, rho_g = 10.0, 1.0
    dt = 0.20 * h

    X, Y = grid.meshgrid()
    phi = R - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
    psi = heaviside(xp, phi, eps)
    rho_h = np.asarray(backend.to_host(rho_g + (rho_l - rho_g) * psi))
    kappa_h = np.asarray(backend.to_host(curv_calc.compute(psi)))
    dpsi_dx = _ccd_grad(psi, ccd, 0, backend)
    dpsi_dy = _ccd_grad(psi, ccd, 1, backend)
    f_x = (SIGMA / WE) * kappa_h * dpsi_dx
    f_y = (SIGMA / WE) * kappa_h * dpsi_dy

    # Run two configurations: U_static = (0,0) and U_offset = (0.1, 0).
    # Galilean property: ||u_offset - U_offset|| should equal ||u_static||
    # at every step (within machine-precision PPE roundoff).
    def _trajectory(U):
        u = U[0] * np.ones_like(rho_h); v = U[1] * np.ones_like(rho_h)
        _wall_bc(u); _wall_bc(v)
        hist = []
        for _ in range(n_steps):
            u_s = u + dt / rho_h * f_x; v_s = v + dt / rho_h * f_y
            _wall_bc(u_s); _wall_bc(v_s)
            rhs = (_ccd_grad(u_s, ccd, 0, backend) + _ccd_grad(v_s, ccd, 1, backend)) / dt
            p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))
            u = u_s - dt / rho_h * _ccd_grad(p, ccd, 0, backend)
            v = v_s - dt / rho_h * _ccd_grad(p, ccd, 1, backend)
            _wall_bc(u); _wall_bc(v)
            hist.append((u - U[0], v - U[1]))
        return hist

    static_h = _trajectory(np.array([0.0, 0.0]))
    offset_h = _trajectory(np.array([0.1, 0.0]))
    diff = []
    for (du_s, dv_s), (du_o, dv_o) in zip(static_h, offset_h):
        diff.append(float(np.max(np.sqrt((du_o - du_s) ** 2 + (dv_o - dv_s) ** 2))))

    return {
        "N": N, "n_steps": n_steps, "dt": dt, "U_offset": [0.1, 0.0],
        "galilean_diff_history": np.asarray(diff),
        "galilean_diff_final": diff[-1],
        "galilean_diff_max": float(max(diff)),
    }


# ── (B) RT linear growth rate ───────────────────────────────────────────────

def _setup_rt(N: int, backend: Backend) -> dict:
    Lx, Ly = 1.0, 2.0
    Nx, Ny = N, 2 * N
    h = Lx / Nx
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(Nx, Ny), L=(Lx, Ly)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    ppe_builder = PPEBuilder(backend, grid, bc_type="wall")
    eps = 1.5 * h
    return dict(grid=grid, ccd=ccd, ppe=ppe_builder, h=h, eps=eps,
                Nx=Nx, Ny=Ny, Lx=Lx, Ly=Ly)


def _interface_amplitude(phi, X, Y, k, Lx) -> float:
    """Max |y where phi=0| - mean y. Heuristic linear-mode amplitude tracker."""
    # Find zero crossing in y for each x column
    Nx = phi.shape[0]
    amps = []
    for ix in range(Nx):
        col = phi[ix, :]
        sign = np.sign(col)
        zc = np.where(np.diff(sign) != 0)[0]
        if len(zc) == 0:
            continue
        j = zc[0]
        a = col[j]; b = col[j + 1]
        frac = a / (a - b) if (a - b) != 0 else 0.0
        y_int = Y[ix, j] + frac * (Y[ix, j + 1] - Y[ix, j])
        amps.append(y_int)
    if len(amps) < Nx // 2:
        return float("nan")
    arr = np.asarray(amps)
    return float((arr.max() - arr.min()) / 2.0)


def _rt_one(N: int, mode: int = 2, A0: float = 0.005, n_steps: int = 200,
            backend: Backend | None = None) -> dict:
    backend = backend or Backend(use_gpu=False)
    xp = backend.xp
    rho_l, rho_g = 5.0, 1.0
    g = 1.0
    A_t = (rho_l - rho_g) / (rho_l + rho_g)

    s = _setup_rt(N, backend)
    Lx, Ly = s["Lx"], s["Ly"]
    Nx, Ny = s["Nx"], s["Ny"]
    h, eps = s["h"], s["eps"]
    grid, ccd, ppe = s["grid"], s["ccd"], s["ppe"]

    k = 2.0 * np.pi * mode / Lx
    gamma_th = float(np.sqrt(g * k * A_t))

    X, Y = grid.meshgrid()
    y0 = Ly / 2.0
    phi = (Y - (y0 + A0 * np.cos(k * X)))  # phi>0 ⇒ above interface (heavy)
    psi = heaviside(xp, phi, eps)
    rho_h = np.asarray(backend.to_host(rho_g + (rho_l - rho_g) * psi))

    dt = 0.25 * h / np.sqrt(g * Ly)
    n_eff = min(n_steps, int(2.0 / max(gamma_th, 1e-3) / dt) + 5)

    phi_h = np.asarray(backend.to_host(phi))
    u = np.zeros_like(phi_h); v = np.zeros_like(phi_h)
    amps = []; times = []

    for step in range(n_eff):
        psi_h = np.asarray(backend.to_host(heaviside(xp, phi_h, eps)))
        rho_h = rho_g + (rho_l - rho_g) * psi_h
        u_star = u.copy(); v_star = v - dt * g

        du_dx = _ccd_grad(u_star, ccd, 0, backend)
        dv_dy = _ccd_grad(v_star, ccd, 1, backend)
        rhs = (du_dx + dv_dy) / dt
        p = np.asarray(_solve_ppe(rhs, rho_h, ppe, backend))

        dp_dx = _ccd_grad(p, ccd, 0, backend)
        dp_dy = _ccd_grad(p, ccd, 1, backend)
        u = u_star - dt / rho_h * dp_dx
        v = v_star - dt / rho_h * dp_dy
        _wall_bc(u); _wall_bc(v)

        # Phi advection: simple 1st-order upwind
        dphidx = (np.roll(phi_h, -1, 0) - np.roll(phi_h, 1, 0)) / (2 * h)
        dphidy = np.zeros_like(phi_h)
        dphidy[:, 1:-1] = (phi_h[:, 2:] - phi_h[:, :-2]) / (2 * h)
        phi_h = phi_h - dt * (u * dphidx + v * dphidy)

        amps.append(_interface_amplitude(phi_h, X, Y, k, Lx))
        times.append((step + 1) * dt)

    times = np.asarray(times); amps = np.asarray(amps)
    valid = np.isfinite(amps) & (amps > A0 * 1.05)
    if valid.sum() < 5:
        gamma_num = float("nan")
    else:
        # Fit log(A) ~ log(A0) + gamma*t in valid window
        t_fit = times[valid]; a_fit = amps[valid]
        log_a = np.log(np.maximum(a_fit, 1e-12))
        slope, _ = np.polyfit(t_fit, log_a, 1)
        gamma_num = float(slope)

    rel_err = abs(gamma_num - gamma_th) / gamma_th if np.isfinite(gamma_num) else float("nan")
    return {
        "N": N, "mode": mode, "A0": A0, "n_steps": n_eff, "dt": dt,
        "gamma_theory": gamma_th, "gamma_num": gamma_num, "rel_err": rel_err,
        "times": times, "amps": amps,
    }


def run_V4b() -> dict:
    backend = Backend(use_gpu=False)
    rows = [_rt_one(N, backend=backend) for N in (64, 128)]
    return {"rt": rows}


def run_all() -> dict:
    return {"V4a": run_V4a(), "V4b": run_V4b()}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_g, ax_r = axes

    a = results["V4a"]
    steps = np.arange(1, len(a["galilean_diff_history"]) + 1)
    ax_g.semilogy(steps, a["galilean_diff_history"], "o-", color="C0",
                  label=f"||(u-U)_offset - u_static||_inf (N={a['N']})")
    ax_g.axhline(1e-8, color="C3", linestyle="--", alpha=0.6, label="pass: 1e-8")
    ax_g.set_xlabel("step"); ax_g.set_ylabel("Galilean residual")
    ax_g.set_title("(A) Galilean translation-stability")
    ax_g.legend()

    for r, color, marker in zip(results["V4b"]["rt"], ("C0", "C2"), ("o", "s")):
        ax_r.semilogy(r["times"], r["amps"], marker + "-", color=color,
                      label=f"N={r['N']}: γ_num={r['gamma_num']:.2f}")
    if len(results["V4b"]["rt"]):
        gam = results["V4b"]["rt"][0]["gamma_theory"]
        A0 = results["V4b"]["rt"][0]["A0"]
        t_th = np.linspace(0, results["V4b"]["rt"][0]["times"][-1], 50)
        ax_r.semilogy(t_th, A0 * np.cosh(gam * t_th), "k--",
                      alpha=0.7, label=f"theory γ={gam:.2f}")
    ax_r.set_xlabel("t"); ax_r.set_ylabel("amplitude (log)")
    ax_r.set_title("(B) RT linear growth")
    ax_r.legend()

    save_figure(fig, OUT / "V4_galilean_rt")


def print_summary(results: dict) -> None:
    a = results["V4a"]
    print("V4-A (Galilean translation-stability, wall BC):")
    print(f"  N={a['N']}  n={a['n_steps']}  dt={a['dt']:.3e}  "
          f"diff_final={a['galilean_diff_final']:.3e}  "
          f"diff_max={a['galilean_diff_max']:.3e}  (pass: <1e-8)")
    print("V4-B (Rayleigh-Taylor linear growth):")
    for r in results["V4b"]["rt"]:
        print(f"  N={r['N']}  γ_th={r['gamma_theory']:.3f}  "
              f"γ_num={r['gamma_num']:.3f}  rel_err={r['rel_err']:.2%}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V4 outputs in {OUT}")


if __name__ == "__main__":
    main()
