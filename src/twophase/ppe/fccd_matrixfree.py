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
      -> legacy pressure-jump decomposition p = p_tilde + σκ(1-ψ)
      -> affine jump closure G_Γ(p;j_gl)=G(p)-B_Γj_gl,
         j_gl=p_gas-p_liquid=-σκ_lg
      -> PPESolverFCCDMatrixFree._face_inverse_density
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

import numpy as np

from ..core.array_checks import all_arrays_exact_zero
from ..simulation.interface_stress_closure import (
    build_young_laplace_interface_stress_context,
    interface_stress_context_is_active,
    signed_pressure_jump_gradient,
)
from .interfaces import IPPESolver
from .fccd_matrixfree_helpers import (
    apply_fccd_interface_jump,
    build_fccd_face_inverse_density,
    build_fccd_geometry_cache,
    build_fccd_interface_jump_context,
    compute_fccd_phase_weighted_means,
    fccd_interface_jump_is_active,
    project_fccd_rhs_compatibility,
    subtract_fccd_phase_means,
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


_WEIGHTED_DIV_INTERIOR_KERNEL = None
_WEIGHTED_DIV_BOUNDARY_KERNEL = None


def _get_weighted_divergence_kernels():
    """Return cached CuPy kernels for ``D_f[(1/rho)_f G_f p]`` accumulation."""
    global _WEIGHTED_DIV_INTERIOR_KERNEL, _WEIGHTED_DIV_BOUNDARY_KERNEL
    if _WEIGHTED_DIV_INTERIOR_KERNEL is None:
        import cupy as cp

        _WEIGHTED_DIV_INTERIOR_KERNEL = cp.ElementwiseKernel(
            "T out_old, T grad_hi, T grad_lo, T coeff_hi, T coeff_lo, T inv_width",
            "T out",
            "out = out_old + (coeff_hi * grad_hi - coeff_lo * grad_lo) * inv_width",
            "twophase_fccd_ppe_weighted_div_interior",
        )
        _WEIGHTED_DIV_BOUNDARY_KERNEL = cp.ElementwiseKernel(
            "T out_old, T grad, T coeff, T inv_width, T sign",
            "T out",
            "out = out_old + sign * coeff * grad * inv_width",
            "twophase_fccd_ppe_weighted_div_boundary",
        )
    return _WEIGHTED_DIV_INTERIOR_KERNEL, _WEIGHTED_DIV_BOUNDARY_KERNEL


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
        if self.interface_coupling_scheme not in {
            "none",
            "jump_decomposition",
            "affine_jump",
        }:
            raise ValueError(
                "FCCD PPE supports ppe_interface_coupling_scheme="
                "'none'|'jump_decomposition'|'affine_jump'"
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
        self._phase_mean_gauge_cache = None
        self._phase_mean_gauge_cache_host = None
        self._h_min = None
        self._node_width = None
        self._node_width_inv = None
        self._cell_volume = None
        self._cell_volume_host = None
        self._phase_threshold = None
        self._interface_jump_context = None
        self._interface_stress_context = None
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
        """Store legacy and affine pressure-jump data.

        Legacy ``jump_decomposition`` keeps its tested decomposition context.
        The affine path consumes the oriented Young--Laplace jump
        ``j_gl=p_gas-p_liquid=-σ κ_lg``.
        """
        self._interface_jump_context = build_fccd_interface_jump_context(
            xp=self.xp,
            backend=self.backend,
            psi=psi,
            kappa=kappa,
            sigma=sigma,
        )
        self._interface_stress_context = build_young_laplace_interface_stress_context(
            xp=self.xp,
            psi=psi,
            kappa_lg=kappa,
            sigma=sigma,
        )

    def prepare_operator(self, rho) -> None:
        """Cache density and optional diagonal preconditioner."""
        prepare_fccd_matrixfree_operator(self, rho)

    def apply(self, p):
        """Apply the FCCD PPE operator with its configured gauge constraint."""
        xp = self.xp
        if self._rho_dev is None or self._coeff_face is None:
            raise RuntimeError("prepare_operator(rho) must be called before apply(p)")
        return_host = self.backend.is_gpu() and not self._is_device_array(p)
        p_dev = xp.asarray(p)
        if self._uses_phase_mean_gauge():
            p_mean_free = self._project_phase_means(p_dev)
            out = self._apply_operator_core(p_mean_free)
            out = self._project_phase_means(out)
            out += p_dev
            out -= p_mean_free
        else:
            out = self._apply_operator_core(p_dev)
            self._pin_flat(out.ravel(), p_dev.ravel())
        if return_host:
            return np.asarray(self.backend.to_host(out))
        return out

    def _apply_operator_core(self, p_dev):
        """Apply physical ``D_f[(1/rho)_f G_f(p)]`` without a gauge row."""
        xp = self.xp
        out = xp.zeros_like(p_dev)
        for axis in range(self.ndim):
            grad_face = self.fccd.face_gradient(p_dev, axis)
            self._accumulate_weighted_face_gradient_divergence(
                out,
                grad_face,
                self._coeff_face[axis],
                axis,
            )
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
        return rhs_dev - self._apply_operator_core(jump_pressure)

    def _add_affine_interface_jump_rhs(self, rhs_dev, *, force: bool = False):
        """Apply affine jump closure: solve ``L(p)=rhs+D_f α_f B_Γ(j)``."""
        if (self._defer_interface_jump and not force) or not (
            self.interface_coupling_scheme == "affine_jump"
            and interface_stress_context_is_active(self._interface_stress_context)
        ):
            return rhs_dev
        affine_rhs = self.xp.zeros_like(rhs_dev)
        for axis in range(self.ndim):
            jump_gradient = signed_pressure_jump_gradient(
                xp=self.xp,
                grid=self.grid,
                context=self._interface_stress_context,
                axis=axis,
            )
            self._accumulate_weighted_face_gradient_divergence(
                affine_rhs,
                jump_gradient,
                self._coeff_face[axis],
                axis,
            )
        return rhs_dev + affine_rhs

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
        rhs_dev = self._add_affine_interface_jump_rhs(rhs_dev)
        rhs_dev = self._project_rhs_compatibility(rhs_dev)
        rhs_flat = rhs_dev.ravel()
        if (
            not self.backend.is_gpu()
            and all_arrays_exact_zero(xp, (rhs_flat,))
        ):
            sol = xp.zeros_like(rhs_dev)
            if not self._uses_phase_mean_gauge():
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
            if self._uses_phase_mean_gauge():
                x0 = self._project_phase_means(x0.reshape(self.grid.shape)).ravel()
            else:
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
                if self._uses_phase_mean_gauge():
                    z = self._project_phase_means(z)
                else:
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
        if self._uses_phase_mean_gauge():
            sol = self._project_phase_means(sol)
        else:
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

    def _project_rhs_compatibility(self, rhs, *, record_stats: bool = True):
        """Enforce one Neumann compatibility condition per phase block."""
        xp = self.xp if self._is_device_array(rhs) else np
        phase_cache = (
            self._phase_mean_gauge_cache
            if xp is self.xp
            else self._phase_mean_gauge_cache_host
        )
        rhs_projected, stats = project_fccd_rhs_compatibility(
            rhs=rhs,
            xp=xp,
            coefficient_scheme=self.coefficient_scheme,
            phase_threshold=self._phase_threshold,
            rho_dev=self._rho_dev,
            rho_host=self._rho,
            cell_volume_dev=self._cell_volume,
            cell_volume_host=self._cell_volume_host,
            phase_masks=None if phase_cache is None else phase_cache.masks,
            phase_weights=None if phase_cache is None else phase_cache.weights,
            phase_weight_sums=(
                None if phase_cache is None else phase_cache.weight_sums
            ),
            phase_weight_stack=(
                None if phase_cache is None else phase_cache.weight_stack
            ),
            phase_weight_sum_stack=(
                None if phase_cache is None else phase_cache.weight_sum_stack
            ),
            pin_dofs=self._pin_dofs,
            interface_coupling_scheme=self.interface_coupling_scheme,
            use_device_density=xp is self.xp,
            to_scalar=self._to_scalar,
            pin_rhs=not self._uses_phase_mean_gauge(),
            record_stats=record_stats,
        )
        if record_stats:
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
            interface_coupling_scheme=self.interface_coupling_scheme,
        )

    def _refresh_phase_gauges(self) -> None:
        refresh_fccd_phase_gauges(self)

    def _pin_flat(self, flat, value) -> None:
        for dof in self._pin_dofs:
            if np.isscalar(value):
                flat[dof] = value
            else:
                flat[dof] = value[dof]

    def _uses_phase_mean_gauge(self) -> bool:
        return (
            self.coefficient_scheme == "phase_separated"
            and self._phase_threshold is not None
        )

    def _project_phase_means(self, arr):
        """Project a field onto the per-phase zero-volume-mean pressure gauge."""
        xp = self.xp if self._is_device_array(arr) else np
        arr_view = xp.asarray(arr)
        if not self._uses_phase_mean_gauge():
            return arr_view
        phase_cache = (
            self._phase_mean_gauge_cache
            if xp is self.xp
            else self._phase_mean_gauge_cache_host
        )
        phase_means = compute_fccd_phase_weighted_means(
            xp=xp,
            arr=arr_view,
            cache=phase_cache,
        )
        return subtract_fccd_phase_means(
            xp=xp,
            arr=arr_view,
            cache=phase_cache,
            means=phase_means,
        )

    def _face_flux_divergence(self, face_flux, axis: int):
        """Divergence with wall Neumann rows retained for the PPE operator."""
        xp = self.xp
        if self.fccd.bc_type == "periodic":
            return self.fccd.face_divergence(face_flux, axis)

        flux = xp.moveaxis(xp.asarray(face_flux), axis, 0)
        N = self.grid.N[axis]
        width = self._broadcast_axis0(self._node_width[axis], flux.ndim)

        out = xp.empty((N + 1,) + flux.shape[1:], dtype=flux.dtype)
        out[1:N] = (flux[1:] - flux[:-1]) / width[1:N]
        out[0] = flux[0] / width[0]
        out[N] = -flux[N - 1] / width[N]
        return xp.moveaxis(out, 0, axis)

    def _accumulate_face_flux_divergence(self, out, face_flux, axis: int) -> None:
        """Accumulate ``D_f[(1/rho)_f G_f p]`` without a full-size copy."""
        xp = self.xp
        if self.fccd.bc_type == "periodic":
            out += self.fccd.face_divergence(face_flux, axis)
            return
        if self._node_width is None:
            self._refresh_grid_geometry_cache()
        flux = xp.moveaxis(xp.asarray(face_flux), axis, 0)
        out_axis0 = xp.moveaxis(out, axis, 0)
        N = self.grid.N[axis]
        width = self._broadcast_axis0(self._node_width[axis], flux.ndim)
        out_axis0[1:N] += (flux[1:] - flux[:-1]) / width[1:N]
        out_axis0[0] += flux[0] / width[0]
        out_axis0[N] -= flux[N - 1] / width[N]

    def _accumulate_weighted_face_gradient_divergence(
        self,
        out,
        grad_face,
        coeff_face,
        axis: int,
    ) -> None:
        """Fuse ``(1/rho)_f`` multiplication with FCCD flux divergence."""
        xp = self.xp
        if self.fccd.bc_type == "periodic":
            self._accumulate_face_flux_divergence(out, coeff_face * grad_face, axis)
            return
        if self._node_width_inv is None:
            self._refresh_grid_geometry_cache()
        grad = xp.moveaxis(xp.asarray(grad_face), axis, 0)
        coeff = xp.moveaxis(xp.asarray(coeff_face), axis, 0)
        out_axis0 = xp.moveaxis(out, axis, 0)
        N = self.grid.N[axis]
        inv_width = self._broadcast_axis0(self._node_width_inv[axis], grad.ndim)
        if self.backend.is_gpu():
            interior_kernel, boundary_kernel = _get_weighted_divergence_kernels()
            interior_kernel(
                out_axis0[1:N],
                grad[1:],
                grad[:-1],
                coeff[1:],
                coeff[:-1],
                inv_width[1:N],
                out_axis0[1:N],
            )
            boundary_kernel(
                out_axis0[0],
                grad[0],
                coeff[0],
                inv_width[0],
                1.0,
                out_axis0[0],
            )
            boundary_kernel(
                out_axis0[N],
                grad[N - 1],
                coeff[N - 1],
                inv_width[N],
                -1.0,
                out_axis0[N],
            )
            return
        out_axis0[1:N] += (
            coeff[1:] * grad[1:] - coeff[:-1] * grad[:-1]
        ) * inv_width[1:N]
        out_axis0[0] += coeff[0] * grad[0] * inv_width[0]
        out_axis0[N] -= coeff[N - 1] * grad[N - 1] * inv_width[N]

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
