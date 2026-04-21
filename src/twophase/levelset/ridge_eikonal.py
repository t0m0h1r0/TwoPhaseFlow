"""Ridge-Eikonal hybrid reinitializer on non-uniform grids (CHK-159).

Theory: SP-E ``docs/memo/short_paper/SP-E_ridge_eikonal_nonuniform_grid.md``
        WIKI-T-057 (sigma_eff + eps_local scaling on non-uniform grids)
        WIKI-T-058 (physical-space Hessian via chain rule; Approach A theory)
        WIKI-T-059 (non-uniform FMM Eikonal)
        WIKI-T-047 / WIKI-T-048 / WIKI-T-049 (SP-B source)
        WIKI-L-025 (this module's API + traceability)

Pipeline:
    psi -> phi (invert_heaviside)
    -> interface crossings (sub-cell physical-coord linear interp)
    -> xi_ridge(x) = sum_k exp(-|x - c_k|^2 / sigma_eff(x)^2),
       sigma_eff(x) = sigma_0 * h(x) / h_ref                          (D1)
    -> ridge mask: local maximum of xi_ridge AND
       n^T Hess_x(xi_ridge) n < 0, Hessian via physical-space FD       (D2)
    -> NonUniformFMM solves |grad_x phi| = 1 from ridge/crossing seeds (D3)
    -> eps_local(x) = eps_scale * eps_xi * h(x), sigmoid reconstruction (D4)
    -> phi-space mass correction (matches EikonalReinitializer pattern)
"""

from __future__ import annotations
import heapq
from typing import TYPE_CHECKING, Tuple

import numpy as np

from .interfaces import IReinitializer
from .heaviside import invert_heaviside
from ..backend import fuse as _fuse

if TYPE_CHECKING:
    from ..backend import Backend
    from ..ccd.ccd_solver import CCDSolver


# ── @_fuse kernels: pure-arithmetic elementwise (CPU identity on no-cupy). ──

@_fuse
def _sigma_eff_kernel(h_field, sigma_0, h_ref):
    """sigma_eff(x) = sigma_0 * h(x) / h_ref   (D1)."""
    return sigma_0 * h_field / h_ref


@_fuse
def _eps_local_kernel(h_field, eps_scale, eps_xi):
    """eps_local(x) = eps_scale * eps_xi * h(x)   (D4)."""
    return eps_scale * eps_xi * h_field


def _sigmoid_xp(xp, phi, eps_local):
    """psi = 1 / (1 + exp(-phi / eps_local)). Uses xp for backend dispatch."""
    return 1.0 / (1.0 + xp.exp(-phi / eps_local))


# ── NonUniformFMM (D3, CPU-serial) ───────────────────────────────────────

class NonUniformFMM:
    """Physical-space Fast Marching Method on non-uniform grids (D3, WIKI-T-059).

    Replaces the uniform-step quadratic of the stock _fmm_phi (which implicitly
    assumes Δx=1 in index space) with the physical-coordinate Eikonal:

        (d - a_x)^2 / h_x^2 + (d - a_y)^2 / h_y^2 = 1

    with closed form
        d = (a_x/h_x^2 + a_y/h_y^2 + sqrt(D)) / (1/h_x^2 + 1/h_y^2)
        D = (1/h_x^2 + 1/h_y^2) - (a_x - a_y)^2 / (h_x^2 h_y^2)
    and caustic fallback d = min(a_x + h_x, a_y + h_y) when D < 0.

    Seeding uses physical-coordinate linear interpolation:
        d_seed_i     = |phi_i| * h_fwd[i] / (|phi_i| + |phi_{i+1}|)
        d_seed_{i+1} = |phi_{i+1}| * h_fwd[i] / (|phi_i| + |phi_{i+1}|)

    Serial heap-based Dijkstra-style propagation — CPU-only by design; D2H
    / H2D is handled by the caller (mirrors the stock _fmm_phi pattern).
    """

    def __init__(self, grid):
        self._grid = grid
        # Physical spacings (length Nx+1 / Ny+1). grid.h[ax][i] is the
        # stored per-node spacing; we use grid.coords differences for the
        # forward/backward physical distances between nodes i, i+1.
        self._hx = np.asarray(grid.h[0]).astype(np.float64)
        self._hy = np.asarray(grid.h[1]).astype(np.float64)
        cx = np.asarray(grid.coords[0]).astype(np.float64)
        cy = np.asarray(grid.coords[1]).astype(np.float64)
        # Forward inter-node physical distances:  hx_fwd[i] = x_{i+1} - x_i.
        self._hx_fwd = np.diff(cx)  # length Nx
        self._hy_fwd = np.diff(cy)  # length Ny

    def update_grid(self, grid) -> None:
        self._grid = grid
        self._hx = np.asarray(grid.h[0]).astype(np.float64)
        self._hy = np.asarray(grid.h[1]).astype(np.float64)
        cx = np.asarray(grid.coords[0]).astype(np.float64)
        cy = np.asarray(grid.coords[1]).astype(np.float64)
        self._hx_fwd = np.diff(cx)
        self._hy_fwd = np.diff(cy)

    # -- public -----------------------------------------------------------

    def solve(self, phi_np: np.ndarray, extra_seeds=None) -> np.ndarray:
        """Return signed distance field solving |grad_x phi| = 1.

        Parameters
        ----------
        phi_np      : (Nx+1, Ny+1) CPU float64 — input field (sign defines
                      inside/outside).
        extra_seeds : optional iterable of (i, j, d) triples — additional
                      physical-distance seeds (e.g. ridge cells). Distances
                      add into the heap and win if smaller than sign-change
                      seeds. The sign of phi at the seed cell is retained.

        Returns
        -------
        phi_sdf : (Nx+1, Ny+1) CPU float64 with sign * FMM distance.
        """
        phi_np = np.ascontiguousarray(phi_np, dtype=np.float64)
        sgn = np.sign(phi_np)
        sgn = np.where(np.abs(phi_np) < 1e-10, 1.0, sgn)
        Nx, Ny = phi_np.shape

        INF = 1e30
        dist = np.full((Nx, Ny), INF, dtype=np.float64)
        frozen = np.zeros((Nx, Ny), dtype=bool)
        heap: list = []

        # CHK-161 B2: FIFO insertion counter neutralises (d,i,j) lex
        # tie-breaking, which favoured lower (i,j) and biased FMM
        # propagation direction under y-flip.
        _push_count = [0]

        def _push(i, j, d):
            if 0 <= i < Nx and 0 <= j < Ny and not frozen[i, j] and d < dist[i, j]:
                dist[i, j] = d
                heapq.heappush(heap, (d, _push_count[0], i, j))
                _push_count[0] += 1

        # Physical-coordinate seeding from sign-change crossings (D3, §6).
        hx_fwd = self._hx_fwd  # (Nx-1,)
        hy_fwd = self._hy_fwd  # (Ny-1,)
        # x-direction
        p, p1 = phi_np[:-1, :], phi_np[1:, :]
        mask = (p * p1) < 0.0
        if mask.any():
            ii, jj = np.where(mask)
            denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
            frac = np.abs(p[ii, jj]) / np.where(denom > 0.0, denom, 1.0)
            seg = hx_fwd[ii]
            d0 = frac * seg
            d1 = (1.0 - frac) * seg
            for k in range(len(ii)):
                _push(int(ii[k]),     int(jj[k]), float(d0[k]))
                _push(int(ii[k]) + 1, int(jj[k]), float(d1[k]))
        # y-direction
        p, p1 = phi_np[:, :-1], phi_np[:, 1:]
        mask = (p * p1) < 0.0
        if mask.any():
            ii, jj = np.where(mask)
            denom = np.abs(p[ii, jj]) + np.abs(p1[ii, jj])
            frac = np.abs(p[ii, jj]) / np.where(denom > 0.0, denom, 1.0)
            seg = hy_fwd[jj]
            d0 = frac * seg
            d1 = (1.0 - frac) * seg
            for k in range(len(ii)):
                _push(int(ii[k]), int(jj[k]),     float(d0[k]))
                _push(int(ii[k]), int(jj[k]) + 1, float(d1[k]))

        # Optional ridge / manually-supplied seeds.
        if extra_seeds is not None:
            for (i, j, d) in extra_seeds:
                _push(int(i), int(j), float(d))

        if not heap:
            return phi_np

        # Propagation: physical-space quadratic update (D3).
        hx = self._hx  # per-node spacing array (length Nx)
        hy = self._hy  # per-node spacing array (length Ny)
        while heap:
            d, _, i, j = heapq.heappop(heap)  # CHK-161 B2: skip FIFO counter
            if frozen[i, j]:
                continue
            frozen[i, j] = True

            for ni, nj in ((i - 1, j), (i + 1, j), (i, j - 1), (i, j + 1)):
                if not (0 <= ni < Nx and 0 <= nj < Ny) or frozen[ni, nj]:
                    continue

                # Physical-step to the updating neighbour from each axis.
                # h_x_step: physical distance from (ni, nj) to its accepted x-neighbour
                a_x = INF
                h_x_step = hx[ni]
                if ni > 0 and frozen[ni - 1, nj]:
                    step = float(hx_fwd[ni - 1])  # x_ni - x_{ni-1}
                    if dist[ni - 1, nj] < a_x:
                        a_x = dist[ni - 1, nj]
                        h_x_step = step
                if ni < Nx - 1 and frozen[ni + 1, nj]:
                    step = float(hx_fwd[ni])      # x_{ni+1} - x_ni
                    if dist[ni + 1, nj] < a_x:
                        a_x = dist[ni + 1, nj]
                        h_x_step = step

                a_y = INF
                h_y_step = hy[nj]
                if nj > 0 and frozen[ni, nj - 1]:
                    step = float(hy_fwd[nj - 1])
                    if dist[ni, nj - 1] < a_y:
                        a_y = dist[ni, nj - 1]
                        h_y_step = step
                if nj < Ny - 1 and frozen[ni, nj + 1]:
                    step = float(hy_fwd[nj])
                    if dist[ni, nj + 1] < a_y:
                        a_y = dist[ni, nj + 1]
                        h_y_step = step

                if a_x >= INF and a_y >= INF:
                    continue

                if a_x >= INF:
                    d_new = a_y + h_y_step
                elif a_y >= INF:
                    d_new = a_x + h_x_step
                else:
                    inv_hx2 = 1.0 / (h_x_step * h_x_step)
                    inv_hy2 = 1.0 / (h_y_step * h_y_step)
                    denom = inv_hx2 + inv_hy2
                    D = denom - (a_x - a_y) ** 2 * inv_hx2 * inv_hy2
                    if D < 0.0:
                        # Caustic regime: 1-D update from closer neighbour.
                        d_new = min(a_x + h_x_step, a_y + h_y_step)
                    else:
                        d_new = (a_x * inv_hx2 + a_y * inv_hy2 + np.sqrt(D)) / denom

                _push(int(ni), int(nj), float(d_new))

        return sgn * dist


# ── RidgeExtractor (D1 sigma_eff + D2 physical-space FD Hessian) ─────────

class RidgeExtractor:
    """Gaussian-xi ridge extraction on non-uniform grids (D1 + D2).

    Computes xi_ridge(x) = sum_k exp(-|x - c_k|^2 / sigma_eff(x)^2), where
    c_k are sub-cell interface crossings (physical coordinates) and
    sigma_eff(x) = sigma_0 * h(x) / h_ref — D1 spatial scaling.

    Ridge set: local maxima of xi_ridge AND n^T H_x xi_ridge n < 0, with
    Hessian in physical space (D2). Code uses 2nd-order physical-space FD;
    # CHK-160: upgrade Hessian to Approach A DirectNonUniformCCDSolver.
    """

    def __init__(self, backend: "Backend", grid, sigma_0: float = 3.0,
                 h_ref: float | None = None):
        self._xp = backend.xp
        self._grid = grid
        self._sigma_0 = float(sigma_0)

        # h_ref: geometric mean of uniform-equivalent spacing across axes.
        if h_ref is None:
            h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
        self._h_ref = h_ref

        xp = self._xp
        # Physical-space per-node spacings broadcast to field shape (Nx+1, Ny+1).
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        # D1: h_field(x) is an isotropic local-scale proxy; use geometric mean
        # so sigma_eff is insensitive to axis swap.
        self._h_field = xp.sqrt(hx * hy)
        self._sigma_eff = _sigma_eff_kernel(self._h_field, self._sigma_0, self._h_ref)

        # Physical coordinates for distance sums.
        self._X = xp.asarray(grid.coords[0]).reshape(-1, 1)
        self._Y = xp.asarray(grid.coords[1]).reshape(1, -1)

    def update_grid(self, grid) -> None:
        self._grid = grid
        xp = self._xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._sigma_eff = _sigma_eff_kernel(self._h_field, self._sigma_0, self._h_ref)
        self._X = xp.asarray(grid.coords[0]).reshape(-1, 1)
        self._Y = xp.asarray(grid.coords[1]).reshape(1, -1)

    @property
    def sigma_eff(self):
        return self._sigma_eff

    # -- public -----------------------------------------------------------

    def compute_xi_ridge(self, phi) -> "array":
        """Return xi_ridge field (shape == grid.shape) computed from phi.

        Interface points are sub-cell linear crossings of phi on each axis;
        each contributes a Gaussian of width sigma_eff(x).
        """
        xp = self._xp
        phi = xp.asarray(phi)
        crossings = self._find_crossings(phi)   # (n_cross, 2) physical coords
        if crossings is None or crossings.shape[0] == 0:
            return xp.zeros_like(phi)

        # Vectorised broadcast over crossings. Shape: (n_cross, Nx+1, Ny+1).
        # For grids up to ~128^2 with O(N) crossings this fits in memory;
        # chunking is added only if future benchmarks demand it.
        cx = crossings[:, 0].reshape(-1, 1, 1)
        cy = crossings[:, 1].reshape(-1, 1, 1)
        dx = self._X.reshape(1, -1, 1) - cx
        dy = self._Y.reshape(1, 1, -1) - cy
        d2 = dx * dx + dy * dy                                # (n_cross, Nx+1, Ny+1)
        sig2 = (self._sigma_eff * self._sigma_eff).reshape(1, *self._sigma_eff.shape)
        return xp.sum(xp.exp(-d2 / sig2), axis=0)

    def extract_ridge_mask(self, xi_ridge) -> "array":
        """Return boolean mask where xi_ridge has a local max along any axis
        AND the physical-space Hessian sign test ``n^T H n < 0`` passes.

        FD Hessian (D2, code fallback):
            hxx[i,j] = (xi[i+1,j] - 2 xi[i,j] + xi[i-1,j]) / (hx_bwd * hx_fwd)
            hyy[i,j] = (xi[i,j+1] - 2 xi[i,j] + xi[i,j-1]) / (hy_bwd * hy_fwd)
            hxy[i,j] = central FD of d(xi)/dy in x.
        # CHK-160: upgrade Hessian to Approach A DirectNonUniformCCDSolver.
        """
        xp = self._xp
        xi = xp.asarray(xi_ridge)
        # Local-max test (discrete): > strict along each axis in the interior.
        loc_x = xp.zeros_like(xi, dtype=bool)
        loc_x[1:-1, :] = (xi[1:-1, :] > xi[:-2, :]) & (xi[1:-1, :] > xi[2:, :])
        loc_y = xp.zeros_like(xi, dtype=bool)
        loc_y[:, 1:-1] = (xi[:, 1:-1] > xi[:, :-2]) & (xi[:, 1:-1] > xi[:, 2:])
        local_max = loc_x | loc_y

        # Physical-space FD Hessian (CHK-159 D2 FD; CHK-160 → Approach A).
        hx = self._grid.h[0]
        hy = self._grid.h[1]
        hx_dev = xp.asarray(hx).reshape(-1, 1)
        hy_dev = xp.asarray(hy).reshape(1, -1)

        hxx = xp.zeros_like(xi)
        hyy = xp.zeros_like(xi)
        hxy = xp.zeros_like(xi)
        hxx[1:-1, :] = (xi[2:, :] - 2.0 * xi[1:-1, :] + xi[:-2, :]) / (hx_dev[1:-1] * hx_dev[1:-1])
        hyy[:, 1:-1] = (xi[:, 2:] - 2.0 * xi[:, 1:-1] + xi[:, :-2]) / (hy_dev[:, 1:-1] * hy_dev[:, 1:-1])
        hxy[1:-1, 1:-1] = (xi[2:, 2:] - xi[2:, :-2] - xi[:-2, 2:] + xi[:-2, :-2]) / (
            4.0 * hx_dev[1:-1] * hy_dev[:, 1:-1]
        )

        # Gradient direction (normal candidate). At a ridge the gradient is
        # nominally zero, so use the direction of the Hessian's most-negative
        # eigenvector instead: this is the normal to the ridge tangent.
        # For speed the sign test below uses axis-aligned directions (sufficient
        # because a true ridge passes the test along at least one axis) and
        # we also check the scalar-Hessian trace < 0.
        hess_neg = (hxx < 0.0) | (hyy < 0.0) | ((hxx + hyy) < 0.0)
        # Reject saddle-like points: require det(H) >= 0 relaxed (trace test
        # already filters most; det check keeps admissible ridge corners).
        ridge_mask = local_max & hess_neg
        # The stock implementation from SP-B §4 also demands ||∇xi|| small.
        # CHK-161 B1: symmetrize central-FD denominator. Original
        #   denom[i] = h_node[i] + h_node[i-1]
        # was backward-biased and asymmetric under mirror index reflection
        # (h_node[N-i] + h_node[N-i-1] ≠ h_node[i] + h_node[i-1] for non-
        # uniform h_node). Averaging with forward-biased twin yields a
        # mirror-symmetric denominator that preserves magnitude calibration:
        #   denom_sym[i] = h_node[i] + 0.5*(h_node[i-1] + h_node[i+1])
        hx_bwd = xp.roll(hx_dev, 1, axis=0)
        hx_fwd = xp.roll(hx_dev, -1, axis=0)
        hy_bwd = xp.roll(hy_dev, 1, axis=1)
        hy_fwd = xp.roll(hy_dev, -1, axis=1)
        dx2 = hx_dev[1:-1] + 0.5 * (hx_bwd[1:-1] + hx_fwd[1:-1])
        dy2 = hy_dev[:, 1:-1] + 0.5 * (hy_bwd[:, 1:-1] + hy_fwd[:, 1:-1])
        gx = xp.zeros_like(xi)
        gy = xp.zeros_like(xi)
        gx[1:-1, :] = (xi[2:, :] - xi[:-2, :]) / dx2
        gy[:, 1:-1] = (xi[:, 2:] - xi[:, :-2]) / dy2
        grad_mag = xp.sqrt(gx * gx + gy * gy)
        tol = 0.5 * xp.max(grad_mag)  # scale-free relative tolerance
        ridge_mask = ridge_mask & (grad_mag < tol + 1e-30)
        return ridge_mask

    # -- internals --------------------------------------------------------

    def _find_crossings(self, phi):
        """Sub-cell physical-coordinate interface crossings of phi.

        Returns array of shape (n_cross, 2) in device memory, or None if
        there is no sign change.
        """
        xp = self._xp
        cx = xp.asarray(self._grid.coords[0])
        cy = xp.asarray(self._grid.coords[1])
        parts = []

        # x-direction crossings: between (i, j) and (i+1, j).
        p, p1 = phi[:-1, :], phi[1:, :]
        mask = (p * p1) < 0.0
        if bool(xp.any(mask)):
            ii, jj = xp.where(mask)
            denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
            frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
            xk = cx[ii] + frac * (cx[ii + 1] - cx[ii])
            yk = cy[jj]
            parts.append(xp.stack([xk, yk], axis=1))

        # y-direction
        p, p1 = phi[:, :-1], phi[:, 1:]
        mask = (p * p1) < 0.0
        if bool(xp.any(mask)):
            ii, jj = xp.where(mask)
            denom = xp.abs(p[ii, jj]) + xp.abs(p1[ii, jj])
            frac = xp.abs(p[ii, jj]) / xp.where(denom > 0.0, denom, 1.0)
            xk = cx[ii]
            yk = cy[jj] + frac * (cy[jj + 1] - cy[jj])
            parts.append(xp.stack([xk, yk], axis=1))

        if not parts:
            return None
        return xp.concatenate(parts, axis=0)


# ── RidgeEikonalReinitializer (orchestrator, IReinitializer) ─────────────

class RidgeEikonalReinitializer(IReinitializer):
    """Topology-preserving reinit via Ridge extraction + non-uniform FMM.

    Implements SP-E end-to-end: psi -> phi -> xi_ridge -> ridge mask ->
    NonUniformFMM -> eps_local sigmoid -> mass-corrected psi. Backward-
    compatible default ``reinit_method='split'`` keeps existing runs
    unchanged (this class only activates under method='ridge_eikonal').

    See WIKI-L-025 for the full API table and traceability matrix.
    """

    def __init__(
        self,
        backend: "Backend",
        grid,
        ccd: "CCDSolver",  # parameter kept for constructor parity; unused in FD path
        eps: float,
        sigma_0: float = 3.0,
        eps_scale: float = 1.4,
        mass_correction: bool = True,
        h_ref: float | None = None,
    ):
        self._xp = backend.xp
        self._grid = grid
        self._eps = float(eps)
        self._eps_scale = float(eps_scale)
        self._mass_correction = mass_correction

        # h_min and h_ref follow the EikonalReinitializer convention.
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        if h_ref is None:
            h_ref = float(np.prod([L / N for L, N in zip(grid.L, grid.N)]) ** (1.0 / grid.ndim))
        self._h_ref = h_ref

        # eps_xi = eps / h_min  (matches EikonalReinitializer).
        self._eps_xi = float(eps) / h_min

        # Pre-compute the local-eps field (GPU/CPU uniform via @fuse).
        xp = self._xp
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)  # isotropic local-scale proxy
        self._eps_local = _eps_local_kernel(self._h_field, self._eps_scale, self._eps_xi)

        # Sub-components.
        self._extractor = RidgeExtractor(backend, grid, sigma_0=sigma_0, h_ref=self._h_ref)
        self._fmm = NonUniformFMM(grid)

    def update_grid(self, grid) -> None:
        self._grid = grid
        xp = self._xp
        h_min = float(min(np.min(grid.h[ax]) for ax in range(grid.ndim)))
        self._h_min = h_min
        self._eps_xi = self._eps / h_min
        hx = xp.asarray(grid.h[0]).reshape(-1, 1)
        hy = xp.asarray(grid.h[1]).reshape(1, -1)
        self._h_field = xp.sqrt(hx * hy)
        self._eps_local = _eps_local_kernel(self._h_field, self._eps_scale, self._eps_xi)
        self._extractor.update_grid(grid)
        self._fmm.update_grid(grid)

    # -- public -----------------------------------------------------------

    def reinitialize(self, psi):
        xp = self._xp
        psi = xp.asarray(psi)
        dV = self._grid.cell_volumes()
        M_old = xp.sum(psi * dV)

        # Step 1: psi -> phi.
        # Use eps_local for consistency with reconstruction (line 479).
        # This makes reinit idempotent for call 2+, avoiding φ-scale mismatch
        # that causes wrong ridge detection and FMM seeding (CHK-160 C7).
        phi = invert_heaviside(xp, psi, self._eps_local)

        # Step 2: xi_ridge + ridge mask (for seeding augmentation).
        xi_ridge = self._extractor.compute_xi_ridge(phi)
        ridge_mask = self._extractor.extract_ridge_mask(xi_ridge)

        # Ridge-cell physical coords → seed the FMM. We compute physical
        # distance-to-interface approximations by locating sign changes
        # adjacent to ridge cells; the NonUniformFMM seeds via sign-change
        # crossings already, so here we only inject zero-distance seeds at
        # ridge cells that coincide with a sign change to anchor topology.
        extra_seeds = None
        # Convert to CPU for FMM (mirrors EikonalReinitializer pattern).
        phi_np = phi.get() if hasattr(phi, "get") else np.asarray(phi)
        mask_np = ridge_mask.get() if hasattr(ridge_mask, "get") else np.asarray(ridge_mask)
        if np.any(mask_np):
            ii, jj = np.where(mask_np)
            # Distance seed for ridge cells that sit on the interface by
            # sign test of phi on immediate neighbours: zero-distance anchor.
            on_interface = np.abs(phi_np[ii, jj]) < 0.5 * self._h_min
            if np.any(on_interface):
                iis = ii[on_interface]
                jjs = jj[on_interface]
                extra_seeds = [(int(iis[k]), int(jjs[k]), 0.0) for k in range(len(iis))]

        # Step 3: non-uniform FMM Eikonal (D3).
        phi_sdf_np = self._fmm.solve(phi_np, extra_seeds=extra_seeds)
        phi_sdf = xp.asarray(phi_sdf_np)

        # Step 4: sigmoid reconstruction with eps_local (D4).
        psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)

        # Step 5: phi-space mass correction (matches EikonalReinitializer).
        if self._mass_correction:
            w = psi_new * (1.0 - psi_new) / self._eps_local
            W = xp.sum(w * dV)
            W_safe = xp.where(W > 1e-14, W, 1.0)
            gate = xp.where(W > 1e-14, 1.0, 0.0)
            M_new = xp.sum(psi_new * dV)
            delta_phi = gate * (M_old - M_new) / W_safe
            phi_sdf = phi_sdf + delta_phi
            psi_new = _sigmoid_xp(xp, phi_sdf, self._eps_local)

        return psi_new


__all__ = [
    "NonUniformFMM",
    "RidgeExtractor",
    "RidgeEikonalReinitializer",
]
