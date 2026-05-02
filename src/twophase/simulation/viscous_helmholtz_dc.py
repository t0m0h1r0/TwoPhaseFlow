"""Defect-correction solver for implicit-BDF2 viscous Helmholtz systems.

Symbol mapping
--------------
``A_H`` -> high-order matrix-free Helmholtz operator
``A_L`` -> low-order sparse Helmholtz correction operator
``tau`` -> ``dt_effective`` = gamma * dt
``u_alpha`` -> one velocity component array
``mu`` -> dynamic viscosity field
``rho`` -> density field
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..core.boundary import is_periodic_axis, sync_periodic_image_nodes_many

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ns_terms.viscous import ViscousTerm


class ViscousHelmholtzDCSolver:
    """Solve Eq. ``eq:viscous_bdf2_dc`` by high-residual defect correction.

    The high operator is evaluated by ``ViscousTerm._evaluate`` so the fixed
    point is the same implicit-BDF2 equation as Eq. ``eq:helmholtz_implicit_bdf2``.
    The low operator is a second-order component-wise Helmholtz approximation
    that shares ``mu``, ``rho``, and periodic quotient constraints with the high
    operator.
    """

    def __init__(
        self,
        backend: "Backend",
        viscous_term: "ViscousTerm",
        *,
        tolerance: float = 1.0e-8,
        max_corrections: int = 3,
        relaxation: float = 0.8,
    ) -> None:
        if max_corrections <= 0:
            raise ValueError("max_corrections must be > 0")
        if tolerance <= 0.0:
            raise ValueError("tolerance must be > 0")
        if relaxation <= 0.0:
            raise ValueError("relaxation must be > 0")
        self.backend = backend
        self.xp = backend.xp
        self._viscous = viscous_term
        self.tolerance = float(tolerance)
        self.max_corrections = int(max_corrections)
        self.relaxation = float(relaxation)
        self.last_residual_history: list[float] = []
        self.last_diagnostics: dict[str, float] = {}

    def solve(
        self,
        *,
        base_velocity: list,
        explicit_acceleration: list,
        mu,
        rho,
        dt_effective: float,
        ccd: "CCDSolver",
        psi=None,
    ) -> tuple:
        """Return the DC approximation to the implicit viscous BDF2 state."""
        xp = self.xp
        rhs_components = [
            xp.asarray(base_velocity[component_index])
            + dt_effective * xp.asarray(explicit_acceleration[component_index])
            for component_index in range(len(base_velocity))
        ]
        self._sync_periodic(rhs_components, ccd)

        low_solver = _LowOrderViscousHelmholtzSolver(
            self.backend,
            ccd,
            xp.asarray(mu),
            xp.asarray(rho),
            reynolds_number=float(self._viscous.Re),
            dt_effective=float(dt_effective),
            component_count=len(rhs_components),
        )
        solution_components = low_solver.solve_components(rhs_components)
        self._sync_periodic(solution_components, ccd)

        scale = max(self._component_norm(rhs_components), 1.0)
        residual_history: list[float] = []
        stopped_by_tolerance = False

        for _correction_index in range(self.max_corrections):
            residual_components = self._residual_components(
                solution_components,
                rhs_components,
                mu,
                rho,
                ccd,
                psi=psi,
                dt_effective=dt_effective,
            )
            residual_components = self._zero_periodic_image_rhs(residual_components, ccd)
            residual_norm = self._component_norm(residual_components)
            residual_history.append(residual_norm)
            if residual_norm <= self.tolerance * scale:
                stopped_by_tolerance = True
                break

            correction_components = low_solver.solve_components(residual_components)
            solution_components = [
                solution_components[component_index]
                + self.relaxation * correction_components[component_index]
                for component_index in range(len(solution_components))
            ]
            self._sync_periodic(solution_components, ccd)

        self.last_residual_history = residual_history
        self.last_diagnostics = {
            "viscous_dc_corrections": float(len(residual_history)),
            "viscous_dc_converged": float(stopped_by_tolerance),
            "viscous_dc_low_factor_reuse": 1.0,
            "viscous_dc_final_residual": (
                float(residual_history[-1]) if residual_history else 0.0
            ),
        }
        return tuple(solution_components)

    def _residual_components(
        self,
        solution_components: list,
        rhs_components: list,
        mu,
        rho,
        ccd: "CCDSolver",
        *,
        psi,
        dt_effective: float,
    ) -> list:
        high_viscous_components = self._viscous._evaluate(
            solution_components,
            mu,
            rho,
            ccd,
            psi=psi,
        )
        return [
            rhs_components[component_index]
            - (
                solution_components[component_index]
                - dt_effective * high_viscous_components[component_index]
            )
            for component_index in range(len(solution_components))
        ]

    def _component_norm(self, components: list) -> float:
        flat = self.xp.concatenate([
            self.xp.asarray(component).ravel()
            for component in components
        ])
        return float(self.backend.asnumpy(self.xp.linalg.norm(flat)))

    def _sync_periodic(self, components: list, ccd: "CCDSolver") -> None:
        sync_periodic_image_nodes_many(components, ccd.bc_type)

    def _zero_periodic_image_rhs(self, components: list, ccd: "CCDSolver") -> list:
        constrained = [self.xp.asarray(component).copy() for component in components]
        for component in constrained:
            for axis_index in range(component.ndim):
                if not is_periodic_axis(ccd.bc_type, axis_index, component.ndim):
                    continue
                image_slice = [slice(None)] * component.ndim
                image_slice[axis_index] = -1
                component[tuple(image_slice)] = 0.0
        return constrained


class _LowOrderViscousHelmholtzSolver:
    """Factorized low-order ``A_L`` for one implicit viscous DC solve."""

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        mu,
        rho,
        *,
        reynolds_number: float,
        dt_effective: float,
        component_count: int,
    ) -> None:
        self.backend = backend
        self.xp = backend.xp
        self.ccd = ccd
        self.shape = tuple(ccd.grid.shape)
        self.ndim = len(self.shape)
        self.node_count = int(np.prod(self.shape))
        self.mu_host = np.asarray(backend.asnumpy(mu), dtype=np.float64)
        self.rho_host = np.asarray(backend.asnumpy(rho), dtype=np.float64)
        self.reynolds_number = float(reynolds_number)
        self.dt_effective = float(dt_effective)
        self.component_count = int(component_count)
        self._factors = [
            self._factor_component(component_index)
            for component_index in range(self.component_count)
        ]

    def solve_components(self, rhs_components: list) -> list:
        solution_components = []
        for component_index, rhs_component in enumerate(rhs_components):
            rhs_vector = np.asarray(
                self.backend.asnumpy(rhs_component),
                dtype=np.float64,
            ).ravel().copy()
            self._zero_periodic_image_rhs_vector(rhs_vector)
            rhs_device = self.xp.asarray(rhs_vector)
            solution_vector = self._factors[component_index].solve(rhs_device)
            solution_component = self.xp.asarray(solution_vector).reshape(self.shape)
            sync_periodic_image_nodes_many([solution_component], self.ccd.bc_type)
            solution_components.append(solution_component)
        return solution_components

    def _factor_component(self, component_index: int):
        matrix = self._build_component_matrix(component_index)
        return self.backend.sparse_linalg.splu(matrix)

    def _build_component_matrix(self, component_index: int):
        rows: list[int] = []
        columns: list[int] = []
        values: list[float] = []

        for node_index in np.ndindex(self.shape):
            row_index = self._flat_index(node_index)
            source_index, is_periodic_image = self._periodic_source_index(node_index)
            if is_periodic_image:
                rows.append(row_index)
                columns.append(row_index)
                values.append(1.0)
                rows.append(row_index)
                columns.append(self._flat_index(source_index))
                values.append(-1.0)
                continue

            row_entries = {row_index: 1.0}
            density = float(self.rho_host[node_index])
            scale = self.dt_effective / (self.reynolds_number * density)
            for axis_index in range(self.ndim):
                stress_weight = 2.0 if axis_index == component_index else 1.0
                for column_index, laplace_weight in self._axis_laplacian_entries(
                    node_index,
                    axis_index,
                ):
                    row_entries[column_index] = row_entries.get(column_index, 0.0) - (
                        scale * stress_weight * laplace_weight
                    )

            for column_index, value in row_entries.items():
                rows.append(row_index)
                columns.append(column_index)
                values.append(float(value))

        row_array = self.xp.asarray(np.asarray(rows, dtype=np.int32))
        column_array = self.xp.asarray(np.asarray(columns, dtype=np.int32))
        value_array = self.xp.asarray(np.asarray(values, dtype=np.float64))
        return self.backend.sparse.csc_matrix(
            (value_array, (row_array, column_array)),
            shape=(self.node_count, self.node_count),
        )

    def _axis_laplacian_entries(
        self,
        node_index: tuple[int, ...],
        axis_index: int,
    ) -> list[tuple[int, float]]:
        left_index = self._neighbor_index(node_index, axis_index, direction=-1)
        right_index = self._neighbor_index(node_index, axis_index, direction=1)
        entries: list[tuple[int, float]] = []
        diagonal_weight = 0.0

        if left_index is not None and right_index is not None:
            left_spacing = self._node_distance(left_index, node_index, axis_index)
            right_spacing = self._node_distance(node_index, right_index, axis_index)
            denominator = left_spacing + right_spacing
            left_weight = (
                2.0
                * self._face_mu(node_index, left_index)
                / (left_spacing * denominator)
            )
            right_weight = (
                2.0
                * self._face_mu(node_index, right_index)
                / (right_spacing * denominator)
            )
        elif left_index is not None:
            left_spacing = self._node_distance(left_index, node_index, axis_index)
            left_weight = 2.0 * self._face_mu(node_index, left_index) / (left_spacing ** 2)
            right_weight = 0.0
        elif right_index is not None:
            right_spacing = self._node_distance(node_index, right_index, axis_index)
            left_weight = 0.0
            right_weight = 2.0 * self._face_mu(node_index, right_index) / (right_spacing ** 2)
        else:
            return [(self._flat_index(node_index), 0.0)]

        if left_index is not None:
            entries.append((self._flat_index(left_index), left_weight))
            diagonal_weight -= left_weight
        if right_index is not None:
            entries.append((self._flat_index(right_index), right_weight))
            diagonal_weight -= right_weight
        entries.append((self._flat_index(node_index), diagonal_weight))
        return entries

    def _neighbor_index(
        self,
        node_index: tuple[int, ...],
        axis_index: int,
        *,
        direction: int,
    ) -> tuple[int, ...] | None:
        neighbor = list(node_index)
        axis_size = self.shape[axis_index]
        periodic_axis = is_periodic_axis(self.ccd.bc_type, axis_index, self.ndim)
        if periodic_axis:
            active_size = axis_size - 1
            neighbor[axis_index] = (neighbor[axis_index] + direction) % active_size
            return tuple(neighbor)

        next_position = neighbor[axis_index] + direction
        if next_position < 0 or next_position >= axis_size:
            return None
        neighbor[axis_index] = next_position
        return tuple(neighbor)

    def _node_distance(
        self,
        left_index: tuple[int, ...],
        right_index: tuple[int, ...],
        axis_index: int,
    ) -> float:
        coords = self.ccd.grid.coords[axis_index]
        left_position = float(coords[left_index[axis_index]])
        right_position = float(coords[right_index[axis_index]])
        if right_position > left_position:
            return right_position - left_position
        return right_position + float(self.ccd.grid.L[axis_index]) - left_position

    def _face_mu(
        self,
        node_index: tuple[int, ...],
        neighbor_index: tuple[int, ...],
    ) -> float:
        return 0.5 * (
            float(self.mu_host[node_index])
            + float(self.mu_host[neighbor_index])
        )

    def _periodic_source_index(
        self,
        node_index: tuple[int, ...],
    ) -> tuple[tuple[int, ...], bool]:
        source = list(node_index)
        changed = False
        for axis_index in range(self.ndim):
            if not is_periodic_axis(self.ccd.bc_type, axis_index, self.ndim):
                continue
            if source[axis_index] == self.shape[axis_index] - 1:
                source[axis_index] = 0
                changed = True
        return tuple(source), changed

    def _zero_periodic_image_rhs_vector(self, rhs_vector: np.ndarray) -> None:
        rhs_field = rhs_vector.reshape(self.shape)
        for axis_index in range(self.ndim):
            if not is_periodic_axis(self.ccd.bc_type, axis_index, self.ndim):
                continue
            image_slice = [slice(None)] * self.ndim
            image_slice[axis_index] = -1
            rhs_field[tuple(image_slice)] = 0.0

    def _flat_index(self, node_index: tuple[int, ...]) -> int:
        return int(np.ravel_multi_index(node_index, self.shape))

