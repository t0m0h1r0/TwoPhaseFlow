#!/usr/bin/env python3
"""Static droplet — C/RC (CCD-enhanced Rhie-Chow) verification.

§7-faithful setup:
  - RC Balanced-Force (kappa/psi/we)
  - DCCD (ε_d=1/4) for PPE RHS checkerboard suppression
  - C/RC correction: h/12*(p''_E − p''_P) added to RC bracket (§7.4.3)
  - CCD ∇p corrector (balanced-force)
  - FD spsolve as comparison PPE solver

Compares: standard RC vs C/RC at N=32, 64, 128
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
import scipy.sparse as sp
from scipy.sparse.linalg import spsolve

from twophase.backend import Backend
from twophase.core.grid import Grid
from twophase.config import GridConfig
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.heaviside import heaviside
from twophase.levelset.curvature import CurvatureCalculator
from twophase.pressure.ppe_builder import PPEBuilder
from twophase.pressure.rhie_chow import RhieChowInterpolator
from twophase.pressure.velocity_corrector import ccd_pressure_gradient

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
N_STEPS = 400
N_LIST  = [32, 64, 128]


# ── C/RC correction ─────────────────────────────────────────────────────────

def precompute_d2_fsigma(ccd, xp, kappa, psi, we, grid):
    """Precompute d2(f_σ) for each axis (static interface, computed once).

    f_σ_cell = (κ/We) · D¹_CCD(ψ) at cell centers.
    Returns list of d2(f_σ) arrays, one per axis.
    """
    d2_fs = []
    for ax in range(grid.ndim):
        dpsi_ax, _ = ccd.differentiate(xp.asarray(psi), ax)
        f_sigma_cell = xp.asarray(kappa) * dpsi_ax / we
        _, d2_fs_ax = ccd.differentiate(f_sigma_cell, ax)
        d2_fs.append(np.asarray(d2_fs_ax))
    return d2_fs


def crc_divergence_correction(ccd, xp, p, grid, dt, rho, d2_fsigma=None):
    """C/RC correction to RC divergence (§7.4.3 eq:rc-face-balanced-ho).

    Applies coefficient matching to BOTH pressure and f_σ brackets:
      pressure: +h/12*(p''_E − p''_P)   → cancel p''' mismatch
      f_σ:      −h/12*(fσ''_E − fσ''_P) → cancel fσ''' mismatch

    The full C/RC bracket correction (eq:rc-face-balanced-ho):
      Δbracket = +h/12*(d2p_R − d2p_L) − h/12*(d2fs_R − d2fs_L)

    Parameters
    ----------
    d2_fsigma : list of arrays — precomputed d2(f_σ) per axis (static interface)
                If None, only pressure correction is applied.
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

        d2p_L = d2p[sl(slice(0, N_ax))]
        d2p_R = d2p[sl(slice(1, N_ax + 1))]
        rho_L = rho[sl(slice(0, N_ax))]
        rho_R = rho[sl(slice(1, N_ax + 1))]
        inv_rho_harm = 2.0 / (rho_L + rho_R)

        # C/RC pressure bracket: +h/12*(d2p_R − d2p_L)
        delta_bracket = (h / 12.0) * (d2p_R - d2p_L)

        # C/RC f_σ bracket: −h/12*(d2fs_R − d2fs_L)
        if d2_fsigma is not None:
            d2fs = d2_fsigma[ax]
            d2fs_L = d2fs[sl(slice(0, N_ax))]
            d2fs_R = d2fs[sl(slice(1, N_ax + 1))]
            delta_bracket -= (h / 12.0) * (d2fs_R - d2fs_L)

        corr_face = -dt * inv_rho_harm * delta_bracket

        flux_shape = list(grid.shape)
        flux_shape[ax] = N_ax + 1
        flux = np.zeros(flux_shape)
        flux[sl(slice(1, N_ax + 1))] = corr_face

        sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(1, None)
        sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, -1)
        div_int = (flux[tuple(sl_hi)] - flux[tuple(sl_lo)]) / h
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

    gc   = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd  = CCDSolver(grid, backend, bc_type="wall")

    X, Y    = grid.meshgrid()
    phi_raw = R - np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    psi     = np.asarray(heaviside(np, phi_raw, eps))
    rho     = RHO_G + (RHO_L - RHO_G) * psi

    rhie_chow = RhieChowInterpolator(backend, grid, ccd, bc_type="wall")
    ppb       = PPEBuilder(backend, grid, bc_type="wall")
    triplet, A_shape = ppb.build(rho)
    A_fd = sp.csr_matrix((triplet[0], (triplet[1], triplet[2])), shape=A_shape)
    pin  = ppb._pin_dof

    curv_calc = CurvatureCalculator(backend, ccd, eps)
    kappa     = np.asarray(curv_calc.compute(psi))

    dpsi_dx, _ = ccd.differentiate(psi, 0)
    dpsi_dy, _ = ccd.differentiate(psi, 1)
    f_csf_x = (SIGMA / WE) * kappa * np.asarray(dpsi_dx)
    f_csf_y = (SIGMA / WE) * kappa * np.asarray(dpsi_dy)

    # C/RC f_σ bracket correction is NOT applied: f_σ = (κ/We)D¹ψ is
    # discontinuous near the interface, so d2(f_σ) is large and the
    # correction destabilises the scheme.  C/RC is applied to pressure only.

    def wall_bc(arr):
        arr[0, :] = 0.0; arr[-1, :] = 0.0
        arr[:, 0] = 0.0; arr[:, -1] = 0.0

    u = np.zeros_like(X); v = np.zeros_like(X); p = np.zeros_like(X)
    u_max_hist = []

    for step in range(N_STEPS):
        u_star = u + dt / rho * f_csf_x
        v_star = v + dt / rho * f_csf_y
        wall_bc(u_star); wall_bc(v_star)

        # PPE RHS: RC BF divergence + C/RC correction (§7.4.3 eq:rc-face-balanced-ho)
        div_rc = rhie_chow.face_velocity_divergence(
            [u_star, v_star], p, rho, dt,
            kappa=xp.asarray(kappa), psi=xp.asarray(psi), we=WE,
        )
        if use_crc:
            crc_corr = crc_divergence_correction(
                ccd, xp, p, grid, dt, rho, d2_fsigma=None,
            )
            div_rc = div_rc + xp.asarray(crc_corr)

        rhs_vec = np.asarray(div_rc).ravel() / dt
        rhs_vec[pin] = 0.0
        p = spsolve(A_fd, rhs_vec).reshape(grid.shape)

        # Corrector: CCD ∇p (balanced-force)
        grad_p = ccd_pressure_gradient(ccd, xp.asarray(p), grid.ndim)
        u = u_star - dt / rho * np.asarray(grad_p[0])
        v = v_star - dt / rho * np.asarray(grad_p[1])
        wall_bc(u); wall_bc(v)

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
