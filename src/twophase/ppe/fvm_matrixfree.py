"""Matrix-free FVM PPE solver with device-resident line preconditioning.

Implements the same FVM projection operator as :mod:`twophase.ppe.fvm_spsolve`,
but evaluates the operator matrix-free:

    L_FVM(rho) p = Σ_a D_a ( A_a(rho) G_a p )

The linear solve is performed by GMRES on a backend-native ``LinearOperator``.
For wall BC the preconditioner applies shifted line solves along each axis using
the variable-batched tridiagonal helper added in CHK-162.

This is an additive solver: the legacy :class:`PPESolverFVMSpsolve` remains the
fallback path and is used automatically for non-wall boundary conditions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

import numpy as np

from .interfaces import IPPESolver
from .fvm_spsolve import PPESolverFVMSpsolve

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..core.boundary import BoundarySpec


class PPESolverFVMMatrixFree(IPPESolver):
    """Matrix-free variable-density FVM PPE solver.

    The discretisation remains the project FVM PPE:

        ∇·[(1/ρ) ∇p] = rhs

    but the operator is applied matrix-free and solved by GMRES with a shifted
    line preconditioner.  The preconditioner is used only to accelerate the
    iteration; the fixed point is still the full FVM operator.
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
    ):
        self.backend = backend
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.bc_type = bc_type
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter
        self.c_tau = config.solver.pseudo_c_tau
        self.restart = min(40, max(10, self.maxiter))

        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        else:
            centre_idx = tuple(n // 2 for n in grid.N)
            self._pin_dof = int(np.ravel_multi_index(centre_idx, grid.shape))

        self._h_min = min(float(np.min(np.diff(np.asarray(c)))) for c in grid.coords)

        self._d_face: list = []
        self._dv_node: list = []
        for ax in range(self.ndim):
            coords = np.asarray(grid.coords[ax], dtype=np.float64)
            d_face = coords[1:] - coords[:-1]
            dv = np.empty_like(coords)
            dv[0] = d_face[0] / 2.0
            dv[-1] = d_face[-1] / 2.0
            dv[1:-1] = (coords[2:] - coords[:-2]) / 2.0

            face_shape = [1] * self.ndim
            node_shape = [1] * self.ndim
            face_shape[ax] = d_face.size
            node_shape[ax] = dv.size
            self._d_face.append(self.xp.asarray(d_face.reshape(face_shape)))
            self._dv_node.append(self.xp.asarray(dv.reshape(node_shape)))

        self._fallback = None
        if self.bc_type != "wall":
            self._fallback = PPESolverFVMSpsolve(
                backend, grid, bc_type=bc_type, bc_spec=bc_spec
            )

        self._operator_coeffs = None
        self._precond_coeffs = None

    def solve(self, rhs, rho, dt: float, p_init=None):
        """Solve the FVM PPE with matrix-free GMRES."""
        if self._fallback is not None:
            return self._fallback.solve(rhs, rho, dt, p_init=p_init)

        la = self.backend.sparse_linalg
        if not hasattr(la, "LinearOperator") or not hasattr(la, "gmres"):
            warnings.warn(
                "Matrix-free FVM solver unavailable on this backend; falling back "
                "to PPESolverFVMSpsolve.",
                RuntimeWarning,
                stacklevel=2,
            )
            return PPESolverFVMSpsolve(
                self.backend, self.grid, bc_type=self.bc_type
            ).solve(rhs, rho, dt, p_init=p_init)

        rho_dev = self.xp.asarray(rho)
        rhs_dev = self.xp.asarray(rhs)
        rhs_flat = rhs_dev.ravel().copy()
        rhs_flat[self._pin_dof] = 0.0

        self._operator_coeffs = [
            self.build_line_coeffs(rho_dev, ax) for ax in range(self.ndim)
        ]
        shift = 2.0 / (self.c_tau * rho_dev * (self._h_min ** 2))
        self._precond_coeffs = []
        for lower, main, upper in self._operator_coeffs:
            self._precond_coeffs.append((
                -lower,
                shift - main,
                -upper,
            ))

        if p_init is None:
            x0 = self.xp.zeros_like(rhs_flat)
        else:
            x0 = self.xp.asarray(p_init).ravel().copy()
            x0[self._pin_dof] = 0.0

        n_dof = int(np.prod(self.grid.shape))

        def _matvec(p_flat):
            p_field = self.xp.asarray(p_flat).reshape(self.grid.shape)
            out = self.apply(p_field)
            return out.ravel()

        def _precond(r_flat):
            r_field = self.xp.asarray(r_flat).reshape(self.grid.shape)
            z = self.apply_line_preconditioner(r_field)
            return z.ravel()

        A = la.LinearOperator((n_dof, n_dof), matvec=_matvec, dtype=rhs_flat.dtype)
        M = la.LinearOperator((n_dof, n_dof), matvec=_precond, dtype=rhs_flat.dtype)

        try:
            sol_flat, info = la.gmres(
                A,
                rhs_flat,
                x0=x0,
                M=M,
                restart=self.restart,
                maxiter=self.maxiter,
                atol=0.0,
                rtol=self.tol,
            )
        except TypeError:
            sol_flat, info = la.gmres(
                A,
                rhs_flat,
                x0=x0,
                M=M,
                restart=self.restart,
                maxiter=self.maxiter,
                tol=self.tol,
            )

        if info != 0:
            warnings.warn(
                f"PPESolverFVMMatrixFree did not converge cleanly (info={info}); "
                "falling back to PPESolverFVMSpsolve.",
                RuntimeWarning,
                stacklevel=2,
            )
            return PPESolverFVMSpsolve(
                self.backend, self.grid, bc_type=self.bc_type
            ).solve(rhs, rho, dt, p_init=p_init)

        sol = self.xp.asarray(sol_flat).reshape(self.grid.shape)
        sol.ravel()[self._pin_dof] = 0.0
        return sol

    def build_line_coeffs(self, rho, axis: int):
        """Return lower/main/upper arrays for all lines along ``axis``."""
        xp = self.xp
        N_ax = self.grid.N[axis]
        d_face = self._d_face[axis]
        dv = self._dv_node[axis]

        lower = xp.zeros_like(rho)
        main = xp.zeros_like(rho)
        upper = xp.zeros_like(rho)

        sl_lo = self._sl(axis, 0, N_ax)
        sl_hi = self._sl(axis, 1, N_ax + 1)

        rho_lo = rho[sl_lo]
        rho_hi = rho[sl_hi]
        coeff_face = 2.0 / (rho_lo + rho_hi) / d_face

        upper[self._sl(axis, 0, N_ax)] = coeff_face / dv[self._sl(axis, 0, N_ax)]
        lower[self._sl(axis, 1, N_ax + 1)] = coeff_face / dv[self._sl(axis, 1, N_ax + 1)]
        main[...] = -(lower + upper)
        return lower, main, upper

    def apply(self, p):
        """Apply the pinned matrix-free FVM operator to ``p``."""
        xp = self.xp
        out = xp.zeros_like(p)

        for axis, (lower, main, upper) in enumerate(self._operator_coeffs):
            out += main * p
            out[self._sl(axis, 1, self.grid.N[axis] + 1)] += (
                lower[self._sl(axis, 1, self.grid.N[axis] + 1)]
                * p[self._sl(axis, 0, self.grid.N[axis])]
            )
            out[self._sl(axis, 0, self.grid.N[axis])] += (
                upper[self._sl(axis, 0, self.grid.N[axis])]
                * p[self._sl(axis, 1, self.grid.N[axis] + 1)]
            )

        out_flat = out.ravel()
        p_flat = p.ravel()
        out_flat[self._pin_dof] = p_flat[self._pin_dof]
        return out

    def apply_line_preconditioner(self, r):
        """Apply the shifted additive line preconditioner."""
        xp = self.xp
        r_work = xp.asarray(r).copy()
        r_work.ravel()[self._pin_dof] = 0.0

        z = xp.zeros_like(r_work)
        for axis, (lower, diag, upper) in enumerate(self._precond_coeffs):
            z += self.backend.solve_tridiagonal_variable_batched(
                lower, diag, upper, r_work, axis=axis
            )

        z /= float(self.ndim)
        z.ravel()[self._pin_dof] = 0.0
        return z

    def _sl(self, axis: int, start: int, stop: int):
        sl = [slice(None)] * self.ndim
        sl[axis] = slice(start, stop)
        return tuple(sl)
