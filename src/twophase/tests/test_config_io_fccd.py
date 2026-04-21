"""Config-IO coverage for FCCD / Ridge-Eikonal keys (CHK-160 prep).

Covers:
  - ``run.advection_scheme`` / ``run.convection_scheme`` default + round-trip.
  - Validator rejection on unknown values.
  - ``run.ridge_sigma_0`` default + positivity check.
"""

from __future__ import annotations

import pytest

from twophase.simulation.config_io import ExperimentConfig


def _minimal(run_extra: dict | None = None) -> dict:
    base = {
        "grid": {"NX": 8, "NY": 8, "LX": 1.0, "LY": 1.0},
        "physics": {"rho_l": 1.0, "rho_g": 1.0, "sigma": 0.0, "mu": 0.01},
        "run": {"T_final": 0.1, "cfl": 0.1},
    }
    if run_extra:
        base["run"].update(run_extra)
    return base


def test_defaults_match_legacy_behaviour():
    cfg = ExperimentConfig.from_dict(_minimal())
    assert cfg.run.advection_scheme == "dissipative_ccd"
    assert cfg.run.convection_scheme == "ccd"
    assert cfg.run.ridge_sigma_0 == 3.0
    assert cfg.physics.mu_l == cfg.physics.mu
    assert cfg.physics.mu_g == cfg.physics.mu


def test_phase_viscosities_round_trip():
    raw = _minimal()
    raw["physics"].pop("mu")
    raw["physics"].update({"mu_l": 0.05, "mu_g": 0.01})
    cfg = ExperimentConfig.from_dict(raw)
    assert cfg.physics.mu_l == 0.05
    assert cfg.physics.mu_g == 0.01
    assert cfg.physics.mu == 0.01


def test_legacy_uniform_mu_sets_both_phases():
    cfg = ExperimentConfig.from_dict(_minimal())
    assert cfg.physics.mu_l == 0.01
    assert cfg.physics.mu_g == 0.01


@pytest.mark.parametrize(
    "adv,conv",
    [("fccd_flux", "fccd_flux"),
     ("fccd_nodal", "ccd"),
     ("weno5", "fccd_nodal")],
)
def test_fccd_keys_round_trip(adv: str, conv: str):
    cfg = ExperimentConfig.from_dict(_minimal({
        "advection_scheme": adv, "convection_scheme": conv,
    }))
    assert cfg.run.advection_scheme == adv
    assert cfg.run.convection_scheme == conv


def test_invalid_advection_scheme_rejected():
    with pytest.raises(ValueError, match="advection_scheme"):
        ExperimentConfig.from_dict(_minimal({"advection_scheme": "bogus"}))


def test_invalid_convection_scheme_rejected():
    with pytest.raises(ValueError, match="convection_scheme"):
        ExperimentConfig.from_dict(_minimal({"convection_scheme": "bogus"}))


def test_ridge_sigma_0_must_be_positive():
    with pytest.raises(ValueError, match="ridge_sigma_0"):
        ExperimentConfig.from_dict(_minimal({"ridge_sigma_0": 0.0}))


def test_ridge_sigma_0_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal({"ridge_sigma_0": 2.5}))
    assert cfg.run.ridge_sigma_0 == 2.5


def test_structured_ch13_yaml_sections_round_trip():
    raw = {
        "grid": {
            "cells": [8, 8],
            "domain": {"size": [1.0, 1.0], "boundary": "wall"},
            "interface_fitting": {
                "enabled": True,
                "method": "gaussian_levelset",
                "alpha": 2.0,
                "schedule": "static",
            },
            "interface_width": {"mode": "local", "base_factor": 1.5},
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 2.0, "mu": 0.03},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.0,
        },
        "run": {
            "time": {"final": 0.1, "cfl": 0.1, "print_every": 7},
            "reinitialization": {
                "method": "ridge_eikonal",
                "every": 2,
                "eps_scale": 1.4,
                "ridge_sigma_0": 2.5,
            },
            "interface_tracking": {
                "enabled": True,
                "method": "phi_primary",
                "redist_every": 5,
                "clip_factor": 10.0,
                "heaviside_eps_scale": 1.2,
            },
            "projection": {"mode": "iim", "face_flux_projection": True},
            "schemes": {
                "levelset_advection": "fccd_flux",
                "momentum_convection": "fccd_nodal",
                "ppe": "fvm_direct",
                "surface_tension": "csf",
                "viscous_time": "crank_nicolson",
            },
            "debug": {"step_diagnostics": True},
        },
        "output": {"snapshots": {"interval": 0.25}},
    }
    cfg = ExperimentConfig.from_dict(raw)
    assert cfg.grid.NX == 8
    assert cfg.grid.NY == 8
    assert cfg.grid.bc_type == "wall"
    assert cfg.grid.alpha_grid == 2.0
    assert cfg.grid.grid_rebuild_freq == 0
    assert cfg.grid.interface_fitting_enabled is True
    assert cfg.grid.interface_fitting_method == "gaussian_levelset"
    assert cfg.grid.use_local_eps is True
    assert cfg.run.snap_interval == 0.25
    assert cfg.run.T_final == 0.1
    assert cfg.run.cfl == 0.1
    assert cfg.run.print_every == 7
    assert cfg.physics.rho_l == 2.0
    assert cfg.physics.rho_g == 1.0
    assert cfg.physics.mu_l == 0.03
    assert cfg.physics.mu_g == 0.01
    assert cfg.run.reinit_method == "ridge_eikonal"
    assert cfg.run.reinit_eps_scale == 1.4
    assert cfg.run.ridge_sigma_0 == 2.5
    assert cfg.run.phi_primary_transport is True
    assert cfg.run.interface_tracking_enabled is True
    assert cfg.run.interface_tracking_method == "phi_primary"
    assert cfg.run.phi_primary_redist_every == 5
    assert cfg.run.phi_primary_clip_factor == 10.0
    assert cfg.run.phi_primary_heaviside_eps_scale == 1.2
    assert cfg.run.reproject_mode == "consistent_iim"
    assert cfg.run.face_flux_projection is True
    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "fccd_nodal"
    assert cfg.run.ppe_solver == "fvm_direct"
    assert cfg.run.pressure_scheme == "fvm_spsolve"
    assert cfg.run.surface_tension_scheme == "csf"
    assert cfg.run.viscous_time_scheme == "crank_nicolson"
    assert cfg.run.cn_viscous is True
    assert cfg.run.debug_diagnostics is True


def test_invalid_structured_reinit_method_rejected():
    with pytest.raises(ValueError, match="reinitialization.method"):
        ExperimentConfig.from_dict(_minimal({
            "reinitialization": {"method": "bogus"},
        }))


def test_invalid_structured_ppe_scheme_rejected():
    with pytest.raises(ValueError, match="schemes.ppe"):
        ExperimentConfig.from_dict(_minimal({
            "schemes": {"ppe": "ccd_lu"},
        }))


def test_invalid_structured_viscous_time_scheme_rejected():
    with pytest.raises(ValueError, match="schemes.viscous_time"):
        ExperimentConfig.from_dict(_minimal({
            "schemes": {"viscous_time": "rk4"},
        }))


def test_invalid_interface_tracking_method_rejected():
    with pytest.raises(ValueError, match="interface_tracking.method"):
        ExperimentConfig.from_dict(_minimal({
            "interface_tracking": {"method": "marker_particles"},
        }))


def test_disabled_interface_fitting_forces_uniform_grid():
    cfg = ExperimentConfig.from_dict({
        "grid": {
            "NX": 8, "NY": 8, "LX": 1.0, "LY": 1.0,
            "interface_fitting": {"enabled": False, "alpha": 2.0},
        },
        "physics": {"rho_l": 1.0, "rho_g": 1.0, "sigma": 0.0, "mu": 0.01},
        "run": {"T_final": 0.1, "cfl": 0.1},
    })
    assert cfg.grid.interface_fitting_enabled is False
    assert cfg.grid.interface_fitting_method == "none"
    assert cfg.grid.alpha_grid == 1.0


def test_invalid_interface_fitting_method_rejected():
    with pytest.raises(ValueError, match="interface_fitting.method"):
        ExperimentConfig.from_dict({
            "grid": {
                "NX": 8, "NY": 8, "LX": 1.0, "LY": 1.0,
                "interface_fitting": {"method": "spline_fit"},
            },
            "physics": {"rho_l": 1.0, "rho_g": 1.0, "sigma": 0.0, "mu": 0.01},
            "run": {"T_final": 0.1, "cfl": 0.1},
        })


def test_invalid_projection_mode_rejected():
    with pytest.raises(ValueError, match="projection.mode"):
        ExperimentConfig.from_dict(_minimal({
            "projection": {"mode": "bogus"},
        }))
