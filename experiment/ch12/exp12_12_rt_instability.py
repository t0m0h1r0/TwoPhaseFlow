#!/usr/bin/env python3
"""exp12_12  Rayleigh-Taylor instability benchmark (refactored).

Paper ref: SS12.4

Rayleigh-Taylor instability with sigma=0, validating the linear growth rate
against inviscid theory.  This is a refactored version of exp12_1 using the
experiment toolkit for consistent I/O, styling, and --plot-only support.

Setup
-----
  Domain : [0, 1] x [0, 4],  wall BC (all sides)
  Density: rho_l = 3 (heavy, y > 2), rho_g = 1 (light, y < 2)
  Interface: y = 2 + A0*sin(2*pi*x),  A0 = 0.05
  Viscosity: mu = 0.01 (uniform),  sigma = 0
  Gravity: g = 1 (dimensionless, pointing -y)
  Grid: 64 x 256

Validation
----------
  Inviscid linear growth rate:
    omega_RT = sqrt(At * g * k) = sqrt(0.5 * 1 * 2*pi) = sqrt(pi) ~ 1.7725
  where At = (rho_l - rho_g) / (rho_l + rho_g) = 0.5,  k = 2*pi/lambda.

Usage
-----
  python experiment/ch12/exp12_12_rt_instability.py
  python experiment/ch12/exp12_12_rt_instability.py --plot-only
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.ppe.ppe_builder import PPEBuilder
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure, COLORS,
)

OUT = experiment_dir(__file__, "12_rt_instability")

# ── Physical parameters ──────────────────────────────────────────────────────
RHO_L   = 3.0
RHO_G   = 1.0
RHO_REF = 0.5 * (RHO_L + RHO_G)
MU      = 0.01
G_ACC   = 1.0
A0      = 0.05
LAMBDA  = 1.0
AT      = (RHO_L - RHO_G) / (RHO_L + RHO_G)
K_WAV   = 2 * np.pi / LAMBDA
OMEGA_RT = np.sqrt(AT * G_ACC * K_WAV)  # ~ 1.7725


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE: nabla . [(1/rho) nabla p] = rhs."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _find_interface_y(psi, Y_col, threshold=0.5):
    """Find interface y-position by linear interpolation of psi=threshold."""
    for j in range(len(psi) - 1):
        if (psi[j] - threshold) * (psi[j + 1] - threshold) < 0:
            t = (threshold - psi[j]) / (psi[j + 1] - psi[j])
            return Y_col[j] + t * (Y_col[j + 1] - Y_col[j])
    return np.nan


def run_rt(Nx=64, Ny=256, T_final=2.5, cfl_safety=0.2):
    """Run Rayleigh-Taylor instability simulation.

    Uses buoyancy formulation + non-incremental projection + Forward Euler.
    """
    backend = Backend(use_gpu=False)
    Lx, Ly = LAMBDA, 4.0 * LAMBDA
    h = Lx / Nx
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(Nx, Ny), L=(Lx, Ly))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    ls_advection = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()

    # Initial level set: psi=1 for heavy fluid (y > y_interface)
    y_interface = 2.0 + A0 * np.sin(K_WAV * X)
    phi = Y - y_interface
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    times = []
    amplitudes = []
    ke_history = []
    mass_history = []
    snapshots = {}

    mass_0 = float(np.sum(psi) * h ** 2)
    snapshot_times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    next_snap_idx = 0

    snapshots["t_0p0"] = {"psi": psi.copy(), "t": 0.0}
    next_snap_idx = 1

    t = 0.0
    step = 0
    max_steps = 200000

    dt_visc = 0.4 * h ** 2 / (MU / RHO_G)

    print(f"  RT instability: Nx={Nx}, Ny={Ny}, h={h:.4f}")
    print(f"  omega_RT(inviscid) = {OMEGA_RT:.4f}")
    print(f"  dt_visc_limit = {dt_visc:.5f}")
    print(f"  T_final = {T_final}")

    while t < T_final and step < max_steps:
        # Adaptive dt
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt_adv = cfl_safety * h / u_max
        dt = min(dt_adv, dt_visc, T_final - t)
        dt = min(dt, 0.002)

        # Advect psi
        psi = ls_advection.advance(psi, [u, v], dt)
        psi = np.asarray(psi)
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # Explicit RHS
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)

        du_dx = np.asarray(du_dx); du_xx = np.asarray(du_xx)
        du_dy = np.asarray(du_dy); du_yy = np.asarray(du_yy)
        dv_dx = np.asarray(dv_dx); dv_xx = np.asarray(dv_xx)
        dv_dy = np.asarray(dv_dy); dv_yy = np.asarray(dv_yy)

        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)
        visc_u = (MU / rho) * (du_xx + du_yy)
        visc_v = (MU / rho) * (dv_xx + dv_yy)
        buoyancy_v = -(rho - RHO_REF) / rho * G_ACC

        # Predictor (non-incremental)
        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v + buoyancy_v)
        wall_bc(u_star)
        wall_bc(v_star)

        # PPE
        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        div_ustar = np.asarray(du_star_dx) + np.asarray(dv_star_dy)
        rhs_ppe = div_ustar / dt
        p = _solve_ppe(rhs_ppe, rho, ppe_builder)

        # Corrector
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u)
        wall_bc(v)

        t += dt
        step += 1

        # Diagnostics
        ix_center = Nx // 2
        psi_col = psi[ix_center, :]
        Y_col = Y[ix_center, :]
        y_if = _find_interface_y(psi_col, Y_col, 0.5)
        amp = abs(y_if - 2.0) if not np.isnan(y_if) else np.nan

        ke = 0.5 * float(np.sum(rho * (u ** 2 + v ** 2)) * h ** 2)
        mass = float(np.sum(psi) * h ** 2)

        times.append(t)
        amplitudes.append(amp)
        ke_history.append(ke)
        mass_history.append(mass)

        # Snapshots
        if next_snap_idx < len(snapshot_times) and t >= snapshot_times[next_snap_idx]:
            key = f"t_{snapshot_times[next_snap_idx]:.1f}".replace(".", "p")
            snapshots[key] = {"psi": psi.copy(), "t": t}
            next_snap_idx += 1

        if step % 500 == 0 or step <= 3:
            amp_str = f"{amp:.4f}" if not np.isnan(amp) else "NaN"
            print(f"    step {step:5d}, t={t:.4f}, dt={dt:.5f}, "
                  f"A={amp_str}, KE={ke:.4e}")

        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step {step}, t={t:.4f}")
            break

    # Measure growth rate (linear regime)
    times_arr = np.array(times)
    amps_arr = np.array(amplitudes)

    valid = np.isfinite(amps_arr) & (amps_arr > 0)
    mask = valid & (amps_arr > A0 * 1.2) & (amps_arr < 0.4)
    if np.sum(mask) > 5:
        t_fit = times_arr[mask]
        lnA_fit = np.log(amps_arr[mask])
        coeffs = np.polyfit(t_fit, lnA_fit, 1)
        omega_meas = coeffs[0]
    else:
        omega_meas = float('nan')

    omega_err = abs(omega_meas - OMEGA_RT) / OMEGA_RT if not np.isnan(
        omega_meas) else float('nan')

    mass_err = abs(mass_history[-1] - mass_0) / mass_0

    print(f"\n  Results:")
    print(f"    omega_measured = {omega_meas:.4f}")
    print(f"    omega_theory   = {OMEGA_RT:.4f} (inviscid)")
    print(f"    Relative error = {omega_err:.2%}")
    print(f"    Total steps    = {step}")
    print(f"    Mass error     = {mass_err:.3e}")

    return {
        "times": times_arr,
        "amplitudes": amps_arr,
        "ke_history": np.array(ke_history),
        "mass_history": np.array(mass_history),
        "omega_measured": omega_meas,
        "omega_theory": OMEGA_RT,
        "omega_rel_err": omega_err,
        "mass_0": mass_0,
        "mass_final": mass_history[-1],
        "n_steps": step,
        "Nx": Nx,
        "Ny": Ny,
        "snapshots": snapshots,
    }


def make_figures(result):
    """Generate RT instability figures."""
    apply_style()

    times = result["times"]
    amps = result["amplitudes"]
    snapshots = result.get("snapshots", {})

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # -- Left: Amplitude vs time (log scale) --
    ax = axes[0]
    valid = np.isfinite(amps) & (amps > 0)
    ax.semilogy(times[valid], amps[valid], "-", color=COLORS[0],
                linewidth=1.5, label="Numerical")
    t_theory = np.linspace(0, float(times[-1]), 200)
    A_theory = A0 * np.exp(OMEGA_RT * t_theory)
    ax.semilogy(t_theory, A_theory, "--", color=COLORS[1], linewidth=1.5,
                label=f"Theory $\\omega_{{RT}}={OMEGA_RT:.3f}$")

    omega_m = result["omega_measured"]
    if not np.isnan(omega_m):
        A_fit = A0 * np.exp(omega_m * t_theory)
        ax.semilogy(t_theory, A_fit, ":", color=COLORS[2], linewidth=1.2,
                    label=f"Measured $\\omega={omega_m:.3f}$")

    ax.set_xlabel("Time $t$")
    ax.set_ylabel("Amplitude $A(t)$")
    ax.set_title("RT Instability: Amplitude Growth")
    ax.legend()
    ax.set_xlim(0, float(times[-1]))
    ax.set_ylim(bottom=A0 * 0.3)
    ax.grid(True, alpha=0.3)

    # -- Right: Interface snapshots --
    ax = axes[1]
    if snapshots:
        snap_keys = sorted(snapshots.keys(),
                           key=lambda s: snapshots[s]["t"])
        cmap_vals = np.linspace(0.1, 0.9, len(snap_keys))
        for i, key in enumerate(snap_keys):
            snap = snapshots[key]
            psi_snap = snap["psi"]
            Nx_s, Ny_s = psi_snap.shape
            t_label = f"$t = {snap['t']:.1f}$"
            color = plt.cm.viridis(cmap_vals[i])
            ax.contour(
                np.linspace(0, 1, Nx_s), np.linspace(0, 4, Ny_s),
                psi_snap.T, levels=[0.5], colors=[color], linewidths=1.5,
            )
            ax.plot([], [], color=color, linewidth=1.5, label=t_label)

    ax.set_xlabel("$x$")
    ax.set_ylabel("$y$")
    ax.set_title(r"Interface Evolution ($\psi=0.5$)")
    ax.set_aspect("equal")
    ax.set_xlim(0, 1)
    ax.set_ylim(0.5, 3.5)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    save_figure(fig, OUT / "rt_instability.pdf")

    # -- Kinetic energy time history --
    if "ke_history" in result:
        fig2, ax2 = plt.subplots(figsize=(7, 5))
        ke = result["ke_history"]
        ax2.semilogy(times, ke, "-", color=COLORS[0], linewidth=1.2)
        ax2.set_xlabel("Time $t$")
        ax2.set_ylabel("Kinetic energy")
        ax2.set_title("RT Instability: Kinetic Energy")
        ax2.grid(True, alpha=0.3)
        save_figure(fig2, OUT / "rt_kinetic_energy.pdf")


def main():
    print("\n" + "=" * 70)
    print("  exp12_12  Rayleigh-Taylor Instability Benchmark")
    print("=" * 70 + "\n")

    result = run_rt(Nx=64, Ny=256, T_final=2.5)
    make_figures(result)

    # Save results (snapshots stored separately)
    snapshots = result.pop("snapshots", {})
    snap_data = {}
    snap_keys = sorted(snapshots.keys(), key=lambda s: snapshots[s]["t"])
    for i, key in enumerate(snap_keys):
        snap_data[f"snap_{i}"] = snapshots[key]["psi"]
        snap_data[f"snap_{i}_t"] = snapshots[key]["t"]
    snap_data["snap_keys"] = np.array(snap_keys)
    snap_data["n_snaps"] = len(snap_keys)

    save_results(OUT / "rt_data.npz", {**result, **snap_data})
    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    args = experiment_argparser("RT instability benchmark").parse_args()

    if args.plot_only:
        d = load_results(OUT / "rt_data.npz")
        # Reconstruct snapshots
        n_snaps = int(d.get("n_snaps", 0))
        snapshots = {}
        for i in range(n_snaps):
            key = str(d.get("snap_keys", np.array([]))[i]
                      if "snap_keys" in d else f"snap_{i}")
            psi = d.get(f"snap_{i}")
            t_val = d.get(f"snap_{i}_t", 0.0)
            if psi is not None:
                snapshots[key] = {"psi": psi, "t": float(t_val)}

        result = {
            "times": d["times"],
            "amplitudes": d["amplitudes"],
            "ke_history": d.get("ke_history", np.array([])),
            "omega_measured": float(d["omega_measured"]),
            "omega_theory": float(d["omega_theory"]),
            "omega_rel_err": float(d["omega_rel_err"]),
            "mass_0": float(d["mass_0"]),
            "mass_final": float(d["mass_final"]),
            "snapshots": snapshots,
        }
        make_figures(result)
    else:
        main()
