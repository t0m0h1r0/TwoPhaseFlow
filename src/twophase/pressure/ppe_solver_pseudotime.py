"""
CCD sparse PPE solver — base class + LGMRES iterative variant.

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
      LGMRES iterative solver (O(n·k) memory, warm start).  Returns
      the best iterate when LGMRES does not converge (no LU fallback).

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
    2026-04-01: Removed LU fallback — LGMRES returns best iterate on
                non-convergence.  Paper alignment (§app:ccd_lu_direct).
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
    from ..core.boundary import BoundarySpec

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
        bc_spec: "BoundarySpec | None" = None,
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

        # 境界条件仕様（pin DOF 等の共通導出）
        if bc_spec is not None:
            self._bc_spec = bc_spec
        else:
            from ..core.boundary import BoundarySpec as _BS
            self._bc_spec = _BS(
                bc_type=config.numerics.bc_type,
                shape=grid.shape,
                N=grid.N,
            )

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

        if self._periodic:
            Nx, Ny = self.grid.N
            n_reduced = Nx * Ny
        else:
            n_reduced = int(np.prod(shape))

        L_pinned, rhs_np = self._assemble_pinned_system(rhs, rho)

        if p_init is not None:
            p_host = np.asarray(self.backend.to_host(p_init), dtype=float)
            if self._periodic:
                p0 = p_host[:Nx, :Ny].ravel()
            else:
                p0 = p_host.ravel()
        else:
            p0 = np.zeros(n_reduced)

        p_flat = self._solve_linear_system(L_pinned, rhs_np, p0)

        if not np.isfinite(p_flat).all():
            warnings.warn(
                f"{type(self).__name__}: ソルバーが非有限値を返しました。"
                " 右辺または密度場を確認してください。",
                RuntimeWarning,
                stacklevel=2,
            )

        if self._periodic:
            # Expand N×N → (N+1)×(N+1): node N = node 0
            p_red = p_flat.reshape(Nx, Ny)
            p_full = np.empty(shape)
            p_full[:Nx, :Ny] = p_red
            p_full[Nx, :Ny] = p_red[0, :]
            p_full[:Nx, Ny] = p_red[:, 0]
            p_full[Nx, Ny] = p_red[0, 0]
            return self.backend.to_device(p_full)
        else:
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
        pin_dof = self._bc_spec.pin_dof
        residual_arr = np.asarray(self.backend.to_host(residual))
        residual_arr.ravel()[pin_dof] = 0.0
        return float(np.sqrt(np.sum(residual_arr ** 2)))

    # ── Private helpers ───────────────────────────────────────────────────

    def _assemble_pinned_system(self, rhs, rho):
        """Build the pinned CCD operator and matching RHS vector.

        Shared by all subclasses; eliminates duplication between
        PPESolverPseudoTime and PPESolverCCDLU.

        For periodic BC the operator is N²×N² (nodes 0..N-1 per axis).
        The RHS is trimmed to N×N and the pin is in the reduced space.

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

        if self._periodic:
            # Reduced DOF space: N×N
            Nx, Ny = self.grid.N
            reduced_shape = (Nx, Ny)
            pin_dof = self._bc_spec.pin_dof_in_shape(reduced_shape)

            rhs_full = np.asarray(self.backend.to_host(rhs), dtype=float)
            rhs_np = rhs_full[:Nx, :Ny].ravel()
        else:
            pin_dof = self._bc_spec.pin_dof
            rhs_np = np.asarray(self.backend.to_host(rhs), dtype=float).ravel()

        L_lil = L_sparse.tolil()
        L_lil[pin_dof, :] = 0.0
        L_lil[pin_dof, pin_dof] = 1.0
        L_pinned = L_lil.tocsr()
        rhs_np[pin_dof] = 0.0

        return L_pinned, rhs_np

    @property
    def _periodic(self) -> bool:
        return getattr(self.ccd, 'bc_type', 'wall') == 'periodic'

    def _build_1d_ccd_matrices(self, axis: int):
        """Build 1D CCD derivative matrices D1, D2 for the given axis.

        For wall BC: (N+1)×(N+1) matrices (all nodes independent).
        For periodic BC: N×N matrices (nodes 0..N-1; node N = node 0).

        Parameters
        ----------
        axis : 0 (x) or 1 (y)

        Returns
        -------
        D1 : np.ndarray — D_axis^{(1)} matrix
        D2 : np.ndarray — D_axis^{(2)} matrix
        """
        n_full = self.grid.N[axis] + 1

        if self._periodic:
            # Periodic: N unique DOFs per axis (0..N-1).  Node N = node 0.
            # We build a "probing" matrix that maps N-DOF input to (N+1)-node
            # field (copying DOF 0 to node N), differentiates, and extracts
            # the N unique output rows/columns.
            N_ax = self.grid.N[axis]
            if axis == 0:
                # Probe: each column j is a (N+1)-node field with 1 at node j
                # and node N copies node 0.  Shape: (N+1, N_ax).
                I_per = np.zeros((n_full, N_ax))
                for j in range(N_ax):
                    I_per[j, j] = 1.0
                I_per[N_ax, 0] = 1.0
                d1, d2 = self.ccd.differentiate(I_per, axis=0)
                # d1 shape: (N+1, N_ax).  Take rows 0..N_ax-1.
                return np.asarray(d1, dtype=float)[:N_ax, :], np.asarray(d2, dtype=float)[:N_ax, :]
            else:
                # axis=1: CCD expects shape[1] = N+1.
                # Probe: (N_ax, N+1) where row j has 1 at column j,
                # and column N copies column 0.
                N_other = self.grid.N[0] + 1  # full size of axis 0
                I_per = np.zeros((N_ax, n_full))
                for j in range(N_ax):
                    I_per[j, j] = 1.0
                I_per[0, N_ax] = 1.0  # column N = column 0 for input
                # But we need shape (*, N+1) for axis=1 differentiation.
                # Reshape: (N_ax, N+1) — each of N_ax "batch" items along axis 0.
                d1, d2 = self.ccd.differentiate(I_per, axis=1)
                # d1 shape: (N_ax, N+1).  Output[j, i] = D_y e_j evaluated at node i.
                # We want D1[i, j] = (D_y e_j)[i], so transpose.
                # Take rows 0..N_ax-1 from the transposed result.
                d1_np = np.asarray(d1, dtype=float)[:, :N_ax]  # (N_ax, N_ax)
                d2_np = np.asarray(d2, dtype=float)[:, :N_ax]
                return d1_np.T, d2_np.T
        else:
            I = np.eye(n_full)
            if axis == 0:
                d1, d2 = self.ccd.differentiate(I, axis=0)
                return np.asarray(d1, dtype=float), np.asarray(d2, dtype=float)
            else:
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

        For periodic BC, the operator uses N×N DOFs per axis (nodes 0..N-1),
        and rho/drho are trimmed to N×N accordingly.

        Parameters
        ----------
        rho_np  : np.ndarray, shape ``grid.shape`` (N+1, N+1)
        drho_np : list of np.ndarray (one per axis), shape ``grid.shape``

        Returns
        -------
        L : scipy.sparse.csr_matrix
            Wall:     shape ((N+1)², (N+1)²)
            Periodic: shape (N², N²)
        """
        import scipy.sparse as sp

        D1x = self._D1[0]
        D2x = self._D2[0]
        D1y = self._D1[1]
        D2y = self._D2[1]

        # Matrix dimension per axis (N for periodic, N+1 for wall)
        mx = D1x.shape[0]
        my = D1y.shape[0]

        D2x_full = sp.kron(sp.csr_matrix(D2x), sp.eye(my), format='csr')
        D2y_full = sp.kron(sp.eye(mx), sp.csr_matrix(D2y), format='csr')
        D1x_full = sp.kron(sp.csr_matrix(D1x), sp.eye(my), format='csr')
        D1y_full = sp.kron(sp.eye(mx), sp.csr_matrix(D1y), format='csr')

        # For periodic BC, trim rho/drho to N×N (nodes 0..N-1)
        if self._periodic:
            Nx, Ny = self.grid.N
            rho_trimmed = rho_np[:Nx, :Ny]
            drho_x_trimmed = drho_np[0][:Nx, :Ny]
            drho_y_trimmed = drho_np[1][:Nx, :Ny] if self.ndim > 1 else np.zeros_like(rho_trimmed)
        else:
            rho_trimmed = rho_np
            drho_x_trimmed = drho_np[0]
            drho_y_trimmed = drho_np[1] if self.ndim > 1 else np.zeros_like(rho_trimmed)

        rho_flat = rho_trimmed.ravel()
        drho_x_flat = drho_x_trimmed.ravel()
        drho_y_flat = drho_y_trimmed.ravel()

        inv_rho = sp.diags(1.0 / rho_flat, format='csr')
        coeff_x = sp.diags(drho_x_flat / rho_flat ** 2, format='csr')
        coeff_y = sp.diags(drho_y_flat / rho_flat ** 2, format='csr')

        L = (inv_rho @ (D2x_full + D2y_full)
             - coeff_x @ D1x_full
             - coeff_y @ D1y_full)

        return L.tocsr()


# ── LGMRES-primary / LU-fallback variant ───────────────────────────────────

class PPESolverPseudoTime(_CCDPPEBase):
    """CCD variable-density PPE solver — LGMRES iterative (O(h⁶)).

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
        """LGMRES iterative solve (O(n·k) memory), no LU fallback.

        The CCD operator is highly asymmetric (max asymmetry ~900 for N=16)
        due to compact one-sided boundary schemes; standard GMRES diverges on
        some grids.  LGMRES (augmented Krylov) is more robust.  When LGMRES
        does not converge within maxiter, the best iterate is returned with
        a warning — no direct-solver fallback.

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
                f"CCD-PPE LGMRES が収束しませんでした (info={info}, "
                f"maxiter={self.maxiter}, tol={self.tol})。"
                " 最良反復解を返します。",
                RuntimeWarning,
                stacklevel=2,
            )

        return p_flat
