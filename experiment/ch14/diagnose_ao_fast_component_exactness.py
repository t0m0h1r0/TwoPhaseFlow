#!/usr/bin/env python3
"""Component-wise CPU-oracle exactness probe for AO-Fast.

The probe compares the current GPU AO-Fast runtime pieces against the dense
CPU SP-AO oracle on the same regular P1 sign stratum.  It is diagnostic: a
failing row identifies the component whose algebra no longer matches the
oracle, without masking the mismatch by a downstream tolerance change.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.geometry.p1_cut_geometry import cut_geometry_2d  # noqa: E402
from twophase.geometry.p1_cut_jacobian import (  # noqa: E402
    cut_geometry_derivatives_2d,
)
from twophase.geometry.phase_state import (  # noqa: E402
    GeometricPhaseState,
    transport_geometric_phase_common_flux_2d,
)
from twophase.simulation.geometric_phase_runtime import (  # noqa: E402
    materialise_geometric_common_flux_state,
    materialise_geometric_runtime_capillary_state,
)
from twophase.simulation.geometric_phase_runtime_gpu import (  # noqa: E402
    _apply_schur_full_gpu,
    _geometry_and_derivatives_full,
    _solve_schur_for_active_policy_gpu,
    build_geometric_phase_state_gpu,
    materialise_geometric_common_flux_state_gpu,
    materialise_geometric_runtime_capillary_state_gpu,
    transport_geometric_phase_common_flux_2d_gpu,
)


def _make_grid(backend, args):
    grid = Grid(
        GridConfig(ndim=2, N=(args.nx, args.ny), L=(args.lx, args.ly)),
        backend,
    )
    grid.bc_type = (args.boundary_x, args.boundary_y)
    return grid


def _phi_np(grid, args):
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    xx, yy = np.meshgrid(x, y, indexing="ij")
    interface_y = args.center_fraction * args.ly + args.amplitude * np.cos(
        2.0 * np.pi * args.wave_number * xx / args.lx
    )
    return yy - interface_y


def _zero_velocity_np(args):
    return (
        np.zeros((args.nx + 1, args.ny), dtype=float),
        np.zeros((args.nx, args.ny + 1), dtype=float),
    )


def _transport_velocity_np(args):
    return (
        args.u0 * np.ones((args.nx + 1, args.ny), dtype=float),
        np.zeros((args.nx, args.ny + 1), dtype=float),
    )


def _to_gpu_pair(xp, pair):
    return tuple(xp.asarray(component) for component in pair)


def _host(backend, value):
    return np.asarray(backend.to_host(value))


def _max_abs(value):
    array = np.asarray(value, dtype=float)
    if array.size == 0:
        return 0.0
    return float(np.max(np.abs(array)))


def _max_diff(cpu_value, gpu_backend, gpu_value):
    return _max_abs(np.asarray(cpu_value) - _host(gpu_backend, gpu_value))


def _max_pair_diff(cpu_pair, gpu_backend, gpu_pair):
    return max(
        _max_diff(cpu_component, gpu_backend, gpu_component)
        for cpu_component, gpu_component in zip(cpu_pair, gpu_pair, strict=True)
    )


def _status(value, tolerance):
    return "PASS" if value <= tolerance else "FAIL"


def _row(component, metric, value, tolerance, note=""):
    print(
        f"{component},{metric},{value:.16e},{tolerance:.16e},"
        f"{_status(value, tolerance)},{note}"
    )


def _geometry_rows(cpu_grid, gpu_grid, gpu_backend, phi_np, phi_gpu, args):
    cpu_geom = cut_geometry_2d(cpu_grid, phi_np)
    cpu_deriv = cut_geometry_derivatives_2d(cpu_grid, phi_np)
    gpu_geom, gpu_deriv = _geometry_and_derivatives_full(gpu_grid, phi_gpu, level=0.0)
    tol = args.exact_tolerance
    _row("geometry", "q_linf_diff", _max_diff(cpu_geom.q, gpu_backend, gpu_geom.q), tol)
    _row(
        "geometry",
        "theta_linf_diff",
        _max_diff(cpu_geom.theta, gpu_backend, gpu_geom.theta),
        tol,
    )
    _row(
        "geometry",
        "cell_surface_linf_diff",
        _max_diff(cpu_geom.cell_surface_lengths, gpu_backend, gpu_geom.cell_surface_lengths),
        tol,
    )
    _row(
        "geometry",
        "surface_length_diff",
        abs(float(cpu_geom.surface_length) - float(_host(gpu_backend, gpu_geom.surface_length))),
        tol,
    )
    _row(
        "geometry",
        "Jq_local_linf_diff",
        _max_diff(cpu_deriv.jq_local, gpu_backend, gpu_deriv.jq_local),
        tol,
    )
    _row(
        "geometry",
        "dS_local_linf_diff",
        _max_diff(cpu_deriv.ds_local, gpu_backend, gpu_deriv.ds_local),
        tol,
    )
    return cpu_geom, cpu_deriv, gpu_geom, gpu_deriv


def _transport_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args):
    boundary = (args.boundary_x, args.boundary_y)
    velocity_cpu = _transport_velocity_np(args)
    velocity_gpu = _to_gpu_pair(gpu_backend.xp, velocity_cpu)
    cpu_result = transport_geometric_phase_common_flux_2d(
        cpu_grid,
        cpu_state,
        velocity_cpu,
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
        project_every_steps=0,
    )
    gpu_result = transport_geometric_phase_common_flux_2d_gpu(
        gpu_grid,
        gpu_state,
        velocity_gpu,
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
        project_every_steps=0,
    )
    tol = args.exact_tolerance
    _row(
        "transport",
        "phase_flux_linf_diff",
        _max_pair_diff(
            cpu_result.phase_transport.swept_flux.phase_fluxes,
            gpu_backend,
            gpu_result.phase_transport.swept_flux.phase_fluxes,
        ),
        tol,
    )
    _row(
        "transport",
        "q_after_flux_linf_diff",
        _max_diff(
            cpu_result.phase_transport.pre_projection_state.q,
            gpu_backend,
            gpu_result.phase_transport.pre_projection_state.q,
        ),
        tol,
    )
    _row(
        "transport",
        "mass_flux_linf_diff",
        _max_pair_diff(cpu_result.mass_fluxes, gpu_backend, gpu_result.mass_fluxes),
        tol,
    )
    return cpu_result, gpu_result


def _projection_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args):
    boundary = (args.boundary_x, args.boundary_y)
    velocity_cpu = _transport_velocity_np(args)
    velocity_gpu = _to_gpu_pair(gpu_backend.xp, velocity_cpu)
    tol = args.tolerance
    try:
        cpu_result = transport_geometric_phase_common_flux_2d(
            cpu_grid,
            cpu_state,
            velocity_cpu,
            dt=args.dt,
            rho_l=args.rho_l,
            rho_g=args.rho_g,
            boundary=boundary,
            tolerance=tol,
            project_every_steps=1,
            step_index=1,
            max_newton_iterations=args.newton,
            max_cg_iterations=args.max_pcg_iterations,
        )
        cpu_residual = float(cpu_result.phase_transport.state.compatibility_residual_linf)
        _row("projection_cpu", "full_q_minus_Q_residual", cpu_residual, tol)
    except Exception as exc:
        _row("projection_cpu", "exception", np.inf, tol, repr(exc).replace(",", ";"))
    gpu_result = transport_geometric_phase_common_flux_2d_gpu(
        gpu_grid,
        gpu_state,
        velocity_gpu,
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=tol,
        project_every_steps=1,
        step_index=1,
        max_newton_iterations=args.newton,
        solver_scheme=args.scheme,
        pcg_tolerance=args.pcg_tolerance,
        pcg_max_iterations=args.max_pcg_iterations,
        pcg_roundoff_floor=args.pcg_roundoff_floor,
        dc_tolerance=args.dc_tolerance,
        dc_max_iterations=args.dc_max_iterations,
        dc_relaxation=args.dc_relaxation,
    )
    gpu_residual = float(
        _host(gpu_backend, gpu_result.phase_transport.state.compatibility_residual_linf)
    )
    _row("projection_gpu", "full_q_minus_Q_residual", gpu_residual, tol)
    return gpu_result


def _schur_rows(gpu_grid, gpu_backend, gpu_deriv, args):
    xp = gpu_backend.xp
    x = xp.asarray(gpu_grid.coords[0], dtype=gpu_deriv.jq_local.dtype).reshape((-1, 1))
    y = xp.asarray(gpu_grid.coords[1], dtype=gpu_deriv.jq_local.dtype).reshape((1, -1))
    nodal = xp.sin(2.0 * xp.pi * x / args.lx) + 0.5 * xp.cos(2.0 * xp.pi * y / args.ly)
    rhs = xp.where(
        xp.sum(gpu_deriv.jq_local * gpu_deriv.jq_local, axis=-1) > 0.0,
        xp.sum(gpu_deriv.jq_local * _local_corners(xp, nodal), axis=-1),
        xp.zeros(tuple(gpu_grid.N), dtype=gpu_deriv.jq_local.dtype),
    )
    row_norm = xp.sum(gpu_deriv.jq_local * gpu_deriv.jq_local, axis=-1)
    active = row_norm > 0.0
    for scheme in ("pcg", "dc", "dc_then_pcg"):
        lagrange = _solve_schur_for_active_policy_gpu(
            gpu_grid,
            xp,
            gpu_deriv.jq_local,
            rhs,
            row_norm,
            active,
            solver_scheme=scheme,
            pcg_tolerance=args.pcg_tolerance,
            pcg_max_iterations=args.max_pcg_iterations,
            pcg_roundoff_floor=args.pcg_roundoff_floor,
            dc_tolerance=args.dc_tolerance,
            dc_max_iterations=args.dc_max_iterations,
            dc_relaxation=args.dc_relaxation,
        )
        residual = xp.where(
            active,
            _apply_schur_full_gpu(gpu_grid, xp, gpu_deriv.jq_local, lagrange) - rhs,
            xp.zeros_like(rhs),
        )
        value = float(_host(gpu_backend, xp.max(xp.abs(residual))))
        _row(f"schur_{scheme}", "active_residual_linf", value, args.tolerance)


def _local_corners(xp, nodal):
    return xp.stack(
        (
            nodal[:-1, :-1],
            nodal[1:, :-1],
            nodal[1:, 1:],
            nodal[:-1, 1:],
        ),
        axis=-1,
    )


def _hodge_and_capillary_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args):
    boundary = (args.boundary_x, args.boundary_y)
    zero_cpu = _zero_velocity_np(args)
    zero_gpu = _to_gpu_pair(gpu_backend.xp, zero_cpu)
    cpu_result = transport_geometric_phase_common_flux_2d(
        cpu_grid,
        cpu_state,
        zero_cpu,
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    gpu_result = transport_geometric_phase_common_flux_2d_gpu(
        gpu_grid,
        gpu_state,
        zero_gpu,
        dt=args.dt,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    cpu_material = materialise_geometric_common_flux_state(
        cpu_grid,
        cpu_result,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    gpu_material = materialise_geometric_common_flux_state_gpu(
        gpu_grid,
        gpu_result,
        rho_l=args.rho_l,
        rho_g=args.rho_g,
        boundary=boundary,
        tolerance=args.tolerance,
    )
    _row(
        "face_hodge",
        "density_linf_diff",
        _max_diff(cpu_material.density, gpu_backend, gpu_material.density),
        args.exact_tolerance,
    )
    _row(
        "face_hodge",
        "weights_linf_diff",
        _max_pair_diff(
            cpu_material.face_hodge.weights,
            gpu_backend,
            gpu_material.face_hodge.weights,
        ),
        args.exact_tolerance,
    )
    cpu_capillary = materialise_geometric_runtime_capillary_state(
        cpu_grid,
        cpu_material,
        sigma=args.sigma,
        tolerance=args.tolerance,
        max_cg_iterations=args.max_pcg_iterations,
    )
    gpu_capillary = materialise_geometric_runtime_capillary_state_gpu(
        gpu_grid,
        gpu_material,
        sigma=args.sigma,
        tolerance=args.tolerance,
        solver_scheme=args.scheme,
        pcg_tolerance=args.pcg_tolerance,
        max_pcg_iterations=args.max_pcg_iterations,
        pcg_roundoff_floor=args.pcg_roundoff_floor,
        dc_tolerance=args.dc_tolerance,
        dc_max_iterations=args.dc_max_iterations,
        dc_relaxation=args.dc_relaxation,
    )
    cpu_surface = (
        cpu_capillary.pressure_capillary_hodge
        .capillary_riesz
        .surface_covector
        .surface_energy
    )
    gpu_surface = (
        gpu_capillary.pressure_capillary_hodge
        .capillary_riesz
        .surface_covector
        .surface_energy
    )
    _row(
        "capillary_riesz",
        "surface_energy_diff",
        abs(float(cpu_surface) - float(_host(gpu_backend, gpu_surface))),
        args.exact_tolerance,
    )
    _row(
        "capillary_riesz",
        "raw_face_covector_linf_diff",
        _max_pair_diff(
            cpu_capillary.capillary_force_face_covectors,
            gpu_backend,
            gpu_capillary.capillary_force_face_covectors,
        ),
        args.tolerance,
    )
    _row(
        "capillary_riesz_cpu",
        "normal_residual_linf",
        float(cpu_capillary.young_laplace_normal_residual_linf),
        args.tolerance,
    )
    _row(
        "capillary_riesz_gpu",
        "normal_residual_linf",
        float(_host(gpu_backend, gpu_capillary.young_laplace_normal_residual_linf)),
        args.tolerance,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nx", type=int, default=32)
    parser.add_argument("--ny", type=int, default=32)
    parser.add_argument("--lx", type=float, default=0.02)
    parser.add_argument("--ly", type=float, default=0.02)
    parser.add_argument("--amplitude", type=float, default=2.0e-4)
    parser.add_argument("--center-fraction", type=float, default=0.47)
    parser.add_argument("--wave-number", type=int, default=2)
    parser.add_argument("--u0", type=float, default=2.0e-2)
    parser.add_argument("--dt", type=float, default=1.0e-5)
    parser.add_argument("--rho-l", type=float, default=998.2)
    parser.add_argument("--rho-g", type=float, default=1.204)
    parser.add_argument("--sigma", type=float, default=0.0728)
    parser.add_argument("--boundary-x", choices=("periodic", "wall"), default="periodic")
    parser.add_argument("--boundary-y", choices=("periodic", "wall"), default="wall")
    parser.add_argument("--tolerance", type=float, default=1.0e-11)
    parser.add_argument("--exact-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--newton", type=int, default=32)
    parser.add_argument("--scheme", choices=("pcg", "dc", "dc_then_pcg"), default="pcg")
    parser.add_argument("--pcg-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--max-pcg-iterations", type=int, default=256)
    parser.add_argument("--pcg-roundoff-floor", type=float, default=1.0e-14)
    parser.add_argument("--dc-tolerance", type=float, default=1.0e-11)
    parser.add_argument("--dc-max-iterations", type=int, default=8)
    parser.add_argument("--dc-relaxation", type=float, default=1.0)
    args = parser.parse_args()

    cpu_backend = Backend(use_gpu=False)
    gpu_backend = Backend(use_gpu=True)
    cpu_grid = _make_grid(cpu_backend, args)
    gpu_grid = _make_grid(gpu_backend, args)
    phi_np = _phi_np(cpu_grid, args)
    phi_gpu = gpu_backend.xp.asarray(phi_np)
    cpu_state = GeometricPhaseState.from_phi(cpu_grid, phi_np)
    gpu_state = build_geometric_phase_state_gpu(gpu_grid, phi_gpu)

    print("component,metric,value,tolerance,status,note")
    _row(
        "initial_state",
        "gpu_q_minus_Q_residual",
        float(_host(gpu_backend, gpu_state.compatibility_residual_linf)),
        args.tolerance,
    )
    _cpu_geom, _cpu_deriv, _gpu_geom, gpu_deriv = _geometry_rows(
        cpu_grid,
        gpu_grid,
        gpu_backend,
        phi_np,
        phi_gpu,
        args,
    )
    _transport_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args)
    _projection_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args)
    _schur_rows(gpu_grid, gpu_backend, gpu_deriv, args)
    _hodge_and_capillary_rows(cpu_grid, gpu_grid, gpu_backend, cpu_state, gpu_state, args)


if __name__ == "__main__":
    main()
