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

import numpy as np


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

    def is_active(self) -> bool:
        """Return whether a non-zero pressure jump should be applied."""
        return (
            self.pressure_jump_gas_minus_liquid is not None
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
    )


def build_young_laplace_interface_stress_context(
    *,
    xp,
    psi,
    kappa_lg,
    sigma: float,
    phase_threshold: float = 0.5,
) -> InterfaceStressContext:
    """Build ``j_gl = p_gas - p_liquid = -σ κ_lg`` for capillarity."""
    return build_interface_stress_context(
        xp=xp,
        psi=psi,
        pressure_jump_gas_minus_liquid=-float(sigma) * xp.asarray(kappa_lg),
        kappa_lg=kappa_lg,
        sigma=sigma,
        phase_threshold=phase_threshold,
    )


def interface_stress_context_is_active(context: InterfaceStressContext | None) -> bool:
    """Return whether ``context`` contains an active pressure jump."""
    return context is not None and context.is_active()


def signed_pressure_jump_gradient(
    *,
    xp,
    grid,
    context: InterfaceStressContext | None,
    axis: int,
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
    pressure_jump_gas_minus_liquid = xp.asarray(
        context.pressure_jump_gas_minus_liquid
    )
    gas_lo = psi[sl(0, n_cells)] < context.phase_threshold
    gas_hi = psi[sl(1, n_cells + 1)] < context.phase_threshold
    cut_face = gas_lo != gas_hi
    pressure_jump = 0.5 * (
        pressure_jump_gas_minus_liquid[sl(0, n_cells)]
        + pressure_jump_gas_minus_liquid[sl(1, n_cells + 1)]
    )
    orientation = gas_hi.astype(pressure_jump.dtype) - gas_lo.astype(
        pressure_jump.dtype
    )
    signed_jump = xp.where(cut_face, orientation * pressure_jump, 0.0)

    d_face = np.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
    shape = [1] * ndim
    shape[axis] = -1
    return signed_jump / xp.asarray(d_face.reshape(shape))
