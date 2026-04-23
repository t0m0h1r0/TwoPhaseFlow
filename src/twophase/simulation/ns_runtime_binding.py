"""Compatibility binding helpers for `TwoPhaseNSSolver` runtime state."""

from __future__ import annotations


def bind_ns_interface_runtime(solver, state) -> None:
    solver._interface_runtime = state
    solver._rebuild_freq = state.rebuild_freq
    solver._reinit_every = state.reinit_every
    solver._reproject_variable_density = state.reproject_variable_density
    solver._face_flux_projection = state.face_flux_projection
    solver._reinit_eps_scale = state.reinit_eps_scale
    solver._kappa_max = state.kappa_max
    solver._interface_tracking_enabled = state.interface_tracking_enabled
    solver._interface_tracking_method = state.interface_tracking_method
    solver._phi_primary_transport = state.phi_primary_transport
    solver._phi_primary_redist_every = state.phi_primary_redist_every
    solver._phi_primary_clip_factor = state.phi_primary_clip_factor
    solver._phi_primary_heaviside_eps_scale = state.phi_primary_heaviside_eps_scale
    solver._reproject_mode = state.reproject_mode


def bind_ns_ppe_runtime(solver, state) -> None:
    solver._ppe_runtime = state
    solver._ppe_solver_name = state.ppe_solver_name
    solver._ppe_iteration_method = state.ppe_iteration_method
    solver._ppe_coefficient_scheme = state.ppe_coefficient_scheme
    solver._ppe_interface_coupling_scheme = state.ppe_interface_coupling_scheme
    solver._ppe_tolerance = state.ppe_tolerance
    solver._ppe_max_iterations = state.ppe_max_iterations
    solver._ppe_restart = state.ppe_restart
    solver._ppe_preconditioner = state.ppe_preconditioner
    solver._ppe_pcr_stages = state.ppe_pcr_stages
    solver._ppe_c_tau = state.ppe_c_tau
    solver._ppe_defect_correction = state.ppe_defect_correction
    solver._ppe_dc_max_iterations = state.ppe_dc_max_iterations
    solver._ppe_dc_tolerance = state.ppe_dc_tolerance
    solver._ppe_dc_relaxation = state.ppe_dc_relaxation
    solver._pressure_scheme = state.pressure_scheme


def bind_ns_scheme_runtime(solver, state) -> None:
    solver._scheme_runtime = state
    solver._convection_time_scheme = state.convection_time_scheme
    solver._momentum_gradient_scheme = state.momentum_gradient_scheme
    solver._pressure_gradient_scheme = state.pressure_gradient_scheme
    solver._surface_tension_gradient_scheme = state.surface_tension_gradient_scheme
    solver._advection_scheme = state.advection_scheme
    solver._convection_scheme = state.convection_scheme
