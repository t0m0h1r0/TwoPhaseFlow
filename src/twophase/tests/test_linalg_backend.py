"""Unit tests for :mod:`twophase.linalg_backend`.

Validates the batched Thomas solver against
``scipy.linalg.solve_banded`` across size and batch sweeps on
diagonally-dominant tridiagonal systems.
"""

import numpy as np
import pytest
from scipy.linalg import solve_banded

from twophase.linalg_backend import (
    _pcr_solve_batched,
    _pcr_solve_variable_batched,
    thomas_batched,
    thomas_precompute,
    tridiag_variable_batched,
)


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


def test_thomas_batched_precomputed_factors_matches_scipy():
    rng = np.random.default_rng(314)
    n = 64
    ab = _random_dd_banded(n, rng)
    rhs = rng.standard_normal((n, 11))

    x_ref = _scipy_solve_axis(ab, rhs, axis=0)
    factors = thomas_precompute(ab)
    x_our = thomas_batched(np, ab, rhs, axis=0, factors=factors)

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


def _random_variable_dd(shape: tuple[int, ...], axis: int, rng: np.random.Generator):
    lower = rng.standard_normal(shape)
    upper = rng.standard_normal(shape)
    diag = rng.standard_normal(shape)

    sl_first = [slice(None)] * len(shape)
    sl_last = [slice(None)] * len(shape)
    sl_first[axis] = 0
    sl_last[axis] = shape[axis] - 1
    lower[tuple(sl_first)] = 0.0
    upper[tuple(sl_last)] = 0.0

    moved_lower = np.moveaxis(lower, axis, 0)
    moved_upper = np.moveaxis(upper, axis, 0)
    moved_diag = np.moveaxis(diag, axis, 0)
    moved_diag[...] = (
        np.abs(moved_lower) + np.abs(moved_upper) + 1.0 + np.abs(moved_diag)
    )
    return lower, moved_diag if axis == 0 else np.moveaxis(moved_diag, 0, axis), upper


def _reference_variable_tridiag(lower, diag, upper, rhs, axis: int):
    moved_l = np.moveaxis(lower, axis, 0).reshape(lower.shape[axis], -1)
    moved_d = np.moveaxis(diag, axis, 0).reshape(diag.shape[axis], -1)
    moved_u = np.moveaxis(upper, axis, 0).reshape(upper.shape[axis], -1)
    moved_r = np.moveaxis(rhs, axis, 0).reshape(rhs.shape[axis], -1)
    n, batch = moved_r.shape
    out = np.empty_like(moved_r)
    for col in range(batch):
        ab = np.zeros((3, n), dtype=np.float64)
        ab[0, 1:] = moved_u[:-1, col]
        ab[1, :] = moved_d[:, col]
        ab[2, :-1] = moved_l[1:, col]
        out[:, col] = solve_banded((1, 1), ab, moved_r[:, col])
    out = out.reshape((n,) + np.moveaxis(rhs, axis, 0).shape[1:])
    return np.moveaxis(out, 0, axis)


def test_pcr_solve_batched_matches_reference():
    rng = np.random.default_rng(2040)
    n = 16
    batch = 5
    ab = _random_dd_banded(n, rng)
    lower = np.zeros(n, dtype=np.float64)
    diag = ab[1].copy()
    upper = np.zeros(n, dtype=np.float64)
    lower[1:] = ab[2, : n - 1]
    upper[: n - 1] = ab[0, 1:]
    rhs = rng.standard_normal((n, batch))

    x_ref = np.column_stack(
        [solve_banded((1, 1), ab, rhs[:, batch_index]) for batch_index in range(batch)]
    )
    x_our = _pcr_solve_batched(np, lower, diag, upper, rhs)

    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)


def test_pcr_solve_variable_batched_matches_reference():
    rng = np.random.default_rng(2041)
    shape = (16, 4)
    lower, diag, upper = _random_variable_dd(shape, axis=0, rng=rng)
    rhs = rng.standard_normal(shape)

    x_ref = _reference_variable_tridiag(lower, diag, upper, rhs, axis=0)
    x_our = _pcr_solve_variable_batched(np, lower, diag, upper, rhs)

    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)


@pytest.mark.parametrize("axis", [0, 1, 2])
def test_tridiag_variable_batched_matches_reference(axis):
    rng = np.random.default_rng(2026 + axis)
    shape = [7, 5, 4]
    shape[axis] = 16
    shape = tuple(shape)
    lower, diag, upper = _random_variable_dd(shape, axis, rng)
    rhs = rng.standard_normal(shape)

    x_ref = _reference_variable_tridiag(lower, diag, upper, rhs, axis)
    x_our = tridiag_variable_batched(np, lower, diag, upper, rhs, axis)

    np.testing.assert_allclose(x_our, x_ref, rtol=1e-12, atol=1e-13)
