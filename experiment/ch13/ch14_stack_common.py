"""Shared §14 production-stack helpers for CH13 verification scripts."""

from __future__ import annotations

import pathlib
from collections.abc import Callable

import numpy as np

from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.ns_step_state import NSStepRequest


def ch14_circle_config(
    *,
    N: int,
    out_dir: pathlib.Path,
    radius: float,
    center: tuple[float, float],
    rho_l: float,
    rho_g: float,
    mu_l: float,
    mu_g: float,
    sigma: float,
    max_steps: int,
    final_time: float,
    cfl: float | None = None,
    dt: float | None = None,
    alpha: float = 1.0,
    eps_mode: str = "nominal",
    reinit_every: int = 20,
    curvature_cap: float = 5.0,
    initial_velocity: dict | None = None,
) -> ExperimentConfig:
    """Build a circle-droplet config using the §14 FCCD/UCCD6/filtered-curvature/PPE stack."""
    if (cfl is None) == (dt is None):
        raise ValueError("exactly one of cfl or dt must be provided")
    distribution_type = "uniform" if alpha <= 1.0 else "interface_fitted"
    time_cfg = {
        "final": final_time,
        "max_steps": max_steps,
        "print_every": max_steps + 1,
    }
    if dt is None:
        time_cfg["cfl"] = cfl
    else:
        time_cfg["dt"] = dt
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [1.0, 1.0], "boundary": "wall"},
            "distribution": {
                "type": distribution_type,
                "method": "gaussian_levelset",
                "alpha": alpha,
                "schedule": "static",
            },
        },
        "interface": {
            "thickness": {"mode": eps_mode, "base_factor": 1.5},
            "geometry": {
                "curvature": {"method": "psi_direct_filtered", "cap": curvature_cap}
            },
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": reinit_every},
                "profile": {"eps_scale": 1.4, "ridge_sigma_0": 3.0},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": rho_l, "mu": mu_l},
                "gas": {"rho": rho_g, "mu": mu_g},
            },
            "surface_tension": sigma,
            "gravity": 0.0,
        },
        "run": {"time": time_cfg, "debug": {"step_diagnostics": True}},
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
            "center": list(center),
            "radius": radius,
            "interior_phase": "liquid",
        },
        "boundary_condition": {"type": "wall"},
        "output": {"dir": str(out_dir), "save_npz": True, "snapshots": {"times": []}},
    }
    if initial_velocity is not None:
        raw["initial_velocity"] = initial_velocity
    return ExperimentConfig.from_dict(raw)


def assert_ch14_stack(cfg: ExperimentConfig, solver: TwoPhaseNSSolver, label: str) -> dict:
    """Fail fast unless the solver is using the §14 FCCD/UCCD6/filtered-curvature/PPE stack."""
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
        raise RuntimeError(f"{label} is not using the §14 stack:\n  " + "\n  ".join(mismatches))
    return {name: actual for name, (actual, _) in expected.items()}


def to_host(solver: TwoPhaseNSSolver, value) -> np.ndarray:
    """Return a NumPy view/copy from the active solver backend."""
    return np.asarray(solver.backend.to_host(value))


def circle_phi(
    X: np.ndarray,
    Y: np.ndarray,
    *,
    radius: float,
    center: tuple[float, float],
) -> np.ndarray:
    """Signed distance with positive liquid interior for the circle droplet."""
    return radius - np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)


def phase_pressure_contrast(
    p: np.ndarray,
    X: np.ndarray,
    Y: np.ndarray,
    *,
    radius: float,
    center: tuple[float, float],
    h_min: float,
) -> float:
    """Mean liquid-minus-gas pressure contrast outside the smeared interface."""
    phi = circle_phi(X, Y, radius=radius, center=center)
    inside = phi > 3.0 * h_min
    outside = phi < -3.0 * h_min
    if inside.any() and outside.any():
        return float(np.mean(p[inside]) - np.mean(p[outside]))
    return float("nan")


def run_ch14_case(
    *,
    cfg: ExperimentConfig,
    label: str,
    radius: float,
    center: tuple[float, float],
    velocity_builder: Callable[[TwoPhaseNSSolver, np.ndarray], tuple[np.ndarray, np.ndarray]]
    | None = None,
    velocity_limit: float = 1.0e3,
) -> dict:
    """Run a short verification case through ``TwoPhaseNSSolver.step_request``."""
    solver = TwoPhaseNSSolver.from_config(cfg)
    stack = assert_ch14_stack(cfg, solver, label)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    ph = cfg.physics
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, ph.rho_l, ph.rho_g)
    if velocity_builder is not None:
        u_host, v_host = velocity_builder(solver, psi)
        u = solver.backend.to_device(u_host)
        v = solver.backend.to_device(v_host)
    X = to_host(solver, solver.X)
    Y = to_host(solver, solver.Y)
    dV = to_host(solver, solver._grid.cell_volumes())
    psi0 = to_host(solver, psi).copy()
    volume0 = float(np.sum(psi0 * dV))
    u_inf_history: list[float] = []
    dp_history: list[float] = []
    volume_history: list[float] = []
    dt_history: list[float] = []
    limiter_history: list[str] = []
    blew_up = False
    error = ""
    p = np.zeros_like(psi0)
    for step in range(cfg.run.max_steps or 0):
        try:
            if cfg.run.dt_fixed is None:
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
                limiter_history.append(str(budget.limiter))
            else:
                dt = float(cfg.run.dt_fixed)
                limiter_history.append("fixed")
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
        psi_h = to_host(solver, psi)
        u_h = to_host(solver, u)
        v_h = to_host(solver, v)
        p_h = to_host(solver, p)
        speed = np.sqrt(u_h * u_h + v_h * v_h)
        u_inf = float(np.max(speed))
        volume = float(np.sum(psi_h * dV))
        dp = phase_pressure_contrast(
            p_h,
            X,
            Y,
            radius=radius,
            center=center,
            h_min=solver.h_min,
        )
        u_inf_history.append(u_inf)
        volume_history.append(abs(volume - volume0) / max(abs(volume0), 1.0e-30))
        dp_history.append(dp)
        dt_history.append(dt)
        if not np.isfinite(u_inf) or u_inf > velocity_limit:
            blew_up = True
            error = f"non-finite or excessive velocity: {u_inf:.3e}"
            break
    psi_h = to_host(solver, psi)
    u_h = to_host(solver, u)
    v_h = to_host(solver, v)
    p_h = to_host(solver, p)
    speed = np.sqrt(u_h * u_h + v_h * v_h)
    return {
        "stack": stack,
        "h_min": float(solver.h_min),
        "n_steps": int(len(u_inf_history)),
        "blew_up": blew_up,
        "error": error,
        "dt_history": np.asarray(dt_history),
        "dt_min": float(np.min(dt_history)) if dt_history else float("nan"),
        "dt_max": float(np.max(dt_history)) if dt_history else float("nan"),
        "limiter_final": limiter_history[-1] if limiter_history else "",
        "u_inf_history": np.asarray(u_inf_history),
        "u_inf_max": float(np.max(u_inf_history)) if u_inf_history else float("nan"),
        "u_inf_final": float(u_inf_history[-1]) if u_inf_history else float("nan"),
        "dp_history": np.asarray(dp_history),
        "dp_final": float(dp_history[-1]) if dp_history else float("nan"),
        "volume_history": np.asarray(volume_history),
        "volume_drift_final": float(volume_history[-1]) if volume_history else float("nan"),
        "X": X,
        "Y": Y,
        "psi": psi_h,
        "u": u_h,
        "v": v_h,
        "pressure": p_h,
        "speed": speed,
    }
