"""GPU fail-closed checks for host-only computational schemes."""

from __future__ import annotations

import pytest

from twophase.config import SimulationConfig
from twophase.ppe.iim_solver import PPESolverIIM
from twophase.ppe.iterative import PPESolverIterative
from twophase.simulation.velocity_reprojector_iim import ConsistentIIMReprojector


class _FakeGPUBackend:
    def is_gpu(self):
        return True


def test_iim_ppe_rejects_gpu_backend_before_host_transfer():
    with pytest.raises(NotImplementedError, match="host-only"):
        PPESolverIIM(_FakeGPUBackend(), SimulationConfig(), object())


def test_iterative_ppe_rejects_gpu_backend_before_host_transfer():
    with pytest.raises(NotImplementedError, match="host-only"):
        PPESolverIterative(_FakeGPUBackend(), SimulationConfig(), object())


def test_consistent_iim_reprojector_rejects_gpu_backend_before_host_transfer():
    reprojector = ConsistentIIMReprojector(
        reproj_iim=object(),
        reconstruct_base=object(),
    )

    with pytest.raises(NotImplementedError, match="host-only"):
        reprojector.reproject(
            psi=None,
            u=None,
            v=None,
            ppe_solver=object(),
            ccd=object(),
            backend=_FakeGPUBackend(),
            rho_l=2.0,
            rho_g=1.0,
        )
