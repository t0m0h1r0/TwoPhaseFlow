"""Readable ch13 YAML schema coverage."""

from __future__ import annotations

from copy import deepcopy

import pytest

from twophase.simulation.config_io import ExperimentConfig


def _deep_update(base: dict, patch: dict) -> dict:
    for key, value in patch.items():
        if key == "solver":
            base[key] = value
        elif isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _minimal(patch: dict | None = None) -> dict:
    raw = {
        "grid": {
            "cells": [8, 8],
            "domain": {"size": [1.0, 1.0], "boundary": "wall"},
            "distribution": {
                "type": "interface_fitted",
                "method": "gaussian_levelset",
                "alpha": 1.0,
                "schedule": "static",
            },
        },
        "interface": {
            "thickness": {"mode": "nominal", "base_factor": 1.5},
            "reinitialization": {
                "algorithm": "ridge_eikonal",
                "schedule": {"every_steps": 2},
                "profile": {"eps_scale": 1.0, "ridge_sigma_0": 3.0},
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
            "time": {"default_integrator": "forward_euler"},
            "interface": {
                "transport": {
                    "variable": "psi",
                    "spatial": "dissipative_ccd",
                },
                "tracking": {"enabled": True, "primary": "psi"},
            },
            "momentum": {
                "form": "primitive_velocity",
                "terms": {
                    "convection": {"spatial": "ccd", "time_integrator": "forward_euler"},
                    "pressure": {
                        "gradient": "projection_consistent",
                        "balanced_with": "surface_tension",
                    },
                    "viscosity": {"spatial": "ccd", "time_integrator": "forward_euler"},
                    "surface_tension": {
                        "enabled": True,
                        "model": "csf",
                        "time_integrator": "forward_euler",
                        "curvature": "psi_direct_hfe",
                        "gradient": "projection_consistent",
                        "balanced_with": "pressure",
                    },
                    "gravity": {"enabled": False},
                },
            },
            "projection": {
                "mode": "standard",
                "poisson": {
                    "operator": {
                        "discretization": "fvm",
                        "coefficient": "variable_density",
                    },
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


def test_iterative_ppe_accepts_jacobi_preconditioner():
    cfg = ExperimentConfig.from_dict(_minimal({
        "numerics": {
            "projection": {
                "poisson": {
                    "solver": {
                        "kind": "iterative",
                        "method": "gmres",
                        "preconditioner": "jacobi",
                    },
                },
            },
        },
    }))

    assert cfg.run.ppe_preconditioner == "jacobi"


def test_readable_structured_sections_round_trip():
    cfg = ExperimentConfig.from_dict(_minimal({
        "grid": {
            "cells": [16, 12],
            "domain": {"size": [2.0, 1.0], "boundary": "periodic"},
            "distribution": {"alpha": 2.0, "schedule": "every_3"},
        },
        "interface": {
            "thickness": {"mode": "local", "base_factor": 1.7},
            "reinitialization": {
                "profile": {
                    "eps_scale": 1.4,
                    "ridge_sigma_0": 2.5,
                },
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
            "interface": {
                "transport": {
                    "spatial": "fccd_flux",
                },
                "tracking": {
                        "primary": "phi",
                        "redistance": {
                            "schedule": {"every_steps": 5},
                            "clip_factor": 10.0,
                            "heaviside_eps_scale": 1.2,
                        },
                },
            },
            "momentum": {
                "terms": {
                    "convection": {
                        "spatial": "uccd6",
                        "uccd6_sigma": 2.0e-3,
                    },
                    "viscosity": {"time_integrator": "crank_nicolson"},
                    "surface_tension": {
                        "model": "none",
                        "curvature_cap": 20.0,
                    },
                },
            },
            "projection": {
                "mode": "consistent_iim",
                "face_flux_projection": True,
                "poisson": {
                    "operator": {"discretization": "fvm"},
                    "solver": {"kind": "direct"},
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
    assert cfg.run.ppe_iteration_method == "none"
    assert cfg.run.ppe_preconditioner == "none"
    assert cfg.run.ppe_max_iterations == 0
    assert cfg.run.surface_tension_scheme == "none"
    assert cfg.run.kappa_max == 20.0
    assert cfg.run.cn_viscous is True
    assert cfg.run.debug_diagnostics is True


@pytest.mark.parametrize("adv", ["bogus", "ccd"])
def test_invalid_interface_transport_scheme_rejected(adv: str):
    with pytest.raises(ValueError, match="interface.transport.spatial"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"interface": {"transport": {"spatial": adv}}},
        }))


def test_invalid_momentum_scheme_rejected():
    with pytest.raises(ValueError, match="momentum.terms.convection.spatial"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "momentum": {"terms": {"convection": {"spatial": "bogus"}}},
            },
        }))


def test_invalid_ppe_solver_kind_rejected():
    with pytest.raises(ValueError, match="projection.poisson.solver.kind"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {"poisson": {"solver": {"kind": "ccd_lu"}}},
            },
        }))


def test_invalid_ppe_iteration_method_rejected():
    with pytest.raises(ValueError, match="projection.poisson.solver.method"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {"solver": {"kind": "iterative", "method": "lgmres"}},
                },
            },
        }))


def test_direct_ppe_rejects_iterative_options():
    with pytest.raises(ValueError, match="does not accept iterative options"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {
                        "solver": {"kind": "direct", "method": "gmres"},
                    },
                },
            },
        }))


def test_defect_correction_ppe_parses_base_solver():
    cfg = ExperimentConfig.from_dict(_minimal({
        "numerics": {
            "projection": {
                "poisson": {
                    "solver": {
                        "kind": "defect_correction",
                        "corrections": {
                            "max_iterations": 3,
                            "tolerance": 1.0e-7,
                            "relaxation": 0.8,
                        },
                        "base_solver": {
                            "kind": "iterative",
                            "method": "gmres",
                            "tolerance": 1.0e-6,
                            "max_iterations": 40,
                            "preconditioner": "none",
                        },
                    },
                },
            },
        },
    }))
    assert cfg.run.ppe_defect_correction is True
    assert cfg.run.ppe_solver == "fvm_iterative"
    assert cfg.run.ppe_preconditioner == "none"
    assert cfg.run.ppe_dc_max_iterations == 3
    assert cfg.run.ppe_dc_tolerance == 1.0e-7
    assert cfg.run.ppe_dc_relaxation == 0.8


def test_defect_correction_ppe_requires_base_solver():
    with pytest.raises(ValueError, match="requires .*base_solver"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {"solver": {"kind": "defect_correction"}},
                },
            },
        }))


def test_non_dc_ppe_rejects_base_solver():
    with pytest.raises(ValueError, match="base_solver is only valid"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {
                        "solver": {
                            "kind": "iterative",
                            "base_solver": {"kind": "direct"},
                        },
                    },
                },
            },
        }))


def test_invalid_viscous_time_scheme_rejected():
    with pytest.raises(ValueError, match="viscosity.time_integrator"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "momentum": {"terms": {"viscosity": {"time_integrator": "rk4"}}},
            },
        }))


def test_invalid_interface_tracking_primary_rejected():
    with pytest.raises(ValueError, match="interface.tracking.primary"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "interface": {"tracking": {"primary": "marker_particles"}},
            },
        }))


def test_invalid_tracking_redistance_frequency_rejected():
    with pytest.raises(ValueError, match="interface.tracking.redistance.schedule.every_steps"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "interface": {
                        "tracking": {
                            "redistance": {"schedule": {"every_steps": 0}},
                        },
                },
            },
        }))


def test_disabled_interface_fitting_forces_uniform_grid():
    cfg = ExperimentConfig.from_dict(_minimal({
        "grid": {"distribution": {"type": "uniform", "method": "none", "alpha": 2.0}},
    }))
    assert cfg.grid.interface_fitting_enabled is False
    assert cfg.grid.interface_fitting_method == "none"
    assert cfg.grid.alpha_grid == 1.0


def test_invalid_interface_fitting_method_rejected():
    with pytest.raises(ValueError, match="grid.distribution.method"):
        ExperimentConfig.from_dict(_minimal({
            "grid": {"distribution": {"method": "spline_fit"}},
        }))


def test_invalid_projection_mode_rejected():
    with pytest.raises(ValueError, match="projection.mode"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {"projection": {"mode": "gfm"}},
        }))
