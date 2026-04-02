#!/usr/bin/env python3
"""Extension PDE × CCD 検証実験

Extension PDE: ∂q/∂τ + S(φ) n̂·∇q = 0  (Aslam 2004)
を CCD D^(1) + Forward Euler で離散化し、以下を検証する:

  Test 1: 1D step function → 延長後の滑らかさ（CCD微分の振動消滅）
  Test 2: 2D 円形界面・圧力ジャンプ → 延長後の CCD ∇p 精度
  Test 3: 2D Laplace 圧力 → CSF シミュレーション内で Extension 有無の比較
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ════════════════════════════════════════════════════════════════════════════
# Extension PDE solver (standalone, Reinitializer 圧縮ステージと同型)
# ════════════════════════════════════════════════════════════════════════════

def _pad_neumann(arr, ax, pad_width):
    """Pad array with Neumann (reflect-value) BC along axis."""
    ndim = arr.ndim
    sl_lo = [slice(None)] * ndim; sl_lo[ax] = slice(0, 1)
    sl_hi = [slice(None)] * ndim; sl_hi[ax] = slice(-1, None)
    pads = [(0, 0)] * ndim
    pads[ax] = (pad_width, pad_width)
    out = np.pad(arr, pads, mode='edge')
    return out


def _dccd_derivative(ccd, f, ax, eps_d=0.25):
    """CCD D^(1) + DCCD filter — same as Reinitializer compression stage.

    Returns filtered first derivative: f̃' = f' + εd(f'_{i+1} - 2f'_i + f'_{i-1})
    εd=0.25 zeroes the 2Δx checkerboard mode (Eq. dccd_eps_checkerboard).
    """
    ndim = f.ndim
    d1, _ = ccd.differentiate(f, ax)
    # DCCD 3-point filter (same as Reinitializer._dccd_compression_div)
    d1_pad = _pad_neumann(d1, ax, 1)
    N_ax = f.shape[ax]
    sl_c  = [slice(None)] * ndim; sl_c[ax]  = slice(1, N_ax + 1)
    sl_p1 = [slice(None)] * ndim; sl_p1[ax] = slice(2, N_ax + 2)
    sl_m1 = [slice(None)] * ndim; sl_m1[ax] = slice(0, N_ax)
    d1_filt = (d1_pad[tuple(sl_c)]
               + eps_d * (d1_pad[tuple(sl_p1)]
                          - 2.0 * d1_pad[tuple(sl_c)]
                          + d1_pad[tuple(sl_m1)]))
    return d1_filt


def extend_field(ccd, grid, q, phi, n_iter=5, cfl=0.5, direction=None):
    """Extension PDE: ∂q/∂τ + S(φ) n̂·∇q = 0

    Two-stage approach:
      1. Upwind FD for extension advection (handles discontinuous q)
      2. After extension, q_ext is smooth → CCD can differentiate it

    Normal n̂ is computed via CCD (φ is always smooth).

    Parameters
    ----------
    ccd       : CCDSolver
    grid      : Grid
    q         : array — field to extend
    phi       : array — signed distance (liquid > 0, gas < 0)
    n_iter    : int   — pseudo-time iterations
    cfl       : float — CFL safety factor
    direction : None → extend both phases outward
                +1  → extend φ>0 values into φ<0 region
                -1  → extend φ<0 values into φ>0 region

    Returns
    -------
    q_ext : array — extended field (smooth, CCD-ready)
    """
    ndim = grid.ndim
    h = [float(grid.L[ax] / grid.N[ax]) for ax in range(ndim)]
    h_min = min(h)
    dtau = cfl * h_min

    # Normal n̂ = ∇φ / |∇φ| via CCD (φ is smooth → CCD OK)
    dphi = []
    for ax in range(ndim):
        d1, _ = ccd.differentiate(phi, ax)
        dphi.append(d1)
    grad_sq = sum(g * g for g in dphi)
    grad_norm = np.maximum(np.sqrt(np.maximum(grad_sq, 1e-28)), 1e-14)
    n_hat = [g / grad_norm for g in dphi]

    # Extension direction:
    #   direction=-1: extend φ<0 (source) values into φ≥0 (target)
    #   direction=+1: extend φ>0 (source) values into φ≤0 (target)
    #   direction=None: bidirectional (both phases extend outward)
    #
    # sign_phi drives propagation: +1 in target (φ>0), -1 in source (φ<0).
    # At φ=0 (interface nodes): assign to TARGET phase to enable seeding.
    if direction is not None:
        source_sign = float(direction)
        # Source: freeze. Target (opposite sign + interface): update.
        # φ=0 nodes go to target by using >= or <= instead of > or <.
        if source_sign < 0:
            sign_phi = np.where(phi >= 0, +1.0, -1.0)
            freeze = (phi < 0)
        else:
            sign_phi = np.where(phi <= 0, -1.0, +1.0)
            freeze = (phi > 0)
    else:
        sign_phi = np.where(phi >= 0, +1.0, -1.0)
        freeze = np.zeros_like(phi, dtype=bool)

    a = [sign_phi * n_hat[ax] for ax in range(ndim)]

    q_ext = np.copy(q)

    for _ in range(n_iter):
        rhs = np.zeros_like(q_ext)
        for ax in range(ndim):
            h_ax = h[ax]
            N_ax = grid.N[ax]

            # D⁺ (forward) and D⁻ (backward) differences
            dq_fwd = np.zeros_like(q_ext)
            dq_bwd = np.zeros_like(q_ext)

            sl_c  = [slice(None)] * ndim
            sl_p  = [slice(None)] * ndim
            sl_m  = [slice(None)] * ndim
            sl_c[ax] = slice(1, N_ax)
            sl_p[ax] = slice(2, N_ax + 1)
            sl_m[ax] = slice(0, N_ax - 1)
            dq_fwd[tuple(sl_c)] = (q_ext[tuple(sl_p)] - q_ext[tuple(sl_c)]) / h_ax
            dq_bwd[tuple(sl_c)] = (q_ext[tuple(sl_c)] - q_ext[tuple(sl_m)]) / h_ax

            # Boundary: Neumann
            sl_0 = [slice(None)] * ndim; sl_0[ax] = 0
            sl_1 = [slice(None)] * ndim; sl_1[ax] = 1
            sl_N = [slice(None)] * ndim; sl_N[ax] = N_ax
            sl_Nm1 = [slice(None)] * ndim; sl_Nm1[ax] = N_ax - 1
            dq_fwd[tuple(sl_0)] = (q_ext[tuple(sl_1)] - q_ext[tuple(sl_0)]) / h_ax
            dq_bwd[tuple(sl_N)] = (q_ext[tuple(sl_N)] - q_ext[tuple(sl_Nm1)]) / h_ax

            # Upwind: a > 0 → D⁻ (backward), a < 0 → D⁺ (forward)
            rhs += a[ax] * np.where(a[ax] > 0, dq_bwd, dq_fwd)

        q_new = q_ext - dtau * rhs
        q_new[freeze] = q[freeze]  # restore source phase values
        q_ext = q_new

    return q_ext


# ════════════════════════════════════════════════════════════════════════════
# Test 1: 1D step function extension
# ════════════════════════════════════════════════════════════════════════════

def test_1d_step_extension():
    """2D slice: 圧力に不連続ジャンプ → Extension PDE → CCD 微分の振動が消えるか

    y方向に一様な 2D 場を使い、x方向の延長を検証（実質1D）。
    """
    from twophase.backend import Backend
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver
    from twophase.config import GridConfig

    print("=" * 60)
    print("Test 1: 1D-like step function extension (2D grid)")
    print("=" * 60)

    N = 64
    gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    be = Backend()
    grid = Grid(gcfg, be)
    ccd = CCDSolver(grid, be, bc_type='wall')

    X, Y = grid.meshgrid()
    x = X[:, 0]
    # Signed distance: φ = x - 0.5 (interface at x=0.5)
    phi = X - 0.5

    # Pressure with Laplace jump: p = 4.0 for x < 0.5, p = 0.0 for x >= 0.5
    p = np.where(X < 0.5, 4.0, 0.0)

    # CCD gradient of raw discontinuous field
    dp_raw, _ = ccd.differentiate(p, 0)

    # Extend: liquid is x < 0.5 where φ < 0.
    # Extend liquid values (p=4) into gas region: direction=-1 means propagate φ<0 → φ>0
    # direction=-1: source is φ<0 (liquid, x<0.5), extend into φ>0 (gas)
    # n_iter=40: cover ~20 cells at CFL=0.5 → reaches x>0.6
    p_ext = extend_field(ccd, grid, p, phi, n_iter=40, direction=-1)

    dp_ext, _ = ccd.differentiate(p_ext, 0)

    # Report along centerline y=N//2
    j = N // 2
    interface_zone = (np.abs(x - 0.5) < 0.1)
    print(f"  max|dp/dx| raw  (|x-0.5|<0.1): {np.max(np.abs(dp_raw[interface_zone, j])):.2f}")
    print(f"  max|dp/dx| ext  (|x-0.5|<0.1): {np.max(np.abs(dp_ext[interface_zone, j])):.2f}")
    print(f"  max|dp/dx| raw  (global):       {np.max(np.abs(dp_raw[:, j])):.2f}")
    print(f"  max|dp/dx| ext  (global):       {np.max(np.abs(dp_ext[:, j])):.2f}")

    liquid_bulk = x < 0.4
    print(f"  max|dp/dx| raw  (liquid bulk):  {np.max(np.abs(dp_raw[liquid_bulk, j])):.4f}")
    print(f"  max|dp/dx| ext  (liquid bulk):  {np.max(np.abs(dp_ext[liquid_bulk, j])):.4f}")

    gas_region = x > 0.6
    print(f"  p_ext in gas (x>0.6): mean={np.mean(p_ext[gas_region, j]):.4f}, "
          f"std={np.std(p_ext[gas_region, j]):.4f} (expect ~4.0)")

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(8, 6))
    axes[0].plot(x, p[:, j], 'k--', label='p (raw, discontinuous)')
    axes[0].plot(x, p_ext[:, j], 'b-', label='p (extended)')
    axes[0].axvline(0.5, color='gray', ls=':')
    axes[0].set_ylabel('p'); axes[0].legend(); axes[0].set_title('Pressure field (y=0.5 slice)')

    axes[1].plot(x, dp_raw[:, j], 'r-', label="CCD dp/dx (raw)", alpha=0.7)
    axes[1].plot(x, dp_ext[:, j], 'b-', label="CCD dp/dx (extended)")
    axes[1].axvline(0.5, color='gray', ls=':')
    axes[1].set_ylabel('dp/dx'); axes[1].legend(); axes[1].set_title('CCD gradient')
    axes[1].set_xlabel('x')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'ext_pde_test1_1d.png'), dpi=150)
    plt.close()
    print(f"  -> Figure saved: ext_pde_test1_1d.png\n")


# ════════════════════════════════════════════════════════════════════════════
# Test 2: 2D circular interface — pressure jump extension
# ════════════════════════════════════════════════════════════════════════════

def test_2d_laplace_extension():
    """2D: 円形界面の Laplace 圧力ジャンプ → Extension → CCD ∇p 精度"""
    from twophase.backend import Backend
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver
    from twophase.config import GridConfig

    print("=" * 60)
    print("Test 2: 2D Laplace pressure extension")
    print("=" * 60)

    N = 64
    R = 0.25
    dp_laplace = 4.0  # κ/We = (1/R)/We for We=1

    gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
    be = Backend()
    grid = Grid(gcfg, be)
    ccd = CCDSolver(grid, be, bc_type='wall')

    X, Y = grid.meshgrid()
    dist = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
    phi = dist - R  # φ > 0 outside (gas), φ < 0 inside (liquid)

    # Exact Laplace pressure: p_in = dp_laplace, p_out = 0
    # Smoothed over ~2h using tanh transition
    h = 1.0 / N
    eps_trans = 1.5 * h
    p_exact = dp_laplace * 0.5 * (1.0 - np.tanh(phi / eps_trans))

    # Sharp version (discontinuous)
    p_sharp = np.where(dist < R, dp_laplace, 0.0)

    # Extend liquid pressure into gas region
    # liquid is φ < 0 (inside circle), extend direction = -1 means
    # propagate from φ<0 to φ>0
    # direction=-1: source is φ<0 (liquid inside), extend into φ>0 (gas outside)
    p_sharp_ext = extend_field(ccd, grid, p_sharp, phi, n_iter=40, direction=-1)

    # CCD gradients
    dpx_sharp, _ = ccd.differentiate(p_sharp, 0)
    dpx_ext, _ = ccd.differentiate(p_sharp_ext, 0)
    dpx_smooth, _ = ccd.differentiate(p_exact, 0)

    # Compare along centerline y = 0.5
    j = N // 2
    x = X[:, j]

    print(f"  Along y=0.5 centerline:")
    near_if = (np.abs(dist[:, j] - R) < 3 * h)
    print(f"  max|∇p_x| sharp  (near Γ): {np.max(np.abs(dpx_sharp[:, j][near_if])):.2f}")
    print(f"  max|∇p_x| ext    (near Γ): {np.max(np.abs(dpx_ext[:, j][near_if])):.2f}")
    print(f"  max|∇p_x| smooth (near Γ): {np.max(np.abs(dpx_smooth[:, j][near_if])):.2f}")

    # In liquid bulk (dist < 0.5*R), ∇p should be ~0
    liquid = dist[:, j] < 0.5 * R
    print(f"  max|∇p_x| sharp  (liquid): {np.max(np.abs(dpx_sharp[:, j][liquid])):.4f}")
    print(f"  max|∇p_x| ext    (liquid): {np.max(np.abs(dpx_ext[:, j][liquid])):.4f}")
    print(f"  max|∇p_x| smooth (liquid): {np.max(np.abs(dpx_smooth[:, j][liquid])):.4f}")

    # Plot
    fig, axes = plt.subplots(2, 1, figsize=(8, 6))
    axes[0].plot(x, p_sharp[:, j], 'k--', label='p (sharp)')
    axes[0].plot(x, p_sharp_ext[:, j], 'b-', label='p (extended)')
    axes[0].plot(x, p_exact[:, j], 'g:', label='p (tanh-smooth)')
    axes[0].axvline(0.5 - R, color='gray', ls=':')
    axes[0].axvline(0.5 + R, color='gray', ls=':')
    axes[0].set_ylabel('p'); axes[0].legend(); axes[0].set_title('Pressure along y=0.5')

    axes[1].plot(x, dpx_sharp[:, j], 'r-', alpha=0.5, label='CCD ∂p/∂x (sharp)')
    axes[1].plot(x, dpx_ext[:, j], 'b-', label='CCD ∂p/∂x (extended)')
    axes[1].plot(x, dpx_smooth[:, j], 'g:', label='CCD ∂p/∂x (smooth)')
    axes[1].axvline(0.5 - R, color='gray', ls=':')
    axes[1].axvline(0.5 + R, color='gray', ls=':')
    axes[1].set_ylabel('∂p/∂x'); axes[1].legend()
    axes[1].set_title('CCD gradient comparison')
    axes[1].set_xlabel('x')

    plt.tight_layout()
    plt.savefig(os.path.join(os.path.dirname(__file__), 'ext_pde_test2_2d.png'), dpi=150)
    plt.close()
    print(f"  → Figure saved: ext_pde_test2_2d.png\n")


# ════════════════════════════════════════════════════════════════════════════
# Test 3: Convergence order — smooth field extension
# ════════════════════════════════════════════════════════════════════════════

def test_convergence_order():
    """Extension の空間収束次数を検証。

    既知の滑らか場 q = cos(2πr) に不連続を導入 → Extension → 精度測定。
    CCD O(h⁶) が界面近傍でも維持されるか確認。
    """
    from twophase.backend import Backend
    from twophase.core.grid import Grid
    from twophase.ccd.ccd_solver import CCDSolver
    from twophase.config import GridConfig

    print("=" * 60)
    print("Test 3: Convergence order of Extension PDE")
    print("=" * 60)

    R = 0.25
    Ns = [32, 64, 128]
    errors_raw = []
    errors_ext = []

    for N in Ns:
        gcfg = GridConfig(ndim=2, N=(N, N), L=(1.0, 1.0))
        be = Backend()
        grid = Grid(gcfg, be)
        ccd = CCDSolver(grid, be, bc_type='wall')

        X, Y = grid.meshgrid()
        dist = np.sqrt((X - 0.5)**2 + (Y - 0.5)**2)
        phi = dist - R

        # Smooth reference: q = 4 - 16*(dist - 0.5)^2 inside, something outside
        # We want: q_liquid(r) = 4 - 16*(r - 0.5)^2 for r < R
        # Extension should propagate this into gas: q_ext(x) ≈ q_liquid(x_Γ(x))
        # i.e., constant along normals = constant along radial direction = q_liquid(R)
        q_liquid_at_R = 4.0 - 16.0 * (R - 0.5)**2

        # Construct field: smooth inside, zero outside (discontinuous at Γ)
        q_inside = 4.0 - 16.0 * (dist - 0.5)**2
        q = np.where(dist < R, q_inside, 0.0)

        # Expected after extension: q_liquid_at_R everywhere outside
        q_expected = np.where(dist < R, q_inside, q_liquid_at_R)

        # Extend
        q_ext = extend_field(ccd, grid, q, phi, n_iter=20, direction=-1)

        # Measure error in a band outside the interface
        band = (phi > 0.5 / N) & (phi < 5.0 / N)
        if band.any():
            err_raw = np.max(np.abs(q[band] - q_expected[band]))
            err_ext = np.max(np.abs(q_ext[band] - q_expected[band]))
        else:
            err_raw = err_ext = float('nan')

        errors_raw.append(err_raw)
        errors_ext.append(err_ext)
        print(f"  N={N:4d}: err_raw={err_raw:.4e}  err_ext={err_ext:.4e}")

    # Compute convergence orders
    if len(Ns) >= 2 and not any(np.isnan(errors_ext)):
        for i in range(1, len(Ns)):
            order = np.log(errors_ext[i-1] / errors_ext[i]) / np.log(Ns[i] / Ns[i-1])
            print(f"  Order ({Ns[i-1]}→{Ns[i]}): {order:.2f}")
    print()


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    test_1d_step_extension()
    test_2d_laplace_extension()
    test_convergence_order()
    print("All Extension PDE verification tests completed.")
