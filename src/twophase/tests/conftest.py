"""Shared pytest fixtures for the twophase test suite.

Adds dual-backend parameterisation for tests that opt in via the
``backend`` fixture. The default run is **CPU only** (no GPU tests) so
existing CI stays fast and GPU-free. Pass ``--gpu`` on the command line to
parametrise the ``backend`` fixture over both backends::

    pytest src/twophase/tests --gpu

Tests that *explicitly* need a CuPy backend can use the marker::

    @pytest.mark.gpu
    def test_only_gpu(gpu_backend):
        ...

The marker-based tests are automatically skipped unless ``--gpu`` is
passed *and* a usable CUDA device is present.
"""

from __future__ import annotations

import pytest

from twophase.backend import Backend


def pytest_addoption(parser):
    parser.addoption(
        "--gpu",
        action="store_true",
        default=False,
        help="Run GPU (CuPy) smoke tests and parametrise backend-aware tests.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "gpu: test requires a CuPy/CUDA backend (skipped unless --gpu is passed)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--gpu"):
        return
    skip_gpu = pytest.mark.skip(reason="GPU tests disabled (pass --gpu to enable)")
    for item in items:
        if "gpu" in item.keywords:
            item.add_marker(skip_gpu)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def cpu_backend() -> Backend:
    """Session-scoped CPU backend (always available)."""
    return Backend(use_gpu=False)


@pytest.fixture(scope="session")
def gpu_backend() -> Backend:
    """Session-scoped GPU backend.

    Skips the requesting test if CuPy is not installed or no CUDA device
    is available. Safe to request unconditionally in tests that are
    either marked ``@pytest.mark.gpu`` or parametrised via ``backend``.
    """
    try:
        import cupy  # noqa: F401
        import cupy.cuda
        cupy.cuda.Device(0).compute_capability
    except Exception as exc:  # pragma: no cover — depends on host hardware
        pytest.skip(f"CuPy/CUDA unavailable: {exc}")
    return Backend(use_gpu=True)


def _backend_ids(val: str) -> str:
    return val


@pytest.fixture(params=["cpu"], ids=_backend_ids)
def backend(request, cpu_backend):
    """Parametrised backend fixture.

    Default: CPU only. When pytest is invoked with ``--gpu`` the
    ``pytest_generate_tests`` hook below extends the parametrisation to
    ``["cpu", "gpu"]`` so every test consuming ``backend`` runs twice.
    """
    kind = request.param
    if kind == "cpu":
        return cpu_backend
    if kind == "gpu":
        return request.getfixturevalue("gpu_backend")
    raise ValueError(f"Unknown backend: {kind!r}")


def pytest_generate_tests(metafunc):
    """Expand ``backend`` parametrisation to include GPU when --gpu is passed."""
    if "backend" not in metafunc.fixturenames:
        return
    if not metafunc.config.getoption("--gpu"):
        return
    metafunc.parametrize(
        "backend", ["cpu", "gpu"], ids=["cpu", "gpu"], indirect=True,
    )
