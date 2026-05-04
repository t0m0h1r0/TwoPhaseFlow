"""Generic interface-stress closure helpers.

Symbol mapping
--------------
``ψ`` -> ``psi``
``κ_lg`` -> ``kappa_lg``
``σ`` -> ``sigma``
``j_gl = p_gas - p_liquid`` -> ``pressure_jump_gas_minus_liquid``
``G_Γ(p; j)`` -> jump-aware face pressure gradient

A3 chain
--------
CHK-RA-CH14-012/013 oriented Young--Laplace closure
  -> affine jump face gradient ``G_Γ(p; j)=G(p)-B_Γj``
  -> ``j_gl = p_gas - p_liquid = -σ κ_lg``
  -> `InterfaceStressContext`
  -> manufactured jump / capillary-wave / rising-bubble verification
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .face_geometry_curvature import implicit_face_curvatures_2d
from .transport_variational_capillary import (
    transport_variational_pressure_jump_gradient,
)


@dataclass(frozen=True)
class InterfaceStressContext:
    """Immutable data contract for interface stress jumps.

    The first production jump is the inviscid pressure jump
    ``j_gl = p_gas - p_liquid``.  For Young--Laplace capillarity with
    ``n_lg`` oriented from liquid to gas and ``κ_lg=∇_Γ·n_lg``, the physical
    law is ``j_gl = -σ κ_lg``.  Viscous/tangential jump slots are intentionally
    not folded into capillary-specific branches; they can be added to this
    context while preserving the same affine face-gradient API.
    """

    psi: Any
    pressure_jump_gas_minus_liquid: Any
    phase_threshold: float = 0.5
    kappa_lg: Any | None = None
    sigma: float = 0.0
    cut_face_quadrature: bool = False
    face_curvature_method: str = "nodal_cut_face"

    def is_active(self) -> bool:
        """Return whether a non-zero pressure jump should be applied."""
        return (
            (
                self.pressure_jump_gas_minus_liquid is not None
                or self.kappa_lg is not None
            )
            and abs(float(self.sigma)) > 0.0
        )

    @property
    def kappa(self):
        """Backward-compatible curvature alias for diagnostics."""
        return self.kappa_lg


def build_interface_stress_context(
    *,
    xp,
    psi,
    pressure_jump_gas_minus_liquid=None,
    kappa=None,
    kappa_lg=None,
    sigma: float = 0.0,
    phase_threshold: float = 0.5,
    face_curvature_method: str = "nodal_cut_face",
) -> InterfaceStressContext:
    """Build the backend-native interface-stress context.

    Prefer passing ``pressure_jump_gas_minus_liquid`` directly.  The
    ``kappa``/``sigma`` fallback is retained as a transitional Young--Laplace
    builder and computes ``p_gas - p_liquid = -sigma * kappa_lg``.
    """
    curvature = kappa_lg if kappa_lg is not None else kappa
    if pressure_jump_gas_minus_liquid is None and curvature is not None:
        pressure_jump_gas_minus_liquid = -float(sigma) * xp.asarray(curvature)
    return InterfaceStressContext(
        psi=xp.asarray(psi),
        pressure_jump_gas_minus_liquid=(
            None
            if pressure_jump_gas_minus_liquid is None
            else xp.asarray(pressure_jump_gas_minus_liquid)
        ),
        kappa_lg=None if curvature is None else xp.asarray(curvature),
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
        cut_face_quadrature=False,
        face_curvature_method=str(face_curvature_method),
    )


def build_young_laplace_interface_stress_context(
    *,
    xp,
    psi,
    kappa_lg,
    sigma: float,
    phase_threshold: float = 0.5,
    face_curvature_method: str = "nodal_cut_face",
) -> InterfaceStressContext:
    """Build ``j_gl = p_gas - p_liquid = -σ κ_lg`` for capillarity."""
    if face_curvature_method == "face_implicit":
        return InterfaceStressContext(
            psi=xp.asarray(psi),
            pressure_jump_gas_minus_liquid=None,
            phase_threshold=float(phase_threshold),
            kappa_lg=xp.asarray(kappa_lg),
            sigma=float(sigma),
            cut_face_quadrature=True,
            face_curvature_method=face_curvature_method,
        )
    context = build_interface_stress_context(
        xp=xp,
        psi=psi,
        pressure_jump_gas_minus_liquid=-float(sigma) * xp.asarray(kappa_lg),
        kappa_lg=kappa_lg,
        sigma=sigma,
        phase_threshold=phase_threshold,
        face_curvature_method=face_curvature_method,
    )
    return InterfaceStressContext(
        psi=context.psi,
        pressure_jump_gas_minus_liquid=context.pressure_jump_gas_minus_liquid,
        phase_threshold=context.phase_threshold,
        kappa_lg=context.kappa_lg,
        sigma=context.sigma,
        cut_face_quadrature=True,
        face_curvature_method=context.face_curvature_method,
    )


def evaluate_interface_face_curvature_lg(
    *,
    xp,
    grid,
    context: InterfaceStressContext | None,
    fccd=None,
) -> tuple[Any, ...] | None:
    """Evaluate ``κ_lg`` on jump faces as an operation-local temporary."""
    if (
        context is None
        or not interface_stress_context_is_active(context)
        or context.face_curvature_method != "face_implicit"
    ):
        return None
    return implicit_face_curvatures_2d(
        xp=xp,
        grid=grid,
        psi=context.psi,
        fccd=fccd,
        phase_threshold=context.phase_threshold,
    )


def affine_jump_face_inverse_density(
    *,
    xp,
    grid,
    rho,
    axis: int,
    context: InterfaceStressContext | None,
):
    r"""Return the cut-face inverse-density coefficient for affine jumps.

    A3 chain:
      ``q_f = (p_H-p_L-j_{\Gamma}) /
      \int_{x_L}^{x_H}\rho\,dn``
        -> piecewise-constant phase resistance
        ``\rho_L\theta + \rho_H(1-\theta)``
        -> ``α_f^\Gamma=1/(\rho_L\theta+\rho_H(1-\theta))`` on cut faces.

    Non-cut faces retain the same nodal harmonic density coefficient used by
    the smooth-pressure face operator.
    """
    ndim = grid.ndim
    n_cells = grid.N[axis]

    def sl(start, stop):
        slices = [slice(None)] * ndim
        slices[axis] = slice(start, stop)
        return tuple(slices)

    rho_arr = xp.asarray(rho)
    rho_lo = rho_arr[sl(0, n_cells)]
    rho_hi = rho_arr[sl(1, n_cells + 1)]
    base_coeff = 2.0 / (rho_lo + rho_hi)
    if context is None or context.psi is None:
        return base_coeff

    psi = xp.asarray(context.psi)
    psi_lo = psi[sl(0, n_cells)]
    psi_hi = psi[sl(1, n_cells + 1)]
    cut_face = (psi_lo < context.phase_threshold) != (
        psi_hi < context.phase_threshold
    )
    dpsi = psi_hi - psi_lo
    denominator = xp.where(cut_face, dpsi, xp.ones_like(dpsi))
    theta = xp.where(
        cut_face,
        (context.phase_threshold - psi_lo) / denominator,
        xp.zeros_like(dpsi),
    )
    cut_coeff = 1.0 / (theta * rho_lo + (1.0 - theta) * rho_hi)
    return xp.where(cut_face, cut_coeff, base_coeff)


def interface_stress_context_is_active(context: InterfaceStressContext | None) -> bool:
    """Return whether ``context`` contains an active pressure jump."""
    return context is not None and context.is_active()


def signed_pressure_jump_gradient(
    *,
    xp,
    grid,
    context: InterfaceStressContext | None,
    axis: int,
    face_curvature_lg: tuple[Any, ...] | None = None,
    fccd=None,
):
    """Return ``B_Γ(j)`` on faces for ``G_Γ(p;j)=G(p)-B_Γ(j)``.

    ``j_gl`` is defined as ``p_gas - p_liquid``.  Therefore a liquid-to-gas
    face in the positive axis direction contributes ``+j_gl/d_f`` and a
    gas-to-liquid face contributes ``-j_gl/d_f``.
    """
    ndim = grid.ndim
    n_cells = grid.N[axis]

    def sl(start, stop):
        slices = [slice(None)] * ndim
        slices[axis] = slice(start, stop)
        return tuple(slices)

    reference = xp.asarray(context.psi if context is not None else xp.zeros(grid.shape))
    face_shape = list(reference.shape)
    face_shape[axis] = n_cells
    if not interface_stress_context_is_active(context):
        return xp.zeros(tuple(face_shape), dtype=reference.dtype)

    psi = xp.asarray(context.psi)
    psi_lo = psi[sl(0, n_cells)]
    psi_hi = psi[sl(1, n_cells + 1)]
    gas_lo = psi_lo < context.phase_threshold
    gas_hi = psi_hi < context.phase_threshold
    cut_face = gas_lo != gas_hi
    if (
        context.cut_face_quadrature
        and context.face_curvature_method == "face_implicit"
    ):
        if face_curvature_lg is None:
            raise ValueError(
                "face_implicit jump evaluation requires the operation-local "
                "face_curvature_lg temporary"
            )
        kappa_face = xp.asarray(face_curvature_lg[axis])
        pressure_jump = -float(context.sigma) * kappa_face
    elif (
        context.cut_face_quadrature
        and context.face_curvature_method
        in {
            "transport_variational",
            "transport_variational_p2",
            "transport_variational_p2_midpoint",
        }
    ):
        return transport_variational_pressure_jump_gradient(
            xp=xp,
            grid=grid,
            psi=context.psi,
            fccd=fccd,
            sigma=context.sigma,
            axis=axis,
            phase_threshold=context.phase_threshold,
            trace_space=(
                "p2"
                if context.face_curvature_method
                in {"transport_variational_p2", "transport_variational_p2_midpoint"}
                else "p1"
            ),
        )
    elif context.cut_face_quadrature and context.kappa_lg is not None:
        kappa_lg = xp.asarray(context.kappa_lg)
        kappa_lo = kappa_lg[sl(0, n_cells)]
        kappa_hi = kappa_lg[sl(1, n_cells + 1)]
        dpsi = psi_hi - psi_lo
        denominator = xp.where(cut_face, dpsi, xp.ones_like(dpsi))
        theta = xp.where(
            cut_face,
            (context.phase_threshold - psi_lo) / denominator,
            xp.zeros_like(dpsi),
        )
        kappa_face = (1.0 - theta) * kappa_lo + theta * kappa_hi
        pressure_jump = -float(context.sigma) * kappa_face
    else:
        pressure_jump_gas_minus_liquid = xp.asarray(
            context.pressure_jump_gas_minus_liquid
        )
        pressure_jump = 0.5 * (
            pressure_jump_gas_minus_liquid[sl(0, n_cells)]
            + pressure_jump_gas_minus_liquid[sl(1, n_cells + 1)]
        )
    orientation = gas_hi.astype(pressure_jump.dtype) - gas_lo.astype(
        pressure_jump.dtype
    )
    signed_jump = xp.where(cut_face, orientation * pressure_jump, 0.0)

    coords_axis = xp.asarray(grid.coords[axis])
    d_face = coords_axis[1:] - coords_axis[:-1]
    shape = [1] * ndim
    shape[axis] = -1
    return signed_jump / d_face.reshape(shape)
