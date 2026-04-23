"""Concrete divergence and projection operators.

Symbol mapping
--------------
∇·u -> ``divergence(components)``
u_f -> ``face_components``
ρ_f^{-1} ∂p/∂n -> ``pressure_fluxes(p, rho)``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .gradient_operator import IDivergenceOperator

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
        nodal = []
        ndim = self._grid.ndim
        for axis, face in enumerate(face_components):
            n_cells = self._grid.N[axis]
            comp = self.xp.zeros(self._grid.shape, dtype=face.dtype)

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            comp[sl(1, n_cells)] = 0.5 * (face[sl(0, n_cells - 1)] + face[sl(1, n_cells)])
            comp[sl(0, 1)] = face[sl(0, 1)]
            comp[sl(n_cells, n_cells + 1)] = face[sl(n_cells - 1, n_cells)]
            nodal.append(comp)
        return nodal

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
        faces = self.face_fluxes(components)
        p_faces = self.pressure_fluxes(p, rho)
        if force_components is None:
            force_faces = [self.xp.zeros_like(face) for face in faces]
        else:
            force_faces = self.face_fluxes(force_components)

        corrected = [
            face - dt * p_face + dt * force_face
            for face, p_face, force_face in zip(faces, p_faces, force_faces)
        ]
        return self.reconstruct_nodes(corrected)

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

    def divergence(self, components: list["array"]) -> "array":
        div = None
        for axis, comp in enumerate(components):
            f_face = self._fccd.face_value(comp, axis)
            d = self._fccd.face_divergence(f_face, axis)
            div = d if div is None else div + d
        return div

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """FCCD face-flux projection (WIKI-T-068 §5)."""
        import numpy as _np

        xp = self._fccd.xp
        grid = self._fccd.grid
        ndim = grid.ndim

        u_faces = [self._fccd.face_value(comp, ax) for ax, comp in enumerate(components)]
        if force_components is None:
            f_faces = [xp.zeros_like(u_faces[ax]) for ax in range(ndim)]
        else:
            f_faces = [self._fccd.face_value(fc, ax) for ax, fc in enumerate(force_components)]

        corrected = []
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
            if pressure_gradient == "fccd":
                p_face = coeff * self._fccd.face_gradient(p, axis)
            else:
                p_face = coeff * (p[sl(1, n_cells + 1)] - p[sl(0, n_cells)]) / d_face_arr

            corrected.append(u_faces[axis] - dt * p_face + dt * f_faces[axis])

        nodal = []
        for axis, face in enumerate(corrected):
            n_cells = grid.N[axis]

            def sl(start, stop, ax=axis):
                s = [slice(None)] * ndim
                s[ax] = slice(start, stop)
                return tuple(s)

            comp = xp.zeros(grid.shape, dtype=face.dtype)
            comp[sl(1, n_cells)] = 0.5 * (face[sl(0, n_cells - 1)] + face[sl(1, n_cells)])
            comp[sl(0, 1)] = face[sl(0, 1)]
            comp[sl(n_cells, n_cells + 1)] = face[sl(n_cells - 1, n_cells)]
            nodal.append(comp)
        return nodal

    def update_weights(self) -> None:
        """Refresh FCCD geometric weights after in-place grid rebuild (WIKI-L-029)."""
        self._fccd._weights = [
            self._fccd._precompute_weights(axis)
            for axis in range(self._fccd.ndim)
        ]
