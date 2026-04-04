#!/usr/bin/env python3
"""【12-1】Rayleigh-Taylor instability (σ=0, linear growth rate validation).

Paper ref: §12.1 (sec:val_rt)

Validates the variable-density NS solver on gravity-driven interface
instability WITHOUT surface tension.  Since σ=0, no pressure jump exists
across the interface, and the smoothed Heaviside one-fluid approach
is viable (§11.4b Test A proved Galilean invariance for σ=0).

Key design choices:
  - Buoyancy formulation: f_buoy = -(ρ-ρ_ref)/ρ · g  (avoids hydrostatic p init)
  - Non-incremental projection (no ∇p^n in predictor → robust for interface)
  - Forward Euler explicit time stepping

Setup
-----
  Domain : [0, 1] × [0, 4],  wall BC (all sides)
  Density: ρ_l = 3 (heavy, y > 2), ρ_g = 1 (light, y < 2)
  Interface: y = 2 + A₀·sin(2πx),  A₀ = 0.05
  Viscosity: μ = 0.01 (uniform),  σ = 0
  Gravity: g = 1 (dimensionless, pointing −y)

Validation
----------
  Inviscid linear growth rate:
    ω_RT = √(At · g · k) = √(0.5 · 1 · 2π) = √π ≈ 1.7725
  where At = (ρ_l − ρ_g) / (ρ_l + ρ_g) = 0.5,  k = 2π/λ.
"""

import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve
from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.pressure.ppe_builder import PPEBuilder

OUT = pathlib.Path(__file__).resolve().parent / "results" / "rt"
OUT.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# Physical parameters
# ═══════════���═══════════════════════════════════════════════════════════════════
RHO_L  = 3.0        # heavy fluid (top)
RHO_G  = 1.0        # light fluid (bottom)
RHO_REF = 0.5 * (RHO_L + RHO_G)  # = 2.0 (for buoyancy formulation)
MU     = 0.01       # uniform viscosity
G_ACC  = 1.0        # gravitational acceleration (dimensionless)
A0     = 0.05       # initial perturbation amplitude
LAMBDA = 1.0        # wavelength
AT     = (RHO_L - RHO_G) / (RHO_L + RHO_G)  # Atwood number = 0.5
K_WAV  = 2 * np.pi / LAMBDA
OMEGA_RT = np.sqrt(AT * G_ACC * K_WAV)       # ≈ 1.7725


def _solve_ppe(rhs, rho, ppe_builder):
    """Solve variable-coefficient PPE: ∇·[(1/ρ)∇p] = rhs."""
    triplet, A_shape = ppe_builder.build(rho)
    data, rows, cols = triplet
    A = sp.csr_matrix((data, (rows, cols)), shape=A_shape)
    rhs_vec = rhs.ravel().copy()
    rhs_vec[ppe_builder._pin_dof] = 0.0
    return spsolve(A, rhs_vec).reshape(rho.shape)


def _find_interface_y(psi, Y_col, threshold=0.5):
    """Find interface y-position by linear interpolation of ψ=threshold."""
    for j in range(len(psi) - 1):
        if (psi[j] - threshold) * (psi[j+1] - threshold) < 0:
            t = (threshold - psi[j]) / (psi[j+1] - psi[j])
            return Y_col[j] + t * (Y_col[j+1] - Y_col[j])
    return np.nan


def run_rt(Nx=64, Ny=256, T_final=2.5, cfl_safety=0.2):
    """Run Rayleigh-Taylor instability simulation.

    Uses buoyancy formulation + non-incremental projection + Forward Euler.
    """
    backend = Backend(use_gpu=False)
    Lx, Ly = LAMBDA, 4.0 * LAMBDA
    h = Lx / Nx  # uniform: Ly/Ny = 4/256 = 1/64 = h
    eps = 1.5 * h

    gc = GridConfig(ndim=2, N=(Nx, Ny), L=(Lx, Ly))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type='wall')
    ppe_builder = PPEBuilder(backend, grid, bc_type='wall')
    ls_advection = DissipativeCCDAdvection(backend, grid, ccd)

    X, Y = grid.meshgrid()

    # Initial level set: ψ=1 for heavy fluid (y > y_interface)
    y_interface = 2.0 + A0 * np.sin(K_WAV * X)
    phi = Y - y_interface  # φ > 0 in heavy region
    psi = np.asarray(heaviside(np, phi, eps))
    rho = RHO_G + (RHO_L - RHO_G) * psi

    u = np.zeros_like(X)
    v = np.zeros_like(X)

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    # Storage
    times = []
    amplitudes = []
    ke_history = []
    mass_history = []
    snapshots = {}

    mass_0 = float(np.sum(psi) * h**2)
    snapshot_times = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5]
    next_snap_idx = 0

    # Save t=0 snapshot
    snapshots["t=0.0"] = {"psi": psi.copy(), "t": 0.0}
    next_snap_idx = 1

    t = 0.0
    step = 0
    max_steps = 200000

    # Viscous CFL limit (constant)
    dt_visc = 0.4 * h**2 / (MU / RHO_G)

    print(f"  RT instability: Nx={Nx}, Ny={Ny}, h={h:.4f}")
    print(f"  ω_RT(inviscid) = {OMEGA_RT:.4f}")
    print(f"  dt_visc_limit = {dt_visc:.5f}")
    print(f"  T_final = {T_final}")

    while t < T_final and step < max_steps:
        # Adaptive dt
        u_max = max(float(np.max(np.abs(u))), float(np.max(np.abs(v))), 1e-10)
        dt_adv = cfl_safety * h / u_max
        dt = min(dt_adv, dt_visc, T_final - t)
        dt = min(dt, 0.002)  # hard cap for safety

        # ── Step 1: Advect ψ ──
        psi = ls_advection.advance(psi, [u, v], dt)
        psi = np.asarray(psi)
        rho = RHO_G + (RHO_L - RHO_G) * psi

        # ── Step 2: Compute explicit RHS (convection + viscosity + buoyancy) ──
        du_dx, du_xx = ccd.differentiate(u, 0)
        du_dy, du_yy = ccd.differentiate(u, 1)
        dv_dx, dv_xx = ccd.differentiate(v, 0)
        dv_dy, dv_yy = ccd.differentiate(v, 1)

        du_dx = np.asarray(du_dx); du_xx = np.asarray(du_xx)
        du_dy = np.asarray(du_dy); du_yy = np.asarray(du_yy)
        dv_dx = np.asarray(dv_dx); dv_xx = np.asarray(dv_xx)
        dv_dy = np.asarray(dv_dy); dv_yy = np.asarray(dv_yy)

        # Convection: -(u·∇)u
        conv_u = -(u * du_dx + v * du_dy)
        conv_v = -(u * dv_dx + v * dv_dy)

        # Viscous: (μ/ρ)∇²u
        visc_u = (MU / rho) * (du_xx + du_yy)
        visc_v = (MU / rho) * (dv_xx + dv_yy)

        # Buoyancy: -(ρ - ρ_ref)/ρ · g  (only y-component)
        buoyancy_v = -(rho - RHO_REF) / rho * G_ACC

        # ── Step 3: Predictor (non-incremental, no ∇p^n) ──
        u_star = u + dt * (conv_u + visc_u)
        v_star = v + dt * (conv_v + visc_v + buoyancy_v)
        wall_bc(u_star)
        wall_bc(v_star)

        # ── Step 4: PPE for full pressure ──
        du_star_dx, _ = ccd.differentiate(u_star, 0)
        dv_star_dy, _ = ccd.differentiate(v_star, 1)
        div_ustar = np.asarray(du_star_dx) + np.asarray(dv_star_dy)
        rhs_ppe = div_ustar / dt

        p = _solve_ppe(rhs_ppe, rho, ppe_builder)

        # ── Step 5: Corrector ──
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)
        u = u_star - dt / rho * np.asarray(dp_dx)
        v = v_star - dt / rho * np.asarray(dp_dy)
        wall_bc(u)
        wall_bc(v)

        t += dt
        step += 1

        # ── Diagnostics ──
        # Spike amplitude: find interface at x ≈ 0.5 (center of sin peak)
        ix_center = Nx // 2
        psi_col = psi[ix_center, :]
        Y_col = Y[ix_center, :]
        y_if = _find_interface_y(psi_col, Y_col, 0.5)
        amp = abs(y_if - 2.0) if not np.isnan(y_if) else np.nan

        ke = 0.5 * float(np.sum(rho * (u**2 + v**2)) * h**2)
        mass = float(np.sum(psi) * h**2)

        times.append(t)
        amplitudes.append(amp)
        ke_history.append(ke)
        mass_history.append(mass)

        # Snapshots
        if next_snap_idx < len(snapshot_times) and t >= snapshot_times[next_snap_idx]:
            snapshots[f"t={snapshot_times[next_snap_idx]:.1f}"] = {
                "psi": psi.copy(), "t": t
            }
            next_snap_idx += 1

        # Progress
        if step % 200 == 0 or step <= 3:
            amp_str = f"{amp:.4f}" if not np.isnan(amp) else "NaN"
            print(f"    step {step:5d}, t={t:.4f}, dt={dt:.5f}, "
                  f"A={amp_str}, KE={ke:.4e}, |u|_max={u_max:.4e}")

        # Blowup check
        if np.isnan(ke) or ke > 1e6:
            print(f"    BLOWUP at step {step}, t={t:.4f}")
            break

    # ── Measure growth rate (linear regime) ──
    times_arr = np.array(times)
    amps_arr = np.array(amplitudes)

    # Fit ln(A) = ω·t + c in the linear regime
    valid = np.isfinite(amps_arr) & (amps_arr > 0)
    mask = valid & (amps_arr > A0 * 1.2) & (amps_arr < 0.4)
    if np.sum(mask) > 5:
        t_fit = times_arr[mask]
        lnA_fit = np.log(amps_arr[mask])
        coeffs = np.polyfit(t_fit, lnA_fit, 1)
        omega_meas = coeffs[0]
    else:
        omega_meas = float('nan')

    omega_err = abs(omega_meas - OMEGA_RT) / OMEGA_RT if not np.isnan(omega_meas) else float('nan')

    print(f"\n  Results:")
    print(f"    ω_measured = {omega_meas:.4f}")
    print(f"    ω_theory   = {OMEGA_RT:.4f} (inviscid)")
    print(f"    Relative error = {omega_err:.2%}")
    print(f"    Total steps = {step}")
    mass_err = abs(mass_history[-1] - mass_0) / mass_0
    print(f"    Mass conservation: |Δm/m₀| = {mass_err:.3e}")

    return {
        "Nx": Nx, "Ny": Ny, "h": h,
        "times": times_arr, "amplitudes": amps_arr,
        "ke_history": np.array(ke_history),
        "mass_history": np.array(mass_history),
        "omega_measured": omega_meas, "omega_theory": OMEGA_RT,
        "omega_rel_err": omega_err,
        "mass_0": mass_0, "mass_final": mass_history[-1],
        "snapshots": snapshots,
        "T_final": t, "n_steps": step,
    }


def make_figures(result):
    """Generate RT instability figures."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    times = result["times"]
    amps = result["amplitudes"]
    snapshots = result["snapshots"]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # ── Left: Amplitude vs time (log scale) ──
    ax = axes[0]
    valid = np.isfinite(amps) & (amps > 0)
    ax.semilogy(times[valid], amps[valid], 'b-', linewidth=1.5, label="Numerical")
    # Theoretical: A(t) = A₀ · exp(ω_RT · t)
    t_theory = np.linspace(0, float(times[-1]), 200)
    A_theory = A0 * np.exp(OMEGA_RT * t_theory)
    ax.semilogy(t_theory, A_theory, 'r--', linewidth=1.5,
                label=f"Theory $\\omega_{{RT}}={OMEGA_RT:.3f}$")

    omega_m = result["omega_measured"]
    if not np.isnan(omega_m):
        A_fit = A0 * np.exp(omega_m * t_theory)
        ax.semilogy(t_theory, A_fit, 'g:', linewidth=1.2,
                    label=f"Measured $\\omega={omega_m:.3f}$")

    ax.set_xlabel("Time $t$", fontsize=12)
    ax.set_ylabel("Amplitude $A(t)$", fontsize=12)
    ax.set_title("RT Instability: Amplitude Growth", fontsize=13)
    ax.legend(fontsize=10)
    ax.set_xlim(0, float(times[-1]))
    ax.set_ylim(bottom=A0 * 0.3)
    ax.grid(True, alpha=0.3)

    # ── Right: Interface snapshots ──
    ax = axes[1]
    snap_keys = sorted(snapshots.keys(), key=lambda s: float(s.split("=")[1]))
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(snap_keys)))
    for i, key in enumerate(snap_keys):
        snap = snapshots[key]
        psi_snap = snap["psi"]
        Nx_s, Ny_s = psi_snap.shape
        ax.contour(
            np.linspace(0, 1, Nx_s), np.linspace(0, 4, Ny_s),
            psi_snap.T, levels=[0.5], colors=[colors[i]], linewidths=1.5
        )
        ax.plot([], [], color=colors[i], linewidth=1.5, label=key)

    ax.set_xlabel("$x$", fontsize=12)
    ax.set_ylabel("$y$", fontsize=12)
    ax.set_title("Interface Evolution ($\\psi=0.5$)", fontsize=13)
    ax.set_aspect("equal")
    ax.set_xlim(0, 1)
    ax.set_ylim(0.5, 3.5)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig(OUT / "rt_instability.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Figure saved: {OUT / 'rt_instability.png'}")


def main():
    print("\n" + "=" * 80)
    print("  【12-1】Rayleigh-Taylor Instability (§12.1)")
    print("=" * 80 + "\n")

    result = run_rt(Nx=64, Ny=256, T_final=2.5)
    make_figures(result)

    # Save data
    _snap_keys = sorted(result["snapshots"].keys(), key=lambda s: float(s.split("=")[1]))
    np.savez(OUT / "rt_data.npz",
             times=result["times"], amplitudes=result["amplitudes"],
             ke_history=result["ke_history"],
             mass_history=result["mass_history"],
             omega_measured=result["omega_measured"],
             omega_theory=result["omega_theory"],
             omega_rel_err=result["omega_rel_err"],
             mass_0=result["mass_0"],
             mass_final=result["mass_final"],
             snap_keys=np.array(_snap_keys),
             **{f"snap_{i}": result["snapshots"][k]["psi"] for i, k in enumerate(_snap_keys)})

    # Save LaTeX table
    with open(OUT / "table_rt.tex", "w") as fp:
        fp.write("% Auto-generated by exp12_1_rayleigh_taylor.py\n")
        fp.write("\\begin{tabular}{lcc}\n\\toprule\n")
        fp.write("指標 & 理論値 & ��測値 \\\\\n\\midrule\n")
        if not np.isnan(result['omega_measured']):
            fp.write(f"成長率 $\\omega_{{\\mathrm{{RT}}}}$ & "
                     f"${OMEGA_RT:.4f}$ & ${result['omega_measured']:.4f}$ \\\\\n")
            fp.write(f"相対誤差 & --- & "
                     f"${result['omega_rel_err']:.1%}$ \\\\\n")
        else:
            fp.write(f"成長率 $\\omega_{{\\mathrm{{RT}}}}$ & "
                     f"${OMEGA_RT:.4f}$ & 測定不可 \\\\\n")
        mass_err = abs(result['mass_final'] - result['mass_0']) / result['mass_0']
        fp.write(f"質量保存誤差 & $0$ & "
                 f"${mass_err:.2e}$ \\\\\n")
        fp.write("\\bottomrule\n\\end{tabular}\n")

    print(f"\n  All results saved to {OUT}")


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser()
    _parser.add_argument('--plot-only', action='store_true')
    _args = _parser.parse_args()

    if _args.plot_only:
        _d = np.load(OUT / "rt_data.npz", allow_pickle=True)
        _snap_keys = list(_d["snap_keys"])
        _snapshots = {k: {"psi": _d[f"snap_{i}"], "t": float(k.split("=")[1])}
                      for i, k in enumerate(_snap_keys)}
        _result = {
            "times": _d["times"], "amplitudes": _d["amplitudes"],
            "snapshots": _snapshots,
            "omega_measured": float(_d["omega_measured"]),
            "omega_theory": float(_d["omega_theory"]),
            "omega_rel_err": float(_d["omega_rel_err"]),
            "mass_0": float(_d["mass_0"]),
            "mass_final": float(_d["mass_final"]),
        }
        make_figures(_result)
    else:
        main()
