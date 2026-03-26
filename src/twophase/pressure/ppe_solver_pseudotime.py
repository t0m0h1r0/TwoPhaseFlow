"""
CCD sparse PPE solver — base class + LGMRES-primary / LU-fallback variant.

Solves the variable-density Pressure Poisson Equation:

    ∇·(1/ρ ∇p) = q_h,   q_h = (1/Δt) ∇·u*_RC

using the 6th-order CCD product-rule operator (§8b Eq. L_CCD_2d_full):

    (L_CCD^ρ p)_{i,j}
        = (1/ρ)(D_x^{(2)}p + D_y^{(2)}p)
          − (D_x^{(1)}ρ / ρ²) D_x^{(1)}p
          − (D_y^{(1)}ρ / ρ²) D_y^{(1)}p         (§8b Eq. Lx_varrho_discrete)

The CCD 1st/2nd derivative matrices (per axis) are built once via a single
batched CCD call on the identity matrix, then assembled into the 2D operator
via Kronecker products (scipy.sparse.kron) — see app:ccd_kronecker.

Architecture (Template Method pattern, OCP + SRP):
  _CCDPPEBase(IPPESolver) — shared matrix assembly + solve template:
      • _build_1d_ccd_matrices()  — precomputed once in __init__
      • _build_sparse_operator()  — Kronecker product L_CCD^ρ
      • _assemble_pinned_system() — operator + pin + RHS preparation
      • solve()                   — template: assemble → _solve_linear_system
      • compute_residual()        — diagnostic
      • _solve_linear_system()    — abstract; subclasses provide solve strategy

  PPESolverPseudoTime(_CCDPPEBase):
      LGMRES iterative solver (O(n·k) memory, warm start) with sparse LU
      fallback when LGMRES does not converge.

  PPESolverCCDLU(_CCDPPEBase)  [ppe_solver_ccd_lu.py]:
      Always-direct sparse LU (spsolve / SuperLU); no iterative phase.

Adding a new solve strategy requires only implementing _solve_linear_system
in a new subclass — no changes to base or factory (OCP).

IPC integration (§4 sec:ipc_derivation):
    Caller passes δp ≡ p^{n+1}−p^n as the unknown (p_init=None → zeros).
    The operator and BC are identical to the absolute-pressure formulation;
    only the unknown variable changes.

Boundary conditions:
    Neumann ∂p/∂n = 0 at all walls: satisfied through the Rhie-Chow RHS
    and velocity BC.  One interior node is pinned to zero to fix the null
    space: the center node (N//2, N//2) is pinned — invariant under all
    square-domain symmetry operations (x-flip, y-flip, diagonal swap).

Refactoring notes:
    2026-03-20: Replaces FVM+MINRES and GMRES matrix-free implementations.
                Accepts ``ccd`` via constructor injection (DIP).
    2026-03-21: Added Kronecker product matrix assembly (app:ccd_kronecker).
                Switched from LU-only to LGMRES-primary / LU-fallback.
    2026-03-22: Pin moved from corner (0,0) to center (N//2,N//2) to
                avoid symmetry breaking.
    2026-03-22: Extracted _CCDPPEBase (Template Method); PPESolverCCDLU
                now inherits _CCDPPEBase directly (OCP, SRP, DRY).
"""

from __future__ import annotations
import warnings
import numpy as np
from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import SimulationConfig
    from ..core.grid import Grid
    from ..ccd.ccd_solver import CCDSolver

from ..interfaces.ppe_solver import IPPESolver


# ── Shared base: matrix assembly + solve template ──────────────────────────

class _CCDPPEBase(IPPESolver):
    """Abstract base for CCD Kronecker-product PPE solvers (O(h⁶)).

    Handles all matrix assembly (D1/D2 pre-computation, Kronecker products,
    pin-node setup) and the solve template.  Subclasses implement only
    ``_solve_linear_system``, which receives the assembled pinned system.

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter)
    grid    : Grid
    ccd     : CCDSolver  (constructor injection; auto-built if None)
    """

    def __init__(
        self,
        backend: "Backend",
        config: "SimulationConfig",
        grid: "Grid",
        ccd: "CCDSolver | None" = None,
    ) -> None:
        self.xp = backend.xp
        self.backend = backend
        self.ndim = grid.ndim
        self.grid = grid
        self.tol = config.solver.pseudo_tol
        self.maxiter = config.solver.pseudo_maxiter

        if ccd is not None:
            self.ccd = ccd
        else:
            from ..ccd.ccd_solver import CCDSolver as _CCDSolver
            self.ccd = _CCDSolver(grid, backend)

        # Pre-compute 1D CCD derivative matrices once per axis
        self._D1: list = []
        self._D2: list = []
        for ax in range(self.ndim):
            d1, d2 = self._build_1d_ccd_matrices(ax)
            self._D1.append(d1)
            self._D2.append(d2)

    # ── IPPESolver implementation (Template Method) ───────────────────────

    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """Solve the PPE via CCD Kronecker operator (O(h⁶)).

        Assembles the pinned system, then delegates to
        ``_solve_linear_system`` (implemented by subclasses).

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — RHS (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — density field
        dt     : float — time step (unused by this solver; kept for LSP)
        p_init : optional array, shape ``grid.shape`` — warm-start initial
                 guess; pass None for IPC incremental formulation (→ zeros)

        Returns
        -------
        p : array, shape ``grid.shape``
        """
        shape = self.grid.shape
        n = int(np.prod(shape))

        L_pinned, rhs_np = self._assemble_pinned_system(rhs, rho)

        p0 = (
            np.asarray(self.backend.to_host(p_init), dtype=float).ravel()
            if p_init is not None
            else np.zeros(n)
        )

        p_flat = self._solve_linear_system(L_pinned, rhs_np, p0)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                f"{type(self).__name__}: ソルバーが非有限値を返しました。"
                " 右辺または密度場を確認してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        return self.backend.to_device(p_flat.reshape(shape))

    @abstractmethod
    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        """Solve the assembled pinned linear system and return the flat solution.

        Parameters
        ----------
        L_pinned : scipy.sparse.csr_matrix — pinned CCD operator
        rhs_np   : np.ndarray, shape (n,) — RHS with pin row zeroed
        p0       : np.ndarray, shape (n,) — initial guess (may be ignored)

        Returns
        -------
        p_flat : np.ndarray, shape (n,)
        """

    # ── Diagnostic: CCD operator residual ────────────────────────────────

    def compute_residual(self, p, rhs, rho) -> float:
        """Return ‖L_CCD^ρ p − rhs‖₂ (for tests / diagnostics).

        **Diagnostic only — not part of the solve pipeline.**
        This method is not called by production code. Use it in tests or
        one-off validation scripts to verify PPE solve quality.
        The pin node (center, N//2,N//2) is excluded from the residual
        since it carries a gauge constraint, not a PDE equation.

        Parameters
        ----------
        p   : array, shape ``grid.shape`` — pressure field
        rhs : array, shape ``grid.shape`` — PPE RHS
        rho : array, shape ``grid.shape`` — density field

        Returns
        -------
        residual : float
        """
        xp = self.xp
        shape = self.grid.shape
        rho_dev = xp.asarray(self.backend.to_host(rho))
        drho = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(rho_dev, ax)
            drho.append(drho_ax)

        p_dev = xp.asarray(self.backend.to_host(p))
        Lp = xp.zeros(shape, dtype=p_dev.dtype)
        for ax in range(self.ndim):
            dp_ax, d2p_ax = self.ccd.differentiate(p_dev, ax)
            Lp += d2p_ax / rho_dev - (drho[ax] / rho_dev ** 2) * dp_ax

        rhs_dev = xp.asarray(self.backend.to_host(rhs))
        residual = Lp - rhs_dev
        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, self.grid.shape))
        residual_arr = np.asarray(self.backend.to_host(residual))
        residual_arr.ravel()[pin_dof] = 0.0
        return float(np.sqrt(np.sum(residual_arr ** 2)))

    # ── Private helpers ───────────────────────────────────────────────────

    def _assemble_pinned_system(self, rhs, rho):
        """Build the pinned CCD operator and matching RHS vector.

        Shared by all subclasses; eliminates duplication between
        PPESolverPseudoTime and PPESolverCCDLU.

        Returns
        -------
        L_pinned : scipy.sparse.csr_matrix, shape (n, n)
        rhs_np   : np.ndarray, shape (n,)
        """
        rho_np = np.asarray(self.backend.to_host(rho), dtype=float)
        xp = self.xp
        drho_np = []
        for ax in range(self.ndim):
            drho_ax, _ = self.ccd.differentiate(xp.asarray(rho_np), ax)
            drho_np.append(np.asarray(self.backend.to_host(drho_ax), dtype=float))

        L_sparse = self._build_sparse_operator(rho_np, drho_np)

        # Pin center node — invariant under all square-domain symmetries
        pin_idx = tuple(ni // 2 for ni in self.grid.N)
        pin_dof = int(np.ravel_multi_index(pin_idx, self.grid.shape))
        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()

        rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()
        rhs_np[pin_dof] = 0.0

        return L_pinned, rhs_np

    def _build_1d_ccd_matrices(self, axis: int):
        """Build 1D CCD derivative matrices D1, D2 for the given axis.

        Parameters
        ----------
        axis : 0 (x) or 1 (y)

        Returns
        -------
        D1 : np.ndarray, shape (n_pts, n_pts) — D_axis^{(1)} matrix
        D2 : np.ndarray, shape (n_pts, n_pts) — D_axis^{(2)} matrix
        """
        n_pts = self.grid.N[axis] + 1
        I = np.eye(n_pts)

        if axis == 0:
            d1, d2 = self.ccd.differentiate(I, axis=0)
            return np.asarray(d1, dtype=float), np.asarray(d2, dtype=float)
        else:
            # axis=1: differentiate returns d1[k,j] = (D_y^{(1)} e_k)[j]
            # Transpose to recover D1[j,k] = (D_y^{(1)} e_k)[j]
            d1, d2 = self.ccd.differentiate(I, axis=1)
            return np.asarray(d1, dtype=float).T, np.asarray(d2, dtype=float).T

    def _build_sparse_operator(self, rho_np, drho_np):
        """Assemble the sparse L_CCD^ρ matrix via Kronecker products.

        L_CCD^ρ p = (1/ρ)(D2x⊗I_y + I_x⊗D2y)p
                    − (Dρ_x/ρ²)(D1x⊗I_y)p
                    − (Dρ_y/ρ²)(I_x⊗D1y)p

        C-order ravel: flat index k = i·Ny + j.  D2x acts on the slow
        (row) index → kron(D2x, I_y); D2y acts on the fast (column)
        index → kron(I_x, D2y).  See KL-08 (docs/LESSONS.md).

        Parameters
        ----------
        rho_np  : np.ndarray, shape ``grid.shape``
        drho_np : list of np.ndarray (one per axis)

        Returns
        -------
        L : scipy.sparse.csr_matrix, shape (n, n)
        """
        import scipy.sparse as sp

        shape = self.grid.shape
        Nx, Ny = shape

        D1x = self._D1[0]
        D2x = self._D2[0]
        D1y = self._D1[1]
        D2y = self._D2[1]

        D2x_full = sp.kron(sp.csr_matrix(D2x), sp.eye(Ny), format='csr')
        D2y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(D2y), format='csr')
        D1x_full = sp.kron(sp.csr_matrix(D1x), sp.eye(Ny), format='csr')
        D1y_full = sp.kron(sp.eye(Nx), sp.csr_matrix(D1y), format='csr')

        rho_flat = rho_np.ravel()
        drho_x_flat = drho_np[0].ravel()
        drho_y_flat = drho_np[1].ravel() if self.ndim > 1 else np.zeros_like(rho_flat)

        inv_rho = sp.diags(1.0 / rho_flat, format='csr')
        coeff_x = sp.diags(drho_x_flat / rho_flat ** 2, format='csr')
        coeff_y = sp.diags(drho_y_flat / rho_flat ** 2, format='csr')

        L = (inv_rho @ (D2x_full + D2y_full)
             - coeff_x @ D1x_full
             - coeff_y @ D1y_full)

        return L.tocsr()


# ── LGMRES-primary / LU-fallback variant ───────────────────────────────────

class PPESolverPseudoTime(_CCDPPEBase):
    """CCD variable-density PPE solver — LGMRES primary, LU fallback (O(h⁶)).

    Parameters
    ----------
    backend : Backend
    config  : SimulationConfig  (pseudo_tol, pseudo_maxiter)
    grid    : Grid
    ccd     : CCDSolver  (constructor injection; auto-built if None)
    """

    def _solve_linear_system(
        self,
        L_pinned,
        rhs_np: np.ndarray,
        p0: np.ndarray,
    ) -> np.ndarray:
        """LGMRES iterative solve (O(n·k) memory) with sparse LU fallback.

        The CCD operator is highly asymmetric (max asymmetry ~900 for N=16)
        due to compact one-sided boundary schemes; standard GMRES diverges on
        some grids.  LGMRES (augmented Krylov) is more robust; the LU fallback
        ensures no blocking when LGMRES does not converge.

        atol: fp64 floor prevents spurious non-convergence when ‖rhs‖ is tiny
        (e.g. immediately after initialisation).  See KL-09 (docs/LESSONS.md).
        """
        import scipy.sparse.linalg as spla

        atol = max(1e-14, self.tol * float(np.linalg.norm(rhs_np)))
        p_flat, info = spla.lgmres(
            L_pinned, rhs_np,
            x0=p0,
            rtol=self.tol,
            maxiter=self.maxiter,
            atol=atol,
        )

        if info != 0:
            warnings.warn(
                f"CCD-PPE LGMRES が収束しませんでした (info={info})。"
                " スパース LU にフォールバックします。",
                RuntimeWarning,
                stacklevel=2,
            )
            p_flat = spla.spsolve(L_pinned, rhs_np)

        return p_flat
