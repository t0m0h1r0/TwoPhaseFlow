"""Pressure gradient/divergence operator strategies (CCD vs FVM).

Encapsulates the choice between:
- CCDGradientOperator: 6th-order CCD compact differentiation
- FVMGradientOperator: face-average FVM gradient (for non-uniform grids)
- CCDDivergenceOperator: CCD nodal divergence
- FVMDivergenceOperator: finite-volume nodal-flux divergence
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


class IGradientOperator(ABC):
    """Abstract interface for computing pressure gradient ∇p."""

    @abstractmethod
    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute gradient of pressure along axis.

        Parameters
        ----------
        p : ndarray  pressure field
        axis : int  coordinate axis (0 for x, 1 for y[, 2 for z])

        Returns
        -------
        dp_daxis : ndarray  pressure gradient along axis
        """


class CCDGradientOperator(IGradientOperator):
    """6th-order CCD gradient: ∂p/∂x via compact differentiation.

    Applies Neumann boundary conditions on walls.
    Used on uniform or locally-refined grids when CCD accuracy is prioritized.
    """

    def __init__(self, backend: "Backend", ccd: "CCDSolver", bc_type: str = "wall") -> None:
        """

        Parameters
        ----------
        backend : Backend
        ccd : CCDSolver  compact-difference solver
        bc_type : {'wall', 'periodic'}  boundary condition type
        """
        self.xp = backend.xp
        self._ccd = ccd
        self.bc_type = bc_type

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute ∂p/∂x_axis via CCD with wall Neumann BC if needed."""
        dp_daxis, _ = self._ccd.differentiate(p, axis)
        if self.bc_type == "wall":
            self._ccd.enforce_wall_neumann(dp_daxis, axis)
        return dp_daxis


class FVMGradientOperator(IGradientOperator):
    """Face-average FVM gradient: J_face = (p_{i+1} − p_i) / Δx_face.

    Consistent with finite-volume discretization on non-uniform grids.
    Computes cell-center gradients from face-averaged differences.
    """

    def __init__(self, backend: "Backend", grid: "Grid") -> None:
        """

        Parameters
        ----------
        backend : Backend
        grid : Grid  coordinate system with spacing (dx_min, dx_max, etc.)
        """
        self.xp = backend.xp
        self._grid = grid
        self._d_face_grad = None  # Lazy-initialized in first call

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute ∂p/∂x_axis via FVM face-averaging."""
        # Lazy initialization of face spacing (done once per axis per step)
        if self._d_face_grad is None:
            self._init_face_spacing()

        d = self._d_face_grad[axis]
        N = self._grid.N[axis]
        ndim = self._grid.ndim

        def sl(start, stop):
            s = [slice(None)] * ndim
            s[axis] = slice(start, stop)
            return tuple(s)

        # Face-center gradient: J_face = (p_{i+1} − p_i) / d_face
        p_shifted_right = p[sl(1, N + 1)]  # p at i+1/2
        p_shifted_left = p[sl(0, N)]       # p at i−1/2
        g_face = (p_shifted_right - p_shifted_left) / d

        # Cell-center gradient (average of two adjacent faces)
        g = self.xp.zeros_like(p)
        g[sl(1, N)] = 0.5 * (g_face[sl(0, N - 1)] + g_face[sl(1, N)])

        return g

    def _init_face_spacing(self) -> None:
        """Compute and cache face spacing Δx_face for all axes."""
        import numpy as _np

        self._d_face_grad = []
        for ax in range(self._grid.ndim):
            d = _np.diff(_np.asarray(self._grid.coords[ax]))
            shape = [1] * self._grid.ndim
            shape[ax] = -1
            self._d_face_grad.append(self.xp.asarray(d.reshape(shape)))


class IDivergenceOperator(ABC):
    """Abstract interface for computing vector divergence."""

    @abstractmethod
    def divergence(self, components: list["array"]) -> "array":
        """Compute ``sum_i d components[i] / dx_i``."""


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
            N = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            faces.append(0.5 * (comp[sl(0, N)] + comp[sl(1, N + 1)]))
        return faces

    def divergence_from_faces(self, face_components: list["array"]) -> "array":
        """Compute finite-volume divergence from normal face fluxes."""
        if self._dv is None:
            self._init_metrics()

        div_shape = self._grid.shape
        div = self.xp.zeros(div_shape, dtype=face_components[0].dtype)
        ndim = self._grid.ndim
        for axis, face in enumerate(face_components):
            N = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            term = self.xp.zeros_like(div)
            term[sl(1, N)] = (
                face[sl(1, N)] - face[sl(0, N - 1)]
            ) / self._dv[axis][sl(1, N)]
            term[sl(0, 1)] = face[sl(0, 1)] / self._dv[axis][sl(0, 1)]
            term[sl(N, N + 1)] = (
                -face[sl(N - 1, N)] / self._dv[axis][sl(N, N + 1)]
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
            N = self._grid.N[axis]

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            rho_l = rho[sl(0, N)]
            rho_r = rho[sl(1, N + 1)]
            coeff = 2.0 / (rho_l + rho_r)
            faces.append(coeff * (p[sl(1, N + 1)] - p[sl(0, N)]) / self._d_face[axis])
        return faces

    def reconstruct_nodes(self, face_components: list["array"]) -> list["array"]:
        """Reconstruct nodal components from corrected normal face fluxes."""
        nodal = []
        ndim = self._grid.ndim
        for axis, face in enumerate(face_components):
            N = self._grid.N[axis]
            comp = self.xp.zeros(self._grid.shape, dtype=face.dtype)

            def sl(start, stop):
                s = [slice(None)] * ndim
                s[axis] = slice(start, stop)
                return tuple(s)

            for i in range(N):
                comp[sl(i + 1, i + 2)] = (
                    2.0 * face[sl(i, i + 1)] - comp[sl(i, i + 1)]
                )
            nodal.append(comp)
        return nodal

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
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
