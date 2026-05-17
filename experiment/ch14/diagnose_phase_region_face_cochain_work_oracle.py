#!/usr/bin/env python3
"""PhaseRegion endpoint face-cochain work-pairing oracle.

A3 mapping
----------
Equation:
    The interface covector ``dE_h`` must reach the pressure/velocity endpoint
    through the same transport map used by the finite-volume phase update:
    ``T_h(u_f) = -D_f(psi_f u_f)``.  The face cochain is the Riesz
    representative ``s_f = -M_f^{-1} T_h^T dE_h`` and must satisfy
    ``dE_h[T_h(u_f)] + <s_f, u_f>_{M_f} = 0``.
Discretization:
    Use the existing fixed-stratum closed-interface Riesz diagnostic on an
    FCCD/FVM face complex.  The uniform periodic ellipse checks virtual work;
    a nonuniform periodic-wall grid checks the negative face-divergence
    adjoint identity on boundary-aware face shapes.
Code:
    This is an experiment oracle only.  It does not connect PhaseRegion force
    to the Ch14 runtime, pressure projection, velocity update, nonlinear
    optimization, micro-steps, or T/8.
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib.pyplot as plt
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from twophase.backend import Backend  # noqa: E402
from twophase.ccd.ccd_solver import CCDSolver  # noqa: E402
from twophase.ccd.fccd import FCCDSolver  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.coupling.closed_interface_riesz import (  # noqa: E402
    _dense_divergence_matrix,
    _flatten_face_components,
    _unflatten_face_components,
    closed_interface_riesz_cochain,
    face_measure_components,
    fixed_stratum_virtual_work_check,
    weighted_hodge_decomposition,
)
from twophase.coupling.transport_variational_capillary import (  # noqa: E402
    _negative_face_divergence_adjoint,
)
from twophase.simulation.divergence_ops import FCCDDivergenceOperator  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()

OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"


def _setup_grid(
    n: int,
    *,
    length: tuple[float, float] = (1.0, 1.0),
    alpha_grid: float = 1.0,
    bc_type: str = "periodic",
) -> tuple[Grid, Backend, FCCDSolver, FCCDDivergenceOperator]:
    backend = Backend(use_gpu=False)
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(int(n), int(n)),
            L=(float(length[0]), float(length[1])),
            alpha_grid=float(alpha_grid),
        ),
        backend,
    )
    ccd = CCDSolver(grid, backend, bc_type=bc_type)
    fccd = FCCDSolver(grid, backend, bc_type=bc_type, ccd_solver=ccd)
    return grid, backend, fccd, FCCDDivergenceOperator(fccd)


def _setup_nonuniform_periodic_wall() -> tuple[Grid, Backend, FCCDSolver]:
    backend = Backend(use_gpu=False)
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(5, 6),
            L=(1.0, 1.3),
            alpha_grid=2.0,
        ),
        backend,
    )
    for axis, power in enumerate((1.15, 1.35)):
        xi = np.linspace(0.0, 1.0, grid.N[axis] + 1)
        coords = grid.L[axis] * xi**power
        coords[-1] = grid.L[axis]
        grid.coords[axis] = coords
        cell_width = np.diff(coords)
        node_width = np.empty(grid.N[axis] + 1)
        node_width[0] = cell_width[0]
        node_width[-1] = cell_width[-1]
        node_width[1:-1] = 0.5 * (cell_width[:-1] + cell_width[1:])
        grid.h[axis] = node_width
    ccd = CCDSolver(grid, backend, bc_type="periodic_wall")
    grid._build_metrics(ccd=ccd)
    fccd = FCCDSolver(grid, backend, bc_type="periodic_wall", ccd_solver=ccd)
    return grid, backend, fccd


def _ellipse_psi(grid: Grid, *, a: float, b: float) -> np.ndarray:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = np.sqrt(((X - 0.5) / float(a)) ** 2 + ((Y - 0.5) / float(b)) ** 2) - 1.0
    eps = 1.5 / float(grid.N[0]) / 0.25
    return 1.0 / (1.0 + np.exp(phi / eps))


def _smooth_face_velocity(grid: Grid) -> list[np.ndarray]:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    x_faces = 0.5 * (x[:-1] + x[1:])
    y_faces = 0.5 * (y[:-1] + y[1:])
    X0, Y0 = np.meshgrid(x_faces, y, indexing="ij")
    X1, Y1 = np.meshgrid(x, y_faces, indexing="ij")
    return [
        np.sin(2.0 * np.pi * X0) * np.cos(np.pi * Y0),
        -0.5 * np.cos(np.pi * X1) * np.sin(2.0 * np.pi * Y1),
    ]


def _nonuniform_adjoint_error() -> float:
    grid, backend, fccd = _setup_nonuniform_periodic_wall()
    xp = backend.xp
    nodal_index = np.arange(np.prod(grid.shape), dtype=float).reshape(grid.shape)
    covector = np.sin(0.23 * nodal_index) + 0.3 * np.cos(0.41 * nodal_index)
    errors = []
    for axis in range(grid.ndim):
        face_shape = list(grid.shape)
        face_shape[axis] = grid.N[axis]
        face_index = np.arange(np.prod(face_shape), dtype=float).reshape(face_shape)
        face_flux = np.cos(0.17 * face_index) - 0.2 * np.sin(0.31 * face_index)
        divergence = np.asarray(fccd.face_divergence(xp.asarray(face_flux), axis=axis))
        adjoint = np.asarray(
            _negative_face_divergence_adjoint(
                xp=xp,
                fccd=fccd,
                nodal_covector=xp.asarray(covector),
                axis=axis,
            )
        )
        lhs = float(np.vdot(covector, -divergence))
        rhs = float(np.vdot(adjoint, face_flux))
        errors.append(abs(lhs - rhs))
    return float(max(errors))


def _manufactured_pressure_range_error(
    *,
    xp,
    grid: Grid,
    div_op: FCCDDivergenceOperator,
    weights: list[np.ndarray],
) -> tuple[float, float]:
    D, shapes, sizes = _dense_divergence_matrix(
        xp=xp,
        div_op=div_op,
        face_templates=weights,
    )
    weight_flat = _flatten_face_components(xp, weights)
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    X, Y = np.meshgrid(x, y, indexing="ij")
    potential = (
        np.sin(2.0 * np.pi * X) * np.cos(3.0 * np.pi * Y)
        + 0.31 * np.cos(np.pi * X + 0.2) * np.sin(2.0 * np.pi * Y + 0.1)
    )
    range_flat = (D.T @ potential.ravel()) / weight_flat
    range_components = _unflatten_face_components(xp, range_flat, shapes, sizes)
    decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=range_components,
        face_weight_components=weights,
    )
    recovered_flat = _flatten_face_components(xp, decomposition.range_components)
    hodge_flat = _flatten_face_components(xp, decomposition.hodge_components)
    hodge_l2 = float(np.sqrt(np.sum(hodge_flat * hodge_flat * weight_flat)))
    recovery_linf = float(np.max(np.abs(recovered_flat - range_flat)))
    return hodge_l2, recovery_linf


def _cell_center_quiver(grid: Grid, face_components: list[np.ndarray]) -> tuple[np.ndarray, ...]:
    x = np.asarray(grid.coords[0], dtype=float)
    y = np.asarray(grid.coords[1], dtype=float)
    xc = 0.5 * (x[:-1] + x[1:])
    yc = 0.5 * (y[:-1] + y[1:])
    Xc, Yc = np.meshgrid(xc, yc, indexing="ij")
    u = 0.5 * (np.asarray(face_components[0])[:, :-1] + np.asarray(face_components[0])[:, 1:])
    v = 0.5 * (np.asarray(face_components[1])[:-1, :] + np.asarray(face_components[1])[1:, :])
    return Xc, Yc, u, v


def _compute(args) -> dict[str, object]:
    grid, backend, fccd, div_op = _setup_grid(int(args.n), bc_type="periodic")
    xp = backend.xp
    psi = _ellipse_psi(grid, a=float(args.axis_a), b=float(args.axis_b))
    cochain = closed_interface_riesz_cochain(
        xp=xp,
        grid=grid,
        psi=psi,
        fccd=fccd,
        sigma=float(args.sigma),
    )
    check_self = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=cochain.surface_acceleration,
        epsilon=float(args.fd_eps),
    )
    smooth_velocity = [xp.asarray(component) for component in _smooth_face_velocity(grid)]
    probe_velocity = [
        surface + 0.125 * smooth
        for surface, smooth in zip(cochain.surface_acceleration, smooth_velocity, strict=True)
    ]
    check_probe = fixed_stratum_virtual_work_check(
        xp=xp,
        grid=grid,
        fccd=fccd,
        cochain=cochain,
        face_velocity_components=probe_velocity,
        epsilon=float(args.fd_eps),
    )
    decomposition = weighted_hodge_decomposition(
        xp=xp,
        div_op=div_op,
        face_components=cochain.surface_acceleration,
        face_weight_components=cochain.face_weight_components,
    )
    range_hodge_l2, range_recovery_linf = _manufactured_pressure_range_error(
        xp=xp,
        grid=grid,
        div_op=div_op,
        weights=[np.asarray(component, dtype=float) for component in face_measure_components(xp=xp, grid=grid)],
    )
    nonuniform_adjoint_error = _nonuniform_adjoint_error()

    if not check_self.valid:
        raise AssertionError(f"self virtual work left stratum: {check_self.reason}")
    if not check_probe.valid:
        raise AssertionError(f"probe virtual work left stratum: {check_probe.reason}")
    if check_self.riesz_residual > float(args.riesz_tolerance):
        raise AssertionError("self Riesz work pairing failed")
    if check_self.finite_difference_power_residual > float(args.fd_power_tolerance):
        raise AssertionError("self finite-difference power pairing failed")
    if check_probe.riesz_residual > float(args.riesz_tolerance):
        raise AssertionError("probe Riesz work pairing failed")
    if check_probe.finite_difference_power_residual > float(args.fd_power_tolerance):
        raise AssertionError("probe finite-difference power pairing failed")
    if decomposition.hodge_divergence_linf > float(args.divergence_tolerance):
        raise AssertionError("Hodge residual is not divergence-free")
    if range_hodge_l2 > float(args.range_tolerance):
        raise AssertionError("manufactured pressure range leaked into Hodge space")
    if range_recovery_linf > float(args.range_tolerance):
        raise AssertionError("manufactured pressure range was not recovered")
    if nonuniform_adjoint_error > float(args.nonuniform_adjoint_tolerance):
        raise AssertionError("nonuniform periodic-wall face adjoint failed")

    return {
        "x_edges": np.asarray(grid.coords[0], dtype=float),
        "y_edges": np.asarray(grid.coords[1], dtype=float),
        "psi": psi,
        "surface_acceleration_0": np.asarray(cochain.surface_acceleration[0], dtype=float),
        "surface_acceleration_1": np.asarray(cochain.surface_acceleration[1], dtype=float),
        "range_component_0": np.asarray(decomposition.range_components[0], dtype=float),
        "range_component_1": np.asarray(decomposition.range_components[1], dtype=float),
        "hodge_component_0": np.asarray(decomposition.hodge_components[0], dtype=float),
        "hodge_component_1": np.asarray(decomposition.hodge_components[1], dtype=float),
        "self_fd_gradient_residual": float(check_self.finite_difference_gradient_residual),
        "self_fd_power_residual": float(check_self.finite_difference_power_residual),
        "self_riesz_residual": float(check_self.riesz_residual),
        "self_finite_difference": float(check_self.finite_difference),
        "self_capillary_power": float(check_self.capillary_power),
        "probe_fd_gradient_residual": float(check_probe.finite_difference_gradient_residual),
        "probe_fd_power_residual": float(check_probe.finite_difference_power_residual),
        "probe_riesz_residual": float(check_probe.riesz_residual),
        "probe_finite_difference": float(check_probe.finite_difference),
        "probe_capillary_power": float(check_probe.capillary_power),
        "component_weighted_l2": float(decomposition.component_weighted_l2),
        "range_weighted_l2": float(decomposition.range_weighted_l2),
        "hodge_weighted_l2": float(decomposition.hodge_weighted_l2),
        "hodge_divergence_linf": float(decomposition.hodge_divergence_linf),
        "manufactured_range_hodge_l2": float(range_hodge_l2),
        "manufactured_range_recovery_linf": float(range_recovery_linf),
        "nonuniform_adjoint_error": float(nonuniform_adjoint_error),
        "force_admissible": 0.0,
    }


def _plot(results: dict[str, object]) -> pathlib.Path:
    x_edges = np.asarray(results["x_edges"], dtype=float)
    y_edges = np.asarray(results["y_edges"], dtype=float)
    psi = np.asarray(results["psi"], dtype=float)
    acceleration = [
        np.asarray(results["surface_acceleration_0"], dtype=float),
        np.asarray(results["surface_acceleration_1"], dtype=float),
    ]
    hodge = [
        np.asarray(results["hodge_component_0"], dtype=float),
        np.asarray(results["hodge_component_1"], dtype=float),
    ]
    Xc, Yc, u, v = _cell_center_quiver(
        _grid_shell_from_edges(x_edges, y_edges),
        acceleration,
    )
    _, _, uh, vh = _cell_center_quiver(_grid_shell_from_edges(x_edges, y_edges), hodge)
    stride = max(int(Xc.shape[0]) // 16, 1)
    speed = np.sqrt(u * u + v * v)
    hodge_speed = np.sqrt(uh * uh + vh * vh)

    fig, axes = plt.subplots(1, 3, figsize=(12.2, 3.9), constrained_layout=True)
    ax = axes[0]
    mesh = ax.pcolormesh(x_edges, y_edges, psi.T, shading="auto", cmap="viridis")
    ax.contour(x_edges, y_edges, psi.T, levels=(0.5,), colors="black", linewidths=1.0)
    ax.set_title("fixed stratum psi")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(mesh, ax=ax)

    ax = axes[1]
    mesh = ax.pcolormesh(
        Xc,
        Yc,
        speed.T,
        shading="auto",
        cmap="magma",
    )
    ax.quiver(
        Xc[::stride, ::stride],
        Yc[::stride, ::stride],
        u[::stride, ::stride],
        v[::stride, ::stride],
        angles="xy",
        scale_units="xy",
        scale=max(float(np.max(speed)), 1.0e-30) * 180.0,
        color="white",
        width=0.004,
    )
    ax.set_title("surface face cochain")
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    fig.colorbar(mesh, ax=ax)

    ax = axes[2]
    labels = (
        "self work",
        "probe work",
        "H div",
        "range H",
        "range rec",
        "nonuni adj",
    )
    values = (
        float(results["self_fd_power_residual"]),
        float(results["probe_fd_power_residual"]),
        float(results["hodge_divergence_linf"]),
        float(results["manufactured_range_hodge_l2"]),
        float(results["manufactured_range_recovery_linf"]),
        float(results["nonuniform_adjoint_error"]),
    )
    ax.bar(np.arange(len(labels)), np.log10(np.maximum(values, 1.0e-30)), color="#34656d")
    ax.set_xticks(np.arange(len(labels)), labels, rotation=30, ha="right")
    ax.set_ylabel("log10 magnitude")
    ax.set_title("face work checks")
    ax.grid(axis="y", alpha=0.25)
    ax.text(
        0.03,
        0.97,
        "\n".join(
            (
                f"|s|_M = {float(results['component_weighted_l2']):.8e}",
                f"|range|_M = {float(results['range_weighted_l2']):.8e}",
                f"|H|_M = {float(results['hodge_weighted_l2']):.8e}",
                f"max |H cell| = {float(np.max(hodge_speed)):.8e}",
                "force_admissible = 0",
            )
        ),
        transform=ax.transAxes,
        va="top",
        family="monospace",
        fontsize=8,
    )

    save_figure(fig, OUT / "phase_region_face_cochain_work_oracle")
    return (OUT / "phase_region_face_cochain_work_oracle").with_suffix(".pdf")


class _GridShell:
    def __init__(self, x_edges: np.ndarray, y_edges: np.ndarray):
        self.coords = (x_edges, y_edges)
        self.N = (x_edges.size - 1, y_edges.size - 1)


def _grid_shell_from_edges(x_edges: np.ndarray, y_edges: np.ndarray) -> _GridShell:
    return _GridShell(np.asarray(x_edges, dtype=float), np.asarray(y_edges, dtype=float))


def _print_summary(results: dict[str, object], figure_path: pathlib.Path) -> None:
    print("metric,value")
    for key in (
        "self_fd_gradient_residual",
        "self_fd_power_residual",
        "self_riesz_residual",
        "self_finite_difference",
        "self_capillary_power",
        "probe_fd_gradient_residual",
        "probe_fd_power_residual",
        "probe_riesz_residual",
        "probe_finite_difference",
        "probe_capillary_power",
        "component_weighted_l2",
        "range_weighted_l2",
        "hodge_weighted_l2",
        "hodge_divergence_linf",
        "manufactured_range_hodge_l2",
        "manufactured_range_recovery_linf",
        "nonuniform_adjoint_error",
        "force_admissible",
    ):
        print(key, f"{float(results[key]):.12e}", sep=",")
    print(f"figure,{figure_path}")
    print(f"==> phase-region face-cochain work oracle PASS; outputs in {OUT}")


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument("--n", type=int, default=16)
    parser.add_argument("--axis-a", type=float, default=0.275)
    parser.add_argument("--axis-b", type=float, default=0.225)
    parser.add_argument("--sigma", type=float, default=0.072)
    parser.add_argument("--fd-eps", type=float, default=1.0e-7)
    parser.add_argument("--riesz-tolerance", type=float, default=1.0e-12)
    parser.add_argument("--fd-power-tolerance", type=float, default=1.0e-5)
    parser.add_argument("--divergence-tolerance", type=float, default=1.0e-8)
    parser.add_argument("--range-tolerance", type=float, default=1.0e-10)
    parser.add_argument("--nonuniform-adjoint-tolerance", type=float, default=1.0e-12)
    args = parser.parse_args()

    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = _compute(args)
        save_results(NPZ, results)
    figure_path = _plot(results)
    _print_summary(results, figure_path)


if __name__ == "__main__":
    main()
