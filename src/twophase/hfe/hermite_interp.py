"""
CCD Hermite 5th-order polynomial interpolation.

Paper reference: §8.4, Eq. (hermite5)

Given CCD Hermite data (f, f', f'') at two adjacent grid points x_a, x_b
(spacing h = x_b - x_a), constructs a unique 5th-degree polynomial P(ξ)
satisfying 6 constraints:

    P(0) = f_a,        P(1) = f_b
    P'(0) = h·f'_a,    P'(1) = h·f'_b
    P''(0) = h²·f''_a,  P''(1) = h²·f''_b

where ξ = (x - x_a) / h ∈ [0, 1].

Interpolation error: |P(x) - f(x)| = O(h^6)   — Eq. (hermite5_error)

Symbol mapping (paper → code):
    x_a, x_b       → xa, xb
    f_a, f'_a, f''_a → fa, dfa, d2fa
    f_b, f'_b, f''_b → fb, dfb, d2fb
    ξ               → xi
    c_0 ... c_5     → coeffs[0:6]
    h               → h
"""

from __future__ import annotations
import numpy as np


def hermite5_coeffs(
    fa: float, dfa: float, d2fa: float,
    fb: float, dfb: float, d2fb: float,
    h: float,
) -> np.ndarray:
    """Compute 5th-degree Hermite polynomial coefficients in ξ-space.

    Parameters
    ----------
    fa, dfa, d2fa : function value, 1st and 2nd derivatives at x_a
    fb, dfb, d2fb : function value, 1st and 2nd derivatives at x_b
    h : grid spacing x_b - x_a

    Returns
    -------
    coeffs : ndarray, shape (6,)
        Polynomial coefficients [c_0, ..., c_5] such that
        P(ξ) = c_0 + c_1·ξ + c_2·ξ² + c_3·ξ³ + c_4·ξ⁴ + c_5·ξ⁵
    """
    # Scaled derivatives (ξ-space): P^(j)(0) = h^j · f_a^(j)
    F0 = fa
    F1 = h * dfa
    F2 = h * h * d2fa
    G0 = fb
    G1 = h * dfb
    G2 = h * h * d2fb

    # Solve 6×6 system (closed-form from Vandermonde-like structure):
    #   P(0) = c0 = F0
    #   P'(0) = c1 = F1
    #   P''(0) = 2·c2 = F2
    #   P(1) = c0 + c1 + c2 + c3 + c4 + c5 = G0
    #   P'(1) = c1 + 2c2 + 3c3 + 4c4 + 5c5 = G1
    #   P''(1) = 2c2 + 6c3 + 12c4 + 20c5 = G2
    c0 = F0
    c1 = F1
    c2 = 0.5 * F2

    # From the last 3 equations:
    #   c3 + c4 + c5 = G0 - c0 - c1 - c2          ... (A)
    #   3c3 + 4c4 + 5c5 = G1 - c1 - 2*c2          ... (B)
    #   6c3 + 12c4 + 20c5 = G2 - 2*c2              ... (C)
    A = G0 - c0 - c1 - c2
    B = G1 - c1 - 2.0 * c2
    C = G2 - 2.0 * c2

    # Solve 3×3 system:
    #   | 1  1  1 | |c3|   |A|
    #   | 3  4  5 | |c4| = |B|
    #   | 6 12 20 | |c5|   |C|
    # Determinant = 1*(80-60) - 1*(60-30) + 1*(36-24) = 20 - 30 + 12 = 2
    c3 = (20.0 * A - 8.0 * B + C) / 2.0
    c4 = (-30.0 * A + 14.0 * B - 2.0 * C) / 2.0
    c5 = (12.0 * A - 6.0 * B + C) / 2.0

    return np.array([c0, c1, c2, c3, c4, c5])


def hermite5_eval(coeffs: np.ndarray, xi: float) -> float:
    """Evaluate 5th-degree Hermite polynomial at ξ using Horner's method.

    Parameters
    ----------
    coeffs : ndarray, shape (6,)
        Coefficients from hermite5_coeffs.
    xi : float
        Evaluation point in ξ-space. Typically ξ ∈ [0, 1] for interpolation,
        but may exceed this range for one-sided extrapolation (§8.4).

    Returns
    -------
    value : float
        P(ξ)
    """
    # Horner: c0 + xi*(c1 + xi*(c2 + xi*(c3 + xi*(c4 + xi*c5))))
    return float(
        coeffs[0] + xi * (
            coeffs[1] + xi * (
                coeffs[2] + xi * (
                    coeffs[3] + xi * (
                        coeffs[4] + xi * coeffs[5]
                    )
                )
            )
        )
    )


def hermite5_eval_batch(coeffs: np.ndarray, xi: np.ndarray) -> np.ndarray:
    """Vectorised evaluation of Hermite polynomial at multiple ξ values.

    Parameters
    ----------
    coeffs : ndarray, shape (M, 6)  — M sets of coefficients
    xi : ndarray, shape (M,)        — evaluation points

    Returns
    -------
    values : ndarray, shape (M,)
    """
    return (
        coeffs[:, 0]
        + xi * (coeffs[:, 1]
        + xi * (coeffs[:, 2]
        + xi * (coeffs[:, 3]
        + xi * (coeffs[:, 4]
        + xi * coeffs[:, 5]))))
    )
