"""
CLS Uniform-Flow Advection — Exact-Solution Convergence Study

Exact solution (all t):  ψ_exact(x, y, t) = ψ₀(x − u·t, y)

Setup
-----
Domain        : [0, 1]²  (periodic BC)
Initial ψ     : tanh circle, R = 0.10, center = (0.30, 0.50)
               ψ₀ = 1 / (1 + exp((r − R) / ε)),  ε = 1.5 h
Velocity      : u = (1, 0)  (uniform, constant)
Final time    : T = 0.10   →  center at (0.40, 0.50)  (no boundary wrap)
Grids         : N = 32, 64, 128, 256

Two experiments
---------------
A. CFL-limited dt (dt = 0.4 h):
   Accumulates both spatial and temporal error.
   Expected convergence:
     DCCD   : O(h²)  — spatial filter truncation dominates
     WENO5  : O(h³)  — TVD-RK3 temporal error dominates over O(h⁵) spatial

B. Fixed dt = 1e-5 (temporal error negligible):
   Isolates spatial scheme order.
   Expected convergence:
     DCCD   : O(h²)  — filter truncation ε_d h² d³f/dx³
     WENO5  : O(h⁵)  — smooth-region WENO5 accuracy

Sanity checks (EXP-02)
----------------------
SC-3: symmetry  max|ψ(x,y) − ψ(x,1−y)| < 1e-12  (y-mirror, u_y = 0)
SC-4: mass conservation  |∫ψ dA|_T / |∫ψ dA|_0 − 1| < 1e-4
"""

from __future__ import annotations
import sys
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from twophase.backend import Backend
from twophase.config import SimulationConfig, GridConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.levelset.advection import DissipativeCCDAdvection, LevelSetAdvection


# ── Experiment parameters ─────────────────────────────────────────────────────
R     = 0.10
CX0   = 0.30
CY0   = 0.50
UX    = 1.0
UY    = 0.0
T_END = 0.10
CFL   = 0.4
N_LIST = [32, 64, 128, 256]

SEP = "=" * 70


# ── Helper: build exact CLS profile ──────────────────────────────────────────
def psi_tanh(X: np.ndarray, Y: np.ndarray,
             cx: float, cy: float, R: float, eps: float) -> np.ndarray:
    """ψ = 1 / (1 + exp((r − R) / ε))  — tanh-smoothed circle."""
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    # clip exponent to avoid overflow in exp
    arg = np.clip((r - R) / eps, -500.0, 500.0)
    return 1.0 / (1.0 + np.exp(arg))


# ── Single-resolution run ─────────────────────────────────────────────────────
def run_one(N: int, scheme: str, dt_fixed: float | None = None) -> dict:
    """Advance ψ to T_END and return error metrics + sanity checks.

    Parameters
    ----------
    N        : grid points per side
    scheme   : 'dccd' | 'weno5'
    dt_fixed : use this dt (spatial-only test); None → CFL-limited
    """
    backend = Backend(use_gpu=False)
    gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    grid = Grid(gc, backend)

    h   = 1.0 / N
    eps = 1.5 * h

    x = grid.coords[0]   # shape (N+1,)
    y = grid.coords[1]
    X, Y = np.meshgrid(x, y, indexing='ij')

    # Initial condition
    psi0 = psi_tanh(X, Y, CX0, CY0, R, eps)

    # Constant velocity fields
    u_field = np.full_like(psi0, UX)
    v_field = np.full_like(psi0, UY)

    # Time step
    if dt_fixed is not None:
        dt = dt_fixed
    else:
        dt = CFL * h / (abs(UX) + abs(UY) + 1e-30)
    n_steps = max(1, int(np.ceil(T_END / dt)))
    dt_actual = T_END / n_steps

    # Build advector
    if scheme == 'dccd':
        ccd = CCDSolver(grid, backend, bc_type='periodic')
        advector = DissipativeCCDAdvection(backend, grid, ccd, bc='periodic')
    else:
        advector = LevelSetAdvection(backend, grid, bc='periodic')

    # ── Time march ───────────────────────────────────────────────────────────
    q = psi0.copy()
    mass0 = float(np.sum(q[:-1, :-1])) * h * h   # interior cells only

    for _ in range(n_steps):
        q = advector.advance(q, [u_field, v_field], dt_actual)

    # ── Exact solution ────────────────────────────────────────────────────────
    cx_ex = CX0 + UX * T_END
    cy_ex = CY0 + UY * T_END
    psi_ex = psi_tanh(X, Y, cx_ex, cy_ex, R, eps)

    # ── Error (interior nodes — exclude periodic-duplicate boundary) ─────────
    q_int  = np.asarray(q)[:-1, :-1]
    ex_int = psi_ex[:-1, :-1]
    err    = q_int - ex_int

    L2   = float(np.sqrt(np.mean(err ** 2)))
    Linf = float(np.max(np.abs(err)))

    # ── SC-3: y-symmetry (u_y = 0, IC symmetric in y about 0.5) ─────────────
    q_flip = np.flip(np.asarray(q), axis=1)
    sym_err = float(np.max(np.abs(np.asarray(q) - q_flip)))

    # ── SC-4: mass conservation ───────────────────────────────────────────────
    mass_T   = float(np.sum(np.asarray(q)[:-1, :-1])) * h * h
    mass_rel = abs(mass_T - mass0) / (abs(mass0) + 1e-30)

    return {
        'N': N, 'h': h, 'n_steps': n_steps, 'dt': dt_actual,
        'L2': L2, 'Linf': Linf,
        'sym_err': sym_err,
        'mass_rel': mass_rel,
    }


# ── Convergence slope ─────────────────────────────────────────────────────────
def slope(h_list: list, e_list: list) -> float:
    h = np.array(h_list, dtype=float)
    e = np.array(e_list, dtype=float)
    ok = e > 0
    if ok.sum() < 2:
        return float('nan')
    return float(np.polyfit(np.log(h[ok]), np.log(e[ok]), 1)[0])


# ── Run one experiment (CFL or fixed-dt) ─────────────────────────────────────
def run_experiment(label: str, dt_fixed: float | None) -> dict:
    print(f"\n{SEP}")
    print(f"Experiment: {label}")
    print(SEP)

    data = {'dccd': [], 'weno5': []}
    sc_pass = True

    for scheme in ('dccd', 'weno5'):
        name = 'DissipativeCCD' if scheme == 'dccd' else 'WENO5'
        print(f"\n  ── {name} ──")
        print(f"  {'N':>5}  {'h':>8}  {'nsteps':>7}  "
              f"{'L2':>10}  {'L∞':>10}  {'sym':>8}  {'mass_rel':>9}")

        for N in N_LIST:
            r = run_one(N, scheme, dt_fixed)
            data[scheme].append(r)

            sc3 = '✓' if r['sym_err'] < 1e-12 else '✗'
            sc4 = '✓' if r['mass_rel'] < 1e-4  else '✗'
            if r['sym_err'] >= 1e-12 or r['mass_rel'] >= 1e-4:
                sc_pass = False

            print(f"  {N:>5}  {r['h']:>8.4f}  {r['n_steps']:>7d}  "
                  f"{r['L2']:>10.3e}  {r['Linf']:>10.3e}  "
                  f"{r['sym_err']:>8.1e}{sc3}  {r['mass_rel']:>9.2e}{sc4}")

        h_list = [r['h']  for r in data[scheme]]
        L2_list = [r['L2'] for r in data[scheme]]
        Li_list = [r['Linf'] for r in data[scheme]]
        s_L2  = slope(h_list, L2_list)
        s_Li  = slope(h_list, Li_list)
        print(f"  → convergence slope:  L2 = {s_L2:.2f},  L∞ = {s_Li:.2f}")

    print(f"\n  EXP-02 SC-3 (symmetry) + SC-4 (mass): "
          f"{'ALL PASS ✓' if sc_pass else 'FAIL ✗'}")
    return data


# ── Plot ──────────────────────────────────────────────────────────────────────
def make_plot(data_cfl: dict, data_fixed: dict, save_path: str) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle(
        'CLS Uniform-Flow Advection — Exact-Solution Convergence\n'
        f'R={R}, center=({CX0},{CY0}), u=({UX},{UY}), T={T_END}',
        fontsize=11
    )

    configs = [
        (data_cfl,   'A: CFL-limited dt',    axes[0]),
        (data_fixed, 'B: Fixed dt = 1e-5',   axes[1]),
    ]

    for (data, title, row_axes) in configs:
        for col, norm in enumerate(('L2', 'Linf')):
            ax = row_axes[col]

            for scheme, color, label in [
                ('dccd',  'tab:blue',   'DCCD'),
                ('weno5', 'tab:orange', 'WENO5'),
            ]:
                hs   = [r['h']         for r in data[scheme]]
                errs = [r[norm]        for r in data[scheme]]
                ax.loglog(hs, errs, 'o-', color=color, label=label, linewidth=1.5)

            # Reference lines
            h_arr = np.array([r['h'] for r in data['dccd']], dtype=float)
            e0_d = data['dccd'][0][norm]
            e0_w = data['weno5'][0][norm]
            ax.loglog(h_arr, e0_d * (h_arr / h_arr[0]) ** 2,
                      '--', color='gray', alpha=0.6, label='O(h²)', linewidth=1)
            ax.loglog(h_arr, e0_w * (h_arr / h_arr[0]) ** 3,
                      ':',  color='olive', alpha=0.7, label='O(h³)', linewidth=1)
            ax.loglog(h_arr, e0_w * (h_arr / h_arr[0]) ** 5,
                      '-.',  color='black', alpha=0.5, label='O(h⁵)', linewidth=1)

            ax.set_xlabel('h = 1/N')
            ax.set_ylabel(f'{norm} error')
            ax.set_title(f'{title} — {norm}')
            ax.legend(fontsize=7)
            ax.grid(True, which='both', alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {save_path}")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(SEP)
    print("CLS Uniform-Flow Advection — Exact-Solution Convergence Study")
    print(f"  R={R}, center=({CX0},{CY0}), u=({UX},{UY}), T={T_END}")
    print(f"  ε = 1.5 h  (varies with N)")
    print(f"  Grids: {N_LIST}")
    print(SEP)

    # Experiment A: CFL-limited
    data_cfl = run_experiment('A — CFL-limited dt (dt = 0.4 h)', dt_fixed=None)

    # Experiment B: fixed tiny dt (spatial order isolation)
    data_fixed = run_experiment('B — Fixed dt = 1e-5 (spatial only)', dt_fixed=1e-5)

    # Final convergence summary
    print(f"\n{SEP}")
    print("CONVERGENCE SUMMARY")
    print(SEP)
    print(f"  {'Experiment':<30}  {'Scheme':<12}  {'L2 slope':>9}  {'L∞ slope':>9}")
    for exp_label, data in [('A: CFL-limited', data_cfl), ('B: Fixed dt=1e-5', data_fixed)]:
        for scheme in ('dccd', 'weno5'):
            name = 'DCCD' if scheme == 'dccd' else 'WENO5'
            hs  = [r['h']    for r in data[scheme]]
            L2s = [r['L2']   for r in data[scheme]]
            Lis = [r['Linf'] for r in data[scheme]]
            s2 = slope(hs, L2s)
            si = slope(hs, Lis)
            print(f"  {exp_label:<30}  {name:<12}  {s2:>9.2f}  {si:>9.2f}")

    # Plot
    os.makedirs('results', exist_ok=True)
    make_plot(data_cfl, data_fixed, 'results/cls_advection_convergence.png')
