"""Tests for Heaviside/interface reconstruction library."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import Backend
from twophase.levelset.reconstruction import (
    ReconstructionConfig,
    HeavisideInterfaceReconstructor,
)


@pytest.fixture
def backend():
    return Backend(use_gpu=False)


def test_phi_psi_roundtrip_reconstruction(backend):
    rec = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(eps=0.02, eps_scale=1.5, clip_factor=12.0),
    )
    x = np.linspace(-0.1, 0.1, 201)
    phi = np.tanh(20.0 * x) * 0.06
    psi = np.asarray(backend.to_host(rec.psi_from_phi(phi)))
    phi_rt = np.asarray(backend.to_host(rec.phi_from_psi(psi)))
    np.testing.assert_allclose(phi_rt, phi, rtol=1e-10, atol=1e-10)


def test_phi_clip_limit(backend):
    rec = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(eps=0.02, eps_scale=2.0, clip_factor=4.0),
    )
    phi = np.array([-1.0, -0.1, 0.0, 0.2, 1.0], dtype=float)
    clipped = np.asarray(backend.to_host(rec.clip_phi(phi)))
    lim = 4.0 * (0.02 * 2.0)
    assert np.all(clipped <= lim + 1e-15)
    assert np.all(clipped >= -lim - 1e-15)


def test_interface_points_from_phi_line(backend):
    rec = HeavisideInterfaceReconstructor(
        backend,
        ReconstructionConfig(eps=0.02, eps_scale=1.0, clip_factor=8.0),
    )
    x = np.linspace(0.0, 1.0, 65)
    y = np.linspace(0.0, 1.0, 49)
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = X - 0.5
    pts = rec.interface_points_from_phi(phi, x, y)
    assert pts.shape[0] > 0
    # x=0.5 vertical interface should dominate reconstructed points.
    assert np.max(np.abs(pts[:, 0] - 0.5)) < 1e-10

