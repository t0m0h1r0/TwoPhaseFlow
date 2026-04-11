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
import numpy as np
from typing import Optional, Tuple, TYPE_CHECKING

from .block_tridiag import BlockTridiagSolver

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

        # Build one solver per axis (wall BC)
        self._solvers: dict = {}
        for ax in range(self.ndim):
            n_pts = grid.N[ax] + 1
            h = float(grid.L[ax] / grid.N[ax])   # uniform spacing for CCD system
            self._solvers[ax] = self._build_axis_solver(n_pts, h)

        # Build periodic solvers if needed (block-circulant, dense LU)
        self._periodic_solvers: dict = {}
        if bc_type == "periodic":
            for ax in range(self.ndim):
                n_pts = grid.N[ax] + 1
                h = float(grid.L[ax] / grid.N[ax])
                self._periodic_solvers[ax] = self._build_axis_solver_periodic(n_pts, h)

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
        if self.bc_type == "periodic" and bc_left is None and bc_right is None:
            return self._differentiate_periodic(data, axis,
                                                apply_metric=apply_metric)

        d1, d2 = self._differentiate_wall_raw(data, axis, bc_left, bc_right)

        # Non-uniform grid: transform from ξ-space back to x-space (§4.9)
        if not self.grid.uniform and apply_metric:
            d1, d2 = self._apply_metric(d1, d2, axis)

        return d1, d2

    def differentiate_raw(self, data: np.ndarray, axis: int):
        """Compute CCD derivatives in ξ-space without metric transformation.

        Used exclusively for grid metric computation (§6 Step 5): call with the
        physical coordinate array x[i] on the uniform computational grid to obtain
        dx/d(x_unif) and d²x/d(x_unif)², from which J and ∂J/∂ξ are derived.

        The input ``data`` must be a 1-D array of shape ``(N[axis]+1,)``.  It is
        internally embedded into an N-dimensional array so that ``axis`` picks the
        correct pre-factored CCD solver.

        Parameters
        ----------
        data : 1-D numpy array, shape ``(N[axis]+1,)``
        axis : spatial axis (0, 1, or 2)

        Returns
        -------
        d1 : 1-D numpy array — ∂data/∂x_unif in ξ-space
        d2 : 1-D numpy array — ∂²data/∂x_unif² in ξ-space
        """
        arr = np.asarray(data).ravel()
        # Embed 1-D coords into an N-D array with shape[axis]=N+1, all others=1,
        # so that moveaxis(data, axis, 0) gives (N+1, 1) regardless of axis value.
        shape = [1] * self.ndim
        shape[axis] = -1
        data_nd = arr.reshape(shape)
        d1_nd, d2_nd = self._differentiate_wall_raw(data_nd, axis, None, None)
        d1_host = self.backend.to_host(d1_nd)
        d2_host = self.backend.to_host(d2_nd)
        return np.asarray(d1_host).ravel(), np.asarray(d2_host).ravel()

    def _differentiate_wall_raw(self, data, axis: int, bc_left, bc_right):
        """Wall-BC CCD solve in ξ-space, no metric transformation.

        Core computation shared by ``differentiate()`` (wall path) and
        ``differentiate_raw()`` (metric computation).  Returns ξ-space
        derivatives in the same shape as ``data``.
        """
        xp = self.xp
        info = self._solvers[axis]
        h = info['h']
        N = info['N']
        n_int = info['n_int']

        # Move target axis to front, flatten remaining axes as batch
        data = xp.asarray(data)
        f = xp.moveaxis(data, axis, 0)          # (N+1, *other)
        orig_shape = f.shape
        n_pts = f.shape[0]
        batch_size = int(np.prod(orig_shape[1:])) if len(orig_shape) > 1 else 1
        f = f.reshape(n_pts, batch_size)         # (N+1, batch)

        # Build interior RHS — vectorised over interior nodes i=1..n_int.
        # Interior index idx=0..n_int-1 maps to node i=idx+1, so
        #   f[i-1] → f[0:n_int],  f[i] → f[1:n_int+1],  f[i+1] → f[2:n_int+2].
        f_m1 = f[0:n_int]
        f_0  = f[1:n_int + 1]
        f_p1 = f[2:n_int + 2]
        d1_rhs = (_A1 / h) * (f_p1 - f_m1)                        # (n_int, batch)
        d2_rhs = (_A2 / (h * h)) * (f_m1 - 2.0 * f_0 + f_p1)      # (n_int, batch)
        rhs = xp.stack((d1_rhs, d2_rhs), axis=1)                  # (n_int, 2, batch)

        # Boundary values (compact or prescribed)
        fp0, fpp0 = self._left_boundary(info, f, h, bc_left)
        fpN, fppN = self._right_boundary(info, f, h, N, bc_right)

        # Subtract boundary coupling from first and last interior RHS rows
        L0 = xp.asarray(info['L0'])
        UN = xp.asarray(info['UN'])
        rhs[0, 0, :] -= L0[0, 0] * fp0 + L0[0, 1] * fpp0
        rhs[0, 1, :] -= L0[1, 0] * fp0 + L0[1, 1] * fpp0
        rhs[n_int - 1, 0, :] -= UN[0, 0] * fpN + UN[0, 1] * fppN
        rhs[n_int - 1, 1, :] -= UN[1, 0] * fpN + UN[1, 1] * fppN

        # Solve block tridiagonal
        sol = info['solver'].solve(rhs)           # (n_int, 2, batch)

        # Assemble full derivative arrays
        d1_flat = xp.zeros((n_pts, batch_size))
        d2_flat = xp.zeros((n_pts, batch_size))
        d1_flat[1:-1] = sol[:, 0, :]
        d2_flat[1:-1] = sol[:, 1, :]

        # Recover boundary values from compact-BC expressions
        M_l = xp.asarray(info['bc_left']['M'])
        d1_flat[0] = M_l[0, 0] * d1_flat[1] + M_l[0, 1] * d2_flat[1] + fp0
        d2_flat[0] = M_l[1, 0] * d1_flat[1] + M_l[1, 1] * d2_flat[1] + fpp0

        M_r = xp.asarray(info['bc_right']['M'])
        d1_flat[N] = M_r[0, 0] * d1_flat[N-1] + M_r[0, 1] * d2_flat[N-1] + fpN
        d2_flat[N] = M_r[1, 0] * d1_flat[N-1] + M_r[1, 1] * d2_flat[N-1] + fppN

        # Restore original shape
        d1 = xp.moveaxis(d1_flat.reshape(orig_shape), 0, axis)
        d2 = xp.moveaxis(d2_flat.reshape(orig_shape), 0, axis)
        return d1, d2

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
        if self.bc_type != "wall":
            return
        sl_lo = [slice(None)] * grad.ndim
        sl_hi = [slice(None)] * grad.ndim
        sl_lo[ax] = 0
        sl_hi[ax] = -1
        grad[tuple(sl_lo)] = 0.0
        grad[tuple(sl_hi)] = 0.0

    # ── Build per-axis solver ─────────────────────────────────────────────

    def _build_axis_solver(self, n_pts: int, h: float) -> dict:
        N = n_pts - 1
        n_int = N - 1
        assert n_int >= 1, f"Need ≥ 3 grid points; got {n_pts}"

        bc_left = _boundary_coeffs_left(h, n_pts)
        bc_right = _boundary_coeffs_right(h, n_pts)

        # Original off-diagonal blocks (before boundary absorption)
        L0 = np.array([[_ALPHA1, _B1 * h],
                        [_B2 / h, _BETA2]])   # couples i=1 with i=0
        UN = np.array([[_ALPHA1, -_B1 * h],
                        [-_B2 / h, _BETA2]])  # couples i=N-1 with i=N

        diag  = [np.eye(2) for _ in range(n_int)]
        lower = [np.array([[_ALPHA1, _B1 * h],
                            [_B2 / h, _BETA2]]) for _ in range(n_int)]
        upper = [np.array([[_ALPHA1, -_B1 * h],
                            [-_B2 / h, _BETA2]]) for _ in range(n_int)]

        # Absorb left boundary (i=1 row couples with i=0)
        diag[0] = diag[0] + lower[0] @ bc_left['M']
        lower[0] = np.zeros((2, 2))

        # Absorb right boundary (i=N-1 row couples with i=N)
        diag[-1] = diag[-1] + upper[-1] @ bc_right['M']
        upper[-1] = np.zeros((2, 2))

        solver = BlockTridiagSolver(self.xp)
        solver.factorize(diag, lower, upper)

        return {
            'solver': solver,
            'h': h,
            'N': N,
            'n_int': n_int,
            'L0': L0,
            'UN': UN,
            'bc_left': bc_left,
            'bc_right': bc_right,
        }

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
        N = n_pts - 1   # number of unique nodes (node N is the periodic image of node 0)
        assert N >= 3, f"Need ≥ 3 unique nodes for periodic CCD; got {N}"

        lower_blk = np.array([[_ALPHA1,  _B1 * h],
                               [_B2 / h,  _BETA2]])   # left-neighbour coupling
        upper_blk = np.array([[_ALPHA1, -_B1 * h],
                               [-_B2 / h,  _BETA2]])  # right-neighbour coupling

        # Build 2N × 2N block-circulant matrix on host (small, one-time build).
        A_host = np.zeros((2 * N, 2 * N))
        for i in range(N):
            A_host[2*i:2*i+2, 2*i:2*i+2] += np.eye(2)                        # diagonal
            j_lo = (i - 1) % N
            A_host[2*i:2*i+2, 2*j_lo:2*j_lo+2] += lower_blk                  # left  (wrap at i=0)
            j_hi = (i + 1) % N
            A_host[2*i:2*i+2, 2*j_hi:2*j_hi+2] += upper_blk                  # right (wrap at i=N-1)

        # Factor on the active device.
        A_dev = self.xp.asarray(A_host)
        lu, piv = self.backend.linalg.lu_factor(A_dev)
        return {'lu': lu, 'piv': piv, 'h': h, 'N': N}

    def _differentiate_periodic(self, data, axis: int, apply_metric: bool = True):
        """Periodic CCD differentiation using the pre-factorised block-circulant solver.

        Nodes 0..N-1 are solved via the 2N×2N system; node N receives a copy
        of node 0 (periodic image). Runs entirely on the active device.
        """
        xp = self.xp
        info = self._periodic_solvers[axis]
        h = info['h']
        N = info['N']

        # Move target axis to front, flatten remaining axes as batch
        data = xp.asarray(data)
        f_full = xp.moveaxis(data, axis, 0)      # (N+1, *other)
        orig_shape = f_full.shape
        n_pts = f_full.shape[0]                  # N+1
        batch_size = int(np.prod(orig_shape[1:])) if len(orig_shape) > 1 else 1
        f_full = f_full.reshape(n_pts, batch_size)  # (N+1, batch)

        # N unique nodes only; node N = node 0 (periodic image).
        f_unique = f_full[:N, :]                 # (N, batch) — device-native view

        # Build RHS (2N × batch) device-native using a vectorised roll/slice pattern.
        f_im1 = xp.roll(f_unique, 1, axis=0)     # f[(i-1) mod N]
        f_ip1 = xp.roll(f_unique, -1, axis=0)    # f[(i+1) mod N]
        rhs_d1 = (_A1 / h) * (f_ip1 - f_im1)                         # (N, batch)
        rhs_d2 = (_A2 / (h * h)) * (f_im1 - 2.0 * f_unique + f_ip1)  # (N, batch)

        rhs = xp.empty((2 * N, batch_size), dtype=f_unique.dtype)
        rhs[0::2, :] = rhs_d1
        rhs[1::2, :] = rhs_d2

        # Solve (2N × batch) on the active device.
        x = self.backend.linalg.lu_solve((info['lu'], info['piv']), rhs)

        # Extract d1 (even rows) and d2 (odd rows) for nodes 0..N-1
        d1_inner = x[0::2, :]   # (N, batch)
        d2_inner = x[1::2, :]   # (N, batch)

        # Full (N+1, batch) arrays: node N = node 0 (periodic image)
        d1_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
        d2_flat = xp.empty((N + 1, batch_size), dtype=f_unique.dtype)
        d1_flat[:N, :] = d1_inner
        d2_flat[:N, :] = d2_inner
        d1_flat[N, :] = d1_inner[0, :]
        d2_flat[N, :] = d2_inner[0, :]

        d1 = xp.moveaxis(d1_flat.reshape(orig_shape), 0, axis)
        d2 = xp.moveaxis(d2_flat.reshape(orig_shape), 0, axis)

        if not self.grid.uniform and apply_metric:
            d1, d2 = self._apply_metric(d1, d2, axis)

        return d1, d2

    # ── Boundary helper methods ───────────────────────────────────────────

    def _left_boundary(self, info, f, h, bc_left_override):
        """Compute the data-dependent part of the left boundary value."""
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
        # Eq-I-bc gives fp0; Eq-II-bc is standalone (no fp1/fpp1 coupling)
        fp0  = R_I
        fpp0 = R_II
        return fp0, fpp0

    def _right_boundary(self, info, f, h, N, bc_right_override):
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
        # Eq-I-bc gives fpN; Eq-II-bc is standalone (no fp_{N-1}/fpp_{N-1} coupling)
        fpN  = R_I_r
        fppN = R_II_r
        return fpN, fppN

    # ── Non-uniform metric transform ──────────────────────────────────────

    def _apply_metric(self, d1_xi, d2_xi, axis: int):
        """Convert ξ-space derivatives to x-space via metric J = ∂ξ/∂x.

        ∂f/∂x   = J · (∂f/∂ξ)
        ∂²f/∂x² = J² · (∂²f/∂ξ²) + J · (dJ/dξ) · (∂f/∂ξ)     (§4.9)
        """
        xp = self.xp
        # Broadcast metric arrays to field shape
        J_1d    = xp.asarray(self.grid.J[axis])
        dJ_1d   = xp.asarray(self.grid.dJ_dxi[axis])

        # Build shape for broadcasting: (1, …, N+1, …, 1) with N+1 at axis
        shape = [1] * self.ndim
        shape[axis] = -1
        J   = J_1d.reshape(shape)
        dJ  = dJ_1d.reshape(shape)

        d1_x = J * d1_xi
        d2_x = J * J * d2_xi + J * dJ * d1_xi
        return d1_x, d2_x


# ── Boundary coefficient constructors (module-level, pure functions) ─────

def _boundary_coeffs_left(h: float, n_pts: int) -> dict:
    """One-sided compact scheme at left boundary (§4.7).

    The boundary values satisfy:
        [f'₀ ]  = M @ [f'₁ ]  + [c₁(f₀…f₃)]
        [f''₀]        [f''₁]    [c₂(f₀…fₖ)]

    Equations (§5 eq:bc_left, eq:bcII_left):
        Eq-I-bc  (O(h⁵)): f'₀ + (3/2)f'₁ − (3h/2)f''₁
                    = (1/h)(−23/6·f₀ + 21/4·f₁ − 3/2·f₂ + 1/12·f₃)
        Eq-II-bc:
          n_pts < 6 → O(h²) 4-point: f''₀ = (1/h²)(2f₀−5f₁+4f₂−f₃)
          n_pts ≥ 6 → O(h⁴) 6-point: f''₀ = (1/(12h²))(45f₀−154f₁+214f₂−156f₃+61f₄−10f₅)

    Eq-II-bc is independent of f'₁, f''₁ (γ=δ=0 in §5 eq:bcII_general).

    After solving for [f'₀, f''₀]:
        M[0,:] = [-3/2,  3h/2]   (from Eq-I-bc)
        M[1,:] = [0,     0   ]   (Eq-II-bc is standalone — no fp₁/fpp₁ coupling)
    and the data-dependent RHS coefficients are returned in c_I, c_II.
    """
    M = np.array([[-3.0 / 2.0, 3.0 * h / 2.0],
                   [ 0.0,       0.0            ]])
    c_I  = np.array([-23.0/6.0, 21.0/4.0, -3.0/2.0, 1.0/12.0]) / h
    if n_pts >= 6:
        # O(h⁴) 6-point formula (§5 eq:bcII_left_h4)
        c_II = np.array([45.0, -154.0, 214.0, -156.0, 61.0, -10.0]) / (12.0 * h * h)
    else:
        # O(h²) 4-point fallback for very small grids
        c_II = np.array([2.0, -5.0, 4.0, -1.0]) / (h * h)
    return {'M': M, 'c_I': c_I, 'c_II': c_II}


def _boundary_coeffs_right(h: float, n_pts: int) -> dict:
    """One-sided compact scheme at right boundary (§4.7).

    Obtained from the left scheme by h → −h symmetry.

    Equations (§5 eq:bc_left mirror, eq:bcII_left mirror):
        Eq-I-bc  (O(h⁵)): f'_N + (3/2)f'_{N-1} + (3h/2)f''_{N-1}
                    = (1/h)(23/6·f_N − 21/4·f_{N-1} + 3/2·f_{N-2} − 1/12·f_{N-3})
        Eq-II-bc:
          n_pts < 6 → O(h²) 4-point: f''_N = (1/h²)(2f_N−5f_{N-1}+4f_{N-2}−f_{N-3})
          n_pts ≥ 6 → O(h⁴) 6-point (mirror of left): coefficients applied as f[N-k]

    After solving for [f'_N, f''_N]:
        M[0,:] = [-3/2, -3h/2]   (from Eq-I-bc mirror)
        M[1,:] = [0,     0   ]   (Eq-II-bc is standalone)
    """
    M = np.array([[-3.0 / 2.0, -3.0 * h / 2.0],
                   [ 0.0,        0.0            ]])
    c_I  = np.array([23.0/6.0, -21.0/4.0, 3.0/2.0, -1.0/12.0]) / h
    if n_pts >= 6:
        # O(h⁴) 6-point formula — mirror of left boundary (applied as f[N-k])
        c_II = np.array([45.0, -154.0, 214.0, -156.0, 61.0, -10.0]) / (12.0 * h * h)
    else:
        # O(h²) 4-point fallback for very small grids
        c_II = np.array([2.0, -5.0, 4.0, -1.0]) / (h * h)
    return {'M': M, 'c_I': c_I, 'c_II': c_II}
