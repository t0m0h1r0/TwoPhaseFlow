"""
LS vs CLS Conservation Experiment — Adaptive Non-Uniform Grid
=============================================================
1D uniform-flow advection on a dynamically adaptive non-uniform periodic grid.

Governing equations (computational coordinates ξ, stationary grid u_g=0)
--------------------------------------------------------------------------
  LS  (non-conservative): ∂φ/∂t + (u/J)·∂φ/∂ξ = 0
  CLS (conservative):     ∂ψ/∂t + (1/J)·∂(uψ)/∂ξ = 0
where J_i = dx/dξ is the grid Jacobian at node i.
For u=const both have the same differential operator; the difference
appears in reinitialization and grid-remapping conservation properties.

Grid
----
  N = 128 unique computational nodes ξ_i = i/N.
  Physical nodes x_i via algebraic mapping with small Jacobian J near x_c:
    J(ξ) ∝ 1/(1+(r−1)exp(−(ξ−x_c)²/2σ²)),  r=4, σ=0.06.
  The finest spacing h_min ≈ h_bg/r  (h_bg = 1/N).
  Mass quadrature: M = (1/N)·Σ q_i·J_i  (midpoint rule in ξ-space).

Dynamic grid refresh
--------------------
  Every K_refresh steps the grid is regenerated centred on the current
  analytical interface position x_c(t) = (x_c0 + u·t) mod 1.
  After regeneration:
    LS  : piecewise-linear interpolation of φ  (non-conservative)
    CLS : piecewise-linear interpolation of ψ, then rescale to preserve M

Reinitialization (applied every advection step)
------------------------------------------------
  LS  : Godunov pseudo-time on non-uniform grid (sign from CURRENT φ).
        4 steps, Δτ = 0.5·h_min.  Physical gradient: |∇φ| = |∂φ/∂ξ|/J.
  CLS : CCD compression + DCCD filter.  4 steps, Δτ = min(0.5h²/(2ε), 0.5h_min).

Spatial discretization (DCCD in ξ-space)
-----------------------------------------
  1. f_i = flux  (φ or uψ)
  2. f′_i = CCD.d1(f)   (6th-order in uniform ξ-space)
  3. F̃_i = f′_i + ε_d·(f′_{i+1}−2f′_i+f′_{i-1})   ε_d = 0.05
  4. RHS_i = −F̃_i/J_i

Time integration: TVD-RK3 (Shu–Osher), CFL = 0.4 based on h_min.
CLS stages clipped to [0, 1].

Metrics
-------
  LS  mass : M = (1/N)·Σ H̃_ε(φ_i)·J_i,  H̃_ε(φ)=0.5·(1−tanh(φ/ε))
  CLS mass : M = (1/N)·Σ ψ_i·J_i
  Relative mass error : (M(t)−M₀)/M₀
  L2 error at T=1 : sqrt(mean((q(T)−q_exact(x_final))²))

Output
------
  results/ls_cls_conservation/
    figures/
      01_mass_error.png        — |ΔM/M₀| vs step (N=128, K_refresh=10)
      02_profile.png           — profile at T=1 vs exact
      03_mass_vs_refresh.png   — peak |ΔM/M₀| vs K_refresh
    data/
      mass_history.csv
      final_metrics.csv
    latex/
      table_conservation.tex
"""
from __future__ import annotations

import csv
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from twophase.ccd.ccd_solver import CCDSolver

# ─── output directories ───────────────────────────────────────────────────────
_ROOT = os.path.join(os.path.dirname(__file__), "..")
_OUT  = os.path.join(_ROOT, "results", "ls_cls_conservation")
_FIG  = os.path.join(_OUT, "figures")
_DAT  = os.path.join(_OUT, "data")
_TEX  = os.path.join(_OUT, "latex")
for _d in (_FIG, _DAT, _TEX):
    os.makedirs(_d, exist_ok=True)

# ─── CCDSolver stub ───────────────────────────────────────────────────────────
class _Grid1D:
    ndim = 1
    uniform = True
    def __init__(self, n: int):
        self.N = (n,)
        self.L = (1.0,)

class _Backend:
    xp = np

def _make_ccd(n: int) -> CCDSolver:
    """Periodic CCDSolver for n unique nodes (arrays must be length n+1)."""
    return CCDSolver(_Grid1D(n), _Backend(), bc_type="periodic")

# ─── parameters ───────────────────────────────────────────────────────────────
N            = 128
U            = 1.0     # advection velocity
T            = 1.0     # final time (one period)
R            = 0.25    # half-width of liquid region: φ<0 on [0.25, 0.75]
CFL          = 0.4
EPS_COEFF    = 3.0     # ε = EPS_COEFF · h_min  (6+ nodes across ±ε)
DCCD_EPS_D   = 0.05    # filter strength ε_d
REFINE_R     = 2.0     # refinement ratio r
REFINE_SIGMA = 0.06    # half-width σ (computational units)
K_REFRESH_DEFAULT = 10
REINIT_EVERY      = 20  # LS reinit stride (CLS: no reinit — conservative form preserves profile)

_STYLE = {
    "ls":  ("LS (SDF)",  "#e06c75", "-",  1.8),
    "cls": ("CLS (ψ)",   "#61afef", "--", 1.8),
}

# ═══════════════════════════════════════════════════════════════════════════════
# Non-uniform grid
# ═══════════════════════════════════════════════════════════════════════════════

def generate_grid(N: int, x_c: float,
                  r: float = REFINE_R,
                  sigma: float = REFINE_SIGMA) -> tuple:
    """Algebraic periodic grid with r× refinement near x_c.

    J(ξ) = c/(1+(r−1)exp(−d²/2σ²)), d = periodic_dist(ξ_i, x_c).
    Normalised so (1/N)·ΣJ = 1.
    Returns: x (N,), J (N,)  with x[0]=0, x monotone on [0,1).
    """
    xi = np.arange(N, dtype=float) / N
    d  = xi - (x_c % 1.0)
    d -= np.round(d)                          # periodic distance
    J  = 1.0 / (1.0 + (r - 1.0) * np.exp(-d**2 / (2.0 * sigma**2)))
    J *= N / np.sum(J)                        # normalize: mean(J)=1, ∫J dξ=1
    # Physical coordinates by integration
    x    = np.empty(N)
    x[0] = 0.0
    for i in range(1, N):
        x[i] = x[i - 1] + J[i - 1] / N
    return x, J


# ═══════════════════════════════════════════════════════════════════════════════
# Exact solution (in physical space)
# ═══════════════════════════════════════════════════════════════════════════════

def phi_exact(x: np.ndarray, t: float = 0.0) -> np.ndarray:
    """SDF: φ < 0 inside liquid [0.25+t, 0.75+t] (periodic)."""
    xc = (0.5 + t) % 1.0             # droplet centre
    d  = x - xc
    d -= np.round(d)
    return np.abs(d) - R


def psi_exact(x: np.ndarray, eps: float, t: float = 0.0) -> np.ndarray:
    """CLS smooth Heaviside: ψ ≈ 1 (liquid), ψ ≈ 0 (gas)."""
    return 0.5 * (1.0 - np.tanh(phi_exact(x, t) / eps))


# ═══════════════════════════════════════════════════════════════════════════════
# DCCD operator in computational ξ-space
# ═══════════════════════════════════════════════════════════════════════════════

def _ccd_d1_periodic(q: np.ndarray, ccd: CCDSolver, N: int) -> np.ndarray:
    """CCD first derivative ∂q/∂ξ in uniform ξ-space (N nodes, periodic)."""
    q_ext    = np.empty(N + 1)
    q_ext[:N] = q
    q_ext[N]  = q[0]
    d1, _    = ccd.differentiate(q_ext, axis=0)
    return np.asarray(d1)[:N]


def dccd_flux_div(flux: np.ndarray, ccd: CCDSolver, N: int) -> np.ndarray:
    """DCCD divergence of flux in ξ-space: (∂flux/∂ξ) with ε_d filter."""
    f_prime = _ccd_d1_periodic(flux, ccd, N)
    f_tilde = (f_prime
               + DCCD_EPS_D * (np.roll(f_prime, -1)
                                - 2.0 * f_prime
                                + np.roll(f_prime,  1)))
    return f_tilde


def rhs_ls(phi: np.ndarray, J: np.ndarray,
           ccd: CCDSolver, N: int) -> np.ndarray:
    """RHS for LS non-conservative advection: −(u/J)·F̃[∂φ/∂ξ]."""
    return -U * dccd_flux_div(phi, ccd, N) / J


def rhs_cls(psi: np.ndarray, J: np.ndarray,
            ccd: CCDSolver, N: int) -> np.ndarray:
    """RHS for CLS conservative advection: −(1/J)·F̃[∂(uψ)/∂ξ]."""
    return -dccd_flux_div(U * psi, ccd, N) / J


# ═══════════════════════════════════════════════════════════════════════════════
# TVD-RK3
# ═══════════════════════════════════════════════════════════════════════════════

def tvd_rk3_ls(phi: np.ndarray, dt: float,
               J: np.ndarray, ccd: CCDSolver, N: int) -> np.ndarray:
    def L(q): return rhs_ls(q, J, ccd, N)
    q1 = phi + dt * L(phi)
    q2 = 0.75 * phi + 0.25 * (q1 + dt * L(q1))
    return (1.0 / 3.0) * phi + (2.0 / 3.0) * (q2 + dt * L(q2))


def tvd_rk3_cls(psi: np.ndarray, dt: float,
                J: np.ndarray, ccd: CCDSolver, N: int) -> np.ndarray:
    def L(q): return rhs_cls(q, J, ccd, N)
    q1 = np.clip(psi + dt * L(psi), 0.0, 1.0)
    q2 = np.clip(0.75 * psi + 0.25 * (q1 + dt * L(q1)), 0.0, 1.0)
    return np.clip((1.0 / 3.0) * psi + (2.0 / 3.0) * (q2 + dt * L(q2)),
                   0.0, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
# Reinitialization
# ═══════════════════════════════════════════════════════════════════════════════

def ls_reinit(phi: np.ndarray, J: np.ndarray, N: int,
              n_steps: int = 4) -> np.ndarray:
    """Godunov LS reinitialization on non-uniform grid.

    Sign is computed from the CURRENT phi (not the initial IC) so that the
    zero level set is correctly tracked after the interface has moved.
    Physical gradient: |∇φ| = |∂φ/∂ξ|/J.
    Gradients clipped to [−G_max, G_max] (G_max=5) to prevent overflow.
    """
    h_xi  = 1.0 / N
    h_min = float(np.min(J)) / N
    dtau  = 0.5 * h_min
    G_max = 5.0           # physical gradient bound; |∇SDF|=1 nominally
    q     = phi.copy()
    phi0  = phi.copy()    # save sign reference for this reinit call

    for _ in range(n_steps):
        a = np.clip((q - np.roll(q, 1)) / (h_xi * J), -G_max, G_max)
        b = np.clip((np.roll(q, -1) - q) / (h_xi * J), -G_max, G_max)
        G_pos = np.sqrt(np.maximum(np.maximum(a, 0.0)**2,
                                   np.minimum(b, 0.0)**2))
        G_neg = np.sqrt(np.maximum(np.minimum(a, 0.0)**2,
                                   np.maximum(b, 0.0)**2))
        # Smooth sign based on phi0 (entry state, prevents zero level set drift)
        delta = h_min
        S     = phi0 / np.sqrt(phi0**2 + delta**2)
        G     = np.where(S > 0.0, G_pos, G_neg)
        q     = q - dtau * S * (G - 1.0)
    return q


def cls_reinit(psi: np.ndarray, J: np.ndarray,
               ccd: CCDSolver, N: int, eps: float,
               n_steps: int = 4) -> np.ndarray:
    """CLS compression reinitialization with DCCD filter.

    ∂ψ/∂τ + (1/J)·∂[ψ(1−ψ)n̂]/∂ξ = 0,  n̂ = sign(∂ψ/∂ξ).
    """
    h_min  = float(np.min(J)) / N
    dtau   = min(0.5 * h_min**2 / (2.0 * eps), 0.5 * h_min)
    q      = psi.copy()
    for _ in range(n_steps):
        dpsi  = _ccd_d1_periodic(q, ccd, N)
        n_hat = np.sign(dpsi)                 # J>0 → physical sign = ξ sign
        g     = q * (1.0 - q) * n_hat
        divg  = dccd_flux_div(g, ccd, N)
        q     = np.clip(q - dtau * divg / J, 0.0, 1.0)
    return q


# ═══════════════════════════════════════════════════════════════════════════════
# Mass diagnostics
# ═══════════════════════════════════════════════════════════════════════════════

def mass_ls(phi: np.ndarray, eps: float, J: np.ndarray, N: int) -> float:
    H = 0.5 * (1.0 - np.tanh(phi / eps))
    return float(np.sum(H * J) / N)


def mass_cls(psi: np.ndarray, J: np.ndarray, N: int) -> float:
    return float(np.sum(psi * J) / N)


# ═══════════════════════════════════════════════════════════════════════════════
# Grid remapping (periodic 1D)
# ═══════════════════════════════════════════════════════════════════════════════

def _interp_periodic(q_old: np.ndarray, x_old: np.ndarray,
                     x_new: np.ndarray) -> np.ndarray:
    """Piecewise-linear interpolation onto x_new from periodic x_old."""
    x3 = np.concatenate([x_old - 1.0, x_old, x_old + 1.0])
    q3 = np.tile(q_old, 3)
    return np.interp(x_new % 1.0, x3, q3)


def remap_ls(phi: np.ndarray, x_old: np.ndarray,
             x_new: np.ndarray) -> np.ndarray:
    """Non-conservative LS remap: piecewise-linear interpolation."""
    return _interp_periodic(phi, x_old, x_new)


def remap_cls(psi: np.ndarray, J_old: np.ndarray, x_old: np.ndarray,
              x_new: np.ndarray, J_new: np.ndarray, N: int) -> np.ndarray:
    """Conservative CLS remap: interpolate then rescale to preserve mass."""
    M_old   = mass_cls(psi, J_old, N)
    psi_new = np.clip(_interp_periodic(psi, x_old, x_new), 0.0, 1.0)
    M_new   = mass_cls(psi_new, J_new, N)
    if M_new > 1e-14:
        psi_new = np.clip(psi_new * (M_old / M_new), 0.0, 1.0)
    return psi_new


# ═══════════════════════════════════════════════════════════════════════════════
# Simulation
# ═══════════════════════════════════════════════════════════════════════════════

def simulate(method: str, K_refresh: int = K_REFRESH_DEFAULT) -> dict:
    """Advect for T=1 period; refresh grid every K_refresh steps.

    Returns dict: mass_history, L2_err, q_final, x_final.
    """
    x_c0 = 0.5                            # initial grid clustering centre
    x, J = generate_grid(N, x_c0)
    h_min = float(np.min(J)) / N
    eps   = EPS_COEFF * h_min
    ccd   = _make_ccd(N)

    if method == "ls":
        q  = phi_exact(x, t=0.0)
        M0 = mass_ls(q, eps, J, N)
    else:
        q  = psi_exact(x, eps, t=0.0)
        M0 = mass_cls(q, J, N)

    dt      = CFL * h_min / abs(U)
    n_steps = max(1, int(np.ceil(T / dt)))
    dt      = T / n_steps
    t_now   = 0.0

    mass_history: list = []

    for step in range(n_steps):
        # ── advection ──────────────────────────────────────────────────
        if method == "ls":
            q = tvd_rk3_ls(q, dt, J, ccd, N)
            if (step + 1) % REINIT_EVERY == 0:
                q = ls_reinit(q, J, N)
        else:
            q = tvd_rk3_cls(q, dt, J, ccd, N)
            # CLS: no reinitialization — conservative form preserves tanh profile

        t_now += dt

        # ── grid refresh ───────────────────────────────────────────────
        if (step + 1) % K_refresh == 0:
            x_c_new = (x_c0 + t_now) % 1.0
            x_new, J_new = generate_grid(N, x_c_new)
            if method == "ls":
                q = remap_ls(q, x, x_new)
            else:
                q = remap_cls(q, J, x, x_new, J_new, N)
            x, J = x_new, J_new
            h_min = float(np.min(J)) / N
            eps   = EPS_COEFF * h_min

        # ── record mass ────────────────────────────────────────────────
        M     = mass_ls(q, eps, J, N) if method == "ls" else mass_cls(q, J, N)
        rel_e = (M - M0) / M0 if abs(M0) > 1e-30 else 0.0
        mass_history.append((step, rel_e))

    # L2 error vs exact on final physical grid
    if method == "ls":
        q_ref = phi_exact(x, t=T)
    else:
        q_ref = psi_exact(x, eps, t=T)
    L2_err = float(np.sqrt(np.mean((q - q_ref)**2)))

    return {"mass_history": mass_history, "L2_err": L2_err,
            "q_final": q, "x_final": x}


def run_all(K_values: list) -> dict:
    """Results[K][method] for all K_refresh values."""
    results: dict = {}
    for K in K_values:
        results[K] = {}
        for method in ("ls", "cls"):
            label = _STYLE[method][0]
            res   = simulate(method, K)
            results[K][method] = res
            final = res["mass_history"][-1][1]
            print(f"  K={K:4d}  [{label:10s}]  L2={res['L2_err']:.3e}"
                  f"  mass_err_final={final:.3e}")
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Plotting
# ═══════════════════════════════════════════════════════════════════════════════

def _style(ax, xlabel="", ylabel="", title=""):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.grid(True, alpha=0.25, lw=0.6)


def plot_mass_error(results: dict, K_main: int):
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for method, (label, color, ls, lw) in _STYLE.items():
        hist  = results[K_main][method]["mass_history"]
        steps = [s for s, _ in hist]
        errs  = [abs(e) + 1e-18 for _, e in hist]
        ax.semilogy(steps, errs, color=color, ls=ls, lw=lw, label=label)
    # Mark refresh events
    n_st = len(results[K_main]["ls"]["mass_history"])
    for kr in range(K_main - 1, n_st, K_main):
        ax.axvline(kr, color="gray", lw=0.5, ls=":", alpha=0.6)
    _style(ax, "Advection step", r"$|\Delta M / M_0|$",
           f"Mass conservation  |  N={N}, r={REFINE_R:.0f}, "
           f"K_refresh={K_main}, CFL={CFL}")
    ax.legend(fontsize=10, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "01_mass_error.png")
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


def plot_profile(results: dict, K_main: int):
    """Compare both methods as ψ-scale (H̃(φ) for LS) on a single axes."""
    fig, ax = plt.subplots(figsize=(8, 4.5))
    h_min_approx = 1.0 / (N * REFINE_R)
    eps_plot     = EPS_COEFF * h_min_approx

    # Exact reference (use CLS grid — same as LS grid for K_main)
    x_ref = results[K_main]["cls"]["x_final"]
    psi_ref = psi_exact(x_ref, eps_plot, t=T)
    ax.plot(x_ref, psi_ref, "k--", lw=2.0, label="Exact $\\tilde{H}_\\varepsilon$",
            zorder=10)

    for method, (label, color, ls_s, lw) in _STYLE.items():
        res   = results[K_main][method]
        x_fin = res["x_final"]
        q_fin = res["q_final"]
        if method == "ls":
            # Convert SDF → Heaviside for direct comparison
            psi_fin = 0.5 * (1.0 - np.tanh(q_fin / eps_plot))
        else:
            psi_fin = q_fin
        ax.plot(x_fin, psi_fin, color=color, ls="-", lw=lw, label=label)

    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.05, 1.15)
    _style(ax, "x (physical)", r"$\tilde{H}_\varepsilon(\phi)$ / $\psi$",
           f"Profile at $T=1$  |  N={N}, r={REFINE_R:.0f}, K={K_main}")
    ax.legend(fontsize=10, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "02_profile.png")
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


def plot_refresh_study(results: dict, K_values: list):
    fig, ax = plt.subplots(figsize=(7, 4.5))
    for method, (label, color, ls_s, lw) in _STYLE.items():
        # Use final |ΔM/M₀| at T=1 — matches the table and is the physically
        # meaningful measure: net mass error accumulated over the whole run.
        finals = [abs(results[K][method]["mass_history"][-1][1])
                  for K in K_values]
        ax.semilogy(K_values, finals, color=color, ls=ls_s, lw=lw,
                    marker="o", ms=5, label=label)
    _style(ax, "Refresh period K (steps)", r"Final $|\Delta M/M_0|$ at $T=1$",
           f"Mass error vs grid-refresh period  |  N={N}, r={REFINE_R:.0f}")
    ax.legend(fontsize=10, framealpha=0.85)
    plt.tight_layout()
    out = os.path.join(_FIG, "03_mass_vs_refresh.png")
    plt.savefig(out, dpi=180, bbox_inches="tight")
    plt.close()
    print(f"  [fig] {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# CSV + LaTeX
# ═══════════════════════════════════════════════════════════════════════════════

def save_csv(results: dict, K_main: int, K_values: list):
    # mass history
    out = os.path.join(_DAT, "mass_history.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "step", "rel_mass_err"])
        for method in ("ls", "cls"):
            for step, err in results[K_main][method]["mass_history"]:
                w.writerow([method, step, f"{err:.8e}"])
    print(f"  [csv] {out}")
    # final metrics
    out = os.path.join(_DAT, "final_metrics.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["K_refresh", "method", "L2_err", "mass_err_final"])
        for K in K_values:
            for method in ("ls", "cls"):
                res  = results[K][method]
                mf   = res["mass_history"][-1][1]
                w.writerow([K, method,
                             f"{res['L2_err']:.6e}", f"{mf:.6e}"])
    print(f"  [csv] {out}")


def save_latex(results: dict, K_values: list):
    heads = " & ".join(f"$K={K}$" for K in K_values)
    lines = [
        r"\begin{table}[htbp]",
        r"  \centering",
        r"  \caption{Final relative mass error $|\Delta M/M_0|$ after $T=1$ advection"
        rf"  on adaptive non-uniform grid ($N={N}$, $r={REFINE_R:.0f}$,"
        rf"  CFL$={CFL}$). CLS uses mass-conservative remapping; LS uses"
        r"  piecewise-linear interpolation.}",
        r"  \label{tab:ls_cls_mass_err}",
        rf"  \begin{{tabular}}{{l{'r'*len(K_values)}}}",
        r"    \toprule",
        rf"    Method & {heads} \\",
        r"    \midrule",
    ]
    for method in ("ls", "cls"):
        label = _STYLE[method][0]
        vals  = [f"{abs(results[K][method]['mass_history'][-1][1]):.2e}"
                 for K in K_values]
        lines.append(f"    {label} & " + " & ".join(vals) + r" \\")
    lines += [r"    \bottomrule", r"  \end{tabular}", r"\end{table}"]
    out = os.path.join(_TEX, "table_conservation.tex")
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  [tex] {out}")


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    K_values = [5, 10, 20, 50]
    K_main   = 10

    print(f"[LS/CLS] N={N}, r={REFINE_R}, σ={REFINE_SIGMA}, CFL={CFL}, T={T}")
    print(f"  K_values = {K_values}")

    print("\n[LS/CLS] Running ...")
    results = run_all(K_values)

    print("\n[LS/CLS] Figures ...")
    plot_mass_error(results, K_main)
    plot_profile(results, K_main)
    plot_refresh_study(results, K_values)

    print("\n[LS/CLS] Data ...")
    save_csv(results, K_main, K_values)

    print("\n[LS/CLS] LaTeX ...")
    save_latex(results, K_values)

    print("\n[LS/CLS] Done.")
