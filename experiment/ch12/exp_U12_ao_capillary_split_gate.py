#!/usr/bin/env python3
"""[U12] AO-Fast geometric capillary split gate.

Paper ref: Chapter 12 U12.

This component gate formalizes the Rung-0 AO capillary split diagnostic used
by the paper. It does not advance Navier--Stokes. It compares the CPU exact
full pressure-image split, the CPU component-volume Hodge residual probe, and
the current GPU AO-Fast packet/fail-close behavior.

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
    return {"rows": _columns(rows)}


def _find(rows: list[dict], case_id: str, path: str) -> dict:
    matches = [row for row in rows if row["case_id"] == case_id and row["path"] == path]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {case_id}/{path}, got {len(matches)}")
    return matches[0]


def is_fail_close(row: dict) -> bool:
    marker = str(row["fail_close"]).strip()
    return str(row["status"]) == "ok" and marker not in ("", "0", "False", "false", "None", "none")


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
            if str(row["case_id"]).startswith("wave_") and not is_fail_close(row):
                raise AssertionError(f"U12 {row['case_id']} GPU packet did not fail-close")


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
    gpu_failed = [
        1.0
        if is_fail_close(_find(rows, case, "gpu_packet"))
        else 0.0
        for case in cases
    ]

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2))
    ax_residual, ax_gpu = axes
    ax_residual.bar(x_pos - width / 2, exact, width, label="CPU exact full pressure")
    ax_residual.bar(x_pos + width / 2, component, width, label="component-volume probe")
    ax_residual.set_xticks(x_pos, cases, rotation=20, ha="right")
    ax_residual.set_ylabel("balanced drive weighted L2")
    ax_residual.set_yscale("symlog", linthresh=1.0e-12)
    ax_residual.set_title("pressure-space split")
    ax_residual.legend(fontsize=7)

    ax_gpu.bar(x_pos, gpu_failed, color="0.35")
    ax_gpu.set_xticks(x_pos, cases, rotation=20, ha="right")
    ax_gpu.set_ylim(-0.05, 1.05)
    ax_gpu.set_yticks([0, 1], ["accepted/skip", "fail-close"])
    ax_gpu.set_title("GPU packet gate")
    fig.suptitle(title)
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
            f"gpu_fail_close={is_fail_close(gpu)}"
        )


def main() -> None:
    parser = experiment_argparser(__doc__)
    parser.add_argument(
        "--require-gpu",
        action="store_true",
        help="Require GPU packet rows to run and fail-close on non-static waves.",
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
        title="U12 AO-Fast capillary split gate",
        figure_name="U12_ao_capillary_split_gate",
        paper_fig=PAPER_FIG,
    )
    print_summary(results)
    print(f"==> U12 outputs in {OUT}")


if __name__ == "__main__":
    main()
