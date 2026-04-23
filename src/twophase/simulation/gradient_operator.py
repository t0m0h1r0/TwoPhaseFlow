"""Pressure gradient/divergence operator strategies (CCD vs FVM vs FCCD).

Encapsulates the choice between:
- CCDGradientOperator: 6th-order CCD compact differentiation
- FCCDGradientOperator: face-centred compact gradient reconstructed to nodes
- FVMGradientOperator: face-average FVM gradient (for non-uniform grids)
- CCDDivergenceOperator: CCD nodal divergence
- FVMDivergenceOperator: finite-volume nodal-flux divergence (O(h²))
- FCCDDivergenceOperator: FCCD face-flux divergence, BF-paired with FCCDGradientOperator (O(h⁴))
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ccd.fccd import FCCDSolver
    from .scheme_build_ctx import GradientBuildCtx


class IGradientOperator(ABC):
    """Abstract interface for computing pressure gradient ∇p."""

    _registry: ClassVar[dict[str, type["IGradientOperator"]]] = {}
    _aliases:  ClassVar[dict[str, str]]                       = {}

    def __init_subclass__(cls, **kw: object) -> None:
        super().__init_subclass__(**kw)
        for name in getattr(cls, "scheme_names", ()):
            IGradientOperator._registry[name] = cls
        for alias, canonical in getattr(cls, "_scheme_aliases", {}).items():
            IGradientOperator._aliases[alias] = canonical

    @classmethod
    def from_scheme(cls, name: str, ctx: "GradientBuildCtx") -> "IGradientOperator":
        """Instantiate the gradient operator registered under *name*."""
        canonical = cls._aliases.get(name, name)
        klass = cls._registry.get(canonical)
        if klass is None:
            raise ValueError(
                f"Unknown gradient scheme {name!r}. "
                f"Known: {sorted(cls._registry)}"
            )
        return klass._build(canonical, ctx)

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

    scheme_names = ("ccd", "projection_consistent")  # projection_consistent: backward-compat alias

    @classmethod
    def _build(cls, name: str, ctx: "GradientBuildCtx") -> "CCDGradientOperator":
        return ctx.ccd_op  # type: ignore[return-value]

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
        dp_daxis = self._ccd.first_derivative(p, axis)
        if self.bc_type == "wall":
            self._ccd.enforce_wall_neumann(dp_daxis, axis)
        return dp_daxis


class FCCDGradientOperator(IGradientOperator):
    """FCCD gradient shared by pressure correction and surface tension force."""

    scheme_names     = ("fccd_flux", "fccd_nodal")
    _scheme_aliases  = {"fccd": "fccd_flux"}

    @classmethod
    def _build(cls, name: str, ctx: "GradientBuildCtx") -> "FCCDGradientOperator":
        return cls(ctx.fccd)

    def __init__(self, fccd: "FCCDSolver") -> None:
        self._fccd = fccd

    def gradient(
        self,
        p: "array",
        axis: int,
    ) -> "array":
        """Compute nodal gradient via FCCD face gradient + R4 reconstruction."""
        return self._fccd.node_gradient(p, axis)


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

    def project(
        self,
        components: list["array"],
        p: "array",
        rho: "array",
        dt: float,
        force_components: list["array"] | None = None,
        pressure_gradient: str = "fvm",
    ) -> list["array"]:
        """Apply face-flux projection if supported by this divergence strategy."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support face-flux projection"
        )


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

            comp[sl(1, N)] = 0.5 * (face[sl(0, N - 1)] + face[sl(1, N)])
            comp[sl(0, 1)] = face[sl(0, 1)]
            comp[sl(N, N + 1)] = face[sl(N - 1, N)]
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
    """FCCD face-flux projector: O(h⁴) face values, BF-paired with FCCDGradientOperator.

    NOT used as the primary PPE-RHS divergence operator (FCCD face_value applied to
    non-smooth surface tension forces gives spurious H²q corrections).  Used
    exclusively through ``project()``, where FCCD face values are applied to the
    smooth velocity field u* while the pressure gradient uses the FVM-consistent
    finite difference that matches the FVM PPE solver (see WIKI-T-068 §4-5).

    For diagnostics or smooth fields, ``divergence()`` can still be called.
    """

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
        """FCCD face-flux projection (WIKI-T-068 §5).

        Uses FCCD Hermite face values for velocity and force (O(h⁴) accuracy),
        with either FVM-consistent ``(p_r - p_l) / H`` pressure fluxes for the
        legacy FVM PPE path or FCCD face gradients for the FCCD PPE path.
        """
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
            N = grid.N[axis]

            def sl(start, stop, ax=axis):
                s = [slice(None)] * ndim
                s[ax] = slice(start, stop)
                return tuple(s)

            d_face = _np.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
            shape = [1] * ndim
            shape[axis] = -1
            d_face_arr = xp.asarray(d_face.reshape(shape))

            rho_lo = rho[sl(0, N)]
            rho_hi = rho[sl(1, N + 1)]
            coeff = 2.0 / (rho_lo + rho_hi)
            if pressure_gradient == "fccd":
                p_face = coeff * self._fccd.face_gradient(p, axis)
            else:
                p_face = coeff * (p[sl(1, N + 1)] - p[sl(0, N)]) / d_face_arr

            corrected.append(u_faces[axis] - dt * p_face + dt * f_faces[axis])

        nodal = []
        for axis, face in enumerate(corrected):
            N = grid.N[axis]

            def sl(start, stop, ax=axis):
                s = [slice(None)] * ndim
                s[ax] = slice(start, stop)
                return tuple(s)

            comp = xp.zeros(grid.shape, dtype=face.dtype)
            comp[sl(1, N)] = 0.5 * (face[sl(0, N - 1)] + face[sl(1, N)])
            comp[sl(0, 1)] = face[sl(0, 1)]
            comp[sl(N, N + 1)] = face[sl(N - 1, N)]
            nodal.append(comp)
        return nodal

    def update_weights(self) -> None:
        """Refresh FCCD geometric weights after in-place grid rebuild (WIKI-L-029)."""
        self._fccd._weights = [
            self._fccd._precompute_weights(ax)
            for ax in range(self._fccd.ndim)
        ]
