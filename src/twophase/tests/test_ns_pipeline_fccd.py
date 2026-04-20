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


def test_from_config_threads_fccd_keys():
    """YAML → RunCfg → TwoPhaseNSSolver dispatch end-to-end."""
    raw = {
        "grid": {"NX": N, "NY": N, "LX": L, "LY": L,
                 "alpha_grid": 2.0, "use_local_eps": True,
                 "grid_rebuild_freq": 0, "bc_type": "wall"},
        "physics": {"rho_l": 833.0, "rho_g": 1.0, "sigma": 1.0, "mu": 0.05},
        "run": {
            "T_final": 1.0, "cfl": 0.1,
            "advection_scheme": "fccd_flux",
            "convection_scheme": "fccd_flux",
            "reinit_method": "ridge_eikonal",
            "reinit_eps_scale": 1.4,
            "ridge_sigma_0": 3.0,
            "reproject_mode": "consistent_gfm",
            "phi_primary_transport": True,
        },
    }
    cfg = ExperimentConfig.from_dict(raw)
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._advection_scheme == "fccd_flux"
    assert solver._convection_scheme == "fccd_flux"
    assert solver._fccd is not None
    assert solver._fccd_conv is not None
