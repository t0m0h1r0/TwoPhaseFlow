"""Concrete divergence and projection operators.

Symbol mapping
--------------
∇·u -> ``divergence(components)``
u_f -> ``face_components``
ρ_f^{-1} ∂p/∂n -> ``pressure_fluxes(p, rho)``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.array_checks import all_arrays_exact_zero
from .face_projection import (
    apply_pressure_projection,
    reconstruct_nodes_from_faces,
    zero_face_components,
)
from .gradient_operator import IDivergenceOperator
from ..coupling.interface_stress_closure import signed_pressure_jump_gradient

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ccd.fccd import FCCDSolver
    from ..core.grid import Grid


class CCDDivergenceOperator(IDivergenceOperator):
    """CCD divergence matching the legacy uniform-grid path."""

    def __init__(self, ccd: "CCDSolver") -> None:
        self._ccd = ccd

    def divergence(self, components: list["array"]) -> "array":
        """Compute nodal divergence via CCD differentiation."""
        div = None
        for axis, comp in enumerate(components):
            grad, _ = self._ccd.differentiate(comp, axis)
            div = grad if div is None else div + grad
        return div


class FVMDivergenceOperator(IDivergenceOperator):
    """Finite-volume divergence on the node-centred non-uniform grid."""

    def __init__(self, backend: "Backend", grid: "Grid") -> None:
        self.xp = backend.xp
        self._grid = grid
        self._dv = None
        self._d_face = None
        self.supports_zero_projection_shortcut = True

    def divergence(self, components: list["array"]) -> "array":
        """Compute divergence from face-averaged nodal fluxes."""
        face_components = self.face_fluxes(components)
        return self.divergence_from_faces(face_components)

    def face_fluxes(self, components: list["array"]) -> list["array"]:
        """Average nodal vector components to normal face fluxes."""
        faces = []
        ndim = self._grid.ndim
        for axis, comp in enumerate(components):
            n_cells = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            faces.append(0.5 * (comp[sl(0, n_cells)] + comp[sl(1, n_cells + 1)]))
        return faces

    def divergence_from_faces(self, face_components: list["array"]) -> "array":
        """Compute finite-volume divergence from normal face fluxes."""
        if self._dv is None:
            self._init_metrics()

        div = self.xp.zeros(self._grid.shape, dtype=face_components[0].dtype)
        ndim = self._grid.ndim
        for axis, face in enumerate(face_components):
            n_cells = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            term = self.xp.zeros_like(div)
            term[sl(1, n_cells)] = (
                face[sl(1, n_cells)] - face[sl(0, n_cells - 1)]
            ) / self._dv[axis][sl(1, n_cells)]
            term[sl(0, 1)] = face[sl(0, 1)] / self._dv[axis][sl(0, 1)]
            term[sl(n_cells, n_cells + 1)] = (
                -face[sl(n_cells - 1, n_cells)] / self._dv[axis][sl(n_cells, n_cells + 1)]
            )
            div = div + term
        return div

    def pressure_fluxes(self, p: "array", rho: "array") -> list["array"]:
        """Compute PPE-consistent face fluxes ``rho_face^-1 dp/dn``."""
        if self._d_face is None:
            self._init_metrics()

        faces = []
        ndim = self._grid.ndim
        for axis in range(ndim):
            n_cells = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            rho_l = rho[sl(0, n_cells)]
            rho_r = rho[sl(1, n_cells + 1)]
            coeff = 2.0 / (rho_l + rho_r)
            faces.append(coeff * (p[sl(1, n_cells + 1)] - p[sl(0, n_cells)]) / self._d_face[axis])
        return faces

    def reconstruct_nodes(self, face_components: list["array"]) -> list["array"]:
        """Reconstruct nodal components from corrected normal face fluxes."""
        return reconstruct_nodes_from_faces(self.xp, self._grid, face_components)

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """Apply PPE-consistent face-flux projection and reconstruct nodes."""
        return self.reconstruct_nodes(
            self.project_faces(
                components,
                p,
                rho,
                dt,
                force_components,
                pressure_gradient=pressure_gradient,
            )
        )

    def project_faces(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """Apply PPE-consistent projection and return corrected face fluxes."""
        faces = self.face_fluxes(components)
        p_faces = self.pressure_fluxes(p, rho)
        if force_components is None:
            force_faces = zero_face_components(self.xp, faces)
        else:
            force_faces = self.face_fluxes(force_components)

        return apply_pressure_projection(faces, p_faces, force_faces, dt)

    def _init_metrics(self) -> None:
        """Compute and cache face spacings and nodal control-volume widths."""
        import numpy as _np

        self._dv = []
        self._d_face = []
        for axis in range(self._grid.ndim):
            coords = _np.asarray(self._grid.coords[axis])
            d_face = coords[1:] - coords[:-1]
            dv = _np.empty_like(coords)
            dv[0] = 0.5 * (coords[1] - coords[0])
            dv[-1] = 0.5 * (coords[-1] - coords[-2])
            dv[1:-1] = 0.5 * (coords[2:] - coords[:-2])
            shape = [1] * self._grid.ndim
            shape[axis] = -1
            self._dv.append(self.xp.asarray(dv.reshape(shape)))
            self._d_face.append(self.xp.asarray(d_face.reshape(shape)))


class FCCDDivergenceOperator(IDivergenceOperator):
    """FCCD face-flux projector paired with FCCD gradient."""

    def __init__(self, fccd: "FCCDSolver") -> None:
        self._fccd = fccd
        self._node_width = None
        self.supports_zero_projection_shortcut = True

    def divergence(self, components: list["array"]) -> "array":
        xp = self._fccd.xp
        if (
            not self._fccd.backend.is_gpu()
            and all_arrays_exact_zero(xp, components)
        ):
            return xp.zeros_like(components[0])
        return self.divergence_from_faces(self.face_fluxes(components))

    def face_fluxes(self, components: list["array"]) -> list["array"]:
        """Evaluate nodal velocity components on normal faces."""
        return [self._fccd.face_value(comp, axis) for axis, comp in enumerate(components)]

    def divergence_from_faces(self, face_components: list["array"]) -> "array":
        """Compute FCCD divergence directly from normal face fluxes."""
        div = None
        for axis, face in enumerate(face_components):
            d = self._face_flux_divergence(face, axis)
            div = d if div is None else div + d
        return div

    def reconstruct_nodes(self, face_components: list["array"]) -> list["array"]:
        """Reconstruct nodal velocities from corrected face fluxes."""
        return reconstruct_nodes_from_faces(
            self._fccd.xp,
            self._fccd.grid,
            face_components,
        )

    def pressure_fluxes(
        self,
        p: "array",
        rho: "array",
        *,
        pressure_gradient: str = "fvm",
        coefficient_scheme: str = "phase_density",
        phase_threshold=None,
        interface_coupling_scheme: str = "none",
        interface_stress_context=None,
    ) -> list["array"]:
        """Compute PPE-consistent face pressure fluxes."""
        import numpy as _np

        xp = self._fccd.xp
        grid = self._fccd.grid
        ndim = grid.ndim
        faces = []
        for axis in range(ndim):
            n_cells = grid.N[axis]

            def sl(start, stop, ax=axis):
                s = [slice(None)] * ndim
                s[ax] = slice(start, stop)
                return tuple(s)

            d_face = _np.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
            shape = [1] * ndim
            shape[axis] = -1
            d_face_arr = xp.asarray(d_face.reshape(shape))

            rho_lo = rho[sl(0, n_cells)]
            rho_hi = rho[sl(1, n_cells + 1)]
            coeff = 2.0 / (rho_lo + rho_hi)
            if (
                coefficient_scheme == "phase_separated"
                and interface_coupling_scheme != "affine_jump"
            ):
                threshold = phase_threshold
                if threshold is None:
                    threshold = 0.5 * (xp.min(rho) + xp.max(rho))
                same_phase = (rho_lo >= threshold) == (rho_hi >= threshold)
                coeff = xp.where(same_phase, coeff, 0.0)
            if pressure_gradient == "fccd":
                pressure_face_gradient = self._fccd.face_gradient(p, axis)
            else:
                pressure_face_gradient = (
                    p[sl(1, n_cells + 1)] - p[sl(0, n_cells)]
                ) / d_face_arr
            if interface_coupling_scheme == "affine_jump":
                pressure_face_gradient = pressure_face_gradient - signed_pressure_jump_gradient(
                    xp=xp,
                    grid=grid,
                    context=interface_stress_context,
                    axis=axis,
                )
            face = coeff * pressure_face_gradient
            faces.append(face)
        return faces

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
        coefficient_scheme: str = "phase_density",
        phase_threshold=None,
        interface_coupling_scheme: str = "none",
        interface_stress_context=None,
    ) -> list["array"]:
        """FCCD face-flux projection (WIKI-T-068 §5)."""
        return self.reconstruct_nodes(
            self.project_faces(
                components,
                p,
                rho,
                dt,
                force_components,
                pressure_gradient=pressure_gradient,
                coefficient_scheme=coefficient_scheme,
                phase_threshold=phase_threshold,
                interface_coupling_scheme=interface_coupling_scheme,
                interface_stress_context=interface_stress_context,
            )
        )

    def project_faces(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
        coefficient_scheme: str = "phase_density",
        phase_threshold=None,
        interface_coupling_scheme: str = "none",
        interface_stress_context=None,
    ) -> list["array"]:
        """Apply FCCD face-flux projection and keep corrected faces."""
        xp = self._fccd.xp
        u_faces = self.face_fluxes(components)
        if force_components is None:
            f_faces = zero_face_components(xp, u_faces)
        else:
            f_faces = self.face_fluxes(force_components)

        p_faces = self.pressure_fluxes(
            p,
            rho,
            pressure_gradient=pressure_gradient,
            coefficient_scheme=coefficient_scheme,
            phase_threshold=phase_threshold,
            interface_coupling_scheme=interface_coupling_scheme,
            interface_stress_context=interface_stress_context,
        )
        return apply_pressure_projection(u_faces, p_faces, f_faces, dt)

    def update_weights(self) -> None:
        """Refresh FCCD geometric weights after in-place grid rebuild (WIKI-L-029)."""
        self._fccd._weights = [
            self._fccd._precompute_weights(axis)
            for axis in range(self._fccd.ndim)
        ]
        self._node_width = None

    def _face_flux_divergence(self, face_flux, axis: int):
        """Divergence paired with the FCCD PPE wall-control-volume rows."""
        if self._fccd.bc_type == "periodic":
            return self._fccd.face_divergence(face_flux, axis)
        if self._node_width is None:
            self._init_node_width()

        xp = self._fccd.xp
        flux = xp.moveaxis(xp.asarray(face_flux), axis, 0)
        n_cells = self._fccd.grid.N[axis]
        width = self._broadcast_axis0(self._node_width[axis], flux.ndim)

        out = xp.zeros((n_cells + 1,) + flux.shape[1:], dtype=flux.dtype)
        out[1:n_cells] = (flux[1:] - flux[:-1]) / width[1:n_cells]
        out[0] = flux[0] / width[0]
        out[n_cells] = -flux[n_cells - 1] / width[n_cells]
        return xp.moveaxis(out, 0, axis)

    def _init_node_width(self) -> None:
        """Cache nodal control-volume widths from physical coordinates."""
        import numpy as _np

        self._node_width = []
        for axis in range(self._fccd.grid.ndim):
            coords = _np.asarray(self._fccd.grid.coords[axis], dtype=_np.float64)
            d_face = coords[1:] - coords[:-1]
            width = _np.empty_like(coords)
            width[0] = 0.5 * d_face[0]
            width[-1] = 0.5 * d_face[-1]
            width[1:-1] = 0.5 * (coords[2:] - coords[:-2])
            self._node_width.append(self._fccd.xp.asarray(width))

    def _broadcast_axis0(self, values, ndim: int):
        shape = [1] * ndim
        shape[0] = -1
        return values.reshape(shape)
