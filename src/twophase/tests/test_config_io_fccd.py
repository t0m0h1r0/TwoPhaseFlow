"""Canonical ch13 experiment YAML schema coverage."""

from __future__ import annotations

from copy import deepcopy

import pytest

from twophase.simulation.config_io import ExperimentConfig


def _deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _minimal(patch: dict | None = None) -> dict:
    raw = {
        "grid": {
            "cells": [8, 8],
            "domain": {"size": [1.0, 1.0], "boundary": "wall"},
            "interface_fitting": {
                "enabled": True,
                "method": "gaussian_levelset",
                "alpha": 1.0,
                "schedule": "static",
            },
            "interface_width": {"mode": "nominal", "base_factor": 1.5},
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 1.0, "mu": 0.01},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.0,
            "gravity": 0.0,
        },
        "run": {
            "time": {"final": 0.1, "cfl": 0.1},
            "reinitialization": {
                "method": "ridge_eikonal",
                "every": 2,
                "eps_scale": 1.0,
                "ridge_sigma_0": 3.0,
            },
            "interface_tracking": {"enabled": True, "method": "psi_direct"},
            "projection": {"mode": "standard"},
            "schemes": {
                "levelset_advection": "dissipative_ccd",
                "momentum_convection": "ccd",
                "ppe": "fvm_iterative",
                "surface_tension": "csf",
                "viscous_time": "explicit",
            },
        },
    }
    return _deep_update(raw, deepcopy(patch)) if patch else raw


def test_canonical_defaults_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal())
    assert cfg.grid.NX == 8
    assert cfg.grid.NY == 8
    assert cfg.grid.bc_type == "wall"
    assert cfg.physics.mu_l == 0.01
    assert cfg.physics.mu_g == 0.01
    assert cfg.run.advection_scheme == "dissipative_ccd"
    assert cfg.run.convection_scheme == "ccd"
    assert cfg.run.ppe_solver == "fvm_iterative"
    assert cfg.run.pressure_scheme == "fvm_matrixfree"


def test_canonical_structured_sections_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal({
        "grid": {
            "cells": [16, 12],
            "domain": {"size": [2.0, 1.0], "boundary": "periodic"},
            "interface_fitting": {"alpha": 2.0, "schedule": "every_3"},
            "interface_width": {"mode": "local", "base_factor": 1.7},
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 2.0, "mu": 0.03},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.5,
        },
        "run": {
            "time": {"final": 0.2, "cfl": 0.05, "print_every": 7},
            "reinitialization": {
                "eps_scale": 1.4,
                "ridge_sigma_0": 2.5,
            },
            "interface_tracking": {
                "method": "phi_primary",
                "redist_every": 5,
                "clip_factor": 10.0,
                "heaviside_eps_scale": 1.2,
            },
            "projection": {"mode": "consistent_iim", "face_flux_projection": True},
            "schemes": {
                "levelset_advection": "fccd_flux",
                "momentum_convection": "uccd6",
                "uccd6_sigma": 2.0e-3,
                "ppe": "fvm_direct",
                "surface_tension": "none",
                "viscous_time": "crank_nicolson",
            },
            "debug": {"step_diagnostics": True},
        },
        "output": {"snapshots": {"interval": 0.25}},
    }))
    assert cfg.grid.NX == 16
    assert cfg.grid.NY == 12
    assert cfg.grid.LX == 2.0
    assert cfg.grid.LY == 1.0
    assert cfg.grid.bc_type == "periodic"
    assert cfg.grid.alpha_grid == 2.0
    assert cfg.grid.grid_rebuild_freq == 3
    assert cfg.grid.use_local_eps is True
    assert cfg.physics.rho_l == 2.0
    assert cfg.physics.rho_g == 1.0
    assert cfg.physics.sigma == 0.5
    assert cfg.run.T_final == 0.2
    assert cfg.run.cfl == 0.05
    assert cfg.run.print_every == 7
    assert cfg.run.snap_interval == 0.25
    assert cfg.run.reinit_method == "ridge_eikonal"
    assert cfg.run.reinit_eps_scale == 1.4
    assert cfg.run.ridge_sigma_0 == 2.5
    assert cfg.run.interface_tracking_method == "phi_primary"
    assert cfg.run.phi_primary_redist_every == 5
    assert cfg.run.reproject_mode == "consistent_iim"
    assert cfg.run.face_flux_projection is True
    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "uccd6"
    assert cfg.run.uccd6_sigma == 2.0e-3
    assert cfg.run.ppe_solver == "fvm_direct"
    assert cfg.run.pressure_scheme == "fvm_spsolve"
    assert cfg.run.surface_tension_scheme == "none"
    assert cfg.run.cn_viscous is True
    assert cfg.run.debug_diagnostics is True


@pytest.mark.parametrize("adv", ["bogus", "ccd"])
def test_invalid_advection_scheme_rejected(adv: str):
    with pytest.raises(ValueError, match="levelset_advection"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"schemes": {"levelset_advection": adv}},
        }))


def test_invalid_convection_scheme_rejected():
    with pytest.raises(ValueError, match="momentum_convection"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"schemes": {"momentum_convection": "bogus"}},
        }))


def test_invalid_ppe_scheme_rejected():
    with pytest.raises(ValueError, match="schemes.ppe"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"schemes": {"ppe": "ccd_lu"}},
        }))


def test_invalid_viscous_time_scheme_rejected():
    with pytest.raises(ValueError, match="schemes.viscous_time"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"schemes": {"viscous_time": "rk4"}},
        }))


def test_invalid_interface_tracking_method_rejected():
    with pytest.raises(ValueError, match="interface_tracking.method"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"interface_tracking": {"method": "marker_particles"}},
        }))


def test_disabled_interface_fitting_forces_uniform_grid():
    cfg = ExperimentConfig.from_dict(_minimal({
        "grid": {"interface_fitting": {"enabled": False, "alpha": 2.0}},
    }))
    assert cfg.grid.interface_fitting_enabled is False
    assert cfg.grid.interface_fitting_method == "none"
    assert cfg.grid.alpha_grid == 1.0


def test_invalid_interface_fitting_method_rejected():
    with pytest.raises(ValueError, match="interface_fitting.method"):
        ExperimentConfig.from_dict(_minimal({
            "grid": {"interface_fitting": {"method": "spline_fit"}},
        }))


def test_invalid_projection_mode_rejected():
    with pytest.raises(ValueError, match="projection.mode"):
        ExperimentConfig.from_dict(_minimal({
            "run": {"projection": {"mode": "gfm"}},
        }))
