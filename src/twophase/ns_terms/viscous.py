"""
Viscous term: (1/Re) ∇·[μ̃ (∇u + ∇uᵀ)] / ρ̃.

Implements §9 of the paper.  In the non-dimensional one-fluid formulation
the full strain-rate tensor divergence is (§2.4):

    V_α = (1/Re) Σ_β ∂/∂x_β [μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α)] / ρ̃

For a nearly-incompressible flow (∇·u ≈ 0) this simplifies to:

    V_α ≈ (1/(Re ρ̃)) [∇·(μ̃ ∇u_α) + Σ_β ∂/∂x_β (μ̃ ∂u_β/∂x_α)]

which is what is implemented here.

Crank-Nicolson (CN) half-implicit treatment (§9, ``cn_viscous=True``):

The CN scheme requires solving for u* implicitly:

    ρ (u* − uⁿ) / Δt = ½ V(u*) + ½ V(uⁿ) + explicit_terms

Rearranging for each component α:

    [ρ/Δt − ½ V_lin] u*_α = ρ uⁿ_α / Δt + ½ V(uⁿ)_α + explicit

where V_lin u_α = (1/Re) ∇·(μ̃ ∇u_α) is the linear part.

The non-linear cross-term Σ_{β≠α} ∂/∂x_β (μ̃ ∂u_β/∂x_α) is treated
explicitly at time n for simplicity (standard practice).

When ``cn_viscous=False`` the term is evaluated explicitly and simply
returned as an array.
"""

from __future__ import annotations
import numpy as np
from typing import List, Optional, TYPE_CHECKING

from .interfaces import INSTerm

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend
    from ..time_integration.cn_advance import ICNAdvance
    from .context import NSComputeContext


class ViscousTerm(INSTerm):
    """Compute the viscous stress divergence.

    Parameters
    ----------
    backend    : Backend
    Re         : Reynolds number
    cn_viscous : If True, use the CN strategy via ``cn_advance``.
                 If False, the caller is expected to use ``compute_explicit``
                 directly (see ``ns_terms/predictor.py``).
    spatial_scheme : Spatial operator for the stress-divergence body.
                 ``ccd``/``ccd_bulk`` uses CCD for Layer-A velocity gradients and
                 low-order physical-coordinate stress divergence.
                 ``conservative_stress`` uses low-order gradients everywhere.
                 ``ccd_stress_legacy`` preserves the old all-CCD
                 stress/divergence path.
    cn_advance : CN time-advance strategy (Strategy pattern). When None,
                 defaults to ``PicardCNAdvance`` — the canonical production
                 behaviour. See ``cn_advance/`` subpackage and
                 ``docs/memo/extended_cn_impl_design.md``.
    """

    def __init__(
        self,
        backend: "Backend",
        Re: float,
        cn_viscous: bool = True,
        spatial_scheme: str = "ccd_bulk",
        cn_advance: Optional["ICNAdvance"] = None,
    ):
        self.xp = backend.xp
        self.Re = Re
        self.cn_viscous = cn_viscous
        self.spatial_scheme = self._canonical_spatial_scheme(spatial_scheme)
        # Lazy import breaks the cn_advance -> viscous typing cycle.
        if cn_advance is None:
            from ..time_integration.cn_advance import PicardCNAdvance
            cn_advance = PicardCNAdvance(backend)
        self.cn_advance = cn_advance

    # ── INSTerm interface ────────────────────────────────────────────────

    def compute(self, ctx: "NSComputeContext") -> List:
        """Compute viscous term via explicit evaluation (Interface implementation).

        Parameters
        ----------
        ctx : NSComputeContext
            Context with velocity, ccd, rho, mu

        Returns
        -------
        List[ndarray]
            Viscous stress per velocity component
        """
        return self.compute_explicit(ctx.velocity, ctx.mu, ctx.rho, ctx.ccd)

    # ── Explicit evaluation ───────────────────────────────────────────────

    def compute_explicit(
        self,
        velocity_components: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        psi=None,
    ) -> List:
        """Return V_α = (1/Re) ∇·[μ̃ (∇u + ∇uᵀ)] / ρ̃ evaluated at current u.

        Parameters
        ----------
        velocity_components : [u, v[, w]]
        mu                  : dynamic viscosity field
        rho                 : density field
        ccd                 : CCDSolver

        Returns
        -------
        visc : list of arrays, one per velocity component
        """
        return self._evaluate(velocity_components, mu, rho, ccd, psi=psi)

    # ── Crank-Nicolson predictor step ─────────────────────────────────────

    def apply_cn_predictor(
        self,
        u_old: List,
        explicit_rhs: List,
        mu: "array",
        rho: "array",
        ccd: "CCDSolver",
        dt: float,
        psi=None,
    ) -> List:
        """Delegate the viscous predictor advance to ``self.cn_advance``.

        The strategy pattern separates the *operator* V(u) (owned here) from
        the *temporal discretization* (owned by the strategy). See
        ``cn_advance/`` subpackage for available strategies and
        ``docs/memo/extended_cn_impl_design.md`` for rationale.

        When ``self.cn_viscous`` is False this method falls back to a plain
        forward-Euler step — preserved for API completeness though the
        production caller in ``ns_terms/predictor.py`` guards the CN branch
        on ``config.numerics.cn_viscous`` and so never triggers the fallback
        via this entrypoint.
        """
        if not self.cn_viscous:
            # Dead fast-path: explicit Euler using V(u^n). Bit-exact with
            # the pre-Phase-1 behaviour.
            visc_n = self._evaluate(u_old, mu, rho, ccd)
            return [
                u_old[c] + dt * (explicit_rhs[c] / rho + visc_n[c])
                for c in range(len(u_old))
            ]
        return self.cn_advance.advance(
            u_old, explicit_rhs, mu, rho, self, ccd, dt, psi=psi,
        )

    # ── Core evaluation ───────────────────────────────────────────────────

    @staticmethod
    def _canonical_spatial_scheme(name: str) -> str:
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

    def _axis_spacing(self, ccd: "CCDSolver", axis: int):
        coords = self.xp.asarray(ccd.grid.coords[axis])
        return coords[1:] - coords[:-1]

    def _low_order_derivative(self, data, axis: int, ccd: "CCDSolver"):
        """Second-order interior / one-sided boundary derivative in physical x."""
        xp = self.xp
        arr = xp.asarray(data)
        deriv = xp.empty_like(arr)
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
        """Compute Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)]/∂x_β for one α."""
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta,  _ = ccd.differentiate(vel[alpha], beta)
            du_b_dalpha, _ = ccd.differentiate(vel[beta],  alpha)
            stress,          _ = ccd.differentiate(mu * (du_a_dbeta + du_b_dalpha), beta)
            total += stress
        return total

    def _stress_divergence_component_conservative(
        self,
        alpha: int,
        vel: List,
        mu,
        ccd: "CCDSolver",
    ):
        """Low-order conservative stress-divergence body for variable μ."""
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
        """CCD Layer-A gradients with low-order conservative stress divergence."""
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta, _ = ccd.differentiate(vel[alpha], beta)
            du_b_dalpha, _ = ccd.differentiate(vel[beta], alpha)
            stress = mu * (du_a_dbeta + du_b_dalpha)
            total += self._low_order_derivative(stress, beta, ccd)
        return total

    def _bulk_laplacian_component(self, component, mu, ccd: "CCDSolver"):
        """Cheap bulk path μ Δ_CCD u using CCD second derivatives directly."""
        lap = self.xp.zeros_like(component)
        for axis in range(ccd.ndim):
            _, d2 = ccd.differentiate(component, axis)
            lap += d2
        return mu * lap

    def _axis_derivative_with_normal_fallback(
        self,
        data,
        axis: int,
        ccd: "CCDSolver",
        normal_axis_masks: list,
    ):
        """CCD tangential derivative with low-order fallback on normal-like axis."""
        d_ccd, _ = ccd.differentiate(data, axis)
        d_low = self._low_order_derivative(data, axis, ccd)
        return self.xp.where(normal_axis_masks[axis], d_low, d_ccd)

    def _interface_band_mask(self, psi):
        xp = self.xp
        p = xp.asarray(psi)
        band = (p > 1.0e-6) & (p < 1.0 - 1.0e-6)
        for axis in range(p.ndim):
            base = xp.copy(band)
            lo = [slice(None)] * p.ndim
            hi = [slice(None)] * p.ndim
            lo[axis] = slice(1, None)
            hi[axis] = slice(None, -1)
            band[tuple(lo)] = band[tuple(lo)] | base[tuple(hi)]
            band[tuple(hi)] = band[tuple(hi)] | base[tuple(lo)]
        return band

    def _normal_axis_masks(self, psi, ccd: "CCDSolver"):
        xp = self.xp
        p = xp.asarray(psi)
        gradients = [self._low_order_derivative(p, axis, ccd) for axis in range(p.ndim)]
        abs_grads = [xp.abs(g) for g in gradients]
        max_grad = abs_grads[0]
        for g in abs_grads[1:]:
            max_grad = xp.maximum(max_grad, g)
        masks = []
        for g in abs_grads:
            masks.append((g >= max_grad) & (max_grad > 1.0e-14))
        flat = max_grad <= 1.0e-14
        masks = [m | flat for m in masks]
        return masks

    def _stress_divergence_component_normal_tangent(
        self,
        alpha: int,
        vel: List,
        mu,
        ccd: "CCDSolver",
        normal_axis_masks: list,
    ):
        """Interface-band stress form: normal-like derivatives low-order, tangent CCD."""
        total = self.xp.zeros_like(vel[alpha])
        for beta in range(len(vel)):
            du_a_dbeta = self._axis_derivative_with_normal_fallback(
                vel[alpha], beta, ccd, normal_axis_masks
            )
            du_b_dalpha = self._axis_derivative_with_normal_fallback(
                vel[beta], alpha, ccd, normal_axis_masks
            )
            stress = mu * (du_a_dbeta + du_b_dalpha)
            total += self._axis_derivative_with_normal_fallback(
                stress, beta, ccd, normal_axis_masks
            )
        return total

    def _evaluate(self, vel: List, mu, rho, ccd: "CCDSolver", psi=None) -> List:
        """Compute ∇·[μ̃ (∇u + ∇uᵀ)] / (ρ̃ Re) for each component.

        Symmetric stress tensor S_{αβ} = μ̃ (∂u_α/∂x_β + ∂u_β/∂x_α) / 2
        Viscous force per unit volume for component α:
            V_α = (1/Re) Σ_β ∂[μ̃(∂u_α/∂x_β + ∂u_β/∂x_α)] / ∂x_β / ρ̃
        """
        ndim = len(vel)
        if self.spatial_scheme == "ccd_stress_legacy":
            return [
                self._stress_divergence_component_legacy(alpha, vel, mu, ccd)
                / (self.Re * rho)
                for alpha in range(ndim)
            ]
        if self.spatial_scheme == "ccd_bulk":
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
