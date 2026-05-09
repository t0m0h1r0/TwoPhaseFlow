#!/usr/bin/env python3
"""[U10] Common-flux ledger gate for conservative phase/momentum transport.

Paper ref: Chapter 12 U10 (planned; common-flux component gate).

Goal
----
Verify the component contract introduced by the conservative common-flux
route: the CLS phase fraction q, affine density rho(q), and momentum rho u
must consume the same FCCD transport ledger.  The gate records closed
common-flux candidates separately from negative controls; q-only clipping or
non-affine density is rejected rather than treated as an admissible route.

Setup
-----
  Domain [0,1]^2, periodic BC.
  q = smooth bounded CLS phase field.
  rho(q) = rho_g + (rho_l - rho_g) q.
  Transport = FCCD flux form + TVD-RK3 with returned stage ledger.
  Closed candidate = ConservativeCommonFluxTransport.advance(...).
  Negative controls = non-affine density and q-only projected ledger.

Usage
-----
  python experiment/ch12/exp_U10_common_flux_ledger.py
  python experiment/ch12/exp_U10_common_flux_ledger.py --plot-only
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from twophase.backend import Backend
from twophase.ccd.fccd import FCCDSolver
from twophase.config import GridConfig
from twophase.core.grid import Grid
from twophase.levelset.fccd_advection import FCCDLevelSetAdvection
from twophase.simulation.conservative_transport import ConservativeCommonFluxTransport
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
    / "ch12_u10_common_flux_ledger"
)

GRID_SIZES = (32, 64, 128)
DENSITY_RATIOS = (1.0, 10.0, 100.0, 833.3333333333334)
CFL_VALUES = (0.10, 0.30, 0.60)
TOL_CONSERVATION = 1.0e-9
TOL_AFFINE = 1.0e-9
TOL_ENERGY = 1.0e-9


def _periodic_case(n: int):
    backend = Backend(use_gpu=False)
    xp = backend.xp
    grid = Grid(GridConfig(ndim=2, N=(n, n), L=(1.0, 1.0)), backend)
    fccd = FCCDSolver(grid, backend, bc_type="periodic")
    advection = FCCDLevelSetAdvection(
        backend,
        grid,
        fccd,
        mode="flux",
        mass_correction=False,
    )
    x, y = grid.meshgrid()
    psi = (
        0.50
        + 0.10 * xp.sin(2.0 * xp.pi * x + 0.25) * xp.cos(2.0 * xp.pi * y - 0.15)
        + 0.04 * xp.cos(4.0 * xp.pi * x - 0.30) * xp.sin(2.0 * xp.pi * y + 0.20)
    )
    return backend, grid, fccd, advection, psi


def _face_velocity(backend, grid, cfl: float):
    xp = backend.xp
    n_x, n_y = grid.N
    h_min = min(float(np.min(np.asarray(grid.h[0]))), float(np.min(np.asarray(grid.h[1]))))
    dt = float(cfl) * h_min
    face_u = xp.full((n_x, n_y + 1), 1.0)
    face_v = xp.full((n_x + 1, n_y), -0.35)
    return [face_u, face_v], dt


def _integral(backend, grid, value) -> float:
    xp = backend.xp
    total = xp.sum(xp.asarray(value) * xp.asarray(grid.cell_volumes()))
    return _scalar(backend, total)


def _scalar(backend, value) -> float:
    value = backend.to_host(value) if hasattr(backend, "to_host") else value
    arr = np.asarray(value)
    return float(arr.item() if arr.shape == () else arr)


def _closed_row(n: int, ratio: float, cfl: float) -> dict:
    backend, grid, fccd, advection, psi = _periodic_case(n)
    xp = backend.xp
    face_velocity, dt = _face_velocity(backend, grid, cfl)
    psi_after, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        clip_bounds=None,
        bound_preserving=True,
        return_ledger=True,
    )
    rho_l = float(ratio)
    rho_g = 1.0
    density0 = rho_g + (rho_l - rho_g) * ledger.psi_before
    velocity = (0.25, -0.10)
    momentum0 = tuple(density0 * component for component in velocity)
    transport = ConservativeCommonFluxTransport(backend, grid, fccd)
    result = transport.advance(
        density0,
        momentum0,
        ledger,
        rho_l=rho_l,
        rho_g=rho_g,
    )

    expected_density = rho_g + (rho_l - rho_g) * psi_after
    affine_error = _scalar(backend, xp.max(xp.abs(result.density - expected_density)))
    energy0 = _scalar(backend, result.kinetic_energy_before)
    energy1 = _scalar(backend, result.kinetic_energy_after)
    mass_delta = _integral(backend, grid, result.density) - _integral(backend, grid, density0)
    momentum_delta = [
        _integral(backend, grid, result.momentum_components[axis])
        - _integral(backend, grid, momentum0[axis])
        for axis in range(2)
    ]
    return {
        "candidate": "common_fccd_ledger_uniform_velocity",
        "n": int(n),
        "density_ratio": float(ratio),
        "cfl": float(cfl),
        "energy0": energy0,
        "energy1": energy1,
        "energy_delta": energy1 - energy0,
        "relative_energy_delta": (energy1 - energy0) / max(abs(energy0), 1.0e-300),
        "mass_delta": mass_delta,
        "momentum_x_delta": momentum_delta[0],
        "momentum_y_delta": momentum_delta[1],
        "affine_density_error": affine_error,
        "min_density": _scalar(backend, xp.min(result.density)),
        "max_density": _scalar(backend, xp.max(result.density)),
        "certificate_status": result.certificate_status,
    }


def _negative_rows() -> list[dict]:
    n = 32
    ratio = 10.0
    cfl = 0.30
    backend, grid, fccd, advection, psi = _periodic_case(n)
    face_velocity, dt = _face_velocity(backend, grid, cfl)
    rho_l = float(ratio)
    rho_g = 1.0
    transport = ConservativeCommonFluxTransport(backend, grid, fccd)

    rows: list[dict] = []
    _psi_after, ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        clip_bounds=None,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * ledger.psi_before
    density_bad = density.copy()
    density_bad[0, 0] += 0.25
    momentum_bad = (density_bad * 0.20, density_bad * -0.05)
    rows.append(
        _expect_reject(
            "non_affine_density_control",
            transport,
            density_bad,
            momentum_bad,
            ledger,
            rho_l,
            rho_g,
            n,
            cfl,
        )
    )

    _psi_projected, projected_ledger = advection.advance_with_face_velocity(
        psi.copy(),
        face_velocity,
        dt,
        return_ledger=True,
    )
    density = rho_g + (rho_l - rho_g) * projected_ledger.psi_before
    momentum = (density * 0.20, density * -0.05)
    rows.append(
        _expect_reject(
            "q_only_projected_ledger_control",
            transport,
            density,
            momentum,
            projected_ledger,
            rho_l,
            rho_g,
            n,
            cfl,
        )
    )
    return rows


def _expect_reject(
    candidate: str,
    transport: ConservativeCommonFluxTransport,
    density,
    momentum,
    ledger,
    rho_l: float,
    rho_g: float,
    n: int,
    cfl: float,
) -> dict:
    try:
        transport.advance(density, momentum, ledger, rho_l=rho_l, rho_g=rho_g)
    except ValueError as exc:
        return {
            "candidate": candidate,
            "n": int(n),
            "density_ratio": float(rho_l / rho_g),
            "cfl": float(cfl),
            "rejected": 1,
            "message": str(exc),
        }
    return {
        "candidate": candidate,
        "n": int(n),
        "density_ratio": float(rho_l / rho_g),
        "cfl": float(cfl),
        "rejected": 0,
        "message": "unexpectedly accepted",
    }


def _open_control_rows() -> list[dict]:
    rows: list[dict] = []
    for ratio in DENSITY_RATIOS:
        backend, grid, _fccd, advection, psi = _periodic_case(64)
        xp = backend.xp
        face_velocity, dt = _face_velocity(backend, grid, 0.60)
        psi_after, ledger = advection.advance_with_face_velocity(
            psi.copy(),
            face_velocity,
            dt,
            clip_bounds=None,
            bound_preserving=True,
            return_ledger=True,
        )
        rho_l = float(ratio)
        rho_g = 1.0
        density0 = rho_g + (rho_l - rho_g) * ledger.psi_before
        density1 = rho_g + (rho_l - rho_g) * psi_after
        x, y = grid.meshgrid()
        u0 = 0.30 + 0.20 * xp.sin(2.0 * xp.pi * x) * xp.cos(2.0 * xp.pi * y)
        v0 = -0.12 + 0.15 * xp.cos(2.0 * xp.pi * x) * xp.sin(2.0 * xp.pi * y)
        momentum0 = (density0 * u0, density0 * v0)
        candidates = {
            "density_moved_velocity_current": (density1 * u0, density1 * v0),
            "momentum_moved_density_current": (
                _simple_upwind(momentum0[0], 0.60),
                _simple_upwind(momentum0[1], 0.60),
            ),
        }
        energy0 = _kinetic_energy(backend, grid, density0, momentum0)
        for candidate, momentum1 in candidates.items():
            energy1 = _kinetic_energy(backend, grid, density1, momentum1)
            rows.append(
                {
                    "candidate": candidate,
                    "n": 64,
                    "density_ratio": float(ratio),
                    "cfl": 0.60,
                    "energy0": energy0,
                    "energy1": energy1,
                    "relative_energy_delta": (energy1 - energy0)
                    / max(abs(energy0), 1.0e-300),
                    "mass_delta": _integral(backend, grid, density1)
                    - _integral(backend, grid, density0),
                    "momentum_x_delta": _integral(backend, grid, momentum1[0])
                    - _integral(backend, grid, momentum0[0]),
                    "momentum_y_delta": _integral(backend, grid, momentum1[1])
                    - _integral(backend, grid, momentum0[1]),
                    "theorem_status": "open_control",
                }
            )
    return rows


def _simple_upwind(q, cfl: float):
    return (1.0 - float(cfl)) * q + float(cfl) * np.roll(q, 1, axis=0)


def _kinetic_energy(backend, grid, density, momentum_components) -> float:
    xp = backend.xp
    momentum_sq = xp.zeros_like(density)
    for component in momentum_components:
        momentum_sq = momentum_sq + xp.asarray(component) * xp.asarray(component)
    return _integral(backend, grid, 0.5 * momentum_sq / density)


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
    closed_rows = [
        _closed_row(n, ratio, cfl)
        for n in GRID_SIZES
        for ratio in DENSITY_RATIOS
        for cfl in CFL_VALUES
    ]
    negative_rows = _negative_rows()
    open_rows = _open_control_rows()
    results = {
        "closed": _columns(closed_rows),
        "negative": _columns(negative_rows),
        "open_controls": _columns(open_rows),
    }
    _assert_acceptance(results)
    return results


def _assert_acceptance(results: dict) -> None:
    closed = results["closed"]
    energy_delta = np.asarray(closed["energy_delta"], dtype=float)
    mass_delta = np.asarray(closed["mass_delta"], dtype=float)
    momentum_x_delta = np.asarray(closed["momentum_x_delta"], dtype=float)
    momentum_y_delta = np.asarray(closed["momentum_y_delta"], dtype=float)
    affine_error = np.asarray(closed["affine_density_error"], dtype=float)
    if np.max(energy_delta) > TOL_ENERGY:
        raise AssertionError("U10 closed common-flux candidate increased kinetic energy")
    if np.max(np.abs(mass_delta)) > TOL_CONSERVATION:
        raise AssertionError("U10 closed common-flux candidate is not mass conservative")
    if np.max(np.abs(momentum_x_delta)) > TOL_CONSERVATION:
        raise AssertionError("U10 closed common-flux candidate loses x momentum")
    if np.max(np.abs(momentum_y_delta)) > TOL_CONSERVATION:
        raise AssertionError("U10 closed common-flux candidate loses y momentum")
    if np.max(affine_error) > TOL_AFFINE:
        raise AssertionError("U10 density is not the affine image of q")
    if not np.all(np.asarray(results["negative"]["rejected"], dtype=int) == 1):
        raise AssertionError("U10 negative controls were not fail-closed")


def make_figures(results: dict) -> None:
    closed = _rows(results["closed"])
    open_rows = _rows(results["open_controls"])
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    ax_closed, ax_open = axes
    for ratio in DENSITY_RATIOS:
        subset = [row for row in closed if abs(float(row["density_ratio"]) - ratio) < 1.0e-12 and int(row["n"]) == 64]
        subset.sort(key=lambda row: float(row["cfl"]))
        ax_closed.plot(
            [float(row["cfl"]) for row in subset],
            [float(row["relative_energy_delta"]) for row in subset],
            marker="o",
            label=f"rho_l/rho_g={ratio:g}",
        )
    ax_closed.axhline(0.0, color="0.25", lw=0.8)
    ax_closed.set_xlabel("CFL")
    ax_closed.set_ylabel("(K1 - K0) / K0")
    ax_closed.set_title("closed common-flux candidate")
    ax_closed.set_yscale("symlog", linthresh=1.0e-15)
    ax_closed.legend(fontsize=7)

    labels = sorted({str(row["candidate"]) for row in open_rows})
    x_pos = np.arange(len(labels))
    values = [
        max(float(row["relative_energy_delta"]) for row in open_rows if row["candidate"] == label)
        for label in labels
    ]
    ax_open.bar(x_pos, values, color="0.35")
    ax_open.axhline(0.0, color="0.25", lw=0.8)
    ax_open.set_xticks(x_pos, labels, rotation=25, ha="right")
    ax_open.set_ylabel("max (K1 - K0) / K0")
    ax_open.set_title("open controls are diagnostics")
    fig.suptitle("U10 common-flux ledger gate")
    save_figure(fig, OUT / "U10_common_flux_ledger", also_to=PAPER_FIG)


def print_summary(results: dict) -> None:
    closed = results["closed"]
    negative = results["negative"]
    print("U10 closed max relative energy delta:",
          f"{np.max(np.asarray(closed['relative_energy_delta'], dtype=float)):.3e}")
    print("U10 closed max |mass delta|:",
          f"{np.max(np.abs(np.asarray(closed['mass_delta'], dtype=float))):.3e}")
    print("U10 closed max |momentum delta|:",
          f"{max(np.max(np.abs(np.asarray(closed['momentum_x_delta'], dtype=float))), np.max(np.abs(np.asarray(closed['momentum_y_delta'], dtype=float)))):.3e}")
    print("U10 closed max affine density error:",
          f"{np.max(np.asarray(closed['affine_density_error'], dtype=float)):.3e}")
    print("U10 negative controls rejected:",
          f"{int(np.sum(np.asarray(negative['rejected'], dtype=int)))} / {len(negative['rejected'])}")


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
    print(f"==> U10 outputs in {OUT}")


if __name__ == "__main__":
    main()
