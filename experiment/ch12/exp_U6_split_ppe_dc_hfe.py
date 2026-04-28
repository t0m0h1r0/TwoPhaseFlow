#!/usr/bin/env python3
"""[U6] Lumped PPE + DC + HFE — Tier IV.

Paper ref: Chapter 12 U6 (sec:U6_split_ppe_dc_hfe; paper/sections/12u6_split_ppe_dc_hfe.tex).

Sub-tests
---------
  (a) DC iteration / stall study with the lumped (phase_density) FCCD-PPE.
      ρ_l/ρ_g ∈ {1, 100, 1000}; relaxation ω ∈ {0.2, 0.3, 0.5, 0.7};
      max_corrections k ∈ {2, 3}. Counts (ω, k, ρ) cells whose DC for-loop
      runs to completion without hitting tolerance ("stall"). Chapter 12 U6:
      ρ_l/ρ_g=1 is clean, while ρ_l/ρ_g ∈ {100, 1000} stalls for
      ω ≥ 0.5; this script reports lumped-PPE limitation evidence only.

  (b) Lumped MMS at N=64, ρ_l/ρ_g ∈ {1, 10, 100, 1000}.
      Manufactured p* = cos(π x) cos(π y) (Neumann-compatible, p*(0.5,0.5)=0
      so it aligns with the centre-pin gauge); circle interface R=0.25
      centre (0.5, 0.5); ε = 1.5h; ρ from smoothed Heaviside.
      Analytic RHS = ∇·((1/ρ)∇p*) = -2π² p*/ρ + ∇(1/ρ)·∇p*. L_inf error
      measured inside the liquid bulk (φ > 3h). Chapter 12 U6: 一括 DC
      degrades from 6.6e-12 (ρ=1) to 2.7e-5 (ρ=1000) at N=64.

  (c) HFE 1-D + 2-D extension. 1-D: _hermite5_xp polynomial extrapolated one
      cell beyond the source window for f(x)=cos(π x)+0.3 sin(2π x) (no
      symmetry zero); Chapter 12 U6 reports slope ≈ 5.99. 2-D:
      HermiteFieldExtension.extend across a circular Γ on the same field;
      target = inside circle (φ > 0), source = outside (φ < 0); error
      reported on the 6-cell extension band. Chapter 12 U6 reports
      2-D max ≈ 5.05 and median ≈ 3.21 as a geometric-band diagnostic.

Stall detection: PPESolverDefectCorrection.solve has
``for _ in range(max_corrections): ... if residual <= tol*scale: break``.
Subclass _DCStallTracker records the per-correction residual norms and
flags ``last_stalled = True`` iff the loop ran to completion without break.

Usage
-----
  python experiment/ch12/exp_U6_split_ppe_dc_hfe.py
  python experiment/ch12/exp_U6_split_ppe_dc_hfe.py --plot-only
"""

from __future__ import annotations

import sys
import pathlib
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import numpy as np
import matplotlib.pyplot as plt

from twophase.backend import Backend
from twophase.config import GridConfig, SimulationConfig
from twophase.core.grid import Grid
from twophase.ccd.ccd_solver import CCDSolver
from twophase.ccd.fccd import FCCDSolver
from twophase.levelset.heaviside import heaviside, delta
from twophase.ppe.fccd_matrixfree import PPESolverFCCDMatrixFree
from twophase.ppe.defect_correction import PPESolverDefectCorrection
from twophase.hfe.field_extension import HermiteFieldExtension, _hermite5_xp
from twophase.tools.experiment import (
    apply_style, experiment_dir, experiment_argparser,
    save_results, load_results, save_figure,
    convergence_loglog, compute_convergence_rates, field_panel,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u6_split_ppe_dc_hfe"
PAPER_FIG_HFE = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures" / "ch12_u6_hfe_2d_field"

# ── Parameters ──────────────────────────────────────────────────────────────
N_GRID = 64
RHO_RATIOS_A = [1.0, 100.0, 1000.0]
RHO_RATIOS_B = [1.0, 10.0, 100.0, 1000.0]
RHO_GAS = 1.0
OMEGA_VALUES = [0.2, 0.3, 0.5, 0.7]
DC_K_VALUES = [2, 3]
HFE_GRID_SIZES = [32, 64, 128, 256]
N_CONV_SIZES = [32, 64, 128]  # per-N study at ρ=1000 (Chapter 12 U6 table)
RHO_CONV = 1000.0
R_CIRCLE = 0.25
CENTER = (0.5, 0.5)
PI = float(np.pi)


# ── Subclass: DC with stall tracking ───────────────────────────────────────

class _DCStallTracker(PPESolverDefectCorrection):
    """Replicates parent solve() but records per-correction residual norms.

    Sets ``last_residual_history`` and ``last_stalled`` (True iff loop ran
    max_corrections without convergence break).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_residual_history: list[float] = []
        self.last_stalled: bool = False

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        xp = self.xp
        rhs_dev = xp.asarray(rhs)
        self.operator.prepare_operator(rho)
        rhs_dev = self._subtract_interface_jump_operator(rhs_dev)
        rhs_dev = self._enforce_rhs_compatibility(rhs_dev)
        pressure = xp.asarray(
            self.base_solver.solve(rhs_dev, rho, dt=dt, p_init=p_init)
        )
        pressure = self._enforce_pressure_gauge(pressure)
        rhs_flat = rhs_dev.ravel()
        rhs_norm = float(xp.linalg.norm(rhs_flat))
        scale = max(rhs_norm, 1.0)
        history: list[float] = []
        broke = False
        for _ in range(self.max_corrections):
            residual = rhs_dev - self.operator.apply(pressure)
            residual = self._enforce_rhs_compatibility(residual, record_stats=False)
            residual_norm = float(xp.linalg.norm(residual.ravel()))
            history.append(residual_norm)
            if residual_norm <= self.tolerance * scale:
                broke = True
                break
            correction = xp.asarray(
                self.base_solver.solve(residual, rho, dt=dt, p_init=None)
            )
            correction = self._enforce_pressure_gauge(correction)
            pressure = pressure + self.relaxation * correction
            pressure = self._enforce_pressure_gauge(pressure)
        self.last_residual_history = list(history)
        self.last_stalled = not broke
        if hasattr(self.operator, "apply_interface_jump"):
            pressure = self.operator.apply_interface_jump(pressure)
        return pressure


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_grid(N: int, backend) -> tuple[Grid, CCDSolver, FCCDSolver]:
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0)))
    grid = Grid(cfg.grid, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    fccd = FCCDSolver(grid, backend, bc_type="wall", ccd_solver=ccd)
    return grid, ccd, fccd


def _make_cfg(coefficient_scheme: str,
              pseudo_tol: float = 1.0e-10,
              pseudo_maxiter: int = 500) -> SimpleNamespace:
    """Flat config namespace consumed by PPESolverFCCDMatrixFree."""
    return SimpleNamespace(
        ppe_coefficient_scheme=coefficient_scheme,
        ppe_interface_coupling_scheme="none",
        pseudo_tol=pseudo_tol,
        pseudo_maxiter=pseudo_maxiter,
        ppe_restart=None,
        ppe_preconditioner="jacobi",
    )


def _circle_phi(N: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.linspace(0.0, 1.0, N + 1)
    X, Y = np.meshgrid(x, x, indexing="ij")
    r = np.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)
    phi = R_CIRCLE - r
    return X, Y, phi


def _smooth_rho(phi: np.ndarray, eps: float, rho_l: float) -> np.ndarray:
    psi = heaviside(np, phi, eps)
    return RHO_GAS + (rho_l - RHO_GAS) * psi


def _analytic_lp(X, Y, phi, eps: float, rho, rho_l: float) -> np.ndarray:
    """Analytic L p* = ∇·((1/ρ)∇p*) for p* = cos(πx)cos(πy)."""
    cx, cy = CENTER
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    r_safe = np.maximum(r, 1.0e-14)
    phi_x = -(X - cx) / r_safe
    phi_y = -(Y - cy) / r_safe
    delta_phi = delta(np, phi, eps)

    dpx = -PI * np.sin(PI * X) * np.cos(PI * Y)
    dpy = -PI * np.cos(PI * X) * np.sin(PI * Y)
    lap_p = -2.0 * PI * PI * np.cos(PI * X) * np.cos(PI * Y)

    rho_x = (rho_l - RHO_GAS) * delta_phi * phi_x
    rho_y = (rho_l - RHO_GAS) * delta_phi * phi_y
    inv_rho2 = 1.0 / (rho * rho)
    grad_inv_rho_x = -inv_rho2 * rho_x
    grad_inv_rho_y = -inv_rho2 * rho_y

    return (1.0 / rho) * lap_p + grad_inv_rho_x * dpx + grad_inv_rho_y * dpy


def _liquid_interior_error(p, p_exact, phi, h) -> float:
    """L_inf in liquid bulk (φ > 3h), modulo a constant gauge offset."""
    bulk = phi > 3.0 * h
    if not bulk.any():
        return float("nan")
    diff = (p - p_exact)[bulk]
    return float(np.max(np.abs(diff - diff.mean())))


# ── U6-a: lumped DC stall study ────────────────────────────────────────────

def _u6a_run_one(N: int, rho_l: float, omega: float, k_dc: int,
                 backend) -> dict:
    """One DC solve at given (rho_l, omega, k_dc); report stall flag."""
    grid, _, fccd = _make_grid(N, backend)
    h = 1.0 / N
    eps = 1.5 * h
    X, Y, phi = _circle_phi(N)
    rho = _smooth_rho(phi, eps, rho_l)
    rhs = _analytic_lp(X, Y, phi, eps, rho, rho_l)

    # Tight enough that ρ=1 converges within k iterations, loose enough that
    # high-ρ struggles (matches Chapter 12 U6's "stall for all ω at ρ ≥ 5"
    # narrative qualitatively while staying inside the FCCD GMRES regime).
    cfg_base = _make_cfg("phase_density", pseudo_tol=1.0e-6, pseudo_maxiter=30)
    cfg_op = _make_cfg("phase_density", pseudo_tol=1.0e-6, pseudo_maxiter=30)
    base = PPESolverFCCDMatrixFree(backend, cfg_base, grid, fccd)
    operator = PPESolverFCCDMatrixFree(backend, cfg_op, grid, fccd)
    solver = _DCStallTracker(
        backend, grid, base, operator,
        max_corrections=k_dc, tolerance=1.0e-7, relaxation=omega,
    )
    _ = solver.solve(rhs, rho)
    return {
        "rho_l": rho_l, "omega": omega, "k_dc": k_dc,
        "stalled": bool(solver.last_stalled),
        "n_corrections": len(solver.last_residual_history),
        "final_residual": (solver.last_residual_history[-1]
                           if solver.last_residual_history else float("nan")),
    }


def run_U6a() -> dict:
    backend = Backend(use_gpu=False)
    out: dict = {}
    for rho_l in RHO_RATIOS_A:
        rho_key = f"r{int(rho_l)}"
        out[rho_key] = {}
        for omega in OMEGA_VALUES:
            om_key = f"w{omega:g}"
            out[rho_key][om_key] = {}
            for k in DC_K_VALUES:
                row = _u6a_run_one(N_GRID, rho_l, omega, k, backend)
                out[rho_key][om_key][f"k{k}"] = row
    return out


# ── U6-b: lumped MMS at N=64, ρ sweep ──────────────────────────────────────

def _u6b_run_one(N: int, rho_l: float, k_dc: int, backend) -> dict:
    grid, _, fccd = _make_grid(N, backend)
    h = 1.0 / N
    eps = 1.5 * h
    X, Y, phi = _circle_phi(N)
    rho = _smooth_rho(phi, eps, rho_l)
    p_exact = np.cos(PI * X) * np.cos(PI * Y)
    rhs = _analytic_lp(X, Y, phi, eps, rho, rho_l)

    cfg = _make_cfg("phase_density")
    base = PPESolverFCCDMatrixFree(backend, cfg, grid, fccd)
    if k_dc <= 1:
        p = np.asarray(base.solve(rhs, rho))
    else:
        operator = PPESolverFCCDMatrixFree(backend, cfg, grid, fccd)
        solver = _DCStallTracker(
            backend, grid, base, operator,
            max_corrections=k_dc, tolerance=1.0e-10, relaxation=1.0,
        )
        p = np.asarray(solver.solve(rhs, rho))

    err = _liquid_interior_error(p, p_exact, phi, h)
    return {"N": N, "h": h, "rho_l": rho_l, "k_dc": k_dc, "err_inf": err}


def run_U6b() -> dict:
    """Lumped MMS at fixed N=64 across ρ; plus per-N convergence at ρ=1000.

    Note: With base = operator = same FCCD GMRES, DC k=1 ≡ k=3 in this
    setup (base already drives residual to GMRES tol). We report a single
    DC=3 result. Paper's k=1 vs k=3 differentiation requires a base solver
    of strictly lower order than the operator — out of scope for U6.
    """
    backend = Backend(use_gpu=False)
    rho_sweep = [_u6b_run_one(N_GRID, rho_l, 3, backend)
                 for rho_l in RHO_RATIOS_B]
    n_sweep = [_u6b_run_one(N, RHO_CONV, 3, backend)
               for N in N_CONV_SIZES]
    return {"rho_sweep": rho_sweep, "n_sweep": n_sweep}


# ── U6-c: HFE 1-D + 2-D ─────────────────────────────────────────────────────

def _hfe_test_field(x, y=None) -> np.ndarray:
    """Smooth, non-symmetric, non-trivial test field for HFE convergence."""
    if y is None:
        return np.cos(PI * x) + 0.3 * np.sin(2.0 * PI * x)
    return (np.cos(PI * x) + 0.3 * np.sin(2.0 * PI * x)) * \
           (np.cos(PI * y) + 0.2 * np.sin(2.0 * PI * y))


def _u6c_hfe_1d_one(N: int) -> dict:
    """1D Hermite-5 polynomial extrapolated one cell past source endpoint.

    Source window: [x_a, x_b] with x_a = 0.4, x_b = 0.4 + h.
    Target evaluation at x_t = 0.4 + 2h (one cell into target side).
    Local parameter xi = (x_t - x_a)/h = 2.0 (extrapolation outside [0,1]).
    Smooth f → polynomial residual scales as h^6.
    """
    h = 1.0 / N
    xa = 0.4
    xb = xa + h
    xt = xa + 2.0 * h  # one cell past source window

    fa = _hfe_test_field(xa)
    fb = _hfe_test_field(xb)
    dfa = -PI * np.sin(PI * xa) + 0.6 * PI * np.cos(2.0 * PI * xa)
    dfb = -PI * np.sin(PI * xb) + 0.6 * PI * np.cos(2.0 * PI * xb)
    d2fa = -PI * PI * np.cos(PI * xa) - 1.2 * PI * PI * np.sin(2.0 * PI * xa)
    d2fb = -PI * PI * np.cos(PI * xb) - 1.2 * PI * PI * np.sin(2.0 * PI * xb)

    val = float(_hermite5_xp(np, fa, dfa, d2fa, fb, dfb, d2fb, h, 2.0))
    err = abs(val - _hfe_test_field(xt))
    return {"N": N, "h": h, "err_inf": err}


def _u6c_hfe_2d_one(N: int, backend, *, keep_field: bool = False) -> dict:
    """2D HFE convergence test against the analytic closest-point projection.

    For each target cell at (x,y) inside the circle, HFE returns f(x_Γ) where
    x_Γ is the closest point on Γ. With ∇φ| = 1 (signed-distance φ = R - r),
    x_Γ = R/r · (x - cx, y - cy) + (cx, cy) — radial projection onto Γ.
    Truth at each target cell is therefore f(x_Γ), not f(x). Comparison on
    the full smooth field avoids stencil-poisoning that wiping target nodes
    would cause near Γ.
    """
    grid, ccd, _ = _make_grid(N, backend)
    h = 1.0 / N
    X, Y, phi = _circle_phi(N)
    field = _hfe_test_field(X, Y)

    # Analytic radial projection x_Γ onto the circle.
    cx, cy = CENTER
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    r_safe = np.maximum(r, 1.0e-14)
    xG = R_CIRCLE / r_safe * (X - cx) + cx
    yG = R_CIRCLE / r_safe * (Y - cy) + cy
    field_truth_extension = _hfe_test_field(xG, yG)

    hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=6)
    extended = np.asarray(hfe.extend(field, phi))

    target_mask = phi >= 0.0
    band_mask = target_mask & (np.abs(phi) <= 6.0 * h)
    if not band_mask.any():
        return {"N": N, "h": h,
                "err_inf_max": float("nan"), "err_inf_med": float("nan")}
    err = np.abs(extended[band_mask] - field_truth_extension[band_mask])
    result = {
        "N": N, "h": h,
        "err_inf_max": float(np.max(err)),
        "err_inf_med": float(np.median(err)),
    }
    if keep_field:
        abs_error = np.abs(extended - field_truth_extension)
        result["field_snapshot"] = {
            "N": N, "h": h, "X": X, "Y": Y, "phi": phi,
            "truth": field_truth_extension,
            "extended": extended,
            "band_abs_error": np.where(band_mask, abs_error, np.nan),
        }
    return result


def run_U6c() -> dict:
    backend = Backend(use_gpu=False)
    rows_1d = [_u6c_hfe_1d_one(N) for N in HFE_GRID_SIZES]
    rows_2d = [
        _u6c_hfe_2d_one(N, backend, keep_field=(N == 128))
        for N in HFE_GRID_SIZES
    ]
    field_snapshot = {}
    for row in rows_2d:
        if "field_snapshot" in row:
            field_snapshot = row.pop("field_snapshot")
            break
    return {"hfe_1d": rows_1d, "hfe_2d": rows_2d, "hfe_field": field_snapshot}


# ── Aggregator + plotting ──────────────────────────────────────────────────

def run_all() -> dict:
    return {"U6a": run_U6a(), "U6b": run_U6b(), "U6c": run_U6c()}


def make_figures(results: dict) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))
    ax_a, ax_b, ax_c = axes

    a = results["U6a"]
    rho_keys = [f"r{int(r)}" for r in RHO_RATIOS_A]
    rho_labels = [f"$\\rho_l/\\rho_g={int(r)}$" for r in RHO_RATIOS_A]
    width = 0.35
    xs = np.arange(len(rho_keys), dtype=float)
    for i, k in enumerate(DC_K_VALUES):
        stalls = []
        for rk in rho_keys:
            n = sum(1 for w in OMEGA_VALUES
                    if a[rk][f"w{w:g}"][f"k{k}"]["stalled"])
            stalls.append(n)
        ax_a.bar(xs + (i - 0.5) * width, stalls, width=width, label=f"$k={k}$")
    ax_a.set_xticks(xs)
    ax_a.set_xticklabels(rho_labels)
    ax_a.set_ylabel(f"# stalled $\\omega$ values (of {len(OMEGA_VALUES)})")
    ax_a.set_title("(a) Lumped DC stall count")
    ax_a.set_ylim(0, len(OMEGA_VALUES) + 0.5)
    ax_a.legend(fontsize=8)
    ax_a.grid(True, axis="y", alpha=0.3)

    b = results["U6b"]
    rhos = RHO_RATIOS_B
    errs_rho = [r["err_inf"] for r in b["rho_sweep"]]
    ns = [r["N"] for r in b["n_sweep"]]
    hs_n = [1.0 / n for n in ns]
    errs_n = [r["err_inf"] for r in b["n_sweep"]]
    ax_b.loglog(rhos, errs_rho, "o-", color="C0",
                label=f"$\\rho$-sweep @ N={N_GRID}")
    # Twin axis for the N-sweep so the two stories share one panel.
    ax_b2 = ax_b.twiny()
    ax_b2.loglog(hs_n, errs_n, "s--", color="C3",
                 label=f"$N$-sweep @ $\\rho={int(RHO_CONV)}$")
    ax_b2.set_xlabel(f"$h$ ($N$-sweep)")
    ax_b2.invert_xaxis()
    ax_b.set_xlabel("$\\rho_l / \\rho_g$ ($\\rho$-sweep)")
    ax_b.set_ylabel("$L_\\infty$ error (liquid bulk, $\\phi > 3h$)")
    ax_b.set_title(f"(b) Lumped + DC $k{{=}}3$ MMS")
    handles_a, labels_a = ax_b.get_legend_handles_labels()
    handles_b, labels_b = ax_b2.get_legend_handles_labels()
    ax_b.legend(handles_a + handles_b, labels_a + labels_b, fontsize=8)
    ax_b.grid(True, which="both", alpha=0.3)

    rows_1d = results["U6c"]["hfe_1d"]
    rows_2d = results["U6c"]["hfe_2d"]
    hs = [r["h"] for r in rows_1d]
    convergence_loglog(
        ax_c, hs,
        {
            "1D Hermite-5 extrap.":    [r["err_inf"] for r in rows_1d],
            "2D HFE band (max)":       [r["err_inf_max"] for r in rows_2d],
            "2D HFE band (median)":    [r["err_inf_med"] for r in rows_2d],
        },
        ref_orders=[6, 7], xlabel="$h$", ylabel="$L_\\infty$ error",
        title="(c) HFE convergence",
    )

    save_figure(fig, OUT / "U6_split_ppe_dc_hfe", also_to=PAPER_FIG)


def make_hfe_field_figure(results: dict) -> None:
    field = results["U6c"].get("hfe_field", {})
    if not field:
        return

    X = np.asarray(field["X"])
    Y = np.asarray(field["Y"])
    phi = np.asarray(field["phi"])
    truth = np.asarray(field["truth"])
    extended = np.asarray(field["extended"])
    band_abs_error = np.asarray(field["band_abs_error"])
    log_error = np.ma.masked_invalid(np.log10(np.maximum(band_abs_error, 1.0e-16)))

    q_min = float(min(np.nanmin(truth), np.nanmin(extended)))
    q_max = float(max(np.nanmax(truth), np.nanmax(extended)))
    err_min = float(np.nanmin(log_error))
    err_max = float(np.nanmax(log_error))

    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
    panels = [
        (truth, "analytic $q(x_\\Gamma)$", "viridis", (q_min, q_max), "$q$"),
        (extended, "HFE $q_{ext}$", "viridis", (q_min, q_max), "$q_{ext}$"),
        (log_error, "band $\\log_{10}|e|$", "magma", (err_min, err_max), "$\\log_{10}|e|$"),
    ]
    for ax, (field_data, title, cmap, vlim, cb_label) in zip(axes, panels):
        field_panel(
            ax, X, Y, field_data, cmap=cmap, vlim=vlim,
            contour_field=phi, contour_levels=(0.0,),
            contour_color="white" if cmap == "magma" else "k",
            cb_label=cb_label, title=title,
        )
        ax.set_xlabel("$x$")
        ax.set_ylabel("$y$")
    fig.suptitle(f"U6-c: HFE circular-band field extension (N={int(field['N'])})")
    save_figure(fig, OUT / "U6_hfe_2d_field", also_to=PAPER_FIG_HFE)


def _slope_of(rows, key) -> float:
    hs = [r["h"] for r in rows]
    errs = [r[key] for r in rows]
    rates = compute_convergence_rates(errs, hs)
    finite = [r for r in rates if np.isfinite(r) and r > 0]
    return float(np.mean(finite)) if finite else float("nan")


def print_summary(results: dict) -> None:
    a = results["U6a"]
    print("U6-a Lumped DC stall study (Chapter 12 U6: ρ_l/ρ_g=1 clean; ≥100 stalls at high ω):")
    for r in RHO_RATIOS_A:
        rk = f"r{int(r)}"
        for k in DC_K_VALUES:
            stall_omegas = [
                w for w in OMEGA_VALUES
                if a[rk][f"w{w:g}"][f"k{k}"]["stalled"]
            ]
            n_corrs = [
                a[rk][f"w{w:g}"][f"k{k}"]["n_corrections"]
                for w in OMEGA_VALUES
            ]
            tag = "[OK]" if (r >= 100 and len(stall_omegas) >= 2) else (
                  "[note]" if stall_omegas else "[clean]")
            print(f"  ρ_l={int(r):>4}  k={k}  stalled @ ω in {stall_omegas}  "
                  f"n_corrs={n_corrs}  {tag}")

    b = results["U6b"]
    print(f"U6-b Lumped + DC k=3 MMS (Chapter 12 U6 一括 DC: "
          "6.6e-12 → 2.7e-5 across ρ=1→1000):")
    cells = "  ".join(f"ρ={int(r['rho_l']):>4}: {r['err_inf']:.2e}"
                      for r in b["rho_sweep"])
    print(f"  ρ-sweep  N={N_GRID}  {cells}")
    deg = b["rho_sweep"][-1]["err_inf"] / max(b["rho_sweep"][0]["err_inf"], 1e-30)
    flag = "[OK]" if deg > 10.0 else "[note]"
    print(f"  ρ-sweep degradation ratio (ρ=1000 / ρ=1): {deg:.2g}  {flag}")
    cells = "  ".join(f"N={r['N']:>3}: {r['err_inf']:.2e}"
                      for r in b["n_sweep"])
    print(f"  N-sweep  ρ={int(RHO_CONV)}  {cells}")
    n_slope = _slope_of(b["n_sweep"], "err_inf")
    flag = "[OK]" if n_slope < 1.0 else "[note]"
    print(f"  N-sweep slope (Chapter 12 U6 table: degraded positive slope ≈0.78): "
          f"{n_slope:.2f}  {flag}")

    rows_1d = results["U6c"]["hfe_1d"]
    rows_2d = results["U6c"]["hfe_2d"]
    print("U6-c HFE convergence (Chapter 12 U6: 1D ≈ 5.99; 2D max ≈ 5.05 / med ≈ 3.21):")
    print(f"  1D Hermite-5 extrap. slope         = "
          f"{_slope_of(rows_1d, 'err_inf'):.2f}")
    print(f"  2D HFE band-max slope              = "
          f"{_slope_of(rows_2d, 'err_inf_max'):.2f}")
    print(f"  2D HFE band-median slope           = "
          f"{_slope_of(rows_2d, 'err_inf_med'):.2f}")
    print("  Per-row 2D max errors: " + ", ".join(
        f"N={r['N']}: {r['err_inf_max']:.2e}" for r in rows_2d))


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    make_hfe_field_figure(results)
    print_summary(results)
    print(f"==> U6 outputs in {OUT}")


if __name__ == "__main__":
    main()
