"""Grid-rebuild orchestration helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass

from ..core.grid_remap import build_grid_remapper
from ..levelset.heaviside import apply_mass_correction


@dataclass(frozen=True)
class NSGridRebuildResult:
    psi: object
    u: object
    v: object
    X: object
    Y: object


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
) -> NSGridRebuildResult:
    if alpha_grid <= 1.0:
        X, Y = grid.meshgrid()
        return NSGridRebuildResult(
            psi=psi,
            u=u,
            v=v,
            X=X,
            Y=Y,
        )

    old_coords = [coords.copy() for coords in grid.coords]
    old_h = [widths.copy() for widths in grid.h]

    xp = backend.xp
    dV_old = xp.asarray(old_h[0])
    for axis in range(1, grid.ndim):
        dV_old = xp.expand_dims(dV_old, axis=axis) * xp.asarray(old_h[axis])
    psi_dev = xp.asarray(psi)
    mass_before = xp.sum(psi_dev * dV_old)

    grid.update_from_levelset(psi, eps, ccd=ccd)

    remapper = build_grid_remapper(backend, old_coords, grid.coords)
    psi_remapped = xp.clip(xp.asarray(remapper.remap(psi)), 0.0, 1.0)
    u_remapped = xp.asarray(remapper.remap(u))
    v_remapped = xp.asarray(remapper.remap(v))

    dV_new = grid.cell_volumes()
    psi_remapped = apply_mass_correction(xp, psi_remapped, dV_new, mass_before)
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
    return NSGridRebuildResult(
        psi=xp.asarray(psi_remapped),
        u=xp.asarray(u_reprojected),
        v=xp.asarray(v_reprojected),
        X=X,
        Y=Y,
    )
