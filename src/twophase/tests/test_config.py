"""
Tests for config dataclasses and config_loader YAML round-trip.

Verified properties:
  1. NumericsConfig.advection_scheme validation — rejects invalid values
  2. NumericsConfig epsilon_factor < 1.2 warning — emits UserWarning with
     dissipative_ccd (§5 warn:adv_risks(B)); silent for weno5
  3. config_loader YAML round-trip — advection_scheme survives load→dump→load
  4. config_loader _known set — advection_scheme does NOT trigger unknown-key warning
"""

import warnings
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from twophase.config import NumericsConfig, SimulationConfig, GridConfig


# ── Test 1: advection_scheme field validation ─────────────────────────────

def test_advection_scheme_valid_dissipative_ccd():
    cfg = NumericsConfig(advection_scheme="dissipative_ccd")
    assert cfg.advection_scheme == "dissipative_ccd"


def test_advection_scheme_valid_weno5():
    cfg = NumericsConfig(advection_scheme="weno5")
    assert cfg.advection_scheme == "weno5"


def test_advection_scheme_invalid_raises():
    with pytest.raises(AssertionError):
        NumericsConfig(advection_scheme="upwind")


# ── Test 2: ε_factor < 1.2 safety warning (§5 warn:adv_risks(B)) ─────────

def test_epsilon_factor_low_with_dccd_warns():
    """epsilon_factor < 1.2 + dissipative_ccd must emit UserWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        NumericsConfig(advection_scheme="dissipative_ccd", epsilon_factor=1.0)
    assert len(w) == 1
    assert issubclass(w[0].category, UserWarning)
    assert "epsilon_factor" in str(w[0].message)
    assert "warn:adv_risks" in str(w[0].message)


def test_epsilon_factor_low_with_weno5_no_warn():
    """epsilon_factor < 1.2 + weno5 must NOT emit a warning (WENO5 is robust)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        NumericsConfig(advection_scheme="weno5", epsilon_factor=1.0)
    assert len(w) == 0


def test_epsilon_factor_safe_no_warn():
    """epsilon_factor >= 1.2 + dissipative_ccd must NOT emit a warning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        NumericsConfig(advection_scheme="dissipative_ccd", epsilon_factor=1.5)
    assert len(w) == 0


# ── Test 3 & 4: config_loader YAML round-trip ────────────────────────────

def _require_config_loader():
    try:
        from twophase.configs.config_loader import load_config, save_config
        import yaml  # noqa: F401
        return load_config, save_config
    except ImportError:
        pytest.skip("PyYAML not installed — skipping YAML round-trip tests")


def test_config_loader_advection_scheme_roundtrip():
    """advection_scheme must survive load → save → load."""
    load_config, save_config = _require_config_loader()

    cfg_orig = SimulationConfig(
        grid=GridConfig(ndim=2, N=(32, 32), L=(1.0, 1.0)),
        numerics=NumericsConfig(advection_scheme="weno5"),
    )

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = f.name

    try:
        save_config(cfg_orig, path)
        cfg_loaded, _, _ic, _vf = load_config(path)
        assert cfg_loaded.numerics.advection_scheme == "weno5", (
            f"Round-trip failed: got '{cfg_loaded.numerics.advection_scheme}'"
        )
    finally:
        os.unlink(path)


def test_config_loader_advection_scheme_no_unknown_key_warning():
    """advection_scheme in YAML must NOT trigger the unknown-key UserWarning."""
    load_config, save_config = _require_config_loader()

    cfg = SimulationConfig(
        grid=GridConfig(ndim=2, N=(32, 32), L=(1.0, 1.0)),
        numerics=NumericsConfig(advection_scheme="dissipative_ccd"),
    )

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = f.name

    try:
        save_config(cfg, path)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_config(path)
        unknown_key_warns = [x for x in w if "未知のキー" in str(x.message)
                             or "advection_scheme" in str(x.message)]
        assert len(unknown_key_warns) == 0, (
            f"Unexpected unknown-key warning for advection_scheme: {unknown_key_warns}"
        )
    finally:
        os.unlink(path)
