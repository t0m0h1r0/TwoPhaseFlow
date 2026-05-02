"""Spatial viscous-stress helpers used by ``ViscousTerm``."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver


def canonical_viscous_spatial_scheme(name: str) -> str:
    aliases = {
        "stress_divergence": "conservative_stress",
        "low_order_conservative": "conservative_stress",
        "ccd": "ccd_bulk",
        "ccd_legacy": "ccd_stress_legacy",
    }
    canonical = aliases.get(str(name).strip().lower(), str(name).strip().lower())
    if canonical not in {"conservative_stress", "ccd_bulk", "ccd_stress_legacy"}:
        raise ValueError(
            "viscous spatial scheme must be one of "
            "'conservative_stress', 'ccd_bulk', or 'ccd_stress_legacy', "
            f"got {name!r}"
        )
    return canonical


class ViscousSpatialEvaluator:
    """Evaluate viscous stress-divergence bodies for the selected scheme."""

    def __init__(self, xp, reynolds_number: float):
        self.xp = xp
        self.Re = reynolds_number

    def evaluate(
        self,
        spatial_scheme: str,
        vel: List,
        mu,
        rho,
        ccd: "CCDSolver",
        psi=None,
    ) -> List:
        ndim = len(vel)
        if spatial_scheme == "ccd_stress_legacy":
            return [
                self._stress_divergence_component_legacy(alpha, vel, mu, ccd)
                / (self.Re * rho)
                for alpha in range(ndim)
            ]
        if spatial_scheme == "ccd_bulk":
            if psi is not None:
                band = self._interface_band_mask(psi)
                normal_axis_masks = self._normal_axis_masks(psi, ccd)
                return [
                    self.xp.where(
                        band,
                        self._stress_divergence_component_normal_tangent(
                            alpha, vel, mu, ccd, normal_axis_masks
                        ),
                        self._bulk_laplacian_component(vel[alpha], mu, ccd),
                    )
                    / (self.Re * rho)
                    for alpha in range(ndim)
                ]
            return [
                self._stress_divergence_component_ccd_bulk(alpha, vel, mu, ccd)
                / (self.Re * rho)
                for alpha in range(ndim)
            ]
        return [
            self._stress_divergence_component_conservative(alpha, vel, mu, ccd)
            / (self.Re * rho)
            for alpha in range(ndim)
        ]

    def _axis_spacing(self, ccd: "CCDSolver", axis: int):
        coords = self.xp.asarray(ccd.grid.coords[axis])
        return coords[1:] - coords[:-1]

    def _low_order_derivative(self, data, axis: int, ccd: "CCDSolver"):
        arr = self.xp.asarray(data)
        deriv = self.xp.empty_like(arr)
        dx = self._axis_spacing(ccd, axis)
        n_pts = arr.shape[axis]

        lo = [slice(None)] * arr.ndim
        hi = [slice(None)] * arr.ndim
        lo[axis] = 0
        hi[axis] = 1
        deriv[tuple(lo)] = (arr[tuple(hi)] - arr[tuple(lo)]) / dx[0]

        lo[axis] = n_pts - 2
        hi[axis] = n_pts - 1
        deriv[tuple(hi)] = (arr[tuple(hi)] - arr[tuple(lo)]) / dx[-1]

        center = [slice(None)] * arr.ndim
        left = [slice(None)] * arr.ndim
        right = [slice(None)] * arr.ndim
        center[axis] = slice(1, n_pts - 1)
        left[axis] = slice(0, n_pts - 2)
        right[axis] = slice(2, n_pts)

        shape = [1] * arr.ndim
        shape[axis] = n_pts - 2
        h_l = dx[:-1].reshape(shape)
        h_r = dx[1:].reshape(shape)
        f_l = arr[tuple(left)]
        f_c = arr[tuple(center)]
        f_r = arr[tuple(right)]

        deriv[tuple(center)] = (
            -(h_r / (h_l * (h_l + h_r))) * f_l
            + ((h_r - h_l) / (h_l * h_r)) * f_c
            + (h_l / (h_r * (h_l + h_r))) * f_r
        )
        return deriv

    def _stress_divergence_component_legacy(self, alpha: int, vel: List, mu, ccd: "CCDSolver"):
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta = ccd.first_derivative(vel[alpha], beta)
            du_b_dalpha = ccd.first_derivative(vel[beta], alpha)
            stress = ccd.first_derivative(mu * (du_a_dbeta + du_b_dalpha), beta)
            total += stress
        return total

    def _stress_divergence_component_conservative(
        self,
        alpha: int,
        vel: List,
        mu,
        ccd: "CCDSolver",
    ):
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta = self._low_order_derivative(vel[alpha], beta, ccd)
            du_b_dalpha = self._low_order_derivative(vel[beta], alpha, ccd)
            stress = mu * (du_a_dbeta + du_b_dalpha)
            total += self._low_order_derivative(stress, beta, ccd)
        return total

    def _stress_divergence_component_ccd_bulk(
        self,
        alpha: int,
        vel: List,
        mu,
        ccd: "CCDSolver",
    ):
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta = ccd.first_derivative(vel[alpha], beta)
            du_b_dalpha = ccd.first_derivative(vel[beta], alpha)
            stress = mu * (du_a_dbeta + du_b_dalpha)
            total += self._low_order_derivative(stress, beta, ccd)
        return total

    def _bulk_laplacian_component(self, component, mu, ccd: "CCDSolver"):
        lap = self.xp.zeros_like(component)
        for axis in range(ccd.ndim):
            lap += ccd.second_derivative(component, axis)
        return mu * lap

    def _axis_derivative_with_interface_switch(
        self,
        data,
        axis: int,
        ccd: "CCDSolver",
        normal_axis_masks: list,
    ):
        d_ccd = ccd.first_derivative(data, axis)
        d_low = self._low_order_derivative(data, axis, ccd)
        return self.xp.where(normal_axis_masks[axis], d_low, d_ccd)

    def _interface_band_mask(self, psi):
        p = self.xp.asarray(psi)
        band = (p > 1.0e-6) & (p < 1.0 - 1.0e-6)
        for axis in range(p.ndim):
            base = self.xp.copy(band)
            lo = [slice(None)] * p.ndim
            hi = [slice(None)] * p.ndim
            lo[axis] = slice(1, None)
            hi[axis] = slice(None, -1)
            band[tuple(lo)] = band[tuple(lo)] | base[tuple(hi)]
            band[tuple(hi)] = band[tuple(hi)] | base[tuple(lo)]
        return band

    def _normal_axis_masks(self, psi, ccd: "CCDSolver"):
        p = self.xp.asarray(psi)
        gradients = [self._low_order_derivative(p, axis, ccd) for axis in range(p.ndim)]
        abs_grads = [self.xp.abs(g) for g in gradients]
        max_grad = abs_grads[0]
        for g in abs_grads[1:]:
            max_grad = self.xp.maximum(max_grad, g)
        masks = []
        for g in abs_grads:
            masks.append((g >= max_grad) & (max_grad > 1.0e-14))
        flat = max_grad <= 1.0e-14
        return [m | flat for m in masks]

    def _stress_divergence_component_normal_tangent(
        self,
        alpha: int,
        vel: List,
        mu,
        ccd: "CCDSolver",
        normal_axis_masks: list,
    ):
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta = self._axis_derivative_with_interface_switch(
                vel[alpha], beta, ccd, normal_axis_masks
            )
            du_b_dalpha = self._axis_derivative_with_interface_switch(
                vel[beta], alpha, ccd, normal_axis_masks
            )
            stress = mu * (du_a_dbeta + du_b_dalpha)
            total += self._axis_derivative_with_interface_switch(
                stress, beta, ccd, normal_axis_masks
            )
        return total
