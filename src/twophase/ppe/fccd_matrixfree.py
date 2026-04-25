"""Matrix-free FCCD pressure Poisson solver.

Symbol mapping:
    p      -> pressure correction
    rho    -> mixture density
    G_f(p) -> FCCD face gradient
    D_f    -> FCCD face-flux divergence
    chi    -> phase indicator derived from sharp density

A3 chain:
    §9 PPE: div((1/rho) grad p) = rhs
      -> FCCD discretisation: D_f[(1/rho)_f G_f(p)]
      -> PPESolverFCCDMatrixFree.apply
    SP-M phase-separated PPE:
      div((1/rho_q) grad p_q) = rhs_q, q∈{L,G}
      -> zero cross-phase FCCD face coupling + one pressure gauge per phase
      -> per-phase RHS compatibility projection
      -> pressure-jump decomposition p = p_tilde + σκ(1-ψ)
      -> PPESolverFCCDMatrixFree._face_inverse_density
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

import numpy as np

from ..core.array_checks import all_arrays_exact_zero
from .interfaces import IPPESolver
from .fccd_matrixfree_helpers import (
    apply_fccd_interface_jump,
    build_fccd_face_inverse_density,
    build_fccd_geometry_cache,
    build_fccd_interface_jump_context,
    fccd_interface_jump_is_active,
    project_fccd_rhs_compatibility,
)
from .fccd_matrixfree_lifecycle import (
    invalidate_fccd_matrixfree_cache,
    prepare_fccd_matrixfree_operator,
    refresh_fccd_geometry_cache,
    refresh_fccd_matrixfree_grid,
    refresh_fccd_phase_gauges,
)
from .gmres_helpers import backend_supports_gmres, solve_gmres

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.fccd import FCCDSolver
    from ..core.boundary import BoundarySpec
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import PPEBuildCtx


class PPESolverFCCDMatrixFree(IPPESolver):
    """Solve the variable-density PPE with FCCD face fluxes."""

    scheme_names = ("fccd_iterative",)
    _scheme_aliases = {"fccd_matrixfree": "fccd_iterative", "fccd": "fccd_iterative"}

    @classmethod
    def _build(cls, name: str, ctx: "PPEBuildCtx") -> "PPESolverFCCDMatrixFree":
        if ctx.fccd is None:
            raise ValueError("FCCD PPE requires PPEBuildCtx.fccd")
        return cls(ctx.backend, ctx.config, ctx.grid, ctx.fccd, bc_spec=ctx.bc_spec)

    def __init__(
        self,
        backend: "Backend",
        config,
        grid: "Grid",
        fccd: "FCCDSolver",
        *,
        bc_spec: "BoundarySpec | None" = None,
    ) -> None:
        self.backend = backend
        self.xp = backend.xp
        self.grid = grid
        self.ndim = grid.ndim
        self.fccd = fccd
        solver_cfg = getattr(config, "solver", config)
        self.tol = float(getattr(solver_cfg, "pseudo_tol", 1.0e-8))
        self.maxiter = int(getattr(solver_cfg, "pseudo_maxiter", 500))
        self.restart = getattr(solver_cfg, "ppe_restart", None)
        if self.restart is not None:
            self.restart = int(self.restart)
        self.preconditioner = str(
            getattr(solver_cfg, "ppe_preconditioner", "none")
        ).strip().lower()
        self.coefficient_scheme = str(
            getattr(solver_cfg, "ppe_coefficient_scheme", "phase_density")
        ).strip().lower()
        self.interface_coupling_scheme = str(
            getattr(solver_cfg, "ppe_interface_coupling_scheme", "none")
        ).strip().lower()
        if self.coefficient_scheme not in {"phase_density", "phase_separated"}:
            raise ValueError(
                "FCCD PPE supports ppe_coefficient_scheme="
                "'phase_density'|'phase_separated'"
            )
        if self.interface_coupling_scheme not in {"none", "jump_decomposition"}:
            raise ValueError(
                "FCCD PPE supports ppe_interface_coupling_scheme="
                "'none'|'jump_decomposition'"
            )
        if (
            self.coefficient_scheme == "phase_density"
            and self.interface_coupling_scheme != "none"
        ):
            raise ValueError("phase_density PPE requires interface_coupling='none'")
        if self.preconditioner not in {"jacobi", "none"}:
            raise ValueError("FCCD PPE supports preconditioner='jacobi'|'none'")
        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        else:
            centre_idx = tuple(n // 2 for n in grid.N)
            self._pin_dof = int(np.ravel_multi_index(centre_idx, grid.shape))
        self._pin_dofs = (self._pin_dof,)
        self._rho = None
        self._rho_dev = None
        self._diag_inv = None
        self._coeff_face = None
        self._h_min = None
        self._node_width = None
        self._phase_threshold = None
        self._interface_jump_context = None
        self._defer_interface_jump = False
        self.last_base_pressure = None
        self.last_diagnostics = {}
        self._refresh_grid_geometry_cache()

    def update_grid(self, grid: "Grid | None" = None) -> None:
        """Refresh grid-dependent FCCD weights after mesh rebuild."""
        refresh_fccd_matrixfree_grid(self, grid=grid)

    def invalidate_cache(self) -> None:
        """Drop density-dependent cached preconditioner state."""
        invalidate_fccd_matrixfree_cache(self)

    def set_interface_jump_context(self, *, psi, kappa, sigma: float) -> None:
        """Store SP-M pressure-jump data for ``p = p_tilde + σκ(1-ψ)``."""
        self._interface_jump_context = build_fccd_interface_jump_context(
            xp=self.xp,
            backend=self.backend,
            psi=psi,
            kappa=kappa,
            sigma=sigma,
        )

    def prepare_operator(self, rho) -> None:
        """Cache density and optional diagonal preconditioner."""
        prepare_fccd_matrixfree_operator(self, rho)

    def apply(self, p):
        """Apply ``D_f[(1/rho)_f G_f(p)]`` with a pinned gauge DOF."""
        xp = self.xp
        if self._rho_dev is None or self._coeff_face is None:
            raise RuntimeError("prepare_operator(rho) must be called before apply(p)")
        return_host = self.backend.is_gpu() and not self._is_device_array(p)
        p_dev = xp.asarray(p)
        out = xp.zeros_like(p_dev)
        for axis in range(self.ndim):
            grad_face = self.fccd.face_gradient(p_dev, axis)
            coeff_face = self._coeff_face[axis]
            out = out + self._face_flux_divergence(coeff_face * grad_face, axis)
        self._pin_flat(out.ravel(), p_dev.ravel())
        if return_host:
            return np.asarray(self.backend.to_host(out))
        return out

    def _subtract_interface_jump_operator(self, rhs_dev):
        """Apply jump decomposition: solve ``L(p_tilde)=rhs-L(J)``."""
        if self._defer_interface_jump or not fccd_interface_jump_is_active(
            coefficient_scheme=self.coefficient_scheme,
            interface_coupling_scheme=self.interface_coupling_scheme,
            interface_jump_context=self._interface_jump_context,
        ):
            return rhs_dev
        jump_pressure = self.apply_interface_jump(self.xp.zeros_like(rhs_dev))
        return rhs_dev - self.apply(jump_pressure)

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        """Solve the FCCD PPE with backend GMRES."""
        la = self.backend.sparse_linalg
        if not backend_supports_gmres(la):
            raise RuntimeError("FCCD matrix-free PPE requires backend GMRES")

        xp = self.xp
        return_host = self.backend.is_gpu() and not self._is_device_array(rhs)
        rhs_dev = xp.asarray(rhs)
        self.prepare_operator(rho)
        rhs_dev = self._subtract_interface_jump_operator(rhs_dev)
        rhs_dev = self._project_rhs_compatibility(rhs_dev)
        rhs_flat = rhs_dev.ravel().copy()
        if all_arrays_exact_zero(xp, (rhs_flat,)):
            sol = xp.zeros_like(rhs_dev)
            self._pin_flat(sol.ravel(), 0.0)
            self.last_base_pressure = xp.copy(sol)
            if not self._defer_interface_jump:
                sol = self.apply_interface_jump(sol)
            if return_host:
                return np.asarray(self.backend.to_host(sol))
            return sol

        if p_init is None:
            x0 = xp.zeros_like(rhs_flat)
        else:
            x0 = xp.asarray(p_init).ravel().copy()
            self._pin_flat(x0, 0.0)

        n_dof = int(np.prod(self.grid.shape))

        def _matvec(p_flat):
            return self.apply(xp.asarray(p_flat).reshape(self.grid.shape)).ravel()

        A = la.LinearOperator((n_dof, n_dof), matvec=_matvec, dtype=rhs_flat.dtype)
        M = None
        if self.preconditioner == "jacobi":
            if self._diag_inv is None:
                raise RuntimeError("Jacobi preconditioner is not initialised")

            def _precond(r_flat):
                z = xp.asarray(r_flat).reshape(self.grid.shape) * self._diag_inv
                self._pin_flat(z.ravel(), 0.0)
                return z.ravel()

            M = la.LinearOperator((n_dof, n_dof), matvec=_precond, dtype=rhs_flat.dtype)

        sol_flat, info = solve_gmres(
            la,
            A,
            rhs_flat,
            x0=x0,
            preconditioner=M,
            restart=self.restart,
            maxiter=self.maxiter,
            tolerance=self.tol,
        )

        if info != 0:
            warnings.warn(
                f"PPESolverFCCDMatrixFree did not converge cleanly (info={info}).",
                RuntimeWarning,
                stacklevel=2,
            )
        sol = xp.asarray(sol_flat).reshape(self.grid.shape)
        self._pin_flat(sol.ravel(), 0.0)
        self.last_base_pressure = xp.copy(sol)
        if not self._defer_interface_jump:
            sol = self.apply_interface_jump(sol)
        if return_host:
            return np.asarray(self.backend.to_host(sol))
        return sol

    def apply_interface_jump(self, pressure):
        """Apply the stored sharp-interface pressure jump decomposition."""
        return apply_fccd_interface_jump(
            pressure=pressure,
            coefficient_scheme=self.coefficient_scheme,
            interface_coupling_scheme=self.interface_coupling_scheme,
            interface_jump_context=self._interface_jump_context,
            backend=self.backend,
            xp=self.xp,
            is_device_array=self._is_device_array,
        )

    def _project_rhs_compatibility(self, rhs):
        """Enforce one Neumann compatibility condition per phase block."""
        xp = self.xp if self._is_device_array(rhs) else np
        rhs_projected, stats = project_fccd_rhs_compatibility(
            rhs=rhs,
            xp=xp,
            coefficient_scheme=self.coefficient_scheme,
            phase_threshold=self._phase_threshold,
            rho_dev=self._rho_dev,
            rho_host=self._rho,
            pin_dofs=self._pin_dofs,
            interface_coupling_scheme=self.interface_coupling_scheme,
            use_device_density=xp is self.xp,
            to_scalar=self._to_scalar,
        )
        self.last_diagnostics = stats
        return rhs_projected

    def _face_inverse_density(self, rho, axis: int):
        return build_fccd_face_inverse_density(
            xp=self.xp if self._is_device_array(rho) else np,
            rho=rho,
            axis=axis,
            ndim=self.ndim,
            grid=self.grid,
            coefficient_scheme=self.coefficient_scheme,
            phase_threshold=self._phase_threshold,
        )

    def _refresh_phase_gauges(self) -> None:
        refresh_fccd_phase_gauges(self)

    def _pin_flat(self, flat, value) -> None:
        for dof in self._pin_dofs:
            if np.isscalar(value):
                flat[dof] = value
            else:
                flat[dof] = value[dof]

    def _face_flux_divergence(self, face_flux, axis: int):
        """Divergence with wall Neumann rows retained for the PPE operator."""
        xp = self.xp
        if self.fccd.bc_type == "periodic":
            return self.fccd.face_divergence(face_flux, axis)

        flux = xp.moveaxis(xp.asarray(face_flux), axis, 0)
        N = self.grid.N[axis]
        width = self._broadcast_axis0(self._node_width[axis], flux.ndim)

        out = xp.zeros((N + 1,) + flux.shape[1:], dtype=flux.dtype)
        out[1:N] = (flux[1:] - flux[:-1]) / width[1:N]
        out[0] = flux[0] / width[0]
        out[N] = -flux[N - 1] / width[N]
        return xp.moveaxis(out, 0, axis)

    def _refresh_grid_geometry_cache(self) -> None:
        """Cache per-axis geometric scalars reused across every GMRES matvec."""
        refresh_fccd_geometry_cache(self)

    def _broadcast_axis0(self, values, ndim: int):
        shape = [1] * ndim
        shape[0] = -1
        return values.reshape(shape)

    def _is_device_array(self, arr) -> bool:
        return self.backend.is_gpu() and hasattr(arr, "__cuda_array_interface__")

    def _to_scalar(self, value) -> float:
        if self._is_device_array(value):
            return float(self.backend.asnumpy(value))
        return float(value)
