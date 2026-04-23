"""Grouped step-state containers for `TwoPhaseNSSolver`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class NSStepInputs:
    psi: Any
    u: Any
    v: Any
    dt: float
    rho_l: float
    rho_g: float
    sigma: float
    mu: float | Any
    g_acc: float = 0.0
    rho_ref: float | None = None
    mu_l: float | None = None
    mu_g: float | None = None
    bc_hook: Any = None
    step_index: int = 0


@dataclass
class NSStepState:
    psi: Any
    u: Any
    v: Any
    dt: float
    rho_l: float
    rho_g: float
    sigma: float
    mu: float | Any
    g_acc: float
    rho_ref: float
    mu_l: float | None
    mu_g: float | None
    bc_hook: Any
    step_index: int
    rho: Any = None
    mu_field: float | Any | None = None
    kappa: Any = None
    f_x: Any = None
    f_y: Any = None
    debug_scalars: list[Any] | None = None
    u_star: Any = None
    v_star: Any = None
    pressure: Any = None
    p_corrector: Any = None

    @classmethod
    def from_inputs(cls, inputs: NSStepInputs, *, backend) -> "NSStepState":
        xp = backend.xp
        rho_ref = (
            0.5 * (inputs.rho_l + inputs.rho_g)
            if inputs.rho_ref is None
            else inputs.rho_ref
        )
        return cls(
            psi=xp.asarray(inputs.psi),
            u=xp.asarray(inputs.u),
            v=xp.asarray(inputs.v),
            dt=float(inputs.dt),
            rho_l=float(inputs.rho_l),
            rho_g=float(inputs.rho_g),
            sigma=float(inputs.sigma),
            mu=inputs.mu,
            g_acc=float(inputs.g_acc),
            rho_ref=float(rho_ref),
            mu_l=inputs.mu_l,
            mu_g=inputs.mu_g,
            bc_hook=inputs.bc_hook,
            step_index=int(inputs.step_index),
        )
