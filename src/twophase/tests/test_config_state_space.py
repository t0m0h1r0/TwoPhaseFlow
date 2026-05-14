"""Fail-closed parser tests for geometric cell-fraction state space."""

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import numpy as np
import pytest

from twophase.simulation.ao_fast_runtime_contract import (
    build_ao_fast_runtime_contract,
    validate_ao_fast_checkpoint_arrays,
)
from twophase.simulation.config_io import ExperimentConfig
from twophase.simulation.config_state_space import parse_interface_state_space
from twophase.simulation.geometric_phase_runtime import (
    GeometricRuntimeCapillaryApplicationState,
    validate_geometric_runtime_capillary_application_admitted,
)
from twophase.simulation.geometric_phase_runtime_gpu import (
    build_geometric_phase_state_gpu,
)
from twophase.simulation.ns_solver_builder import build_solver_init_options
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
            "state_space": "active_geometry_capillary",
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


def test_state_space_scheme_kind_conflict_fails_closed():
    raw = _minimal(
        {
            "interface": {
                "state_space": {
                    "scheme": "diffuse_cls",
                    "kind": "geometric_cell_fraction",
                }
            }
        }
    )

    with pytest.raises(ValueError, match="must not be combined"):
        ExperimentConfig.from_dict(raw)


def test_q_transport_without_geometric_state_space_fails_closed():
    with pytest.raises(ValueError, match="requires interface.state_space"):
        ExperimentConfig.from_dict(
            _minimal({"numerics": {"interface": {"transport": {"variable": "q"}}}})
        )


def test_q_tracking_without_geometric_state_space_fails_closed():
    with pytest.raises(ValueError, match="requires interface.state_space"):
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
    with pytest.raises(ValueError, match="requires interface.state_space"):
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
    assert cfg.active_projection_solver_scheme == "pcg"
    assert cfg.active_projection_primary == "active_pcg_newton"
    assert cfg.active_projection_pcg_tolerance == pytest.approx(1.0e-12)

    experiment_cfg = ExperimentConfig.from_dict(raw)
    assert experiment_cfg.interface_state_space.scheme == "active_geometry_capillary"
    assert experiment_cfg.interface_state_space.kind == "geometric_cell_fraction"
    assert experiment_cfg.run.advection_scheme == "geometric_swept_volume"
    assert experiment_cfg.run.interface_tracking_method == "q_cell_fraction"
    assert experiment_cfg.run.capillary_force_source == "bundle_virtual_work"
    contract = build_ao_fast_runtime_contract(experiment_cfg)
    assert contract.capillary_constraints == ("cell_volume",)
    assert contract.checkpoint_state_phase == "pre_step"
    assert contract.projection_implementation == "active_cached"
    assert contract.dense_reference == "test_only"
    assert contract.gpu_required is True
    assert contract.fallback_policy == "none"
    assert contract.active_projection_solver_scheme == "pcg"
    assert contract.active_projection_primary == "active_pcg_newton"
    assert contract.active_projection_pcg_roundoff_floor == pytest.approx(1.0e-14)

    options = build_solver_init_options(experiment_cfg)
    assert options.grid.use_gpu is True
    assert options.schemes.advection_scheme == "geometric_swept_volume"


def test_column_height_graph_endpoint_is_yaml_selected_contract():
    raw = _geometric_raw(
        {
            "numerics": {
                "interface": {
                    "tracking": {
                        "primary": "q",
                        "gauge_reconstruction": "column_height_graph",
                    }
                },
                "momentum": {
                    "terms": {
                        "surface_tension": {
                            "closed_interface": {
                                "endpoint": "column_height_graph",
                            }
                        }
                    }
                },
            }
        }
    )

    experiment_cfg = ExperimentConfig.from_dict(raw)
    contract = build_ao_fast_runtime_contract(experiment_cfg)
    options = build_solver_init_options(experiment_cfg)

    assert experiment_cfg.run.interface_gauge_reconstruction == "column_height_graph"
    assert experiment_cfg.run.capillary_closed_interface_endpoint == "column_height_graph"
    assert contract.capillary_endpoint == "column_height_graph"
    assert contract.capillary_constraints == ("cell_volume",)
    assert options.schemes.capillary_closed_interface_endpoint == "column_height_graph"


def test_column_height_graph_gauge_rejects_p1_endpoint():
    raw = _geometric_raw(
        {
            "numerics": {
                "interface": {
                    "tracking": {
                        "primary": "q",
                        "gauge_reconstruction": "column_height_graph",
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="closed_interface.endpoint"):
        ExperimentConfig.from_dict(raw)


def test_active_geometry_capillary_scalar_preset_expands_defaults():
    raw = _geometric_raw()
    cfg = ExperimentConfig.from_dict(raw)

    assert cfg.interface_state_space.scheme == "active_geometry_capillary"
    assert cfg.interface_state_space.kind == "geometric_cell_fraction"
    assert cfg.interface_state_space.conserved_variable == "q"
    assert cfg.interface_state_space.projection_implementation == "active_cached"
    assert cfg.interface_state_space.fallback_policy == "none"
    assert cfg.interface_state_space.active_projection_solver_scheme == "pcg"
    options = build_solver_init_options(cfg)
    assert options.grid.use_gpu is True
    assert options.interface.interface_tracking_method == "q_cell_fraction"
    assert options.schemes.capillary_force_source == "bundle_virtual_work"


@pytest.mark.parametrize(
    ("scheme", "primary", "fallback_policy", "fallback_target"),
    [
        ("dc", "residual_monotone_dc", "none", None),
        ("pcg", "active_pcg_newton", "none", None),
        ("dc_then_pcg", "residual_monotone_dc", "explicit_chain", "active_pcg_newton"),
    ],
)
def test_active_geometry_projection_solver_yaml_modes(
    scheme,
    primary,
    fallback_policy,
    fallback_target,
):
    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "active_geometry": {
                        "solver": {
                            "scheme": scheme,
                            "convergence": {
                                "norm": "linf",
                                "absolute_tolerance": 2.0e-11,
                                "relative_tolerance": 1.0e-9,
                                "max_iterations": 9,
                            },
                            "dc": {
                                "tolerance": 3.0e-11,
                                "max_iterations": 4,
                                "relaxation": 0.75,
                            },
                            "fallback": {
                                "triggers": ["not_converged", "residual_floor_exceeded"]
                            },
                        }
                    }
                }
            }
        }
    )
    solver_cfg = raw["numerics"]["projection"]["active_geometry"]["solver"]
    if scheme == "pcg":
        solver_cfg.pop("dc")
        solver_cfg.pop("fallback")
    elif scheme == "dc":
        solver_cfg.pop("fallback")

    experiment_cfg = ExperimentConfig.from_dict(raw)
    cfg = experiment_cfg.interface_state_space
    assert cfg.active_projection_solver_scheme == scheme
    assert cfg.active_projection_primary == primary
    assert cfg.fallback_policy == fallback_policy
    assert cfg.active_projection_fallback_policy == fallback_policy
    assert cfg.active_projection_fallback_target == fallback_target
    assert cfg.active_projection_absolute_tolerance == pytest.approx(2.0e-11)
    assert cfg.active_projection_relative_tolerance == pytest.approx(1.0e-9)
    assert cfg.active_projection_max_iterations == 9
    expected_dc_tolerance = 2.0e-11 if scheme == "pcg" else 3.0e-11
    expected_dc_iterations = 9 if scheme == "pcg" else 4
    expected_dc_relaxation = 1.0 if scheme == "pcg" else 0.75
    assert cfg.active_projection_dc_tolerance == pytest.approx(expected_dc_tolerance)
    assert cfg.active_projection_dc_max_iterations == expected_dc_iterations
    assert cfg.active_projection_dc_relaxation == pytest.approx(expected_dc_relaxation)
    if scheme == "dc_then_pcg":
        assert cfg.active_projection_fallback_triggers == (
            "not_converged",
            "residual_floor_exceeded",
        )
    contract = build_ao_fast_runtime_contract(experiment_cfg)
    assert contract.active_projection_solver_scheme == scheme
    assert contract.active_projection_primary == primary
    assert contract.active_projection_fallback_policy == fallback_policy
    assert contract.active_projection_convergence_norm == "linf"
    assert contract.active_projection_absolute_tolerance == pytest.approx(2.0e-11)


def test_active_geometry_projection_solver_rejects_hidden_fallback():
    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "active_geometry": {
                        "solver": {
                            "scheme": "dc",
                            "fallback": {"triggers": ["not_converged"]},
                        }
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="DC-only"):
        ExperimentConfig.from_dict(raw)


def test_active_geometry_projection_solver_rejects_invalid_convergence():
    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "active_geometry": {
                        "solver": {
                            "scheme": "pcg",
                            "pcg": {
                                "tolerance": 1.0e-12,
                                "roundoff_floor": 1.0e-10,
                            },
                        }
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="roundoff_floor"):
        ExperimentConfig.from_dict(raw)


def test_active_geometry_projection_solver_rejects_internal_scheme_name():
    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "active_geometry": {
                        "solver": {"scheme": "active_pcg_newton"}
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="solver.scheme"):
        ExperimentConfig.from_dict(raw)


def test_active_geometry_projection_solver_rejects_ambiguous_convergence_key():
    raw = _geometric_raw(
        {
            "numerics": {
                "projection": {
                    "active_geometry": {
                        "solver": {
                            "scheme": "pcg",
                            "convergence": {"tolerance": 1.0e-11},
                        }
                    }
                }
            }
        }
    )

    with pytest.raises(ValueError, match="unknown keys: tolerance"):
        ExperimentConfig.from_dict(raw)


def test_nonstatic_ao_capillary_runtime_rejects_unadmitted_reaction():
    zeros = (np.zeros((1, 1)), np.zeros((1, 1)))
    application = GeometricRuntimeCapillaryApplicationState(
        capillary=SimpleNamespace(pressure_range_tolerance=1.0e-11),
        dt=1.0,
        predictor_face_acceleration=zeros,
        pressure_reaction_face_acceleration=zeros,
        predictor_face_increment=zeros,
        pressure_reaction_face_increment=zeros,
        pressure_balanced_face_increment=zeros,
        predictor_increment_weighted_l2=1.0,
        pressure_reaction_increment_weighted_l2=0.0,
        pressure_balanced_increment_weighted_l2=1.0,
        max_abs_pressure_balanced_face_increment=1.0,
        pressure_exact_static=False,
        capillary_drive_present=True,
    )

    with pytest.raises(ValueError, match="R_p\\(q_T\\)"):
        validate_geometric_runtime_capillary_application_admitted(application)


def test_nonstatic_ao_capillary_runtime_allows_pending_split_only_at_boundary():
    zeros = (np.zeros((1, 1)), np.zeros((1, 1)))
    application = GeometricRuntimeCapillaryApplicationState(
        capillary=SimpleNamespace(
            pressure_range_tolerance=1.0e-11,
            pressure_reaction_projection_status="pressure_reaction_projection_pending",
        ),
        dt=1.0,
        predictor_face_acceleration=zeros,
        pressure_reaction_face_acceleration=zeros,
        predictor_face_increment=zeros,
        pressure_reaction_face_increment=zeros,
        pressure_balanced_face_increment=zeros,
        predictor_increment_weighted_l2=1.0,
        pressure_reaction_increment_weighted_l2=0.0,
        pressure_balanced_increment_weighted_l2=1.0,
        max_abs_pressure_balanced_face_increment=1.0,
        pressure_exact_static=False,
        capillary_drive_present=True,
        pressure_reaction_projection_status="pressure_reaction_projection_pending",
    )

    with pytest.raises(ValueError, match="R_p\\(q_T\\)"):
        validate_geometric_runtime_capillary_application_admitted(application)
    validate_geometric_runtime_capillary_application_admitted(
        application,
        allow_pending_reaction_projection=True,
    )


@pytest.mark.parametrize(
    "status",
    ("pressure_component_hodge_split", "pressure_jump_affine"),
)
def test_nonstatic_ao_capillary_runtime_accepts_admitted_routes(status):
    zeros = (np.zeros((1, 1)), np.zeros((1, 1)))
    application = GeometricRuntimeCapillaryApplicationState(
        capillary=SimpleNamespace(pressure_range_tolerance=1.0e-11),
        dt=1.0,
        predictor_face_acceleration=zeros,
        pressure_reaction_face_acceleration=zeros,
        predictor_face_increment=zeros,
        pressure_reaction_face_increment=zeros,
        pressure_balanced_face_increment=zeros,
        predictor_increment_weighted_l2=1.0,
        pressure_reaction_increment_weighted_l2=0.0,
        pressure_balanced_increment_weighted_l2=1.0,
        max_abs_pressure_balanced_face_increment=1.0,
        pressure_exact_static=False,
        capillary_drive_present=True,
        pressure_reaction_projection_status=status,
    )

    validate_geometric_runtime_capillary_application_admitted(application)


def test_direct_geometric_runtime_rejects_cpu_backend():
    with pytest.raises(RuntimeError, match="requires a GPU backend"):
        TwoPhaseNSSolver(
            8,
            8,
            1.0,
            1.0,
            advection_scheme="geometric_swept_volume",
            use_gpu=False,
        )


def test_active_geometry_capillary_rejects_mapping_form():
    raw = _geometric_raw()
    raw["interface"]["state_space"] = {"scheme": "active_geometry_capillary"}

    with pytest.raises(ValueError, match="scalar 'active_geometry_capillary'"):
        ExperimentConfig.from_dict(raw)


@pytest.mark.parametrize(
    "scheme",
    [
        "ao_fast",
        "ao-fast",
        "active-geometry-capillary",
        "geometric_cell_fraction",
    ],
)
def test_active_geometry_capillary_rejects_legacy_scheme_names(scheme):
    raw = _geometric_raw()
    raw["interface"]["state_space"] = {"scheme": scheme}

    with pytest.raises(ValueError, match="active_geometry_capillary"):
        ExperimentConfig.from_dict(raw)


def test_active_geometry_capillary_rejects_kind_only_front_door():
    raw = _geometric_raw()
    raw["interface"]["state_space"] = {"kind": "geometric_cell_fraction"}

    with pytest.raises(ValueError, match="state_space: active_geometry_capillary"):
        ExperimentConfig.from_dict(raw)


@pytest.mark.parametrize(
    "extra",
    [
        {"kind": "geometric_cell_fraction"},
        {"conserved_variable": "q"},
        {"normalized_view": "theta"},
        {"gauge": {"variable": "phi"}},
        {"compatibility": {"projection": {"implementation": "active_cached"}}},
    ],
)
def test_active_geometry_capillary_rejects_parser_owned_yaml_knobs(extra):
    raw = _geometric_raw()
    raw["interface"]["state_space"] = {
        "scheme": "active_geometry_capillary",
        **extra,
    }

    with pytest.raises(ValueError, match="scalar 'active_geometry_capillary'"):
        ExperimentConfig.from_dict(raw)


def test_geometric_runtime_accepts_active_projection_schedule():
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
    contract = build_ao_fast_runtime_contract(experiment_cfg)
    assert contract.active_projection_solver_scheme == "pcg"


def test_geometric_runtime_gpu_backend_marks_capillary_projection_pending():
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
    solver._advance_geometric_phase_stage(state)
    assert solver._last_geometric_runtime_material is not None
    assert solver._last_geometric_runtime_capillary_application is not None
    assert (
        solver._last_geometric_runtime_capillary.pressure_range_status
        == "pressure_reaction_projection_pending"
    )
    assert (
        solver._last_geometric_runtime_capillary_application
        .pressure_reaction_projection_status
        == "pressure_reaction_projection_pending"
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
