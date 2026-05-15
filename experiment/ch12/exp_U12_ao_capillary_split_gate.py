#!/usr/bin/env python3
"""[U12] Active-geometry capillary split gate.

Paper ref: Chapter 12 U12.

This component gate formalizes the active-geometry capillary split diagnostic
used by the paper. It does not advance Navier--Stokes. It compares the CPU
exact full pressure-image split, the CPU component-volume Hodge residual probe,
the current GPU split-pending boundary, and the production graph-HFE contracts
that protect the Chapter 14 capillary route.

Usage
-----
  python experiment/ch12/exp_U12_ao_capillary_split_gate.py
  python experiment/ch12/exp_U12_ao_capillary_split_gate.py --require-gpu
  python experiment/ch12/exp_U12_ao_capillary_split_gate.py --plot-only
"""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

import matplotlib.pyplot as plt
import numpy as np

from experiment.ch14.diagnose_ao_algebraic_split import (  # noqa: E402
    _cpu_component_hodge,
    _cpu_exact,
    _gpu_packet,
)
from twophase.backend import Backend  # noqa: E402
from twophase.config import GridConfig  # noqa: E402
from twophase.core.grid import Grid  # noqa: E402
from twophase.simulation.geometric_phase_runtime import (  # noqa: E402
    GeometricRuntimeCapillaryApplicationState,
    validate_geometric_runtime_capillary_application_admitted,
)
from twophase.simulation.ns_step_services import (  # noqa: E402
    _pressure_coordinate_history_base,
)
from twophase.simulation.ns_step_state import NSStepState  # noqa: E402
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_figure,
    save_results,
)

apply_style()
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = ROOT / "paper" / "figures" / "ch12_u12_ao_capillary_split_gate"

BOUNDARY = ("periodic", "wall")
TOL_ZERO = 1.0e-10
TOL_WAVE = 1.0e-2
TOL_GRAPH_MEAN = 1.0e-12


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    mode: str
    nx: int
    ny: int
    amplitude: float
    pressure_history: str = "pressure_coordinate"


U12_CASES = (
    CaseSpec("flat_n32", "flat", 32, 32, 0.0),
    CaseSpec("wave_n32", "capillary_wave", 32, 32, 2.0e-4),
    CaseSpec("wave_n64", "capillary_wave", 64, 64, 2.0e-4),
)

PATHS = {
    "cpu_exact": _cpu_exact,
    "cpu_component_hodge": _cpu_component_hodge,
    "gpu_packet": _gpu_packet,
}

NUMERIC_FIELDS = (
    "compat_linf",
    "force_l2",
    "reaction_l2",
    "balanced_l2",
    "balanced_max",
    "yl_residual_l2",
    "yl_normal_linf",
    "residual_accel_l2",
    "residual_face_max",
)


def _probe_args(spec: CaseSpec) -> SimpleNamespace:
    return SimpleNamespace(
        mode=spec.mode,
        nx=spec.nx,
        ny=spec.ny,
        lx=0.02,
        ly=0.02,
        amplitude=spec.amplitude,
        center_fraction=0.47,
        wave_number=2,
        sigma=0.0728,
        rho_l=998.2,
        rho_g=1.204,
        dt=1.0e-5,
        tolerance=1.0e-11,
        pressure_history=spec.pressure_history,
        boundary_x=BOUNDARY[0],
        boundary_y=BOUNDARY[1],
    )


def _normalise_row(spec: CaseSpec, path: str, raw: dict) -> dict:
    row = {
        "case_id": spec.case_id,
        "mode": spec.mode,
        "nx": spec.nx,
        "ny": spec.ny,
        "amplitude": spec.amplitude,
        "pressure_history": spec.pressure_history,
        "path": path,
        "status": str(raw.get("status", "")),
        "fail_close": str(raw.get("fail_close", "")),
        "range_status": str(raw.get("range_status", "")),
        "exact_static": int(bool(raw.get("exact_static", False))),
        "drive_present": int(bool(raw.get("drive_present", False))),
    }
    for field in NUMERIC_FIELDS:
        value = raw.get(field, np.nan)
        try:
            row[field] = float(value)
        except (TypeError, ValueError):
            row[field] = np.nan
    return row


def _columns(rows: list[dict]) -> dict[str, np.ndarray]:
    keys = sorted({key for row in rows for key in row})
    return {key: np.asarray([row.get(key, "") for row in rows]) for key in keys}


def _component_row(metric: str, value: float, criterion: str, passed: bool) -> dict:
    return {
        "metric": metric,
        "value": float(value),
        "criterion": criterion,
        "passed": int(bool(passed)),
    }


def _graph_hfe_jump_contract_rows() -> list[dict]:
    """Check the q-owned graph HFE jump formula on a nonuniform x grid."""
    n = 32
    lx = 0.02
    ly = 0.02
    sigma = 0.0728
    amplitude = 2.0e-4
    wave_number = 2
    xi = np.linspace(0.0, 1.0, n + 1)
    x_edges = lx * xi**1.35
    x_edges[-1] = lx
    dx = np.diff(x_edges)
    x_centers = 0.5 * (x_edges[:-1] + x_edges[1:])
    height = (
        0.47 * ly
        + amplitude * np.cos(2.0 * np.pi * wave_number * x_centers / lx)
    )
    segment_dx = 0.5 * (dx + np.roll(dx, -1))
    dh = np.roll(height, -1) - height
    segment_length = np.sqrt(segment_dx * segment_dx + dh * dh)
    slope_right = dh / segment_length
    slope_left = np.roll(slope_right, 1)
    height_gradient = sigma * (slope_left - slope_right)
    pressure_jump = -height_gradient / dx
    jump_linf = float(np.max(np.abs(pressure_jump)))
    dx_weighted_mean = float(abs(np.sum(pressure_jump * dx) / np.sum(dx)))
    crest_jump = float(pressure_jump[int(np.argmax(height))])
    return [
        _component_row("graph_hfe_jump_linf", jump_linf, "> 0", jump_linf > 0.0),
        _component_row(
            "graph_hfe_jump_dx_mean",
            dx_weighted_mean,
            f"<= {TOL_GRAPH_MEAN:.0e}",
            dx_weighted_mean <= TOL_GRAPH_MEAN,
        ),
        _component_row("graph_hfe_crest_sign", crest_jump, "< 0", crest_jump < 0.0),
    ]


def _pressure_history_contract_rows() -> list[dict]:
    """Graph HFE jumps are current affine PPE data, never smooth history."""
    previous = np.asarray([[1.0, 2.0], [4.0, 8.0]])
    state = NSStepState(
        psi=np.ones_like(previous),
        u=np.zeros_like(previous),
        v=np.zeros_like(previous),
        dt=1.0e-3,
        rho_l=1.0,
        rho_g=1.0,
        sigma=1.0,
        mu=0.0,
        g_acc=0.0,
        rho_ref=1.0,
        mu_l=None,
        mu_g=None,
        bc_hook=None,
        step_index=0,
        previous_base_pressure=previous,
        previous_previous_base_pressure=0.5 * previous,
        geometric_runtime_capillary_application=SimpleNamespace(
            capillary=SimpleNamespace(
                pressure_jump_status="column_height_graph_hfe",
                pressure_jump_gas_minus_liquid=np.full_like(previous, 3.0),
                pressure_jump_psi=np.zeros_like(previous),
                pressure_jump_phase_threshold=0.0,
            ),
        ),
    )
    history = _pressure_coordinate_history_base(
        xp=np,
        state=state,
        ppe_runtime=SimpleNamespace(pressure_history_extrapolation="bdf2"),
    )
    return [
        _component_row(
            "pressure_history_no_jump_reuse",
            1.0 if history is None else 0.0,
            "is None",
            history is None,
        )
    ]


def _hfe_admission_contract_rows() -> list[dict]:
    """HFE admission is governed by spatial capillary drive, not dt scaling."""
    capillary = SimpleNamespace(
        pressure_range_tolerance=1.0e-11,
        capillary_force_weighted_acceleration_l2=1.0e-6,
        max_abs_capillary_force_face_covector=1.0e-6,
    )
    zero = (np.zeros((2, 3)), np.zeros((3, 2)))
    application = GeometricRuntimeCapillaryApplicationState(
        capillary=capillary,
        dt=1.0e-8,
        predictor_face_acceleration=zero,
        pressure_reaction_face_acceleration=zero,
        predictor_face_increment=zero,
        pressure_reaction_face_increment=zero,
        pressure_balanced_face_increment=zero,
        predictor_increment_weighted_l2=1.0e-14,
        pressure_reaction_increment_weighted_l2=0.0,
        pressure_balanced_increment_weighted_l2=1.0e-14,
        max_abs_pressure_balanced_face_increment=1.0e-14,
        pressure_exact_static=False,
        capillary_drive_present=True,
        pressure_reaction_projection_status="hfe_pressure_jump",
    )
    try:
        validate_geometric_runtime_capillary_application_admitted(application)
        admitted = True
    except Exception:
        admitted = False
    return [
        _component_row(
            "hfe_drive_admission",
            1.0 if admitted else 0.0,
            "admitted",
            admitted,
        )
    ]


def _regular_stratum_contract_rows() -> list[dict]:
    """Nearly horizontal graph guards must move y lines, not squeeze x cells."""
    grid = Grid(
        GridConfig(
            ndim=2,
            N=(8, 8),
            L=(1.0, 1.0),
            alpha_grid=2.0,
            fitting_axes=(True, True),
            fitting_dx_min_floor=(1.0e-4, 1.0e-4),
        ),
        Backend(use_gpu=False),
    )
    x = np.asarray(grid.coords[0])
    y = np.asarray(grid.coords[1])
    X, Y = np.meshgrid(x, y, indexing="ij")
    phi = 0.5 - Y + 1.0e-8 * np.cos(2.0 * np.pi * X)
    shifted = grid._enforce_regular_interface_stratum_backend(
        np,
        phi,
        [x.copy(), y.copy()],
        [x.copy(), y.copy()],
        fitting_axes=(True, True),
        fitting_dx_floor=(1.0e-4, 1.0e-4),
    )
    x_shift = float(np.max(np.abs(shifted[0] - x)))
    y_shift = float(np.max(np.abs(shifted[1] - y)))
    return [
        _component_row("stratum_guard_x_preserved", x_shift, "== 0", x_shift == 0.0),
        _component_row("stratum_guard_y_moved", y_shift, "> 0", y_shift > 0.0),
    ]


def compute_component_contracts() -> dict[str, np.ndarray]:
    rows = (
        _graph_hfe_jump_contract_rows()
        + _pressure_history_contract_rows()
        + _hfe_admission_contract_rows()
        + _regular_stratum_contract_rows()
    )
    return _columns(rows)


def component_rows_from_results(results: dict) -> list[dict]:
    table = results.get("component_rows", {})
    if not table:
        return []
    keys = list(table.keys())
    n = len(np.asarray(table[keys[0]])) if keys else 0
    return [
        {key: np.asarray(table[key])[i].item() for key in keys}
        for i in range(n)
    ]


def rows_from_results(results: dict) -> list[dict]:
    table = results["rows"]
    keys = list(table.keys())
    n = len(np.asarray(table[keys[0]])) if keys else 0
    return [
        {key: np.asarray(table[key])[i].item() for key in keys}
        for i in range(n)
    ]


def compute_results(cases: tuple[CaseSpec, ...] = U12_CASES) -> dict:
    rows: list[dict] = []
    for spec in cases:
        args = _probe_args(spec)
        for path, fn in PATHS.items():
            try:
                raw = fn(args, BOUNDARY)
            except Exception as exc:  # pragma: no cover - experiment guard
                raw = {"status": "error", "fail_close": repr(exc)}
            rows.append(_normalise_row(spec, path, raw))
    return {"rows": _columns(rows), "component_rows": compute_component_contracts()}


def _find(rows: list[dict], case_id: str, path: str) -> dict:
    matches = [row for row in rows if row["case_id"] == case_id and row["path"] == path]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {case_id}/{path}, got {len(matches)}")
    return matches[0]


def is_fail_close(row: dict) -> bool:
    marker = str(row["fail_close"]).strip()
    return str(row["status"]) == "ok" and marker not in ("", "0", "False", "false", "None", "none")


def is_pending_packet(row: dict) -> bool:
    return (
        str(row["status"]) == "ok"
        and str(row["range_status"]) == "pressure_reaction_projection_pending"
    )


def assert_component_contracts(results: dict) -> None:
    rows = component_rows_from_results(results)
    if not rows:
        raise AssertionError("U12 component contract rows are missing")
    failures = [row for row in rows if int(row["passed"]) != 1]
    if failures:
        labels = ", ".join(str(row["metric"]) for row in failures)
        raise AssertionError(f"U12 component contracts failed: {labels}")


def assert_u12_acceptance(results: dict, *, require_gpu: bool) -> None:
    rows = rows_from_results(results)
    flat_exact = _find(rows, "flat_n32", "cpu_exact")
    flat_component = _find(rows, "flat_n32", "cpu_component_hodge")
    if abs(float(flat_exact["balanced_l2"])) > TOL_ZERO:
        raise AssertionError("U12 flat CPU exact split is not zero-drive")
    if abs(float(flat_component["balanced_l2"])) > TOL_ZERO:
        raise AssertionError("U12 flat component-volume probe is not zero-drive")

    for case_id in ("wave_n32", "wave_n64"):
        exact = _find(rows, case_id, "cpu_exact")
        component = _find(rows, case_id, "cpu_component_hodge")
        if abs(float(exact["balanced_l2"])) > TOL_ZERO:
            raise AssertionError(f"U12 {case_id} full pressure split did not cancel")
        if float(exact["yl_residual_l2"]) <= 0.0:
            raise AssertionError(f"U12 {case_id} has no Young--Laplace residual")
        if float(component["balanced_l2"]) <= TOL_WAVE:
            raise AssertionError(f"U12 {case_id} component probe did not detect wave")

    gpu_rows = [row for row in rows if row["path"] == "gpu_packet"]
    if require_gpu and not all(row["status"] == "ok" for row in gpu_rows):
        raise AssertionError("U12 GPU gate was required but at least one GPU row did not run")
    if require_gpu:
        for row in gpu_rows:
            if str(row["case_id"]).startswith("wave_"):
                if not is_pending_packet(row):
                    raise AssertionError(
                        f"U12 {row['case_id']} GPU packet did not stop at split-pending"
                    )
                if float(row["balanced_l2"]) <= 0.0:
                    raise AssertionError(
                        f"U12 {row['case_id']} GPU packet erased non-static drive"
                    )
            elif abs(float(row["balanced_l2"])) > TOL_ZERO:
                raise AssertionError(
                    f"U12 {row['case_id']} flat GPU packet is not zero-drive"
                )
    assert_component_contracts(results)


def make_figures(
    results: dict,
    *,
    title: str,
    figure_name: str,
    paper_fig: pathlib.Path,
    out_dir: pathlib.Path = OUT,
) -> None:
    rows = rows_from_results(results)
    cases = list(dict.fromkeys(str(row["case_id"]) for row in rows))
    x_pos = np.arange(len(cases))
    width = 0.34
    exact = [float(_find(rows, case, "cpu_exact")["balanced_l2"]) for case in cases]
    component = [
        float(_find(rows, case, "cpu_component_hodge")["balanced_l2"])
        for case in cases
    ]
    gpu_pending = [
        1.0
        if is_pending_packet(_find(rows, case, "gpu_packet"))
        else 0.0
        for case in cases
    ]

    component_rows = component_rows_from_results(results)
    contract_labels = [str(row["metric"]) for row in component_rows]
    contract_passed = [int(row["passed"]) for row in component_rows]

    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.4))
    ax_residual, ax_gpu, ax_contract = axes
    ax_residual.bar(x_pos - width / 2, exact, width, label="CPU exact full pressure")
    ax_residual.bar(x_pos + width / 2, component, width, label="component-volume probe")
    ax_residual.set_xticks(x_pos, cases, rotation=20, ha="right")
    ax_residual.set_ylabel("balanced drive weighted L2")
    ax_residual.set_yscale("symlog", linthresh=1.0e-12)
    ax_residual.set_title("pressure-space split")
    ax_residual.legend(fontsize=7)

    ax_gpu.bar(x_pos, gpu_pending, color="0.35")
    ax_gpu.set_xticks(x_pos, cases, rotation=20, ha="right")
    ax_gpu.set_ylim(-0.05, 1.05)
    ax_gpu.set_yticks([0, 1], ["other", "split-pending"])
    ax_gpu.set_title("GPU packet boundary")

    contract_pos = np.arange(len(contract_labels))
    ax_contract.bar(contract_pos, contract_passed, color="0.25")
    ax_contract.set_xticks(contract_pos, contract_labels, rotation=35, ha="right")
    ax_contract.set_ylim(-0.05, 1.05)
    ax_contract.set_yticks([0, 1], ["fail", "pass"])
    ax_contract.set_title("graph-HFE/grid contracts")
    fig.suptitle(title)
    fig.tight_layout()
    save_figure(fig, out_dir / figure_name, also_to=paper_fig)


def print_summary(results: dict) -> None:
    rows = rows_from_results(results)
    for case_id in dict.fromkeys(str(row["case_id"]) for row in rows):
        exact = _find(rows, case_id, "cpu_exact")
        component = _find(rows, case_id, "cpu_component_hodge")
        gpu = _find(rows, case_id, "gpu_packet")
        print(
            f"U12 {case_id}: "
            f"cpu_exact_balanced={float(exact['balanced_l2']):.6e}, "
            f"component_balanced={float(component['balanced_l2']):.6e}, "
            f"gpu_status={gpu['status']}, "
            f"gpu_split_pending={is_pending_packet(gpu)}"
        )
    for row in component_rows_from_results(results):
        print(
            f"U12 contract {row['metric']}: "
            f"value={float(row['value']):.6e}, "
            f"criterion={row['criterion']}, passed={bool(row['passed'])}"
        )


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--require-gpu",
        action="store_true",
        help="Require GPU packet rows to run and stop at split-pending on non-static waves.",
    )
    args = parser.parse_args()
    if args.plot_only:
        results = load_results(NPZ)
    else:
        results = compute_results()
        save_results(NPZ, results)
    assert_u12_acceptance(results, require_gpu=args.require_gpu)
    make_figures(
        results,
        title="U12 active-geometry capillary split gate",
        figure_name="U12_ao_capillary_split_gate",
        paper_fig=PAPER_FIG,
    )
    print_summary(results)
    print(f"==> U12 outputs in {OUT}")


if __name__ == "__main__":
    main()
