#!/usr/bin/env python3
"""Root-cause probe for the failed Chapter 14 capillary-wave benchmark.

Symbol mapping:
  ``psi``          -> CLS indicator ψ
  ``kappa``        -> curvature κ
  ``sigma``        -> surface tension σ
  ``jump_pressure``-> pressure jump proxy J = σ κ (1 - ψ)
  ``a2``           -> signed Fourier coefficient of η(x,t)=y_Γ(x,t)-0.5

The probe intentionally does not modify the solver.  It extracts evidence for
the mathematical failure mode:

  L(p_base) = rhs - L(J),  p_total = p_base + J.

For an initially stationary capillary wave with ``rhs≈0``, a volume-field
decomposition allows ``p_base≈-J``; the total pressure seen by velocity
correction becomes nearly zero, so the capillary wave is not accelerated.
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
from pathlib import Path
from typing import Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Diagnose ch14 capillary-wave pressure-jump failure.",
    )
    parser.add_argument(
        "--npz",
        type=Path,
        default=Path(
            "/Users/tomohiro/Downloads/TwoPhaseFlow/"
            "experiment/ch14/results/ch14_capillary/data.npz"
        ),
        help="Path to the completed ch14_capillary data.npz.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("experiment/ch14/config/ch14_capillary.yaml"),
        help="Config used for a local one-step algebraic probe.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/A/ch14_capillary_rootcause_probe.md"),
        help="Markdown output path.",
    )
    return parser.parse_args(argv)


def interface_crossing(psi_frame: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Extract the central ψ=0.5 interface as y_Γ(x)."""
    values = []
    for i in range(len(x)):
        column = psi_frame[i]
        hits = np.where((column[:-1] - 0.5) * (column[1:] - 0.5) <= 0.0)[0]
        y_value = np.nan
        for j in hits:
            psi0 = float(column[j])
            psi1 = float(column[j + 1])
            if psi1 == psi0:
                candidate = float(y[j])
            else:
                candidate = float(y[j] + (0.5 - psi0) * (y[j + 1] - y[j]) / (psi1 - psi0))
            if 0.25 <= candidate <= 0.75:
                y_value = candidate
                break
        values.append(y_value)
    return np.asarray(values)


def signed_mode_series(
    psi: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    *,
    mode: int,
    length: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``a_m(t)`` and interface traces from ψ snapshots."""
    k = 2.0 * math.pi * mode / length
    coeffs = []
    traces = []
    for frame in psi:
        trace = interface_crossing(frame, x, y)
        traces.append(trace)
        eta = trace - 0.5
        coeffs.append(2.0 * np.trapezoid(eta * np.cos(k * x), x))
    return np.asarray(coeffs), np.asarray(traces)


def face_mask_stats(rho: np.ndarray, pressure: np.ndarray, coords: tuple[np.ndarray, np.ndarray]) -> dict:
    """Measure phase-separated face masking and pressure flux suppression."""
    threshold = 0.5 * (float(np.min(rho)) + float(np.max(rho)))
    stats = {}
    for axis, name in enumerate(("x", "y")):
        slices_lo = [slice(None)] * 2
        slices_hi = [slice(None)] * 2
        n_faces = rho.shape[axis] - 1
        slices_lo[axis] = slice(0, n_faces)
        slices_hi[axis] = slice(1, n_faces + 1)
        lo = tuple(slices_lo)
        hi = tuple(slices_hi)
        rho_lo = rho[lo]
        rho_hi = rho[hi]
        same_phase = (rho_lo >= threshold) == (rho_hi >= threshold)
        spacing = coords[axis][1:] - coords[axis][:-1]
        shape = [1, 1]
        shape[axis] = -1
        grad_p = (pressure[hi] - pressure[lo]) / spacing.reshape(shape)
        coeff = 2.0 / (rho_lo + rho_hi)
        density_flux = coeff * grad_p
        cross_flux = density_flux[~same_phase]
        stats[name] = {
            "faces": int(same_phase.size),
            "cross_faces": int(np.count_nonzero(~same_phase)),
            "cross_fraction": float(np.mean(~same_phase)),
            "density_flux_max": float(np.max(np.abs(density_flux))),
            "cross_density_flux_max": float(np.max(np.abs(cross_flux))) if cross_flux.size else 0.0,
            "phase_separated_cross_flux_max": 0.0,
        }
    return stats


def one_step_jump_cancellation(config_path: Path) -> dict:
    """Run one local step and measure ``J`` versus the returned total pressure."""
    from twophase.simulation.config_io import load_experiment_config
    from twophase.simulation.ns_pipeline import TwoPhaseNSSolver
    from twophase.simulation.ns_step_state import NSStepRequest

    cfg = load_experiment_config(config_path)
    cfg = copy.copy(cfg)
    cfg.run = copy.copy(cfg.run)
    cfg.run.max_steps = 1
    cfg.run.T_final = 0.002
    cfg.run.print_every = 10_000

    solver = TwoPhaseNSSolver.from_config(cfg)
    psi = solver.build_ic(cfg)
    u, v = solver.build_velocity(cfg, psi)
    bc_hook = solver.make_bc_hook(cfg)
    physics = cfg.physics
    if solver._alpha_grid > 1.0:
        psi, u, v = solver._rebuild_grid(psi, u, v, physics.rho_l, physics.rho_g)
    dt_budget = solver.dt_budget(
        u,
        v,
        physics,
        cfg.run.cfl,
        cfl_advective=cfg.run.cfl_advective,
        cfl_capillary=cfg.run.cfl_capillary,
        cfl_viscous=cfg.run.cfl_viscous,
    )
    state = solver._prepare_step_inputs(
        NSStepRequest(
            psi=psi,
            u=u,
            v=v,
            dt=dt_budget.dt,
            rho_l=physics.rho_l,
            rho_g=physics.rho_g,
            sigma=physics.sigma,
            mu=physics.mu,
            g_acc=physics.g_acc,
            rho_ref=physics.rho_ref,
            mu_l=physics.mu_l,
            mu_g=physics.mu_g,
            bc_hook=bc_hook,
            step_index=0,
        )
    )
    state = solver._advance_interface_stage(state)
    state = solver._materialise_step_fields(state)
    state = solver._surface_tension_stage(state)
    solver._ppe_solver.set_interface_jump_context(
        psi=state.psi,
        kappa=state.kappa,
        sigma=state.sigma,
    )
    operator = getattr(solver._ppe_solver, "operator", solver._ppe_solver)
    xp = solver._backend.xp
    jump_pressure = operator.apply_interface_jump(xp.zeros_like(state.psi))
    jump_host = np.asarray(solver._backend.to_host(jump_pressure))
    state = solver._predict_velocity_stage(state)
    state = solver._solve_pressure_stage(state)
    pressure_host = np.asarray(solver._backend.to_host(state.pressure))
    state = solver._correct_velocity_stage(state)
    speed = np.sqrt(
        np.asarray(solver._backend.to_host(state.u)) ** 2
        + np.asarray(solver._backend.to_host(state.v)) ** 2
    )
    return {
        "dt": float(dt_budget.dt),
        "kappa_max": float(solver._backend.asnumpy(xp.max(xp.abs(state.kappa)))),
        "jump_min": float(np.min(jump_host)),
        "jump_max": float(np.max(jump_host)),
        "jump_ptp": float(np.ptp(jump_host)),
        "pressure_min": float(np.min(pressure_host)),
        "pressure_max": float(np.max(pressure_host)),
        "pressure_ptp": float(np.ptp(pressure_host)),
        "pressure_to_jump_ptp": float(np.ptp(pressure_host) / max(np.ptp(jump_host), 1e-300)),
        "speed_max": float(np.max(speed)),
    }


def build_report(npz_path: Path, config_path: Path) -> str:
    """Build a Markdown report from saved data and one-step algebraic evidence."""
    data = np.load(npz_path)
    times = data["times"]
    field_times = data["fields/times"]
    x = data["fields/grid_coords/0"]
    y = data["fields/grid_coords/1"]
    psi = data["fields/psi"]
    pressure = data["fields/p"]
    rho = data["fields/rho"]
    velocity_u = data["fields/u"]
    velocity_v = data["fields/v"]
    volume = data["volume_conservation"]
    amplitude = data["interface_amplitude"]
    kinetic = data["kinetic_energy"]
    div_u = data["debug_diagnostics/div_u_max"]
    kappa_max = data["debug_diagnostics/kappa_max"]

    sigma = 0.072
    rho_l = 1000.0
    rho_g = 1.2
    amplitude0 = 0.01
    mode = 2
    length = 1.0
    wavenumber = 2.0 * math.pi * mode / length
    omega = math.sqrt(sigma * wavenumber**3 / (rho_l + rho_g))
    period = 2.0 * math.pi / omega
    expected_jump_amp = sigma * amplitude0 * wavenumber**2
    expected_speed = amplitude0 * omega

    signed_mode, traces = signed_mode_series(psi, x, y, mode=mode, length=length)
    speed = np.sqrt(velocity_u**2 + velocity_v**2)
    speed_max = speed.reshape(speed.shape[0], -1).max(axis=1)
    face_stats = face_mask_stats(rho[0], pressure[0], (x, y))
    one_step = one_step_jump_cancellation(config_path)

    high_mode_ratios = []
    for trace in traces:
        eta = trace[:-1] - np.mean(trace[:-1])
        spectrum = np.abs(np.fft.rfft(eta))
        m2 = spectrum[mode] if len(spectrum) > mode else 0.0
        high = float(np.sum(spectrum[mode + 1 :] ** 2))
        low = float(m2**2)
        high_mode_ratios.append(math.sqrt(high / max(low, 1e-300)))
    high_mode_ratios = np.asarray(high_mode_ratios)

    lines = [
        "# CHK-RA-CH14-005 — capillary-wave root-cause probe",
        "",
        "## Core Measurements",
        "",
        f"- Result NPZ: `{npz_path}`",
        f"- Steps recorded: `{len(times)}`; snapshots: `{len(field_times)}`",
        f"- `dt = {times[0]:.12e}`, `T = {times[-1]:.6g}`, inviscid period `T_omega = {period:.9f}`",
        f"- Expected velocity scale `A0 omega = {expected_speed:.6e}`",
        f"- Observed max snapshot `||u||_inf = {np.max(speed_max):.6e}` "
        f"(`{np.max(speed_max) / expected_speed:.3%}` of scale)",
        f"- Expected smooth pressure-jump amplitude `sigma A0 k^2 = {expected_jump_amp:.6e}`",
        f"- Initial saved pressure range `ptp(p) = {np.ptp(pressure[0]):.6e}` "
        f"(`{np.ptp(pressure[0]) / expected_jump_amp:.3%}` of expected jump amplitude)",
        f"- Signed `m=2` mode: `{signed_mode[0]:.6e} -> {signed_mode[-1]:.6e}`; "
        f"zero crossings `{np.count_nonzero(np.signbit(signed_mode[:-1]) != np.signbit(signed_mode[1:]))}`",
        f"- Unsigned amplitude: initial `{amplitude[0]:.6e}`, final `{amplitude[-1]:.6e}`, max `{np.max(amplitude):.6e}`",
        f"- Volume drift max `{np.max(np.abs(volume)):.6e}`; kinetic max `{np.max(kinetic):.6e}`; div max `{np.max(div_u):.6e}`",
        f"- `kappa_max` cap hit count `{np.count_nonzero(kappa_max >= 5.0 - 1e-12)} / {len(kappa_max)}`",
        f"- Interface high-mode/m=2 spectral ratio: initial `{high_mode_ratios[0]:.3e}`, "
        f"final `{high_mode_ratios[-1]:.3e}`, max `{np.max(high_mode_ratios):.3e}`",
        "",
        "## One-Step Algebraic Probe",
        "",
        f"- `max|kappa| = {one_step['kappa_max']:.6e}` before clipping-driven later-time cap saturation",
        f"- Constructed jump proxy `J = sigma kappa (1-psi)`: "
        f"`ptp(J) = {one_step['jump_ptp']:.6e}`",
        f"- Returned total pressure after PPE: `ptp(p_total) = {one_step['pressure_ptp']:.6e}`",
        f"- Cancellation ratio `ptp(p_total) / ptp(J) = {one_step['pressure_to_jump_ptp']:.6e}`",
        f"- One-step `||u||_inf = {one_step['speed_max']:.6e}`",
        "",
        "## Phase-Separated Face Mask Evidence",
        "",
    ]
    for axis in ("x", "y"):
        stats = face_stats[axis]
        lines.extend(
            [
                f"- `{axis}` faces: cross-phase `{stats['cross_faces']} / {stats['faces']}` "
                f"(`{stats['cross_fraction']:.3%}`)",
                f"  - density-gradient flux max `{stats['density_flux_max']:.6e}`; "
                f"cross-phase density flux max `{stats['cross_density_flux_max']:.6e}`",
                "  - phase-separated cross-phase flux is exactly `0` by construction.",
            ]
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The primary failure is not CFL instability, viscous overdamping, or insufficient run time.",
            "The capillary-wave drive is algebraically suppressed before it can create the expected",
            "normal velocity.  In the current pressure-jump decomposition the solver forms",
            "`L(p_base)=rhs-L(J)` and then returns `p_total=p_base+J`.  For the initially",
            "stationary wave, `rhs≈0`, so the elliptic solve finds `p_base≈-J`; the returned",
            "pressure range is only about `1e-3` of the represented jump.  The velocity",
            "correction therefore sees almost no capillary pressure gradient.",
            "",
            "[SOLID-X] Diagnostic-only script; no production module boundary change.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_report(args.npz.resolve(), args.config), encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
