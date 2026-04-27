"""Concrete viscous predictor implementations.

Symbol mapping
--------------
u*, v* -> ``u_star``, ``v_star``
ρ -> ``rho``
μ -> ``mu``
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING

from ..core.array_checks import all_arrays_exact_zero
from ..ppe.gmres_helpers import backend_supports_gmres, solve_gmres
from .viscous_predictor import IViscousPredictor

IMPLICIT_BDF2_PROJECTION_FACTOR = 2.0 / 3.0

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver
    from ..ns_terms.viscous import ViscousTerm
    from .scheme_build_ctx import ViscousBuildCtx


class ExplicitViscousPredictor(IViscousPredictor):
    """Forward-Euler explicit viscous predictor, O(Δt)."""

    scheme_names = ("explicit", "forward_euler")

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "ExplicitViscousPredictor":
        return cls(ctx.backend, ctx.re, ctx.spatial_scheme, ctx.viscous_term)

    def __init__(
        self,
        backend: "Backend",
        Re: float,
        spatial_scheme: str = "ccd_bulk",
        viscous_term: "ViscousTerm | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.Re = Re
        if viscous_term is None:
            from ..ns_terms.viscous import ViscousTerm

            viscous_term = ViscousTerm(
                backend,
                Re=Re,
                cn_viscous=False,
                spatial_scheme=spatial_scheme,
            )
        self._viscous = viscous_term

    def predict(
        self,
        u: "array",
        v: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
        intermediate_velocity_operator_transform: Callable[[list], None] | None = None,
        predictor_state_assembly: Callable[..., list] | None = None,
    ) -> tuple["array", "array"]:
        """Explicit forward-Euler step."""
        del intermediate_velocity_operator_transform, predictor_state_assembly
        visc_u, visc_v = self._viscous.compute_explicit([u, v], mu, rho, ccd, psi=psi)

        u_star = u + dt * (conv_u + visc_u)
        if buoy_v is not None:
            v_star = v + dt * (conv_v + visc_v + buoy_v)
        else:
            v_star = v + dt * (conv_v + visc_v)

        return u_star, v_star


class CNViscousPredictor(IViscousPredictor):
    """Crank-Nicolson implicit viscous predictor, O(Δt²)."""

    scheme_names = ("crank_nicolson",)
    _scheme_aliases = {"cn": "crank_nicolson", "crank-nicolson": "crank_nicolson"}

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "CNViscousPredictor":
        return cls(ctx.backend, ctx.viscous_term)

    def __init__(self, backend: "Backend", viscous_term: "ViscousTerm") -> None:
        self.xp = backend.xp
        self._viscous = viscous_term

    def predict(
        self,
        u: "array",
        v: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
        intermediate_velocity_operator_transform: Callable[[list], None] | None = None,
        predictor_state_assembly: Callable[..., list] | None = None,
    ) -> tuple["array", "array"]:
        """CN implicit step via ``ViscousTerm.apply_cn_predictor()``."""
        explicit_rhs = [rho * conv_u, rho * (conv_v + buoy_v if buoy_v is not None else conv_v)]
        convective_rhs = [rho * conv_u, rho * conv_v]
        buoyancy_rhs = [
            self.xp.zeros_like(conv_u),
            rho * buoy_v if buoy_v is not None else self.xp.zeros_like(conv_v),
        ]
        vel_star = self._viscous.apply_cn_predictor(
            [u, v],
            explicit_rhs,
            mu,
            rho,
            ccd,
            dt,
            psi=psi,
            intermediate_velocity_operator_transform=intermediate_velocity_operator_transform,
            predictor_state_assembly=predictor_state_assembly,
            convective_rhs=convective_rhs,
            buoyancy_rhs=buoyancy_rhs,
        )
        return vel_star[0], vel_star[1]


class ImplicitBDF2ViscousPredictor(IViscousPredictor):
    """Matrix-free implicit viscous solve for BDF2 projection steps."""

    scheme_names = ("implicit_bdf2",)
    _scheme_aliases = {
        "bdf2": "implicit_bdf2",
        "imex_bdf2": "implicit_bdf2",
        "implicit-bdf2": "implicit_bdf2",
    }

    @classmethod
    def _build(cls, name: str, ctx: "ViscousBuildCtx") -> "ImplicitBDF2ViscousPredictor":
        return cls(ctx.backend, ctx.viscous_term)

    def __init__(
        self,
        backend: "Backend",
        viscous_term: "ViscousTerm",
        *,
        tolerance: float = 1.0e-8,
        max_iterations: int = 80,
        restart: int = 40,
    ) -> None:
        self.backend = backend
        self.xp = backend.xp
        self._viscous = viscous_term
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.restart = restart

    def predict(
        self,
        u: "array",
        v: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
        intermediate_velocity_operator_transform: Callable[[list], None] | None = None,
        predictor_state_assembly: Callable[..., list] | None = None,
    ) -> tuple["array", "array"]:
        """First-step backward-Euler startup for the BDF2 history."""
        del intermediate_velocity_operator_transform, predictor_state_assembly
        explicit_acceleration = self._explicit_acceleration(conv_u, conv_v, buoy_v)
        return self._solve_implicit(
            base_velocity=[u, v],
            initial_guess=[u, v],
            explicit_acceleration=explicit_acceleration,
            mu=mu,
            rho=rho,
            dt_effective=dt,
            ccd=ccd,
            psi=psi,
        )

    def predict_bdf2(
        self,
        u: "array",
        v: "array",
        u_prev: "array",
        v_prev: "array",
        conv_u: "array",
        conv_v: "array",
        mu: "array",
        rho: "array",
        dt: float,
        ccd: "CCDSolver",
        buoy_v: "array" | None = None,
        psi: "array" | None = None,
    ) -> tuple["array", "array"]:
        """Solve u* - (2/3)dt V(u*) = 4/3 uⁿ - 1/3 uⁿ⁻¹ + (2/3)dt E.

        Implements §7.3 eq:predictor_imex_bdf2 (BDF2 coefficients 4/3, -1/3, 2/3)
        and §7.4 eq:helmholtz_implicit_bdf2 (Helmholtz form, dt_effective = 2/3·dt).
        """
        base_velocity = [
            (4.0 / 3.0) * u - (1.0 / 3.0) * u_prev,
            (4.0 / 3.0) * v - (1.0 / 3.0) * v_prev,
        ]
        explicit_acceleration = self._explicit_acceleration(conv_u, conv_v, buoy_v)
        return self._solve_implicit(
            base_velocity=base_velocity,
            initial_guess=[u, v],
            explicit_acceleration=explicit_acceleration,
            mu=mu,
            rho=rho,
            dt_effective=IMPLICIT_BDF2_PROJECTION_FACTOR * dt,
            ccd=ccd,
            psi=psi,
        )

    def _explicit_acceleration(self, conv_u, conv_v, buoy_v) -> list:
        if buoy_v is None:
            return [conv_u, conv_v]
        return [conv_u, conv_v + buoy_v]

    def _solve_implicit(
        self,
        *,
        base_velocity: list,
        initial_guess: list,
        explicit_acceleration: list,
        mu,
        rho,
        dt_effective: float,
        ccd: "CCDSolver",
        psi=None,
    ) -> tuple["array", "array"]:
        linear_algebra = self.backend.sparse_linalg
        if not backend_supports_gmres(linear_algebra):
            raise RuntimeError("Implicit BDF2 viscosity requires backend-native GMRES.")

        xp = self.xp
        shape = xp.asarray(base_velocity[0]).shape
        component_size = int(xp.asarray(base_velocity[0]).size)
        mu_device = xp.asarray(mu)
        rho_device = xp.asarray(rho)
        psi_device = xp.asarray(psi) if psi is not None else None
        if (
            not self.backend.is_gpu()
            and all_arrays_exact_zero(xp, (*base_velocity, *explicit_acceleration))
        ):
            return xp.zeros_like(base_velocity[0]), xp.zeros_like(base_velocity[1])
        rhs_components = [
            xp.asarray(base_velocity[component])
            + dt_effective * xp.asarray(explicit_acceleration[component])
            for component in range(2)
        ]
        rhs_flat = self._flatten_components(rhs_components)
        initial_flat = self._flatten_components(initial_guess)
        n_dof = int(rhs_flat.size)

        def split_components(flat_array):
            flat_device = xp.asarray(flat_array)
            return [
                flat_device[:component_size].reshape(shape),
                flat_device[component_size:].reshape(shape),
            ]

        def matrix_vector(flat_array):
            velocity_components = split_components(flat_array)
            viscous_components = self._viscous._evaluate(
                velocity_components,
                mu_device,
                rho_device,
                ccd,
                psi=psi_device,
            )
            return self._flatten_components([
                velocity_components[component]
                - dt_effective * viscous_components[component]
                for component in range(2)
            ])

        operator = linear_algebra.LinearOperator(
            (n_dof, n_dof),
            matvec=matrix_vector,
            dtype=rhs_flat.dtype,
        )
        solution_flat, info = solve_gmres(
            linear_algebra,
            operator,
            rhs_flat,
            x0=initial_flat,
            preconditioner=None,
            restart=self.restart,
            maxiter=self.max_iterations,
            tolerance=self.tolerance,
        )
        if info != 0:
            raise RuntimeError(
                f"Implicit BDF2 viscous GMRES did not converge (info={info})."
            )
        solution = split_components(solution_flat)
        return solution[0], solution[1]

    def _flatten_components(self, components: list):
        return self.xp.concatenate([
            self.xp.asarray(component).ravel()
            for component in components
        ])
