"""Generic interface-stress closure helpers.

Symbol mapping
--------------
``ψ`` -> ``psi``
``κ`` -> ``kappa``
``σ`` -> ``sigma``
``j = [[p]]`` -> ``pressure_jump``
``G_Γ(p; j)`` -> jump-aware face pressure gradient

A3 chain
--------
CHK-RA-CH14-006/007 interface-stress closure
  -> affine jump face gradient ``G_Γ(p; j)=G(p)-B_Γj``
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
    ``j = p_gas - p_liquid = σ κ``.  Viscous/tangential jump slots are
    intentionally not folded into capillary-specific branches; they can be
    added to this context while preserving the same affine face-gradient API.
    """

    psi: Any
    kappa: Any
    sigma: float
    phase_threshold: float = 0.5

    def is_active(self) -> bool:
        """Return whether a non-zero pressure jump should be applied."""
        return self.kappa is not None and abs(float(self.sigma)) > 0.0


def build_interface_stress_context(
    *,
    xp,
    psi,
    kappa,
    sigma: float,
    phase_threshold: float = 0.5,
) -> InterfaceStressContext:
    """Build the backend-native interface-stress context."""
    return InterfaceStressContext(
        psi=xp.asarray(psi),
        kappa=None if kappa is None else xp.asarray(kappa),
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
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

    ``j`` is defined as ``p_gas - p_liquid``.  Therefore a liquid-to-gas
    face in the positive axis direction contributes ``+j/d_f`` and a
    gas-to-liquid face contributes ``-j/d_f``.
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
    kappa = xp.asarray(context.kappa)
    gas_lo = psi[sl(0, n_cells)] < context.phase_threshold
    gas_hi = psi[sl(1, n_cells + 1)] < context.phase_threshold
    cut_face = gas_lo != gas_hi
    pressure_jump = float(context.sigma) * 0.5 * (
        kappa[sl(0, n_cells)] + kappa[sl(1, n_cells + 1)]
    )
    orientation = gas_hi.astype(pressure_jump.dtype) - gas_lo.astype(
        pressure_jump.dtype
    )
    signed_jump = xp.where(cut_face, orientation * pressure_jump, 0.0)

    d_face = np.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
    shape = [1] * ndim
    shape[axis] = -1
    return signed_jump / xp.asarray(d_face.reshape(shape))
