"""Readable ch13 YAML schema coverage."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

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
            "geometry": {"curvature": {"method": "psi_direct_hfe"}},
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
            "time": {
                "interface_transport": "tvd_rk3",
                "momentum_predictor": "projection_predictor_corrector",
            },
            "interface": {
                "transport": {
                    "variable": "psi",
                    "spatial": "dissipative_ccd",
                },
                "tracking": {"primary": "psi"},
            },
            "momentum": {
                "form": "primitive_velocity",
                "terms": {
                    "convection": {"spatial": "ccd", "time_integrator": "ab2"},
                    "pressure": {"gradient": "ccd"},
                    "viscosity": {"spatial": "ccd", "time_integrator": "crank_nicolson"},
                    "surface_tension": {
                        "gradient": "ccd",
                        "formulation": "csf",
                    },
                },
            },
            "projection": {
                "mode": "standard",
                "poisson": {
                    "operator": {
                        "discretization": "fvm",
                        "coefficient": "phase_density",
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
    assert cfg.run.convection_time_scheme == "ab2"
    assert cfg.run.ppe_solver == "fvm_iterative"
    assert cfg.run.ppe_iteration_method == "gmres"
    assert cfg.run.ppe_preconditioner == "line_pcr"
    assert cfg.run.momentum_gradient_scheme == "ccd"
    assert cfg.run.pressure_gradient_scheme == "ccd"
    assert cfg.run.surface_tension_gradient_scheme == "ccd"
    assert cfg.run.viscous_spatial_scheme == "ccd_bulk"


def test_ch13_fccd_hfe_uccd_yaml_loads_execution_stack():
    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)

    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "uccd6"
    assert cfg.run.convection_time_scheme == "imex_bdf2"
    assert cfg.run.viscous_spatial_scheme == "ccd_bulk"
    assert cfg.run.viscous_time_scheme == "implicit_bdf2"
    assert cfg.run.pressure_gradient_scheme == "fccd_flux"
    assert cfg.run.surface_tension_gradient_scheme == "none"
    assert cfg.run.surface_tension_scheme == "pressure_jump"
    assert cfg.run.reinit_method == "ridge_eikonal"
    assert cfg.run.reproject_mode == "gfm"
    assert cfg.run.ppe_solver == "fccd_iterative"
    assert cfg.run.pressure_scheme == "fccd_matrixfree"
    assert cfg.run.ppe_coefficient_scheme == "phase_separated"
    assert cfg.run.ppe_interface_coupling_scheme == "jump_decomposition"
    assert cfg.run.ppe_defect_correction is True
    assert cfg.grid.grid_rebuild_freq == 0
    assert cfg.run.reinit_every == 4
    assert cfg.run.interface_tracking_method == "psi_direct"
    assert cfg.run.phi_primary_transport is False


def test_ch13_rising_bubble_water_air_yaml_loads_execution_stack():
    path = (
        Path(__file__).resolve().parents[3]
        / "experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml"
    )
    cfg = ExperimentConfig.from_yaml(path)

    assert cfg.grid.NX == 128
    assert cfg.grid.NY == 256
    assert cfg.grid.LX == 1.0
    assert cfg.grid.LY == 2.0
    assert cfg.grid.grid_rebuild_freq == 0
    assert cfg.physics.g_acc == pytest.approx(0.001)
    assert cfg.run.reinit_every == 4
    assert cfg.run.interface_tracking_method == "psi_direct"
    assert cfg.run.phi_primary_transport is False
    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "uccd6"
    assert cfg.run.convection_time_scheme == "imex_bdf2"
    assert cfg.run.viscous_time_scheme == "implicit_bdf2"
    assert cfg.run.pressure_scheme == "fccd_matrixfree"


def test_fccd_ppe_discretization_maps_to_fccd_solver():
    cfg = ExperimentConfig.from_dict(_minimal({
        "numerics": {
            "projection": {
                "poisson": {
                    "operator": {"discretization": "fccd", "coefficient": "phase_density"},
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
        },
    }))

    assert cfg.run.ppe_solver == "fccd_iterative"
    assert cfg.run.pressure_scheme == "fccd_matrixfree"


def test_phase_separated_coefficient_maps_to_gfm_projection():
    raw = _minimal({
        "numerics": {
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_separated",
                    },
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_separated",
                        "interface_coupling": "jump_decomposition",
                    },
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
        },
    })
    del raw["numerics"]["projection"]["mode"]
    cfg = ExperimentConfig.from_dict(raw)

    assert cfg.run.ppe_solver == "fccd_iterative"
    assert cfg.run.pressure_scheme == "fccd_matrixfree"
    assert cfg.run.ppe_coefficient_scheme == "phase_separated"
    assert cfg.run.ppe_interface_coupling_scheme == "jump_decomposition"
    assert cfg.run.reproject_mode == "gfm"


def test_phase_density_rejects_jump_decomposition_coupling():
    raw = _minimal({
        "numerics": {
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_density",
                        "interface_coupling": "jump_decomposition",
                    },
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
        },
    })

    with pytest.raises(ValueError, match="phase_density"):
        ExperimentConfig.from_dict(raw)


def test_pressure_jump_rejects_body_force_gradient():
    raw = _minimal({
        "numerics": {
            "momentum": {
                "terms": {
                    "surface_tension": {
                        "gradient": "fccd",
                        "formulation": "pressure_jump",
                    },
                },
            },
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_separated",
                        "interface_coupling": "jump_decomposition",
                    },
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
        },
    })

    with pytest.raises(ValueError, match="must be omitted"):
        ExperimentConfig.from_dict(raw)


def test_pressure_jump_requires_phase_separated_ppe():
    raw = _minimal({
        "numerics": {
            "momentum": {
                "terms": {
                    "surface_tension": {"formulation": "pressure_jump"},
                },
            },
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_density",
                    },
                    "solver": {"kind": "iterative", "preconditioner": "none"},
                },
            },
        },
    })

    with pytest.raises(ValueError, match="phase_separated"):
        ExperimentConfig.from_dict(raw)


def test_fccd_ppe_rejects_direct_solver_kind():
    with pytest.raises(ValueError, match="does not support"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {
                        "operator": {"discretization": "fccd", "coefficient": "phase_density"},
                        "solver": {"kind": "direct"},
                    },
                },
            },
        }))


def test_projection_coefficient_is_required_for_phase_ppe():
    raw = _minimal()
    del raw["numerics"]["projection"]["poisson"]["operator"]["coefficient"]
    with pytest.raises(ValueError, match="coefficient.*required"):
        ExperimentConfig.from_dict(raw)


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
            "geometry": {"curvature": {"cap": 20.0}},
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
                    "spatial": "fccd",
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
                        "time_integrator": "ab2",
                        "uccd6_sigma": 2.0e-3,
                    },
                    "pressure": {"spatial": "projection_consistent"},
                    "viscosity": {"spatial": "ccd", "time_integrator": "crank_nicolson"},
                    "surface_tension": {"gradient": "fccd", "formulation": "none"},
                },
            },
            "projection": {
                "mode": "iim",
                "face_flux_projection": True,
                "preserve_projected_faces": True,
                "projection_consistent_buoyancy": True,
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
    assert cfg.run.reproject_mode == "iim"
    assert cfg.run.face_flux_projection is True
    assert cfg.run.preserve_projected_faces is True
    assert cfg.run.projection_consistent_buoyancy is True
    assert cfg.run.advection_scheme == "fccd_flux"
    assert cfg.run.convection_scheme == "uccd6"
    assert cfg.run.uccd6_sigma == 2.0e-3
    assert cfg.run.ppe_solver == "fvm_direct"
    assert cfg.run.pressure_scheme == "fvm_spsolve"
    assert cfg.run.ppe_iteration_method == "none"
    assert cfg.run.ppe_preconditioner == "none"
    assert cfg.run.ppe_max_iterations == 0
    assert cfg.run.surface_tension_scheme == "none"
    assert cfg.run.pressure_gradient_scheme == "ccd"
    assert cfg.run.surface_tension_gradient_scheme == "fccd_flux"
    assert cfg.run.momentum_gradient_scheme == "ccd"
    assert cfg.run.kappa_max == 20.0
    assert cfg.run.cn_viscous is True
    assert cfg.run.viscous_spatial_scheme == "ccd_bulk"
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


def test_imex_bdf2_requires_implicit_bdf2_viscosity():
    with pytest.raises(ValueError, match="viscosity.time_integrator"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "momentum": {
                    "terms": {
                        "convection": {"time_integrator": "imex_bdf2"},
                    },
                },
            },
        }))


def test_implicit_bdf2_viscosity_requires_imex_bdf2_convection():
    with pytest.raises(ValueError, match="convection.time_integrator"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "momentum": {
                    "terms": {
                        "viscosity": {"time_integrator": "implicit_bdf2"},
                    },
                },
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
            "numerics": {"projection": {"mode": "sharp_interface"}},
        }))


@pytest.mark.parametrize("extra_key", ["pcr_stages", "c_tau"])
def test_pcr_stages_and_c_tau_rejected_for_non_line_pcr(extra_key: str):
    with pytest.raises(ValueError, match=f"{extra_key}.*line_pcr"):
        ExperimentConfig.from_dict(_minimal({
            "numerics": {
                "projection": {
                    "poisson": {
                        "solver": {
                            "kind": "iterative",
                            "preconditioner": "jacobi",
                            extra_key: 4,
                        },
                    },
                },
            },
        }))


def test_gradient_key_reads_pressure_and_surface_tension():
    cfg = ExperimentConfig.from_dict(_minimal({
        "numerics": {
            "momentum": {
                "terms": {
                    "pressure": {"gradient": "fccd"},
                    "surface_tension": {"gradient": "fccd_nodal", "formulation": "csf"},
                },
            },
        },
    }))
    assert cfg.run.pressure_gradient_scheme == "fccd_flux"
    assert cfg.run.surface_tension_gradient_scheme == "fccd_nodal"


def test_fractional_step_algorithm_alias():
    cfg = ExperimentConfig.from_dict(_minimal({
        "numerics": {"time": {"algorithm": "fractional_step"}},
    }))
    assert cfg.run.reproject_mode == "legacy"
