"""Matrix-free FVM PPE solver with device-resident line preconditioning.

Implements the same FVM projection operator as :mod:`twophase.ppe.fvm_spsolve`,
but evaluates the operator matrix-free:

    L_FVM(rho) p = Σ_a D_a ( A_a(rho) G_a p )

The linear solve is performed by GMRES on a backend-native ``LinearOperator``.
For wall BC the preconditioner can apply either cheap diagonal Jacobi scaling
or shifted line solves along each axis using the variable-batched tridiagonal
helper added in CHK-162.

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
    from ..simulation.scheme_build_ctx import PPEBuildCtx


class PPESolverFVMMatrixFree(IPPESolver):
    """Matrix-free variable-density FVM PPE solver.

    The discretisation remains the project FVM PPE:

        ∇·[(1/ρ) ∇p] = rhs

    but the operator is applied matrix-free and solved by GMRES with a shifted
    line preconditioner.  The preconditioner is used only to accelerate the
    iteration; the fixed point is still the full FVM operator.
    """

    scheme_names     = ("fvm_iterative",)
    _scheme_aliases  = {"fvm_matrixfree": "fvm_iterative", "matrixfree": "fvm_iterative"}

    @classmethod
    def _build(cls, name: str, ctx: "PPEBuildCtx") -> "PPESolverFVMMatrixFree":
        return cls(ctx.backend, ctx.config, ctx.grid, bc_type=ctx.bc_type, bc_spec=ctx.bc_spec)

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
        solver_cfg = getattr(config, "solver", config)
        self.tol = getattr(solver_cfg, "pseudo_tol", 1e-8)
        self.maxiter = getattr(solver_cfg, "pseudo_maxiter", 500)
        self.c_tau = getattr(solver_cfg, "pseudo_c_tau", 2.0)
        self.iteration_method = str(
            getattr(solver_cfg, "ppe_iteration_method", "gmres")
        ).strip().lower()
        if self.iteration_method in {"explicit", "gauss_seidel", "adi"}:
            self.iteration_method = "gmres"
        if self.iteration_method != "gmres":
            raise ValueError(
                "PPESolverFVMMatrixFree supports ppe_iteration_method='gmres' "
                f"today, got {self.iteration_method!r}"
            )
        restart = getattr(solver_cfg, "ppe_restart", None)
        self.restart = int(restart) if restart is not None else min(80, max(20, self.maxiter))
        self.preconditioner = str(
            getattr(solver_cfg, "ppe_preconditioner", "line_pcr")
        ).strip().lower()
        if self.preconditioner not in {"jacobi", "line_pcr", "none"}:
            raise ValueError(
                "ppe_preconditioner must be 'jacobi', 'line_pcr', or 'none', "
                f"got {self.preconditioner!r}"
            )
        pcr_stages = getattr(solver_cfg, "ppe_pcr_stages", 4)
        if pcr_stages is None:
            pcr_stages = 4
        self.precond_pcr_stages = (
            int(pcr_stages)
            if self.backend.is_gpu() and self.preconditioner == "line_pcr"
            else None
        )

        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        else:
            centre_idx = tuple(n // 2 for n in grid.N)
            self._pin_dof = int(np.ravel_multi_index(centre_idx, grid.shape))

        self._fallback = None
        if self.bc_type != "wall":
            self._fallback = PPESolverFVMSpsolve(
                backend, grid, bc_type=bc_type, bc_spec=bc_spec
            )

        self._operator_coeffs = None
        self._precond_coeffs = None
        self._diag_inv = None
        self._refresh_grid_metrics()

    def update_grid(self, grid: "Grid | None" = None) -> None:
        """Refresh metric caches after an in-place grid rebuild."""
        if grid is not None:
            self.grid = grid
            self.ndim = grid.ndim
        self._operator_coeffs = None
        self._precond_coeffs = None
        self._diag_inv = None
        self._refresh_grid_metrics()
        if self._fallback is not None:
            self._fallback = PPESolverFVMSpsolve(
                self.backend, self.grid, bc_type=self.bc_type
            )

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
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

        self.prepare_operator(rho_dev)
        self._precond_coeffs = None
        self._diag_inv = None
        if self.preconditioner == "line_pcr":
            shift = 2.0 / (self.c_tau * rho_dev * (self._h_min ** 2))
            self._precond_coeffs = []
            for lower, main, upper in self._operator_coeffs:
                self._precond_coeffs.append((
                    -lower,
                    shift - main,
                    -upper,
                ))
        elif self.preconditioner == "jacobi":
            diag = self.xp.zeros_like(rho_dev)
            for _lower, main, _upper in self._operator_coeffs:
                diag += main
            diag.ravel()[self._pin_dof] = 1.0
            self._diag_inv = 1.0 / self.xp.where(
                self.xp.abs(diag) > 1e-30,
                diag,
                1.0,
            )

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
            if self.preconditioner == "jacobi":
                z = self.apply_jacobi_preconditioner(r_field)
            else:
                z = self.apply_line_preconditioner(r_field)
            return z.ravel()

        A = la.LinearOperator((n_dof, n_dof), matvec=_matvec, dtype=rhs_flat.dtype)
        M = None
        if self.preconditioner in {"jacobi", "line_pcr"}:
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

    def prepare_operator(self, rho) -> None:
        """Build matrix-free FVM operator coefficients for the current density."""
        rho_dev = self.xp.asarray(rho)
        self._operator_coeffs = [
            self.build_line_coeffs(rho_dev, ax) for ax in range(self.ndim)
        ]

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
        if self._precond_coeffs is None:
            raise RuntimeError("line preconditioner coefficients are not initialised")
        r_work = xp.asarray(r).copy()
        r_work.ravel()[self._pin_dof] = 0.0

        z = xp.zeros_like(r_work)
        for axis, (lower, diag, upper) in enumerate(self._precond_coeffs):
            z += self.backend.solve_tridiagonal_variable_batched(
                lower,
                diag,
                upper,
                r_work,
                axis=axis,
                max_stages=self.precond_pcr_stages,
            )

        z /= float(self.ndim)
        z.ravel()[self._pin_dof] = 0.0
        return z

    def apply_jacobi_preconditioner(self, r):
        """Apply a diagonal Jacobi preconditioner on the active backend."""
        if self._diag_inv is None:
            raise RuntimeError("Jacobi preconditioner diagonal is not initialised")
        z = self.xp.asarray(r) * self._diag_inv
        z.ravel()[self._pin_dof] = 0.0
        return z

    def _sl(self, axis: int, start: int, stop: int):
        sl = [slice(None)] * self.ndim
        sl[axis] = slice(start, stop)
        return tuple(sl)

    def _refresh_grid_metrics(self) -> None:
        """Build backend-native face and control-volume spacing arrays."""
        self._h_min = min(
            float(np.min(np.diff(np.asarray(coord)))) for coord in self.grid.coords
        )
        self._d_face = []
        self._dv_node = []
        for axis in range(self.ndim):
            coords = np.asarray(self.grid.coords[axis], dtype=np.float64)
            d_face = coords[1:] - coords[:-1]
            dv = np.empty_like(coords)
            dv[0] = d_face[0] / 2.0
            dv[-1] = d_face[-1] / 2.0
            dv[1:-1] = (coords[2:] - coords[:-2]) / 2.0

            face_shape = [1] * self.ndim
            node_shape = [1] * self.ndim
            face_shape[axis] = d_face.size
            node_shape[axis] = dv.size
            self._d_face.append(self.xp.asarray(d_face.reshape(face_shape)))
            self._dv_node.append(self.xp.asarray(dv.reshape(node_shape)))
