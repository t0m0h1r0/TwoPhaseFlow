"""Shared §14 production-stack helpers for CH13 verification scripts."""

from __future__ import annotations

import pathlib
from dataclasses import dataclass
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
    step_diagnostics: bool = False,
    initial_velocity: dict | None = None,
) -> ExperimentConfig:
    """Build a circle-droplet config using the §14 FCCD/UCCD6/filtered-curvature/PPE stack."""
    if (cfl is None) == (dt is None):
        raise ValueError("exactly one of cfl or dt must be provided")
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
            "distribution": distribution,
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
        "run": {"time": time_cfg, "debug": {"step_diagnostics": step_diagnostics}},
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
                        "solver": {
                            "kind": "defect_correction",
                            "tolerance": 1.0e-8,
                            "corrections": {
                                "max_iterations": 3,
                                "relaxation": 0.8,
                            },
                        },
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


@dataclass(frozen=True)
class CircleMetricContext:
    """Device-resident static-droplet masks and quadrature data."""

    dV: object
    volume0: float
    inside_mask: object
    outside_mask: object
    inside_count: int
    outside_count: int


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


def make_circle_metric_context(
    solver: TwoPhaseNSSolver,
    psi,
    *,
    radius: float,
    center: tuple[float, float],
) -> CircleMetricContext:
    """Precompute device-side masks for static circle-droplet diagnostics."""
    xp = solver.backend.xp
    dV = solver._grid.cell_volumes()
    psi_dev = xp.asarray(psi)
    volume0 = float(solver.backend.to_host(xp.sum(psi_dev * dV)))
    phi = radius - xp.sqrt(
        (solver.X - float(center[0])) ** 2
        + (solver.Y - float(center[1])) ** 2
    )
    inside_mask = phi > 3.0 * solver.h_min
    outside_mask = phi < -3.0 * solver.h_min
    counts = np.asarray(
        solver.backend.to_host(
            xp.stack([xp.sum(inside_mask), xp.sum(outside_mask)])
        )
    )
    return CircleMetricContext(
        dV=dV,
        volume0=volume0,
        inside_mask=inside_mask,
        outside_mask=outside_mask,
        inside_count=int(counts[0]),
        outside_count=int(counts[1]),
    )


def collect_circle_step_metrics(
    solver: TwoPhaseNSSolver,
    context: CircleMetricContext,
    *,
    psi,
    u,
    v,
    p,
) -> tuple[float, float, float]:
    """Return ``u_inf``, volume drift, and pressure contrast with one scalar sync."""
    xp = solver.backend.xp
    psi_dev = xp.asarray(psi)
    u_dev = xp.asarray(u)
    v_dev = xp.asarray(v)
    p_dev = xp.asarray(p)
    u_inf = xp.sqrt(xp.max(u_dev * u_dev + v_dev * v_dev))
    volume = xp.sum(psi_dev * context.dV)
    volume_drift = xp.abs(volume - context.volume0) / max(abs(context.volume0), 1.0e-30)
    if context.inside_count > 0 and context.outside_count > 0:
        inside_sum = xp.sum(xp.where(context.inside_mask, p_dev, 0.0))
        outside_sum = xp.sum(xp.where(context.outside_mask, p_dev, 0.0))
        pressure_contrast = (
            inside_sum / float(context.inside_count)
            - outside_sum / float(context.outside_count)
        )
    else:
        pressure_contrast = xp.asarray(float("nan"))
    metrics = np.asarray(
        solver.backend.to_host(
            xp.stack([u_inf, volume_drift, pressure_contrast])
        )
    )
    return float(metrics[0]), float(metrics[1]), float(metrics[2])


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
    metric_context = make_circle_metric_context(
        solver,
        psi,
        radius=radius,
        center=center,
    )
    u_inf_history: list[float] = []
    dp_history: list[float] = []
    volume_history: list[float] = []
    dt_history: list[float] = []
    limiter_history: list[str] = []
    blew_up = False
    error = ""
    p = solver.backend.xp.zeros_like(solver.backend.xp.asarray(psi))
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
        u_inf, volume_drift, dp = collect_circle_step_metrics(
            solver,
            metric_context,
            psi=psi,
            u=u,
            v=v,
            p=p,
        )
        u_inf_history.append(u_inf)
        volume_history.append(volume_drift)
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
