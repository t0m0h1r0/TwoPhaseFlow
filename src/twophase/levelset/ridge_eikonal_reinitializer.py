"""Ridge-eikonal reinitializer orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from .heaviside import invert_heaviside
from .interfaces import IReinitializer
from .ridge_eikonal_extractor import RidgeExtractor
from .ridge_eikonal_fmm import NonUniformFMM
from .ridge_eikonal_kernels import _eps_local_kernel, _sigmoid_xp
from .wall_contact import WallContactSet
from ..core.boundary import boundary_axes

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


class RidgeEikonalReinitializer(IReinitializer):
    """Topology-preserving reinit via ridge extraction + non-uniform FMM.

    The redistancing step solves the static Eikonal problem ``|grad(phi)| = 1``
    with the accepted-set upwind rule implemented in :class:`NonUniformFMM`.
    Approximate fixed-sweep pseudo-time reinitialisation is intentionally not
    used here because the downstream curvature and capillary/buoyancy balance
    depend on the converged signed-distance field.
    """

    def __init__(
        self,
        backend: "Backend",
        grid,
        ccd: "CCDSolver",
        eps: float,
        sigma_0: float = 3.0,
        eps_scale: float = 1.4,
        mass_correction: bool = True,
        h_ref: float | None = None,
    ):
        self._xp = backend.xp
        self._backend = backend
        self._grid = grid
        self._eps = float(eps)
        self._eps_scale = float(eps_scale)
        self._mass_correction = mass_correction
        self._wall_axes = tuple(
            axis == "wall"
            for axis in boundary_axes(getattr(ccd, "bc_type", "wall"), grid.ndim)
        )
        self._wall_closure = any(self._wall_axes)
        self._wall_contacts = WallContactSet.empty()

        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        if h_ref is None:
            h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
        self._h_ref = h_ref

        self._eps_xi = float(eps) / h_min

        xp = self._xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._eps_local = _eps_local_kernel(self._h_field, self._eps_scale, self._eps_xi)
        self._dV = grid.cell_volumes()

        self._extractor = RidgeExtractor(
            backend, grid, sigma_0=sigma_0, h_ref=self._h_ref,
            wall_closure=self._wall_closure,
            wall_axes=self._wall_axes,
        )
        self._fmm = NonUniformFMM(grid, backend=backend)

    def update_grid(self, grid) -> None:
        self._grid = grid
        xp = self._xp
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        self._eps_xi = self._eps / h_min
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._eps_local = _eps_local_kernel(self._h_field, self._eps_scale, self._eps_xi)
        self._dV = grid.cell_volumes()
        self._extractor.update_grid(grid)
        self._fmm.update_grid(grid)

    def set_wall_contacts(self, wall_contacts) -> None:
        """Attach no-slip wall-contact constraints in physical coordinates."""
        self._wall_contacts = wall_contacts or WallContactSet.empty()

    def reinitialize(self, psi):
        xp = self._xp
        psi = xp.asarray(psi)
        dV = self._dV
        M_old = xp.sum(psi * dV)

        phi = invert_heaviside(xp, psi, self._eps_local)
        pinned_points = self._wall_contacts.physical_points(self._grid)
        xi_ridge = self._extractor.compute_xi_ridge(phi, extra_points=pinned_points)
        ridge_mask = self._extractor.extract_ridge_mask(xi_ridge)
        contact_seeds = self._wall_contacts.nearest_node_seeds(self._grid)

        if self._backend.is_gpu():
            phi_sdf = self._fmm.solve(
                phi,
                ridge_mask=ridge_mask,
                h_min=self._h_min,
                extra_seeds=contact_seeds,
            )
        else:
            extra_seeds = list(contact_seeds)
            phi_np = np.asarray(phi)
            mask_np = np.asarray(ridge_mask)
            if np.any(mask_np):
                ii, jj = np.where(mask_np)
                on_interface = np.abs(phi_np[ii, jj]) < 0.5 * self._h_min
                if np.any(on_interface):
                    iis = ii[on_interface]
                    jjs = jj[on_interface]
                    extra_seeds.extend(
                        (int(iis[k]), int(jjs[k]), 0.0) for k in range(len(iis))
                    )

            phi_sdf_np = self._fmm.solve(phi_np, extra_seeds=extra_seeds)
            phi_sdf = xp.asarray(phi_sdf_np)
        psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)
        psi_new = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi_new)

        if self._mass_correction:
            w = psi_new * (1.0 - psi_new) / self._eps_local
            if self._wall_contacts:
                constrained_band = self._wall_contacts.constraint_mask(
                    xp,
                    self._grid,
                    tuple(psi_new.shape),
                    band_width=2.0 * self._h_min,
                )
            else:
                constrained_band = self._wall_contact_band(phi, phi_sdf)
            free_mask = xp.where(constrained_band, 0.0, 1.0)
            w = w * free_mask
            W = xp.sum(w * dV)
            W_safe = xp.where(W > 1e-14, W, 1.0)
            gate = xp.where(W > 1e-14, 1.0, 0.0)
            M_new = xp.sum(psi_new * dV)
            delta_phi = gate * (M_old - M_new) / W_safe
            phi_sdf = phi_sdf + delta_phi * free_mask
            psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)
            psi_new = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi_new)

        return psi_new

    def _wall_contact_band(self, phi_raw, phi_sdf):
        """Return a mask that pins wall-contact seeds during mass correction."""
        xp = self._xp
        if not self._wall_closure:
            return xp.zeros_like(phi_sdf, dtype=bool)
        phi_raw = xp.asarray(phi_raw)
        phi_sdf = xp.asarray(phi_sdf)
        contact_band = xp.zeros_like(phi_sdf, dtype=bool)
        tol = max(1.0e-12, 1.0e-10 * self._h_min)
        band_width = 2.0 * self._h_min
        near_interface = xp.abs(phi_sdf) <= band_width

        left_trace = phi_raw[0, :]
        right_trace = phi_raw[-1, :]
        bottom_trace = phi_raw[:, 0]
        top_trace = phi_raw[:, -1]
        left_contact = xp.any(left_trace[:-1] * left_trace[1:] <= 0.0) | xp.any(xp.abs(left_trace) <= tol)
        right_contact = xp.any(right_trace[:-1] * right_trace[1:] <= 0.0) | xp.any(xp.abs(right_trace) <= tol)
        bottom_contact = xp.any(bottom_trace[:-1] * bottom_trace[1:] <= 0.0) | xp.any(xp.abs(bottom_trace) <= tol)
        top_contact = xp.any(top_trace[:-1] * top_trace[1:] <= 0.0) | xp.any(xp.abs(top_trace) <= tol)

        left_flag = xp.asarray(left_contact, dtype=phi_sdf.dtype)
        right_flag = xp.asarray(right_contact, dtype=phi_sdf.dtype)
        bottom_flag = xp.asarray(bottom_contact, dtype=phi_sdf.dtype)
        top_flag = xp.asarray(top_contact, dtype=phi_sdf.dtype)

        contact_weight = xp.zeros_like(phi_sdf)
        contact_weight[0:2, :] = xp.maximum(contact_weight[0:2, :], left_flag)
        contact_weight[-2:, :] = xp.maximum(contact_weight[-2:, :], right_flag)
        contact_weight[:, 0:2] = xp.maximum(contact_weight[:, 0:2], bottom_flag)
        contact_weight[:, -2:] = xp.maximum(contact_weight[:, -2:], top_flag)
        contact_band = (contact_weight > 0.0) & near_interface
        return contact_band
