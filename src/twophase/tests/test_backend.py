"""Backend boundary helper tests."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.backend import (
    Backend,
    array_namespace,
    host_array,
    is_device_array,
    scalar_value,
)
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.simulation.ns_predictor_assembly import select_gravity_aligned_axis
from twophase.time_integration.cfl import CFLCalculator
from twophase.tools.diagnostics.collector import DiagnosticCollector
from twophase.tools.diagnostics.field_diagnostics import kinetic_energy
from twophase.tools.diagnostics.interface_diagnostics import (
    midband_fraction,
    parasitic_current_linf,
    relative_mass_error,
)


def test_backend_boundary_helpers_cpu():
    backend = Backend(use_gpu=False)
    values = np.asarray([1.0, 2.0, 3.0])

    assert array_namespace(values) is np
    assert not is_device_array(values)
    np.testing.assert_allclose(host_array(values), values)
    assert backend.to_scalar(np.sum(values)) == pytest.approx(6.0)
    assert scalar_value(np.asarray(2.5)) == pytest.approx(2.5)


def test_cfl_scalar_boundary_cpu():
    backend = Backend(use_gpu=False)
    grid = Grid(GridConfig(ndim=2, N=(4, 4), L=(1.0, 1.0)), backend)
    calculator = CFLCalculator(
        backend,
        grid,
        cfl_number=0.4,
        cn_viscous=False,
    )
    u = np.ones(grid.shape) * 2.0
    v = np.ones(grid.shape) * 3.0
    mu = np.ones(grid.shape) * 0.5
    rho = np.ones(grid.shape) * 2.0

    assert calculator.compute([u, v], mu, rho) == pytest.approx(0.02)


@pytest.mark.gpu
def test_backend_boundary_helpers_gpu(gpu_backend):
    xp = gpu_backend.xp
    values = xp.asarray([1.0, 2.0, 3.0])

    assert array_namespace(values) is xp
    assert is_device_array(values)
    np.testing.assert_allclose(host_array(values), np.asarray([1.0, 2.0, 3.0]))
    assert gpu_backend.to_scalar(xp.sum(values)) == pytest.approx(6.0)


@pytest.mark.gpu
def test_cfl_and_axis_scalar_boundaries_gpu(gpu_backend):
    xp = gpu_backend.xp
    grid = Grid(GridConfig(ndim=2, N=(4, 4), L=(1.0, 1.0)), gpu_backend)
    calculator = CFLCalculator(
        gpu_backend,
        grid,
        cfl_number=0.4,
        cn_viscous=False,
    )
    u = xp.ones(grid.shape) * 2.0
    v = xp.ones(grid.shape) * 3.0
    mu = xp.ones(grid.shape) * 0.5
    rho = xp.ones(grid.shape) * 2.0

    assert calculator.compute([u, v], mu, rho) == pytest.approx(0.02)
    assert select_gravity_aligned_axis([u, v], xp) == 1


@pytest.mark.gpu
def test_diagnostic_boundaries_accept_gpu_arrays(gpu_backend):
    xp = gpu_backend.xp
    x = xp.linspace(0.0, 1.0, 2)
    X, Y = xp.meshgrid(x, x, indexing="ij")
    psi = xp.asarray([[0.2, 0.8], [0.4, 0.6]])
    u = xp.ones_like(psi) * 2.0
    v = xp.zeros_like(psi)
    dV = xp.ones_like(psi) * 0.25

    assert kinetic_energy([u, v], dV) == pytest.approx(2.0)
    assert parasitic_current_linf([u, v]) == pytest.approx(2.0)
    assert midband_fraction(psi) == pytest.approx(1.0)
    assert relative_mass_error(psi, dV, 0.5) == pytest.approx(0.0)

    diagnostics = DiagnosticCollector(["kinetic_energy"], X, Y, h=0.5)
    diagnostics.collect(0.0, psi, u, v, xp.zeros_like(psi), dV=dV)
    assert diagnostics.last("kinetic_energy") == pytest.approx(2.0)
