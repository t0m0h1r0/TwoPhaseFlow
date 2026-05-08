"""Ridge-eikonal reinitializer orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from ..coupling.closed_interface_geometry import liquid_area_2d
from .heaviside import invert_heaviside
from .interfaces import IReinitializer
from .ridge_eikonal_extractor import RidgeExtractor
from .ridge_eikonal_fmm import NonUniformFMM
from .ridge_eikonal_kernels import _eps_local_kernel, _sigmoid_xp
from .wall_contact import WallContactSet
from ..core.boundary import boundary_axes, sync_periodic_image_nodes

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
        ridge_zero_seeds: bool = False,
        volume_constraint: str = "diffuse_mass",
    ):
        self._xp = backend.xp
        self._backend = backend
        self._grid = grid
        self._ccd = ccd
        self._eps = float(eps)
        self._eps_scale = float(eps_scale)
        self._mass_correction = mass_correction
        self._volume_constraint = _canonical_volume_constraint(volume_constraint)
        self._ridge_zero_seeds = bool(ridge_zero_seeds)
        self._bc_axes = boundary_axes(getattr(ccd, "bc_type", "wall"), grid.ndim)
        self._wall_axes = tuple(axis == "wall" for axis in self._bc_axes)
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
            ccd=ccd,
        )
        self._fmm = NonUniformFMM(grid, backend=backend)

    @property
    def preserves_sharp_volume(self) -> bool:
        """Whether reinitialization applies a sharp P1 phase-volume constraint."""
        return self._mass_correction and self._volume_constraint == "sharp_phase_volume"

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

    def _axis_wall(self, axis: int) -> bool:
        return axis < len(self._wall_axes) and self._wall_axes[axis]

    def reinitialize(self, psi):
        xp = self._xp
        psi = xp.asarray(psi)
        sync_periodic_image_nodes(psi, self._bc_axes)
        dV = self._dV
        M_old = xp.sum(psi * dV)
        V_old = None
        if self.preserves_sharp_volume:
            V_old = self._sharp_phase_volume(psi)

        phi = invert_heaviside(xp, psi, self._eps_local)
        sync_periodic_image_nodes(phi, self._bc_axes)
        pinned_points = self._wall_contacts.physical_points(self._grid)
        ridge_mask = None
        if self._ridge_zero_seeds:
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
            if ridge_mask is not None:
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
        sync_periodic_image_nodes(phi_sdf, self._bc_axes)
        psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)
        psi_new = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi_new)
        sync_periodic_image_nodes(psi_new, self._bc_axes)

        if self._mass_correction:
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
            if self._volume_constraint == "sharp_phase_volume":
                phi_sdf, psi_new = self._apply_sharp_phase_volume_constraint(
                    phi_sdf,
                    free_mask=free_mask,
                    target_volume=V_old,
                    target_mass=M_old,
                    dV=dV,
                )
            else:
                w = psi_new * (1.0 - psi_new) / self._eps_local
                w = w * free_mask
                W = xp.sum(w * dV)
                W_safe = xp.where(W > 1e-14, W, 1.0)
                gate = xp.where(W > 1e-14, 1.0, 0.0)
                M_new = xp.sum(psi_new * dV)
                delta_phi = gate * (M_old - M_new) / W_safe
                phi_sdf = phi_sdf + delta_phi * free_mask
                sync_periodic_image_nodes(phi_sdf, self._bc_axes)
                psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)
                psi_new = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi_new)
                sync_periodic_image_nodes(psi_new, self._bc_axes)

        return psi_new

    def _psi_from_shifted_phi(
        self,
        phi_sdf,
        delta_phi,
        free_mask,
        *,
        profile_scale: float = 1.0,
    ):
        xp = self._xp
        eps_profile = self._eps_local * float(profile_scale)
        psi = _sigmoid_xp(xp, phi_sdf + float(delta_phi) * free_mask, eps_profile)
        psi = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi)
        sync_periodic_image_nodes(psi, self._bc_axes)
        return psi

    def _sharp_phase_volume(self, psi) -> float:
        value = liquid_area_2d(
            xp=self._xp,
            grid=self._grid,
            psi=psi,
            phase_threshold=0.5,
        )
        if hasattr(value, "get"):
            value = value.get()
        return float(value)

    def _can_measure_shifted_phi_volume(self) -> bool:
        """Return whether ``V_h`` can be measured directly from shifted phi."""
        return bool(
            self._backend.is_gpu()
            and not self._wall_closure
            and not self._wall_contacts
        )

    def _sharp_phase_volume_from_shifted_phi(
        self,
        phi_sdf,
        delta_phi: float,
        free_mask,
    ) -> float:
        """Measure ``V_h`` using ``phi=0`` instead of materialising ``psi``."""
        phi_shifted = self._xp.asarray(phi_sdf) + float(delta_phi) * self._xp.asarray(
            free_mask
        )
        value = liquid_area_2d(
            xp=self._xp,
            grid=self._grid,
            psi=phi_shifted,
            phase_threshold=0.0,
        )
        return self._scalar_float(value)

    def _apply_sharp_phase_volume_constraint(
        self,
        phi_sdf,
        *,
        free_mask,
        target_volume: float | None,
        target_mass,
        dV,
    ):
        """Apply the Lagrange multiplier shift enforcing ``V_Gamma``.

        A constant signed-distance shift is the discrete volume multiplier for
        the fixed-topology reinitialization projection: it preserves
        ``|grad(phi)|=1`` away from explicitly pinned wall-contact bands while
        solving the sharp P1 constraint ``V_h(phi + lambda)=V_target``.  A
        second scalar profile-width multiplier then restores the diffuse CLS
        mass without moving that zero level.
        """
        xp = self._xp
        if target_volume is None:
            raise ValueError("sharp phase-volume correction requires a target volume")
        target = float(target_volume)
        domain_volume = float(np.prod(self._grid.L))
        tol = max(1.0e-12, 1.0e-10 * max(domain_volume, 1.0))
        phi_volume_fast_path = self._can_measure_shifted_phi_volume()
        if phi_volume_fast_path:
            psi_zero = None
            volume_zero = self._sharp_phase_volume_from_shifted_phi(
                phi_sdf,
                0.0,
                free_mask,
            )
        else:
            psi_zero = self._psi_from_shifted_phi(phi_sdf, 0.0, free_mask)
            volume_zero = self._sharp_phase_volume(psi_zero)
        if abs(volume_zero - target) <= tol:
            psi_zero = self._apply_diffuse_mass_profile_constraint(
                phi_sdf,
                target_mass=target_mass,
                dV=dV,
            )
            return phi_sdf, psi_zero
        if target < -tol or target > domain_volume + tol:
            raise ValueError(
                "sharp phase-volume target is outside domain volume: "
                f"target={target:.16e}, domain={domain_volume:.16e}"
            )
        direction = 1.0 if volume_zero < target else -1.0
        lo = 0.0
        hi = max(self._h_min, 1.0e-12) * direction
        max_shift = max(float(max(self._grid.L)), self._h_min)
        for _ in range(40):
            if phi_volume_fast_path:
                volume_hi = self._sharp_phase_volume_from_shifted_phi(
                    phi_sdf,
                    hi,
                    free_mask,
                )
            else:
                volume_hi = self._sharp_phase_volume(
                    self._psi_from_shifted_phi(phi_sdf, hi, free_mask)
                )
            if (direction > 0.0 and volume_hi >= target - tol) or (
                direction < 0.0 and volume_hi <= target + tol
            ):
                break
            hi *= 2.0
            if abs(hi) > max_shift:
                raise ValueError(
                    "failed to bracket sharp phase-volume correction: "
                    f"target={target:.16e}, V0={volume_zero:.16e}, "
                    f"last_shift={hi:.16e}"
                )
        else:
            raise ValueError("failed to bracket sharp phase-volume correction")

        left = min(lo, hi)
        right = max(lo, hi)
        psi_mid = psi_zero
        mid = 0.0
        for _ in range(48):
            mid = 0.5 * (left + right)
            if phi_volume_fast_path:
                volume_mid = self._sharp_phase_volume_from_shifted_phi(
                    phi_sdf,
                    mid,
                    free_mask,
                )
            else:
                psi_mid = self._psi_from_shifted_phi(phi_sdf, mid, free_mask)
                volume_mid = self._sharp_phase_volume(psi_mid)
            if abs(volume_mid - target) <= tol:
                break
            if volume_mid < target:
                left = mid
            else:
                right = mid
        phi_shifted = phi_sdf + float(mid) * free_mask
        sync_periodic_image_nodes(phi_shifted, self._bc_axes)
        psi_mid = self._apply_diffuse_mass_profile_constraint(
            phi_shifted,
            target_mass=target_mass,
            dV=dV,
        )
        return phi_shifted, psi_mid

    def _apply_diffuse_mass_profile_constraint(self, phi_sdf, *, target_mass, dV):
        """Restore ``sum psi*dV`` by changing profile width, not zero level."""
        xp = self._xp
        target = self._scalar_float(target_mass)
        dV = xp.asarray(dV)
        tol = max(1.0e-12, 1.0e-10 * max(abs(target), 1.0))

        def psi_at(scale: float):
            psi = _sigmoid_xp(xp, phi_sdf, self._eps_local * float(scale))
            psi = self._wall_contacts.impose_on_wall_trace(xp, self._grid, psi)
            sync_periodic_image_nodes(psi, self._bc_axes)
            return psi

        def residual(scale: float) -> tuple[float, object]:
            psi = psi_at(scale)
            mass = self._scalar_float(xp.sum(psi * dV))
            return mass - target, psi

        residual_one, psi_one = residual(1.0)
        if abs(residual_one) <= tol:
            return psi_one

        scales = [
            1.0 / 16.0,
            1.0 / 12.0,
            1.0 / 8.0,
            1.0 / 6.0,
            1.0 / 4.0,
            1.0 / 3.0,
            1.0 / 2.0,
            2.0 / 3.0,
            1.5,
            2.0,
            3.0,
            4.0,
            6.0,
            8.0,
            12.0,
            16.0,
        ]
        samples: list[tuple[float, float]] = [(1.0, residual_one)]
        for scale in scales:
            value, psi_candidate = residual(scale)
            if abs(value) <= tol:
                return psi_candidate
            samples.append((scale, value))
        samples.sort(key=lambda item: item[0])

        bracket = None
        for left, right in zip(samples[:-1], samples[1:]):
            if left[1] * right[1] < 0.0:
                bracket = (left[0], left[1], right[0])
                break
        if bracket is None:
            raise ValueError(
                "failed to bracket diffuse-mass profile correction without "
                "moving the sharp interface"
            )

        left, value_left, right = bracket
        psi_mid = psi_one
        for _ in range(48):
            mid = 0.5 * (left + right)
            value_mid, psi_mid = residual(mid)
            if abs(value_mid) <= tol:
                return psi_mid
            if value_left * value_mid <= 0.0:
                right = mid
            else:
                left = mid
                value_left = value_mid
        return psi_mid

    @staticmethod
    def _scalar_float(value) -> float:
        if hasattr(value, "get"):
            value = value.get()
        return float(value)

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

        left_contact = right_contact = False
        bottom_contact = top_contact = False
        if self._axis_wall(0):
            left_trace = phi_raw[0, :]
            right_trace = phi_raw[-1, :]
            left_contact = xp.any(left_trace[:-1] * left_trace[1:] <= 0.0) | xp.any(xp.abs(left_trace) <= tol)
            right_contact = xp.any(right_trace[:-1] * right_trace[1:] <= 0.0) | xp.any(xp.abs(right_trace) <= tol)
        if self._axis_wall(1):
            bottom_trace = phi_raw[:, 0]
            top_trace = phi_raw[:, -1]
            bottom_contact = xp.any(bottom_trace[:-1] * bottom_trace[1:] <= 0.0) | xp.any(xp.abs(bottom_trace) <= tol)
            top_contact = xp.any(top_trace[:-1] * top_trace[1:] <= 0.0) | xp.any(xp.abs(top_trace) <= tol)

        left_flag = xp.asarray(left_contact, dtype=phi_sdf.dtype)
        right_flag = xp.asarray(right_contact, dtype=phi_sdf.dtype)
        bottom_flag = xp.asarray(bottom_contact, dtype=phi_sdf.dtype)
        top_flag = xp.asarray(top_contact, dtype=phi_sdf.dtype)

        contact_weight = xp.zeros_like(phi_sdf)
        if self._axis_wall(0):
            contact_weight[0:2, :] = xp.maximum(contact_weight[0:2, :], left_flag)
            contact_weight[-2:, :] = xp.maximum(contact_weight[-2:, :], right_flag)
        if self._axis_wall(1):
            contact_weight[:, 0:2] = xp.maximum(contact_weight[:, 0:2], bottom_flag)
            contact_weight[:, -2:] = xp.maximum(contact_weight[:, -2:], top_flag)
        contact_band = (contact_weight > 0.0) & near_interface
        return contact_band


def _canonical_volume_constraint(value: str) -> str:
    normalized = str(value).strip().lower().replace("-", "_")
    aliases = {
        "diffuse": "diffuse_mass",
        "diffuse_mass": "diffuse_mass",
        "psi_mass": "diffuse_mass",
        "sharp": "sharp_phase_volume",
        "sharp_area": "sharp_phase_volume",
        "sharp_volume": "sharp_phase_volume",
        "sharp_phase_area": "sharp_phase_volume",
        "sharp_phase_volume": "sharp_phase_volume",
    }
    if normalized not in aliases:
        raise ValueError(
            "ridge_eikonal volume_constraint must be "
            "'diffuse_mass' or 'sharp_phase_volume', "
            f"got {value!r}"
        )
    return aliases[normalized]
