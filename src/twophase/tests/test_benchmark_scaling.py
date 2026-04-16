"""Tests for benchmark scaling helpers."""

from __future__ import annotations

import pytest

from twophase.tools.benchmarks.scaling import (
    mu_from_re,
    sigma_from_eo,
    mu_sigma_from_re_eo,
)


def test_mu_from_re_matches_formula():
    mu = mu_from_re(rho_l=10.0, g_acc=1.0, d_ref=0.5, re_num=35.0)
    expected = 10.0 * (1.0 * 0.5) ** 0.5 * 0.5 / 35.0
    assert mu == pytest.approx(expected, rel=1e-15, abs=0.0)


def test_sigma_from_eo_matches_formula():
    sigma = sigma_from_eo(rho_l=10.0, rho_g=1.0, g_acc=1.0, d_ref=0.5, eo_num=10.0)
    expected = 1.0 * (10.0 - 1.0) * 0.5 ** 2 / 10.0
    assert sigma == pytest.approx(expected, rel=1e-15, abs=0.0)


def test_mu_sigma_from_re_eo_consistent():
    mu, sigma = mu_sigma_from_re_eo(
        rho_l=10.0, rho_g=1.0, g_acc=1.0, d_ref=0.5, re_num=35.0, eo_num=10.0
    )
    assert mu == pytest.approx(mu_from_re(10.0, 1.0, 0.5, 35.0), rel=1e-15)
    assert sigma == pytest.approx(sigma_from_eo(10.0, 1.0, 1.0, 0.5, 10.0), rel=1e-15)

