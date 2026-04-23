"""Shared kernels and helper functions for CLS advection schemes."""

from __future__ import annotations

from ..backend import fuse as _fuse

_D0, _D1, _D2 = 1.0 / 10.0, 6.0 / 10.0, 3.0 / 10.0
_WENO_EPS = 1e-6
_EPS_D_ADV = 0.05


@_fuse
def _dccd_filter_stencil(fp, fp_p1, fp_m1, eps_d):
    return fp + eps_d * (fp_p1 - 2.0 * fp + fp_m1)


@_fuse
def _weno5_pos_impl(q0, q1, q2, q3, q4):
    _t0a = q0 - 2*q1 + q2;  _t0b = q0 - 4*q1 + 3*q2
    _t1a = q1 - 2*q2 + q3;  _t1b = q1 - q3
    _t2a = q2 - 2*q3 + q4;  _t2b = 3*q2 - 4*q3 + q4
    b0 = (13.0/12.0)*_t0a*_t0a + (1.0/4.0)*_t0b*_t0b
    b1 = (13.0/12.0)*_t1a*_t1a + (1.0/4.0)*_t1b*_t1b
    b2 = (13.0/12.0)*_t2a*_t2a + (1.0/4.0)*_t2b*_t2b

    _e0 = _WENO_EPS + b0; _e1 = _WENO_EPS + b1; _e2 = _WENO_EPS + b2
    a0 = _D0 / (_e0*_e0)
    a1 = _D1 / (_e1*_e1)
    a2 = _D2 / (_e2*_e2)
    a_sum = a0 + a1 + a2
    w0, w1, w2 = a0/a_sum, a1/a_sum, a2/a_sum

    r0 = (1.0/3.0)*q0 - (7.0/6.0)*q1 + (11.0/6.0)*q2
    r1 = -(1.0/6.0)*q1 + (5.0/6.0)*q2 + (1.0/3.0)*q3
    r2 = (1.0/3.0)*q2 + (5.0/6.0)*q3 - (1.0/6.0)*q4
    return w0*r0 + w1*r1 + w2*r2


@_fuse
def _weno5_neg_impl(q0, q1, q2, q3, q4):
    _t0a = q0 - 2*q1 + q2;  _t0b = q0 - 4*q1 + 3*q2
    _t1a = q1 - 2*q2 + q3;  _t1b = q1 - q3
    _t2a = q2 - 2*q3 + q4;  _t2b = 3*q2 - 4*q3 + q4
    b0 = (13.0/12.0)*_t0a*_t0a + (1.0/4.0)*_t0b*_t0b
    b1 = (13.0/12.0)*_t1a*_t1a + (1.0/4.0)*_t1b*_t1b
    b2 = (13.0/12.0)*_t2a*_t2a + (1.0/4.0)*_t2b*_t2b

    _e0 = _WENO_EPS + b0; _e1 = _WENO_EPS + b1; _e2 = _WENO_EPS + b2
    a0 = _D2 / (_e0*_e0)
    a1 = _D1 / (_e1*_e1)
    a2 = _D0 / (_e2*_e2)
    a_sum = a0 + a1 + a2
    w0, w1, w2 = a0/a_sum, a1/a_sum, a2/a_sum

    r0 = -(1.0/6.0)*q0 + (5.0/6.0)*q1 + (1.0/3.0)*q2
    r1 = (1.0/3.0)*q1 + (5.0/6.0)*q2 - (1.0/6.0)*q3
    r2 = (11.0/6.0)*q2 - (7.0/6.0)*q3 + (1.0/3.0)*q4
    return w0*r0 + w1*r1 + w2*r2


def _weno5_pos(*args):
    """Compatibility wrapper accepting either `(q0..q4)` or `(xp, q0..q4)`."""
    if len(args) == 6:
        _, q0, q1, q2, q3, q4 = args
    else:
        q0, q1, q2, q3, q4 = args
    return _weno5_pos_impl(q0, q1, q2, q3, q4)


def _weno5_neg(*args):
    """Compatibility wrapper accepting either `(q0..q4)` or `(xp, q0..q4)`."""
    if len(args) == 6:
        _, q0, q1, q2, q3, q4 = args
    else:
        q0, q1, q2, q3, q4 = args
    return _weno5_neg_impl(q0, q1, q2, q3, q4)


def _pad_bc(xp, arr, axis: int, n_ghost: int, bc_type: str):
    from ..core.boundary import pad_ghost_cells
    return pad_ghost_cells(xp, arr, axis, n_ghost, bc_type)
