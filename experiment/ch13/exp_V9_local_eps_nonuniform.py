#!/usr/bin/env python3
"""[V9] Local-epsilon validation on non-uniform grid with the §14 stack.

Paper ref: §13.5 (sec:local_eps_validation).

V9 is a reduced static-droplet diagnostic for the non-uniform-grid interface
width rule.  The numerical path is deliberately config-driven through
``TwoPhaseNSSolver.from_config`` so that the tested operators match the §14
production stack:

  - FCCD interface transport and pressure gradient,
  - UCCD6 momentum convection,
  - direct-ψ curvature with interface-limited filtering (``psi_direct_filtered``),
  - pressure-jump surface tension embedded in phase-separated FCCD PPE,
  - face-flux projection.

Cases
-----
  A:  alpha = 1.0  + nominal eps = 1.5 h  (uniform reference)
  B:  alpha = 2.0  + nominal eps = 1.5 h  (fixed-width non-uniform)
  C:  alpha = 2.0  + local eps_ij = 1.5 max(h_x_i, h_y_j)

The material constants and resolution are intentionally reduced relative to
§14's water-air run; V9 tests the operator-stack consistency and the local-eps
choice, not the full §14 material benchmark.  In this pressure-jump path the
returned pressure is a projection/corrector diagnostic, so the primary V9
metrics are spurious current and volume drift; pressure contrast is plotted
only as a secondary solver diagnostic.

Usage
-----
  make run EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
  make plot EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.ns_step_state import NSStepRequest
from twophase.tools.experiment import (
    apply_style,
    experiment_argparser,
    experiment_dir,
    field_panel,
    load_results,
    save_figure,
    save_results,
)

apply_style()
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIGURES = pathlib.Path(__file__).resolve().parents[2] / "paper" / "figures"

R = 0.25
CENTER = (0.5, 0.5)
SIGMA = 0.10
RHO_L = 10.0
RHO_G = 1.0
MU_L = 1.0e-3
MU_G = 1.0e-4
N_LIST = (24, 32)
FIELD_N = 32
N_STEPS = 10
CFL_MULTIPLIER = 0.50
DP_EXACT = SIGMA / R


def _case_config(N: int, alpha: float, eps_mode: str) -> ExperimentConfig:
    if alpha <= 1.0:
        distribution = {
            "type": "uniform",
            "method": "none",
            "alpha": 1.0,
            "schedule": "static",
        }
    else:
        distribution = {
            "schedule": "static",
            "axes": {
                "x": {
                    "type": "nonuniform",
                    "monitors": {"interface": {"alpha": alpha}},
                },
                "y": {
                    "type": "nonuniform",
                    "monitors": {"interface": {"alpha": alpha}},
                },
            },
        }
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [1.0, 1.0], "boundary": "wall"},
            "distribution": distribution,
        },
        "interface": {
            "thickness": {"mode": eps_mode, "base_factor": 1.5},
            "geometry": {"curvature": {"method": "psi_direct_filtered", "cap": 5.0}},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 20},
                "profile": {"eps_scale": 1.4, "ridge_sigma_0": 3.0},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": RHO_L, "mu": MU_L},
                "gas": {"rho": RHO_G, "mu": MU_G},
            },
            "surface_tension": SIGMA,
            "gravity": 0.0,
        },
        "run": {
            "time": {
                "final": 10.0,
                "max_steps": N_STEPS,
                "cfl": CFL_MULTIPLIER,
                "print_every": N_STEPS + 1,
            },
            "debug": {"step_diagnostics": True},
        },
        "numerics": {
            "time": {"algorithm": "fractional_step"},
            "interface": {
                "transport": {
                    "variable": "psi",
                    "spatial": "fccd",
                    "time_integrator": "tvd_rk3",
                }
            },
            "momentum": {
                "predictor": {"assembly": "balanced_buoyancy"},
                "terms": {
                    "convection": {
                        "spatial": "uccd6",
                        "time_integrator": "imex_bdf2",
                    },
                    "pressure": {"gradient": "fccd"},
                    "viscosity": {
                        "spatial": "ccd",
                        "time_integrator": "implicit_bdf2",
                    },
                    "surface_tension": {"formulation": "pressure_jump"},
                },
            },
            "projection": {
                "face_flux_projection": True,
                "canonical_face_state": True,
                "face_native_predictor_state": True,
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_separated",
                        "interface_coupling": "affine_jump",
                    },
                    "solver": {
                        "kind": "defect_correction",
                        "corrections": {
                            "max_iterations": 3,
                            "tolerance": 1.0e-8,
                            "relaxation": 1.0,
                        },
                        "base_solver": {
                            "kind": "iterative",
                            "method": "gmres",
                            "tolerance": 1.0e-6,
                            "max_iterations": 500,
                            "restart": 80,
                            "preconditioner": "jacobi",
                        },
                    },
                },
            },
        },
        "initial_condition": {
            "type": "circle",
            "center": list(CENTER),
            "radius": R,
            "interior_phase": "liquid",
        },
        "boundary_condition": {"type": "wall"},
        "output": {"dir": str(OUT), "save_npz": True, "snapshots": {"times": []}},
    }
    return ExperimentConfig.from_dict(raw)


def _assert_ch14_stack(cfg: ExperimentConfig, solver: TwoPhaseNSSolver) -> dict:
    expected = {
        "interface transport": (cfg.run.advection_scheme, "fccd_flux"),
        "momentum convection": (cfg.run.convection_scheme, "uccd6"),
        "pressure gradient": (cfg.run.pressure_gradient_scheme, "fccd_flux"),
        "surface tension": (cfg.run.surface_tension_scheme, "pressure_jump"),
        "PPE": (cfg.run.ppe_solver, "fccd_iterative"),
        "PPE coefficient": (cfg.run.ppe_coefficient_scheme, "phase_separated"),
        "PPE coupling": (cfg.run.ppe_interface_coupling_scheme, "affine_jump"),
        "reinitialization": (cfg.run.reinit_method, "ridge_eikonal"),
    }
    mismatches = [
        f"{name}: got {actual!r}, expected {want!r}"
        for name, (actual, want) in expected.items()
        if actual != want
    ]
    if not cfg.run.face_flux_projection:
        mismatches.append("projection: face_flux_projection is disabled")
    if solver._fccd is None or solver._fccd_div_op is None:
        mismatches.append("solver: FCCD operator/divergence stack was not built")
    if mismatches:
        raise RuntimeError("V9 is not using the §14 stack:\n  " + "\n  ".join(mismatches))
    return {name: actual for name, (actual, _) in expected.items()}


def _to_host(solver: TwoPhaseNSSolver, value) -> np.ndarray:
    return np.asarray(solver.backend.to_host(value))


def _control_volumes(solver: TwoPhaseNSSolver) -> np.ndarray:
    return np.asarray(solver.backend.to_host(solver._grid.cell_volumes()))


def _volume(psi: np.ndarray, dV: np.ndarray) -> float:
    return float(np.sum(np.asarray(psi) * np.asarray(dV)))


def _signed_distance(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    return R - np.sqrt((X - CENTER[0]) ** 2 + (Y - CENTER[1]) ** 2)


def _measure_dp(p: np.ndarray, X: np.ndarray, Y: np.ndarray, h_min: float) -> float:
    phi = _signed_distance(X, Y)
    inside = phi > 3.0 * h_min
    outside = phi < -3.0 * h_min
    if inside.any() and outside.any():
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float("nan")


def _case_label(case_id: str) -> str:
    return {
        "A": r"$\alpha=1$, nominal $\epsilon$",
        "B": r"$\alpha=2$, nominal $\epsilon$",
        "C": r"$\alpha=2$, local $\epsilon_{ij}$",
    }[case_id]


def _run_case(N: int, case_id: str, alpha: float, eps_mode: str) -> dict:
    cfg = _case_config(N, alpha, eps_mode)
    solver = TwoPhaseNSSolver.from_config(cfg)
    stack = _assert_ch14_stack(cfg, solver)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics

    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
        mode = "local" if cfg.grid.use_local_eps else "nominal"
        print(
            f"  [V9 {case_id}] static non-uniform grid built "
            f"(eps={mode}, h_min={solver.h_min:.4e})"
        )

    X = _to_host(solver, solver.X)
    Y = _to_host(solver, solver.Y)
    dV = _control_volumes(solver)
    psi0 = _to_host(solver, psi).copy()
    vol0 = _volume(psi0, dV)

    u_inf_history = []
    dp_history = []
    volume_history = []
    dt_history = []
    limiter_history = []
    blew_up = False
    error = ""
    p = np.zeros_like(psi0)

    for step in range(cfg.run.max_steps or N_STEPS):
        try:
            budget = solver.dt_budget(
                u,
                v,
                ph,
                cfg.run.cfl,
                cfl_advective=cfg.run.cfl_advective,
                cfl_capillary=cfg.run.cfl_capillary,
                cfl_viscous=cfg.run.cfl_viscous,
            )
            dt = float(budget.dt)
            if not np.isfinite(dt) or dt <= 0.0:
                raise FloatingPointError(f"invalid dt={dt}")
            psi, u, v, p = solver.step_request(
                NSStepRequest(
                    psi=psi,
                    u=u,
                    v=v,
                    dt=dt,
                    rho_l=ph.rho_l,
                    rho_g=ph.rho_g,
                    sigma=ph.sigma,
                    mu=ph.mu,
                    g_acc=ph.g_acc,
                    rho_ref=ph.rho_ref,
                    mu_l=ph.mu_l,
                    mu_g=ph.mu_g,
                    bc_hook=bc_hook,
                    step_index=step,
                ),
                return_host_pressure=False,
            )
        except Exception as exc:
            blew_up = True
            error = f"{type(exc).__name__}: {exc}"
            break

        psi_h = _to_host(solver, psi)
        u_h = _to_host(solver, u)
        v_h = _to_host(solver, v)
        p_h = _to_host(solver, p)
        speed = np.sqrt(u_h * u_h + v_h * v_h)
        u_inf = float(np.max(speed))
        dp = _measure_dp(p_h, X, Y, solver.h_min)
        volume = _volume(psi_h, dV)

        u_inf_history.append(u_inf)
        dp_history.append(dp)
        volume_history.append(abs(volume - vol0) / max(abs(vol0), 1.0e-30))
        dt_history.append(dt)
        limiter_history.append(str(budget.limiter))
        if not np.isfinite(u_inf) or u_inf > 1.0e3:
            blew_up = True
            error = f"non-finite or excessive velocity: {u_inf:.3e}"
            break

    psi_h = _to_host(solver, psi)
    u_h = _to_host(solver, u)
    v_h = _to_host(solver, v)
    p_h = _to_host(solver, p)
    speed = np.sqrt(u_h * u_h + v_h * v_h)
    u_arr = np.asarray(u_inf_history)
    dp_arr = np.asarray(dp_history)
    vol_arr = np.asarray(volume_history)
    dt_arr = np.asarray(dt_history)
    dp_final = float(dp_arr[-1]) if len(dp_arr) else float("nan")

    return {
        "N": N,
        "case": case_id,
        "label": _case_label(case_id),
        "alpha": alpha,
        "eps_mode": eps_mode,
        "stack": stack,
        "h_min": float(solver.h_min),
        "n_steps": int(len(u_arr)),
        "blew_up": blew_up,
        "error": error,
        "dt_min": float(np.min(dt_arr)) if len(dt_arr) else float("nan"),
        "dt_max": float(np.max(dt_arr)) if len(dt_arr) else float("nan"),
        "limiter_final": limiter_history[-1] if limiter_history else "",
        "u_inf_history": u_arr,
        "dp_history": dp_arr,
        "volume_history": vol_arr,
        "u_inf_max": float(np.max(u_arr)) if len(u_arr) else float("nan"),
        "u_inf_final": float(u_arr[-1]) if len(u_arr) else float("nan"),
        "dp_final": dp_final,
        "dp_exact": DP_EXACT,
        "dp_abs_ratio": abs(dp_final) / DP_EXACT
        if np.isfinite(dp_final)
        else float("nan"),
        "volume_drift_final": float(vol_arr[-1]) if len(vol_arr) else float("nan"),
        "X": X,
        "Y": Y,
        "psi": psi_h,
        "pressure": p_h,
        "speed": speed,
    }


def run_all() -> dict:
    cases = {
        "A": (1.0, "nominal"),
        "B": (2.0, "nominal"),
        "C": (2.0, "local"),
    }
    runs = {}
    for N in N_LIST:
        for case_id, (alpha, eps_mode) in cases.items():
            print(f"[V9] N={N}, case={case_id}, alpha={alpha}, eps={eps_mode}")
            runs[f"N{N}_{case_id}"] = _run_case(N, case_id, alpha, eps_mode)
    return {
        "runs": runs,
        "meta": {
            "N_steps": N_STEPS,
            "cfl_multiplier": CFL_MULTIPLIER,
            "rho_l": RHO_L,
            "rho_g": RHO_G,
            "sigma": SIGMA,
            "R": R,
            "dp_exact": DP_EXACT,
        },
    }


def make_figures(results: dict) -> None:
    runs = results["runs"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax_u, ax_d = axes
    colors = {"A": "C0", "B": "C1", "C": "C2"}
    for N in N_LIST:
        for case_id in ("A", "B", "C"):
            r = runs.get(f"N{N}_{case_id}")
            if r is None or len(r["u_inf_history"]) == 0:
                continue
            arr = np.asarray(r["u_inf_history"])
            linestyle = "-" if N == N_LIST[0] else "--"
            ax_u.semilogy(
                np.arange(1, len(arr) + 1),
                arr,
                color=colors[case_id],
                linestyle=linestyle,
                label=f"N={N}, {case_id}",
            )
    ax_u.set_xlabel("step")
    ax_u.set_ylabel(r"$\|u\|_\infty$")
    ax_u.set_title("V9 §14 stack: spurious-current trajectory")
    ax_u.legend(fontsize=7)

    cats, vals, bar_colors = [], [], []
    for N in N_LIST:
        for case_id in ("A", "B", "C"):
            r = runs.get(f"N{N}_{case_id}")
            cats.append(f"N{N}\n{case_id}")
            vals.append(r["dp_abs_ratio"] if r and not r["blew_up"] else np.nan)
            bar_colors.append(colors[case_id])
    ax_d.bar(cats, vals, color=bar_colors)
    ax_d.set_ylabel(r"$|\Delta p_{\rm corr}|/(\sigma/R)$")
    ax_d.set_yscale("log")
    ax_d.set_title("V9 §14 stack: pressure-corrector contrast")
    save_figure(
        fig,
        OUT / "V9_local_eps_nonuniform",
        also_to=PAPER_FIGURES / "ch13_v9_local_eps",
    )

    field_runs = [runs.get(f"N{FIELD_N}_{case_id}") for case_id in ("A", "B", "C")]
    field_runs = [r for r in field_runs if r is not None and len(r["u_inf_history"]) > 0]
    if len(field_runs) != 3:
        print("Skipping V9 field figure: not all FIELD_N cases are available.")
        return
    vmax = max(float(np.nanmax(r["speed"])) for r in field_runs)
    if not np.isfinite(vmax) or vmax <= 0.0:
        vmax = 1.0

    fig_f, axes_f = plt.subplots(1, 3, figsize=(12.6, 4.0), constrained_layout=True)
    for ax, r in zip(axes_f, field_runs):
        field_panel(
            ax,
            r["X"],
            r["Y"],
            r["speed"],
            cmap="magma",
            vlim=(0.0, vmax),
            contour_field=r["psi"],
            contour_levels=(0.5,),
            contour_color="white",
            contour_lw=0.9,
            cb_label=r"$|u|$",
            title=f"{r['case']}: {_case_label(r['case'])}",
            annotation=(
                rf"$\|u\|_\infty={r['u_inf_final']:.2e}$"
                "\n"
                rf"$|\Delta p_c|/(\sigma/R)={r['dp_abs_ratio']:.2f}$"
            ),
        )
        ax.set_xlabel("x")
        ax.set_ylabel("y")
    fig_f.suptitle(f"V9: §14-stack local-epsilon fields (N={FIELD_N})", fontsize=11)
    save_figure(
        fig_f,
        OUT / "V9_ch14_stack_field",
        also_to=PAPER_FIGURES / "ch13_v9_ch14_stack_field",
    )


def print_summary(results: dict) -> None:
    print(
        "V9 (§14-stack local-ε validation; "
        "A=α1+nominal, B=α2+nominal, C=α2+local):"
    )
    runs = results["runs"]
    for N in N_LIST:
        for case_id in ("A", "B", "C"):
            r = runs.get(f"N{N}_{case_id}")
            if r is None:
                continue
            if r["blew_up"]:
                tag = f"BLEW UP after {r['n_steps']} steps ({r['error']})"
            else:
                tag = (
                    f"|u|_max={r['u_inf_max']:.2e}  "
                    f"Δp={r['dp_final']:.4f}  "
                    f"|Δp_corr|/(σ/R)={r['dp_abs_ratio']:.2f}  "
                    f"vol={r['volume_drift_final']:.2e}"
                )
            print(f"  N={N:>2}  ({case_id}) {_case_label(case_id):>28s}: {tag}")


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    make_figures(results)
    print_summary(results)
    print(f"==> V9 outputs in {OUT}")


if __name__ == "__main__":
    main()
