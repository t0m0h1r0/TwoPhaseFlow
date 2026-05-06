"""Diagnostics for interface projection and capillary face cochains.

Symbol mapping
--------------
``q^-``      -> ``psi_before`` before metric/reinitialization projection.
``q^+``      -> ``psi_after`` after projection and mass closure.
``S_h(q)``   -> ``p2_trace_surface_energy_2d``.
``D_f``      -> ``div_op.divergence_from_faces``.
``a_f``      -> capillary/pressure-jump face cochain.

These helpers are diagnostic only.  They do not alter the interface transport,
Ridge-Eikonal reconstruction, PPE solve, or velocity corrector.
"""

from __future__ import annotations

from typing import Any

from ..coupling.transport_variational_capillary import p2_trace_surface_energy_2d


_REINIT_ZERO_DIAGNOSTICS = {
    "reinit_triggered": 0.0,
    "reinit_volume_delta": 0.0,
    "reinit_surface_energy_delta": 0.0,
    "reinit_linf_delta": 0.0,
    "reinit_zero_level_displacement": 0.0,
    "reinit_zero_crossing_change_count": 0.0,
}

_FACE_ZERO_DIAGNOSTICS = {
    "capillary_face_linf": 0.0,
    "capillary_face_divergence_linf": 0.0,
    "capillary_hodge_residual": 0.0,
}


def zero_reinit_projection_diagnostics() -> dict[str, float]:
    """Return the default no-projection diagnostic row."""
    return dict(_REINIT_ZERO_DIAGNOSTICS)


def zero_capillary_face_diagnostics() -> dict[str, float]:
    """Return the default no-face-cochain diagnostic row."""
    return dict(_FACE_ZERO_DIAGNOSTICS)


def reinit_projection_diagnostics(
    *,
    xp,
    backend,
    grid,
    psi_before,
    psi_after,
    sigma: float,
    phase_threshold: float = 0.5,
) -> dict[str, float]:
    """Measure the metric projection ``q^- -> q^+`` without changing fields."""
    before = xp.asarray(psi_before)
    after = xp.asarray(psi_after)
    dV = xp.asarray(grid.cell_volumes())
    volume_delta = xp.sum((after - before) * dV)
    surface_before = p2_trace_surface_energy_2d(
        xp=xp,
        grid=grid,
        psi=before,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )
    surface_after = p2_trace_surface_energy_2d(
        xp=xp,
        grid=grid,
        psi=after,
        sigma=float(sigma),
        phase_threshold=float(phase_threshold),
    )
    zero_disp, crossing_change_count = _zero_level_projection_metrics(
        xp=xp,
        grid=grid,
        psi_before=before,
        psi_after=after,
        phase_threshold=float(phase_threshold),
    )
    raw = xp.stack(
        [
            volume_delta,
            surface_after - surface_before,
            xp.max(xp.abs(after - before)),
            zero_disp,
            crossing_change_count,
        ]
    )
    values = [float(value) for value in backend.asnumpy(raw)]
    return {
        "reinit_triggered": 1.0,
        "reinit_volume_delta": values[0],
        "reinit_surface_energy_delta": values[1],
        "reinit_linf_delta": values[2],
        "reinit_zero_level_displacement": values[3],
        "reinit_zero_crossing_change_count": values[4],
    }


def capillary_face_cochain_diagnostics(
    *,
    xp,
    backend,
    div_op,
    face_components,
) -> dict[str, float]:
    """Measure the post-PPE face cochain left in the projection face space.

    ``capillary_hodge_residual`` is the infinity norm of the residual face
    cochain after the pressure solve.  Paired with
    ``capillary_face_divergence_linf``, it exposes the dangerous static-droplet
    pattern where a cochain is divergence-small but still face-large.
    """
    if face_components is None:
        return zero_capillary_face_diagnostics()
    face_linf = _face_components_linf(xp, face_components)
    if hasattr(div_op, "divergence_from_faces"):
        div_field = div_op.divergence_from_faces(face_components)
        div_linf = xp.max(xp.abs(div_field))
    else:
        div_linf = xp.asarray(0.0, dtype=face_linf.dtype)
    face_linf_h, div_linf_h = [
        float(value) for value in backend.asnumpy(xp.stack([face_linf, div_linf]))
    ]
    return {
        "capillary_face_linf": face_linf_h,
        "capillary_face_divergence_linf": div_linf_h,
        "capillary_hodge_residual": face_linf_h,
    }


def _face_components_linf(xp, face_components) -> Any:
    maxima = [xp.max(xp.abs(xp.asarray(component))) for component in face_components]
    if not maxima:
        return xp.asarray(0.0)
    return xp.max(xp.stack(maxima))


def _zero_level_projection_metrics(
    *,
    xp,
    grid,
    psi_before,
    psi_after,
    phase_threshold: float,
):
    displacement_maxima = []
    crossing_changes = []
    threshold = xp.asarray(phase_threshold, dtype=psi_before.dtype)
    for axis in range(grid.ndim):
        n_cells = grid.N[axis]

        def sl(start, stop, ax=axis):
            slices = [slice(None)] * grid.ndim
            slices[ax] = slice(start, stop)
            return tuple(slices)

        before_lo = psi_before[sl(0, n_cells)]
        before_hi = psi_before[sl(1, n_cells + 1)]
        after_lo = psi_after[sl(0, n_cells)]
        after_hi = psi_after[sl(1, n_cells + 1)]
        before_cross = (before_lo < threshold) != (before_hi < threshold)
        after_cross = (after_lo < threshold) != (after_hi < threshold)
        common = before_cross & after_cross
        before_theta = _crossing_fraction(xp, before_lo, before_hi, threshold)
        after_theta = _crossing_fraction(xp, after_lo, after_hi, threshold)
        d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
        d_shape = [1] * grid.ndim
        d_shape[axis] = -1
        displacement = xp.abs(after_theta - before_theta) * d_face.reshape(d_shape)
        displacement_maxima.append(
            xp.max(xp.where(common, displacement, xp.zeros_like(displacement)))
        )
        crossing_changes.append(xp.sum((before_cross != after_cross).astype(psi_before.dtype)))
    return xp.max(xp.stack(displacement_maxima)), xp.sum(xp.stack(crossing_changes))


def _crossing_fraction(xp, lo, hi, threshold):
    denom = hi - lo
    safe = xp.where(xp.abs(denom) > 1.0e-30, denom, xp.ones_like(denom))
    return (threshold - lo) / safe
