#!/usr/bin/env python3
"""[V11] Active-geometry capillary split integration gate.

Paper ref: Chapter 13 V11.

This experiment promotes the U12 algebraic split diagnostic and graph-HFE
component contracts into a Chapter 13 admission gate. Passing this gate means
the old all-pressure-image split remains rejected, while the production
active-geometry route is guarded by current-interface HFE jumps, smooth
pressure-coordinate history, and regular-stratum grid rebuilding.

Usage
-----
  python experiment/ch13/exp_V11_ao_capillary_split_gate.py --require-gpu
  python experiment/ch13/exp_V11_ao_capillary_split_gate.py --plot-only
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

from experiment.ch12.exp_U12_ao_capillary_split_gate import (  # noqa: E402
    CaseSpec,
    assert_component_contracts,
    component_rows_from_results,
    compute_results,
    is_pending_packet,
    make_figures,
    rows_from_results,
)
from twophase.tools.experiment import (  # noqa: E402
    apply_style,
    experiment_argparser,
    experiment_dir,
    load_results,
    save_results,
)

apply_style()
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = experiment_dir(__file__)
NPZ = OUT / "data.npz"
PAPER_FIG = ROOT / "paper" / "figures" / "ch13_v11_ao_capillary_split_gate"

V11_CASES = (
    CaseSpec("flat_n32_pressure_coordinate", "flat", 32, 32, 0.0, "pressure_coordinate"),
    CaseSpec("wave_n32_pressure_coordinate", "capillary_wave", 32, 32, 2.0e-4, "pressure_coordinate"),
    CaseSpec("wave_n32_face_acceleration", "capillary_wave", 32, 32, 2.0e-4, "face_acceleration"),
    CaseSpec("wave_n64_pressure_coordinate", "capillary_wave", 64, 64, 2.0e-4, "pressure_coordinate"),
)

TOL_ZERO = 1.0e-10
TOL_WAVE = 1.0e-2


def _find(rows: list[dict], case_id: str, path: str) -> dict:
    matches = [row for row in rows if row["case_id"] == case_id and row["path"] == path]
    if len(matches) != 1:
        raise AssertionError(f"expected one row for {case_id}/{path}, got {len(matches)}")
    return matches[0]


def assert_v11_acceptance(results: dict, *, require_gpu: bool) -> None:
    rows = rows_from_results(results)
    flat = _find(rows, "flat_n32_pressure_coordinate", "cpu_component_hodge")
    if abs(float(flat["balanced_l2"])) > TOL_ZERO:
        raise AssertionError("V11 flat baseline is not zero-drive")

    for case_id in (
        "wave_n32_pressure_coordinate",
        "wave_n32_face_acceleration",
        "wave_n64_pressure_coordinate",
    ):
        exact = _find(rows, case_id, "cpu_exact")
        component = _find(rows, case_id, "cpu_component_hodge")
        gpu = _find(rows, case_id, "gpu_packet")
        if abs(float(exact["balanced_l2"])) > TOL_ZERO:
            raise AssertionError(f"V11 {case_id} full pressure split did not cancel")
        if float(component["balanced_l2"]) <= TOL_WAVE:
            raise AssertionError(f"V11 {case_id} component probe did not detect wave")
        if require_gpu and gpu["status"] != "ok":
            raise AssertionError(f"V11 {case_id} GPU row did not run")
        if require_gpu and not is_pending_packet(gpu):
            raise AssertionError(f"V11 {case_id} GPU packet did not stop at split-pending")
        if require_gpu and float(gpu["balanced_l2"]) <= 0.0:
            raise AssertionError(f"V11 {case_id} GPU packet erased non-static drive")
    assert_component_contracts(results)


def print_summary(results: dict) -> None:
    rows = rows_from_results(results)
    for case_id in dict.fromkeys(str(row["case_id"]) for row in rows):
        component = _find(rows, case_id, "cpu_component_hodge")
        gpu = _find(rows, case_id, "gpu_packet")
        print(
            f"V11 {case_id}: "
            f"component_balanced={float(component['balanced_l2']):.6e}, "
            f"gpu_status={gpu['status']}, "
            f"gpu_split_pending={is_pending_packet(gpu)}"
        )
    for row in component_rows_from_results(results):
        print(
            f"V11 contract {row['metric']}: "
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
        results = compute_results(V11_CASES)
        save_results(NPZ, results)
    assert_v11_acceptance(results, require_gpu=args.require_gpu)
    make_figures(
        results,
        title="V11 active-geometry capillary split integration gate",
        figure_name="V11_ao_capillary_split_gate",
        paper_fig=PAPER_FIG,
        out_dir=OUT,
    )
    print_summary(results)
    print(f"==> V11 outputs in {OUT}")


if __name__ == "__main__":
    main()
