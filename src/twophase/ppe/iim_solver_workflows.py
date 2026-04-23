"""Workflow helpers for IIM PPE solver backends.

Symbol mapping
--------------
``rhs_np``   -> PPE right-hand side
``rho_np``   -> density field ``ρ``
``phi_np``   -> signed level-set field ``φ``
``kap_np``   -> curvature ``κ``
``p_jump``   -> decomposed jump field ``σκ(1-H_ε(φ))``
``drho``     -> density gradients
"""

from __future__ import annotations

import warnings

import numpy as np


def solve_iim_decomp_backend(solver, rhs, rho, dt, p_init, *, phi, kappa, sigma):
    """Solve the jump-decomposition IIM backend."""
    rho_np = np.asarray(solver.backend.to_host(rho), dtype=float)
    rhs_np = np.asarray(solver.backend.to_host(rhs), dtype=float)
    has_iim = phi is not None and kappa is not None and sigma > 0.0

    if has_iim:
        phi_np = np.asarray(solver.backend.to_host(phi), dtype=float)
        kap_np = np.asarray(solver.backend.to_host(kappa), dtype=float)
        rho_smooth, p_jump = build_iim_decomposition_fields(
            rho_np=rho_np,
            phi_np=phi_np,
            kap_np=kap_np,
            sigma=sigma,
            h=solver._h_min,
        )
        from .ccd_ppe_utils import precompute_density_gradients

        drho_s = precompute_density_gradients(rho_smooth, solver.ccd, solver.backend)
        p_tilde = solve_iim_dc_smooth(
            solver,
            rhs_np=rhs_np,
            rho_np=rho_smooth,
            drho_np=drho_s,
            p_init=None,
        )
        solver._last_jump_field = sigma * kap_np
        return solver.backend.to_device(p_tilde + p_jump)

    from .ccd_ppe_utils import precompute_density_gradients

    drho = precompute_density_gradients(rho_np, solver.ccd, solver.backend)
    p = solve_iim_dc_smooth(
        solver,
        rhs_np=rhs_np,
        rho_np=rho_np,
        drho_np=drho,
        p_init=p_init,
    )
    return solver.backend.to_device(p)


def build_iim_decomposition_fields(*, rho_np, phi_np, kap_np, sigma: float, h: float):
    """Build smoothed density and explicit jump field for IIM decomposition."""
    rho_l = float(np.max(rho_np))
    rho_g = float(np.min(rho_np))
    eps = 1.5 * h
    H_smooth = 0.5 * (1.0 + np.tanh(phi_np / (2.0 * eps)))
    rho_smooth = rho_l + (rho_g - rho_l) * H_smooth
    p_jump = sigma * kap_np * (1.0 - H_smooth)
    return rho_smooth, p_jump


def solve_iim_lu_smooth(solver, rhs_np, rho_np, drho_np):
    """Kronecker LU solve for smooth fields."""
    L_sparse = solver._build_sparse_operator(rho_np, drho_np)

    from ..core.boundary import pin_sparse_row

    pin_dof = solver._bc_spec.pin_dof
    L_lil = L_sparse.tolil()
    rhs_flat = rhs_np.ravel().copy()
    pin_sparse_row(L_lil, rhs_flat, pin_dof)
    L_pinned = L_lil.tocsr()

    p_flat = solver._spsolve(L_pinned, rhs_flat)
    if not np.isfinite(p_flat).all():
        warnings.warn(
            "PPESolverIIM(decomp): LU returned non-finite values.",
            RuntimeWarning,
            stacklevel=2,
        )
    return p_flat.reshape(solver.grid.shape)


def solve_iim_dc_smooth(solver, rhs_np, rho_np, drho_np, p_init=None):
    """Solve a smooth PPE field by the DC iteration used in IIM backends."""
    from .ccd_ppe_utils import (
        check_convergence,
        compute_ccd_laplacian_with_derivatives,
        compute_lts_dtau,
    )
    from .thomas_sweep_legacy import thomas_sweep_1d

    shape = solver.grid.shape
    dtau = compute_lts_dtau(rho_np, solver._c_tau, solver._h_min)
    p = np.zeros(shape, dtype=float) if p_init is None else np.asarray(p_init, dtype=float)

    pin_dof = solver._bc_spec.pin_dof
    converged = False
    residual = float("inf")

    for _ in range(solver.maxiter):
        Lp, _, _ = compute_ccd_laplacian_with_derivatives(
            p,
            rho_np,
            drho_np,
            solver.ccd,
            solver.backend,
        )
        R = rhs_np - Lp
        residual, converged = check_convergence(R, pin_dof, solver.tol)
        if converged:
            break

        q = thomas_sweep_1d(R, rho_np, drho_np[0], dtau, axis=0, grid=solver.grid)
        q.ravel()[pin_dof] = 0.0
        dp = thomas_sweep_1d(q, rho_np, drho_np[1], dtau, axis=1, grid=solver.grid)
        dp.ravel()[pin_dof] = 0.0
        p = p + dp
        p.ravel()[pin_dof] = 0.0

    if not converged:
        warnings.warn(
            f"PPESolverIIM(decomp+dc): did not converge ({residual:.3e}).",
            RuntimeWarning,
            stacklevel=2,
        )
    return p


def solve_iim_lu_backend(solver, rhs, rho, dt, p_init, *, phi, kappa, sigma):
    """Solve the legacy RHS-correction LU backend."""
    shape = solver.grid.shape
    rho_np = np.asarray(solver.backend.to_host(rho), dtype=float)
    rhs_np = np.asarray(solver.backend.to_host(rhs), dtype=float)

    from .ccd_ppe_utils import precompute_density_gradients
    from ..core.boundary import pin_sparse_row

    drho_np = precompute_density_gradients(rho_np, solver.ccd, solver.backend)
    L_sparse = solver._build_sparse_operator(rho_np, drho_np)
    rhs_flat = rhs_np.ravel().copy()

    if phi is not None and kappa is not None and sigma > 0.0:
        phi_np = np.asarray(solver.backend.to_host(phi), dtype=float)
        kap_np = np.asarray(solver.backend.to_host(kappa), dtype=float)
        dp_dx, dp_dy = None, None
        if solver._iim_mode == "hermite" and p_init is not None:
            p_prev = solver.xp.asarray(np.asarray(solver.backend.to_host(p_init), dtype=float))
            dp_dx_dev, _ = solver.ccd.differentiate(p_prev, 0)
            dp_dy_dev, _ = solver.ccd.differentiate(p_prev, 1)
            dp_dx = np.asarray(solver.backend.to_host(dp_dx_dev), dtype=float)
            dp_dy = np.asarray(solver.backend.to_host(dp_dy_dev), dtype=float)
        rhs_flat += solver._corrector.compute_correction(
            L_sparse,
            phi_np,
            kap_np,
            sigma,
            rho_np,
            rhs_np,
            dp_dx=dp_dx,
            dp_dy=dp_dy,
        )

    pin_dof = solver._bc_spec.pin_dof
    L_lil = L_sparse.tolil()
    pin_sparse_row(L_lil, rhs_flat, pin_dof)
    L_pinned = L_lil.tocsr()

    p_flat = solver._spsolve(L_pinned, rhs_flat)
    if not np.isfinite(p_flat).all():
        warnings.warn("PPESolverIIM(lu): non-finite values.", RuntimeWarning, stacklevel=2)
    return solver.backend.to_device(p_flat.reshape(shape))


def solve_iim_dc_backend(solver, rhs, rho, dt, p_init, *, phi, kappa, sigma):
    """Solve the legacy RHS-correction DC backend."""
    from .ccd_ppe_utils import (
        check_convergence,
        compute_ccd_laplacian_with_derivatives,
        compute_lts_dtau,
        precompute_density_gradients,
    )
    from .thomas_sweep_legacy import thomas_sweep_1d

    shape = solver.grid.shape
    rho_np = np.asarray(solver.backend.to_host(rho), dtype=float)
    rhs_np = np.asarray(solver.backend.to_host(rhs), dtype=float)

    phi_np = kap_np = None
    if phi is not None and kappa is not None and sigma > 0.0:
        phi_np = np.asarray(solver.backend.to_host(phi), dtype=float)
        kap_np = np.asarray(solver.backend.to_host(kappa), dtype=float)

    dtau = compute_lts_dtau(rho_np, solver._c_tau, solver._h_min)
    p = np.zeros(shape, dtype=float) if p_init is None else np.asarray(solver.backend.to_host(p_init), dtype=float)
    drho = precompute_density_gradients(rho_np, solver.ccd, solver.backend)
    pin_dof = solver._bc_spec.pin_dof

    converged = False
    residual = float("inf")
    for _ in range(solver.maxiter):
        Lp, dp_arrays, _ = compute_ccd_laplacian_with_derivatives(
            p,
            rho_np,
            drho,
            solver.ccd,
            solver.backend,
        )
        R = rhs_np - Lp
        if phi_np is not None and sigma > 0.0:
            L_sparse = solver._build_sparse_operator(rho_np, drho)
            R += solver._corrector.compute_correction(
                L_sparse,
                phi_np,
                kap_np,
                sigma,
                rho_np,
                rhs_np,
                dp_dx=dp_arrays[0] if dp_arrays else None,
                dp_dy=dp_arrays[1] if len(dp_arrays) > 1 else None,
            ).reshape(shape)

        residual, converged = check_convergence(R, pin_dof, solver.tol)
        if converged:
            break

        q = thomas_sweep_1d(R, rho_np, drho[0], dtau, axis=0, grid=solver.grid)
        q.ravel()[pin_dof] = 0.0
        dp = thomas_sweep_1d(q, rho_np, drho[1], dtau, axis=1, grid=solver.grid)
        dp.ravel()[pin_dof] = 0.0
        p = p + dp
        p.ravel()[pin_dof] = 0.0

    if not converged:
        warnings.warn(
            f"PPESolverIIM(dc): did not converge ({residual:.3e}).",
            RuntimeWarning,
            stacklevel=2,
        )
    return solver.backend.to_device(p)
