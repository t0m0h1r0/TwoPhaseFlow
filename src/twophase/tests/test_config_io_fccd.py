"""Readable ch13 YAML schema coverage."""

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
        },
        "interface": {
            "geometry": {
                "fitting": {
                    "enabled": True,
                    "method": "gaussian_levelset",
                    "alpha": 1.0,
                    "schedule": "static",
                },
                "width": {"mode": "nominal", "base_factor": 1.5},
            },
            "tracking": {"enabled": True, "primary": "psi"},
            "reinitialization": {
                "method": "ridge_eikonal",
                "every": 2,
                "eps_scale": 1.0,
                "ridge_sigma_0": 3.0,
            },
        },
        "physics": {
            "phases": {
                "liquid": {"rho": 1.0, "mu": 0.01},
                "gas": {"rho": 1.0, "mu": 0.01},
            },
            "surface_tension": 0.0,
            "gravity": 0.0,
        },
        "run": {"time": {"final": 0.1, "cfl": 0.1}},
        "numerics": {
            "terms": {
                "interface_transport": {
                    "spatial": "dissipative_ccd",
                    "time": "explicit",
                },
                "momentum_advection": {
                    "form": "primitive_velocity",
                    "spatial": "ccd",
                    "time": "explicit",
                },
                "viscosity": {"spatial": "ccd", "time": "explicit"},
                "surface_tension": {
                    "model": "csf",
                    "curvature": "psi_direct_hfe",
                    "force_gradient": "projection_consistent",
                },
                "pressure_projection": {
                    "mode": "standard",
                    "solver": {
                        "kind": "iterative",
                        "method": "gmres",
                        "tolerance": 1.0e-8,
                        "max_iterations": 500,
                        "restart": 80,
                        "preconditioner": "line_pcr",
                        "pcr_stages": 4,
                        "c_tau": 2.0,
                    },
                },
            },
        },
    }
    return _deep_update(raw, deepcopy(patch)) if patch else raw


def test_readable_defaults_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal())
    assert cfg.grid.NX == 8
    assert cfg.grid.NY == 8
    assert cfg.physics.mu_l == 0.01
    assert cfg.physics.mu_g == 0.01
    assert cfg.run.advection_scheme == "dissipative_ccd"
    assert cfg.run.convection_scheme == "ccd"
    assert cfg.run.ppe_solver == "fvm_iterative"
    assert cfg.run.ppe_iteration_method == "gmres"
    assert cfg.run.ppe_preconditioner == "line_pcr"


def test_readable_structured_sections_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal({
        "grid": {
            "cells": [16, 12],
            "domain": {"size": [2.0, 1.0], "boundary": "periodic"},
        },
        "interface": {
            "geometry": {
                "fitting": {"alpha": 2.0, "schedule": "every_3"},
                "width": {"mode": "local", "base_factor": 1.7},
            },
            "tracking": {
                "primary": "phi",
                "redist_every": 5,
                "clip_factor": 10.0,
                "heaviside_eps_scale": 1.2,
            },
            "reinitialization": {
                "eps_scale": 1.4,
                "ridge_sigma_0": 2.5,
            },
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
            "debug": {"step_diagnostics": True},
        },
        "numerics": {
            "terms": {
                "interface_transport": {"spatial": "fccd_flux"},
                "momentum_advection": {
                    "spatial": "uccd6",
                    "uccd6_sigma": 2.0e-3,
                },
                "viscosity": {"time": "crank_nicolson"},
                "surface_tension": {
                    "model": "none",
                    "curvature_cap": 20.0,
                },
                "pressure_projection": {
                    "mode": "consistent_iim",
                    "face_flux_projection": True,
                    "solver": {
                        "kind": "direct",
                        "method": "gmres",
                        "preconditioner": "none",
                        "max_iterations": 50,
                    },
                },
            },
        },
        "output": {"snapshots": {"interval": 0.25}},
    }))
    assert cfg.grid.NX == 16
    assert cfg.grid.NY == 12
    assert cfg.grid.alpha_grid == 2.0
    assert cfg.grid.grid_rebuild_freq == 3
    assert cfg.grid.use_local_eps is True
    assert cfg.physics.rho_l == 2.0
    assert cfg.physics.rho_g == 1.0
    assert cfg.physics.sigma == 0.5
    assert cfg.run.T_final == 0.2
    assert cfg.run.snap_interval == 0.25
    assert cfg.run.reinit_eps_scale == 1.4
    assert cfg.run.ridge_sigma_0 == 2.5
    assert cfg.run.interface_tracking_method == "phi_primary"
    assert cfg.run.reproject_mode == "consistent_iim"
    assert cfg.run.face_flux_projection is True
    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "uccd6"
    assert cfg.run.uccd6_sigma == 2.0e-3
    assert cfg.run.ppe_solver == "fvm_direct"
    assert cfg.run.pressure_scheme == "fvm_spsolve"
    assert cfg.run.ppe_preconditioner == "none"
    assert cfg.run.ppe_max_iterations == 50
    assert cfg.run.surface_tension_scheme == "none"
    assert cfg.run.kappa_max == 20.0
    assert cfg.run.cn_viscous is True
    assert cfg.run.debug_diagnostics is True


@pytest.mark.parametrize("adv", ["bogus", "ccd"])
def test_invalid_interface_transport_scheme_rejected(adv: str):
    with pytest.raises(ValueError, match="interface_transport.spatial"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"terms": {"interface_transport": {"spatial": adv}}},
        }))


def test_invalid_momentum_scheme_rejected():
    with pytest.raises(ValueError, match="momentum_advection.spatial"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"terms": {"momentum_advection": {"spatial": "bogus"}}},
        }))


def test_invalid_ppe_solver_kind_rejected():
    with pytest.raises(ValueError, match="pressure_projection.solver.kind"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "terms": {
                    "pressure_projection": {"solver": {"kind": "ccd_lu"}},
                },
            },
        }))


def test_invalid_ppe_iteration_method_rejected():
    with pytest.raises(ValueError, match="pressure_projection.solver.method"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "terms": {
                    "pressure_projection": {"solver": {"method": "lgmres"}},
                },
            },
        }))


def test_invalid_viscous_time_scheme_rejected():
    with pytest.raises(ValueError, match="viscosity.time"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"terms": {"viscosity": {"time": "rk4"}}},
        }))


def test_invalid_interface_tracking_primary_rejected():
    with pytest.raises(ValueError, match="interface.tracking.primary"):
        ExperimentConfig.from_dict(_minimal({
            "interface": {"tracking": {"primary": "marker_particles"}},
        }))


def test_disabled_interface_fitting_forces_uniform_grid():
    cfg = ExperimentConfig.from_dict(_minimal({
        "interface": {"geometry": {"fitting": {"enabled": False, "alpha": 2.0}}},
    }))
    assert cfg.grid.interface_fitting_enabled is False
    assert cfg.grid.interface_fitting_method == "none"
    assert cfg.grid.alpha_grid == 1.0


def test_invalid_interface_fitting_method_rejected():
    with pytest.raises(ValueError, match="interface.geometry.fitting.method"):
        ExperimentConfig.from_dict(_minimal({
            "interface": {"geometry": {"fitting": {"method": "spline_fit"}}},
        }))


def test_invalid_projection_mode_rejected():
    with pytest.raises(ValueError, match="pressure_projection.mode"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"terms": {"pressure_projection": {"mode": "gfm"}}},
        }))
