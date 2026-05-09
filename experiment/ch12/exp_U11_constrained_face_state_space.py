#!/usr/bin/env python3
"""[U11] Constrained face-state space gate for wall and periodic-wall PPE.

Paper ref: Chapter 12 U11 (constrained face-state component gate).

Goal
----
Verify the algebraic state-space contract introduced by the Chapter 9
boundary-Hodge theory:

  F_w = ker(B_w R_h),        G_w = P_w G_A,
  D_w G_w has the same range as D_w on the constrained face space.

The experiment is intentionally manufactured and small.  It certifies the
projection, Green identity, and rank topology before any production restricted
PPE solve is allowed to rely on the constrained face space.

Setup
-----
  Grid: small nonuniform-free tensor grids on [0,1] x [0,1.2].
  BCs: full wall and x-periodic/y-wall.
  Positive gates:
    * wall trace removed by P_w;
    * P_w idempotent and metric self-adjoint;
    * restricted pressure force satisfies the discrete Green identity;
    * restricted pressure rank equals restricted divergence rank.
  Negative controls:
    * boundary-only/no-slip post clamp does not equal P_w;
    * full periodic endpoint topology is not accepted as the quotient space.

Usage
-----
  python experiment/ch12/exp_U11_constrained_face_state_space.py
  python experiment/ch12/exp_U11_constrained_face_state_space.py --plot-only
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from twophase.backend import Backend
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig, SimulationConfig
from twophase.core.boundary import sync_periodic_image_nodes
from twophase.core.grid import Grid
from twophase.simulation.boundary_hodge import (
    face_mass_inner_product,
    periodic_unique_node_mask,
    project_wall_trace,
    restricted_pressure_fluxes,
    sync_periodic_face_images,
    wall_trace_from_faces,
)
from twophase.simulation.divergence_ops import FCCDDivergenceOperator
from twophase.tools.experiment import (
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
PAPER_FIG = (
    pathlib.Path(__file__).resolve().parents[2]
    / "paper"
    / "figures"
    / "ch12_u11_constrained_face_state_space"
)

TRACE_TOL = 1.0e-10
IDENTITY_TOL = 1.0e-10
GREEN_TOL = 1.0e-10
RANK_TOL = 1.0e-10
NEGATIVE_TRACE_TOL = 1.0e-8


def _grid(nx: int = 7, ny: int = 6, *, bc_type: str = "wall"):
    backend = Backend(use_gpu=False)
    cfg = SimulationConfig(grid=GridConfig(ndim=2, N=(nx, ny), L=(1.0, 1.2)))
    grid = Grid(cfg.grid, backend)
    return backend, grid, FCCDSolver(grid, backend, bc_type=bc_type)


def _rho(grid: Grid) -> np.ndarray:
    x = np.asarray(grid.coords[0])[:, None]
    y = np.asarray(grid.coords[1])[None, :]
    return 2.0 + 0.1 * np.sin(2.0 * np.pi * x) * np.cos(np.pi * y / grid.L[1])


def _random_faces(rng: np.random.Generator, grid: Grid) -> list[np.ndarray]:
    faces = []
    for axis in range(grid.ndim):
        shape = list(grid.shape)
        shape[axis] = grid.N[axis]
        faces.append(rng.normal(size=tuple(shape)))
    return faces


def _vec(faces: list[np.ndarray]) -> np.ndarray:
    return np.concatenate([np.asarray(face).ravel() for face in faces])


def _unvec(values: np.ndarray, grid: Grid) -> list[np.ndarray]:
    faces = []
    offset = 0
    for axis in range(grid.ndim):
        shape = list(grid.shape)
        shape[axis] = grid.N[axis]
        size = int(np.prod(shape))
        faces.append(values[offset : offset + size].reshape(tuple(shape)))
        offset += size
    return faces


def _assemble_face_matrix(grid: Grid, apply_column) -> np.ndarray:
    face_size = sum(
        int(
            np.prod(
                tuple(
                    grid.N[axis] if i == axis else grid.shape[i]
                    for i in range(grid.ndim)
                )
            )
        )
        for axis in range(grid.ndim)
    )
    columns = []
    for index in range(face_size):
        basis = np.zeros(face_size)
        basis[index] = 1.0
        columns.append(apply_column(_unvec(basis, grid)))
    return np.column_stack(columns)


def _node_widths(grid: Grid) -> list[np.ndarray]:
    widths = []
    for axis in range(grid.ndim):
        coords = np.asarray(grid.coords[axis], dtype=float)
        d_face = coords[1:] - coords[:-1]
        width = np.empty_like(coords)
        width[0] = 0.5 * d_face[0]
        width[-1] = 0.5 * d_face[-1]
        width[1:-1] = 0.5 * (coords[2:] - coords[:-2])
        widths.append(width)
    return widths


def _nodal_volume(grid: Grid) -> np.ndarray:
    wx, wy = _node_widths(grid)
    return wx[:, None] * wy[None, :]


def _pressure_inner(grid: Grid, pressure: np.ndarray, divergence: np.ndarray) -> float:
    return float(np.vdot(pressure, _nodal_volume(grid) * divergence).real)


def _periodic_quotient_pressure_inner(
    grid: Grid,
    pressure: np.ndarray,
    divergence: np.ndarray,
    bc_type: str,
) -> float:
    weighted = _nodal_volume(grid) * divergence
    if bc_type == "periodic_wall":
        weighted = weighted.copy()
        weighted[0, :] += weighted[-1, :]
    mask = np.asarray(periodic_unique_node_mask(np, grid, bc_type), dtype=bool)
    return float(np.vdot(pressure[mask], weighted[mask]).real)


def _pressure_kwargs() -> dict[str, str]:
    return {
        "pressure_gradient": "fccd",
        "pressure_force_contract": "variational_adjoint",
        "coefficient_scheme": "phase_density",
        "interface_coupling_scheme": "none",
    }


def _post_clamp_control(faces: list[np.ndarray], grid: Grid, bc_type: str) -> list[np.ndarray]:
    """Boundary-only clamp surrogate; it must not pass as constrained P_w."""
    clamped = [np.array(face, copy=True) for face in faces]
    if bc_type == "wall":
        clamped[0][0, :] = 0.0
        clamped[0][-1, :] = 0.0
    clamped[1][:, 0] = 0.0
    clamped[1][:, -1] = 0.0
    if bc_type == "periodic_wall":
        clamped = sync_periodic_face_images(np, grid, clamped, bc_type)
    return clamped


def _case_metrics(bc_type: str, seed: int) -> dict:
    backend, grid, fccd = _grid(bc_type=bc_type)
    div_op = FCCDDivergenceOperator(fccd)
    rng = np.random.default_rng(seed)
    rho = _rho(grid)
    faces_a = _random_faces(rng, grid)
    faces_b = _random_faces(rng, grid)
    if bc_type == "periodic_wall":
        faces_a = sync_periodic_face_images(backend.xp, grid, faces_a, bc_type)
        faces_b = sync_periodic_face_images(backend.xp, grid, faces_b, bc_type)

    projection_a = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=faces_a,
        rho=rho,
        bc_type=bc_type,
        tolerance=1.0e-12,
        max_iterations=220,
    )
    projection_aa = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=projection_a.face_components,
        rho=rho,
        bc_type=bc_type,
        tolerance=1.0e-12,
        max_iterations=220,
    )
    projection_b = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=faces_b,
        rho=rho,
        bc_type=bc_type,
        tolerance=1.0e-12,
        max_iterations=220,
    )

    raw_trace = wall_trace_from_faces(backend.xp, grid, faces_a, bc_type)
    projected_trace = wall_trace_from_faces(
        backend.xp,
        grid,
        projection_a.face_components,
        bc_type,
    )
    clamped = _post_clamp_control(faces_a, grid, bc_type)
    clamped_trace = wall_trace_from_faces(backend.xp, grid, clamped, bc_type)
    idempotence_abs = np.linalg.norm(
        _vec(projection_aa.face_components) - _vec(projection_a.face_components)
    )
    self_left = face_mass_inner_product(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        rho=rho,
        left_components=projection_a.face_components,
        right_components=faces_b,
    )
    self_right = face_mass_inner_product(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        rho=rho,
        left_components=faces_a,
        right_components=projection_b.face_components,
    )
    self_scale = abs(float(self_left)) + abs(float(self_right)) + 1.0e-300
    self_adjoint_rel = abs(float(self_left) - float(self_right)) / self_scale

    pressure_rho = np.ones(grid.shape)
    pressure = rng.normal(size=grid.shape)
    if bc_type == "periodic_wall":
        sync_periodic_image_nodes(pressure, bc_type)
    eta = project_wall_trace(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        face_components=_random_faces(rng, grid),
        rho=pressure_rho,
        bc_type=bc_type,
        tolerance=1.0e-12,
        max_iterations=240,
    ).face_components
    raw_pressure_faces = div_op.pressure_fluxes(pressure, pressure_rho, **_pressure_kwargs())
    restricted = restricted_pressure_fluxes(
        xp=backend.xp,
        grid=grid,
        fccd=fccd,
        div_op=div_op,
        pressure=pressure,
        rho=pressure_rho,
        bc_type=bc_type,
        pressure_flux_kwargs=_pressure_kwargs(),
        tolerance=1.0e-12,
        max_iterations=240,
    )
    lhs = float(
        face_mass_inner_product(
            xp=backend.xp,
            grid=grid,
            fccd=fccd,
            rho=pressure_rho,
            left_components=restricted.face_components,
            right_components=eta,
        )
    )
    divergence = np.asarray(div_op.divergence_from_faces(eta))
    if bc_type == "periodic_wall":
        rhs = _periodic_quotient_pressure_inner(grid, pressure, divergence, bc_type)
    else:
        rhs = _pressure_inner(grid, pressure, divergence)
    green_rel = abs(lhs + rhs) / (abs(lhs) + abs(rhs) + 1.0e-300)
    endpoint_pressure_gap_linf = 0.0
    endpoint_mode_flux_l2 = 0.0
    if bc_type == "periodic_wall":
        endpoint_mode = np.zeros(grid.shape)
        endpoint_mode[0, :] = 1.0
        endpoint_mode[-1, :] = -1.0
        endpoint_pressure_gap_linf = float(
            np.max(np.abs(endpoint_mode[0, :] - endpoint_mode[-1, :]))
        )
        endpoint_faces = restricted_pressure_fluxes(
            xp=backend.xp,
            grid=grid,
            fccd=fccd,
            div_op=div_op,
            pressure=endpoint_mode,
            rho=pressure_rho,
            bc_type=bc_type,
            pressure_flux_kwargs=_pressure_kwargs(),
            tolerance=1.0e-12,
            max_iterations=240,
        ).face_components
        endpoint_mode_flux_l2 = float(np.linalg.norm(_vec(endpoint_faces)))
    raw_pressure_trace = wall_trace_from_faces(
        backend.xp,
        grid,
        raw_pressure_faces,
        bc_type,
    )
    restricted_pressure_trace = wall_trace_from_faces(
        backend.xp,
        grid,
        restricted.face_components,
        bc_type,
    )

    return {
        "bc_type": bc_type,
        "grid": f"{grid.N[0]}x{grid.N[1]}",
        "raw_trace_linf": float(np.max(np.abs(raw_trace))),
        "projected_trace_linf": float(np.max(np.abs(projected_trace))),
        "idempotence_abs": float(idempotence_abs),
        "self_adjoint_rel": float(self_adjoint_rel),
        "green_rel": float(green_rel),
        "endpoint_pressure_gap_linf": float(endpoint_pressure_gap_linf),
        "endpoint_mode_flux_l2": float(endpoint_mode_flux_l2),
        "raw_pressure_trace_linf": float(np.max(np.abs(raw_pressure_trace))),
        "restricted_pressure_trace_linf": float(np.max(np.abs(restricted_pressure_trace))),
        "projection_cg_converged": float(
            projection_a.diagnostics.get("boundary_hodge_cg_converged", 0.0)
        ),
        "pressure_cg_converged": float(
            restricted.diagnostics.get(
                "constrained_face_space_pressure_cg_converged",
                0.0,
            )
        ),
        "post_clamp_trace_linf": float(np.max(np.abs(clamped_trace))),
        "post_clamp_rejected": int(
            np.max(np.abs(clamped_trace)) > NEGATIVE_TRACE_TOL
        ),
        "full_array_endpoint_rejected": int(
            bc_type != "periodic_wall"
            or endpoint_pressure_gap_linf > NEGATIVE_TRACE_TOL
        ),
    }


def _rank_metrics(bc_type: str) -> dict:
    backend, grid, fccd = _grid(nx=6, ny=5, bc_type=bc_type)
    div_op = FCCDDivergenceOperator(fccd)
    rho = np.ones(grid.shape)

    d_full = _assemble_face_matrix(
        grid,
        lambda faces: np.asarray(div_op.divergence_from_faces(faces)).ravel(),
    )
    d_mat = d_full
    if bc_type == "periodic_wall":
        mask = np.asarray(periodic_unique_node_mask(np, grid, bc_type), dtype=bool)
        d_mat = d_full[mask.ravel(), :]
    p_w = _assemble_face_matrix(
        grid,
        lambda faces: _vec(
            project_wall_trace(
                xp=backend.xp,
                grid=grid,
                fccd=fccd,
                face_components=faces,
                rho=rho,
                bc_type=bc_type,
                tolerance=1.0e-12,
                max_iterations=240,
            ).face_components
        ),
    )
    pressure_columns = []
    for index in range(int(np.prod(grid.shape))):
        pressure = np.zeros(grid.shape)
        pressure.ravel()[index] = 1.0
        pressure_columns.append(
            _vec(div_op.pressure_fluxes(pressure, rho, **_pressure_kwargs()))
        )
    g_mat = np.column_stack(pressure_columns)

    full_div_rank = int(np.linalg.matrix_rank(d_full @ p_w, tol=RANK_TOL))
    full_pressure_rank = int(np.linalg.matrix_rank(d_full @ p_w @ g_mat, tol=RANK_TOL))
    quotient_div_rank = int(np.linalg.matrix_rank(d_mat @ p_w, tol=RANK_TOL))
    quotient_pressure_rank = int(np.linalg.matrix_rank(d_mat @ p_w @ g_mat, tol=RANK_TOL))
    return {
        "bc_type": bc_type,
        "grid": f"{grid.N[0]}x{grid.N[1]}",
        "restricted_divergence_rank": quotient_div_rank,
        "restricted_pressure_rank": quotient_pressure_rank,
        "rank_match": int(quotient_div_rank == quotient_pressure_rank),
        "full_array_divergence_rank": full_div_rank,
        "full_array_pressure_rank": full_pressure_rank,
    }


def _columns(rows: list[dict]) -> dict:
    keys = sorted({key for row in rows for key in row})
    return {key: np.asarray([row.get(key, "") for row in rows]) for key in keys}


def _rows(table: dict) -> list[dict]:
    keys = list(table.keys())
    if not keys:
        return []
    n = len(np.asarray(table[keys[0]]))
    return [{key: np.asarray(table[key])[i].item() for key in keys} for i in range(n)]


def run_all() -> dict:
    cases = [
        _case_metrics("wall", seed=211),
        _case_metrics("periodic_wall", seed=212),
    ]
    ranks = [_rank_metrics("wall"), _rank_metrics("periodic_wall")]
    results = {
        "cases": _columns(cases),
        "ranks": _columns(ranks),
    }
    _assert_acceptance(results)
    return results


def _assert_acceptance(results: dict) -> None:
    cases = results["cases"]
    if np.max(np.asarray(cases["projected_trace_linf"], dtype=float)) > TRACE_TOL:
        raise AssertionError("U11 P_w did not remove the wall trace")
    if np.max(np.asarray(cases["idempotence_abs"], dtype=float)) > IDENTITY_TOL:
        raise AssertionError("U11 P_w is not idempotent")
    if np.max(np.asarray(cases["self_adjoint_rel"], dtype=float)) > IDENTITY_TOL:
        raise AssertionError("U11 P_w is not metric self-adjoint")
    if np.max(np.asarray(cases["green_rel"], dtype=float)) > GREEN_TOL:
        raise AssertionError("U11 restricted pressure Green identity failed")
    if np.max(np.asarray(cases["restricted_pressure_trace_linf"], dtype=float)) > TRACE_TOL:
        raise AssertionError("U11 restricted pressure left the wall space")
    if np.min(np.asarray(cases["raw_trace_linf"], dtype=float)) <= NEGATIVE_TRACE_TOL:
        raise AssertionError("U11 raw wall trace negative control is degenerate")
    if np.min(np.asarray(cases["raw_pressure_trace_linf"], dtype=float)) <= NEGATIVE_TRACE_TOL:
        raise AssertionError("U11 raw pressure trace negative control is degenerate")
    if not np.all(np.asarray(cases["post_clamp_rejected"], dtype=int) == 1):
        raise AssertionError("U11 boundary-only clamp was accepted as P_w")
    periodic_cases = [
        row for row in _rows(cases) if str(row["bc_type"]) == "periodic_wall"
    ]
    if int(periodic_cases[0]["full_array_endpoint_rejected"]) != 1:
        raise AssertionError("U11 full-array periodic endpoints were accepted")
    if not np.all(np.asarray(cases["projection_cg_converged"], dtype=float) == 1.0):
        raise AssertionError("U11 wall projection CG did not converge")
    if not np.all(np.asarray(cases["pressure_cg_converged"], dtype=float) == 1.0):
        raise AssertionError("U11 restricted pressure CG did not converge")

    ranks = results["ranks"]
    if not np.all(np.asarray(ranks["rank_match"], dtype=int) == 1):
        raise AssertionError("U11 restricted pressure rank does not match divergence rank")


def make_figures(results: dict) -> None:
    cases = _rows(results["cases"])
    ranks = _rows(results["ranks"])
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2))
    ax_res, ax_rank = axes

    metrics = [
        ("projected_trace_linf", r"$\|B_w R_h P_w f\|_\infty$"),
        ("idempotence_abs", r"$\|P_w^2 f-P_w f\|_2$"),
        ("self_adjoint_rel", "metric adjoint rel."),
        ("green_rel", "Green rel."),
        ("restricted_pressure_trace_linf", "restricted pressure trace"),
    ]
    x = np.arange(len(metrics))
    width = 0.36
    for offset, row in zip((-0.5 * width, 0.5 * width), cases):
        values = [max(float(row[key]), 1.0e-16) for key, _label in metrics]
        ax_res.bar(x + offset, values, width=width, label=str(row["bc_type"]))
    ax_res.axhline(TRACE_TOL, color="0.15", lw=0.8, ls="--", label="gate")
    ax_res.set_yscale("log")
    ax_res.set_xticks(x, [label for _key, label in metrics], rotation=25, ha="right")
    ax_res.set_ylabel("residual")
    ax_res.set_title("constrained face-state identities")
    ax_res.legend(fontsize=7)

    rank_labels = [str(row["bc_type"]) for row in ranks]
    rank_x = np.arange(len(rank_labels))
    ax_rank.bar(
        rank_x - 0.18,
        [int(row["restricted_divergence_rank"]) for row in ranks],
        width=0.36,
        label=r"rank $D_w P_w$",
    )
    ax_rank.bar(
        rank_x + 0.18,
        [int(row["restricted_pressure_rank"]) for row in ranks],
        width=0.36,
        label=r"rank $D_w P_w G_A$",
    )
    for idx, row in enumerate(ranks):
        ax_rank.text(
            idx,
            max(int(row["restricted_divergence_rank"]), int(row["restricted_pressure_rank"]))
            + 0.45,
            f"full {int(row['full_array_divergence_rank'])}/"
            f"{int(row['full_array_pressure_rank'])}",
            ha="center",
            va="bottom",
            fontsize=7,
        )
    ax_rank.set_xticks(rank_x, rank_labels, rotation=15, ha="right")
    ax_rank.set_ylabel("matrix rank")
    ax_rank.set_title("restricted pressure rank gate")
    ax_rank.legend(fontsize=7)

    fig.suptitle("U11 constrained face-state space gate")
    fig.tight_layout()
    save_figure(fig, OUT / "U11_constrained_face_state_space", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    cases = results["cases"]
    ranks = _rows(results["ranks"])
    print(
        "U11 max projected wall trace:",
        f"{np.max(np.asarray(cases['projected_trace_linf'], dtype=float)):.3e}",
    )
    print(
        "U11 max idempotence error:",
        f"{np.max(np.asarray(cases['idempotence_abs'], dtype=float)):.3e}",
    )
    print(
        "U11 max metric self-adjoint relative error:",
        f"{np.max(np.asarray(cases['self_adjoint_rel'], dtype=float)):.3e}",
    )
    print(
        "U11 max Green relative residual:",
        f"{np.max(np.asarray(cases['green_rel'], dtype=float)):.3e}",
    )
    for row in ranks:
        print(
            "U11 rank gate",
            row["bc_type"],
            f"D={int(row['restricted_divergence_rank'])}",
            f"DPG={int(row['restricted_pressure_rank'])}",
            f"full={int(row['full_array_divergence_rank'])}/"
            f"{int(row['full_array_pressure_rank'])}",
        )


def main() -> None:
    args = experiment_argparser(__doc__).parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = run_all()
        save_results(NPZ, results)
    _assert_acceptance(results)
    make_figures(results)
    print_summary(results)
    print(f"==> U11 outputs in {OUT}")


if __name__ == "__main__":
    main()
