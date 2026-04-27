"""Scheme factory registry — wraps library operator classes into scheme adapters.

Each factory function is registered via @register_scheme and called by handlers as:

    adapter = SCHEME_REGISTRY["ccd"](N=64, domain={"Lx": 1.0, "Ly": 1.0}, bc_type="wall")
    errors = adapter.compute_errors(test_fn)

Adapters expose a uniform interface per experiment category:
  - SpatialSchemeAdapter: compute_errors(test_fn) → dict
  - TimeIntegratorAdapter: run(n_steps, dt, ic) → dict  [future]
  - AdvectionAdapter: advect(q0, vel, dt, n_steps) → array  [future]
"""

from __future__ import annotations

import numpy as np

from .registry import register_scheme


def _build_ccd(N: int, domain: dict, bc_type: str = "periodic",
               alpha_grid: float = 1.0, nonuniform_init: bool = False,
               diff_axes=None, **_):
    """Build a CCDSolver and return a _CCDAdapter."""
    from twophase.backend import Backend
    from twophase.config import GridConfig
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver

    backend = Backend()
    Lx = float(domain.get("Lx", 1.0))
    Ly = float(domain.get("Ly", 1.0))
    gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Ly), alpha_grid=alpha_grid)
    grid = Grid(gc, backend)

    if nonuniform_init and alpha_grid > 1.0:
        # Fit grid to a circular interface at domain centre (standard non-uniform probe)
        ccd_tmp = CCDSolver(grid, backend, bc_type="wall")
        X0, Y0 = np.meshgrid(
            np.linspace(0, Lx, N + 1),
            np.linspace(0, Ly, N + 1),
            indexing="ij",
        )
        R = min(Lx, Ly) * 0.25
        phi_init = np.sqrt((X0 - Lx / 2) ** 2 + (Y0 - Ly / 2) ** 2) - R
        grid.update_from_levelset(phi_init, eps=0.05, ccd=ccd_tmp)
        h_eff = float(
            sum(float(backend.to_host(grid.h[ax]).mean()) for ax in range(2)) / 2
        )
    else:
        h_eff = Lx / N

    ccd = CCDSolver(grid, backend, bc_type=bc_type)

    axes = tuple(diff_axes) if diff_axes is not None else (0, 1)
    return _CCDAdapter(ccd, grid, backend, bc_type=bc_type,
                       diff_axes=axes, h=h_eff, N=N)


def _build_ab2_ode(ode: str = "decay", **_):
    return _AB2OdeAdapter(ode=ode)


# ── Young-Laplace / curvature convergence ────────────────────────────────────

class _YoungLaplaceAdapter:
    """Measures Δp = κ (We=1) for a circular droplet of radius R."""

    def __init__(self, R: float = 0.25, We: float = 1.0, eps_scale: float = 1.5):
        self.R = R
        self.We = We
        self.eps_scale = eps_scale

    def compute_errors(self, test_fn=None) -> dict:
        raise NotImplementedError("YoungLaplaceAdapter uses compute_dp, not compute_errors.")

    def compute_dp(self, N: int, domain: dict) -> dict:
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.curvature import CurvatureCalculator
        from twophase.levelset.heaviside import heaviside

        backend = Backend()
        xp = backend.xp
        Lx = float(domain.get("Lx", 1.0))
        Ly = float(domain.get("Ly", 1.0))
        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Ly))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        h = Lx / N
        eps = self.eps_scale * h
        X, Y = grid.meshgrid()

        phi = self.R - xp.sqrt((X - Lx / 2) ** 2 + (Y - Ly / 2) ** 2)
        psi = heaviside(xp, phi, eps)
        curv_calc = CurvatureCalculator(backend, ccd, eps)
        kappa = curv_calc.compute(psi)

        near = xp.abs(phi) < 3 * h
        kappa_mean = float(xp.mean(kappa[near])) if bool(xp.any(near)) else float("nan")
        Dp_exact = (1.0 / self.R) / self.We
        Dp_measured = kappa_mean / self.We
        rel_err = abs(Dp_measured - Dp_exact) / Dp_exact

        return {"N": N, "h": h, "Dp": Dp_measured, "Dp_exact": Dp_exact, "rel_err": rel_err}


def _build_young_laplace(N: int, domain: dict, R: float = 0.25,
                          We: float = 1.0, eps_scale: float = 1.5, **_):
    return _YoungLaplaceScheme(R=R, We=We, eps_scale=eps_scale, N=N, domain=domain)


def _build_ppe_neumann(N: int, domain: dict, k_dc: int = 3, **_):
    return _PPENeumannScheme(N=N, domain=domain, k_dc=k_dc)


# ── Hydrostatic NS (ch12-style IPC projection) ───────────────────────────────

class _HydrostaticNSScheme:
    """IPC projection for hydrostatic equilibrium (rho=1, gravity=-1 in y).

    Convergence metric: L∞ pressure error vs p_exact = ρ|g|(1-y).
    """

    def __init__(self, N: int, domain: dict,
                 n_steps: int = 100, rho: float = 1.0,
                 g_y: float = -1.0, dt_scale: float = 0.1):
        self._N = N
        self._domain = domain
        self._n_steps = n_steps
        self._rho = rho
        self._g_y = g_y
        self._dt_scale = dt_scale

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.ppe.ppe_builder import PPEBuilder
        from twophase.tools.experiment.gpu import sparse_solve_2d

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        dt = self._dt_scale * h

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        ppe_builder = PPEBuilder(backend, grid, bc_type="wall")

        X, Y = grid.meshgrid()
        rho = xp.full_like(X, self._rho)

        u = xp.zeros_like(X)
        v = xp.zeros_like(X)
        p = self._rho * abs(self._g_y) * (1.0 - Y)   # exact IC

        def wall_bc(arr):
            arr[0, :] = 0; arr[-1, :] = 0
            arr[:, 0] = 0; arr[:, -1] = 0

        def solve_ppe(rhs):
            triplet, shape = ppe_builder.build(rho)
            data, rows, cols = [backend.to_device(a) for a in triplet]
            A = backend.sparse.csr_matrix((data, (rows, cols)), shape=shape)
            return sparse_solve_2d(backend, A, rhs.ravel()).reshape(rhs.shape)

        u_max_final = 0.0
        for _ in range(self._n_steps):
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)
            u_star = u - dt / rho * dp_dx
            v_star = v + dt * self._g_y - dt / rho * dp_dy
            wall_bc(u_star); wall_bc(v_star)
            du_dx, _ = ccd.differentiate(u_star, 0)
            dv_dy, _ = ccd.differentiate(v_star, 1)
            phi = solve_ppe((du_dx + dv_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_star - dt / rho * dphi_dx
            v = v_star - dt / rho * dphi_dy
            wall_bc(u); wall_bc(v)
            p = p + phi
            u_max_final = float(xp.max(xp.sqrt(u**2 + v**2)))
            if _np.isnan(u_max_final) or u_max_final > 1e6:
                break

        p_exact = self._rho * abs(self._g_y) * (1.0 - Y)
        p_shifted = p - xp.mean(p) + xp.mean(p_exact)
        s = slice(2, -2)
        p_err = float(xp.max(xp.abs(p_shifted[s, s] - p_exact[s, s])))
        return {"N": N, "h": h, "p_err_inf": p_err, "u_inf_final": u_max_final}


@register_scheme("hydrostatic_ns")
def _build_hydrostatic_ns(N: int, domain: dict, n_steps: int = 100,
                           rho: float = 1.0, g_y: float = -1.0,
                           dt_scale: float = 0.1, **_):
    return _HydrostaticNSScheme(N=N, domain=domain, n_steps=n_steps,
                                rho=rho, g_y=g_y, dt_scale=dt_scale)


def _build_curvature_ccd(N: int, domain: dict, interface: str = "circle",
                          R: float = 0.25, eps_scale: float = 1.5, **_):
    return _CurvatureCCDScheme(N=N, domain=domain, interface=interface,
                               R=R, eps_scale=eps_scale)


def _build_rc_bracket(N: int, domain: dict, **_):
    return _RCBracketScheme(N=N, domain=domain)


def _build_dc_poisson_dirichlet(N: int, domain: dict, k_dc: int = 3, **_):
    return _DCPoissonDirichletScheme(N=N, domain=domain, k_dc=k_dc)


def _build_varrho_ppe_smooth(N: int, domain: dict, A: float = 0.8, k_dc: int = 3, **_):
    return _VarroPPESmoothScheme(N=N, domain=domain, A=A, k_dc=k_dc)


def _build_mixed_partial_ccd(N: int, domain: dict, bc_type: str = "periodic", **_):
    return _MixedPartialCCDScheme(N=N, domain=domain, bc_type=bc_type)


def _build_reinit_shift(N: int, domain: dict, n_calls: int = 1,
                         eps_coeff: float = 1.5, **_):
    return _ReinitShiftScheme(N=N, domain=domain, n_calls=n_calls, eps_coeff=eps_coeff)


def _build_tvd_rk3_ode(**_):
    return _TVDrk3OdeAdapter()


def _build_tvd_rk3_advection(N: int = 256, **_):
    return _TVDrk3AdvectionAdapter(N=N)


def _build_cross_viscous_lte(N: int = 64, mu_ratio: float = 1.0,
                              mu_base: float = 0.01, **_):
    return _CrossViscousLTEAdapter(N=N, mu_ratio=mu_ratio, mu_base=mu_base)


def _build_cn_viscous_temporal(N: int = 64, nu: float = 0.01, **_):
    return _CNViscousTemporalAdapter(N=N, nu=nu)


# ── Kovasznay NS residual (exp12_05) ──────────────────────────────────────────

class _KovasznayNSScheme:
    """Steady NS momentum + divergence residual on Kovasznay exact flow."""

    def __init__(self, N: int, domain: dict, Re: float = 40.0):
        self._N = N
        self._domain = domain
        self._Re = Re

    def compute_errors(self, test_fn=None) -> dict:
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import (
            kovasznay_velocity, kovasznay_pressure,
        )

        backend = Backend()
        xp = backend.xp
        N = self._N
        Lx = float(self._domain.get("Lx", 1.0))
        h = Lx / N
        nu = 1.0 / self._Re

        gc = GridConfig(ndim=2, N=(N, N), L=(Lx, Lx))
        grid = Grid(gc, backend)
        # Shift y to [-0.5, 0.5]
        grid.coords[1] = grid.coords[1] - 0.5
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()

        u, v = kovasznay_velocity(X, Y, self._Re)
        p = kovasznay_pressure(X, Y, self._Re)

        du_dx, d2u_dx2 = ccd.differentiate(u, 0)
        du_dy, d2u_dy2 = ccd.differentiate(u, 1)
        dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
        dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
        dp_dx, _ = ccd.differentiate(p, 0)
        dp_dy, _ = ccd.differentiate(p, 1)

        R_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2) - dp_dx
        R_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2) - dp_dy
        R_div = du_dx + dv_dy

        s = (slice(1, -1), slice(1, -1))
        err_mom = float(max(xp.max(xp.abs(R_u[s])), xp.max(xp.abs(R_v[s]))))
        err_div = float(xp.max(xp.abs(R_div[s])))
        return {"N": N, "h": h, "err_mom": err_mom, "err_div": err_div}


@register_scheme("kovasznay_ns")
def _build_kovasznay_ns(N: int, domain: dict, Re: float = 40.0, **_):
    return _KovasznayNSScheme(N=N, domain=domain, Re=Re)


# ── TGV AB2 temporal convergence (exp12_04) ───────────────────────────────────

class _TGVab2Adapter:
    """AB2 + IPC projection on TGV; L∞ velocity error vs dt at fixed N."""

    def __init__(self, N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307):
        self._N = N
        self._nu = nu
        self._L = L_dom

    def run(self, n_steps: int, T_final: float = 0.5) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import tgv_velocity

        backend = Backend()
        xp = backend.xp
        N = self._N
        nu = self._nu
        L = self._L
        h = L / N
        dt = T_final / n_steps

        gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        def fft_poisson(rhs):
            rhs_int = rhs[:-1, :-1]
            Ni = rhs_int.shape[0]
            kx = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            ky = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            KX, KY = xp.meshgrid(kx, ky, indexing="ij")
            K2 = KX**2 + KY**2; K2[0, 0] = 1.0
            p_hat = xp.fft.fft2(rhs_int) / (-K2); p_hat[0, 0] = 0.0
            p_int = xp.real(xp.fft.ifft2(p_hat))
            p = xp.zeros_like(rhs)
            p[:-1, :-1] = p_int; p[-1, :] = p[0, :]; p[:, -1] = p[:, 0]
            return p

        u, v = tgv_velocity(X, Y, 0.0, nu)
        p = -0.25 * (xp.cos(2 * X) + xp.cos(2 * Y))
        rhs_u_prev = rhs_v_prev = None

        for step in range(n_steps):
            du_dx, d2u_dx2 = ccd.differentiate(u, 0)
            du_dy, d2u_dy2 = ccd.differentiate(u, 1)
            dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
            dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
            rhs_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2)
            rhs_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2)
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)

            if step == 0:
                u_s = u + dt * rhs_u - dt * dp_dx
                v_s = v + dt * rhs_v - dt * dp_dy
            else:
                u_s = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * dp_dx
                v_s = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * dp_dy

            rhs_u_prev, rhs_v_prev = rhs_u, rhs_v
            du_s_dx, _ = ccd.differentiate(u_s, 0)
            dv_s_dy, _ = ccd.differentiate(v_s, 1)
            phi = fft_poisson((du_s_dx + dv_s_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_s - dt * dphi_dx
            v = v_s - dt * dphi_dy
            p = p + phi

        u_ex, v_ex = tgv_velocity(X, Y, T_final, nu)
        err = float(max(xp.max(xp.abs(u - u_ex)), xp.max(xp.abs(v - v_ex))))
        return {"n": n_steps, "dt": dt, "q_final": err}


@register_scheme("tgv_ab2")
def _build_tgv_ab2(N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307, **_):
    return _TGVab2Adapter(N=N, nu=nu, L_dom=L_dom)


# ── CN interface viscous temporal (exp12_13) ──────────────────────────────────

class _CNInterfaceViscousAdapter:
    """CN viscous with jump μ; measures bulk vs interface L2 error vs dt.

    Returns q_final = bulk_l2 (primary metric for time_accuracy handler).
    """

    def __init__(self, N: int = 64, mu_base: float = 0.01, mu_ratio: float = 100.0,
                 decay: float = 1.0):
        self._N = N
        self._mu_base = mu_base
        self._mu_ratio = mu_ratio
        self._decay = decay

    def run(self, n_steps: int, T_final: float = 0.1) -> dict:
        import numpy as _np
        from scipy.sparse.linalg import gmres, LinearOperator
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver

        backend = Backend()
        xp = backend.xp
        N = self._N
        dt = T_final / n_steps
        k = 2 * _np.pi
        decay = self._decay

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X_d, Y_d = grid.meshgrid()
        X = _np.asarray(backend.to_host(X_d))
        Y = _np.asarray(backend.to_host(Y_d))

        h = 1.0 / N
        eps = 2.0 * h
        H = 0.5 * (1 + _np.tanh((X - 0.5) / eps))
        mu = self._mu_base * (1.0 + (self._mu_ratio - 1.0) * H)
        mu_d = xp.asarray(mu)

        def u_exact(t):
            return _np.exp(-decay * t) * _np.sin(k * X) * _np.sin(k * Y)

        def visc_op(u_np):
            u_d = xp.asarray(u_np)
            _, d2y = ccd.differentiate(u_d, 1)
            Lv = _np.asarray(backend.to_host(mu_d * d2y))
            return Lv

        u = u_exact(0.0)
        shape = u.shape
        n = u.size

        # MMS source: f = u_t - L[u]  where L[u] = mu(x)*d2u/dy2
        # u = exp(-decay*t)*sin(kx)*sin(ky) → d2u/dy2 = -k^2*u
        # f = -decay*u - mu*(-k^2)*u = u*(-decay + k^2*mu) (time-independent)
        f = u_exact(0.0) * (-decay + k**2 * mu)

        for _ in range(n_steps):
            Lv_n = visc_op(u)
            rhs = (u + 0.5 * dt * Lv_n + dt * f).flatten()

            def matvec(v_flat):
                v = v_flat.reshape(shape)
                return (v - 0.5 * dt * visc_op(v)).flatten()

            A_op = LinearOperator((n, n), matvec=matvec)
            u_new, _ = gmres(A_op, rhs, x0=u.flatten(), atol=1e-14,
                             restart=200, maxiter=1000)
            u = u_new.reshape(shape)

        u_ref = u_exact(T_final)
        err = _np.sqrt(_np.mean((u - u_ref)**2))

        bulk_mask = _np.abs(X - 0.5) > 6 * eps
        intf_mask = _np.abs(X - 0.5) < 3 * eps
        bulk_l2 = float(_np.sqrt(_np.mean(((u - u_ref)[bulk_mask])**2))) if bulk_mask.any() else float("nan")
        intf_l2 = float(_np.sqrt(_np.mean(((u - u_ref)[intf_mask])**2))) if intf_mask.any() else float("nan")

        return {"n": n_steps, "dt": dt, "q_final": bulk_l2, "intf_l2": intf_l2}


@register_scheme("cn_interface_viscous")
def _build_cn_interface_viscous(N: int = 64, mu_base: float = 0.01,
                                 mu_ratio: float = 100.0, decay: float = 1.0, **_):
    return _CNInterfaceViscousAdapter(N=N, mu_base=mu_base,
                                      mu_ratio=mu_ratio, decay=decay)


# ── TGV AB2 time history ──────────────────────────────────────────────────────

class _TGVab2HistoryAdapter:
    """AB2 + IPC projection on TGV; records E_k(t) and ||div||_∞ history."""

    def __init__(self, N: int = 64, nu: float = 0.01, L_dom: float = 6.283185307):
        self._N = N
        self._nu = nu
        self._L = L_dom

    def run_history(self, n_steps: int = 200, dt: float = 0.01,
                    checkpoint_interval: int = 5) -> list:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.tools.benchmarks.analytical_solutions import tgv_velocity

        backend = Backend()
        xp = backend.xp
        N, nu, L = self._N, self._nu, self._L
        h = L / N

        gc = GridConfig(ndim=2, N=(N, N), L=(L, L))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        def fft_poisson(rhs):
            rhs_int = rhs[:-1, :-1]
            Ni = rhs_int.shape[0]
            kx = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            ky = xp.fft.fftfreq(Ni, d=h) * 2 * _np.pi
            KX, KY = xp.meshgrid(kx, ky, indexing="ij")
            K2 = KX**2 + KY**2; K2[0, 0] = 1.0
            p_hat = xp.fft.fft2(rhs_int) / (-K2); p_hat[0, 0] = 0.0
            p_int = xp.real(xp.fft.ifft2(p_hat))
            p = xp.zeros_like(rhs)
            p[:-1, :-1] = p_int; p[-1, :] = p[0, :]; p[:, -1] = p[:, 0]
            return p

        u, v = tgv_velocity(X, Y, 0.0, nu)
        p = -0.25 * (xp.cos(2 * X) + xp.cos(2 * Y))
        rhs_u_prev = rhs_v_prev = None
        history: list[dict] = []

        for step in range(n_steps):
            t = step * dt
            if step % checkpoint_interval == 0:
                E_k = float(0.5 * (xp.mean(u**2) + xp.mean(v**2)))
                E_k_exact = _np.pi**2 * _np.exp(-4 * nu * t) / L**2 * h**2 * N**2
                # Simple exact: 0.5*(u_ex^2 + v_ex^2) mean
                u_ex, v_ex = tgv_velocity(X, Y, t, nu)
                E_k_exact = float(0.5 * (xp.mean(u_ex**2) + xp.mean(v_ex**2)))
                du_dx, _ = ccd.differentiate(u, 0)
                dv_dy, _ = ccd.differentiate(v, 1)
                div_inf = float(xp.max(xp.abs(du_dx + dv_dy)))
                history.append({"t": t, "E_k": E_k, "E_k_exact": E_k_exact,
                                 "div_inf": div_inf})

            du_dx, d2u_dx2 = ccd.differentiate(u, 0)
            du_dy, d2u_dy2 = ccd.differentiate(u, 1)
            dv_dx, d2v_dx2 = ccd.differentiate(v, 0)
            dv_dy, d2v_dy2 = ccd.differentiate(v, 1)
            rhs_u = -(u * du_dx + v * du_dy) + nu * (d2u_dx2 + d2u_dy2)
            rhs_v = -(u * dv_dx + v * dv_dy) + nu * (d2v_dx2 + d2v_dy2)
            dp_dx, _ = ccd.differentiate(p, 0)
            dp_dy, _ = ccd.differentiate(p, 1)

            if step == 0:
                u_s = u + dt * rhs_u - dt * dp_dx
                v_s = v + dt * rhs_v - dt * dp_dy
            else:
                u_s = u + dt * (1.5 * rhs_u - 0.5 * rhs_u_prev) - dt * dp_dx
                v_s = v + dt * (1.5 * rhs_v - 0.5 * rhs_v_prev) - dt * dp_dy

            rhs_u_prev, rhs_v_prev = rhs_u, rhs_v
            du_s_dx, _ = ccd.differentiate(u_s, 0)
            dv_s_dy, _ = ccd.differentiate(v_s, 1)
            phi = fft_poisson((du_s_dx + dv_s_dy) / dt)
            dphi_dx, _ = ccd.differentiate(phi, 0)
            dphi_dy, _ = ccd.differentiate(phi, 1)
            u = u_s - dt * dphi_dx
            v = v_s - dt * dphi_dy
            p = p + phi

        # Final checkpoint
        t_final = n_steps * dt
        u_ex, v_ex = tgv_velocity(X, Y, t_final, nu)
        E_k = float(0.5 * (xp.mean(u**2) + xp.mean(v**2)))
        E_k_exact = float(0.5 * (xp.mean(u_ex**2) + xp.mean(v_ex**2)))
        du_dx, _ = ccd.differentiate(u, 0)
        dv_dy, _ = ccd.differentiate(v, 1)
        div_inf = float(xp.max(xp.abs(du_dx + dv_dy)))
        history.append({"t": t_final, "E_k": E_k, "E_k_exact": E_k_exact,
                         "div_inf": div_inf})
        return history


@register_scheme("tgv_ab2_history")
def _build_tgv_ab2_history(N: int = 64, nu: float = 0.01,
                            L_dom: float = 6.283185307, domain=None, **_):
    return _TGVab2HistoryAdapter(N=N, nu=nu, L_dom=L_dom)


def _build_pressure_filter(N: int = 64, eps_d: float = 0.0, **kw):
    return _PressureFilterScheme(N=N, eps_d=eps_d)


# ── Cross-viscous CFL (binary search, parameter_sweep) ─────────────────────

class _CrossViscousCFLScheme:
    """Binary-search critical dt for cross-viscous explicit Euler step.

    Sweeps mu_ratio = mu_l/mu_g. Returns C_cross = dt_crit * Δμ / (ρ h²) ≈ 0.23.
    """

    _MU_G = 0.01
    _RHO = 1.0
    _R_IFACE = 0.25
    _N_CHECK = 20
    _GROW_LIMIT = 10.0

    def __init__(self, N: int = 64, mu_ratio: float = 10.0, **_):
        self._N = N
        self._mu_ratio = float(mu_ratio)

    def compute_result(self) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.heaviside import heaviside

        backend = Backend()
        xp = backend.xp
        N = self._N
        h = 1.0 / N
        eps = 1.5 * h

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        X, Y = grid.meshgrid()

        mu_g = self._MU_G
        mu_l = mu_g * self._mu_ratio
        phi = self._R_IFACE - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
        H = heaviside(xp, phi, eps)
        mu = mu_g + (mu_l - mu_g) * H
        delta_mu = max(float(mu_l - mu_g), float(mu_g))

        u0 = xp.sin(2 * _np.pi * X) * xp.sin(2 * _np.pi * Y)

        def _cross_visc(u):
            du_dx, _ = ccd.differentiate(u, 0)
            du_dy, _ = ccd.differentiate(u, 1)
            d_dx, _ = ccd.differentiate(mu * du_dy, 0)
            d_dy, _ = ccd.differentiate(mu * du_dx, 1)
            return d_dx + d_dy

        def _stable(dt):
            u = u0.copy()
            thresh = self._GROW_LIMIT * float(xp.max(xp.abs(u)))
            for _ in range(self._N_CHECK):
                u = u + dt * _cross_visc(u)
                if not _np.isfinite(float(xp.max(xp.abs(u)))) or float(xp.max(xp.abs(u))) > thresh:
                    return False
            return True

        dt_scale = h ** 2 * self._RHO / delta_mu
        dt_lo, dt_hi = 0.01 * dt_scale, 2.0 * dt_scale
        while not _stable(dt_lo):
            dt_lo *= 0.5
        while _stable(dt_hi):
            dt_hi *= 2.0
        for _ in range(60):
            dt_mid = 0.5 * (dt_lo + dt_hi)
            if _stable(dt_mid):
                dt_lo = dt_mid
            else:
                dt_hi = dt_mid
            if (dt_hi - dt_lo) / max(dt_lo, 1e-300) < 0.01:
                break

        dt_crit = dt_lo
        C_cross = dt_crit * delta_mu / (self._RHO * h ** 2)
        return {"mu_ratio": self._mu_ratio, "dt_crit": float(dt_crit), "C_cross": float(C_cross)}


@register_scheme("cross_viscous_cfl")
def _build_cross_viscous_cfl(N: int = 64, mu_ratio: float = 10.0, domain=None, **_):
    return _CrossViscousCFLScheme(N=N, mu_ratio=mu_ratio)


# ── Capillary CFL (binary search, convergence_study over N) ───────────────

class _CapillaryCFLScheme:
    """Binary-search critical dt for 1D linearized capillary wave (RK4, pure numpy)."""

    _RHO_L = 2.0
    _RHO_G = 1.0
    _SIGMA = 1.0
    _L = 1.0
    _N_PROBE = 400
    _GROW_LIMIT = 10.0

    def __init__(self, N: int = 64, sigma: float = 1.0, rho_l: float = 2.0,
                 rho_g: float = 1.0, **_):
        self._N = N
        self._sigma = sigma
        self._rho_l = rho_l
        self._rho_g = rho_g

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np

        N = self._N
        L = self._L
        h = L / N
        sigma = self._sigma
        rho_l, rho_g = self._rho_l, self._rho_g
        grow_limit = self._GROW_LIMIT
        n_probe = self._N_PROBE

        x = _np.arange(N) * h
        eta0 = _np.sin(_np.pi * x / h) + 1e-3 * _np.sin(2 * _np.pi * x / L)
        if _np.max(_np.abs(eta0)) < 1e-14:
            eta0 = _np.cos(_np.pi * x / h)

        k = 2.0 * _np.pi * _np.fft.fftfreq(N, d=h)
        k3 = (sigma / (rho_l + rho_g)) * _np.abs(k) ** 3

        def _rk4(eta, vel, dt):
            def rhs(e, v):
                return v, _np.fft.ifft(-k3 * _np.fft.fft(e)).real
            k1e, k1v = rhs(eta, vel)
            k2e, k2v = rhs(eta + 0.5 * dt * k1e, vel + 0.5 * dt * k1v)
            k3e, k3v = rhs(eta + 0.5 * dt * k2e, vel + 0.5 * dt * k2v)
            k4e, k4v = rhs(eta + dt * k3e, vel + dt * k3v)
            return (eta + dt / 6.0 * (k1e + 2 * k2e + 2 * k3e + k4e),
                    vel + dt / 6.0 * (k1v + 2 * k2v + 2 * k3v + k4v))

        def _stable(dt):
            eta, vel = eta0.copy(), _np.zeros_like(eta0)
            amp0 = max(float(_np.max(_np.abs(eta))), 1e-30)
            for _ in range(n_probe):
                eta, vel = _rk4(eta, vel, dt)
                amp = max(float(_np.max(_np.abs(eta))), float(_np.max(_np.abs(vel))))
                if not _np.isfinite(amp) or amp > grow_limit * amp0:
                    return False
            return True

        dt_sigma = _np.sqrt((rho_l + rho_g) * h ** 3 / (2.0 * _np.pi * sigma))
        dt_lo, dt_hi = 0.05 * dt_sigma, 4.0 * dt_sigma
        while not _stable(dt_lo):
            dt_lo *= 0.5
        while _stable(dt_hi):
            dt_hi *= 1.5
        for _ in range(80):
            dt_mid = 0.5 * (dt_lo + dt_hi)
            if _stable(dt_mid):
                dt_lo = dt_mid
            else:
                dt_hi = dt_mid
            if (dt_hi - dt_lo) / max(dt_lo, 1e-300) < 0.005:
                break

        dt_max = float(dt_lo)
        return {"N": N, "h": h, "dt_max": dt_max,
                "dt_sigma": float(dt_sigma), "ratio": dt_max / float(dt_sigma)}


@register_scheme("capillary_cfl")
def _build_capillary_cfl(N: int = 64, sigma: float = 1.0,
                          rho_l: float = 2.0, rho_g: float = 1.0,
                          domain=None, **_):
    return _CapillaryCFLScheme(N=N, sigma=sigma, rho_l=rho_l, rho_g=rho_g)


# ── Galilean CLS invariance (scheme_comparison: lab vs rest frame) ─────────

class _GalileanCLSScheme:
    """CLS advection Galilean invariance test.

    case='lab'  — uniform background u=U_BG; circle traverses domain once.
    case='rest' — u=0; circle stays; trivially accurate baseline.

    Returns shape_err (||psi_T - psi_0||_2 / ||psi_0||_2) and mass_err.
    """

    _CFL = 0.25
    _R = 0.25
    _N_TRAVERSALS = 1

    def __init__(self, N: int = 64, U_BG: float = 1.0, case: str = "lab", **_):
        self._N = N
        self._U_BG = float(U_BG)
        self._case = case

    def compute_errors(self, test_fn=None) -> dict:
        import numpy as _np
        from twophase.backend import Backend
        from twophase.config import GridConfig
        from twophase.core.grid import Grid
        from twophase.ccd.ccd_solver import CCDSolver
        from twophase.levelset.heaviside import heaviside
        from twophase.levelset.advection import DissipativeCCDAdvection

        backend = Backend()
        xp = backend.xp
        N = self._N
        h = 1.0 / N
        eps = 1.5 * h
        U_BG = self._U_BG
        is_lab = (self._case == "lab")

        gc = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="periodic")
        advect = DissipativeCCDAdvection(backend, grid, ccd, bc="periodic")

        X, Y = grid.meshgrid()
        phi0 = self._R - xp.sqrt((X - 0.5) ** 2 + (Y - 0.5) ** 2)
        psi0 = heaviside(xp, phi0, eps)
        psi = psi0.copy()

        speed = U_BG if U_BG > 1e-14 else 1.0
        T_total = self._N_TRAVERSALS * 1.0 / speed
        dt = self._CFL * h / speed
        n_steps = max(1, int(_np.ceil(T_total / dt)))
        dt_actual = T_total / n_steps

        u = xp.full_like(X, U_BG if is_lab else 0.0)
        v = xp.zeros_like(X)

        mass0 = float(xp.sum(psi0))
        for _ in range(n_steps):
            psi = advect.advance(psi, [u, v], dt_actual)

        shape_err = float(xp.sqrt(xp.mean((psi - psi0) ** 2)) /
                          max(float(xp.sqrt(xp.mean(psi0 ** 2))), 1e-30))
        mass_T = float(xp.sum(psi))
        mass_err = abs(mass_T - mass0) / max(abs(mass0), 1e-30)
        return {"N": N, "h": h, "shape_err": shape_err, "mass_err": mass_err}


@register_scheme("galilean_cls")
def _build_galilean_cls(N: int = 64, U_BG: float = 1.0, case: str = "lab",
                         domain=None, **_):
    return _GalileanCLSScheme(N=N, U_BG=U_BG, case=case)


# ── Zalesak disk on non-uniform grid (scheme_comparison + parameter_sweep) ──

def _run_zalesak_loop(N, alpha_grid, eps_g_factor, eps_g_cells, eps_xi_cells,
                      eps_ratio, reinit_freq):
    """Shared Zalesak rigid-rotation loop with optional non-uniform grid rebuild.

    Returns {"N", "h", "L2_psi", "area_err", "mass_err"}.
    """
    import numpy as _np
    from twophase.backend import Backend
    from twophase.config import GridConfig
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver
    from twophase.core.grid_remap import build_grid_remapper
    from twophase.levelset.advection import DissipativeCCDAdvection
    from twophase.levelset.reinitialize import Reinitializer
    from twophase.levelset.heaviside import heaviside, invert_heaviside
    from twophase.simulation.initial_conditions.velocity_fields import RigidRotation
    from twophase.simulation.initial_conditions.shapes import ZalesakDisk

    backend = Backend()
    xp = backend.xp

    gc_kw = dict(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    if eps_g_cells is not None:
        gc_kw["eps_g_cells"] = eps_g_cells
    else:
        gc_kw["eps_g_factor"] = eps_g_factor
    gc = GridConfig(**gc_kw)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h

    def _eps_field():
        if eps_xi_cells is not None:
            hx = xp.asarray(grid.h[0])[:, None]   # (N+1, 1) node-centred spacings
            hy = xp.asarray(grid.h[1])[None, :]   # (1, N+1)
            return eps_xi_cells * xp.maximum(hx, hy)
        return eps

    def _zalesak_sdf(X_h, Y_h):
        return ZalesakDisk(center=(0.5, 0.5), radius=0.15,
                           slot_width=0.05, slot_depth=0.25).sdf(X_h, Y_h)

    X, Y = grid.meshgrid()
    X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
    phi0 = xp.asarray(_zalesak_sdf(X_h, Y_h))
    eps_f = _eps_field()
    psi0 = heaviside(xp, phi0, eps_f)

    if alpha_grid > 1.0:
        grid.update_from_levelset(psi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
        phi0 = xp.asarray(_zalesak_sdf(X_h, Y_h))
        eps_f = _eps_field()
        psi0 = heaviside(xp, phi0, eps_f)

    T = 2 * _np.pi
    vf = RigidRotation(center=(0.5, 0.5), period=T)
    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                  eps_d=0.05, mass_correction=True)
    eps_r = float(xp.min(xp.asarray(eps_f))) if eps_xi_cells is not None else eps
    reinit = Reinitializer(backend, grid, ccd, eps_r, n_steps=4,
                           bc="zero", method="split")

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(xp.sum(psi * dV))

    for step in range(n_steps):
        u, v = vf.compute(X, Y, t=0)
        psi = adv.advance(psi, [u, v], dt)

        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            old_coords = [c.copy() for c in grid.coords]
            M_before = float(xp.sum(psi * dV))
            grid.update_from_levelset(psi, eps, ccd=ccd)
            remapper = build_grid_remapper(backend, old_coords, grid.coords)
            psi = xp.clip(remapper.remap(psi), 0.0, 1.0)
            dV = grid.cell_volumes()
            M_after = float(xp.sum(psi * dV))
            w = 4.0 * psi * (1.0 - psi)
            W = float(xp.sum(w * dV))
            if W > 1e-12:
                psi = xp.clip(psi + ((M_before - M_after) / W) * w, 0.0, 1.0)
            ccd = CCDSolver(grid, backend, bc_type="wall")
            adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                          eps_d=0.05, mass_correction=True)
            eps_f = _eps_field()
            eps_r = float(xp.min(xp.asarray(eps_f))) if eps_xi_cells is not None else eps
            reinit = Reinitializer(backend, grid, ccd, eps_r, n_steps=4,
                                   bc="zero", method="split")
            X, Y = grid.meshgrid()

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)

    X, Y = grid.meshgrid()
    X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
    phi0_final = xp.asarray(_zalesak_sdf(X_h, Y_h))
    psi0_final = heaviside(xp, phi0_final, eps)
    dV_final = grid.cell_volumes()
    mass_final = float(xp.sum(psi * dV_final))
    mass_err = abs(mass_final - mass0) / max(abs(mass0), 1e-30)
    L2_psi = float(xp.sqrt(xp.mean((psi - psi0_final) ** 2)))
    psi_area = float(xp.sum(xp.where(psi >= 0.5, dV_final, 0.0)))
    psi0_area = float(xp.sum(xp.where(psi0_final >= 0.5, dV_final, 0.0)))
    area_err = abs(psi_area - psi0_area) / max(abs(psi0_area), 1e-30)
    return {"N": N, "h": h, "L2_psi": L2_psi, "area_err": area_err, "mass_err": mass_err}


class _ZalesakNonuniformScheme:
    """Zalesak rigid rotation with non-uniform grid rebuild (exp12_19, 20)."""

    def __init__(self, N: int = 128, alpha_grid: float = 1.0,
                 eps_g_factor: float = 2.0, eps_g_cells=None,
                 eps_xi_cells=None, eps_ratio: float = 0.5,
                 reinit_freq: int = 20, **_):
        self._kw = dict(N=N, alpha_grid=alpha_grid, eps_g_factor=eps_g_factor,
                        eps_g_cells=eps_g_cells, eps_xi_cells=eps_xi_cells,
                        eps_ratio=eps_ratio, reinit_freq=reinit_freq)

    def compute_errors(self, test_fn=None) -> dict:
        return _run_zalesak_loop(**self._kw)

    def compute_result(self) -> dict:
        return _run_zalesak_loop(**self._kw)


@register_scheme("zalesak_nonuniform")
def _build_zalesak_nonuniform(N: int = 128, alpha_grid: float = 1.0,
                               eps_g_factor: float = 2.0, eps_g_cells=None,
                               eps_xi_cells=None, eps_ratio: float = 0.5,
                               reinit_freq: int = 20, domain=None, **_):
    return _ZalesakNonuniformScheme(N=N, alpha_grid=alpha_grid,
                                    eps_g_factor=eps_g_factor,
                                    eps_g_cells=eps_g_cells,
                                    eps_xi_cells=eps_xi_cells,
                                    eps_ratio=eps_ratio,
                                    reinit_freq=reinit_freq)


# ── Single vortex on non-uniform grid (scheme_comparison, exp12_21) ────────

def _run_single_vortex_loop(N, alpha_grid, eps_g_factor, eps_g_cells, eps_xi_cells,
                             eps_ratio, reinit_freq):
    """Shared single-vortex loop with optional non-uniform grid rebuild.

    Returns {"N", "h", "L2_psi", "area_err", "mass_err"}.
    """
    import numpy as _np
    from twophase.backend import Backend
    from twophase.config import GridConfig
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver
    from twophase.core.grid_remap import build_grid_remapper
    from twophase.levelset.advection import DissipativeCCDAdvection
    from twophase.levelset.reinitialize import Reinitializer
    from twophase.levelset.heaviside import heaviside, invert_heaviside
    from twophase.simulation.initial_conditions.velocity_fields import SingleVortex

    backend = Backend()
    xp = backend.xp

    gc_kw = dict(ndim=2, N=(N, N), L=(1.0, 1.0), alpha_grid=alpha_grid)
    if eps_g_cells is not None:
        gc_kw["eps_g_cells"] = eps_g_cells
    else:
        gc_kw["eps_g_factor"] = eps_g_factor
    gc = GridConfig(**gc_kw)
    grid = Grid(gc, backend)
    ccd = CCDSolver(grid, backend, bc_type="wall")
    h = 1.0 / N
    eps = eps_ratio * h

    def _eps_field():
        if eps_xi_cells is not None:
            hx2d = xp.asarray(grid.h[0])[:, None]   # (N+1, 1) node-centred spacings
            hy2d = xp.asarray(grid.h[1])[None, :]   # (1, N+1)
            return eps_xi_cells * xp.maximum(hx2d, hy2d)
        return eps

    T = 8.0
    vf = SingleVortex(period=T)

    def _circle_sdf(X_h, Y_h):
        return 0.15 - _np.sqrt((X_h - 0.5) ** 2 + (Y_h - 0.75) ** 2)

    X, Y = grid.meshgrid()
    X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
    phi0 = xp.asarray(_circle_sdf(X_h, Y_h))
    eps_f = _eps_field()
    psi0 = heaviside(xp, phi0, eps_f)

    if alpha_grid > 1.0:
        grid.update_from_levelset(psi0, eps, ccd=ccd)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        X, Y = grid.meshgrid()
        X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
        phi0 = xp.asarray(_circle_sdf(X_h, Y_h))
        eps_f = _eps_field()
        psi0 = heaviside(xp, phi0, eps_f)

    adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                  eps_d=0.05, mass_correction=True)
    eps_r = float(xp.min(xp.asarray(eps_f))) if eps_xi_cells is not None else eps
    reinit = Reinitializer(backend, grid, ccd, eps_r, n_steps=4,
                           bc="zero", method="split")

    dt = 0.45 / N
    n_steps = int(T / dt); dt = T / n_steps
    psi = psi0.copy()
    dV = grid.cell_volumes()
    mass0 = float(xp.sum(psi * dV))

    for step in range(n_steps):
        t = step * dt
        u, v = vf.compute(X, Y, t=t)
        psi = adv.advance(psi, [u, v], dt)

        if alpha_grid > 1.0 and (step + 1) % reinit_freq == 0:
            old_coords = [c.copy() for c in grid.coords]
            M_before = float(xp.sum(psi * dV))
            grid.update_from_levelset(psi, eps, ccd=ccd)
            remapper = build_grid_remapper(backend, old_coords, grid.coords)
            psi = xp.clip(remapper.remap(psi), 0.0, 1.0)
            dV = grid.cell_volumes()
            M_after = float(xp.sum(psi * dV))
            w = 4.0 * psi * (1.0 - psi)
            W = float(xp.sum(w * dV))
            if W > 1e-12:
                psi = xp.clip(psi + ((M_before - M_after) / W) * w, 0.0, 1.0)
            ccd = CCDSolver(grid, backend, bc_type="wall")
            adv = DissipativeCCDAdvection(backend, grid, ccd, bc="zero",
                                          eps_d=0.05, mass_correction=True)
            eps_f = _eps_field()
            eps_r = float(xp.min(xp.asarray(eps_f))) if eps_xi_cells is not None else eps
            reinit = Reinitializer(backend, grid, ccd, eps_r, n_steps=4,
                                   bc="zero", method="split")
            X, Y = grid.meshgrid()

        if (step + 1) % reinit_freq == 0:
            psi = reinit.reinitialize(psi)

    X, Y = grid.meshgrid()
    X_h, Y_h = _np.asarray(backend.to_host(X)), _np.asarray(backend.to_host(Y))
    phi0_final = xp.asarray(_circle_sdf(X_h, Y_h))
    psi0_final = heaviside(xp, phi0_final, eps)
    dV_final = grid.cell_volumes()
    mass_final = float(xp.sum(psi * dV_final))
    mass_err = abs(mass_final - mass0) / max(abs(mass0), 1e-30)
    L2_psi = float(xp.sqrt(xp.mean((psi - psi0_final) ** 2)))
    psi_area = float(xp.sum(xp.where(psi >= 0.5, dV_final, 0.0)))
    psi0_area = float(xp.sum(xp.where(psi0_final >= 0.5, dV_final, 0.0)))
    area_err = abs(psi_area - psi0_area) / max(abs(psi0_area), 1e-30)
    return {"N": N, "h": h, "L2_psi": L2_psi, "area_err": area_err, "mass_err": mass_err}


class _SingleVortexCLSScheme:
    """Single vortex (LeVeque) with non-uniform grid rebuild (exp12_21)."""

    def __init__(self, N: int = 128, alpha_grid: float = 1.0,
                 eps_g_factor: float = 2.0, eps_g_cells=None,
                 eps_xi_cells=None, eps_ratio: float = 1.5,
                 reinit_freq: int = 20, **_):
        self._kw = dict(N=N, alpha_grid=alpha_grid, eps_g_factor=eps_g_factor,
                        eps_g_cells=eps_g_cells, eps_xi_cells=eps_xi_cells,
                        eps_ratio=eps_ratio, reinit_freq=reinit_freq)

    def compute_errors(self, test_fn=None) -> dict:
        return _run_single_vortex_loop(**self._kw)


@register_scheme("single_vortex_cls")
def _build_single_vortex_cls(N: int = 128, alpha_grid: float = 1.0,
                               eps_g_factor: float = 2.0, eps_g_cells=None,
                               eps_xi_cells=None, eps_ratio: float = 1.5,
                               reinit_freq: int = 20, domain=None, **_):
    return _SingleVortexCLSScheme(N=N, alpha_grid=alpha_grid,
                                   eps_g_factor=eps_g_factor,
                                   eps_g_cells=eps_g_cells,
                                   eps_xi_cells=eps_xi_cells,
                                   eps_ratio=eps_ratio,
                                   reinit_freq=reinit_freq)
