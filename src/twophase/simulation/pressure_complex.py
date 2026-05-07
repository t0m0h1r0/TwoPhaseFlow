"""Variational pressure-complex helpers.

Symbol mapping
--------------
``D``     -> ``divergence_from_faces``
``W``     -> nodal control-volume pressure metric
``alpha`` -> face inverse-density coefficient
``M``     -> face kinetic metric ``Q_f / alpha``
``G``     -> pressure reaction returned by ``pressure_fluxes``

The production pressure reaction follows the subtractive projection convention

    u_new = u_old - dt * G(p),

with ``G = -M^{-1}D^T W`` for the signed Green identity used by the code:

    <G p, w>_M + <p, D w>_W = 0.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..core.boundary import is_periodic_axis, sync_periodic_image_nodes

if TYPE_CHECKING:
    from ..core.grid import Grid


PRESSURE_FORCE_CONTRACT_RAW = "raw_compact_gradient"
PRESSURE_FORCE_CONTRACT_VARIATIONAL = "variational_adjoint"
SCALAR_OPERATOR_PAIRING_LEGACY = "legacy"
SCALAR_OPERATOR_PAIRING_REQUIRE_CERTIFIED = "require_certified"
SCALAR_OPERATOR_PAIRING_VARIATIONAL = "variational_operator"


def normalise_pressure_force_contract(value: str | None) -> str:
    """Return the canonical pressure-force contract name."""
    key = str(value or PRESSURE_FORCE_CONTRACT_RAW).strip().lower()
    aliases = {
        "raw": PRESSURE_FORCE_CONTRACT_RAW,
        "raw_gradient": PRESSURE_FORCE_CONTRACT_RAW,
        "raw_compact": PRESSURE_FORCE_CONTRACT_RAW,
        "fccd_gradient": PRESSURE_FORCE_CONTRACT_RAW,
        "variational": PRESSURE_FORCE_CONTRACT_VARIATIONAL,
        "adjoint": PRESSURE_FORCE_CONTRACT_VARIATIONAL,
        "pressure_adjoint": PRESSURE_FORCE_CONTRACT_VARIATIONAL,
    }
    key = aliases.get(key, key)
    if key not in {
        PRESSURE_FORCE_CONTRACT_RAW,
        PRESSURE_FORCE_CONTRACT_VARIATIONAL,
    }:
        raise ValueError(
            "Unsupported pressure_force_contract="
            f"{value!r}; use raw_compact_gradient|variational_adjoint."
        )
    return key


def normalise_scalar_operator_pairing(value: str | None) -> str:
    """Return the canonical scalar-operator pairing mode."""
    key = str(value or SCALAR_OPERATOR_PAIRING_LEGACY).strip().lower()
    aliases = {
        "raw": SCALAR_OPERATOR_PAIRING_LEGACY,
        "old": SCALAR_OPERATOR_PAIRING_LEGACY,
        "certified": SCALAR_OPERATOR_PAIRING_REQUIRE_CERTIFIED,
        "require": SCALAR_OPERATOR_PAIRING_REQUIRE_CERTIFIED,
        "variational": SCALAR_OPERATOR_PAIRING_VARIATIONAL,
        "l_var": SCALAR_OPERATOR_PAIRING_VARIATIONAL,
    }
    key = aliases.get(key, key)
    if key not in {
        SCALAR_OPERATOR_PAIRING_LEGACY,
        SCALAR_OPERATOR_PAIRING_REQUIRE_CERTIFIED,
        SCALAR_OPERATOR_PAIRING_VARIATIONAL,
    }:
        raise ValueError(
            "Unsupported scalar_operator_pairing="
            f"{value!r}; use legacy|require_certified|variational_operator."
        )
    return key


def variational_pressure_reaction_faces(
    *,
    xp,
    grid: "Grid",
    bc_type: str,
    pressure,
    coeff_faces: list,
) -> list:
    """Return ``G(p)`` as the Riesz-adjoint pressure reaction on faces.

    The current FCCD projection divergence is finite-volume in the face
    unknowns.  Its signed Riesz adjoint is therefore the coefficient-weighted
    two-point pressure jump on the same physical face quotient.  Periodic image
    pressure nodes are synchronized before the face differences are formed.
    """
    p = xp.array(xp.asarray(pressure), copy=True)
    sync_periodic_image_nodes(p, bc_type)

    faces = []
    ndim = grid.ndim
    for axis in range(ndim):
        n_cells = grid.N[axis]
        p_axis0 = xp.moveaxis(p, axis, 0)
        if is_periodic_axis(bc_type, axis, ndim):
            p_lo = p_axis0[:n_cells]
            p_hi = xp.roll(p_lo, shift=-1, axis=0)
        else:
            p_lo = p_axis0[:n_cells]
            p_hi = p_axis0[1 : n_cells + 1]
        d_face = xp.asarray(grid.coords[axis][1:] - grid.coords[axis][:-1])
        shape = [1] * p_lo.ndim
        shape[0] = -1
        grad_axis0 = (p_hi - p_lo) / d_face.reshape(shape)
        grad = xp.moveaxis(grad_axis0, 0, axis)
        faces.append(xp.asarray(coeff_faces[axis]) * grad)
    return faces

