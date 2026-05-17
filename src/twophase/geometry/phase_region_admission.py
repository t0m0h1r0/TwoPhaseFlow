"""Low-mode PhaseRegion admission solvers.

Symbol mapping
--------------
``delta`` -> correction in admitted chart-mode coordinates.
``J_Q`` -> linearized map from chart modes to measured q residual moments.
``r`` -> residual moments to reduce without promoting cellwise noise to geometry.
``J_C`` -> linearized declared constraints, such as total volume.
``H_E`` -> optional energy Hessian in admitted mode coordinates.

This module implements only the small F1 KKT correction from the PhaseRegion
admission ladder.  It does not choose charts, build ``J_Q`` from cells, perform
full nonlinear optimization, reconstruct ``phi``, or admit forces.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .interface_atlas import AtlasValidationError


@dataclass(frozen=True)
class LowModeKKTResult:
    """Result of one low-mode linearized admission correction."""

    delta: object
    multipliers: object | None
    predicted_residual: object
    residual_l2: object
    constraint_residual_linf: object | None
    objective: object
    force_admissible: bool


def solve_low_mode_kkt(
    jacobian_q: object,
    residual: object,
    *,
    weights: object | None = None,
    energy_hessian: object | None = None,
    energy_weight: float = 0.0,
    constraint_jacobian: object | None = None,
    constraint_rhs: object | None = None,
) -> LowModeKKTResult:
    """Solve the F1 low-mode KKT correction.

    The solved problem is:

    ``min_delta 1/2 ||J_Q delta - r||_W^2
        + 1/2 energy_weight delta^T H_E delta``

    subject to:

    ``J_C delta = constraint_rhs``.

    Args:
        jacobian_q: Linearized q-moment map, shape ``(m, k)`` or
            ``(batch, m, k)``.
        residual: Residual moments, shape ``(m,)`` or ``(batch, m)``.
        weights: Optional positive residual weights, shape ``(m,)`` or
            ``(batch, m)``.
        energy_hessian: Optional symmetric mode-space Hessian, shape
            ``(k, k)`` or ``(batch, k, k)``.
        energy_weight: Nonnegative multiplier for ``energy_hessian``.
        constraint_jacobian: Optional constraint matrix, shape ``(p, k)`` or
            ``(batch, p, k)``.
        constraint_rhs: Optional constraint target, shape ``(p,)`` or
            ``(batch, p)``.  Required when ``constraint_jacobian`` is provided.

    Returns:
        ``LowModeKKTResult`` with ``force_admissible=False``.
    """
    j_q, residual_b, was_batched = _as_batched_system(jacobian_q, residual)
    batch_size, moment_count, mode_count = j_q.shape
    weight_b = _as_batched_weights(weights, batch_size, moment_count)
    hessian_b = _as_batched_hessian(energy_hessian, batch_size, mode_count)
    alpha = float(energy_weight)
    if alpha < 0.0:
        raise AtlasValidationError("energy_weight must be nonnegative")

    normal = np.einsum("bmk,bm,bml->bkl", j_q, weight_b, j_q)
    normal = normal + alpha * hessian_b
    rhs = np.einsum("bmk,bm,bm->bk", j_q, weight_b, residual_b)

    constraints = _as_batched_constraints(
        constraint_jacobian,
        constraint_rhs,
        batch_size,
        mode_count,
    )
    try:
        if constraints is None:
            delta = np.linalg.solve(normal, rhs[..., None])[..., 0]
            multipliers = None
            constraint_residual_linf = None
        else:
            c_jac, c_rhs = constraints
            constraint_count = c_jac.shape[1]
            zeros = np.zeros((batch_size, constraint_count, constraint_count), dtype=float)
            kkt = np.concatenate(
                (
                    np.concatenate((normal, np.swapaxes(c_jac, -1, -2)), axis=-1),
                    np.concatenate((c_jac, zeros), axis=-1),
                ),
                axis=-2,
            )
            kkt_rhs = np.concatenate((rhs, c_rhs), axis=-1)
            solution = np.linalg.solve(kkt, kkt_rhs[..., None])[..., 0]
            delta = solution[:, :mode_count]
            multipliers = solution[:, mode_count:]
            constraint_residual = np.einsum("bpk,bk->bp", c_jac, delta) - c_rhs
            constraint_residual_linf = np.max(np.abs(constraint_residual), axis=-1)
    except np.linalg.LinAlgError as exc:
        raise AtlasValidationError("low-mode KKT system is singular") from exc

    predicted_residual = residual_b - np.einsum("bmk,bk->bm", j_q, delta)
    residual_l2 = np.sqrt(np.sum(predicted_residual * predicted_residual, axis=-1))
    data_misfit = 0.5 * np.sum(weight_b * predicted_residual * predicted_residual, axis=-1)
    energy_penalty = 0.5 * alpha * np.einsum("bk,bkl,bl->b", delta, hessian_b, delta)
    objective = data_misfit + energy_penalty

    if not was_batched:
        delta = delta[0]
        predicted_residual = predicted_residual[0]
        residual_l2 = float(residual_l2[0])
        objective = float(objective[0])
        if multipliers is not None:
            multipliers = multipliers[0]
        if constraint_residual_linf is not None:
            constraint_residual_linf = float(constraint_residual_linf[0])

    return LowModeKKTResult(
        delta=delta,
        multipliers=multipliers,
        predicted_residual=predicted_residual,
        residual_l2=residual_l2,
        constraint_residual_linf=constraint_residual_linf,
        objective=objective,
        force_admissible=False,
    )


def _as_batched_system(jacobian_q: object, residual: object) -> tuple[object, object, bool]:
    j_q = np.asarray(jacobian_q, dtype=float)
    r = np.asarray(residual, dtype=float)
    if j_q.ndim == 2:
        j_q = j_q[None, ...]
        was_batched = False
    elif j_q.ndim == 3:
        was_batched = True
    else:
        raise AtlasValidationError("jacobian_q must have shape (m,k) or (batch,m,k)")
    if not np.all(np.isfinite(j_q)):
        raise AtlasValidationError("jacobian_q must be finite")
    batch_size, moment_count, _mode_count = j_q.shape
    if r.ndim == 1 and not was_batched:
        r = r[None, ...]
    elif r.ndim == 1 and was_batched:
        r = np.broadcast_to(r[None, :], (batch_size, r.size))
    elif r.ndim != 2:
        raise AtlasValidationError("residual must have shape (m,) or (batch,m)")
    if r.shape != (batch_size, moment_count):
        raise AtlasValidationError("residual shape must match jacobian_q moments")
    if not np.all(np.isfinite(r)):
        raise AtlasValidationError("residual must be finite")
    return j_q, r, was_batched


def _as_batched_weights(weights: object | None, batch_size: int, moment_count: int) -> object:
    if weights is None:
        return np.ones((batch_size, moment_count), dtype=float)
    w = np.asarray(weights, dtype=float)
    if w.ndim == 1:
        w = np.broadcast_to(w[None, :], (batch_size, moment_count))
    if w.shape != (batch_size, moment_count):
        raise AtlasValidationError("weights must have shape (m,) or (batch,m)")
    if not np.all(np.isfinite(w)) or np.any(w <= 0.0):
        raise AtlasValidationError("weights must be positive and finite")
    return w


def _as_batched_hessian(hessian: object | None, batch_size: int, mode_count: int) -> object:
    if hessian is None:
        return np.zeros((batch_size, mode_count, mode_count), dtype=float)
    h = np.asarray(hessian, dtype=float)
    if h.ndim == 2:
        if h.shape != (mode_count, mode_count):
            raise AtlasValidationError("energy_hessian must have shape (k,k) or (batch,k,k)")
        h = np.broadcast_to(h[None, :, :], (batch_size, mode_count, mode_count))
    if h.shape != (batch_size, mode_count, mode_count):
        raise AtlasValidationError("energy_hessian must have shape (k,k) or (batch,k,k)")
    if not np.all(np.isfinite(h)):
        raise AtlasValidationError("energy_hessian must be finite")
    if not np.allclose(h, np.swapaxes(h, -1, -2), rtol=1.0e-12, atol=1.0e-14):
        raise AtlasValidationError("energy_hessian must be symmetric")
    if h.size:
        eig_min = np.min(np.linalg.eigvalsh(h), axis=-1)
        if np.any(eig_min < -1.0e-12):
            raise AtlasValidationError("energy_hessian must be positive semidefinite")
    return h


def _as_batched_constraints(
    constraint_jacobian: object | None,
    constraint_rhs: object | None,
    batch_size: int,
    mode_count: int,
) -> tuple[object, object] | None:
    if constraint_jacobian is None:
        if constraint_rhs is not None:
            raise AtlasValidationError("constraint_rhs requires constraint_jacobian")
        return None
    if constraint_rhs is None:
        raise AtlasValidationError("constraint_rhs is required with constraint_jacobian")
    c_jac = np.asarray(constraint_jacobian, dtype=float)
    if c_jac.ndim == 2:
        if c_jac.shape[1] != mode_count:
            raise AtlasValidationError("constraint_jacobian must have shape (p,k) or (batch,p,k)")
        c_jac = np.broadcast_to(c_jac[None, :, :], (batch_size, c_jac.shape[0], mode_count))
    if c_jac.ndim != 3 or c_jac.shape[0] != batch_size or c_jac.shape[2] != mode_count:
        raise AtlasValidationError("constraint_jacobian must have shape (p,k) or (batch,p,k)")
    if not np.all(np.isfinite(c_jac)):
        raise AtlasValidationError("constraint_jacobian must be finite")
    c_rhs = np.asarray(constraint_rhs, dtype=float)
    if c_rhs.ndim == 1:
        c_rhs = np.broadcast_to(c_rhs[None, :], (batch_size, c_jac.shape[1]))
    if c_rhs.shape != (batch_size, c_jac.shape[1]):
        raise AtlasValidationError("constraint_rhs must have shape (p,) or (batch,p)")
    if not np.all(np.isfinite(c_rhs)):
        raise AtlasValidationError("constraint_rhs must be finite")
    return c_jac, c_rhs
