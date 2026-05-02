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
        low_operator: str = "component",
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
        self.low_operator = _normalise_low_operator(low_operator)
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
            low_operator=self.low_operator,
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
            "viscous_dc_low_operator_scalar": (
                1.0 if low_solver.low_operator == "scalar" else 0.0
            ),
            "viscous_dc_fixed_pattern": 1.0,
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


_LOW_OPERATOR_ALIASES = {
    "component": "component",
    "tensor": "component",
    "componentwise": "component",
    "scalar": "scalar",
    "isotropic": "scalar",
}


def _normalise_low_operator(low_operator: str) -> str:
    key = str(low_operator).strip().lower()
    value = _LOW_OPERATOR_ALIASES.get(key, key)
    if value not in {"component", "scalar"}:
        raise ValueError("viscous DC low_operator must be component|scalar")
    return value


class _LowOrderViscousHelmholtzPattern:
    """Topology-only sparse pattern for the low-order Helmholtz operator."""

    _CACHE: dict[tuple, "_LowOrderViscousHelmholtzPattern"] = {}

    @classmethod
    def for_ccd(cls, ccd: "CCDSolver") -> "_LowOrderViscousHelmholtzPattern":
        shape = tuple(ccd.grid.shape)
        ndim = len(shape)
        key = (shape, ndim, repr(ccd.bc_type))
        pattern = cls._CACHE.get(key)
        if pattern is None:
            pattern = cls(ccd)
            cls._CACHE[key] = pattern
        return pattern

    def __init__(self, ccd: "CCDSolver") -> None:
        shape = tuple(ccd.grid.shape)
        ndim = len(shape)
        node_count = int(np.prod(shape))

        image_rows: list[int] = []
        image_cols: list[int] = []
        image_values: list[float] = []
        active_diag_rows: list[int] = []
        neighbor_rows: list[int] = []
        neighbor_cols: list[int] = []
        neighbor_axes: list[int] = []
        neighbor_sides: list[int] = []
        row_axis_positions: list[int] = []
        left_axis_positions: list[int] = []
        right_axis_positions: list[int] = []

        for node_index in np.ndindex(shape):
            row_index = int(np.ravel_multi_index(node_index, shape))
            source_index, is_periodic_image = self._periodic_source_index(
                node_index,
                shape,
                ndim,
                ccd.bc_type,
            )
            if is_periodic_image:
                image_rows.extend([row_index, row_index])
                image_cols.extend([
                    row_index,
                    int(np.ravel_multi_index(source_index, shape)),
                ])
                image_values.extend([1.0, -1.0])
                continue

            active_diag_rows.append(row_index)
            for axis_index in range(ndim):
                left_index = self._neighbor_index(
                    node_index,
                    shape,
                    ndim,
                    ccd.bc_type,
                    axis_index,
                    direction=-1,
                )
                right_index = self._neighbor_index(
                    node_index,
                    shape,
                    ndim,
                    ccd.bc_type,
                    axis_index,
                    direction=1,
                )
                left_axis_position = (
                    int(left_index[axis_index]) if left_index is not None else -1
                )
                right_axis_position = (
                    int(right_index[axis_index]) if right_index is not None else -1
                )
                for side, neighbor_index in ((-1, left_index), (1, right_index)):
                    if neighbor_index is None:
                        continue
                    neighbor_rows.append(row_index)
                    neighbor_cols.append(int(np.ravel_multi_index(neighbor_index, shape)))
                    neighbor_axes.append(axis_index)
                    neighbor_sides.append(side)
                    row_axis_positions.append(int(node_index[axis_index]))
                    left_axis_positions.append(left_axis_position)
                    right_axis_positions.append(right_axis_position)

        self.shape = shape
        self.ndim = ndim
        self.node_count = node_count
        self.image_rows = np.asarray(image_rows, dtype=np.int32)
        self.image_cols = np.asarray(image_cols, dtype=np.int32)
        self.image_values = np.asarray(image_values, dtype=np.float64)
        self.active_diag_rows = np.asarray(active_diag_rows, dtype=np.int32)
        self.neighbor_rows = np.asarray(neighbor_rows, dtype=np.int32)
        self.neighbor_cols = np.asarray(neighbor_cols, dtype=np.int32)
        self.neighbor_axes = np.asarray(neighbor_axes, dtype=np.int32)
        self.neighbor_sides = np.asarray(neighbor_sides, dtype=np.int8)
        self.row_axis_positions = np.asarray(row_axis_positions, dtype=np.int32)
        self.left_axis_positions = np.asarray(left_axis_positions, dtype=np.int32)
        self.right_axis_positions = np.asarray(right_axis_positions, dtype=np.int32)
        self.rows = np.concatenate([
            self.image_rows,
            self.active_diag_rows,
            self.neighbor_rows,
        ]).astype(np.int32, copy=False)
        self.cols = np.concatenate([
            self.image_cols,
            self.active_diag_rows,
            self.neighbor_cols,
        ]).astype(np.int32, copy=False)

    @staticmethod
    def _neighbor_index(
        node_index: tuple[int, ...],
        shape: tuple[int, ...],
        ndim: int,
        bc_type,
        axis_index: int,
        *,
        direction: int,
    ) -> tuple[int, ...] | None:
        neighbor = list(node_index)
        axis_size = shape[axis_index]
        if is_periodic_axis(bc_type, axis_index, ndim):
            active_size = axis_size - 1
            neighbor[axis_index] = (neighbor[axis_index] + direction) % active_size
            return tuple(neighbor)

        next_position = neighbor[axis_index] + direction
        if next_position < 0 or next_position >= axis_size:
            return None
        neighbor[axis_index] = next_position
        return tuple(neighbor)

    @staticmethod
    def _periodic_source_index(
        node_index: tuple[int, ...],
        shape: tuple[int, ...],
        ndim: int,
        bc_type,
    ) -> tuple[tuple[int, ...], bool]:
        source = list(node_index)
        changed = False
        for axis_index in range(ndim):
            if not is_periodic_axis(bc_type, axis_index, ndim):
                continue
            if source[axis_index] == shape[axis_index] - 1:
                source[axis_index] = 0
                changed = True
        return tuple(source), changed


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
        low_operator: str = "component",
    ) -> None:
        self.backend = backend
        self.xp = backend.xp
        self.ccd = ccd
        self.shape = tuple(ccd.grid.shape)
        self.ndim = len(self.shape)
        self.node_count = int(np.prod(self.shape))
        self.mu = self.xp.asarray(mu, dtype=self.xp.float64)
        self.rho = self.xp.asarray(rho, dtype=self.xp.float64)
        self.reynolds_number = float(reynolds_number)
        self.dt_effective = float(dt_effective)
        self.component_count = int(component_count)
        self.low_operator = _normalise_low_operator(low_operator)
        self.scalar_weight = (float(self.ndim) + 1.0) / float(self.ndim)
        self._factor_count = 1 if self.low_operator == "scalar" else self.component_count
        self._pattern = _LowOrderViscousHelmholtzPattern.for_ccd(ccd)
        self._pattern_rows = self.xp.asarray(self._pattern.rows)
        self._pattern_cols = self.xp.asarray(self._pattern.cols)
        self._image_values = self.xp.asarray(self._pattern.image_values)
        self._active_diag_rows = self.xp.asarray(self._pattern.active_diag_rows)
        self._neighbor_rows = self.xp.asarray(self._pattern.neighbor_rows)
        self._neighbor_cols = self.xp.asarray(self._pattern.neighbor_cols)
        self._neighbor_axes = self.xp.asarray(self._pattern.neighbor_axes)
        self._neighbor_sides = self.xp.asarray(self._pattern.neighbor_sides)
        self._row_axis_positions = self.xp.asarray(self._pattern.row_axis_positions)
        self._left_axis_positions = self.xp.asarray(self._pattern.left_axis_positions)
        self._right_axis_positions = self.xp.asarray(self._pattern.right_axis_positions)
        self._factors = [
            self._factor_component(component_index)
            for component_index in range(self._factor_count)
        ]

    def solve_components(self, rhs_components: list) -> list:
        if self.low_operator == "scalar":
            return self._solve_scalar_components(rhs_components)

        solution_components = []
        for component_index, rhs_component in enumerate(rhs_components):
            rhs_vector = self.xp.asarray(rhs_component, dtype=self.xp.float64).ravel().copy()
            self._zero_periodic_image_rhs_vector(rhs_vector)
            solution_vector = self._factors[component_index].solve(rhs_vector)
            solution_component = self.xp.asarray(solution_vector).reshape(self.shape)
            sync_periodic_image_nodes_many([solution_component], self.ccd.bc_type)
            solution_components.append(solution_component)
        return solution_components

    def _solve_scalar_components(self, rhs_components: list) -> list:
        rhs_vectors = []
        for rhs_component in rhs_components:
            rhs_vector = self.xp.asarray(rhs_component, dtype=self.xp.float64).ravel().copy()
            self._zero_periodic_image_rhs_vector(rhs_vector)
            rhs_vectors.append(rhs_vector)
        rhs_matrix = self.xp.stack(rhs_vectors, axis=1)
        solution_matrix = self._factors[0].solve(rhs_matrix)
        solution_components = []
        for component_index in range(len(rhs_components)):
            solution_component = self.xp.asarray(
                solution_matrix[:, component_index]
            ).reshape(self.shape)
            sync_periodic_image_nodes_many([solution_component], self.ccd.bc_type)
            solution_components.append(solution_component)
        return solution_components

    def _factor_component(self, component_index: int):
        matrix = self._build_component_matrix(component_index)
        return self.backend.sparse_linalg.splu(matrix)

    def _build_component_matrix(self, component_index: int):
        value_array = self._build_component_values(component_index)
        return self.backend.sparse.csc_matrix(
            (value_array, (self._pattern_rows, self._pattern_cols)),
            shape=(self.node_count, self.node_count),
        )

    def _build_component_values(self, component_index: int):
        xp = self.xp
        if self._neighbor_rows.size == 0:
            return xp.concatenate([
                self._image_values,
                xp.ones_like(self._active_diag_rows, dtype=xp.float64),
            ])

        mu_flat = self.mu.ravel()
        rho_flat = self.rho.ravel()
        row_indices = self._neighbor_rows
        neighbor_indices = self._neighbor_cols
        face_mu = 0.5 * (mu_flat[row_indices] + mu_flat[neighbor_indices])
        stencil_weights = self._neighbor_stencil_weights(face_mu)
        scale = self.dt_effective / (self.reynolds_number * rho_flat[row_indices])
        stress = self._stress_weights(component_index)
        increment = scale * stress * stencil_weights
        neighbor_values = -increment
        diagonal_increment = xp.zeros(self.node_count, dtype=xp.float64)
        xp.add.at(diagonal_increment, row_indices, increment)
        diagonal_values = (
            xp.ones_like(self._active_diag_rows, dtype=xp.float64)
            + diagonal_increment[self._active_diag_rows]
        )
        return xp.concatenate([self._image_values, diagonal_values, neighbor_values])

    def _stress_weights(self, component_index: int):
        if self.low_operator == "scalar":
            return self.xp.full_like(
                self._neighbor_axes,
                self.scalar_weight,
                dtype=self.xp.float64,
            )
        return self.xp.where(
            self._neighbor_axes == int(component_index),
            2.0,
            1.0,
        ).astype(self.xp.float64)

    def _neighbor_stencil_weights(self, face_mu):
        xp = self.xp
        weights = xp.zeros_like(face_mu, dtype=xp.float64)
        for axis_index in range(self.ndim):
            mask = self._neighbor_axes == axis_index
            coords = xp.asarray(
                np.asarray(self.ccd.grid.coords[axis_index], dtype=np.float64)
            )
            axis_length = float(self.ccd.grid.L[axis_index])
            row_positions = self._row_axis_positions[mask]
            left_positions = self._left_axis_positions[mask]
            right_positions = self._right_axis_positions[mask]
            side_values = self._neighbor_sides[mask]
            face_mu_axis = face_mu[mask]

            left_exists = left_positions >= 0
            right_exists = right_positions >= 0
            row_coords = coords[row_positions]
            safe_left_positions = xp.where(left_exists, left_positions, row_positions)
            safe_right_positions = xp.where(right_exists, right_positions, row_positions)
            left_spacing = self._forward_distance(
                coords[safe_left_positions],
                row_coords,
                axis_length,
            )
            right_spacing = self._forward_distance(
                row_coords,
                coords[safe_right_positions],
                axis_length,
            )
            spacing = xp.where(side_values < 0, left_spacing, right_spacing)
            both_sides = left_exists & right_exists
            denominator = xp.where(both_sides, left_spacing + right_spacing, spacing)
            weights[mask] = 2.0 * face_mu_axis / (spacing * denominator)
        return weights

    def _forward_distance(self, left_coords, right_coords, axis_length: float):
        distance = right_coords - left_coords
        return self.xp.where(distance > 0.0, distance, distance + axis_length)

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
        if not hasattr(self, "_mu_host_cache"):
            self._mu_host_cache = np.asarray(self.backend.asnumpy(self.mu), dtype=np.float64)
        return 0.5 * (
            float(self._mu_host_cache[node_index])
            + float(self._mu_host_cache[neighbor_index])
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
