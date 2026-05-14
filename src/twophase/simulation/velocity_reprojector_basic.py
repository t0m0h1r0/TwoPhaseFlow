"""Basic velocity reprojector implementations.

Symbol mapping
--------------
ψ -> ``psi``
u*, v* -> ``u``, ``v``
ρ -> ``rho``
φ -> ``phi``
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..core.boundary import is_all_periodic
from .face_boundary import zero_wall_normal_face_components
from .velocity_reprojector import IVelocityReprojector, _device_array

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ppe.interfaces import IPPESolver
    from .scheme_build_ctx import ReprojectorBuildCtx


def _clear_interface_for_reprojection(ppe_solver: "IPPESolver") -> None:
    clearer = getattr(ppe_solver, "clear_interface_jump_context", None)
    if callable(clearer):
        clearer()


def _set_neutral_affine_context_for_reprojection(ppe_solver: "IPPESolver", *, xp, psi):
    """Install a zero-jump interface context for homogeneous face-Hodge projection."""
    setter = getattr(ppe_solver, "set_interface_jump_context", None)
    if not callable(setter):
        _clear_interface_for_reprojection(ppe_solver)
        return None
    psi_dev = xp.asarray(psi)
    setter(
        psi=psi_dev,
        kappa=xp.zeros_like(psi_dev),
        sigma=0.0,
        psi_previous=psi_dev,
    )
    operator = getattr(ppe_solver, "operator", ppe_solver)
    return getattr(operator, "_interface_stress_context", None)


def _face_hodge_pressure_kwargs(*, ppe_runtime, interface_stress_context):
    if ppe_runtime is None:
        raise RuntimeError("face_hodge reprojection requires ppe_runtime")
    solver_name = getattr(ppe_runtime, "ppe_solver_name", None)
    kwargs = {
        "pressure_gradient": "fccd" if solver_name == "fccd_iterative" else "fvm",
    }
    contract = getattr(
        ppe_runtime,
        "pressure_force_contract",
        "raw_compact_gradient",
    )
    if contract != "raw_compact_gradient":
        kwargs["pressure_force_contract"] = contract
    coefficient = getattr(ppe_runtime, "ppe_coefficient_scheme", "phase_density")
    if coefficient == "phase_separated":
        kwargs["coefficient_scheme"] = "phase_separated"
    coupling = getattr(ppe_runtime, "ppe_interface_coupling_scheme", "none")
    if coupling == "affine_jump":
        if interface_stress_context is None:
            raise RuntimeError(
                "face_hodge affine-jump reprojection requires an interface "
                "stress context, even for zero physical jump"
            )
        kwargs["interface_coupling_scheme"] = "affine_jump"
        kwargs["interface_stress_context"] = interface_stress_context
    elif coupling != "none":
        raise RuntimeError(
            "face_hodge reprojection supports none|affine_jump interface "
            f"coupling, got {coupling!r}"
        )
    return kwargs


class LegacyReprojector(IVelocityReprojector):
    """Uniform-grid baseline reprojector (constant ρ = 1)."""

    scheme_names = ("legacy",)

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "LegacyReprojector":
        return cls()

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1
        del div_op, ppe_runtime, bc_type

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        rho = xp.ones_like(psi_d)
        _clear_interface_for_reprojection(ppe_solver)
        phi = ppe_solver.solve(div, rho)

        dp_dx = ccd.first_derivative(phi, 0)
        dp_dy = ccd.first_derivative(phi, 1)
        u_proj = u_d - xp.asarray(dp_dx)
        v_proj = v_d - xp.asarray(dp_dy)
        return u_proj, v_proj

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


class VariableDensityReprojector(IVelocityReprojector):
    """Reprojector with variable density ρ = ρ_g + (ρ_l − ρ_g) ψ."""

    scheme_names = ("variable_density_only",)

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "VariableDensityReprojector":
        return cls()

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1
        del div_op, ppe_runtime, bc_type

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)

        if rho_l is None or rho_g is None:
            raise ValueError(
                "variable_density_only reprojection requires explicit rho_l and rho_g; "
                "select reproject_mode='legacy' explicitly for constant-density projection."
            )
        rho = rho_g + (rho_l - rho_g) * psi_d

        du_dx = ccd.first_derivative(u_d, 0)
        dv_dy = ccd.first_derivative(v_d, 1)
        div = (xp.asarray(du_dx) + xp.asarray(dv_dy)) / 1.0

        _clear_interface_for_reprojection(ppe_solver)
        phi = ppe_solver.solve(div, rho)

        rho_inv = 1.0 / xp.where(xp.abs(rho) > 1e-30, rho, 1.0)
        dp_dx = ccd.first_derivative(phi, 0)
        dp_dy = ccd.first_derivative(phi, 1)
        u_proj = u_d - rho_inv * xp.asarray(dp_dx)
        v_proj = v_d - rho_inv * xp.asarray(dp_dy)
        return u_proj, v_proj

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


class FaceHodgeReprojector(IVelocityReprojector):
    """Projection-native face Hodge reprojection after grid rebuild.

    Symbol mapping
    --------------
    ``D_f`` -> ``div_op.divergence_from_faces``
    ``G_f`` -> ``div_op.pressure_fluxes``
    ``P_f`` -> ``u_f - G_f phi`` with ``D_f P_f = 0``

    A3 chain:
      Paper equation: variable-density Hodge projection
      ``D_f(u_f - M_f^{-1}D_f^* phi)=0``.
      Discretisation: use the active FCCD face complex and the configured PPE
      operator with zero physical jump on the rebuilt grid.
      Code: solve ``L phi = D_f u_f`` and reconstruct nodal velocity from the
      corrected projection-native faces.
    """

    scheme_names = ("face_hodge", "projection_native_face_hodge")

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "FaceHodgeReprojector":
        return cls()

    def __init__(self) -> None:
        self._stats = {
            "calls": 0,
            "pre_div_linf": 0.0,
            "post_div_linf": 0.0,
        }

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
    ) -> tuple[np.ndarray, np.ndarray]:
        del ccd
        if div_op is None or not hasattr(div_op, "face_fluxes"):
            raise RuntimeError("face_hodge reprojection requires div_op.face_fluxes")
        xp = backend.xp
        u_d = _device_array(u, backend)
        v_d = _device_array(v, backend)
        faces = [xp.asarray(component) for component in div_op.face_fluxes([u_d, v_d])]
        u_proj, v_proj, _ = self.reproject_faces(
            psi,
            faces,
            ppe_solver,
            backend,
            rho_l=rho_l,
            rho_g=rho_g,
            div_op=div_op,
            ppe_runtime=ppe_runtime,
            bc_type=bc_type,
        )
        return u_proj, v_proj

    def reproject_faces(
        self,
        psi: np.ndarray,
        face_components,
        ppe_solver: "IPPESolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
    ):
        self._stats["calls"] += 1
        if div_op is None:
            raise RuntimeError("face_hodge reprojection requires div_op")
        required = (
            "divergence_from_faces",
            "pressure_fluxes",
            "reconstruct_nodes",
        )
        missing = [name for name in required if not hasattr(div_op, name)]
        if missing:
            raise RuntimeError(
                "face_hodge reprojection requires projection-native operator "
                f"methods {required!r}; missing {missing!r}"
            )
        if rho_l is None or rho_g is None:
            raise ValueError("face_hodge reprojection requires explicit rho_l and rho_g")

        xp = backend.xp
        psi_d = _device_array(psi, backend)
        rho = rho_g + (rho_l - rho_g) * psi_d

        interface_context = _set_neutral_affine_context_for_reprojection(
            ppe_solver,
            xp=xp,
            psi=psi_d,
        )
        pressure_kwargs = _face_hodge_pressure_kwargs(
            ppe_runtime=ppe_runtime,
            interface_stress_context=interface_context,
        )

        try:
            faces = [xp.asarray(component) for component in face_components]
            if not is_all_periodic(bc_type, 2):
                faces = zero_wall_normal_face_components(faces, xp=xp, bc_type=bc_type)
            rhs = div_op.divergence_from_faces(faces)
            pre_linf = xp.max(xp.abs(rhs))
            phi = ppe_solver.solve(rhs, rho, dt=1.0, p_init=None)
            pressure_faces = div_op.pressure_fluxes(phi, rho, **pressure_kwargs)
            projected_faces = [
                face - xp.asarray(pressure_face)
                for face, pressure_face in zip(faces, pressure_faces, strict=True)
            ]
            post_div = div_op.divergence_from_faces(projected_faces)
            post_linf = xp.max(xp.abs(post_div))
            stats = backend.asnumpy(xp.stack([pre_linf, post_linf]))
            self._stats["pre_div_linf"] = float(stats[0])
            self._stats["post_div_linf"] = float(stats[1])
            u_proj, v_proj = div_op.reconstruct_nodes(projected_faces)
            return xp.asarray(u_proj), xp.asarray(v_proj), tuple(
                xp.asarray(component) for component in projected_faces
            )
        finally:
            _clear_interface_for_reprojection(ppe_solver)

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


class ConsistentGFMReprojectorLegacy(IVelocityReprojector):
    """Fail-closed placeholder for the unimplemented consistent-GFM reprojector."""

    scheme_names = ("gfm", "consistent_gfm")

    def __init__(self) -> None:
        self._stats = {"calls": 0}

    @classmethod
    def _build(cls, name: str, ctx: "ReprojectorBuildCtx") -> "ConsistentGFMReprojectorLegacy":
        raise ValueError(
            f"reproject_mode={name!r} is not implemented as a GFM velocity "
            "reprojection scheme. It must not run as variable_density_only implicitly; "
            "select reproject_mode='variable_density_only' explicitly for the "
            "density-weighted projection."
        )

    def reproject(
        self,
        psi: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        ppe_solver: "IPPESolver",
        ccd: "CCDSolver",
        backend: "Backend",
        rho_l: float | None = None,
        rho_g: float | None = None,
        *,
        div_op=None,
        ppe_runtime=None,
        bc_type: str = "wall",
    ) -> tuple[np.ndarray, np.ndarray]:
        self._stats["calls"] += 1
        del div_op, ppe_runtime, bc_type
        raise RuntimeError(
            "consistent_gfm velocity reprojection is not implemented; "
            "no alternate reprojection scheme was applied."
        )

    @property
    def stats(self) -> dict[str, float]:
        return dict(self._stats)


ConsistentGFMReprojector = ConsistentGFMReprojectorLegacy
