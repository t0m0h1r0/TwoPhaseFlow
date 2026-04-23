"""Non-hot advection composition helpers for `FCCDSolver`."""

from __future__ import annotations


def compute_fccd_flux_contribution(solver, u_k, phi, axis: int):
    """Conservative face-flux contribution for one axis."""
    prod = u_k * phi
    q_prod = solver._ccd.second_derivative(prod, axis)
    F_cons = solver.face_value(prod, axis, q=q_prod)
    return -solver.face_divergence(F_cons, axis)


def compute_fccd_advection_rhs(solver, velocity_components, scalar=None, mode: str = "flux"):
    """Compose FCCD nodal or flux-form advection RHS."""
    if mode not in ("node", "flux"):
        raise ValueError(f"mode must be 'node' or 'flux', got {mode!r}")

    xp = solver.xp
    ndim = len(velocity_components)
    q_cache = {}

    def get_q(field, ax):
        key = (id(field), ax)
        if key not in q_cache:
            q_cache[key] = solver._ccd.second_derivative(field, ax)
        return q_cache[key]

    if scalar is None:
        result = []
        for j in range(ndim):
            u_j = velocity_components[j]
            acc = xp.zeros_like(u_j)
            for k in range(ndim):
                u_k = velocity_components[k]
                if mode == "node":
                    q_j = get_q(u_j, k)
                    du_j_dk = solver.node_gradient(u_j, k, q=q_j)
                    acc -= u_k * du_j_dk
                else:
                    acc += compute_fccd_flux_contribution(solver, u_k, u_j, k)
            result.append(acc)
        return result

    psi = scalar
    acc = xp.zeros_like(psi)
    for k in range(ndim):
        u_k = velocity_components[k]
        if mode == "node":
            q_psi = get_q(psi, k)
            dpsi_dk = solver.node_gradient(psi, k, q=q_psi)
            acc -= u_k * dpsi_dk
        else:
            acc += compute_fccd_flux_contribution(solver, u_k, psi, k)
    return [acc]
