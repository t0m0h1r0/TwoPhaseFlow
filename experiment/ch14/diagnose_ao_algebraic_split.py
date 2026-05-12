#!/usr/bin/env python3
"""Rung-0 algebraic AO capillary split probe.

This probe does not advance Navier--Stokes.  It compares the CPU exact
fixed-stratum pressure split against the current GPU packet on the same
geometric interface, then reports which fail-close contract is first violated.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from types import SimpleNamespace

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.geometry.phase_state import (  # noqa: E402
    GeometricPhaseState,
    transport_geometric_phase_common_flux_2d,
)
from twophase.geometry import (  # noqa: E402
    geometric_component_volume_reaction_hodge_2d,
    geometric_pressure_capillary_hodge_2d,
)
from twophase.simulation.geometric_phase_runtime import (  # noqa: E402
    materialise_geometric_common_flux_state,
    materialise_geometric_runtime_capillary_application_state,
    materialise_geometric_runtime_capillary_state,
)
from twophase.simulation.geometric_phase_runtime_gpu import (  # noqa: E402
    build_geometric_phase_state_gpu,
    materialise_geometric_common_flux_state_gpu,
    materialise_geometric_runtime_capillary_application_state_gpu,
    materialise_geometric_runtime_capillary_state_gpu,
    transport_geometric_phase_common_flux_2d_gpu,
    validate_geometric_runtime_capillary_fail_close_gpu,
)


def _scalar(backend, value) -> float:
    return float(np.asarray(backend.to_host(value)))


def _row(label: str, fields: dict[str, object]) -> None:
    names = [
        "label",
        "status",
        "fail_close",
        "compat_linf",
        "range_status",
        "exact_static",
        "drive_present",
        "force_l2",
        "reaction_l2",
        "balanced_l2",
        "balanced_max",
        "yl_residual_l2",
        "yl_normal_linf",
        "residual_accel_l2",
        "residual_face_max",
    ]
    values = {"label": label, **fields}
    print(",".join(str(values.get(name, "")) for name in names))


def _header() -> None:
    print(
        "label,status,fail_close,compat_linf,range_status,exact_static,"
        "drive_present,force_l2,reaction_l2,balanced_l2,balanced_max,"
        "yl_residual_l2,yl_normal_linf,residual_accel_l2,residual_face_max"
    )


def _phi_field(
    grid,
    *,
    mode: str,
    amplitude: float,
    wave_number: int,
    center_fraction: float,
):
    xp = grid.xp
    x, y = grid.meshgrid()
    center_y = center_fraction * float(grid.L[1])
    if mode == "flat":
        interface_y = center_y
    elif mode == "capillary_wave":
        interface_y = center_y + amplitude * xp.cos(
            2.0 * xp.pi * int(wave_number) * x / float(grid.L[0])
        )
    else:
        raise ValueError(f"unsupported mode {mode!r}")
    return y - interface_y


def _zero_face_velocity(grid):
    xp = grid.xp
    return (
        xp.zeros((grid.N[0] + 1, grid.N[1])),
        xp.zeros((grid.N[0], grid.N[1] + 1)),
    )


def _build_grid(*, backend, nx: int, ny: int, lx: float, ly: float, boundary):
    grid = Grid(
        GridConfig(ndim=2, N=(nx, ny), L=(lx, ly)),
        backend,
    )
    grid.bc_type = boundary
    return grid


def _cpu_exact(args, boundary):
    backend = Backend(use_gpu=False)
    grid = _build_grid(
        backend=backend,
        nx=args.nx,
        ny=args.ny,
        lx=args.lx,
        ly=args.ly,
        boundary=boundary,
    )
    phi = _phi_field(
        grid,
        mode=args.mode,
        amplitude=args.amplitude,
        wave_number=args.wave_number,
        center_fraction=args.center_fraction,
    )
    state = GeometricPhaseState.from_phi(grid, phi)
    transport = transport_geometric_phase_common_flux_2d(
        grid,
        state,
        _zero_face_velocity(grid),
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    material = materialise_geometric_common_flux_state(
        grid,
        transport,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    capillary = materialise_geometric_runtime_capillary_state(
        grid,
        material,
        sigma=args.sigma,
        tolerance=args.tolerance,
    )
    app = materialise_geometric_runtime_capillary_application_state(
        grid,
        capillary,
        dt=args.dt,
    )
    return {
        "status": "ok",
        "fail_close": "",
        "compat_linf": capillary.material.phase_state.compatibility_residual_linf,
        "range_status": capillary.pressure_range_status,
        "exact_static": capillary.pressure_exact_static,
        "drive_present": capillary.capillary_drive_present,
        "force_l2": capillary.capillary_force_weighted_acceleration_l2,
        "reaction_l2": capillary.pressure_reaction_weighted_acceleration_l2,
        "balanced_l2": app.pressure_balanced_increment_weighted_l2,
        "balanced_max": app.max_abs_pressure_balanced_face_increment,
        "yl_residual_l2": capillary.young_laplace_residual_l2,
        "yl_normal_linf": capillary.young_laplace_normal_residual_linf,
        "residual_accel_l2": capillary.weighted_residual_acceleration_l2,
        "residual_face_max": capillary.max_abs_residual_face_covector,
    }


def _cpu_component_hodge(args, boundary):
    backend = Backend(use_gpu=False)
    grid = _build_grid(
        backend=backend,
        nx=args.nx,
        ny=args.ny,
        lx=args.lx,
        ly=args.ly,
        boundary=boundary,
    )
    phi = _phi_field(
        grid,
        mode=args.mode,
        amplitude=args.amplitude,
        wave_number=args.wave_number,
        center_fraction=args.center_fraction,
    )
    state = GeometricPhaseState.from_phi(grid, phi)
    hodge = geometric_component_volume_reaction_hodge_2d(
        grid,
        state,
        sigma=args.sigma,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    pressure_hodge = geometric_pressure_capillary_hodge_2d(
        grid,
        state,
        sigma=args.sigma,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    return {
        "status": "ok",
        "fail_close": "",
        "compat_linf": state.compatibility_residual_linf,
        "range_status": "component_volume_reaction_residual",
        "exact_static": hodge.residual_weighted_l2 <= args.tolerance,
        "drive_present": hodge.residual_weighted_l2 > args.tolerance,
        "force_l2": hodge.source_weighted_l2,
        "reaction_l2": hodge.represented_weighted_l2,
        "balanced_l2": hodge.residual_weighted_l2,
        "balanced_max": hodge.max_abs_residual_face_covector,
        "yl_residual_l2": pressure_hodge.young_laplace_residual.residual_l2,
        "yl_normal_linf": hodge.max_component_orthogonality,
        "residual_accel_l2": hodge.residual_weighted_l2,
        "residual_face_max": hodge.max_abs_residual_face_covector,
    }


def _gpu_packet(args, boundary):
    try:
        backend = Backend(use_gpu=True)
    except RuntimeError as exc:
        return {"status": "skip", "fail_close": f"GPU unavailable: {exc}"}
    grid = _build_grid(
        backend=backend,
        nx=args.nx,
        ny=args.ny,
        lx=args.lx,
        ly=args.ly,
        boundary=boundary,
    )
    phi = _phi_field(
        grid,
        mode=args.mode,
        amplitude=args.amplitude,
        wave_number=args.wave_number,
        center_fraction=args.center_fraction,
    )
    state = build_geometric_phase_state_gpu(grid, phi)
    transport = transport_geometric_phase_common_flux_2d_gpu(
        grid,
        state,
        _zero_face_velocity(grid),
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    material = materialise_geometric_common_flux_state_gpu(
        grid,
        transport,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    capillary = materialise_geometric_runtime_capillary_state_gpu(
        grid,
        material,
        sigma=args.sigma,
        tolerance=args.tolerance,
    )
    app = materialise_geometric_runtime_capillary_application_state_gpu(
        grid,
        capillary,
        dt=args.dt,
    )
    fail_close = ""
    try:
        validate_geometric_runtime_capillary_fail_close_gpu(
            backend,
            capillary,
            app,
            ppe_runtime=SimpleNamespace(pressure_history_mode=args.pressure_history),
        )
    except ValueError as exc:
        fail_close = str(exc)
    return {
        "status": "ok",
        "fail_close": fail_close,
        "compat_linf": _scalar(
            backend,
            capillary.material.phase_state.compatibility_residual_linf,
        ),
        "range_status": capillary.pressure_range_status,
        "exact_static": capillary.pressure_exact_static,
        "drive_present": capillary.capillary_drive_present,
        "force_l2": _scalar(backend, capillary.capillary_force_weighted_acceleration_l2),
        "reaction_l2": _scalar(
            backend,
            capillary.pressure_reaction_weighted_acceleration_l2,
        ),
        "balanced_l2": _scalar(backend, app.pressure_balanced_increment_weighted_l2),
        "balanced_max": _scalar(
            backend,
            app.max_abs_pressure_balanced_face_increment,
        ),
        "yl_residual_l2": _scalar(backend, capillary.young_laplace_residual_l2),
        "yl_normal_linf": _scalar(
            backend,
            capillary.young_laplace_normal_residual_linf,
        ),
        "residual_accel_l2": _scalar(
            backend,
            capillary.weighted_residual_acceleration_l2,
        ),
        "residual_face_max": _scalar(
            backend,
            capillary.max_abs_residual_face_covector,
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("flat", "capillary_wave"), default="capillary_wave")
    parser.add_argument("--nx", type=int, default=32)
    parser.add_argument("--ny", type=int, default=32)
    parser.add_argument("--lx", type=float, default=0.02)
    parser.add_argument("--ly", type=float, default=0.02)
    parser.add_argument("--amplitude", type=float, default=2.0e-4)
    parser.add_argument("--center-fraction", type=float, default=0.47)
    parser.add_argument("--wave-number", type=int, default=2)
    parser.add_argument("--sigma", type=float, default=0.0728)
    parser.add_argument("--rho-l", type=float, default=998.2)
    parser.add_argument("--rho-g", type=float, default=1.204)
    parser.add_argument("--dt", type=float, default=1.0e-5)
    parser.add_argument("--tolerance", type=float, default=1.0e-11)
    parser.add_argument("--pressure-history", choices=("face_acceleration", "pressure_coordinate"), default="pressure_coordinate")
    parser.add_argument("--boundary-x", choices=("wall", "periodic"), default="periodic")
    parser.add_argument("--boundary-y", choices=("wall", "periodic"), default="wall")
    args = parser.parse_args()

    boundary = (args.boundary_x, args.boundary_y)
    _header()
    try:
        _row("cpu_exact", _cpu_exact(args, boundary))
    except Exception as exc:
        _row("cpu_exact", {"status": "error", "fail_close": repr(exc)})
    try:
        _row("cpu_component_hodge", _cpu_component_hodge(args, boundary))
    except Exception as exc:
        _row("cpu_component_hodge", {"status": "error", "fail_close": repr(exc)})
    try:
        _row("gpu_packet", _gpu_packet(args, boundary))
    except Exception as exc:
        _row("gpu_packet", {"status": "error", "fail_close": repr(exc)})


if __name__ == "__main__":
    main()
