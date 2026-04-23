"""Fused kernels and small helpers for ridge-eikonal reinitialization."""

from __future__ import annotations

from ..backend import fuse as _fuse


@_fuse
def _sigma_eff_kernel(h_field, sigma_0, h_ref):
    return sigma_0 * h_field / h_ref


@_fuse
def _eps_local_kernel(h_field, eps_scale, eps_xi):
    return eps_scale * eps_xi * h_field


def _sigmoid_xp(xp, phi, eps_local):
    return 1.0 / (1.0 + xp.exp(-phi / eps_local))
