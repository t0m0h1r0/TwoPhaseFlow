"""Fail-closed parser tests for geometric cell-fraction state space."""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from twophase.simulation.ao_fast_runtime_contract import (
    build_ao_fast_runtime_contract,
    validate_ao_fast_checkpoint_arrays,
)
from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.config_state_space import parse_interface_state_space
from twophase.simulation.geometric_phase_runtime_gpu import (
    build_geometric_phase_state_gpu,
)
from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
from twophase.simulation.ns_step_state import NSStepRequest, NSStepState


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


def _ao_fast_checkpoint_arrays(cell_shape: tuple[int, int] = (8, 8)) -> dict:
    nx, ny = cell_shape
    node_shape = (nx + 1, ny + 1)
    return {
        "state/q": np.full(cell_shape, 0.25),
        "state/theta": np.full(cell_shape, 0.25),
        "state/phi": np.zeros(node_shape),
        "state/stratum/case_code": np.zeros(cell_shape, dtype=np.int16),
        "solver/transport_stage_ledger/epoch": np.asarray(3, dtype=np.int64),
        "solver/compatibility_projection_ledger/epoch": np.asarray(3, dtype=np.int64),
        "solver/p_prev_accel_face_components/count": np.asarray(2, dtype=np.int64),
        "solver/p_prev_accel_face_components/0": np.zeros((nx, ny + 1)),
        "solver/p_prev_accel_face_components/1": np.zeros((nx + 1, ny)),
        "solver/projected_face_components/count": np.asarray(2, dtype=np.int64),
        "solver/projected_face_components/0": np.zeros((nx, ny + 1)),
        "solver/projected_face_components/1": np.zeros((nx + 1, ny)),
    }


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


@pytest.mark.parametrize(
    "patch",
    [
        {
            "numerics": {
                "momentum": {
                    "terms": {
                        "surface_tension": {"source": "bundle_virtual_work"}
                    }
                }
            }
        },
        {
            "numerics": {
                "momentum": {
                    "capillary_force": {"source": "bundle_virtual_work"}
                }
            }
        },
        {
            "numerics": {
                "momentum": {
                    "terms": {
                        "surface_tension": {
                            "closed_interface": {
                                "endpoint": "geometric_cell_fraction",
                            }
                        }
                    }
                }
            }
        },
        {
            "numerics": {
                "momentum": {
                    "terms": {
                        "surface_tension": {
                            "closed_interface": {
                                "residual_contract": {
                                    "constraints": ["cell_volume"],
                                }
                            }
                        }
                    }
                }
            }
        },
    ],
)
def test_geometric_capillary_without_geometric_state_space_fails_closed(patch):
    with pytest.raises(ValueError, match="requires interface.state_space.kind"):
        ExperimentConfig.from_dict(_minimal(patch))


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


def test_valid_geometric_contract_builds_config_and_solver_runtime():
    raw = _geometric_raw()
    cfg = parse_interface_state_space(raw["interface"], raw["numerics"])
    assert cfg.scheme == "active_geometry_capillary"
    assert cfg.kind == "geometric_cell_fraction"
    assert cfg.projection_implementation == "active_cached"
    assert cfg.fallback_policy == "none"

    experiment_cfg = ExperimentConfig.from_dict(raw)
    assert experiment_cfg.interface_state_space.scheme == "active_geometry_capillary"
    assert experiment_cfg.interface_state_space.kind == "geometric_cell_fraction"
    assert experiment_cfg.run.advection_scheme == "geometric_swept_volume"
    assert experiment_cfg.run.interface_tracking_method == "q_cell_fraction"
    assert experiment_cfg.run.capillary_force_source == "bundle_virtual_work"
    contract = build_ao_fast_runtime_contract(experiment_cfg)
    assert contract.capillary_constraints == ("cell_volume",)
    assert contract.checkpoint_state_phase == "pre_step"

    solver = TwoPhaseNSSolver.from_config(experiment_cfg)
    assert solver._advection_scheme == "geometric_swept_volume"


def test_active_geometry_capillary_scheme_preset_expands_defaults():
    patch = _geometric_patch()
    patch["interface"]["state_space"] = {"scheme": "active_geometry_capillary"}
    raw = _minimal(patch)
    cfg = ExperimentConfig.from_dict(raw)

    assert cfg.interface_state_space.scheme == "active_geometry_capillary"
    assert cfg.interface_state_space.kind == "geometric_cell_fraction"
    assert cfg.interface_state_space.conserved_variable == "q"
    assert cfg.interface_state_space.projection_implementation == "active_cached"
    assert cfg.interface_state_space.fallback_policy == "none"
    solver = TwoPhaseNSSolver.from_config(cfg)
    assert solver._interface_tracking_method == "q_cell_fraction"
    assert solver._capillary_force_source == "bundle_virtual_work"


def test_geometric_runtime_rejects_active_projection_schedule():
    raw = _geometric_raw(
        {
            "interface": {
                "reinitialization": {
                    "algorithm": "compatibility_projection",
                    "schedule": {"every_steps": 1},
                }
            }
        }
    )
    experiment_cfg = ExperimentConfig.from_dict(raw)
    with pytest.raises(ValueError, match="active compatibility_projection"):
        build_ao_fast_runtime_contract(experiment_cfg)


def test_geometric_runtime_gpu_backend_fail_closes_uncertified_capillary_packet():
    try:
        import cupy  # noqa: F401
    except Exception:
        pytest.skip("CuPy is not importable")

    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "pressure_history": {
                        "form": "pressure_coordinate",
                        "extrapolation": "bdf2",
                    }
                }
            }
        }
    )
    experiment_cfg = ExperimentConfig.from_dict(raw)
    try:
        solver = TwoPhaseNSSolver.from_config(experiment_cfg)
    except RuntimeError as exc:
        pytest.skip(f"GPU backend unavailable: {exc}")
    if not solver.backend.is_gpu():
        pytest.skip("TWOPHASE_USE_GPU is not active")

    xp = solver.backend.xp
    zeros = xp.zeros((9, 9))
    x = xp.asarray(solver._grid.coords[0]).reshape((-1, 1))
    y = xp.asarray(solver._grid.coords[1]).reshape((1, -1))
    phi = y - (
        xp.asarray(0.47)
        + xp.asarray(0.05) * xp.cos(xp.asarray(4.0 * np.pi) * x)
    )
    solver._geometric_phase_state = (
        getattr(solver, "_geometric_phase_state", None)
        or build_geometric_phase_state_gpu(solver._grid, phi)
    )
    state = NSStepState.from_inputs(
        NSStepRequest(
            psi=zeros,
            u=zeros,
            v=zeros,
            dt=1.0e-4,
            rho_l=1.0,
            rho_g=1.0,
            sigma=1.0,
            mu=0.01,
        ),
        backend=solver.backend,
    )
    with pytest.raises(ValueError, match="GPU AO capillary fail-close") as excinfo:
        solver._advance_geometric_phase_stage(state)
    assert "pressure_history_mode='pressure_coordinate'" in str(excinfo.value)
    assert solver._last_geometric_runtime_material is not None
    assert solver._last_geometric_runtime_capillary_application is not None
    assert (
        solver._last_geometric_runtime_capillary.pressure_range_status
        == "gpu_diagonal_active_schur_approximation"
    )


def test_geometric_runtime_gpu_backend_sigma_zero_is_static_no_drive():
    try:
        import cupy  # noqa: F401
    except Exception:
        pytest.skip("CuPy is not importable")

    experiment_cfg = ExperimentConfig.from_dict(_geometric_raw())
    try:
        solver = TwoPhaseNSSolver.from_config(experiment_cfg)
    except RuntimeError as exc:
        pytest.skip(f"GPU backend unavailable: {exc}")
    if not solver.backend.is_gpu():
        pytest.skip("TWOPHASE_USE_GPU is not active")

    xp = solver.backend.xp
    zeros = xp.zeros((9, 9))
    x = xp.asarray(solver._grid.coords[0]).reshape((-1, 1))
    phi = xp.broadcast_to(x - xp.asarray(0.5), zeros.shape)
    solver._geometric_phase_state = build_geometric_phase_state_gpu(
        solver._grid,
        phi,
    )
    state = NSStepState.from_inputs(
        NSStepRequest(
            psi=zeros,
            u=zeros,
            v=zeros,
            dt=1.0e-4,
            rho_l=1.0,
            rho_g=1.0,
            sigma=0.0,
            mu=0.01,
        ),
        backend=solver.backend,
    )
    state = solver._advance_geometric_phase_stage(state)
    assert state.geometric_runtime_capillary.pressure_exact_static is True
    assert state.geometric_runtime_capillary.capillary_drive_present is False
    assert (
        state.conservative_transport_certificate["ao_static_downstream_unblocked"]
        is True
    )


def test_ao_fast_checkpoint_contract_validates_handoff_and_face_histories():
    validation = validate_ao_fast_checkpoint_arrays(
        _ao_fast_checkpoint_arrays(),
        cell_shape=(8, 8),
    )
    assert validation.cell_shape == (8, 8)
    assert validation.node_shape == (9, 9)
    assert validation.required_arrays[0] == "state/q"
    assert "solver/projected_face_components" in validation.face_history_prefixes


def test_ao_fast_checkpoint_contract_rejects_missing_q_state():
    arrays = _ao_fast_checkpoint_arrays()
    arrays.pop("state/q")
    with pytest.raises(ValueError, match="missing required array state/q"):
        validate_ao_fast_checkpoint_arrays(arrays, cell_shape=(8, 8))


def test_ao_fast_checkpoint_contract_rejects_cell_node_shape_mixup():
    arrays = _ao_fast_checkpoint_arrays()
    arrays["state/phi"] = np.zeros((8, 8))
    with pytest.raises(ValueError, match="state/phi"):
        validate_ao_fast_checkpoint_arrays(arrays, cell_shape=(8, 8))


def test_ao_fast_checkpoint_contract_rejects_bad_face_history_shape():
    arrays = _ao_fast_checkpoint_arrays()
    arrays["solver/projected_face_components/1"] = np.zeros((8, 8))
    with pytest.raises(ValueError, match="face history"):
        validate_ao_fast_checkpoint_arrays(arrays, cell_shape=(8, 8))


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
