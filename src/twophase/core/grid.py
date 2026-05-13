"""
Computational grid.

Implements Section 5 of the paper (interface-fitted / uniform collocated grid).

For the uniform case (``alpha_grid = 1.0``) the grid spacing is simply
``h[ax] = L[ax] / N[ax]`` and node coordinates are
``x[ax] = linspace(0, L[ax], N[ax]+1)``.

For the interface-fitted case (``alpha_grid > 1.0``) a smooth grid density
function ω(φ) = exp(−α·(φ/ε)²) concentrates nodes near the interface.
The physical coordinate is obtained by integrating a scaled spacing field
and renormalising to the domain length.  A minimum cell-width floor
``dx_min_floor`` prevents near-zero spacings that would make the CCD
system ill-conditioned (Known Issue #3 in the architecture document).

Key equations:
    Uniform:  Δx = L / N                                         (§5 baseline)
    Grid density: ω(φ) = exp(−α·(φ/ε)²)                         (§5 Eq.~grid)
    Metric:   J = ∂ξ/∂x  (used by CCD for non-uniform spacing)  (§4.9)
"""

from __future__ import annotations
import math
import numpy as np
from typing import TYPE_CHECKING, Tuple

from .boundary import periodic_axis_flags
from .metrics import compute_metrics

if TYPE_CHECKING:
    from ..backend import Backend
    from ..config import GridConfig


class Grid:
    """Collocated Cartesian grid (2-D or 3-D).

    Attributes
    ----------
    ndim : int
    N : tuple[int, ...]  — number of cells per axis (nodes = N+1)
    L : tuple[float, ...] — domain lengths
    h : list[numpy.ndarray] — 1-D spacing arrays, shape (N[ax]+1,) each
    coords : list[numpy.ndarray] — node coordinate vectors, shape (N[ax]+1,)
    shape : tuple[int, ...] — (N[0]+1, N[1]+1[, N[2]+1])
    J : list[numpy.ndarray] — metric ∂ξ/∂x per axis (= 1/h for uniform)
    dJ_dxi : list[numpy.ndarray] — gradient of metric in ξ-space
    """

    def __init__(self, grid_config: "GridConfig", backend: "Backend"):
        self._gc = grid_config
        self.backend = backend
        self.xp = backend.xp

        self.ndim = grid_config.ndim
        self.N = tuple(grid_config.N)
        self.L = tuple(grid_config.L)

        # Build uniform grid (interface-fitted update happens separately)
        self.coords: list[np.ndarray] = []
        self.h: list[np.ndarray] = []
        for ax in range(self.ndim):
            c = np.linspace(0.0, grid_config.L[ax], grid_config.N[ax] + 1)
            self.coords.append(c)
            # h[ax] is length-N[ax] spacing (between consecutive nodes)
            # We store per-node spacing (averaged from both sides) for metrics
            dx = np.full(grid_config.N[ax] + 1, grid_config.L[ax] / grid_config.N[ax])
            self.h.append(dx)

        self.shape: tuple = tuple(n + 1 for n in self.N)
        self._cell_volumes = None
        self._cell_volume_axes: tuple[str, ...] | None = None
        self._device_coord_cache: dict[tuple, object] = {}
        self._device_cell_width_cache: dict[tuple, object] = {}
        self._device_metric_cache: dict[tuple, object] = {}
        self._device_metric_gradient_cache: dict[tuple, object] = {}
        self.bc_type = getattr(grid_config, "bc_type", "wall")

        # Metrics (identity for uniform grid)
        self._build_metrics()

    # ── Public interface ──────────────────────────────────────────────────

    def meshgrid(self) -> Tuple:
        """Return open meshgrid arrays in physical coordinates.

        2-D: returns (X, Y) each shape ``(N[0]+1, N[1]+1)``.
        3-D: returns (X, Y, Z) each shape ``(N[0]+1, N[1]+1, N[2]+1)``.

        Output arrays live on the backend device: NumPy on CPU backend,
        CuPy on GPU backend.  ``self.coords`` stays on host for the
        metric-building path; conversion happens only at this boundary.
        """
        xp = self.xp
        return xp.meshgrid(
            *[self.device_coords(axis) for axis in range(self.ndim)],
            indexing="ij",
        )

    def device_coords(self, axis: int, dtype=None):
        """Return a cached backend-native coordinate vector for one axis."""
        coords = self.coords[axis]
        dtype_key = np.dtype(dtype if dtype is not None else coords.dtype).str
        key = (int(axis), dtype_key, id(coords), tuple(coords.shape))
        cached = self._device_coord_cache.get(key)
        if cached is None:
            cached = self.xp.asarray(coords, dtype=np.dtype(dtype_key))
            self._device_coord_cache[key] = cached
        return cached

    def device_cell_widths(self, axis: int, dtype=None):
        """Return cached backend-native cell widths for one axis."""
        coords = self.coords[axis]
        dtype_key = np.dtype(dtype if dtype is not None else coords.dtype).str
        key = (int(axis), dtype_key, id(coords), tuple(coords.shape))
        cached = self._device_cell_width_cache.get(key)
        if cached is None:
            cached = self.xp.asarray(np.diff(coords), dtype=np.dtype(dtype_key))
            self._device_cell_width_cache[key] = cached
        return cached

    def device_metric(self, axis: int, dtype=None):
        """Return cached backend-native CCD metric ``J`` for one axis."""
        metric = self.J[axis]
        dtype_key = np.dtype(dtype if dtype is not None else metric.dtype).str
        key = (int(axis), dtype_key, id(metric), tuple(metric.shape))
        cached = self._device_metric_cache.get(key)
        if cached is None:
            cached = self.xp.asarray(metric, dtype=np.dtype(dtype_key))
            self._device_metric_cache[key] = cached
        return cached

    def device_metric_gradient(self, axis: int, dtype=None):
        """Return cached backend-native CCD metric derivative for one axis."""
        metric_gradient = self.dJ_dxi[axis]
        dtype_key = np.dtype(
            dtype if dtype is not None else metric_gradient.dtype
        ).str
        key = (int(axis), dtype_key, id(metric_gradient), tuple(metric_gradient.shape))
        cached = self._device_metric_gradient_cache.get(key)
        if cached is None:
            cached = self.xp.asarray(metric_gradient, dtype=np.dtype(dtype_key))
            self._device_metric_gradient_cache[key] = cached
        return cached

    def update_from_levelset(
        self,
        psi_data: np.ndarray,
        eps: float,
        ccd=None,
        wall_contacts=None,
    ) -> None:
        """Rebuild interface-fitted grid given the Heaviside field ψ.

        Only active when ``grid_config.alpha_grid > 1.0``.

        Internally converts ψ → φ via logit inversion, then applies the
        paper's composite Gaussian grid monitor (§10):
            I_Γ = exp(−φ²/ε_Γ²), I_W = exp(−d_W²/ε_W²)
            ω_a = 1 + (α_Γ,a−1)I_Γ + (α_W,a−1)I_W
        on axes enabled by interface fitting or wall refinement. Disabled axes are kept
        exactly uniform, giving a separable map
        ``x_a = X_a(ξ_a)`` for active axes and ``x_a = L_a ξ_a`` otherwise.
        Active axes are regenerated by equidistributing the physical monitor
        ``ω_a(x_a)`` over the current coordinates, so dynamic rebuilds follow
        the currently tracked interface rather than a stale array index.

        Parameters
        ----------
        psi_data : array — Heaviside field ψ ∈ [0, 1]
        eps      : interface half-width ε
        ccd      : CCDSolver instance for O(h⁶) metric evaluation (optional)
        """
        from ..levelset.heaviside import invert_heaviside

        alpha = self._gc.alpha_grid
        if alpha <= 1.0:
            return  # uniform grid — nothing to do
        fitting_axes = tuple(bool(enabled) for enabled in self._gc.fitting_axes)
        wall_axes = tuple(bool(enabled) for enabled in self._gc.wall_refinement_axes)
        if not any(fitting_axes) and not any(wall_axes):
            return

        xp = self.backend.xp

        fitting_alpha = tuple(float(value) for value in self._gc.fitting_alpha_grid)
        fitting_eps_factor = tuple(float(value) for value in self._gc.fitting_eps_g_factor)
        fitting_eps_cells = tuple(self._gc.fitting_eps_g_cells)
        fitting_dx_floor = tuple(float(value) for value in self._gc.fitting_dx_min_floor)
        wall_alpha = tuple(float(value) for value in self._gc.wall_alpha_grid)
        wall_eps_factor = tuple(float(value) for value in self._gc.wall_eps_g_factor_axes)
        wall_eps_cells = tuple(self._gc.wall_eps_g_cells)
        wall_sides = tuple(tuple(sides) for sides in self._gc.wall_sides)

        interface_active_any = any(
            fitting_axes[ax] and fitting_alpha[ax] > 1.0
            for ax in range(self.ndim)
        )
        if self.backend.is_gpu():
            self._update_from_levelset_backend(
                psi_data,
                eps,
                ccd=ccd,
                wall_contacts=wall_contacts,
                fitting_axes=fitting_axes,
                wall_axes=wall_axes,
                fitting_alpha=fitting_alpha,
                fitting_eps_factor=fitting_eps_factor,
                fitting_eps_cells=fitting_eps_cells,
                fitting_dx_floor=fitting_dx_floor,
                wall_alpha=wall_alpha,
                wall_eps_factor=wall_eps_factor,
                wall_eps_cells=wall_eps_cells,
                wall_sides=wall_sides,
                interface_active_any=interface_active_any,
            )
            return

        phi = None
        old_coords_all = [
            np.asarray(coords, dtype=float).copy() for coords in self.coords
        ]
        if interface_active_any:
            # ψ → φ (logit inversion) on the active backend. Wall-only rebuilds
            # do not need φ and therefore avoid the extra GPU kernel/D2H path.
            phi = invert_heaviside(xp, xp.asarray(psi_data), eps)

        for ax in range(self.ndim):
            alpha_axis = fitting_alpha[ax]
            interface_active = fitting_axes[ax] and alpha_axis > 1.0
            wall_active = wall_axes[ax] and wall_alpha[ax] > 1.0
            if not interface_active and not wall_active:
                self._reset_axis_to_uniform(ax)
                continue

            omega = np.ones(self._gc.N[ax] + 1, dtype=float)
            coords_old = np.asarray(self.coords[ax], dtype=float)

            if interface_active:
                assert phi is not None
                eps_g_cells = fitting_eps_cells[ax]
                if eps_g_cells is not None:
                    h_uniform = self._gc.L[ax] / self._gc.N[ax]
                    eps_g = eps_g_cells * h_uniform
                else:
                    eps_g = fitting_eps_factor[ax] * eps

                # 1-D marginal: min |φ| over other axes (§10 φ̄^x_i = min_j |φ_{i,j}|)
                axes_other = tuple(a for a in range(self.ndim) if a != ax)
                phi_1d = xp.min(xp.abs(phi), axis=axes_other)

                # Bounded interface indicator ∈ [0, 1].
                indicator_1d_dev = xp.exp(-(phi_1d * phi_1d) / (eps_g * eps_g))
                indicator_1d_dev = xp.maximum(
                    indicator_1d_dev,
                    self._closure_seed_indicator_1d_backend(
                        xp,
                        phi,
                        ax,
                        eps_g,
                    ),
                )
                indicator_1d = np.asarray(self.backend.to_host(indicator_1d_dev))
                if wall_contacts:
                    indicator_1d = np.maximum(
                        indicator_1d,
                        self._wall_contact_indicator_1d(wall_contacts, ax, eps_g),
                    )
                omega = omega + (alpha_axis - 1.0) * indicator_1d

            if wall_active:
                eps_w_cells = wall_eps_cells[ax]
                if eps_w_cells is not None:
                    h_uniform = self._gc.L[ax] / self._gc.N[ax]
                    eps_w = eps_w_cells * h_uniform
                else:
                    eps_w = wall_eps_factor[ax] * eps
                wall_indicator = self._physical_wall_indicator_1d(
                    ax,
                    eps_w,
                    wall_sides[ax],
                )
                omega = omega + (wall_alpha[ax] - 1.0) * wall_indicator

            # Equidistribution on the physical old coordinate:
            #     ∫_0^{x_i} ω_a(s) ds = i/N_a ∫_0^L ω_a(s) ds.
            # This keeps Mode-2 rebuilds attached to the tracked interface
            # position on non-uniform grids, not to the raw node index.
            monitor_cell = 0.5 * (omega[:-1] + omega[1:]) * np.diff(coords_old)
            monitor_cdf = np.zeros(self._gc.N[ax] + 1, dtype=float)
            monitor_cdf[1:] = np.cumsum(monitor_cell)
            target = np.linspace(0.0, monitor_cdf[-1], self._gc.N[ax] + 1)
            coords_ax_h = np.interp(target, monitor_cdf, coords_old)
            coords_ax_h[0] = 0.0
            coords_ax_h[-1] = self._gc.L[ax]

            cell_dx = np.diff(coords_ax_h)
            cell_dx = self._apply_cell_width_floor(
                cell_dx,
                fitting_dx_floor[ax],
                self._gc.L[ax],
            )
            coords_ax_h = np.zeros(self._gc.N[ax] + 1, dtype=float)
            coords_ax_h[1:] = np.cumsum(cell_dx)
            coords_ax_h[-1] = self._gc.L[ax]

            self.coords[ax] = coords_ax_h
            # Per-node spacing (average of left and right cell widths)
            node_dx = np.empty(self._gc.N[ax] + 1)
            node_dx[0] = cell_dx[0]
            node_dx[-1] = cell_dx[-1]
            node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
            self.h[ax] = node_dx

        if interface_active_any:
            assert phi is not None
            phi_host = np.asarray(self.backend.to_host(phi), dtype=float)
            self._enforce_regular_interface_stratum(
                phi_host,
                old_coords_all,
                fitting_axes=fitting_axes,
                fitting_dx_floor=fitting_dx_floor,
            )

        self._build_metrics(ccd=ccd)

    # ── Private helpers ───────────────────────────────────────────────────

    def _update_from_levelset_backend(
        self,
        psi_data,
        eps: float,
        *,
        ccd=None,
        wall_contacts=None,
        fitting_axes: tuple[bool, ...],
        wall_axes: tuple[bool, ...],
        fitting_alpha: tuple[float, ...],
        fitting_eps_factor: tuple[float, ...],
        fitting_eps_cells: tuple[float | None, ...],
        fitting_dx_floor: tuple[float, ...],
        wall_alpha: tuple[float, ...],
        wall_eps_factor: tuple[float, ...],
        wall_eps_cells: tuple[float | None, ...],
        wall_sides: tuple[tuple[str, ...], ...],
        interface_active_any: bool,
    ) -> None:
        """GPU-resident fitted-grid rebuild with host coordinate metadata.

        A3 mapping:
        - Equation: monitor equidistribution in WIKI-T-171.
        - Discretisation: prefix CDF and lower-width projection.
        - Code: device arrays here; only final coordinate metadata is copied
          to host because ``Grid.coords`` is the current metric builder SSoT.
        """
        from ..levelset.heaviside import invert_heaviside

        xp = self.backend.xp
        old_coords_host = [
            np.asarray(coords, dtype=float).copy() for coords in self.coords
        ]
        old_coords_dev = [xp.asarray(coords) for coords in old_coords_host]
        candidate_coords = list(old_coords_dev)
        phi = (
            invert_heaviside(xp, xp.asarray(psi_data), eps)
            if interface_active_any
            else None
        )

        for ax in range(self.ndim):
            alpha_axis = fitting_alpha[ax]
            interface_active = fitting_axes[ax] and alpha_axis > 1.0
            wall_active = wall_axes[ax] and wall_alpha[ax] > 1.0
            if not interface_active and not wall_active:
                candidate_coords[ax] = xp.linspace(
                    0.0,
                    float(self._gc.L[ax]),
                    int(self._gc.N[ax]) + 1,
                    dtype=old_coords_dev[ax].dtype,
                )
                continue

            coords_old = old_coords_dev[ax]
            omega = xp.ones(int(self._gc.N[ax]) + 1, dtype=coords_old.dtype)

            if interface_active:
                assert phi is not None
                eps_g_cells = fitting_eps_cells[ax]
                if eps_g_cells is not None:
                    h_uniform = self._gc.L[ax] / self._gc.N[ax]
                    eps_g = eps_g_cells * h_uniform
                else:
                    eps_g = fitting_eps_factor[ax] * eps

                axes_other = tuple(a for a in range(self.ndim) if a != ax)
                phi_1d = xp.min(xp.abs(phi), axis=axes_other)
                indicator_1d = xp.exp(-(phi_1d * phi_1d) / (eps_g * eps_g))
                indicator_1d = xp.maximum(
                    indicator_1d,
                    self._closure_seed_indicator_1d_backend(
                        xp,
                        phi,
                        ax,
                        eps_g,
                        coords=old_coords_dev,
                    ),
                )
                if wall_contacts:
                    indicator_1d = xp.maximum(
                        indicator_1d,
                        self._wall_contact_indicator_1d_backend(
                            wall_contacts,
                            ax,
                            eps_g,
                            coords_old,
                        ),
                    )
                omega = omega + (alpha_axis - 1.0) * indicator_1d

            if wall_active:
                eps_w_cells = wall_eps_cells[ax]
                if eps_w_cells is not None:
                    h_uniform = self._gc.L[ax] / self._gc.N[ax]
                    eps_w = eps_w_cells * h_uniform
                else:
                    eps_w = wall_eps_factor[ax] * eps
                omega = omega + (wall_alpha[ax] - 1.0) * (
                    self._physical_wall_indicator_1d_backend(
                        xp,
                        coords_old,
                        float(self._gc.L[ax]),
                        eps_w,
                        wall_sides[ax],
                    )
                )

            candidate_coords[ax] = self._equidistribute_coords_backend(
                xp,
                omega,
                coords_old,
                floor=fitting_dx_floor[ax],
                length=float(self._gc.L[ax]),
            )

        if interface_active_any and phi is not None:
            candidate_coords = self._enforce_regular_interface_stratum_backend(
                xp,
                phi,
                old_coords_dev,
                candidate_coords,
                fitting_axes=fitting_axes,
                fitting_dx_floor=fitting_dx_floor,
            )

        for ax, coords_dev in enumerate(candidate_coords):
            self.coords[ax] = np.asarray(self.backend.to_host(coords_dev), dtype=float)
            self._refresh_node_spacing(ax)
        self._build_metrics(ccd=ccd)

    def _reset_axis_to_uniform(self, axis: int) -> None:
        """Keep an inactive fitting axis on the exact uniform coordinate map."""
        coords_axis = np.linspace(0.0, self._gc.L[axis], self._gc.N[axis] + 1)
        self.coords[axis] = coords_axis
        self.h[axis] = np.full(
            self._gc.N[axis] + 1,
            self._gc.L[axis] / self._gc.N[axis],
        )

    @staticmethod
    def _apply_cell_width_floor(
        cell_widths: np.ndarray,
        floor: float,
        length: float,
    ) -> np.ndarray:
        """Enforce a positive physical cell-width floor while preserving length."""
        if floor <= 0.0 or np.min(cell_widths) >= floor:
            return cell_widths
        n_cells = cell_widths.size
        if floor * n_cells >= length:
            return np.full(n_cells, length / n_cells)
        surplus = np.maximum(cell_widths - floor, 0.0)
        total_surplus = surplus.sum()
        if total_surplus <= 0.0:
            return np.full(n_cells, length / n_cells)
        scale = (length - floor * n_cells) / total_surplus
        return floor + surplus * scale

    def _closure_seed_indicator_1d(
        self,
        phi: np.ndarray,
        axis: int,
        eps_g: float,
    ) -> np.ndarray:
        """Build a Gaussian monitor from closed-domain interface crossings."""
        coords_axis = np.asarray(self.coords[axis], dtype=float)
        indicator = np.zeros_like(coords_axis)
        if self.ndim != 2:
            return indicator

        coords_x = np.asarray(self.coords[0], dtype=float)
        coords_y = np.asarray(self.coords[1], dtype=float)
        projections = []
        tol = max(1.0e-12, 1.0e-10 * eps_g)

        phi_left = phi[:-1, :]
        phi_right = phi[1:, :]
        crossing_mask = (phi_left * phi_right) < 0.0
        if np.any(crossing_mask):
            crossing_i, crossing_j = np.where(crossing_mask)
            denom = np.abs(phi_left[crossing_i, crossing_j]) + np.abs(phi_right[crossing_i, crossing_j])
            frac = np.abs(phi_left[crossing_i, crossing_j]) / np.where(denom > 0.0, denom, 1.0)
            crossing_x = coords_x[crossing_i] + frac * (coords_x[crossing_i + 1] - coords_x[crossing_i])
            crossing_y = coords_y[crossing_j]
            projections.append(crossing_x if axis == 0 else crossing_y)

        phi_down = phi[:, :-1]
        phi_up = phi[:, 1:]
        crossing_mask = (phi_down * phi_up) < 0.0
        if np.any(crossing_mask):
            crossing_i, crossing_j = np.where(crossing_mask)
            denom = np.abs(phi_down[crossing_i, crossing_j]) + np.abs(phi_up[crossing_i, crossing_j])
            frac = np.abs(phi_down[crossing_i, crossing_j]) / np.where(denom > 0.0, denom, 1.0)
            crossing_x = coords_x[crossing_i]
            crossing_y = coords_y[crossing_j] + frac * (coords_y[crossing_j + 1] - coords_y[crossing_j])
            projections.append(crossing_x if axis == 0 else crossing_y)

        zero_i, zero_j = np.where(np.abs(phi) <= tol)
        if len(zero_i) > 0:
            projections.append(coords_x[zero_i] if axis == 0 else coords_y[zero_j])

        if not projections:
            return indicator
        projected = np.concatenate(projections)
        if projected.size == 0:
            return indicator
        distance = coords_axis.reshape(-1, 1) - projected.reshape(1, -1)
        return np.max(np.exp(-(distance * distance) / (eps_g * eps_g)), axis=1)

    def _closure_seed_indicator_1d_backend(
        self,
        xp,
        phi,
        axis: int,
        eps_g: float,
        *,
        coords=None,
    ):
        """Backend-native closed-interface projection monitor.

        This keeps monitor construction from transferring the full
        two-dimensional ``φ`` field to host; the regular-stratum guard later
        materializes ``φ`` on host only after candidate coordinates exist.
        """
        phi_dtype = xp.asarray(phi).dtype
        if self.ndim != 2:
            coords_axis = (
                self.device_coords(axis, dtype=phi_dtype)
                if coords is None
                else xp.asarray(coords[axis], dtype=phi_dtype)
            )
            indicator = xp.zeros_like(coords_axis)
            return indicator

        if coords is None:
            coords_x = self.device_coords(0, dtype=phi_dtype)
            coords_y = self.device_coords(1, dtype=phi_dtype)
            coords_axis = coords_x if axis == 0 else coords_y
        else:
            coords_x = xp.asarray(coords[0], dtype=phi_dtype)
            coords_y = xp.asarray(coords[1], dtype=phi_dtype)
            coords_axis = coords_x if axis == 0 else coords_y
        indicator = xp.zeros_like(coords_axis)
        eps_sq = xp.asarray(eps_g * eps_g, dtype=phi_dtype)
        zero = xp.asarray(0.0, dtype=phi_dtype)
        one = xp.asarray(1.0, dtype=phi_dtype)

        def projected_indicator(projected, mask):
            distance = coords_axis.reshape((-1,) + (1,) * projected.ndim) - projected
            contribution = xp.where(
                mask.reshape((1,) + mask.shape),
                xp.exp(-(distance * distance) / eps_sq),
                zero,
            )
            return xp.max(contribution, axis=tuple(range(1, contribution.ndim)))

        phi_left = phi[:-1, :]
        phi_right = phi[1:, :]
        crossing_mask = (phi_left * phi_right) < zero
        denom = xp.abs(phi_left) + xp.abs(phi_right)
        frac = xp.abs(phi_left) / xp.where(denom > zero, denom, one)
        crossing_x = coords_x[:-1, None] + frac * (
            coords_x[1:, None] - coords_x[:-1, None]
        )
        crossing_y = xp.broadcast_to(coords_y[None, :], crossing_x.shape)
        indicator = xp.maximum(
            indicator,
            projected_indicator(crossing_x if axis == 0 else crossing_y, crossing_mask),
        )

        phi_down = phi[:, :-1]
        phi_up = phi[:, 1:]
        crossing_mask = (phi_down * phi_up) < zero
        denom = xp.abs(phi_down) + xp.abs(phi_up)
        frac = xp.abs(phi_down) / xp.where(denom > zero, denom, one)
        crossing_x = xp.broadcast_to(coords_x[:, None], phi_down.shape)
        crossing_y = coords_y[None, :-1] + frac * (
            coords_y[None, 1:] - coords_y[None, :-1]
        )
        indicator = xp.maximum(
            indicator,
            projected_indicator(crossing_x if axis == 0 else crossing_y, crossing_mask),
        )

        phi_dtype = xp.asarray(phi).dtype
        dtype_eps = xp.asarray(xp.finfo(phi_dtype).eps, dtype=phi_dtype)
        tol = xp.sqrt(dtype_eps) * (one + xp.asarray(eps_g, dtype=phi_dtype))
        zero_mask = xp.abs(phi) <= tol
        zero_projection = (
            xp.broadcast_to(coords_x[:, None], phi.shape)
            if axis == 0
            else xp.broadcast_to(coords_y[None, :], phi.shape)
        )
        return xp.maximum(indicator, projected_indicator(zero_projection, zero_mask))

    @staticmethod
    def _physical_wall_indicator_1d_backend(
        xp,
        coords_axis,
        length: float,
        eps_w: float,
        sides: tuple[str, ...],
    ):
        """Backend-native wall monitor along one coordinate axis."""
        indicator = xp.zeros_like(coords_axis)
        if eps_w <= 0.0 or not sides:
            return indicator
        eps_sq = eps_w * eps_w
        if "lower" in sides:
            indicator = xp.maximum(indicator, xp.exp(-(coords_axis * coords_axis) / eps_sq))
        if "upper" in sides:
            distance = length - coords_axis
            indicator = xp.maximum(indicator, xp.exp(-(distance * distance) / eps_sq))
        return indicator

    def _wall_contact_indicator_1d_backend(
        self,
        wall_contacts,
        axis: int,
        eps_g: float,
        coords_axis,
    ):
        """Backend-native monitor contribution from pinned wall contacts."""
        xp = self.backend.xp
        indicator = xp.zeros_like(coords_axis)
        if not wall_contacts:
            return indicator
        projected = wall_contacts.projected_coordinates(axis, self)
        if projected.size == 0:
            return indicator
        projected_dev = xp.asarray(projected, dtype=coords_axis.dtype)
        distance = coords_axis.reshape(-1, 1) - projected_dev.reshape(1, -1)
        return xp.max(xp.exp(-(distance * distance) / (eps_g * eps_g)), axis=1)

    @staticmethod
    def _equidistribute_coords_backend(
        xp,
        omega,
        coords_old,
        *,
        floor: float,
        length: float,
    ):
        """Device implementation of monitor CDF inversion plus width floor."""
        monitor_cell = 0.5 * (omega[:-1] + omega[1:]) * (coords_old[1:] - coords_old[:-1])
        zero = xp.zeros((1,), dtype=coords_old.dtype)
        monitor_cdf = xp.concatenate([zero, xp.cumsum(monitor_cell)])
        target = xp.linspace(
            0.0,
            monitor_cdf[-1],
            int(coords_old.size),
            dtype=coords_old.dtype,
        )
        idx, frac = Grid._monotone_interval_indices_backend(xp, monitor_cdf, target)
        coords = coords_old[idx] + frac * (coords_old[idx + 1] - coords_old[idx])
        cell_dx = Grid._apply_cell_width_floor_backend(
            xp,
            coords[1:] - coords[:-1],
            floor=floor,
            length=length,
        )
        rebuilt = xp.concatenate([zero, xp.cumsum(cell_dx)])
        rebuilt = rebuilt.copy()
        rebuilt[0] = 0.0
        rebuilt[-1] = length
        return rebuilt

    @staticmethod
    def _apply_cell_width_floor_backend(xp, cell_widths, *, floor: float, length: float):
        """Project cell widths to ``sum d_i=L`` and ``d_i>=floor`` on device."""
        if floor <= 0.0:
            return cell_widths
        n_cells = int(cell_widths.size)
        if floor * n_cells >= length:
            return xp.full_like(cell_widths, length / n_cells)
        surplus = xp.maximum(cell_widths - floor, 0.0)
        total_surplus = xp.sum(surplus)
        scale = (length - floor * n_cells) / xp.where(
            total_surplus > 0.0,
            total_surplus,
            xp.asarray(1.0, dtype=cell_widths.dtype),
        )
        return floor + surplus * scale

    @staticmethod
    def _monotone_interval_indices_backend(xp, coords, target):
        """Find monotone interpolation intervals without host-side search."""
        leq_count = xp.sum(coords[:, None] <= target[None, :], axis=0)
        idx = xp.asarray(leq_count - 1, dtype=xp.int64)
        idx = xp.clip(idx, 0, int(coords.size) - 2)
        left = coords[idx]
        right = coords[idx + 1]
        denom = xp.where(right > left, right - left, xp.asarray(1.0, dtype=coords.dtype))
        frac = xp.clip((target - left) / denom, 0.0, 1.0)
        return idx, frac

    def _physical_wall_indicator_1d(
        self,
        axis: int,
        eps_w: float,
        sides: tuple[str, ...],
    ) -> np.ndarray:
        """Build the non-periodic wall-distance monitor along one axis."""
        coords_axis = np.asarray(self.coords[axis], dtype=float)
        indicator = np.zeros_like(coords_axis)
        if eps_w <= 0.0 or not sides:
            return indicator
        length = float(self._gc.L[axis])
        if "lower" in sides:
            indicator = np.maximum(
                indicator,
                np.exp(-(coords_axis * coords_axis) / (eps_w * eps_w)),
            )
        if "upper" in sides:
            distance = length - coords_axis
            indicator = np.maximum(
                indicator,
                np.exp(-(distance * distance) / (eps_w * eps_w)),
            )
        return indicator

    def _wall_contact_indicator_1d(
        self,
        wall_contacts,
        axis: int,
        eps_g: float,
    ) -> np.ndarray:
        """Build monitor contribution from pinned no-slip contacts."""
        coords_axis = np.asarray(self.coords[axis], dtype=float)
        indicator = np.zeros_like(coords_axis)
        if not wall_contacts:
            return indicator
        projected = wall_contacts.projected_coordinates(axis, self)
        if projected.size == 0:
            return indicator
        distance = coords_axis.reshape(-1, 1) - projected.reshape(1, -1)
        return np.max(np.exp(-(distance * distance) / (eps_g * eps_g)), axis=1)

    def _enforce_regular_interface_stratum(
        self,
        phi_source: np.ndarray,
        source_coords: list[np.ndarray],
        *,
        fitting_axes: tuple[bool, ...],
        fitting_dx_floor: tuple[float, ...],
    ) -> None:
        """Keep rebuilt nodes inside a regular P1 cut-geometry stratum.

        The P1 cut-cell maps ``Q_h(phi)`` and ``S_h(phi)`` are smooth only while
        the zero level set does not pass through a grid node.  Interface
        monitors deliberately cluster nodes near ``phi=0``; this guard applies
        the smallest coordinate-line correction needed to keep the rebuilt
        tensor grid in that open sign stratum.
        """
        if self.ndim != 2 or not any(fitting_axes):
            return
        value_floor = self._regular_stratum_value_floor()
        if value_floor <= 0.0:
            return

        active_axes = tuple(
            axis
            for axis, enabled in enumerate(fitting_axes)
            if enabled and self.N[axis] > 1
        )
        if not active_axes:
            return

        for _sweep in range(4):
            phi_new = self._interpolate_levelset_to_current_grid(
                phi_source,
                source_coords,
            )
            abs_phi = np.abs(phi_new)
            sign_margin = float(np.min(abs_phi))
            if sign_margin >= value_floor:
                return
            near_nodes = np.argwhere(abs_phi < value_floor)
            if near_nodes.size == 0:
                return
            changed = False
            for node in near_nodes[np.argsort(abs_phi[tuple(near_nodes.T)])]:
                changed = self._move_node_coordinate_line_off_interface(
                    phi_new,
                    tuple(int(index) for index in node),
                    active_axes=active_axes,
                    value_floor=value_floor,
                    fitting_dx_floor=fitting_dx_floor,
                ) or changed
            if not changed:
                return
        self._refresh_node_spacings()

    def _enforce_regular_interface_stratum_backend(
        self,
        xp,
        phi_source,
        source_coords,
        candidate_coords,
        *,
        fitting_axes: tuple[bool, ...],
        fitting_dx_floor: tuple[float, ...],
    ):
        """Fixed-sweep device guard for the regular P1 interface stratum."""
        if self.ndim != 2 or not any(fitting_axes):
            return candidate_coords
        value_floor = self._regular_stratum_value_floor()
        if value_floor <= 0.0:
            return candidate_coords
        active_axes = tuple(
            axis
            for axis, enabled in enumerate(fitting_axes)
            if enabled and self.N[axis] > 1
        )
        if not active_axes:
            return candidate_coords

        coords = list(candidate_coords)
        value_floor_dev = xp.asarray(value_floor, dtype=xp.asarray(phi_source).dtype)
        for _sweep in range(4):
            phi_new = self._interpolate_levelset_to_grid_backend(
                xp,
                phi_source,
                source_coords,
                coords,
            )
            violation = xp.abs(phi_new) < value_floor_dev
            for axis in active_axes:
                gradient = self._nodal_levelset_gradient_backend(
                    xp,
                    phi_new,
                    coords[axis],
                    axis,
                )
                coords[axis] = self._apply_regular_stratum_line_shift_backend(
                    xp,
                    coords[axis],
                    phi_new,
                    gradient,
                    violation,
                    axis,
                    value_floor_dev,
                    floor=max(
                        float(fitting_dx_floor[axis]),
                        1.0e-12 * float(self.L[axis]),
                    ),
                )
        return coords

    @staticmethod
    def _interpolate_levelset_to_grid_backend(
        xp,
        phi_source,
        source_coords,
        target_coords,
    ):
        """Separable tensor-product linear interpolation on backend arrays."""
        idx_x, frac_x = Grid._monotone_interval_indices_backend(
            xp,
            source_coords[0],
            target_coords[0],
        )
        left_x = xp.take(phi_source, idx_x, axis=0)
        right_x = xp.take(phi_source, idx_x + 1, axis=0)
        x_interp = left_x + frac_x[:, None] * (right_x - left_x)

        idx_y, frac_y = Grid._monotone_interval_indices_backend(
            xp,
            source_coords[1],
            target_coords[1],
        )
        left_y = xp.take(x_interp, idx_y, axis=1)
        right_y = xp.take(x_interp, idx_y + 1, axis=1)
        return left_y + frac_y[None, :] * (right_y - left_y)

    @staticmethod
    def _nodal_levelset_gradient_backend(xp, phi, coords_axis, axis: int):
        """Nonuniform nodal gradient along one axis on backend arrays."""
        values = xp.moveaxis(phi, axis, 0)
        grad = xp.empty_like(values)
        grad[0] = (values[1] - values[0]) / (coords_axis[1] - coords_axis[0])
        grad[-1] = (values[-1] - values[-2]) / (coords_axis[-1] - coords_axis[-2])
        denom = coords_axis[2:] - coords_axis[:-2]
        grad[1:-1] = (values[2:] - values[:-2]) / denom.reshape(
            (denom.size,) + (1,) * (values.ndim - 1)
        )
        return xp.moveaxis(grad, 0, axis)

    @staticmethod
    def _apply_regular_stratum_line_shift_backend(
        xp,
        coords_axis,
        phi,
        gradient,
        violation,
        axis: int,
        value_floor,
        *,
        floor: float,
    ):
        """Apply one vectorized coordinate-line correction sweep."""
        abs_grad = xp.abs(gradient)
        valid = violation & (abs_grad > 1.0e-14)
        deficit = xp.maximum(value_floor - xp.abs(phi), 0.0)
        sign_phi = xp.where(phi >= 0.0, 1.0, -1.0)
        sign_grad = xp.where(gradient >= 0.0, 1.0, -1.0)
        proposed = sign_phi * sign_grad * deficit / xp.where(
            abs_grad > 1.0e-14,
            abs_grad,
            1.0,
        )
        score = xp.where(valid, abs_grad, -1.0)
        other_axis = 1 - axis
        best = xp.argmax(score, axis=other_axis)
        if axis == 0:
            selected = xp.take_along_axis(proposed, best[:, None], axis=1)[:, 0]
            has_valid = xp.any(valid, axis=1)
        else:
            selected = xp.take_along_axis(proposed, best[None, :], axis=0)[0, :]
            has_valid = xp.any(valid, axis=0)

        interior = xp.ones_like(coords_axis, dtype=bool)
        interior[0] = False
        interior[-1] = False
        selected = xp.where(has_valid & interior, selected, 0.0)

        lower = coords_axis.copy()
        upper = coords_axis.copy()
        lower[1:-1] = coords_axis[:-2] + floor
        upper[1:-1] = coords_axis[2:] - floor
        shifted = xp.clip(coords_axis + selected, lower, upper)
        return xp.where(interior, shifted, coords_axis)

    def _regular_stratum_value_floor(self) -> float:
        length_scale = min(
            float(length) / max(int(count), 1)
            for length, count in zip(self.L, self.N)
        )
        roundoff_floor = 64.0 * np.finfo(float).eps * max(float(max(self.L)), 1.0)
        return max(0.02 * length_scale, roundoff_floor)

    def _interpolate_levelset_to_current_grid(
        self,
        phi_source: np.ndarray,
        source_coords: list[np.ndarray],
    ) -> np.ndarray:
        if phi_source.shape != tuple(count + 1 for count in self.N):
            raise ValueError("level-set source shape does not match grid shape")
        target_x = np.asarray(self.coords[0], dtype=float)
        target_y = np.asarray(self.coords[1], dtype=float)
        source_x = np.asarray(source_coords[0], dtype=float)
        source_y = np.asarray(source_coords[1], dtype=float)
        x_interp = np.empty((target_x.size, source_y.size), dtype=float)
        for j in range(source_y.size):
            x_interp[:, j] = np.interp(target_x, source_x, phi_source[:, j])
        out = np.empty((target_x.size, target_y.size), dtype=float)
        for i in range(target_x.size):
            out[i, :] = np.interp(target_y, source_y, x_interp[i, :])
        return out

    def _move_node_coordinate_line_off_interface(
        self,
        phi: np.ndarray,
        node: tuple[int, int],
        *,
        active_axes: tuple[int, ...],
        value_floor: float,
        fitting_dx_floor: tuple[float, ...],
    ) -> bool:
        phi_value = float(phi[node])
        deficit = value_floor - abs(phi_value)
        if deficit <= 0.0:
            return False

        candidates = []
        for axis in active_axes:
            index = node[axis]
            if index <= 0 or index >= self.N[axis]:
                continue
            gradient = self._nodal_levelset_gradient(phi, node, axis)
            if abs(gradient) <= 1.0e-14:
                continue
            candidates.append((abs(gradient), axis, gradient))
        if not candidates:
            return False
        _magnitude, axis, gradient = max(candidates, key=lambda item: item[0])

        coords_axis = np.asarray(self.coords[axis], dtype=float).copy()
        index = node[axis]
        floor = max(float(fitting_dx_floor[axis]), 1.0e-12 * float(self.L[axis]))
        lower = coords_axis[index - 1] + floor
        upper = coords_axis[index + 1] - floor
        if not lower < upper:
            return False

        if phi_value == 0.0:
            positive_room = upper - coords_axis[index]
            negative_room = coords_axis[index] - lower
            direction = 1.0 if positive_room >= negative_room else -1.0
        else:
            direction = np.sign(phi_value) * np.sign(gradient)
        shift = direction * deficit / abs(gradient)
        shifted = float(np.clip(coords_axis[index] + shift, lower, upper))
        if shifted == coords_axis[index]:
            return False

        coords_axis[index] = shifted
        self.coords[axis] = coords_axis
        self._refresh_node_spacing(axis)
        return True

    def _nodal_levelset_gradient(
        self,
        phi: np.ndarray,
        node: tuple[int, int],
        axis: int,
    ) -> float:
        coords_axis = np.asarray(self.coords[axis], dtype=float)
        index = node[axis]
        selector_left = list(node)
        selector_right = list(node)
        if index <= 0:
            selector_right[axis] = index + 1
            distance = coords_axis[index + 1] - coords_axis[index]
            return float((phi[tuple(selector_right)] - phi[node]) / distance)
        if index >= self.N[axis]:
            selector_left[axis] = index - 1
            distance = coords_axis[index] - coords_axis[index - 1]
            return float((phi[node] - phi[tuple(selector_left)]) / distance)
        selector_left[axis] = index - 1
        selector_right[axis] = index + 1
        distance = coords_axis[index + 1] - coords_axis[index - 1]
        return float((phi[tuple(selector_right)] - phi[tuple(selector_left)]) / distance)

    def _refresh_node_spacings(self) -> None:
        for axis in range(self.ndim):
            self._refresh_node_spacing(axis)

    def _refresh_node_spacing(self, axis: int) -> None:
        cell_dx = np.diff(np.asarray(self.coords[axis], dtype=float))
        node_dx = np.empty(self.N[axis] + 1)
        node_dx[0] = cell_dx[0]
        node_dx[-1] = cell_dx[-1]
        node_dx[1:-1] = 0.5 * (cell_dx[:-1] + cell_dx[1:])
        self.h[axis] = node_dx

    def _build_metrics(self, ccd=None) -> None:
        """Compute CCD metrics J = dxi/dx and dJ/dxi for each axis.

        Delegates to core.metrics.compute_metrics() (SRP extraction).
        """
        self._device_coord_cache.clear()
        self._device_cell_width_cache.clear()
        self._device_metric_cache.clear()
        self._device_metric_gradient_cache.clear()
        self.J, self.dJ_dxi = compute_metrics(
            self.coords, self.h, self.N, self.ndim, self.uniform, ccd,
        )
        axes = self._cell_volume_axes_from_bc(self.bc_type)
        self._cell_volumes = self._build_cell_volume_field(axes)
        self._cell_volume_axes = axes

    # ── Convenience ──────────────────────────────────────────────────────

    @property
    def uniform(self) -> bool:
        """True when the grid is uniform (alpha_grid ≤ 1)."""
        return self._gc.alpha_grid <= 1.0

    def cell_volume(self) -> float:
        """Approximate uniform cell volume (product of mean spacings)."""
        return math.prod(L / N for L, N in zip(self.L, self.N))

    def set_boundary_type(self, bc_type) -> None:
        """Set the topology used by physical nodal control volumes."""
        axes = self._cell_volume_axes_from_bc(bc_type)
        if axes == self._cell_volume_axes:
            self.bc_type = bc_type
            return
        self.bc_type = bc_type
        self._cell_volumes = None
        self._cell_volume_axes = None

    def cell_volumes(self, bc_type=None):
        """Per-node physical control volumes on the boundary quotient.

        The CCD metric spacing ``self.h`` is retained on non-periodic axes
        because the current pressure/FCCD Hodge contracts are calibrated to
        that nodal metric.  For periodic axes, however, the terminal nodal
        plane is an image of node 0 and carries zero independent measure, while
        node 0 receives the wrapped half cell.
        """
        axes = self._cell_volume_axes_from_bc(
            self.bc_type if bc_type is None else bc_type
        )
        if self._cell_volumes is not None and self._cell_volume_axes == axes:
            return self._cell_volumes
        self._cell_volumes = self._build_cell_volume_field(axes)
        self._cell_volume_axes = axes
        return self._cell_volumes

    def _cell_volume_axes_from_bc(self, bc_type) -> tuple[str, ...]:
        """Reduce boundary labels to physical quotient axes for integration."""
        flags = periodic_axis_flags(bc_type, self.ndim)
        return tuple("periodic" if flag else "wall" for flag in flags)

    def _build_cell_volume_field(self, axes=None):
        """Materialize the physical control-volume field for this grid build."""
        if axes is None:
            axes = self._cell_volume_axes_from_bc(self.bc_type)
        xp = self.xp
        vol = xp.asarray(self._axis_control_widths(0, axes[0]))
        for ax in range(1, self.ndim):
            vol = xp.expand_dims(vol, axis=ax) * xp.asarray(
                self._axis_control_widths(ax, axes[ax])
            )
        return vol

    def _axis_control_widths(self, axis: int, boundary: str) -> np.ndarray:
        """Return one-dimensional dual-cell widths for one coordinate axis."""
        coords = np.asarray(self.coords[axis], dtype=float)
        widths = np.empty_like(coords)
        if coords.size == 1:
            widths[0] = self.L[axis]
            return widths
        cell_widths = np.diff(coords)
        if str(boundary).lower() == "periodic":
            widths[:-1] = 0.5 * (np.roll(cell_widths, 1) + cell_widths)
            widths[-1] = 0.0
            return widths
        return np.asarray(self.h[axis], dtype=float)

    def __repr__(self) -> str:
        h_str = " × ".join(
            f"{self.L[ax]/self.N[ax]:.4g}" for ax in range(self.ndim)
        )
        return f"Grid(ndim={self.ndim}, N={self.N}, L={self.L}, h≈{h_str})"
