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
      -> PPESolverFCCDMatrixFree._face_inverse_density
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import warnings

import numpy as np

from .interfaces import IPPESolver

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
        if self.coefficient_scheme not in {"phase_density", "phase_separated"}:
            raise ValueError(
                "FCCD PPE supports ppe_coefficient_scheme="
                "'phase_density'|'phase_separated'"
            )
        if self.preconditioner not in {"jacobi", "none"}:
            raise ValueError("FCCD PPE supports preconditioner='jacobi'|'none'")
        if bc_spec is not None:
            self._pin_dof = bc_spec.pin_dof
        else:
            centre_idx = tuple(n // 2 for n in grid.N)
            self._pin_dof = int(np.ravel_multi_index(centre_idx, grid.shape))
        self._pin_dofs = (self._pin_dof,)
        self._rho = None
        self._diag_inv = None
        self._phase_threshold = None

    def update_grid(self, grid: "Grid | None" = None) -> None:
        """Refresh grid-dependent FCCD weights after mesh rebuild."""
        if grid is not None:
            self.grid = grid
            self.ndim = grid.ndim
            self.fccd.grid = grid
        self.fccd._weights = [
            self.fccd._precompute_weights(ax)
            for ax in range(self.fccd.ndim)
        ]
        self._rho = None
        self._diag_inv = None
        self._phase_threshold = None

    def invalidate_cache(self) -> None:
        """Drop density-dependent cached preconditioner state."""
        self._rho = None
        self._diag_inv = None
        self._phase_threshold = None

    def prepare_operator(self, rho) -> None:
        """Cache density and optional diagonal preconditioner."""
        xp = self.xp
        self._rho = xp.asarray(rho)
        self._diag_inv = None
        self._refresh_phase_gauges()
        if self.preconditioner == "jacobi":
            diag = xp.zeros_like(self._rho)
            for axis in range(self.ndim):
                h_min = float(np.min(np.diff(np.asarray(self.grid.coords[axis]))))
                diag -= 2.0 / (self._rho * h_min * h_min)
            self._pin_flat(diag.ravel(), 1.0)
            self._diag_inv = 1.0 / xp.where(xp.abs(diag) > 1.0e-30, diag, 1.0)

    def apply(self, p):
        """Apply ``D_f[(1/rho)_f G_f(p)]`` with a pinned gauge DOF."""
        xp = self.xp
        if self._rho is None:
            raise RuntimeError("prepare_operator(rho) must be called before apply(p)")
        out = xp.zeros_like(p)
        for axis in range(self.ndim):
            grad_face = self.fccd.face_gradient(p, axis)
            coeff_face = self._face_inverse_density(self._rho, axis)
            out = out + self._face_flux_divergence(coeff_face * grad_face, axis)
        self._pin_flat(out.ravel(), p.ravel())
        return out

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        """Solve the FCCD PPE with backend GMRES."""
        la = self.backend.sparse_linalg
        if not hasattr(la, "LinearOperator") or not hasattr(la, "gmres"):
            raise RuntimeError("FCCD matrix-free PPE requires backend GMRES")

        xp = self.xp
        rhs_dev = xp.asarray(rhs)
        self.prepare_operator(rho)
        rhs_flat = rhs_dev.ravel().copy()
        self._pin_flat(rhs_flat, 0.0)

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
                f"PPESolverFCCDMatrixFree did not converge cleanly (info={info}).",
                RuntimeWarning,
                stacklevel=2,
            )
        sol = xp.asarray(sol_flat).reshape(self.grid.shape)
        self._pin_flat(sol.ravel(), 0.0)
        return sol

    def _face_inverse_density(self, rho, axis: int):
        xp = self.xp
        ndim = self.ndim
        N = self.grid.N[axis]

        def sl(start, stop):
            s = [slice(None)] * ndim
            s[axis] = slice(start, stop)
            return tuple(s)

        rho_lo = rho[sl(0, N)]
        rho_hi = rho[sl(1, N + 1)]
        coeff = 2.0 / (rho_lo + rho_hi)
        if self.coefficient_scheme != "phase_separated":
            return coeff
        threshold = self._phase_threshold
        if threshold is None:
            return coeff
        same_phase = (rho_lo >= threshold) == (rho_hi >= threshold)
        return xp.where(same_phase, coeff, 0.0)

    def _refresh_phase_gauges(self) -> None:
        if self.coefficient_scheme != "phase_separated":
            self._pin_dofs = (self._pin_dof,)
            self._phase_threshold = None
            return
        rho_np = np.asarray(self.backend.asnumpy(self._rho), dtype=np.float64)
        rho_min = float(np.min(rho_np))
        rho_max = float(np.max(rho_np))
        if not np.isfinite(rho_min + rho_max) or abs(rho_max - rho_min) < 1.0e-14:
            self._pin_dofs = (self._pin_dof,)
            self._phase_threshold = None
            return
        threshold = 0.5 * (rho_min + rho_max)
        gas = np.flatnonzero(rho_np.ravel() < threshold)
        liquid = np.flatnonzero(rho_np.ravel() >= threshold)
        pins = []
        if gas.size:
            pins.append(int(gas[0]))
        if liquid.size:
            pins.append(int(liquid[0]))
        self._pin_dofs = tuple(sorted(set(pins))) or (self._pin_dof,)
        self._phase_threshold = threshold

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
        coords = np.asarray(self.grid.coords[axis], dtype=np.float64)
        face_width = coords[1:] - coords[:-1]
        node_width = np.empty_like(coords)
        node_width[0] = 0.5 * face_width[0]
        node_width[-1] = 0.5 * face_width[-1]
        node_width[1:-1] = 0.5 * (coords[2:] - coords[:-2])
        width = self._broadcast_axis0(self.xp.asarray(node_width), flux.ndim)

        out = xp.zeros((N + 1,) + flux.shape[1:], dtype=flux.dtype)
        out[1:N] = (flux[1:] - flux[:-1]) / width[1:N]
        out[0] = flux[0] / width[0]
        out[N] = -flux[N - 1] / width[N]
        return xp.moveaxis(out, 0, axis)

    def _broadcast_axis0(self, values, ndim: int):
        shape = [1] * ndim
        shape[0] = -1
        return values.reshape(shape)
