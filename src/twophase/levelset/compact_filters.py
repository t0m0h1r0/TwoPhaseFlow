"""
Compact implicit filters for interface curvature computation.

Provides two high-order filters that target intermediate wavenumbers
(kh ~ π/4 – π/2), where the standard Laplacian/biharmonic explicit filters
are ineffective.

Classes
-------
HelmholtzKappaFilter
    Implicit Helmholtz filter applied to κ:
        (I − α h² ∇²) κ* = κ         per axis (operator-splitting)
    Transfer function: H(ξ) = 1 / (1 + 2α(1−cosξ))   (unconditionally stable)

LeleCompactFilter
    Padé compact filter applied to φ (before CCD differentiation):
        α_f f̂_{j-1} + f̂_j + α_f f̂_{j+1} = ((1+2α_f)/4)(f_{j-1}+2f_j+f_{j+1})
    Transfer function: H(ξ) = (1+2α_f)(1+cosξ) / (2(1+2α_f cosξ))
    Kim (2010) prescription: given ξ_c, set α_f = −cos(ξ_c)/2  → H(ξ_c) = 0.5.

A3 traceability
───────────────
  Helmholtz  → Olsson, Kreiss & Zahedi, J. Comput. Phys. 225:785–807, 2007; §3
  Padé/Lele  → Lele, J. Comput. Phys. 103:16–42, 1992; Table 3
  Kim param. → Kim, Computers & Fluids 39:1168–1182, 2010; §3

§ Stability
────────────
  Helmholtz (splitting per axis):
      H_ax(ξ) = 1/(1+2α(1−cosξ)) ∈ (0,1]  for α > 0  → unconditionally stable
  Padé compact:
      H(ξ) ∈ (0,1] iff α_f ∈ (−0.5, 0.5)  (spectral radius of LHS < 1)
      Kim prescription: |α_f| = |cos(ξ_c)|/2 < 0.5  for ξ_c ∈ (0, π) ✓

§ Solver backend
─────────────────
  Both filters perform 1-D tridiagonal solves (one per axis) via
  scipy.linalg.solve_banded with LAPACK's dgbsv.
  Input/output arrays are kept in the caller's xp namespace;
  solve is performed in NumPy (CPU) regardless of backend.
"""

from __future__ import annotations
import numpy as np
from scipy.linalg import solve_banded
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..ccd.ccd_solver import CCDSolver
    from ..backend import Backend


# ── Shared helper ─────────────────────────────────────────────────────────────

def _banded_solve_along_axis(ab: np.ndarray, rhs: np.ndarray, ax: int) -> np.ndarray:
    """Apply 1-D banded solve along axis ``ax`` of ``rhs``.

    Parameters
    ----------
    ab  : (3, n) banded matrix in solve_banded format (l=u=1):
              ab[0, 1:]  = upper diagonal
              ab[1, :]   = main  diagonal
              ab[2, :-1] = lower diagonal
    rhs : ndarray of arbitrary shape; axis ``ax`` has length n.

    Returns
    -------
    x : ndarray, same shape as rhs.
    """
    n = rhs.shape[ax]
    # Move the target axis to front: shape (n, *batch)
    moved = np.moveaxis(rhs, ax, 0)
    batch_shape = moved.shape[1:]
    rhs_2d = moved.reshape(n, -1)                 # (n, batch)
    x_2d = solve_banded((1, 1), ab, rhs_2d)       # (n, batch)
    x_moved = x_2d.reshape((n,) + batch_shape)    # (n, *batch)
    return np.moveaxis(x_moved, 0, ax)             # restore original order


# ── Helmholtz κ filter ────────────────────────────────────────────────────────

class HelmholtzKappaFilter:
    """Implicit Helmholtz low-pass filter applied to curvature κ.

    Equation (A3: Olsson et al. 2007 §3):

        (I − α h² ∇²) κ*  =  κ          (per axis, operator-splitting)

    Discrete 1-D system along axis ax (uniform spacing h):

        −α κ*_{j−1}  +  (1+2α) κ*_j  −  α κ*_{j+1}  =  κ_j

    Boundary condition (Neumann, zero-flux):

        (1+α) κ*_0  −  α κ*_1  =  κ_0
        −α κ*_{N−1}  +  (1+α) κ*_N  =  κ_N

    Transfer function (interior, uniform h):

        H(ξ) = 1 / (1 + 2α(1−cosξ))         ξ = kh

    Properties: H(0)=1, H(π)=1/(1+4α), monotone decrease, always in (0,1].
    Unconditionally stable for all α > 0.

    Interface blending (post-solve):

        κ_out  =  w(ψ) · κ*  +  (1−w(ψ)) · κ        w = 4ψ(1−ψ)

    Only the interface band (ψ ≈ 0.5) is strongly filtered; the bulk is
    left unchanged.

    Parameters
    ----------
    backend : Backend
    ccd     : CCDSolver — used only for grid metadata (n_pts, h per axis)
    alpha   : float  — filter strength (default 1.0).
                       H(π/4) = 1/(1+0.586α); for α=1: 37% damping per pass.
                       Recommended: 0.5–2.0.
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        alpha: float = 1.0,
    ):
        self.xp = backend.xp
        self.alpha = alpha
        grid = ccd.grid
        ndim = ccd.ndim

        # Pre-build banded matrices (one per axis); coefficients are constant
        self._ab: dict[int, np.ndarray] = {}
        for ax in range(ndim):
            n = grid.N[ax] + 1
            a = alpha                 # h² cancels: −α × (Δf/h²) × h² = −α Δf
            main = np.full(n, 1.0 + 2.0 * a)
            main[0]  = 1.0 + a       # Neumann BC: ghost = boundary value
            main[-1] = 1.0 + a
            off = np.full(n - 1, -a)
            ab = np.zeros((3, n))
            ab[0, 1:]  = off         # upper (shifted right in solve_banded)
            ab[1, :]   = main
            ab[2, :-1] = off         # lower (shifted left  in solve_banded)
            self._ab[ax] = ab

        self._ndim = ndim

    # ── Public API ─────────────────────────────────────────────────────────

    def apply(self, q, psi):
        """Apply Helmholtz filter to scalar field q, blended at interface.

        Parameters
        ----------
        q   : array  — curvature field κ
        psi : array  — CLS field ψ ∈ (0,1)

        Returns
        -------
        κ_out : array — filtered field (same namespace as q)
        """
        xp = self.xp
        q_np   = np.asarray(q)
        psi_np = np.asarray(psi)

        # ── Operator-splitting: solve per axis ──────────────────────────
        q_filt = q_np.copy()
        for ax in range(self._ndim):
            q_filt = _banded_solve_along_axis(self._ab[ax], q_filt, ax)

        # ── Interface-band blending ──────────────────────────────────────
        w = 4.0 * psi_np * (1.0 - psi_np)   # peaks at 1 when ψ=0.5
        q_out = w * q_filt + (1.0 - w) * q_np

        return xp.asarray(q_out)


# ── Padé compact filter (Lele 1992 / Kim 2010) ───────────────────────────────

class LeleCompactFilter:
    """Padé compact low-pass filter applied to a scalar field φ.

    Filter equation (A3: Lele 1992 Table 3; 4th-order symmetric):

        α_f f̂_{j−1}  +  f̂_j  +  α_f f̂_{j+1}
            =  ((1+2α_f)/4) · (f_{j−1} + 2f_j + f_{j+1})

    Transfer function:

        H(ξ) = (1+2α_f)(1+cosξ) / (2(1+2α_f cosξ))     ξ = kh

    Kim (2010) cut-off prescription:
        Given target −3 dB wavenumber ξ_c:  α_f = −cos(ξ_c) / 2
        → H(ξ_c) = 0.5 exactly.

    Boundary treatment (Neumann ghost):
        Left  (j=0): (1+α_f) f̂_0  + α_f f̂_1   = RHS_0
        Right (j=N): α_f f̂_{N−1} + (1+α_f) f̂_N = RHS_N
        RHS_j uses ghost f_{−1} = f_0, f_{N+1} = f_N.

    Parameters
    ----------
    backend : Backend
    ccd     : CCDSolver — grid metadata
    xi_c    : float  — target cut-off wavenumber ξ_c ∈ (0, π) (Kim prescription).
                       Overrides alpha_f if both are given.
    alpha_f : float  — Padé off-diagonal coefficient ∈ (−0.5, 0.5).
                       Used directly if xi_c is None.
    """

    def __init__(
        self,
        backend: "Backend",
        ccd: "CCDSolver",
        xi_c: float | None = None,
        alpha_f: float | None = None,
    ):
        self.xp = backend.xp
        grid = ccd.grid
        ndim = ccd.ndim

        # ── Resolve α_f ────────────────────────────────────────────────
        if xi_c is not None:
            # Kim (2010) prescription: H(ξ_c) = 0.5 → α_f = −cos(ξ_c)/2
            alpha_f = -np.cos(xi_c) / 2.0
        elif alpha_f is None:
            raise ValueError("Provide xi_c or alpha_f")

        if not (-0.5 < alpha_f < 0.5):
            raise ValueError(
                f"alpha_f={alpha_f:.4f} outside stable range (−0.5, 0.5). "
                f"Choose ξ_c ∈ (0, π)."
            )

        self.alpha_f = float(alpha_f)
        self.xi_c = float(xi_c) if xi_c is not None else None
        self._ndim = ndim

        # ── Pre-build banded matrices (one per axis) ────────────────────
        af = self.alpha_f
        self._ab_lhs: dict[int, np.ndarray] = {}
        self._rhs_coeff: dict[int, tuple] = {}  # (a0, a1) per axis
        for ax in range(ndim):
            n = grid.N[ax] + 1
            # LHS: (α_f, 1, α_f) tridiagonal
            main = np.ones(n)
            main[0]  = 1.0 + af    # Neumann ghost: left
            main[-1] = 1.0 + af    # Neumann ghost: right
            off = np.full(n - 1, af)
            ab = np.zeros((3, n))
            ab[0, 1:]  = off
            ab[1, :]   = main
            ab[2, :-1] = off
            self._ab_lhs[ax] = ab
            # RHS coefficients: a0=a1=(1+2α_f)/2 → stencil (a1/2, a0, a1/2)
            a01 = (1.0 + 2.0 * af) / 2.0
            self._rhs_coeff[ax] = a01   # RHS = a01/2*(f_{j-1}+f_{j+1}) + a01*f_j

    # ── Public API ─────────────────────────────────────────────────────────

    def apply(self, f):
        """Apply Padé compact filter to scalar field f along every axis.

        Parameters
        ----------
        f : array  — field to filter (φ, n_i, or κ)

        Returns
        -------
        f̂ : array — filtered field (same namespace as f)
        """
        xp = self.xp
        f_np = np.asarray(f)
        f_filt = f_np.copy()

        for ax in range(self._ndim):
            f_filt = self._apply_axis(f_filt, ax)

        return xp.asarray(f_filt)

    # ── Private ────────────────────────────────────────────────────────────

    def _apply_axis(self, f: np.ndarray, ax: int) -> np.ndarray:
        n = f.shape[ax]
        a01 = self._rhs_coeff[ax]

        # Build RHS: a01 * f_j + (a01/2) * (f_{j-1} + f_{j+1})
        # Using np.roll for periodic neighbours (then fix boundaries)
        f_prev = np.roll(f, 1,  axis=ax)  # f_{j-1}
        f_next = np.roll(f, -1, axis=ax)  # f_{j+1}

        rhs = a01 * f + (a01 / 2.0) * (f_prev + f_next)

        # Fix boundary RHS (Neumann ghost: f_{-1}=f_0, f_{N+1}=f_N)
        sl0 = [slice(None)] * f.ndim; sl0[ax] = 0
        sl1 = [slice(None)] * f.ndim; sl1[ax] = 1
        slN = [slice(None)] * f.ndim; slN[ax] = -1
        slNm = [slice(None)] * f.ndim; slNm[ax] = -2

        # At j=0: f_prev used f_N (from roll) — replace with f_0 (ghost)
        # rhs[0] = a01*f[0] + (a01/2)*(f[0] + f[1])  (ghost=f[0])
        rhs[tuple(sl0)] = a01 * f[tuple(sl0)] + (a01 / 2.0) * (f[tuple(sl0)] + f[tuple(sl1)])
        # At j=N: f_next used f_0 (from roll) — replace with f_N (ghost)
        rhs[tuple(slN)] = a01 * f[tuple(slN)] + (a01 / 2.0) * (f[tuple(slNm)] + f[tuple(slN)])

        return _banded_solve_along_axis(self._ab_lhs[ax], rhs, ax)
