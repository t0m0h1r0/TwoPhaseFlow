"""Unit tests for :mod:`twophase.linalg_backend`.

Validates the batched Thomas solver against
``scipy.linalg.solve_banded`` across size and batch sweeps on
diagonally-dominant tridiagonal systems.
"""

import numpy as np
import pytest
from scipy.linalg import solve_banded

from twophase.linalg_backend import thomas_batched


def _random_dd_banded(n: int, rng: np.random.Generator) -> np.ndarray:
    """Build a random strictly diagonally dominant (3, n) banded matrix."""
    ab = np.zeros((3, n), dtype=np.float64)
    ab[0, 1:] = rng.standard_normal(n - 1)           # upper
    ab[2, :-1] = rng.standard_normal(n - 1)          # lower
    main = rng.standard_normal(n)
    off_sum = np.abs(ab[0]) + np.abs(ab[2])
    # Enforce |main| > sum of off-diagonals
    ab[1] = np.sign(main + (main == 0)) * (off_sum + 1.0 + np.abs(main))
    return ab


def _scipy_solve_axis(ab: np.ndarray, rhs: np.ndarray, axis: int) -> np.ndarray:
    """Reference axis-aware wrapper around scipy.linalg.solve_banded."""
    n = rhs.shape[axis]
    moved = np.moveaxis(rhs, axis, 0)
    batch_shape = moved.shape[1:]
    rhs_2d = moved.reshape(n, -1)
    x_2d = solve_banded((1, 1), ab, rhs_2d)
    x_moved = x_2d.reshape((n,) + batch_shape)
    return np.moveaxis(x_moved, 0, axis)


@pytest.mark.parametrize("n", [8, 32, 128, 256])
@pytest.mark.parametrize("batch_shape", [(), (7,), (4, 5), (3, 4, 5)])
def test_thomas_batched_matches_scipy_axis0(n, batch_shape):
    rng = np.random.default_rng(seed=hash((n, batch_shape)) & 0xFFFF)
    ab = _random_dd_banded(n, rng)
    rhs = rng.standard_normal((n, *batch_shape))

    x_ref = _scipy_solve_axis(ab, rhs, axis=0)
    x_our = thomas_batched(np, ab, rhs, axis=0)

    assert x_our.shape == x_ref.shape
    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_thomas_batched_axis_independence(axis):
    rng = np.random.default_rng(42)
    n = 64
    shape = [16, 12, 8]
    shape[axis] = n
    ab = _random_dd_banded(n, rng)
    rhs = rng.standard_normal(tuple(shape))

    x_ref = _scipy_solve_axis(ab, rhs, axis=axis)
    x_our = thomas_batched(np, ab, rhs, axis=axis)

    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)


def test_thomas_batched_large_batch():
    rng = np.random.default_rng(7)
    n = 128
    ab = _random_dd_banded(n, rng)
    rhs = rng.standard_normal((n, 50_000))

    x_ref = _scipy_solve_axis(ab, rhs, axis=0)
    x_our = thomas_batched(np, ab, rhs, axis=0)
    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)


def test_thomas_batched_rejects_wrong_shape():
    rng = np.random.default_rng(0)
    ab = _random_dd_banded(16, rng)
    rhs = rng.standard_normal((16, 4))
    with pytest.raises(ValueError):
        thomas_batched(np, ab[:, :8], rhs, axis=0)  # mismatched n
