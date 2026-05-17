"""Tests for low-mode PhaseRegion admission helpers."""

from __future__ import annotations

import numpy as np
import pytest

from twophase.geometry import AtlasValidationError, solve_low_mode_kkt


def test_low_mode_kkt_solves_unconstrained_least_squares():
    jacobian = np.array(((1.0, 0.0), (0.0, 2.0), (1.0, 1.0)))
    delta_true = np.array((0.25, -0.10))
    residual = jacobian @ delta_true

    result = solve_low_mode_kkt(jacobian, residual)

    np.testing.assert_allclose(result.delta, delta_true, atol=1.0e-14)
    np.testing.assert_allclose(result.predicted_residual, np.zeros(3), atol=1.0e-14)
    assert result.residual_l2 < 1.0e-14
    assert result.multipliers is None
    assert result.force_admissible is False


def test_low_mode_kkt_enforces_declared_constraint():
    jacobian = np.eye(2)
    residual = np.array((0.0, 0.0))
    constraint_jacobian = np.array(((1.0, 1.0),))
    constraint_rhs = np.array((0.3,))

    result = solve_low_mode_kkt(
        jacobian,
        residual,
        constraint_jacobian=constraint_jacobian,
        constraint_rhs=constraint_rhs,
    )

    assert abs(float(np.sum(result.delta)) - 0.3) < 1.0e-14
    assert result.constraint_residual_linf < 1.0e-14
    np.testing.assert_allclose(result.delta, np.array((0.15, 0.15)), atol=1.0e-14)


def test_low_mode_kkt_energy_regularization_shrinks_correction():
    jacobian = np.eye(2)
    residual = np.array((1.0, 0.5))
    unregularized = solve_low_mode_kkt(jacobian, residual)
    regularized = solve_low_mode_kkt(
        jacobian,
        residual,
        energy_hessian=np.eye(2),
        energy_weight=3.0,
    )

    assert np.linalg.norm(regularized.delta) < np.linalg.norm(unregularized.delta)
    assert regularized.objective > 0.0


def test_low_mode_kkt_matches_exact_weighted_regularized_constrained_system():
    jacobian = np.array(
        (
            (1.0, 2.0),
            (-1.0, 0.5),
            (0.25, 1.5),
        )
    )
    residual = np.array((0.3, -0.2, 0.5))
    weights = np.array((2.0, 0.5, 1.25))
    energy_hessian = np.array(((2.0, 0.1), (0.1, 1.0)))
    energy_weight = 0.7
    constraint_jacobian = np.array(((1.0, -1.0),))
    constraint_rhs = np.array((0.05,))

    normal = jacobian.T @ (weights[:, None] * jacobian) + energy_weight * energy_hessian
    rhs = jacobian.T @ (weights * residual)
    kkt_matrix = np.block(
        [
            [normal, constraint_jacobian.T],
            [constraint_jacobian, np.zeros((1, 1))],
        ]
    )
    exact_solution = np.linalg.solve(
        kkt_matrix,
        np.concatenate((rhs, constraint_rhs)),
    )
    exact_delta = exact_solution[:2]
    exact_multipliers = exact_solution[2:]
    exact_predicted_residual = residual - jacobian @ exact_delta
    exact_objective = (
        0.5 * np.sum(weights * exact_predicted_residual * exact_predicted_residual)
        + 0.5 * energy_weight * exact_delta @ energy_hessian @ exact_delta
    )

    result = solve_low_mode_kkt(
        jacobian,
        residual,
        weights=weights,
        energy_hessian=energy_hessian,
        energy_weight=energy_weight,
        constraint_jacobian=constraint_jacobian,
        constraint_rhs=constraint_rhs,
    )

    np.testing.assert_allclose(result.delta, exact_delta, atol=1.0e-14)
    np.testing.assert_allclose(result.multipliers, exact_multipliers, atol=1.0e-14)
    np.testing.assert_allclose(result.predicted_residual, exact_predicted_residual, atol=1.0e-14)
    assert result.objective == pytest.approx(exact_objective, abs=1.0e-14)
    assert result.constraint_residual_linf < 1.0e-14
    assert result.force_admissible is False


def test_low_mode_kkt_supports_batched_solve():
    jacobian = np.stack((np.eye(2), 2.0 * np.eye(2)), axis=0)
    delta_true = np.array(((0.2, -0.1), (0.05, 0.15)))
    residual = np.einsum("bmk,bk->bm", jacobian, delta_true)

    result = solve_low_mode_kkt(jacobian, residual)

    np.testing.assert_allclose(result.delta, delta_true, atol=1.0e-14)
    np.testing.assert_allclose(result.residual_l2, np.zeros(2), atol=1.0e-14)


def test_low_mode_kkt_fails_closed_on_invalid_inputs():
    with pytest.raises(AtlasValidationError, match="weights"):
        solve_low_mode_kkt(np.eye(2), np.ones(2), weights=np.array((1.0, 0.0)))

    with pytest.raises(AtlasValidationError, match="energy_weight"):
        solve_low_mode_kkt(np.eye(2), np.ones(2), energy_weight=-1.0)

    with pytest.raises(AtlasValidationError, match="constraint_rhs"):
        solve_low_mode_kkt(np.eye(2), np.ones(2), constraint_jacobian=np.ones((1, 2)))

    with pytest.raises(AtlasValidationError, match="energy_hessian"):
        solve_low_mode_kkt(np.eye(2), np.ones(2), energy_hessian=np.ones((3, 3)))

    with pytest.raises(AtlasValidationError, match="symmetric"):
        solve_low_mode_kkt(
            np.eye(2),
            np.ones(2),
            energy_hessian=np.array(((1.0, 2.0), (0.0, 1.0))),
        )

    with pytest.raises(AtlasValidationError, match="positive semidefinite"):
        solve_low_mode_kkt(
            np.eye(2),
            np.ones(2),
            energy_hessian=np.array(((1.0, 0.0), (0.0, -1.0))),
        )

    with pytest.raises(AtlasValidationError, match="constraint_jacobian"):
        solve_low_mode_kkt(
            np.eye(2),
            np.ones(2),
            constraint_jacobian=np.ones((1, 3)),
            constraint_rhs=np.ones(1),
        )

    with pytest.raises(AtlasValidationError, match="singular"):
        solve_low_mode_kkt(np.zeros((2, 2)), np.ones(2))
