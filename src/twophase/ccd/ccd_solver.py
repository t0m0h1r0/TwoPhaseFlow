"""
CCD (Combined Compact Difference) solver.

Implements the 6th-order compact finite-difference scheme described in
Section 4 of the paper (Chu & Fan 1998).

Given a 1-D function sampled at uniform nodes f₀, f₁, …, f_N (spacing h),
the CCD scheme simultaneously solves for the first derivative f' and second
derivative f'' by coupling nearest-neighbour stencils:

    Eq-I:   α₁(f'ᵢ₋₁ + f'ᵢ₊₁) + f'ᵢ
              = (a₁/h)(fᵢ₊₁ − fᵢ₋₁) + b₁ h (f''ᵢ₊₁ − f''ᵢ₋₁)      (§4 Eq-I)

    Eq-II:  β₂(f''ᵢ₋₁ + f''ᵢ₊₁) + f''ᵢ
              = (a₂/h²)(fᵢ₋₁ − 2fᵢ + fᵢ₊₁) + (b₂/h)(f'ᵢ₊₁ − f'ᵢ₋₁) (§4 Eq-II)

with coefficients (Table 1 of the paper):
    α₁ = 7/16,  a₁ = 15/16,  b₁ = 1/16
    β₂ = −1/8,  a₂ = 3,      b₂ = −9/8

Together these form a (2n×2n) block-tridiagonal system that is solved once
per differentiation call via a pre-factored LU decomposition.

Boundary treatment (§4.7, O(h⁵)):
    Left  (i=0): 4-point one-sided compact scheme involving f₀…f₃.
    Right (i=N): mirror of the left scheme.

2-D / 3-D batching:
    When differentiating along axis ``ax`` on a 2-D/3-D array, all slices
    perpendicular to ``ax`` are processed simultaneously as a batch dimension,
    making the cost independent of the number of batch axes.

Non-uniform grid (§4.9):
    When ``grid.uniform`` is False, the CCD system is solved in the
    uniform computational coordinate ξ and the results are mapped back to
    physical space using the metric J = ∂ξ/∂x stored on the grid.
"""

from __future__ import annotations
import math
import numpy as np
from typing import Optional, Tuple, TYPE_CHECKING

from .block_tridiag import BlockTridiagSolver
from .ccd_boundary_helpers import (
    compute_ccd_left_boundary,
    compute_ccd_right_boundary,
    enforce_ccd_wall_neumann,
)
from .ccd_solver_helpers import (
    apply_ccd_metric,
    build_ccd_axis_solver,
    build_ccd_axis_solver_legacy,
    build_ccd_axis_solver_periodic,
    differentiate_ccd_periodic,
    differentiate_ccd_periodic_second_only,
    differentiate_ccd_wall_first_only,
    differentiate_ccd_wall_raw,
    differentiate_ccd_wall_second_only,
)
from ..core.boundary import is_periodic_axis

if TYPE_CHECKING:
    from ..core.grid import Grid
    from ..backend import Backend


# ── CCD interior coefficients (Table 1 of the paper) ─────────────────────
_ALPHA1 = 7.0 / 16.0   # Eq-I  off-diagonal (f')
_A1     = 15.0 / 16.0  # Eq-I  RHS function value coefficient
_B1     = 1.0 / 16.0   # Eq-I  RHS f'' coupling coefficient

_BETA2  = -1.0 / 8.0   # Eq-II off-diagonal (f'')
_A2     = 3.0           # Eq-II RHS function value coefficient
_B2     = -9.0 / 8.0   # Eq-II RHS f' coupling coefficient


class CCDSolver:
    """Batch CCD differentiator for 2-D/3-D scalar fields.

    Parameters
    ----------
    grid    : Grid object describing node positions and spacings.
    backend : Backend carrying the array namespace ``xp``.
    bc_type : 'wall' (default) or 'periodic'.
              'wall'     — one-sided compact scheme at boundaries (O(h⁵)).
              'periodic' — block-circulant system for all N nodes; node N
                           is treated as the periodic image of node 0 and
                           its derivative is set equal to node 0 after the
                           solve.  Uses a dense LU factorisation of the
                           2N×2N block-circulant matrix (pre-computed once).

    The solver pre-factorise the block-tridiagonal (or block-circulant)
    system once per axis during ``__init__``, so ``differentiate()``
    calls are cheap.
    """

    def __init__(self, grid: "Grid", backend: "Backend", bc_type: str = "wall"):
        self.grid = grid
        self.backend = backend
        self.xp = backend.xp
        self.ndim = grid.ndim
        self.bc_type = bc_type

        # Wall-BC solvers are built lazily per used axis. This avoids
        # constructing a lower-order closure for thin batch axes that are never
        # differentiated, while still rejecting paper-inexact axes on use.
        self._solvers: dict = {}

        # Build periodic solvers if needed (block-circulant, dense LU)
        self._periodic_solvers: dict = {}
        for ax in range(self.ndim):
            if not self._axis_periodic(ax):
                continue
            n_pts = grid.N[ax] + 1
            h = float(grid.L[ax] / grid.N[ax])
            self._periodic_solvers[ax] = self._build_axis_solver_periodic(n_pts, h)

    def _axis_periodic(self, axis: int) -> bool:
        """Return whether one coordinate axis uses periodic topology."""
        return is_periodic_axis(self.bc_type, axis, self.ndim)

    # ── Public API ────────────────────────────────────────────────────────

    def differentiate(
        self,
        data,
        axis: int,
        bc_left: Optional[Tuple[float, float]] = None,
        bc_right: Optional[Tuple[float, float]] = None,
        apply_metric: bool = True,
    ):
        """Compute first and second derivatives along ``axis``.

        When ``bc_type='periodic'`` (and no bc_left/bc_right overrides),
        the periodic block-circulant solver is used instead of the
        one-sided boundary scheme.

        Parameters
        ----------
        data    : array_like, shape ``grid.shape``
        axis    : spatial axis to differentiate (0, 1, or 2)
        bc_left : (f'₀, f''₀) override (testing only; default=compact BC)
        bc_right: (f'_N, f''_N) override (testing only; default=compact BC)
        apply_metric : bool — if False, return ξ-space derivatives without
                       metric transformation (for non-uniform filter operations)

        Returns
        -------
        d1 : array, same shape as ``data`` — ∂data/∂x_axis (or ∂data/∂ξ)
        d2 : array, same shape as ``data`` — ∂²data/∂x_axis² (or ∂²data/∂ξ²)
        """
        if self._axis_periodic(axis) and bc_left is None and bc_right is None:
            return self._differentiate_periodic(data, axis,
                                                apply_metric=apply_metric)

        d1, d2 = self._differentiate_wall_raw(data, axis, bc_left, bc_right)

        # Non-uniform grid: transform from ξ-space back to x-space (§4.9)
        if not self.grid.uniform and apply_metric:
            d1, d2 = self._apply_metric(d1, d2, axis)

        return d1, d2

    def differentiate_raw(self, data, axis: int):
        """Compute CCD derivatives in ξ-space without metric transformation.

        Used exclusively for grid metric computation (§6 Step 5): call with the
        physical coordinate array x[i] on the uniform computational grid to obtain
        dx/d(x_unif) and d²x/d(x_unif)², from which J and ∂J/∂ξ are derived.

        The input ``data`` must be a 1-D array of shape ``(N[axis]+1,)``.  It is
        internally embedded into an N-dimensional array so that ``axis`` picks the
        correct pre-factored CCD solver.

        Parameters
        ----------
        data : 1-D array, shape ``(N[axis]+1,)``
        axis : spatial axis (0, 1, or 2)

        Returns
        -------
        d1 : 1-D array — ∂data/∂x_unif in ξ-space
        d2 : 1-D array — ∂²data/∂x_unif² in ξ-space
        """
        xp = self.xp
        arr = xp.asarray(data).ravel()
        # Embed 1-D coords into an N-D array with shape[axis]=N+1, all others=1,
        # so that moveaxis(data, axis, 0) gives (N+1, 1) regardless of axis value.
        shape = [1] * self.ndim
        shape[axis] = -1
        data_nd = arr.reshape(shape)
        d1_nd, d2_nd = self._differentiate_wall_raw(data_nd, axis, None, None)
        return xp.asarray(d1_nd).ravel(), xp.asarray(d2_nd).ravel()

    def first_derivative(
        self,
        data,
        axis: int,
        bc_left: Optional[Tuple[float, float]] = None,
        bc_right: Optional[Tuple[float, float]] = None,
        apply_metric: bool = True,
    ):
        """Compute only the first derivative along ``axis``."""
        if self._axis_periodic(axis) and bc_left is None and bc_right is None:
            return self._differentiate_periodic(
                data, axis, apply_metric=apply_metric
            )[0]
        return self._differentiate_wall_first_only(
            data, axis, bc_left, bc_right, apply_metric=apply_metric
        )

    def second_derivative(
        self,
        data,
        axis: int,
        bc_left: Optional[Tuple[float, float]] = None,
        bc_right: Optional[Tuple[float, float]] = None,
        apply_metric: bool = True,
    ):
        """Compute only the second derivative along ``axis``."""
        if self._axis_periodic(axis) and bc_left is None and bc_right is None:
            return self._differentiate_periodic_second_only(
                data, axis, apply_metric=apply_metric
            )
        return self._differentiate_wall_second_only(
            data, axis, bc_left, bc_right, apply_metric=apply_metric
        )

    def _differentiate_wall_raw(self, data, axis: int, bc_left, bc_right):
        """Wall-BC CCD solve in ξ-space, no metric transformation.

        Core computation shared by ``differentiate()`` (wall path) and
        ``differentiate_raw()`` (metric computation).  Returns ξ-space
        derivatives in the same shape as ``data``.
        """
        return differentiate_ccd_wall_raw(self, data, axis, bc_left, bc_right)

    def _differentiate_wall_first_only(
        self, data, axis: int, bc_left, bc_right, apply_metric: bool = True
    ):
        """Wall-BC CCD solve returning only the first derivative."""
        return differentiate_ccd_wall_first_only(
            self, data, axis, bc_left, bc_right, apply_metric=apply_metric
        )

    def _differentiate_wall_second_only(
        self, data, axis: int, bc_left, bc_right, apply_metric: bool = True
    ):
        """Wall-BC CCD solve returning only the second derivative."""
        return differentiate_ccd_wall_second_only(
            self, data, axis, bc_left, bc_right, apply_metric=apply_metric
        )

    def enforce_wall_neumann(self, grad, ax: int) -> None:
        """Zero CCD gradient at wall boundaries (Neumann BC: ∂p/∂n = 0).

        No-op when ``bc_type != 'wall'``.

        The CCD one-sided boundary stencil gives a nonzero wall-normal gradient
        even when the physical BC is zero-flux.  Explicitly zeroing the boundary
        planes corrects for this and prevents accumulating IPC feedback errors.

        Used by both ``VelocityCorrector`` and ``Predictor`` (IPC term) so that
        the zeroing logic lives in one place (DRY).

        Parameters
        ----------
        grad : array — gradient field (modified in-place)
        ax   : int   — axis along which the wall boundaries are zeroed
        """
        enforce_ccd_wall_neumann(self, grad, ax)

    # ── Build per-axis solver ─────────────────────────────────────────────

    def _build_axis_solver(self, n_pts: int, h: float) -> dict:
        return build_ccd_axis_solver(
            self,
            n_pts,
            h,
            _boundary_coeffs_left,
            _boundary_coeffs_right,
        )

    def _get_axis_solver(self, axis: int) -> dict:
        if axis not in self._solvers:
            n_pts = self.grid.N[axis] + 1
            h = float(self.grid.L[axis] / self.grid.N[axis])
            self._solvers[axis] = self._build_axis_solver(n_pts, h)
        return self._solvers[axis]

    # DO NOT DELETE — CHK-117 legacy reference.
    # Pre-dense-LU block-Thomas path retained per C2 (never delete tested
    # code). Not wired to any call site; kept for auditability + rollback.
    # Uses BlockTridiagSolver — which is why the import at the top stays.
    def _build_axis_solver_legacy(self, n_pts: int, h: float) -> dict:
        return build_ccd_axis_solver_legacy(
            self,
            n_pts,
            h,
            _boundary_coeffs_left,
            _boundary_coeffs_right,
        )

    # ── Periodic solver ───────────────────────────────────────────────────

    def _build_axis_solver_periodic(self, n_pts: int, h: float) -> dict:
        """Build block-circulant CCD solver for periodic BC.

        For a periodic domain sampled at N+1 nodes (0..N) with node N = node 0,
        the N unique DOFs (0..N-1) all use the standard interior CCD stencil
        with wrap-around neighbours.

        The resulting 2N×2N block-circulant system is pre-factorised once
        using the backend's LU (scipy on CPU, cupyx.scipy on GPU). The factors
        live on the active device; solve-time runs entirely device-native.
        """
        return build_ccd_axis_solver_periodic(self, n_pts, h)

    def _differentiate_periodic(self, data, axis: int, apply_metric: bool = True):
        """Periodic CCD differentiation using the pre-factorised block-circulant solver.

        Nodes 0..N-1 are solved via the 2N×2N system; node N receives a copy
        of node 0 (periodic image). Runs entirely on the active device.
        """
        return differentiate_ccd_periodic(self, data, axis, apply_metric=apply_metric)

    def _differentiate_periodic_second_only(
        self, data, axis: int, apply_metric: bool = True
    ):
        """Periodic CCD differentiation returning only the second derivative."""
        return differentiate_ccd_periodic_second_only(
            self, data, axis, apply_metric=apply_metric
        )

    # ── Boundary helper methods ───────────────────────────────────────────

    def _left_boundary(self, info, f, h, bc_left_override):
        """Compute the data-dependent part of the left boundary value.

        Returns a ``(2, batch)`` stacked array ``[fp0, fpp0]`` — pre-stacked
        so downstream boundary-subtraction and ghost-recovery math can use
        a single matmul rather than 4 scalar-indexed ops.
        """
        return compute_ccd_left_boundary(self, info, f, h, bc_left_override)

    def _right_boundary(self, info, f, h, N, bc_right_override):
        """Compute the data-dependent part of the right boundary value.

        Returns a ``(2, batch)`` stacked array ``[fpN, fppN]`` — same
        convention as :meth:`_left_boundary`.
        """
        return compute_ccd_right_boundary(self, info, f, h, N, bc_right_override)

    # DO NOT DELETE — CHK-118 legacy reference.
    # Pre-matmul scalar-gather boundary helpers. Retained per C2.
    def _left_boundary_legacy(self, info, f, h, bc_left_override):
        xp = self.xp
        if bc_left_override is not None:
            batch = f.shape[1]
            fp0  = xp.full(batch, float(bc_left_override[0]))
            fpp0 = xp.full(batch, float(bc_left_override[1]))
            return fp0, fpp0
        bc = info['bc_left']
        c_I  = xp.asarray(bc['c_I'])
        c_II = xp.asarray(bc['c_II'])
        R_I  = (c_I[0]*f[0] + c_I[1]*f[1] + c_I[2]*f[2] + c_I[3]*f[3])
        R_II = sum(c_II[k] * f[k] for k in range(len(bc['c_II'])))
        return R_I, R_II

    def _right_boundary_legacy(self, info, f, h, N, bc_right_override):
        xp = self.xp
        if bc_right_override is not None:
            batch = f.shape[1]
            fpN  = xp.full(batch, float(bc_right_override[0]))
            fppN = xp.full(batch, float(bc_right_override[1]))
            return fpN, fppN
        bc = info['bc_right']
        c_I_r  = xp.asarray(bc['c_I'])
        c_II_r = xp.asarray(bc['c_II'])
        R_I_r  = (c_I_r[0]*f[N] + c_I_r[1]*f[N-1]
                  + c_I_r[2]*f[N-2] + c_I_r[3]*f[N-3])
        R_II_r = sum(c_II_r[k] * f[N - k] for k in range(len(bc['c_II'])))
        return R_I_r, R_II_r

    # ── Non-uniform metric transform ──────────────────────────────────────

    def _apply_metric(self, d1_xi, d2_xi, axis: int):
        """Convert ξ-space derivatives to x-space via metric J = ∂ξ/∂x.

        ∂f/∂x   = J · (∂f/∂ξ)
        ∂²f/∂x² = J² · (∂²f/∂ξ²) + J · (dJ/dξ) · (∂f/∂ξ)     (§4.9)
        """
        return apply_ccd_metric(self, d1_xi, d2_xi, axis)


# ── Boundary coefficient constructors (module-level, pure functions) ─────

def _boundary_coeffs_left(h: float, n_pts: int) -> dict:
    """One-sided compact scheme at left boundary (§4.7).

    The boundary values satisfy:
        [f'₀ ]  = M @ [f'₁ ]  + [c₁(f₀…f₃)]
        [f''₀]        [f''₁]    [c₂(f₀…fₖ)]

    Equations (§5 eq:bc_left, eq:bcII_left):
        Eq-I-bc  (O(h⁵)): f'₀ + (3/2)f'₁ − (3h/2)f''₁
                    = (1/h)(−23/6·f₀ + 21/4·f₁ − 3/2·f₂ + 1/12·f₃)
        Eq-II-bc (O(h⁴), requires n_pts ≥ 6):
            f''₀ = (1/(12h²))(45f₀−154f₁+214f₂−156f₃+61f₄−10f₅)

    Eq-II-bc is independent of f'₁, f''₁ (γ=δ=0 in §5 eq:bcII_general).

    After solving for [f'₀, f''₀]:
        M[0,:] = [-3/2,  3h/2]   (from Eq-I-bc)
        M[1,:] = [0,     0   ]   (Eq-II-bc is standalone — no fp₁/fpp₁ coupling)
    and the data-dependent RHS coefficients are returned in c_I, c_II.
    """
    _require_eqii_h4_boundary_points(n_pts)
    M = np.array([[-3.0 / 2.0, 3.0 * h / 2.0],
                   [ 0.0,       0.0            ]])
    c_I  = np.array([-23.0/6.0, 21.0/4.0, -3.0/2.0, 1.0/12.0]) / h
    c_II = np.array([45.0, -154.0, 214.0, -156.0, 61.0, -10.0]) / (12.0 * h * h)
    return {'M': M, 'c_I': c_I, 'c_II': c_II}


def _boundary_coeffs_right(h: float, n_pts: int) -> dict:
    """One-sided compact scheme at right boundary (§4.7).

    Obtained from the left scheme by h → −h symmetry.

    Equations (§5 eq:bc_left mirror, eq:bcII_left mirror):
        Eq-I-bc  (O(h⁵)): f'_N + (3/2)f'_{N-1} + (3h/2)f''_{N-1}
                    = (1/h)(23/6·f_N − 21/4·f_{N-1} + 3/2·f_{N-2} − 1/12·f_{N-3})
        Eq-II-bc (O(h⁴), requires n_pts ≥ 6):
            mirror of left boundary, coefficients applied as f[N-k].

    After solving for [f'_N, f''_N]:
        M[0,:] = [-3/2, -3h/2]   (from Eq-I-bc mirror)
        M[1,:] = [0,     0   ]   (Eq-II-bc is standalone)
    """
    _require_eqii_h4_boundary_points(n_pts)
    M = np.array([[-3.0 / 2.0, -3.0 * h / 2.0],
                   [ 0.0,        0.0            ]])
    c_I  = np.array([23.0/6.0, -21.0/4.0, 3.0/2.0, -1.0/12.0]) / h
    c_II = np.array([45.0, -154.0, 214.0, -156.0, 61.0, -10.0]) / (12.0 * h * h)
    return {'M': M, 'c_I': c_I, 'c_II': c_II}


def _require_eqii_h4_boundary_points(n_pts: int) -> None:
    if n_pts < 6:
        raise ValueError(
            "CCD wall Eq-II boundary closure requires n_pts >= 6 for the "
            "paper §4 O(h^4) six-point formula; lower-order fallback is "
            "prohibited by paper-exact policy."
        )
