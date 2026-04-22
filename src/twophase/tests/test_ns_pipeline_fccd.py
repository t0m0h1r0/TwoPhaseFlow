"""
CHK-160 integration coverage: FCCD + Ridge-Eikonal + α=2 + GFM-style
reproject + InterfaceLimitedFilter HFE, end-to-end through
``TwoPhaseNSSolver``.

Covers the minimum stack the user requested for
``experiment/ch13/config/ch13_04_capwave_fullstack_alpha2.yaml`` at
``N=16`` so the test stays fast, 2 steps, sigma>0.  No NaN, finite KE,
non-trivial ψ advection after the stack swap.
"""

from __future__ import annotations

import numpy as np
import pytest

from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.config_io import ExperimentConfig


N = 16
L = 1.0


def _mode2_ic(solver: TwoPhaseNSSolver) -> np.ndarray:
    """Prolate-perturbed disc: ψ=1 inside, ψ=0 outside, ε-widening applied."""
    X, Y = solver.X, solver.Y
    Xh = np.asarray(solver._backend.to_host(X))
    Yh = np.asarray(solver._backend.to_host(Y))
    r = np.sqrt((Xh - 0.5) ** 2 + (Yh - 0.5) ** 2)
    theta = np.arctan2(Yh - 0.5, Xh - 0.5)
    R_iface = 0.25 * (1.0 + 0.05 * np.cos(2.0 * theta))
    phi = R_iface - r
    return solver.psi_from_phi(phi)


@pytest.mark.parametrize(
    "advection_scheme,convection_scheme",
    [("fccd_flux", "fccd_flux"), ("fccd_nodal", "fccd_nodal")],
)
def test_fullstack_two_steps_no_nan(advection_scheme: str, convection_scheme: str):
    """FCCD × Ridge-Eikonal × α=2 × consistent_gfm × HFE — 2 steps stable."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        use_local_eps=True,
        eps_factor=1.5,
        grid_rebuild_freq=0,         # static α=2 grid
        reinit_method="ridge_eikonal",
        reinit_every=2,
        reinit_eps_scale=1.4,
        ridge_sigma_0=3.0,
        reproject_mode="consistent_gfm",
        phi_primary_transport=True,
        advection_scheme=advection_scheme,
        convection_scheme=convection_scheme,
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    # Mimic run_simulation()'s one-shot rebuild for static α>1 configs, so
    # _fvm_pressure_grad finds its precomputed spacing (grid_rebuild_freq=0).
    psi, u, v = solver._rebuild_grid(psi, u, v, rho_l=833.0, rho_g=1.0)
    for i in range(2):
        psi, u, v, p = solver.step(
            psi, u, v, dt=5e-4,
            rho_l=833.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )
    for name, arr in [("psi", psi), ("u", u), ("v", v), ("p", p)]:
        assert np.all(np.isfinite(arr)), f"{name} not finite"
    # ψ bounded in [0, 1] to within tiny drift (CLS invariant)
    assert float(np.min(psi)) >= -1e-10
    assert float(np.max(psi)) <= 1.0 + 1e-10


def test_fccd_solver_is_shared():
    """Sanity: convection + advection share one FCCDSolver instance."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        advection_scheme="fccd_flux",
        convection_scheme="fccd_flux",
    )
    assert solver._fccd is not None
    assert solver._fccd_conv._fccd is solver._fccd
    assert solver._adv._fccd is solver._fccd


def test_fccd_not_constructed_when_unused():
    """Baseline path: no FCCDSolver allocated when both schemes are legacy."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        advection_scheme="dissipative_ccd",
        convection_scheme="ccd",
    )
    assert solver._fccd is None
    assert solver._fccd_conv is None


def test_pipeline_uses_matrixfree_fvm_ppe():
    """Stage 4 PPE uses the shared NumPy/CuPy matrix-free FVM solver."""
    from twophase.ppe.fvm_matrixfree import PPESolverFVMMatrixFree

    solver = TwoPhaseNSSolver(N, N, L, L, bc_type="wall")
    assert isinstance(solver._ppe_solver, PPESolverFVMMatrixFree)


def test_pipeline_can_select_direct_fvm_ppe():
    """Stage 4 PPE direct sparse solve remains selectable for comparisons."""
    from twophase.ppe.fvm_spsolve import PPESolverFVMSpsolve

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        ppe_solver="fvm_direct",
    )
    assert isinstance(solver._ppe_solver, PPESolverFVMSpsolve)


def test_surface_tension_uses_projector_gradient_operator():
    """R-1.5: CSF ∇ψ uses the same gradient operator as pressure correction."""
    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        alpha_grid=2.0,
        grid_rebuild_freq=0,
    )
    psi = _mode2_ic(solver)
    velocity = np.zeros_like(psi)
    psi, _u, _v = solver._rebuild_grid(psi, velocity, velocity)
    kappa = np.ones_like(psi)

    force_x, force_y = solver._st_force.compute(
        kappa, psi, 2.0, solver._ccd, solver._grad_op,
    )

    np.testing.assert_allclose(
        solver._backend.to_host(force_x),
        solver._backend.to_host(2.0 * solver._grad_op.gradient(psi, 0)),
    )
    np.testing.assert_allclose(
        solver._backend.to_host(force_y),
        solver._backend.to_host(2.0 * solver._grad_op.gradient(psi, 1)),
    )


def test_weno5_advection_constructed_from_scheme():
    """YAML-advertised WENO5 path must not silently fall back to DCCD."""
    from twophase.levelset.advection import LevelSetAdvection

    solver = TwoPhaseNSSolver(
        N, N, L, L, bc_type="wall",
        advection_scheme="weno5",
        convection_scheme="ccd",
    )
    assert isinstance(solver._adv, LevelSetAdvection)
    assert solver._fccd is None


def test_fccd_psi_bimodal_preserved():
    """Regression: ψ bimodal structure must survive FCCD + phi_primary transport.

    Prior bug: ns_pipeline constructed ``FCCDLevelSetAdvection(
    mass_correction=True)``.  Under ``phi_primary_transport=True`` the
    ``advance`` call is on **φ (SDF)**, and the ψ-CLS correction formula
    ``w = 4q(1-q)`` goes negative in the liquid bulk (φ < 0), scrambling
    φ every step.  After psi_from_phi the interface smeared to the domain
    mean V_liq/V_tot ≈ 0.2 within ~6 steps.  Mass integral was preserved
    by the outer ψ correction, so ``volume_conservation`` passed while
    the interface was visually gone.

    This test locks in the fix (mass_correction=False in ns_pipeline) with
    a stronger gate: the bimodal [0, 1] structure of ψ must survive.
    """
    solver = TwoPhaseNSSolver(
        32, 32, L, L, bc_type="wall",
        alpha_grid=2.0,
        use_local_eps=True,
        eps_factor=1.5,
        grid_rebuild_freq=0,
        reinit_method="ridge_eikonal",
        reinit_every=2,
        reinit_eps_scale=1.4,
        ridge_sigma_0=3.0,
        reproject_mode="consistent_gfm",
        phi_primary_transport=True,
        advection_scheme="fccd_flux",
        convection_scheme="fccd_flux",
    )
    psi = _mode2_ic(solver)
    u = np.zeros_like(psi)
    v = np.zeros_like(psi)
    psi, u, v = solver._rebuild_grid(psi, u, v, rho_l=833.0, rho_g=1.0)
    for i in range(6):
        psi, u, v, p = solver.step(
            psi, u, v, dt=5e-4,
            rho_l=833.0, rho_g=1.0, sigma=1.0, mu=0.05, step_index=i,
        )
    psi_host = np.asarray(solver._backend.to_host(psi))
    assert float(np.max(psi_host)) > 0.9, (
        f"ψ max collapsed to {float(np.max(psi_host))!r} — interface vanished"
    )
    assert float(np.min(psi_host)) < 0.1, (
        f"ψ min rose to {float(np.min(psi_host))!r} — interface vanished"
    )


def test_from_config_threads_fccd_keys():
    """YAML → RunCfg → TwoPhaseNSSolver dispatch end-to-end."""
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [L, L], "boundary": "wall"},
            "distribution": {
                "type": "interface_fitted",
                "method": "gaussian_levelset",
                "alpha": 2.0,
                "schedule": "static",
            },
        },
        "interface": {
            "thickness": {"mode": "local", "base_factor": 1.5},
            "tracking": {"enabled": True, "primary": "phi"},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 2},
                "profile": {"eps_scale": 1.4, "ridge_sigma_0": 3.0},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 833.0, "mu": 0.05},
                "gas": {"rho": 1.0, "mu": 0.05},
            },
            "surface_tension": 1.0,
        },
        "run": {
            "time": {"final": 1.0, "cfl": 0.1},
        },
        "numerics": {
            "physical_time": {
                "interface_advection": {"spatial": "fccd_flux", "time": "explicit"},
                "momentum": {
                    "form": "primitive_velocity",
                    "convection": {"spatial": "fccd_flux", "time": "explicit"},
                    "viscosity": {"spatial": "ccd", "time": "crank_nicolson"},
                    "capillary_force": {
                        "model": "csf",
                        "time": "explicit",
                        "curvature": "psi_direct_hfe",
                        "force_gradient": "projection_consistent",
                    },
                },
            },
            "elliptic": {
                "pressure_projection": {
                    "mode": "consistent_gfm",
                    "poisson": {
                        "discretization": "fvm",
                        "solver": {"kind": "direct"},
                    },
                },
            },
        },
    }
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._advection_scheme == "fccd_flux"
    assert solver._convection_scheme == "fccd_flux"
    assert solver._ppe_solver_name == "fvm_direct"
    assert solver._cn_viscous is True
    assert solver._interface_tracking_method == "phi_primary"
    assert solver._interface_tracking_enabled is True
    assert solver._fccd is not None
    assert solver._fccd_conv is not None


def test_from_config_can_disable_interface_tracking():
    raw = {
        "grid": {
            "cells": [N, N],
            "domain": {"size": [L, L], "boundary": "wall"},
            "distribution": {
                "type": "uniform",
                "method": "none",
                "alpha": 1.0,
                "schedule": "static",
            },
        },
        "interface": {
            "thickness": {"mode": "nominal", "base_factor": 1.5},
            "tracking": {"enabled": False, "primary": "none"},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 2},
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 1.0, "mu": 0.01},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.0,
        },
        "run": {
            "time": {"final": 0.1, "cfl": 0.1},
        },
        "numerics": {
            "physical_time": {
                "interface_advection": {"spatial": "dissipative_ccd", "time": "explicit"},
                "momentum": {
                    "form": "primitive_velocity",
                    "convection": {"spatial": "ccd", "time": "explicit"},
                    "viscosity": {"spatial": "ccd", "time": "explicit"},
                    "capillary_force": {
                        "model": "csf",
                        "time": "explicit",
                        "curvature": "psi_direct_hfe",
                        "force_gradient": "projection_consistent",
                    },
                },
            },
            "elliptic": {
                "pressure_projection": {
                    "mode": "standard",
                    "poisson": {
                        "discretization": "fvm",
                        "solver": {"kind": "iterative", "method": "gmres"},
                    },
                },
            },
        },
    }
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._interface_tracking_enabled is False
    assert solver._interface_tracking_method == "none"
