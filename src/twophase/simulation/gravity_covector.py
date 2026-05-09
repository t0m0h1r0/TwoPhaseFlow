"""Variational gravity covectors compatible with common-flux transport."""

from __future__ import annotations

from dataclasses import dataclass

from .transport_adjoint import negative_face_divergence_adjoint


@dataclass(frozen=True)
class VariationalGravityFaces:
    """Face-native gravity objects for one transported state."""

    nodal_covector: object
    face_density_components: list[object]
    covector_components: list[object]
    acceleration_components: list[object]


def build_variational_gravity_faces(
    *,
    xp,
    fccd,
    rho,
    vertical_coordinate,
    g_acc: float,
    gravity_axis: int = 1,
) -> VariationalGravityFaces:
    """Build ``r_g=-T_m(q)^T dΦ_g/dm`` and its face acceleration.

    A3 mapping:
      Equation: ``Φ_g(m)=∑ m_i g y_i`` and
      ``r_g(w)=-⟨dΦ_g/dm, T_m(q) w⟩``.
      Discretization: ``T_m(q)w=-D_f(ρ_f w_f)`` uses the same
      ``FCCDSolver.face_divergence`` as conservative common-flux transport.
      Code: apply the exact ``(-D_f)^T`` helper to ``g y`` and divide the face
      covector by the transported face density.  No nodal body-force residual
      or pressure fallback is introduced.
    """
    if fccd._axis_periodic(gravity_axis) and float(g_acc) != 0.0:
        raise ValueError(
            "variational_potential gravity requires a non-periodic gravity axis; "
            "a single-valued gravitational potential cannot be imposed on a "
            "periodic vertical coordinate."
        )
    rho_nodal = xp.asarray(rho)
    nodal_covector = xp.asarray(g_acc, dtype=rho_nodal.dtype) * xp.asarray(
        vertical_coordinate,
        dtype=rho_nodal.dtype,
    )
    face_density_components = [
        fccd.face_value(rho_nodal, axis=axis) for axis in range(fccd.grid.ndim)
    ]
    covector_components = []
    acceleration_components = []
    for axis, face_density in enumerate(face_density_components):
        transport_adjoint = negative_face_divergence_adjoint(
            xp=xp,
            fccd=fccd,
            nodal_covector=nodal_covector,
            axis=axis,
        )
        covector = -face_density * transport_adjoint
        acceleration = xp.where(
            face_density > 0.0,
            covector / face_density,
            xp.zeros_like(covector),
        )
        covector_components.append(covector)
        acceleration_components.append(acceleration)
    return VariationalGravityFaces(
        nodal_covector=nodal_covector,
        face_density_components=face_density_components,
        covector_components=covector_components,
        acceleration_components=acceleration_components,
    )
