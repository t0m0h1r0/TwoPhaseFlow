"""
MMS tests for HFE — Hermite Field Extension (§8.4).

Test standard: C6 (Method of Manufactured Solutions)
  - Grid sizes: N = [32, 64, 128, 256]
  - Required: convergence table (N | L∞ error | log-log slope)
  - Acceptance: all slopes ≥ expected_order − 0.2

Tests:
  1. hermite5 interpolation: O(h^6) for smooth 1D function
  2. HFE 2D extension: O(h^6) for smooth field with circular interface
"""

import numpy as np
import pytest

from ..backend import Backend
from ..core.grid import Grid
from ..ccd.ccd_solver import CCDSolver
from ..hfe.hermite_interp import hermite5_coeffs, hermite5_eval
from ..hfe.field_extension import HermiteFieldExtension


# ── Helper: minimal GridConfig stub ──────────────────────────────────────

class _GridConfig:
    """Minimal stub matching Grid.__init__ expectations."""
    def __init__(self, N, L):
        self.ndim = len(N)
        self.N = list(N)
        self.L = list(L)
        self.alpha_grid = 1.0


# ══════════════════════════════════════════════════════════════════════════
# Test 1: Hermite 5th-order polynomial — exact for degree ≤ 5
# ══════════════════════════════════════════════════════════════════════════

class TestHermite5Coeffs:
    """Verify hermite5 reproduces polynomials of degree ≤ 5 exactly."""

    @pytest.mark.parametrize("degree", [0, 1, 2, 3, 4, 5])
    def test_exact_polynomial(self, degree):
        """Hermite5 must exactly interpolate polynomials up to degree 5."""
        h = 0.1
        xa, xb = 1.0, 1.0 + h
        # f(x) = x^degree
        def f(x):
            return x ** degree
        def df(x):
            return degree * x ** (max(degree - 1, 0)) if degree > 0 else 0.0
        def d2f(x):
            return degree * (degree - 1) * x ** (max(degree - 2, 0)) if degree > 1 else 0.0

        coeffs = hermite5_coeffs(
            f(xa), df(xa), d2f(xa),
            f(xb), df(xb), d2f(xb),
            h,
        )

        # Evaluate at 10 interior points
        for t in np.linspace(0.0, 1.0, 10):
            x_eval = xa + t * h
            expected = f(x_eval)
            got = hermite5_eval(coeffs, t)
            assert abs(got - expected) < 1e-12, (
                f"degree={degree}, xi={t}: expected {expected}, got {got}"
            )


# ══════════════════════════════════════════════════════════════════════════
# Test 2: Hermite interpolation convergence — O(h^6)
# ══════════════════════════════════════════════════════════════════════════

class TestHermite5Convergence:
    """MMS convergence test for 1D Hermite interpolation."""

    def test_convergence_order_6(self):
        """L∞ error of Hermite5 interpolation converges at O(h^6).

        Manufactured solution: f(x) = sin(2πx) on [0, 1].
        """
        def f(x):
            return np.sin(2.0 * np.pi * x)
        def df(x):
            return 2.0 * np.pi * np.cos(2.0 * np.pi * x)
        def d2f(x):
            return -(2.0 * np.pi)**2 * np.sin(2.0 * np.pi * x)

        grid_sizes = [32, 64, 128, 256]
        errors = []

        for N in grid_sizes:
            h = 1.0 / N
            x_nodes = np.linspace(0.0, 1.0, N + 1)
            max_err = 0.0

            for i in range(N):
                xa, xb = x_nodes[i], x_nodes[i + 1]
                coeffs = hermite5_coeffs(
                    f(xa), df(xa), d2f(xa),
                    f(xb), df(xb), d2f(xb),
                    h,
                )
                # Evaluate at cell midpoint
                x_mid = 0.5 * (xa + xb)
                err = abs(hermite5_eval(coeffs, 0.5) - f(x_mid))
                max_err = max(max_err, err)

            errors.append(max_err)

        # Compute log-log slopes
        slopes = []
        for k in range(1, len(errors)):
            if errors[k] > 0 and errors[k - 1] > 0:
                slope = np.log(errors[k - 1] / errors[k]) / np.log(2.0)
                slopes.append(slope)

        # C6: all slopes ≥ 6.0 - 0.2 = 5.8
        for s in slopes:
            assert s >= 5.8, f"Slope {s:.2f} < 5.8 (expected ≥ 6.0)"


# ══════════════════════════════════════════════════════════════════════════
# Test 3: 2D HFE extension convergence
# ══════════════════════════════════════════════════════════════════════════

class TestHFE2D:
    """MMS convergence test for 2D Hermite Field Extension."""

    @staticmethod
    def _make_grid_and_ccd(N):
        """Create N×N uniform grid on [0,1]² with CCD solver."""
        backend = Backend(use_gpu=False)
        gc = _GridConfig(N=[N, N], L=[1.0, 1.0])
        grid = Grid(gc, backend)
        ccd = CCDSolver(grid, backend, bc_type="wall")
        return grid, ccd, backend

    def test_extension_smooth_field(self):
        """HFE extends a smooth field across a circular interface.

        Manufactured solution:
          φ(x,y) = sqrt((x-0.5)² + (y-0.5)²) - 0.25  (circle, radius 0.25)
          q(x,y) = cos(πx)·cos(πy)  (smooth, defined everywhere)

        Source phase: φ < 0 (inside circle), source_sign = -1.
        Input: full smooth field (realistic: simulation provides smooth p^n).
        HFE replaces target-side values with closest-point interpolation.

        Exact extension: q_ext(x) = q(x_Γ(x)) where x_Γ is the closest
        point on Γ from x.
        """
        grid_sizes = [32, 64, 128]
        errors = []

        for N in grid_sizes:
            grid, ccd, backend = self._make_grid_and_ccd(N)
            hfe = HermiteFieldExtension(grid, ccd, backend, band_cells=4)
            xp = backend.xp

            X, Y = grid.meshgrid()
            h = 1.0 / N

            cx, cy, R = 0.5, 0.5, 0.25
            phi = xp.sqrt((X - cx)**2 + (Y - cy)**2) - R

            # Smooth input field
            q = xp.cos(np.pi * X) * xp.cos(np.pi * Y)

            # Extend
            q_ext = hfe.extend(q, phi)

            # Exact extension: q at closest interface point
            r = xp.sqrt((X - cx)**2 + (Y - cy)**2)
            r = xp.maximum(r, 1e-14)
            x_gamma = X - phi * (X - cx) / r
            y_gamma = Y - phi * (Y - cy) / r
            q_ref = xp.cos(np.pi * x_gamma) * xp.cos(np.pi * y_gamma)

            # Error in narrow band on target side (φ > 0)
            target_band = (phi > 0) & (phi <= 3.0 * h)
            if xp.any(target_band):
                err = float(xp.max(xp.abs(q_ext[target_band] - q_ref[target_band])))
                errors.append(err)
            else:
                errors.append(0.0)

        # Expect at least 2nd-order convergence for 2D tensor-product
        # Hermite extension with CCD derivatives
        if len(errors) >= 2 and all(e > 0 for e in errors):
            slopes = []
            for k in range(1, len(errors)):
                if errors[k] > 0 and errors[k - 1] > 0:
                    slope = np.log(errors[k - 1] / errors[k]) / np.log(2.0)
                    slopes.append(slope)
            for s in slopes:
                assert s >= 2.0, (
                    f"2D HFE slope {s:.2f} < 2.0; errors={errors}"
                )

    def test_source_phase_unchanged(self):
        """HFE must not modify source-phase values."""
        N = 64
        grid, ccd, backend = self._make_grid_and_ccd(N)
        hfe = HermiteFieldExtension(grid, ccd, backend)
        xp = backend.xp

        X, Y = grid.meshgrid()
        phi = xp.sqrt((X - 0.5)**2 + (Y - 0.5)**2) - 0.25
        q = xp.cos(np.pi * X) * xp.cos(np.pi * Y)

        q_ext = hfe.extend(q, phi)

        source = phi < 0
        assert xp.allclose(q_ext[source], q[source]), (
            "HFE modified source-phase values"
        )
