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
