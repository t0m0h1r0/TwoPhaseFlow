#!/usr/bin/env python3
"""[11-19] CLS shape preservation: priority-ordered parameter study.

Tests four improvements for CLS shape accuracy (single vortex, N=128):
  P1: DCCD filter strength eps_d  (0.05, 0.025, 0.01, 0.0)
  P2: Interface thickness eps/h   (2.0, 1.5, 1.0, 0.75)
  P3: Adaptive reinit trigger     (M(tau)/M_ref > threshold vs fixed freq)
  P4: TVD-RK3 pseudo-time for reinit (vs Forward Euler)

Baseline: eps_d=0.05, eps=1.5h, reinit every 10 steps, FE reinit.
"""

import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
from twophase.backend import Backend
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection
from twophase.levelset.reinitialize import Reinitializer
from twophase.levelset.heaviside import heaviside, invert_heaviside
from twophase.initial_conditions.velocity_fields import SingleVortex
from twophase.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    COLORS, FIGSIZE_2COL,
)

apply_style()
OUT = experiment_dir(__file__)


def single_vortex_field(X, Y, t, T):
    """LeVeque (1996) single vortex — delegates to library."""
    return SingleVortex(period=T).compute(X, Y, t=t)


def run_vortex(N, eps_over_h, eps_d, reinit_mode, reinit_n_steps,
               rk3_reinit, backend):
    """Run single vortex test with given parameters.

    reinit_mode: ('fixed', freq) or ('adaptive', threshold)
    rk3_reinit:  if True, use TVD-RK3 for reinit pseudo-time steps
    """
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_over_h * h
    X, Y = grid.meshgrid()

    phi0 = np.sqrt((X - 0.5)**2 + (Y - 0.75)**2) - 0.15
    psi0 = heaviside(np, phi0, eps)

    adv = DissipativeCCDAdvection(
        backend, grid, ccd, bc="zero", eps_d=eps_d, mass_correction=True,
    )

    # For TVD-RK3 reinit, use n_steps=1 and call 3x externally
    actual_n_steps = reinit_n_steps if not rk3_reinit else 1
    reinit = Reinitializer(
        backend, grid, ccd, eps, n_steps=actual_n_steps, bc="zero",
        mass_correction=True,
    )

    T_final = 8.0; dt = 0.45 / N
    n_steps = int(T_final / dt); dt = T_final / n_steps
    psi = psi0.copy()
    mass0 = float(np.sum(psi))

    # Volume monitor baseline for adaptive trigger
    M_ref = float(np.sum(psi * (1.0 - psi))) * (h ** 2)
    reinit_count = 0

    for step in range(n_steps):
        u, v = single_vortex_field(X, Y, step * dt, T_final)
        psi = adv.advance(psi, [u, v], dt)

        # Reinit decision
        do_reinit = False
        if reinit_mode[0] == 'fixed':
            freq = reinit_mode[1]
            if freq > 0 and (step + 1) % freq == 0:
                do_reinit = True
        elif reinit_mode[0] == 'adaptive':
            threshold = reinit_mode[1]
            M_cur = float(np.sum(psi * (1.0 - psi))) * (h ** 2)
            if M_ref > 1e-15 and M_cur / M_ref > threshold:
                do_reinit = True

        if do_reinit:
            if rk3_reinit:
                # TVD-RK3 for reinit: 3 evaluations per pseudo-step
                for _ in range(reinit_n_steps):
                    psi = _rk3_reinit_step(psi, reinit)
            else:
                psi = reinit.reinitialize(psi)
            reinit_count += 1
            M_ref = float(np.sum(psi * (1.0 - psi))) * (h ** 2)

    mass_err = abs(float(np.sum(psi)) - mass0) / max(mass0, 1e-15)
    err_L2 = float(np.sqrt(np.mean((psi - psi0)**2)))
    phi_final = invert_heaviside(np, psi, eps)
    band = np.abs(phi0) < 6 * eps
    err_L2_phi = float(np.sqrt(np.mean((phi_final[band] - phi0[band])**2)))
    area0 = float(np.sum(psi0 >= 0.5))
    area_err = abs(float(np.sum(psi >= 0.5)) - area0) / max(area0, 1.0)
    return {"L2": err_L2, "L2_phi": err_L2_phi, "area_err": area_err,
            "mass_err": mass_err, "reinit_count": reinit_count}


def _rk3_reinit_step(psi, reinit):
    """One TVD-RK3 pseudo-time step using the reinitializer's internals.

    Uses Reinitializer with n_steps=1 as a single FE step builder,
    then combines via Shu-Osher TVD-RK3 weights.
    """
    xp = reinit.xp
    dtau = reinit.dtau

    def L(q):
        """Compute RHS = -compression + diffusion for one step."""
        ccd = reinit.ccd
        ndim = reinit.grid.ndim
        eps_val = reinit.eps

        # Gradient + Laplacian
        dpsi = []
        d2psi_sum = xp.zeros_like(q)
        for ax in range(ndim):
            g1, g2 = ccd.differentiate(q, ax)
            dpsi.append(g1)
            d2psi_sum += g2

        grad_sq = sum(g * g for g in dpsi)
        safe_grad = xp.maximum(xp.sqrt(xp.maximum(grad_sq, 1e-28)), 1e-14)
        n_hat = [g / safe_grad for g in dpsi]

        # Compression with DCCD
        from twophase.levelset.reinitialize import _EPS_D_COMP, _pad_bc, _sl
        psi_1mpsi = q * (1.0 - q)
        C = xp.zeros_like(q)
        for ax in range(ndim):
            flux_ax = psi_1mpsi * n_hat[ax]
            g_prime, _ = ccd.differentiate(flux_ax, ax)
            g_prime_pad = _pad_bc(xp, g_prime, ax, 1, reinit._bc)
            sl_c = _sl(q.ndim, ax, 1, -1)
            sl_p1 = _sl(q.ndim, ax, 2, None)
            sl_m1 = _sl(q.ndim, ax, 0, -2)
            g_tilde = (g_prime_pad[sl_c]
                       + _EPS_D_COMP * (g_prime_pad[sl_p1]
                                        - 2.0 * g_prime_pad[sl_c]
                                        + g_prime_pad[sl_m1]))
            C = C + g_tilde

        # Diffusion
        D = eps_val * d2psi_sum
        return -C + D

    # TVD-RK3 (Shu-Osher)
    q0 = xp.copy(psi)
    M_old = float(xp.sum(q0))
    q1 = xp.clip(q0 + dtau * L(q0), 0.0, 1.0)
    q2 = xp.clip(0.75 * q0 + 0.25 * (q1 + dtau * L(q1)), 0.0, 1.0)
    q_new = xp.clip(
        (1.0 / 3.0) * q0 + (2.0 / 3.0) * (q2 + dtau * L(q2)),
        0.0, 1.0,
    )

    # Mass correction
    M_new = float(xp.sum(q_new))
    w = 4.0 * q_new * (1.0 - q_new)
    W = float(xp.sum(w))
    if W > 1e-12:
        q_new = q_new + ((M_old - M_new) / W) * w
        q_new = xp.clip(q_new, 0.0, 1.0)

    return q_new


# ── P1: eps_d study ───────────────────────────────────────────────────────

def test_p1_eps_d(N=128):
    backend = Backend(use_gpu=False)
    eps_ds = [0.05, 0.025, 0.01, 0.0]
    results = []
    print(f"\n=== P1: eps_d Study (N={N}) ===")
    for ed in eps_ds:
        t0 = time.time()
        r = run_vortex(N, 1.5, ed, ('fixed', 10), 4, False, backend)
        elapsed = time.time() - t0
        r["eps_d"] = ed
        results.append(r)
        print(f"  eps_d={ed:.3f}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e} ({elapsed:.0f}s)")
    return results


# ── P2: eps study ─────────────────────────────────────────────────────────

def test_p2_eps(N=128):
    backend = Backend(use_gpu=False)
    eps_ratios = [2.0, 1.5, 1.0, 0.75]
    results = []
    print(f"\n=== P2: eps/h Study (N={N}) ===")
    for er in eps_ratios:
        t0 = time.time()
        r = run_vortex(N, er, 0.05, ('fixed', 10), 4, False, backend)
        elapsed = time.time() - t0
        r["eps_ratio"] = er
        results.append(r)
        print(f"  eps/h={er:.2f}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, area={r['area_err']:.2e} ({elapsed:.0f}s)")
    return results


# ── P3: adaptive reinit ──────────────────────────────────────────────────

def test_p3_adaptive(N=128):
    backend = Backend(use_gpu=False)
    configs = [
        ("fixed-10",     ('fixed', 10)),
        ("fixed-20",     ('fixed', 20)),
        ("adaptive-1.05", ('adaptive', 1.05)),
        ("adaptive-1.10", ('adaptive', 1.10)),
        ("adaptive-1.20", ('adaptive', 1.20)),
        ("no-reinit",     ('fixed', 0)),
    ]
    results = []
    print(f"\n=== P3: Adaptive Reinit (N={N}) ===")
    for name, mode in configs:
        t0 = time.time()
        r = run_vortex(N, 1.5, 0.05, mode, 4, False, backend)
        elapsed = time.time() - t0
        r["name"] = name
        results.append(r)
        print(f"  {name:>16}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, "
              f"reinits={r['reinit_count']} ({elapsed:.0f}s)")
    return results


# ── P4: TVD-RK3 reinit ──────────────────────────────────────────────────

def test_p4_rk3_reinit(N=128):
    backend = Backend(use_gpu=False)
    configs = [
        ("FE-4step",   4, False),
        ("RK3-4step",  4, True),
        ("FE-8step",   8, False),
        ("RK3-2step",  2, True),
    ]
    results = []
    print(f"\n=== P4: TVD-RK3 Reinit (N={N}) ===")
    for name, ns, rk3 in configs:
        t0 = time.time()
        r = run_vortex(N, 1.5, 0.05, ('fixed', 10), ns, rk3, backend)
        elapsed = time.time() - t0
        r["name"] = name
        results.append(r)
        print(f"  {name:>12}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e} ({elapsed:.0f}s)")
    return results


# ── Combined best ─────────────────────────────────────────────────────────

def test_combined_best(N=128):
    """Run with best parameters from each study combined."""
    backend = Backend(use_gpu=False)
    configs = [
        # (label, eps_ratio, eps_d, reinit_mode, n_steps, rk3)
        ("baseline",       1.5,  0.05,  ('fixed', 10),      4, False),
        ("best-eps_d",     1.5,  0.01,  ('fixed', 10),      4, False),
        ("best-eps",       1.0,  0.05,  ('fixed', 10),      4, False),
        ("best-adaptive",  1.5,  0.05,  ('adaptive', 1.10),  4, False),
        ("combined-123",   1.0,  0.01,  ('adaptive', 1.10),  4, False),
        ("combined-all",   1.0,  0.01,  ('adaptive', 1.10),  4, True),
    ]
    results = []
    print(f"\n=== Combined Best (N={N}) ===")
    for label, er, ed, mode, ns, rk3 in configs:
        t0 = time.time()
        r = run_vortex(N, er, ed, mode, ns, rk3, backend)
        elapsed = time.time() - t0
        r["name"] = label
        results.append(r)
        print(f"  {label:>16}: L2ψ={r['L2']:.4e}, L2φ={r['L2_phi']:.4e}, "
              f"reinits={r['reinit_count']} ({elapsed:.0f}s)")
    return results


# ── Plotting ──────────────────────────────────────────────────────────────

def plot_all(p1, p2, p3, p4, combined):
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 3, figsize=(10.5, 6.5))

    # (a) P1: eps_d
    ax = axes[0, 0]
    eds = [r["eps_d"] for r in p1]
    l2s = [r["L2"] for r in p1]
    ax.plot(eds, l2s, "o-", color=COLORS[0])
    ax.set_xlabel(r"$\varepsilon_d$")
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title(r"(a) P1: Filter strength $\varepsilon_d$")
    ax.grid(True, alpha=0.3)
    ax.invert_xaxis()

    # (b) P2: eps/h
    ax = axes[0, 1]
    ers = [r["eps_ratio"] for r in p2]
    l2s = [r["L2"] for r in p2]
    ax.plot(ers, l2s, "s-", color=COLORS[1])
    ax.set_xlabel(r"$\varepsilon / h$")
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title(r"(b) P2: Interface thickness $\varepsilon/h$")
    ax.grid(True, alpha=0.3)

    # (c) P3: adaptive reinit
    ax = axes[0, 2]
    names = [r["name"] for r in p3]
    l2s = [r["L2"] for r in p3]
    x = range(len(names))
    bars = ax.bar(x, l2s, color=COLORS[2], alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=6)
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title("(c) P3: Reinit strategy")
    ax.grid(True, alpha=0.3, axis="y")
    # Annotate reinit counts
    for bar, r in zip(bars, p3):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f'{r["reinit_count"]}', ha='center', va='bottom', fontsize=6)

    # (d) P4: RK3 reinit
    ax = axes[1, 0]
    names = [r["name"] for r in p4]
    l2s = [r["L2"] for r in p4]
    x = range(len(names))
    ax.bar(x, l2s, color=COLORS[3], alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=7)
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title("(d) P4: Reinit time integration")
    ax.grid(True, alpha=0.3, axis="y")

    # (e) Combined
    ax = axes[1, 1]
    names = [r["name"] for r in combined]
    l2s = [r["L2"] for r in combined]
    colors_e = [COLORS[0]] + [COLORS[i % len(COLORS)] for i in range(1, len(names))]
    x = range(len(names))
    bars = ax.bar(x, l2s, color=colors_e, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=6)
    ax.set_ylabel(r"$L_2$ error")
    ax.set_title("(e) Combined improvements")
    ax.grid(True, alpha=0.3, axis="y")
    # Baseline reference line
    ax.axhline(combined[0]["L2"], color="gray", ls=":", alpha=0.5)

    # (f) Summary table as text
    ax = axes[1, 2]
    ax.axis("off")
    baseline_l2 = combined[0]["L2"]
    rows = []
    for r in combined:
        improvement = (1.0 - r["L2"] / baseline_l2) * 100
        rows.append([r["name"], f'{r["L2"]:.4e}', f'{improvement:+.1f}%'])
    table = ax.table(cellText=rows,
                     colLabels=["Config", "$L_2$", "vs baseline"],
                     loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(7)
    table.scale(1.0, 1.4)
    ax.set_title("(f) Summary", fontsize=10)

    fig.tight_layout()
    save_figure(fig, OUT / "shape_preservation")


def main():
    args = experiment_argparser("[11-19] Shape Preservation").parse_args()
    if args.plot_only:
        d = load_results(OUT / "data.npz")
        plot_all(d["p1"], d["p2"], d["p3"], d["p4"], d["combined"])
        return

    p1 = test_p1_eps_d()
    p2 = test_p2_eps()
    p3 = test_p3_adaptive()
    p4 = test_p4_rk3_reinit()
    combined = test_combined_best()

    save_results(OUT / "data.npz", {
        "p1": p1, "p2": p2, "p3": p3, "p4": p4, "combined": combined,
    })
    plot_all(p1, p2, p3, p4, combined)

    # Summary
    baseline_psi = combined[0]["L2"]
    baseline_phi = combined[0]["L2_phi"]
    print(f"\n=== Final Summary (baseline L2ψ={baseline_psi:.4e}, L2φ={baseline_phi:.4e}) ===")
    for r in combined:
        impr_psi = (1.0 - r["L2"] / baseline_psi) * 100
        impr_phi = (1.0 - r["L2_phi"] / baseline_phi) * 100
        print(f"  {r['name']:>16}: L2ψ={r['L2']:.4e} ({impr_psi:+.1f}%), "
              f"L2φ={r['L2_phi']:.4e} ({impr_phi:+.1f}%)")


if __name__ == "__main__":
    main()
