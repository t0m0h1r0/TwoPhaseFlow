"""Factorized low-order FD correction solver for defect correction.

Paper mapping
-------------
In Eq. ``eq:dc_three_step``, this class supplies the low-order correction
operator ``L_L``.  It solves the same second-order conservative FD flux form as
the legacy sparse low-order PPE path, but prepares the pinned matrix once per
outer defect-correction solve and explicitly reuses that prepared solve flow
for all correction RHSs.

Symbol mapping
--------------
``rhs`` → defect ``d^{(k)}``; ``rho`` → low-order density coefficient field;
``prepare_operator`` → factorize ``L_L``; ``solve`` → apply ``L_L^{-1}``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..coupling.interface_stress_closure import (
    build_interface_stress_context,
    build_young_laplace_interface_stress_context,
)
from ..gpu_sparse_solve import _PreparedCuPySuperLUSolve
from .interfaces import IPPESolver
from .ppe_builder import PPEBuilder

if TYPE_CHECKING:
    from ..backend import Backend
    from ..core.boundary import BoundarySpec
    from ..core.grid import Grid
    from ..simulation.scheme_build_ctx import PPEBuildCtx


class PPESolverFDDirect(IPPESolver):
    """Pinned low-order FD direct solve with per-DC factor reuse."""

    scheme_names = ("fd_direct",)
    _scheme_aliases = {"fd_spsolve": "fd_direct"}

    @classmethod
    def _build(cls, name: str, ctx: "PPEBuildCtx") -> "PPESolverFDDirect":
        solver_cfg = getattr(getattr(ctx, "config", None), "solver", None)
        return cls(
            ctx.backend,
            ctx.grid,
            bc_type=ctx.bc_type,
            bc_spec=ctx.bc_spec,
            coefficient_scheme=getattr(
                solver_cfg,
                "ppe_coefficient_scheme",
                "phase_density",
            ),
            interface_coupling_scheme=getattr(
                solver_cfg,
                "ppe_interface_coupling_scheme",
                "none",
            ),
        )

    def __init__(
        self,
        backend: "Backend",
        grid: "Grid",
        bc_type: str = "wall",
        bc_spec: "BoundarySpec | None" = None,
        *,
        coefficient_scheme: str = "phase_density",
        interface_coupling_scheme: str = "none",
    ):
        self.backend = backend
        self.xp = backend.xp
        self.bc_type = bc_type
        self.bc_spec = bc_spec
        self.coefficient_scheme = str(coefficient_scheme).strip().lower()
        self.interface_coupling_scheme = str(interface_coupling_scheme).strip().lower()
        self._interface_stress_context = None
        self.ppb = self._make_builder(grid)
        self._refresh_structure(grid)
        self._factor = None
        self._reuse_static_operator = False
        self._prepared_rho_token = None

    def _make_builder(self, grid: "Grid") -> PPEBuilder:
        return PPEBuilder(
            self.backend,
            grid,
            self.bc_type,
            self.bc_spec,
            coefficient_scheme=self.coefficient_scheme,
            interface_coupling_scheme=self.interface_coupling_scheme,
            interface_stress_context=self._interface_stress_context,
        )

    def set_static_operator_cache(self, enabled: bool) -> None:
        self._reuse_static_operator = bool(enabled)
        if not enabled:
            self._prepared_rho_token = None

    def _refresh_structure(self, grid: "Grid") -> None:
        dummy_rho = np.ones(grid.shape, dtype=np.float64)
        structure_builder = PPEBuilder(
            self.backend,
            grid,
            self.bc_type,
            self.bc_spec,
        )
        triplet, shape = structure_builder.build(dummy_rho)
        self._rows = triplet[1]
        self._cols = triplet[2]
        self._shape = shape

    def update_grid(self, grid: "Grid") -> None:
        self.ppb = self._make_builder(grid)
        self._refresh_structure(grid)
        self._factor = None
        self._prepared_rho_token = None

    def invalidate_cache(self) -> None:
        self.ppb.invalidate_gpu_cache()
        self._factor = None
        self._prepared_rho_token = None

    def set_interface_jump_context(
        self,
        *,
        psi,
        kappa,
        sigma: float,
        psi_previous=None,
        pressure_jump_gas_minus_liquid=None,
        phase_threshold: float = 0.5,
        face_curvature_method: str = "nodal_cut_face",
        transport_variational_nodal_covector=None,
        transport_variational_psi=None,
        transport_variational_previous_surface_energy=None,
    ) -> None:
        """Bind affine-jump geometry to the low-order DC correction matrix."""
        if pressure_jump_gas_minus_liquid is None:
            self._interface_stress_context = (
                build_young_laplace_interface_stress_context(
                    xp=self.xp,
                    psi=psi,
                    kappa_lg=kappa,
                    sigma=sigma,
                    psi_previous=psi_previous,
                    face_curvature_method=face_curvature_method,
                    transport_variational_nodal_covector=(
                        transport_variational_nodal_covector
                    ),
                    transport_variational_psi=transport_variational_psi,
                    transport_variational_previous_surface_energy=(
                        transport_variational_previous_surface_energy
                    ),
                )
            )
        else:
            self._interface_stress_context = build_interface_stress_context(
                xp=self.xp,
                psi=psi,
                pressure_jump_gas_minus_liquid=pressure_jump_gas_minus_liquid,
                psi_previous=psi_previous,
                phase_threshold=phase_threshold,
                face_curvature_method=face_curvature_method,
                transport_variational_nodal_covector=(
                    transport_variational_nodal_covector
                ),
                transport_variational_psi=transport_variational_psi,
                transport_variational_previous_surface_energy=(
                    transport_variational_previous_surface_energy
                ),
            )
        self.ppb.set_interface_stress_context(self._interface_stress_context)
        self._factor = None
        self._prepared_rho_token = None

    def clear_interface_jump_context(self) -> None:
        """Clear affine-jump geometry from the low-order correction matrix."""
        self._interface_stress_context = None
        self.ppb.set_interface_stress_context(None)
        self._factor = None
        self._prepared_rho_token = None

    def prepare_operator(self, rho) -> None:
        rho_dev = self.xp.asarray(rho)
        rho_token = _static_rho_token(rho_dev)
        if (
            self._reuse_static_operator
            and self._factor is not None
            and self._prepared_rho_token == rho_token
        ):
            return
        data = self.ppb.build_values(rho_dev)
        if self.backend.is_gpu():
            matrix = self.backend.sparse.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        else:
            import scipy.sparse as sp

            matrix = sp.csc_matrix(
                (data, (self._rows, self._cols)),
                shape=self._shape,
            )
        factor = self.backend.sparse_linalg.splu(matrix)
        if self.backend.is_gpu():
            factor = _PreparedCuPySuperLUSolve(
                factor,
                rhs_shape=(self._shape[0], 1),
            )
        self._factor = factor
        self._prepared_rho_token = rho_token

    def solve(self, rhs, rho, dt: float = 0.0, p_init=None):
        if self._factor is None:
            self.prepare_operator(rho)
        rhs_vec = self.xp.asarray(rhs).ravel().copy()
        rhs_vec[self.ppb._pin_dof] = 0.0
        pressure_vec = self._factor.solve(rhs_vec)
        analysis_count = getattr(self._factor, "analysis_count", 0)
        self.last_diagnostics = {
            "ppe_fd_direct_factor_reuse": 1.0,
            "ppe_fd_direct_prepared_spsm_analysis_count": float(analysis_count),
        }
        return self.xp.asarray(pressure_vec).reshape(self.ppb.shape_field)


def _static_rho_token(rho) -> tuple:
    pointer = getattr(getattr(rho, "data", None), "ptr", None)
    dtype = getattr(getattr(rho, "dtype", None), "str", str(getattr(rho, "dtype", "")))
    return (id(rho), pointer, tuple(getattr(rho, "shape", ())), dtype)
