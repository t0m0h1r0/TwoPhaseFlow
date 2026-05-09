"""Grid-rebuild orchestration helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.grid_remap import build_grid_remapper
from ..core.boundary import sync_periodic_image_nodes
from ..levelset.heaviside import apply_mass_correction
from ..levelset.wall_contact import apply_masked_mass_correction


@dataclass(frozen=True)
class NSGridRebuildResult:
    psi: object
    u: object
    v: object
    X: object
    Y: object
    density: object | None = None
    momentum_components: tuple[object, ...] | None = None


def rebuild_ns_grid(
    *,
    backend,
    grid,
    ccd,
    eps,
    alpha_grid: float,
    psi,
    u,
    v,
    rho_l: float | None,
    rho_g: float | None,
    use_local_eps: bool,
    curvature_operator,
    make_eps_field,
    reinitializer,
    ppe_solver,
    fccd_div_op,
    reprojector,
    wall_contacts=None,
    conservative_momentum_components=None,
    bc_type=None,
) -> NSGridRebuildResult:
    """Fit the grid to the supplied interface and remap primary fields.

    The standard non-uniform solver path uses this both for initial fitted-grid
    construction and scheduled interface-following rebuilds. The split rebuild
    step remaps ``psi`` conservatively by volume correction, remaps either
    velocity or conservative momentum, updates geometry-bound operators,
    invalidates pressure caches, and reprojects velocity on the rebuilt grid.
    """
    if alpha_grid <= 1.0:
        X, Y = grid.meshgrid()
        return NSGridRebuildResult(
            psi=psi,
            u=u,
            v=v,
            X=X,
            Y=Y,
            density=(
                None
                if conservative_momentum_components is None or rho_l is None or rho_g is None
                else backend.xp.asarray(rho_g + (rho_l - rho_g) * psi)
            ),
            momentum_components=(
                None
                if conservative_momentum_components is None
                else tuple(backend.xp.asarray(c) for c in conservative_momentum_components)
            ),
        )

    old_coords = [coords.copy() for coords in grid.coords]
    old_h = [widths.copy() for widths in grid.h]

    xp = backend.xp
    dV_old = xp.asarray(old_h[0])
    for axis in range(1, grid.ndim):
        dV_old = xp.expand_dims(dV_old, axis=axis) * xp.asarray(old_h[axis])
    psi_dev = xp.asarray(psi)
    mass_before = xp.sum(psi_dev * dV_old)
    conservative_momentum = (
        None
        if conservative_momentum_components is None
        else tuple(xp.asarray(component) for component in conservative_momentum_components)
    )
    momentum_targets = (
        None
        if conservative_momentum is None
        else tuple(xp.sum(component * dV_old) for component in conservative_momentum)
    )

    grid.update_from_levelset(psi, eps, ccd=ccd, wall_contacts=wall_contacts)

    remapper = build_grid_remapper(backend, old_coords, grid.coords)
    psi_remapped = xp.clip(xp.asarray(remapper.remap(psi)), 0.0, 1.0)

    dV_new = grid.cell_volumes()
    if wall_contacts:
        psi_remapped = wall_contacts.impose_on_wall_trace(xp, grid, psi_remapped)
        pinned = wall_contacts.constraint_mask(xp, grid, tuple(psi_remapped.shape))
        free_mask = xp.logical_not(pinned)
        psi_remapped = apply_masked_mass_correction(
            xp,
            psi_remapped,
            dV_new,
            mass_before,
            free_mask,
        )
        psi_remapped = wall_contacts.impose_on_wall_trace(xp, grid, psi_remapped)
    else:
        psi_remapped = apply_mass_correction(xp, psi_remapped, dV_new, mass_before)
    if bc_type is not None:
        sync_periodic_image_nodes(psi_remapped, bc_type)

    density_remapped = None
    momentum_remapped = None
    if conservative_momentum is not None:
        if rho_l is None or rho_g is None:
            raise ValueError(
                "conservative grid rebuild requires rho_l and rho_g to rebuild density"
            )
        density_remapped = xp.asarray(rho_g + (rho_l - rho_g) * psi_remapped)
        momentum_remapped = tuple(
            _apply_integral_correction(
                xp,
                xp.asarray(remapper.remap(component)),
                dV_new,
                target,
            )
            for component, target in zip(
                conservative_momentum, momentum_targets, strict=True
            )
        )
        if bc_type is not None:
            momentum_remapped = tuple(
                sync_periodic_image_nodes(component, bc_type)
                for component in momentum_remapped
            )
        u_remapped = momentum_remapped[0] / density_remapped
        v_remapped = momentum_remapped[1] / density_remapped
    else:
        u_remapped = xp.asarray(remapper.remap(u))
        v_remapped = xp.asarray(remapper.remap(v))
    X, Y = grid.meshgrid()

    if use_local_eps:
        curvature_operator.eps = make_eps_field()

    reinitializer.update_grid(grid)
    ppe_solver.update_grid(grid)
    ppe_solver.invalidate_cache()
    if fccd_div_op is not None:
        fccd_div_op.update_weights()

    u_reprojected, v_reprojected = reprojector.reproject(
        psi_remapped,
        u_remapped,
        v_remapped,
        ppe_solver,
        ccd,
        backend,
        rho_l=rho_l,
        rho_g=rho_g,
    )
    if conservative_momentum is not None:
        density_remapped = xp.asarray(rho_g + (rho_l - rho_g) * psi_remapped)
        momentum_remapped = (
            density_remapped * xp.asarray(u_reprojected),
            density_remapped * xp.asarray(v_reprojected),
        )
    return NSGridRebuildResult(
        psi=xp.asarray(psi_remapped),
        u=xp.asarray(u_reprojected),
        v=xp.asarray(v_reprojected),
        X=X,
        Y=Y,
        density=density_remapped,
        momentum_components=momentum_remapped,
    )


def _apply_integral_correction(xp, field, dV, target):
    """Least-change correction preserving one transported integral.

    The conservative common-flux state treats momentum density as the primary
    unknown.  After coordinate interpolation to the rebuilt tensor grid, the
    metric integral is restored by the constant L2(dV)-minimal correction,
    i.e. the solution of ``min ||delta||_M`` subject to
    ``sum((field + delta) dV) = target``.
    """
    total_volume = xp.sum(dV)
    correction = (xp.asarray(target) - xp.sum(field * dV)) / total_volume
    return field + correction
