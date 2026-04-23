"""Workflow helpers for the iterative PPE solver.

Symbol mapping
--------------
``rhs_np`` -> PPE right-hand side ``q_h``
``rho_np`` -> density field ``ρ``
``dtau``   -> pseudo-time step ``Δτ``
``R``      -> nonlinear residual ``rhs - L(p)``
``pin``    -> gauge-fix degree of freedom
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings
from typing import Callable

import numpy as np

from .iterative_residuals import compute_density_gradient_3pt
from .iterative_smoothers import (
    step_iterative_adi,
    step_iterative_explicit,
    step_iterative_gauss_seidel,
)
from .iterative_state import (
    pack_iterative_solution_state,
    unpack_iterative_initial_pressure,
)


@dataclass(frozen=True)
class IterativeSolveContext:
    backend: object
    discretization: str
    method: str
    c_tau: float
    tol: float
    maxiter: int
    h: list[float]
    h_min: float
    ndim: int
    shape: tuple[int, ...]
    pin: int


def prepare_iterative_density_gradient(
    context: IterativeSolveContext,
    rho_np: np.ndarray,
    *,
    ccd,
) -> list[np.ndarray]:
    """Build the frozen density gradient field for one iterative solve."""
    if context.discretization == "ccd":
        from .ccd_ppe_utils import precompute_density_gradients

        return precompute_density_gradients(rho_np, ccd, context.backend)
    return compute_density_gradient_3pt(
        rho_np,
        h=context.h,
        ndim=context.ndim,
    )


def run_iterative_solve(
    context: IterativeSolveContext,
    *,
    rhs_np: np.ndarray,
    rho_np: np.ndarray,
    p_init,
    residual_ccd: Callable,
    residual_3pt: Callable,
    ccd,
    thomas_sweep: Callable,
):
    """Run the shared iterative PPE solve loop."""
    from .ccd_ppe_utils import check_convergence, compute_lts_dtau

    c_limit = 0.19 if context.discretization == "ccd" else 0.45
    c_eff = min(context.c_tau, c_limit) if context.method == "explicit" else context.c_tau
    dtau = compute_lts_dtau(rho_np, c_eff, context.h_min)

    p = unpack_iterative_initial_pressure(
        p_init,
        backend=context.backend,
        shape=context.shape,
    )
    drho = prepare_iterative_density_gradient(context, rho_np, ccd=ccd)

    last_dp: list[np.ndarray] = [np.zeros(context.shape) for _ in range(context.ndim)]
    last_d2p: list[np.ndarray] = [np.zeros(context.shape) for _ in range(context.ndim)]
    residual = np.inf
    converged = False

    for _ in range(context.maxiter):
        if context.discretization == "ccd":
            R, dp_list, d2p_list = residual_ccd(p, rhs_np, rho_np, drho)
        else:
            R, dp_list, d2p_list = residual_3pt(p, rhs_np, rho_np, drho)
        last_dp = dp_list
        last_d2p = d2p_list

        residual, converged = check_convergence(R, context.pin, context.tol)
        if converged:
            break

        neg_R = -R
        if context.method == "explicit":
            p = step_iterative_explicit(
                p,
                neg_R,
                dtau,
                pin=context.pin,
                ndim=context.ndim,
            )
        elif context.method == "gauss_seidel":
            p = step_iterative_gauss_seidel(
                p,
                neg_R,
                rho_np,
                drho,
                dtau,
                h=context.h,
                shape=context.shape,
                pin=context.pin,
            )
        elif context.method == "adi":
            p = step_iterative_adi(
                p,
                neg_R,
                rho_np,
                drho,
                dtau,
                pin=context.pin,
                thomas_sweep=thomas_sweep,
            )

    if not converged:
        warnings.warn(
            f"PPESolverIterative({context.discretization},{context.method}): "
            f"not converged after {context.maxiter} iterations "
            f"(residual={residual:.3e}, tol={context.tol:.3e}).",
            RuntimeWarning,
            stacklevel=2,
        )

    if not np.isfinite(p).all():
        warnings.warn(
            "PPESolverIterative: non-finite values detected. "
            "Check the density field or reduce pseudo_c_tau.",
            RuntimeWarning,
            stacklevel=2,
        )

    return pack_iterative_solution_state(
        p,
        last_dp,
        last_d2p,
        backend=context.backend,
    )


def compute_iterative_diagnostic_residual(
    context: IterativeSolveContext,
    *,
    p_np: np.ndarray,
    rhs_np: np.ndarray,
    rho_np: np.ndarray,
    residual_ccd: Callable,
    residual_3pt: Callable,
    ccd,
) -> float:
    """Return the residual norm used by diagnostics."""
    from .ccd_ppe_utils import check_convergence

    drho = prepare_iterative_density_gradient(context, rho_np, ccd=ccd)
    if context.discretization == "ccd":
        R, _, _ = residual_ccd(p_np, rhs_np, rho_np, drho)
    else:
        R, _, _ = residual_3pt(p_np, rhs_np, rho_np, drho)
    residual, _ = check_convergence(R, context.pin, 0.0)
    return residual
