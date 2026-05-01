"""PPE runtime helpers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from .ns_runtime_config import NSPPERuntimeState
from .ns_runtime_factories import (
    NSPPEFactoryOptions,
    build_ns_ppe_cfg_shim,
    build_ns_ppe_solver,
    build_ns_plain_ppe_solver,
)


def make_ns_ppe_factory_options(
    state: NSPPERuntimeState,
    *,
    solver_name: str | None = None,
) -> NSPPEFactoryOptions:
    return NSPPEFactoryOptions(
        solver_name=solver_name or state.ppe_solver_name,
        dc_base_solver_name=state.ppe_dc_base_solver_name,
        tolerance=state.ppe_tolerance,
        max_iterations=state.ppe_max_iterations,
        restart=state.ppe_restart,
        preconditioner=state.ppe_preconditioner,
        pcr_stages=state.ppe_pcr_stages,
        c_tau=state.ppe_c_tau,
        iteration_method=state.ppe_iteration_method,
        coefficient_scheme=state.ppe_coefficient_scheme,
        interface_coupling_scheme=state.ppe_interface_coupling_scheme,
        defect_correction=state.ppe_defect_correction,
        dc_max_iterations=state.ppe_dc_max_iterations,
        dc_tolerance=state.ppe_dc_tolerance,
        dc_relaxation=state.ppe_dc_relaxation,
    )


def build_ns_runtime_ppe_solver(
    *,
    backend,
    grid,
    bc_type: str,
    fccd,
    state: NSPPERuntimeState,
    pressure_scheme: str,
):
    return build_ns_ppe_solver(
        backend=backend,
        grid=grid,
        bc_type=bc_type,
        fccd=fccd,
        options=make_ns_ppe_factory_options(state, solver_name=pressure_scheme),
    )


def build_ns_runtime_plain_ppe_solver(
    *,
    backend,
    grid,
    bc_type: str,
    fccd,
    state: NSPPERuntimeState,
    ppe_scheme: str,
):
    return build_ns_plain_ppe_solver(
        backend=backend,
        grid=grid,
        bc_type=bc_type,
        fccd=fccd,
        options=make_ns_ppe_factory_options(state, solver_name=ppe_scheme),
    )


def build_ns_runtime_ppe_cfg_shim(
    state: NSPPERuntimeState,
    *,
    preconditioner: str | None = None,
    pcr_stages: int | None = None,
):
    return build_ns_ppe_cfg_shim(
        make_ns_ppe_factory_options(state),
        preconditioner=preconditioner,
        pcr_stages=pcr_stages,
    )
