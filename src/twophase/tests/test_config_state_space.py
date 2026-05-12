"""Fail-closed parser tests for geometric cell-fraction state space."""

from __future__ import annotations

from copy import deepcopy

import pytest

from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.config_state_space import parse_interface_state_space
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver


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
            "distribution": {"schedule": "static"},
        },
        "interface": {
            "thickness": {"mode": "nominal", "base_factor": 1.5},
            "geometry": {"curvature": {"method": "psi_direct_filtered"}},
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
        "run": {"time": {"final": 0.1, "cfl": 1.0}},
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
                    },
                },
            },
        },
    }
    return _deep_update(raw, deepcopy(patch)) if patch else raw


def _geometric_patch() -> dict:
    return {
        "interface": {
            "state_space": {
                "kind": "geometric_cell_fraction",
                "conserved_variable": "q",
                "normalized_view": "theta",
                "gauge": {"variable": "phi", "trace": "p1_levelset"},
                "compatibility": {
                    "constraint": "hard_cell_volume",
                    "units": "physical_volume",
                    "projection": {
                        "implementation": "active_cached",
                        "dense_reference": "test_only",
                        "gpu_contract": {
                            "required": True,
                            "active_storage": "struct_of_arrays",
                            "inner_host_transfers": "forbidden",
                            "dense_runtime_fallback": "forbidden",
                            "record_kernel_counters": True,
                        },
                        "method": "fixed_stratum_schur",
                        "metric": "screened_gauge_hodge",
                        "fail_close": True,
                        "trust_region": "sign_margin",
                        "residual_tolerance": 1.0e-11,
                        "condition_gate": "fail_close",
                        "support_budget": {
                            "max_active_ratio": 0.25,
                            "max_support_stream_ratio": 0.25,
                            "max_epoch_growth_ratio": 1.5,
                            "on_overrun": "fail_close",
                        },
                        "solver": {
                            "primary": "active_pcg_newton",
                            "accelerators": {
                                "dc_candidate": {
                                    "enabled": True,
                                    "role": "proposal_only",
                                    "on_reject": "discard_candidate",
                                },
                            },
                            "fallback": {"policy": "none"},
                        },
                    },
                },
            },
            "reinitialization": {
                "algorithm": "none",
                "schedule": {"every_steps": 0},
                "profile": {"eps_scale": 1.0, "ridge_sigma_0": 3.0},
            },
        },
        "numerics": {
            "interface": {
                "transport": {
                    "variable": "q",
                    "spatial": "geometric_swept_volume",
                    "time_integrator": "tvd_rk3",
                    "boundedness": "certified",
                    "fail_close": True,
                },
                "tracking": {"primary": "q"},
            },
            "momentum": {
                "form": "conservative_common_flux",
                "terms": {
                    "surface_tension": {
                        "gradient": "none",
                        "formulation": "pressure_jump",
                        "source": "bundle_virtual_work",
                        "closed_interface": {
                            "endpoint": "geometric_cell_fraction",
                            "residual_contract": {
                                "metric": "pressure_adjoint",
                                "constraints": ["cell_volume"],
                                "fail_close": True,
                            },
                        },
                    },
                },
            },
            "projection": {
                "poisson": {
                    "operator": {
                        "discretization": "fccd",
                        "coefficient": "phase_separated",
                        "interface_coupling": "affine_jump",
                        "pressure_force_contract": "variational_adjoint",
                        "scalar_operator_pairing": "variational_operator",
                        "capillary_reaction_projection": "pressure_component_hodge",
                    },
                },
            },
        },
    }


def _geometric_raw(patch: dict | None = None) -> dict:
    raw = _minimal(_geometric_patch())
    return _deep_update(raw, deepcopy(patch)) if patch else raw


def test_legacy_diffuse_state_space_still_parses():
    cfg = ExperimentConfig.from_dict(_minimal())
    assert cfg.interface_state_space.kind == "diffuse_cls"
    assert cfg.run.advection_scheme == "dissipative_ccd"


def test_q_transport_without_geometric_state_space_fails_closed():
    with pytest.raises(ValueError, match="requires interface.state_space.kind"):
        ExperimentConfig.from_dict(
            _minimal({"numerics": {"interface": {"transport": {"variable": "q"}}}})
        )


def test_q_tracking_without_geometric_state_space_fails_closed():
    with pytest.raises(ValueError, match="requires interface.state_space.kind"):
        ExperimentConfig.from_dict(
            _minimal({"numerics": {"interface": {"tracking": {"primary": "q"}}}})
        )


def test_reinitialization_none_requires_zero_schedule():
    with pytest.raises(ValueError, match="algorithm='none' requires"):
        ExperimentConfig.from_dict(
            _minimal(
                {
                    "interface": {
                        "reinitialization": {
                            "algorithm": "none",
                            "schedule": {"every_steps": 1},
                        },
                    },
                }
            )
        )


def test_valid_geometric_contract_builds_config_but_solver_runtime_fails_closed():
    raw = _geometric_raw()
    cfg = parse_interface_state_space(raw["interface"], raw["numerics"])
    assert cfg.kind == "geometric_cell_fraction"
    assert cfg.projection_implementation == "active_cached"
    assert cfg.fallback_policy == "none"

    experiment_cfg = ExperimentConfig.from_dict(raw)
    assert experiment_cfg.interface_state_space.kind == "geometric_cell_fraction"
    assert experiment_cfg.run.advection_scheme == "geometric_swept_volume"
    assert experiment_cfg.run.interface_tracking_method == "q_cell_fraction"
    assert experiment_cfg.run.capillary_force_source == "bundle_virtual_work"

    with pytest.raises(ValueError, match="runtime adapter is disabled"):
        TwoPhaseNSSolver.from_config(experiment_cfg)


@pytest.mark.parametrize(
    ("patch", "match"),
    [
        (
            {
                "interface": {
                    "state_space": {
                        "compatibility": {
                            "projection": {"implementation": "dense_reference"}
                        }
                    }
                }
            },
            "projection.implementation",
        ),
        (
            {
                "interface": {
                    "state_space": {
                        "compatibility": {
                            "projection": {"dense_reference": "runtime"}
                        }
                    }
                }
            },
            "dense_reference",
        ),
        (
            {
                "interface": {
                    "state_space": {
                        "compatibility": {
                            "projection": {"gpu_contract": {"required": False}}
                        }
                    }
                }
            },
            "gpu_contract.required",
        ),
        (
            {
                "interface": {
                    "state_space": {
                        "compatibility": {
                            "projection": {"condition_gate": "diagnostic"}
                        }
                    }
                }
            },
            "condition_gate",
        ),
        (
            {
                "interface": {
                    "state_space": {
                        "compatibility": {
                            "projection": {
                                "solver": {"fallback": {"policy": "auto"}}
                            }
                        }
                    }
                }
            },
            "fallback.policy",
        ),
    ],
)
def test_geometric_state_space_negative_parser_gates(patch, match):
    raw = _geometric_raw(patch)
    with pytest.raises(ValueError, match=match):
        ExperimentConfig.from_dict(raw)


def test_explicit_chain_requires_complete_transition_metadata():
    raw = _geometric_raw(
        {
            "interface": {
                "state_space": {
                    "compatibility": {
                        "projection": {
                            "solver": {
                                "primary": "residual_monotone_dc",
                                "fallback": {
                                    "policy": "explicit_chain",
                                    "chain": [
                                        {
                                            "from": "residual_monotone_dc",
                                            "to": "active_pcg_newton",
                                            "triggers": ["trust_region_exhausted"],
                                        }
                                    ],
                                },
                            }
                        }
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="record_as"):
        ExperimentConfig.from_dict(raw)
