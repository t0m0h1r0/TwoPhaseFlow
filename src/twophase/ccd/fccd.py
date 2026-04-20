"""
FCCD (Face-Centered Combined Compact Difference) solver.

Implements the face-located 4th-order compact difference scheme established in
short papers SP-C (matrix formulation) and SP-D (advection extension).

Face gradient (uniform grid, SP-C §4 boxed equation):

    d_{f_{i-1/2}} = (u_i - u_{i-1})/H - (H/24)(q_i - q_{i-1})

where q = S_CCD u is the nodal CCD second derivative, obtained from
``CCDSolver.differentiate`` which returns both d1 and d2 in one call — no
extra block solve is required by FCCD.

Non-uniform cell-centred face (θ = 1/2 → μ = 0, λ = 1/24 per SP-C §5):

    d_{f_{i-1/2}} = (u_i - u_{i-1})/H_i - (H_i/24)(q_i - q_{i-1})

with per-face H_i = x_i - x_{i-1}.

4th-order face value interpolation (SP-D §5):

    u_{f_{i-1/2}} = (u_{i-1} + u_i)/2 - (H^2/16)(q_{i-1} + q_i)/2 + O(H^4)

4th-order Hermite face→node reconstructor R_4 (SP-D §6, Option C):

    (∂_x u)_i = 0.5(d_{f_{i-1/2}} + d_{f_{i+1/2}}) - (H/16)(q_{i+1} - q_{i-1}) + O(H^4)

The H/16 correction cancels the (H²/8)·u''' leading term of the plain average.

Conservative face-flux advection (SP-D §7, Option B):

    F^{(k)}_{f_{i-1/2}} = u^{(k)}_{f} · (∂_{x_k} u^{(j)})_{f}   (non-conservative)
    F^{(k)cons}_{f_{i-1/2}} = u^{(k)}_{f} · u^{(j)}_{f}        (conservative)
    [∇ · F^{(j)}]_i = Σ_k (F^{(k)}_{f_{i+1/2}} - F^{(k)}_{f_{i-1/2}}) / H_i

Wall BC:
    Option III (Neumann fields ψ, p): boundary faces zero.
    Option IV (Dirichlet u no-slip): ghost mirror sign-flip.

Periodic BC: inherited block-circulant structure from CCDSolver;
face operator is circulant, leading DFT truncation −7(ωH)⁴/5760 at face.

References: SP-C, SP-D; WIKI-T-046, T-050, T-051, T-053, T-054, T-055, T-056.
"""

from __future__ import annotations
import math
from typing import List, Optional, TYPE_CHECKING

from .ccd_solver import CCDSolver
from ..backend import fuse as _fuse

if TYPE_CHECKING:
    from ..core.grid import Grid
    from ..backend import Backend


# ── Fused face stencils (collapse to single CUDA kernel on GPU) ──────────


@_fuse
def _face_gradient_kernel(u_lo, u_hi, q_lo, q_hi, inv_H, H_over_24):
    """d_f = (u_hi - u_lo)/H - (H/24)*(q_hi - q_lo). SP-C §4 / §5."""
    return (u_hi - u_lo) * inv_H - H_over_24 * (q_hi - q_lo)


@_fuse
def _face_value_kernel(u_lo, u_hi, q_lo, q_hi, H_sq_over_32):
    """u_f = (u_lo + u_hi)/2 - (H²/32)*(q_lo + q_hi). SP-D §5."""
    return 0.5 * (u_lo + u_hi) - H_sq_over_32 * (q_lo + q_hi)


@_fuse
def _hermite_kernel(d_L, d_R, q_m1, q_p1, H_over_16):
    """node = 0.5*(d_L + d_R) - (H/16)*(q_p1 - q_m1). SP-D §6 R_4."""
    return 0.5 * (d_L + d_R) - H_over_16 * (q_p1 - q_m1)


# ── FCCD solver ─────────────────────────────────────────────────────────


class FCCDSolver:
    """Face-centered compact-difference differentiator.

    Composes the nodal CCD second derivative ``q = S_CCD u`` with sparse
    bidiagonal face stencils to produce 4th-order face gradients (Option A
    primitive), 4th-order face interpolation (new Option B primitive), and
    4th-order node gradients via Hermite reconstruction (Option C).

    Parameters
    ----------
    grid : Grid
    backend : Backend  — provides ``xp`` array namespace and device branching.
    bc_type : str, default ``"wall"`` — also accepts ``"periodic"``.
    ccd_solver : CCDSolver, optional
        Existing CCD solver to share pre-factored block LU. If None, a new
        one is constructed. Sharing avoids duplicate factorisation.

    Notes
    -----
    FCCD cost per ``face_gradient`` call is one CCDSolver.differentiate
    (already amortised by callers that also need d2) plus O(N) face
    stencils. When the caller passes ``q`` explicitly (pre-computed from
    a prior CCD call), the FCCD path reduces to O(N) face stencils only.
    """

    def __init__(
        self,
        grid: "Grid",
        backend: "Backend",
        bc_type: str = "wall",
        ccd_solver: Optional[CCDSolver] = None,
    ) -> None:
        self.grid = grid
        self.backend = backend
        self.xp = backend.xp
        self.ndim = grid.ndim
        self.bc_type = bc_type
        self._ccd = ccd_solver if ccd_solver is not None else CCDSolver(
            grid, backend, bc_type
        )

        self._weights = [self._precompute_weights(ax) for ax in range(self.ndim)]

    # ── Pre-computation ──────────────────────────────────────────────────

    def _precompute_weights(self, ax: int) -> dict:
        """Precompute per-axis geometric constants.

        For cell-centred faces (θ = 1/2) on either uniform or non-uniform
        grids, μ = 0 and λ = 1/24 per SP-C §5; the non-uniform formula
        reduces to the uniform one with per-face H_i. We therefore only
        distinguish scalar vs array weights, not uniform vs non-uniform.
        """
        xp = self.xp
        N_faces = self.grid.N[ax]
        coords_host = self.grid.coords[ax]  # (N+1,) numpy
        H_host = coords_host[1:] - coords_host[:-1]   # (N,) face widths

        if self.grid.uniform:
            H = float(H_host[0])
            return {
                "uniform": True,
                "H": H,
                "inv_H": 1.0 / H,
                "H_over_24": H / 24.0,
                "H_sq_over_32": H * H / 32.0,
                "H_over_16": H / 16.0,
                "N_faces": N_faces,
            }

        H = xp.asarray(H_host)
        return {
            "uniform": False,
            "H": H,
            "inv_H": 1.0 / H,
            "H_over_24": H / 24.0,
            "H_sq_over_32": H * H / 32.0,
            # H/16 is applied at NODE positions for R_4; use mean of adjacent faces.
            "H_over_16_node": self._node_H_over_16(H_host),
            "N_faces": N_faces,
        }

    def _node_H_over_16(self, H_host):
        """Per-node H/16 = (H_i + H_{i+1})/2 / 16 for R_4 correction (node i)."""
        import numpy as np
        H_node = np.zeros(len(H_host) + 1)
        H_node[1:-1] = 0.5 * (H_host[:-1] + H_host[1:])
        H_node[0] = H_host[0]    # boundary — one-sided
        H_node[-1] = H_host[-1]
        return self.xp.asarray(H_node / 16.0)

    # ── Face-to-node slicing helpers ─────────────────────────────────────

    def _face_slice(self, u, axis):
        """Return (u_lo, u_hi) slices of a nodal array for face stencil.

        Shape (N, ...) along axis, where N = grid.N[axis].

        Wall BC: u_lo = u[0:N], u_hi = u[1:N+1] — N interior faces.
        Periodic BC: uses only u[0:N] and wraps via xp.roll.
        """
        xp = self.xp
        u = xp.asarray(u)
        u = xp.moveaxis(u, axis, 0)   # (N+1, *rest)
        if self.bc_type == "periodic":
            N = self.grid.N[axis]
            u_unique = u[:N]
            u_lo = xp.roll(u_unique, 1, axis=0)
            u_hi = u_unique
        else:
            u_lo = u[:-1]
            u_hi = u[1:]
        return u_lo, u_hi

    def _broadcast_axis0(self, w, ndim: int):
        """Reshape a 1-D weight array to broadcast against axis-0-first arrays."""
        shape = [1] * ndim
        shape[0] = -1
        return w.reshape(shape)

    # ── Public primitives ────────────────────────────────────────────────

    def face_gradient(self, u, axis: int, q=None):
        """FCCD 4th-order face gradient along ``axis``.

        Parameters
        ----------
        u : array, shape ``grid.shape``
        axis : int
        q : array or None
            Pre-computed nodal CCD second derivative (same shape as ``u``).
            If None, computed via the internal CCD solver.

        Returns
        -------
        d_face : array, shape ``grid.shape`` with axis dim replaced by
            ``grid.N[axis]`` (i.e., one less along ``axis``).
        """
        xp = self.xp
        if q is None:
            _, q = self._ccd.differentiate(u, axis)
        u_lo, u_hi = self._face_slice(u, axis)
        q_lo, q_hi = self._face_slice(q, axis)

        w = self._weights[axis]
        if w["uniform"]:
            d_face = _face_gradient_kernel(
                u_lo, u_hi, q_lo, q_hi, w["inv_H"], w["H_over_24"]
            )
        else:
            inv_H = self._broadcast_axis0(w["inv_H"], u_lo.ndim)
            H_over_24 = self._broadcast_axis0(w["H_over_24"], u_lo.ndim)
            d_face = _face_gradient_kernel(
                u_lo, u_hi, q_lo, q_hi, inv_H, H_over_24
            )

        return xp.moveaxis(d_face, 0, axis)

    def face_value(self, u, axis: int, q=None):
        """4th-order compact face-value interpolation (SP-D §5).

        u_f = (u_lo + u_hi)/2 - (H²/32)(q_lo + q_hi) + O(H⁴)

        Parameters mirror ``face_gradient``.
        """
        xp = self.xp
        if q is None:
            _, q = self._ccd.differentiate(u, axis)
        u_lo, u_hi = self._face_slice(u, axis)
        q_lo, q_hi = self._face_slice(q, axis)

        w = self._weights[axis]
        if w["uniform"]:
            H_sq_over_32 = w["H_sq_over_32"]
        else:
            H_sq_over_32 = self._broadcast_axis0(w["H_sq_over_32"], u_lo.ndim)

        u_f = _face_value_kernel(u_lo, u_hi, q_lo, q_hi, H_sq_over_32)
        return xp.moveaxis(u_f, 0, axis)

    def node_gradient(self, u, axis: int, q=None):
        """4th-order node gradient via R_4 Hermite reconstruction (SP-D §6).

        (∂_x u)_i = 0.5(d_{f_{i-1/2}} + d_{f_{i+1/2}}) - (H/16)(q_{i+1} - q_{i-1})

        Output shape matches input (node array). This is a drop-in
        replacement for ``ccd.differentiate(u, axis)[0]``.

        Boundary nodes (wall BC):
            i=0 : one-sided (uses only face f_{1/2}); order reduces to O(H²)
            i=N : one-sided mirror; order reduces to O(H²)

        Periodic BC: no boundary loss; all nodes use full R_4 stencil.
        """
        xp = self.xp
        if q is None:
            _, q = self._ccd.differentiate(u, axis)
        d_face = self.face_gradient(u, axis, q=q)   # shape (..., N, ...)
        w = self._weights[axis]

        # Move axes to front for slicing
        d_face = xp.moveaxis(d_face, axis, 0)       # (N, *rest)
        q_moved = xp.moveaxis(xp.asarray(q), axis, 0)  # (N+1, *rest)

        N = self.grid.N[axis]

        if self.bc_type == "periodic":
            # Periodic: output has shape (N+1, *rest) with out[N] = out[0]
            # For interior nodes 0..N-1: out[i] = 0.5*(d_face[i] + d_face[(i+1) mod N])
            #                                    - (H/16)*(q[i+1] - q[i-1])
            # d_face is indexed 0..N-1; d_face[(i+1) mod N] uses wrap.
            d_L = d_face                                   # (N, *rest)
            d_R = xp.roll(d_face, -1, axis=0)             # d_face[(i+1) mod N]
            q_unique = q_moved[:N]
            q_m1 = xp.roll(q_unique, 1, axis=0)
            q_p1 = xp.roll(q_unique, -1, axis=0)
            if w["uniform"]:
                node_grad_unique = _hermite_kernel(d_L, d_R, q_m1, q_p1, w["H_over_16"])
            else:
                H_over_16 = self._broadcast_axis0(w["H_over_16_node"][:N], d_L.ndim)
                node_grad_unique = _hermite_kernel(d_L, d_R, q_m1, q_p1, H_over_16)
            # Expand to (N+1, *rest) with wrap
            out_shape = (N + 1,) + d_L.shape[1:]
            out = xp.empty(out_shape, dtype=node_grad_unique.dtype)
            out[:N] = node_grad_unique
            out[N] = node_grad_unique[0]  # periodic image
            return xp.moveaxis(out, 0, axis)

        # Wall BC: interior nodes i=1..N-1 use full R_4; i=0 and i=N are one-sided.
        # d_face[0] = d_{f_{1/2}}, d_face[N-1] = d_{f_{N-1/2}}
        # For node i (1 <= i <= N-1): d_L = d_face[i-1], d_R = d_face[i]
        d_L = d_face[:-1]                               # (N-1, *rest) for i=1..N-1
        d_R = d_face[1:]                                # (N-1, *rest)
        q_m1 = q_moved[:-2]                             # q[i-1], i=1..N-1 → 0..N-2
        q_p1 = q_moved[2:]                              # q[i+1], i=1..N-1 → 2..N
        if w["uniform"]:
            H_over_16 = w["H_over_16"]
        else:
            H_over_16 = self._broadcast_axis0(w["H_over_16_node"][1:-1], d_L.ndim)
        interior = _hermite_kernel(d_L, d_R, q_m1, q_p1, H_over_16)

        out_shape = (N + 1,) + d_face.shape[1:]
        out = xp.empty(out_shape, dtype=interior.dtype)
        out[1:N] = interior
        # One-sided boundary (node 0 uses face f_{1/2} only; node N uses face f_{N-1/2} only)
        # These are O(H²) — acceptable for boundary nodes; Option III/IV apply
        # externally for fields with additional physical wall constraints.
        out[0] = d_face[0]
        out[N] = d_face[N - 1]
        return xp.moveaxis(out, 0, axis)

    def face_divergence(self, F_face, axis: int):
        """Nodal divergence of a face-flux array along ``axis``.

        Parameters
        ----------
        F_face : array with axis dim = ``grid.N[axis]`` (face-located)
        axis : int

        Returns
        -------
        div : array with axis dim = ``grid.N[axis] + 1`` (node-located)

        Formula (uniform, interior):
            div[i] = (F[i] - F[i-1]) / H
        where F[i] = F_{f_{i+1/2}}, F[i-1] = F_{f_{i-1/2}}.

        Wall BC: boundary nodes (i=0, N) are set to zero — Option III
        compatibility for Neumann fields. Override externally if needed.

        Periodic BC: all nodes use cyclic differences.
        """
        xp = self.xp
        F = xp.moveaxis(xp.asarray(F_face), axis, 0)   # (N, *rest)
        N = self.grid.N[axis]
        w = self._weights[axis]

        if self.bc_type == "periodic":
            # div[i] = (F[i] - F[i-1]) / H_i, with i=0..N-1 cyclic; repeat at N.
            F_m1 = xp.roll(F, 1, axis=0)
            if w["uniform"]:
                div_unique = (F - F_m1) * w["inv_H"]
            else:
                inv_H = self._broadcast_axis0(w["inv_H"], F.ndim)
                div_unique = (F - F_m1) * inv_H
            out_shape = (N + 1,) + F.shape[1:]
            out = xp.empty(out_shape, dtype=div_unique.dtype)
            out[:N] = div_unique
            out[N] = div_unique[0]
            return xp.moveaxis(out, 0, axis)

        # Wall BC: interior i=1..N-1 uses (F[i] - F[i-1])/H_i
        # H_i for node i = mean of adjacent face widths; but with cell-centred faces
        # H at node i is approximately (H_faces[i-1] + H_faces[i])/2.
        # For uniform grid H is the same everywhere.
        if w["uniform"]:
            # Interior: (F[i] - F[i-1]) / H
            interior = (F[1:] - F[:-1]) * w["inv_H"]    # (N-1, *rest)
        else:
            # Per-node 1/H at interior: use face-to-node mean.
            import numpy as np
            H_host = self.grid.coords[axis][1:] - self.grid.coords[axis][:-1]
            H_node_host = 0.5 * (H_host[:-1] + H_host[1:])    # (N-1,) at i=1..N-1
            inv_H_node = self._broadcast_axis0(
                xp.asarray(1.0 / H_node_host), F.ndim
            )
            interior = (F[1:] - F[:-1]) * inv_H_node

        out_shape = (N + 1,) + F.shape[1:]
        out = xp.zeros(out_shape, dtype=interior.dtype)
        out[1:N] = interior
        # Boundary nodes default to zero (Option III compatible).
        return xp.moveaxis(out, 0, axis)

    # ── Composed advection operator ──────────────────────────────────────

    def advection_rhs(
        self,
        velocity_components: List,
        scalar=None,
        mode: str = "flux",
    ) -> List:
        """Composed (u·∇)u RHS for momentum, or -u·∇ψ for scalar.

        Returns a list-of-arrays (one per component) with shape
        ``grid.shape`` — drop-in compatible with
        ``ConvectionTerm.compute(velocity_components, ccd)`` and
        ``DissipativeCCDAdvection._rhs(psi, vel)`` downstream.

        Parameters
        ----------
        velocity_components : list of ``ndim`` nodal velocity arrays
        scalar : array or None
            If None: returns ``[-(u·∇)u_j]`` for each component j (momentum).
            If provided: returns scalar ``[-u·∇ψ]`` (level-set); output is
            a length-1 list to keep the interface uniform.
        mode : 'node' | 'flux'
            'node' → Option C: R_4 Hermite reconstructor on (∂_xk u)
                     and multiply at node by u^(k).  O(H⁴) where R_4 applies.
            'flux' → Option B: skew-symmetric face flux form.
                     F_f = 0.5 [u_f^(k)·(∂u)_f + (u^(k)·u)_f]
                     then nodal face divergence. O(H⁴) uniform.
        """
        if mode not in ("node", "flux"):
            raise ValueError(f"mode must be 'node' or 'flux', got {mode!r}")
        xp = self.xp
        ndim = len(velocity_components)

        # Pre-compute q for each velocity component and reuse across axes.
        # Saves ndim² CCD calls to ndim*ndim = ndim² (no reduction in count,
        # but caches d2 per (component, axis) for both face_gradient + node).
        q_cache = {}

        def get_q(field, ax):
            key = (id(field), ax)
            if key not in q_cache:
                _, q_cache[key] = self._ccd.differentiate(field, ax)
            return q_cache[key]

        if scalar is None:
            # Momentum: -(u·∇)u_j for each j
            result = []
            for j in range(ndim):
                u_j = velocity_components[j]
                acc = xp.zeros_like(u_j)
                for k in range(ndim):
                    u_k = velocity_components[k]
                    if mode == "node":
                        q_j = get_q(u_j, k)
                        du_j_dk = self.node_gradient(u_j, k, q=q_j)
                        acc -= u_k * du_j_dk
                    else:  # flux
                        acc += self._flux_contribution(u_k, u_j, k)
                result.append(acc)
            return result

        # Scalar: -u·∇ψ as a single-element list
        psi = scalar
        acc = xp.zeros_like(psi)
        for k in range(ndim):
            u_k = velocity_components[k]
            if mode == "node":
                q_psi = get_q(psi, k)
                dpsi_dk = self.node_gradient(psi, k, q=q_psi)
                acc -= u_k * dpsi_dk
            else:
                acc += self._flux_contribution(u_k, psi, k)
        return [acc]

    def _flux_contribution(self, u_k, phi, axis: int):
        """Skew-symmetric face flux contribution for one axis (SP-D §7).

        Returns nodal (−∂/∂x_k (u_k · φ))_i via:

            F_face = 0.5 [u_k^face · (∂_k φ)_face + (u_k · φ)_face_direct]
            out = -face_divergence(F_face, axis=k)

        The split is algebraically redundant for the continuous equation
        but discretely suppresses aliasing. Both halves use FCCD face
        primitives (face_value + face_gradient).
        """
        xp = self.xp
        _, q_u = self._ccd.differentiate(u_k, axis)
        _, q_phi = self._ccd.differentiate(phi, axis)
        _, q_prod = self._ccd.differentiate(u_k * phi, axis)

        u_k_face = self.face_value(u_k, axis, q=q_u)
        dphi_dk_face = self.face_gradient(phi, axis, q=q_phi)
        prod_face = self.face_value(u_k * phi, axis, q=q_prod)

        F_face_nc = u_k_face * dphi_dk_face        # non-conservative u_k * ∂_k φ
        F_face_cons_term = prod_face                # conservative u_k * φ (face-interpolated)

        # For skew-symmetric: split the divergence form:
        #   -∂/∂x_k(u_k φ) ≡ -u_k ∂_k φ - φ ∂_k u_k   (continuity-neutral)
        # Discretely both forms have subtly different aliasing. The
        # skew-symmetric choice averages the purely non-conservative
        # (u_k · ∂φ)_f and the conservative face flux (u_k·φ)_f:
        F_face = 0.5 * (F_face_nc + F_face_cons_term)

        # For pure flux divergence (conservative only), we'd use prod_face directly;
        # for pure non-conservative, u_k_face · dphi_dk_face.
        # The 0.5 average is the standard skew-symmetric choice (Kok 2000;
        # Ham et al. 2002) that minimises aliasing for energy conservation.

        return -self.face_divergence(F_face, axis)

    # ── Wall BC helpers ─────────────────────────────────────────────────

    def enforce_wall_option_iii(self, face_array, axis: int):
        """Zero boundary face values for Neumann fields (ψ, p).

        Acts in-place on a face-shaped array. For periodic BC this is a
        no-op (no wall faces). For wall BC, with the face array having
        shape ``grid.N[axis]`` along ``axis``, **no boundary face is
        included** — interior faces only. This function is a no-op at
        the array level; it is exposed for semantic clarity at callers.

        Option III is a face-level zeroing; the augmented matrix rows
        (SP-C §6) add wall face entries at positions f_{-1/2} and
        f_{N+1/2} that are not in our interior-only face array.
        """
        return face_array  # no-op for the interior-only face layout

    def enforce_wall_option_iv(self, face_array, axis: int, wall_value: float = 0.0):
        """Mirror-flip boundary faces for Dirichlet fields (u no-slip).

        For no-slip u = wall_value at the wall, the face at i=0 uses
        the ghost mirror u_{-1} = -u_1 (per SP-D §T4), giving

            d_{f_{-1/2}} = (u_0 + u_1)/H - (H/24)(q_0 + q_1)

        at the first interior face (left wall). Mirror formula on the
        right. **This function currently returns ``face_array`` unchanged**;
        the face layout is interior-only, and Dirichlet u = 0 yields a
        face velocity ``u_f = 0`` (Option IV face interpolation), so for
        the typical no-slip case no explicit modification is needed.

        When ``wall_value != 0`` or the mirror stencil must be applied
        explicitly, this is the hook point — deferred until a concrete
        moving-wall case arises.
        """
        return face_array

    # ── Diagnostics ─────────────────────────────────────────────────────

    def periodic_symbol(self, omega: float, axis: int = 0) -> complex:
        """Analytic DFT symbol of the face operator for validation tests.

        Returns hat(M_face)(ω) = i·ω·[1 - 7(ωH)⁴/5760 + O((ωH)⁶)]
        truncated at the explicit 4th-order term (SP-C §7.4 / WIKI-T-054).
        """
        if not self._weights[axis]["uniform"]:
            raise ValueError("periodic_symbol only defined for uniform grid")
        H = self._weights[axis]["H"]
        return 1j * omega * (1.0 - 7.0 * (omega * H) ** 4 / 5760.0)
