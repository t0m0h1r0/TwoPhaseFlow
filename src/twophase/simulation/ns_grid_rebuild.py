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
    projected_face_components: tuple[object, ...] | None = None


def _sharp_volume_target(reinitializer, psi) -> float | None:
    if not getattr(reinitializer, "preserves_sharp_volume", False):
        return None
    volume_fn = getattr(reinitializer, "sharp_phase_volume", None)
    if not callable(volume_fn):
        return None
    return float(volume_fn(psi))


def _set_sharp_volume_target(reinitializer, target: float | None) -> None:
    if target is None:
        return
    setter = getattr(reinitializer, "set_sharp_phase_volume_target", None)
    if callable(setter):
        setter(target)


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
    div_op,
    ppe_runtime,
    reprojector,
    wall_contacts=None,
    conservative_momentum_components=None,
    projected_face_components=None,
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
            projected_face_components=(
                None
                if projected_face_components is None
                else tuple(backend.xp.asarray(c) for c in projected_face_components)
            ),
        )

    old_coords = [coords.copy() for coords in grid.coords]
    xp = backend.xp
    dV_old = xp.asarray(grid.cell_volumes(bc_type=bc_type))
    psi_dev = xp.asarray(psi)
    mass_before = xp.sum(psi_dev * dV_old)
    sharp_volume_before = _sharp_volume_target(reinitializer, psi_dev)
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

    dV_new = grid.cell_volumes(bc_type=bc_type)
    reinitializer.update_grid(grid)
    if sharp_volume_before is not None:
        _set_sharp_volume_target(reinitializer, sharp_volume_before)
        psi_remapped = xp.asarray(reinitializer.reinitialize(psi_remapped))
    elif wall_contacts:
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
    projected_faces_remapped = (
        None
        if projected_face_components is None
        else _remap_projection_face_components(
            backend,
            old_coords,
            grid.coords,
            projected_face_components,
        )
    )
    X, Y = grid.meshgrid()

    if use_local_eps:
        curvature_operator.eps = make_eps_field()

    ppe_solver.update_grid(grid)
    ppe_solver.invalidate_cache()
    if fccd_div_op is not None:
        fccd_div_op.update_weights()

    projected_faces_new = None
    if projected_faces_remapped is not None:
        reproject_faces = getattr(reprojector, "reproject_faces", None)
        if not callable(reproject_faces):
            raise RuntimeError(
                "grid rebuild received projection-native face history but the "
                "active reprojector cannot reproject face cochains"
            )
        u_reprojected, v_reprojected, projected_faces_new = reproject_faces(
            psi_remapped,
            projected_faces_remapped,
            ppe_solver,
            backend,
            rho_l=rho_l,
            rho_g=rho_g,
            div_op=div_op,
            ppe_runtime=ppe_runtime,
            bc_type=bc_type or "wall",
        )
    else:
        u_reprojected, v_reprojected = reprojector.reproject(
            psi_remapped,
            u_remapped,
            v_remapped,
            ppe_solver,
            ccd,
            backend,
            rho_l=rho_l,
            rho_g=rho_g,
            div_op=div_op,
            ppe_runtime=ppe_runtime,
            bc_type=bc_type or "wall",
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
        projected_face_components=projected_faces_new,
    )


def _projection_face_coords(coords, axis: int):
    return [
        0.5 * (coord[:-1] + coord[1:]) if idx == axis else coord
        for idx, coord in enumerate(coords)
    ]


def _remap_projection_face_components(
    backend,
    old_coords,
    new_coords,
    face_components,
):
    """Move projection-native normal face cochains to the rebuilt face lattice."""
    remapped = []
    for axis, component in enumerate(face_components):
        mapper = build_grid_remapper(
            backend,
            _projection_face_coords(old_coords, axis),
            _projection_face_coords(new_coords, axis),
        )
        remapped.append(backend.xp.asarray(mapper.remap(component)))
    return tuple(remapped)


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
