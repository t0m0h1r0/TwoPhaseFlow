"""UCCD6: Sixth-order upwind combined compact difference with order-preserving
hyperviscosity.

Implements the UCCD6 scheme from SP-H / WIKI-T-062:

    ∂_t U + a · D1^CCD U + σ|a|·h^7·(-D2^CCD)^4 U = 0

where D1^CCD, D2^CCD are the Chu & Fan (1998) CCD operators obtained from
``CCDSolver.differentiate``. The hyperviscosity ``(-D2^CCD)^4`` is built by four
successive CCD differentiations — the negation cancels because the exponent is
even, so the implementation applies D2 four times directly.

Key Fourier identities (periodic BC, exact; SP-H §2):
    Symbol(D1^CCD)    = i·ω_1(θ) / h
    Symbol(D2^CCD)    = -ω_2(θ)^2 / h^2
    Symbol((-D2)^4)   = ω_2(θ)^8 / h^8          (positive semi-definite, all θ)
    Re λ(θ)           = -σ|a|·ω_2^8 / h ≤ 0     (strict L^2 dissipation)

Energy identity (SP-H §4):
    d/dt (½||U||_h^2) = -σ|a|·h^7·||(-D2^CCD)^2 U||_h^2 ≤ 0

GPU/CPU backend via ``backend.xp``; the elementwise RHS combination uses
``backend.fuse`` to collapse into a single CUDA kernel on GPU. Dispersion via
D1^CCD and hyperviscosity via four CCD calls share the same pre-factored
block-LU — each additional CCD call is O(N).

References
----------
- SP-H (``docs/memo/short_paper/SP-H_uccd6_hyperviscosity.md``)
- WIKI-T-062 (``docs/wiki/theory/WIKI-T-062.md``)
- Chu, P. C., & Fan, C. (1998). *JCP* 140, 370–399.
"""

from __future__ import annotations
from typing import Optional, TYPE_CHECKING

from .ccd_solver import CCDSolver
from ..backend import fuse as _fuse
from ..time_integration.tvd_rk3 import tvd_rk3

if TYPE_CHECKING:
    from ..core.grid import Grid
    from ..backend import Backend


# ── Fused kernel (single CUDA kernel on GPU; NumPy expression on CPU) ────


@_fuse
def _uccd6_rhs_kernel(d1, d8, neg_a, neg_sigma_abs_a_h7):
    """Fused -a·d1 - σ|a|·h^7·d8 combination.

    The RHS of ∂_t U = -Lh U is
        rhs = -a·(D1^CCD U) - σ|a|·h^7·((-D2^CCD)^4 U)
    and since (-D2)^4 = D2^4, ``d8 = D2^4 U`` can be used directly.
    """
    return neg_a * d1 + neg_sigma_abs_a_h7 * d8


# ── UCCD6 operator ───────────────────────────────────────────────────────


class UCCD6Operator:
    """Sixth-order upwind CCD with order-preserving eighth-derivative hyperviscosity.

    Discretises the linear advection operator ``Lh U = a·D1^CCD U + σ|a|·h^7·(-D2^CCD)^4 U``
    so that ``∂_t U = -Lh U`` for a scalar advection velocity ``a``.

    Parameters
    ----------
    grid : Grid
    backend : Backend
    sigma : float, default ``1.0``
        Hyperviscosity coefficient σ > 0. Larger σ damps the Nyquist mode more
        aggressively at a small smooth-mode accuracy cost; see SP-H §8 for
        calibration.
    bc_type : {"periodic", "wall"}, default ``"periodic"``
        Boundary condition mode for the underlying CCDSolver.
    ccd_solver : CCDSolver, optional
        Existing CCDSolver to share pre-factored block-LU. If ``None`` a new
        one is constructed.

    Notes
    -----
    One ``apply_rhs`` call costs four ``CCDSolver.differentiate`` solves
    (one for D1, plus three more for (D2)^2..(D2)^4) and one fused elementwise
    kernel. Each CCD call reuses the pre-factored LU and is O(N) per axis.
    """

    def __init__(
        self,
        grid: "Grid",
        backend: "Backend",
        sigma: float = 1.0,
        bc_type: str = "periodic",
        ccd_solver: Optional[CCDSolver] = None,
    ) -> None:
        if sigma <= 0.0:
            raise ValueError(f"sigma must be > 0, got {sigma}")
        if bc_type not in ("periodic", "wall"):
            raise ValueError(f"bc_type must be 'periodic' or 'wall', got {bc_type!r}")
        self.grid = grid
        self.backend = backend
        self.xp = backend.xp
        self.sigma = float(sigma)
        self.bc_type = bc_type
        self._ccd = ccd_solver if ccd_solver is not None else CCDSolver(
            grid, backend, bc_type
        )
        self._h = [float(grid.L[ax] / grid.N[ax]) for ax in range(grid.ndim)]
        self._h7 = [h ** 7 for h in self._h]

    # ── Primary API ──────────────────────────────────────────────────────

    def apply_rhs(self, u, axis: int, a: float):
        """Compute the time-derivative RHS ``-Lh U`` along ``axis``.

        Parameters
        ----------
        u : array, shape ``grid.shape``
        axis : int
            Spatial axis along which advection acts.
        a : float
            Scalar advection velocity. Used only as ``a`` (dispersion) and
            ``|a|`` (hyperviscosity strength).

        Returns
        -------
        rhs : array, shape ``grid.shape`` — ``∂_t U = rhs``.
        """
        ccd = self._ccd

        d1, d2 = ccd.differentiate(u, axis)
        _, d4 = ccd.differentiate(d2, axis)
        _, d6 = ccd.differentiate(d4, axis)
        _, d8 = ccd.differentiate(d6, axis)

        neg_a = -float(a)
        neg_sigma_abs_a_h7 = -self.sigma * abs(float(a)) * self._h7[axis]

        return _uccd6_rhs_kernel(d1, d8, neg_a, neg_sigma_abs_a_h7)

    def rk3_step(self, u, axis: int, a: float, dt: float):
        """Advance ``u`` by one TVD-RK3 step of ``∂_t U = -Lh U``.

        The explicit TVD-RK3 time integrator is third-order in time; for
        convergence studies at fixed CFL ``a·dt/h``, the global error is
        ``O(h^6)`` + ``O(dt^3)``. Select ``dt`` small relative to ``h^2`` to
        expose the spatial sixth order.
        """
        return tvd_rk3(
            self.xp, u, dt,
            lambda q: self.apply_rhs(q, axis, a),
        )

    # ── Diagnostics ──────────────────────────────────────────────────────

    def energy(self, u):
        """Discrete L^2 energy ½·Σ_h U_i^2 (periodic: drops last node).

        For a single-axis transport problem the "cell volume" is h[axis]; for
        multi-axis arrays the product ∏h is used (isotropic assumption).
        """
        xp = self.xp
        h_vol = 1.0
        for ax in range(self.grid.ndim):
            h_vol *= self._h[ax]
        if self.bc_type == "periodic":
            slices = tuple(slice(None, -1) for _ in range(self.grid.ndim))
            u_core = u[slices]
        else:
            u_core = u
        return 0.5 * float(h_vol) * float(xp.sum(u_core * u_core))

    def hyperviscosity_symbol(self, theta):
        """Fourier symbol of ``σ|a|·h^7·(-D2^CCD)^4`` in dimensionless form.

        Returns
        -------
        real_part : float or array
            ``Re λ(θ) / (σ|a|/h) = -ω_2(θ)^8`` using the exact Chu & Fan
            closed-form ``ω_2(θ)^2 = (81 - 48 cos θ - 33 cos 2θ) /
            (48 + 40 cos θ + 2 cos 2θ)``.

        Useful for stability diagnostics and comparison with the pedagogical
        analysis in SP-G.
        """
        xp = self.xp
        theta = xp.asarray(theta)
        c1 = xp.cos(theta)
        c2 = xp.cos(2.0 * theta)
        num = 81.0 - 48.0 * c1 - 33.0 * c2
        den = 48.0 + 40.0 * c1 + 2.0 * c2
        omega2_sq = num / den
        return -(omega2_sq ** 4)
