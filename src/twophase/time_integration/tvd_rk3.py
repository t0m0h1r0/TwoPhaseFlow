"""
TVD-RK3 (Total Variation Diminishing Runge-Kutta 3rd order).

Implements §8 (Eq. 79–81) of the paper.

The Shu-Osher TVD-RK3 scheme for dq/dt = L(q):

    q^(1) = qⁿ + Δt · L(qⁿ)
    q^(2) = (3/4) qⁿ + (1/4) q^(1) + (1/4) Δt · L(q^(1))
    q^{n+1} = (1/3) qⁿ + (2/3) q^(2) + (2/3) Δt · L(q^(2))

This scheme is 3rd-order accurate and total-variation diminishing for
scalar conservation laws, making it suitable for the CLS advection
equation where ψ is nearly discontinuous.

Usage::

    def my_rhs(q): ...
    q_new = tvd_rk3(xp, q, dt, my_rhs)
"""

from __future__ import annotations
from typing import Callable


def tvd_rk3(xp, q, dt: float, rhs_func: Callable):
    """Advance ``q`` by one step with TVD-RK3.

    Parameters
    ----------
    xp        : array namespace (numpy or cupy)
    q         : current state array (not modified)
    dt        : time step
    rhs_func  : callable ``L(q) -> array``, same shape as q

    Returns
    -------
    q_new : advanced state
    """
    q0 = q
    q1 = q0 + dt * rhs_func(q0)
    q2 = 0.75 * q0 + 0.25 * (q1 + dt * rhs_func(q1))
    q_new = (1.0 / 3.0) * q0 + (2.0 / 3.0) * (q2 + dt * rhs_func(q2))
    return q_new
