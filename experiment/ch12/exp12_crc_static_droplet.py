#!/usr/bin/env python3
"""Static droplet — C/RC (CCD-enhanced Rhie-Chow) verification.

§7-faithful setup:
  - Periodic BC (avoids CCD wall Neumann null-space issue)
  - DCCD (ε_d=1/4) filtered CCD divergence for PPE RHS (§7.5)
  - CCD-PPE Kronecker LU (§8b)
  - CCD ∇p corrector (balanced-force)

Compares: DCCD+CCD-PPE baseline vs with C/RC at N=32, 64
Grid convergence of ‖u‖∞ and Δp error.

A3 traceability
───────────────
  C/RC theory     → §7.4.3 eq:rc_crc_bracket
  Balanced-Force  → §7 eq:rc-face-balanced
  DCCD            → §7 eq:dccd_ppe_rhs

Output:
  experiment/ch12/results/crc_static_droplet/
    crc_static_droplet.pdf
    crc_static_droplet_data.npz

Usage:
  python experiment/ch12/exp12_crc_static_droplet.py
  python experiment/ch12/exp12_crc_static_droplet.py --plot-only
"""

import sys, pathlib, argparse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.dccd_ppe_filter import DCCDPPEFilter
from twophase.pressure.ppe_solver_ccd_lu import PPESolverCCDLU
from twophase.pressure.velocity_corrector import ccd_pressure_gradient
from twophase.config import SimulationConfig

OUT_DIR = pathlib.Path(__file__).resolve().parent / "results" / "crc_static_droplet"
OUT_DIR.mkdir(parents=True, exist_ok=True)
NPZ_PATH = OUT_DIR / "crc_static_droplet_data.npz"
FIG_PATH = OUT_DIR / "crc_static_droplet.pdf"

# ── Physical parameters ──────────────────────────────────────────────────────
R       = 0.25
SIGMA   = 1.0
WE      = 10.0
RHO_G   = 1.0
RHO_L   = 2.0
N_STEPS = 100
N_LIST  = [32, 64]


# ── C/RC correction ─────────────────────────────────────────────────────────

def crc_divergence_correction(ccd, xp, p, grid, dt, rho, bc_type="periodic"):
    """C/RC correction to RC divergence (§7.4.3 eq:rc-face-balanced-ho).

    Adds h/12*(p''_E − p''_P) to the standard RC bracket at each face.
    Pressure only (f_σ bracket excluded — see §7.4.3 note).
    """
    ndim = grid.ndim
    correction = np.zeros(grid.shape)

    for ax in range(ndim):
        N_ax = grid.N[ax]
        h = float(grid.L[ax] / N_ax)

        _, d2p = ccd.differentiate(xp.asarray(p), ax)
        d2p = np.asarray(d2p)

        def sl(idx):
            s = [slice(None)] * ndim
            s[ax] = idx
            return tuple(s)

        # Internal faces: face k between nodes k-1 and k (faces 1..N_ax)
        d2p_L = d2p[sl(slice(0, N_ax))]
        d2p_R = d2p[sl(slice(1, N_ax + 1))]
        rho_L = rho[sl(slice(0, N_ax))]
        rho_R = rho[sl(slice(1, N_ax + 1))]
        inv_rho_harm = 2.0 / (rho_L + rho_R)

        corr_face = -dt * inv_rho_harm * (h / 12.0) * (d2p_R - d2p_L)

        # Build face flux array
        flux_shape = list(grid.shape)
        flux_shape[ax] = N_ax + 1
        flux = np.zeros(flux_shape)
        flux[sl(slice(1, N_ax + 1))] = corr_face

        if bc_type == "periodic":
            # Face 0 wraps: node N_ax ↔ node 0
            d2p_L0 = d2p[sl(N_ax)]
            d2p_R0 = d2p[sl(0)]
            rho_L0 = rho[sl(N_ax)]
            rho_R0 = rho[sl(0)]
            inv_rho_0 = 2.0 / (rho_L0 + rho_R0)
            flux[sl(0)] = -dt * inv_rho_0 * (h / 12.0) * (d2p_R0 - d2p_L0)

        # FVM divergence
        sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(1, None)
        sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, -1)
        div_int = (flux[tuple(sl_hi)] - flux[tuple(sl_lo)]) / h

        if bc_type == "periodic":
            div_Nax = (flux[sl(0)] - flux[sl(N_ax)]) / h
            # reshape for concat
            shape_1 = list(div_int.shape); shape_1[ax] = 1
            correction += np.concatenate(
                [div_int, np.reshape(div_Nax, shape_1)], axis=ax
            )
        else:
            sl_last = [slice(None)] * ndim; sl_last[ax] = slice(-1, None)
            div_Nax = -flux[tuple(sl_last)] / h
            correction += np.concatenate([div_int, div_Nax], axis=ax)

    return correction


# ── Core simulation ──────────────────────────────────────────────────────────

def run(N: int, use_crc: bool):
    """Run static droplet with or without C/RC.

    Parameters
    ----------
    N       : grid resolution
    use_crc : if True, apply C/RC correction to RC divergence
    """
    backend = Backend(use_gpu=False)
    xp = backend.xp

    h   = 1.0 / N
    eps = 1.5 * h
    dt  = 0.25 * h

    bc = "periodic"

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type=bc)

    X, Y    = grid.meshgrid()
    phi_raw = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi     = np.asarray(heaviside(np, phi_raw, eps))
    rho     = RHO_G + (RHO_L - RHO_G) * psi

    dccd_filt = DCCDPPEFilter(backend, grid, ccd, bc_type=bc)

    # CCD-PPE: Kronecker LU (periodic BC, §8b)
    sim_cfg = SimulationConfig()
    ppe_solver = PPESolverCCDLU(backend, sim_cfg, grid, ccd)

    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa     = np.asarray(curv_calc.compute(psi))

    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)
    u_max_hist = []

    for step in range(N_STEPS):
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y

        # PPE RHS: DCCD-filtered CCD divergence (§7.5 eq:dccd_ppe_rhs)
        # C/RC-DCCD: use d2 to reduce filter dissipation O(ε_d h²) → O(ε_d h⁴)
        div_rhs = dccd_filt.compute_filtered_divergence(
            [u_star, v_star], crc_dccd=use_crc,
        )

        rhs_field = np.asarray(div_rhs).reshape(grid.shape) / dt
        p = np.asarray(ppe_solver.solve(rhs_field, rho, dt, p_init=p))

        # Corrector: CCD ∇p (balanced-force)
        grad_p = ccd_pressure_gradient(ccd, xp.asarray(p), grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])

        u_max_hist.append(float(np.max(np.sqrt(u**2 + v**2))))
        if np.isnan(u_max_hist[-1]) or u_max_hist[-1] > 1e6:
            print(f"    BLOWUP at step={step+1}")
            break

    inside   = phi_raw >  3.0 / N
    outside  = phi_raw < -3.0 / N
    dp_exact = SIGMA / (R * WE)
    dp_meas  = float(np.mean(p[inside]) - np.mean(p[outside]))
    dp_err   = abs(dp_meas - dp_exact) / dp_exact

    near       = np.abs(phi_raw) < 2.0 * eps
    kappa_mean = float(np.mean(kappa[near])) if np.any(near) else float("nan")
    kappa_std  = float(np.std(kappa[near]))  if np.any(near) else float("nan")

    return {
        "N": N, "use_crc": use_crc,
        "u_max": float(np.max(np.sqrt(u**2 + v**2))),
        "u_max_hist": np.array(u_max_hist),
        "dp_meas": dp_meas, "dp_exact": dp_exact, "dp_err": dp_err,
        "kappa_mean": kappa_mean, "kappa_std": kappa_std,
        "phi_raw": phi_raw, "p": p, "vel_mag": np.sqrt(u**2 + v**2),
    }


# ── Main ─────────────────────────────────────────────────────────────────────

def compute_all():
    results = {}
    for N in N_LIST:
        for crc in [False, True]:
            tag = f"N{N}_{'crc' if crc else 'std'}"
            print(f"  [{tag}] ...")
            r = run(N, crc)
            print(f"    κ̄={r['kappa_mean']:.3f}  σ_κ={r['kappa_std']:.3f} "
                  f"| ‖u‖∞={r['u_max']:.3e}  Δp err={r['dp_err']*100:.2f}%")
            results[tag] = r
    return results


def save_npz(results):
    flat = {}
    for tag, r in results.items():
        for k, v in r.items():
            if isinstance(v, bool):
                v = int(v)
            flat[f"{tag}__{k}"] = np.asarray(v)
    np.savez(NPZ_PATH, **flat)
    print(f"Saved data → {NPZ_PATH}")


def load_npz():
    data = np.load(NPZ_PATH, allow_pickle=False)
    results = {}
    for fullkey, val in data.items():
        tag, subkey = fullkey.split("__", 1)
        results.setdefault(tag, {})[subkey] = val
    for r in results.values():
        for k in ("u_max", "dp_meas", "dp_exact", "dp_err", "N",
                  "kappa_mean", "kappa_std"):
            if k in r:
                r[k] = float(r[k])
        if "use_crc" in r:
            r["use_crc"] = bool(int(r["use_crc"]))
    return results


# ── Plotting ─────────────────────────────────────────────────────────────────

def plot(results):
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.35)

    # Separate std/crc results
    std_tags = sorted([t for t in results if t.endswith("_std")])
    crc_tags = sorted([t for t in results if t.endswith("_crc")])

    # ── Panel (0,0): ‖u‖∞ grid convergence ──
    ax00 = fig.add_subplot(gs[0, 0])
    for tags, label, color, marker in [
        (std_tags, "Standard RC", "C0", "o"),
        (crc_tags, "C/RC", "C4", "^"),
    ]:
        Ns = [int(results[t]["N"]) for t in tags]
        hs = [1.0 / n for n in Ns]
        u_maxs = [results[t]["u_max"] for t in tags]
        ax00.loglog(hs, u_maxs, f"{marker}-", color=color, lw=2, ms=8, label=label)
    # Reference slopes
    hs_ref = np.array([1.0/N_LIST[0], 1.0/N_LIST[-1]])
    u0 = results[std_tags[0]]["u_max"]
    ax00.loglog(hs_ref, u0 * (hs_ref / hs_ref[0])**2,
                ":", color="gray", alpha=0.5, label="$h^2$ ref")
    ax00.set_xlabel("$h$"); ax00.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax00.set_title(r"Spurious current: grid convergence")
    ax00.legend(fontsize=9); ax00.grid(True, which="both", ls="--", alpha=0.3)

    # ── Panel (0,1): Δp error grid convergence ──
    ax01 = fig.add_subplot(gs[0, 1])
    for tags, label, color, marker in [
        (std_tags, "Standard RC", "C0", "o"),
        (crc_tags, "C/RC", "C4", "^"),
    ]:
        Ns = [int(results[t]["N"]) for t in tags]
        hs = [1.0 / n for n in Ns]
        dp_errs = [results[t]["dp_err"] for t in tags]
        ax01.loglog(hs, dp_errs, f"{marker}-", color=color, lw=2, ms=8, label=label)
    ax01.loglog(hs_ref, results[std_tags[0]]["dp_err"] * (hs_ref/hs_ref[0])**2,
                ":", color="gray", alpha=0.5, label="$h^2$ ref")
    ax01.set_xlabel("$h$"); ax01.set_ylabel(r"$|\Delta p - \Delta p_{\mathrm{exact}}| / \Delta p_{\mathrm{exact}}$")
    ax01.set_title(r"Laplace pressure error: grid convergence")
    ax01.legend(fontsize=9); ax01.grid(True, which="both", ls="--", alpha=0.3)

    # ── Panel (1,0): ‖u‖∞ time history (all N) ──
    ax10 = fig.add_subplot(gs[1, 0])
    cmap = {"32": 0.4, "64": 0.7, "128": 1.0}
    for tag in sorted(results.keys()):
        r = results[tag]
        N_val = int(r["N"])
        is_crc = "crc" in tag
        hist = np.asarray(r["u_max_hist"])
        t_ax = np.arange(1, len(hist) + 1) * 0.25 / N_val
        ax10.semilogy(t_ax, hist,
                      "-." if is_crc else "-",
                      color=f"C4" if is_crc else "C0",
                      alpha=cmap.get(str(N_val), 1.0),
                      lw=1.5,
                      label=f"N={N_val} {'C/RC' if is_crc else 'std'}")
    ax10.set_xlabel("Physical time $t$")
    ax10.set_ylabel(r"$\|\mathbf{u}\|_\infty$")
    ax10.set_title("Spurious current history")
    ax10.legend(fontsize=7, ncol=2); ax10.grid(True, which="both", ls="--", alpha=0.3)

    # ── Panel (1,1): Summary table ──
    ax11 = fig.add_subplot(gs[1, 1])
    ax11.axis("off")
    rows = [["N", "RC", r"$\|u\|_\infty$", r"$\Delta p$ err", "reduction"]]
    for N in N_LIST:
        std_r = results[f"N{N}_std"]
        crc_r = results[f"N{N}_crc"]
        red = (1.0 - crc_r["u_max"] / std_r["u_max"]) * 100
        rows.append([str(N), "std", f"{std_r['u_max']:.2e}", f"{std_r['dp_err']*100:.2f}%", "—"])
        rows.append([str(N), "C/RC", f"{crc_r['u_max']:.2e}", f"{crc_r['dp_err']*100:.2f}%",
                     f"{red:+.1f}%"])
    table = ax11.table(cellText=rows[1:], colLabels=rows[0],
                       loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.4)
    ax11.set_title("Summary: Standard RC vs C/RC", fontsize=10, pad=20)

    dp_exact = SIGMA / (R * WE)
    fig.suptitle(
        f"Static droplet — C/RC (CCD-enhanced Rhie-Chow) verification\n"
        f"$R={R}$, $\\rho_l/\\rho_g={int(RHO_L)}$, $We={WE}$, "
        f"{N_STEPS} steps, $\\Delta p_{{exact}}={dp_exact:.4f}$",
        fontsize=10, y=1.01,
    )
    fig.savefig(FIG_PATH, format="pdf", bbox_inches="tight")
    print(f"Saved figure → {FIG_PATH}")
    plt.close(fig)


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plot-only", action="store_true")
    args = parser.parse_args()

    if args.plot_only:
        results = load_npz()
    else:
        results = compute_all()
        save_npz(results)
    plot(results)


if __name__ == "__main__":
    main()
