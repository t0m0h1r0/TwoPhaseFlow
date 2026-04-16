# xi-Space CCD on Non-Uniform Grids: An Impossibility Result

**Date**: 2026-04-17
**Related**: WIKI-T-039, WIKI-T-038, WIKI-T-037

---

## Abstract

We investigate the accuracy of Combined Compact Difference (CCD) schemes on
interface-fitted non-uniform grids, where a coordinate mapping x(xi) concentrates
grid nodes near the interface. The standard approach solves CCD in uniform
computational space (xi) and converts to physical space (x) via the metric
J = d(xi)/dx. We prove that this approach is fundamentally limited for localized
grid refinement: the metric transition occupies a fixed number of xi-cells
regardless of resolution N, preventing convergence of the second derivative.
A Two-Pass reformulation that algebraically eliminates the problematic cross-term
is implemented and MMS-tested, but fails for the same reason -- the intermediate
function g = J * f_xi is equally under-resolved in xi-space. We conclude that
direct non-uniform CCD (with node-dependent coefficients in physical space) is
the necessary path forward.

## 1. Background

### 1.1 CCD Metric Transform

The CCD scheme (Chu & Fan 1998) simultaneously computes f' and f'' on a uniform
grid with spacing h. On a non-uniform physical grid x_i, a mapping xi_i = i/N
provides uniform computational coordinates. Derivatives are converted via:

    df/dx   = J * (df/d(xi))                                          (1)
    d2f/dx2 = J^2 * (d2f/d(xi)^2) + J * (dJ/d(xi)) * (df/d(xi))     (2)

where J = d(xi)/dx = 1/(dx/d(xi)). The second term in (2) is the **cross-term**.

### 1.2 Interface-Fitted Grid

The grid density function concentrates nodes near phi = 0:

    omega(phi) = 1 + (alpha - 1) * exp(-phi^2 / eps_g^2)             (3)

where alpha is the refinement ratio and eps_g = eps_g_factor * eps is the
Gaussian bandwidth. Node spacings are proportional to 1/omega, giving
h_min = h_uniform / alpha near the interface.

### 1.3 Known Problem

Experiments (WIKI-T-037, WIKI-T-038) show that non-uniform grids with alpha=2
produce 94x worse area error than uniform grids in Zalesak disk rotation,
regardless of interpolation order (linear vs cubic remap) or eps_g_factor
bandwidth adjustments.

## 2. Analysis of the Cross-Term

### 2.1 Metric Gradient Scaling

The density function (3) produces a metric J(xi) whose gradient scales as:

    max|dJ/d(xi)| ~ (alpha - 1) * N / (eps_g_factor * eps_ratio)     (4)

For alpha=2, N=128, eps_g_factor=2, eps_ratio=0.5:

    max|dJ/d(xi)| ~ 1 * 128 / (2 * 0.5) = 128

This is 128x the function values being differentiated, making the cross-term
in (2) the dominant error source.

### 2.2 Resolution-Independence of the Transition

The Gaussian density transition has physical width eps_g. In xi-space (uniform
spacing d(xi) = 1/N), the transition spans:

    W_transition = eps_g * N = eps_g_factor * eps_ratio                (5)

**This is independent of N.** With eps_g_factor=2, eps_ratio=0.5, the transition
is always 1 cell in xi-space. CCD requires ~4 cells to resolve a function,
so the metric is permanently under-resolved.

### 2.3 Formal Accuracy Degradation

The CCD achieves O(h^6) for functions that are smooth relative to h. When
dJ/d(xi) ~ O(N), the cross-term error in (2) is:

    |delta(d2f/dx2)| ~ |J * dJ/d(xi)| * |delta(f_xi)| ~ N^2 * h^6 = O(h^4)

The effective accuracy degrades from O(h^6) to O(h^4). Moreover, when the
transition spans < 4 cells, the CCD stencil cannot even achieve its polynomial
accuracy, and the error saturates at O(1).

## 3. Two-Pass Metric Avoidance

### 3.1 Formulation

To eliminate the cross-term algebraically, we reformulate (2) as a composition:

    Pass 1:  g_i = J_i * (df/d(xi))_i  = df/dx |_i               (6)
    Pass 2:  CCD(g, xi) -> dg/d(xi),  then d2f/dx2 = J * dg/d(xi)   (7)

This is exact: g = df/dx implies dg/dx = d2f/dx2, and J * dg/d(xi) = dg/dx.
No cross-term appears.

### 3.2 Implementation

In `ccd_solver.py`, the `_apply_metric` method was modified:

```python
# Original (cross-term formula):
d1_x = J * d1_xi
d2_x = J**2 * d2_xi + J * dJ * d1_xi

# Two-Pass:
d1_x = J * d1_xi                          # Pass 1
g_xi, _ = self._solve_xi_raw(d1_x, axis)  # Pass 2: CCD on g
d2_x = J * g_xi                           # No cross-term
```

### 3.3 Why It Fails

The function g(xi) = J(xi) * f_xi(xi) inherits the rapid variation of J(xi).
The second derivative of g in xi-space:

    d2g/d(xi)^2 ~ 154  (at N=64, alpha=2, eps_g_factor=2)

This is O(N^2), confirming that g is as under-resolved as J itself.

The Two-Pass eliminates the cross-term **in the formula** but cannot eliminate
the cross-term **in the data**. The rapid variation of J is encoded in the nodal
values of g, and CCD cannot resolve it with 1-cell transitions.

### 3.4 MMS Results

f(x) = sin(pi*x), d2f/dx2 = -pi^2*sin(pi*x), alpha=2, eps_g_factor=2:

| N    | d2 Two-Pass | d2 Cross-Term | d1 error |
|------|-------------|---------------|----------|
|  16  |  2.47e-01   |   2.96e-01    | 3.90e-03 |
|  32  |  2.33e-01   |   2.86e-01    | 1.80e-03 |
|  64  |  2.30e-01   |   2.83e-01    | 8.78e-04 |
| 128  |  2.29e-01   |   2.83e-01    | 4.34e-04 |

**Table 1**: d2 error does not converge for either formula. d1 converges at
~O(h^1), degraded from the O(h^6) uniform-grid rate.

With eps_g_factor scaled proportionally to N (maintaining 8 transition cells):

| N    | egf  | d2 Two-Pass | d2 Cross-Term |
|------|------|-------------|---------------|
|  32  |  4.0 |  3.36e-02   |   3.15e-02    |
|  64  |  8.0 |  1.29e-02   |   7.68e-03    |
| 128  | 16.0 |  2.50e-02   |   1.51e-02    |

**Table 2**: When the transition is well-resolved, the cross-term formula
outperforms Two-Pass (one CCD solve vs two accumulates less error).

## 4. The Impossibility Result

**Theorem.** Let the grid density function omega(phi) have compact support of
physical width W_phys in xi-space, the transition spans W_xi = W_phys * N
cells. If W_phys = c * eps = c * eps_ratio * h (proportional to h), then
W_xi = c * eps_ratio, which is independent of N.

**Corollary.** For any algebraic formula that converts xi-space CCD derivatives
to physical space using J(xi) and its derivatives, the d2f/dx2 accuracy is
bounded by the CCD interpolation error for functions with transitions spanning
W_xi cells. When W_xi < 4, d2 accuracy saturates at O(1) regardless of N.

**Corollary.** The only ways to achieve convergence are:
1. Scale W_phys with the domain size (eps_g_factor ~ N), eliminating localization
2. Abandon xi-space CCD entirely and use physical-space node-dependent coefficients

## 5. Path Forward: Direct Non-Uniform CCD

### 5.1 Formulation

At each node i with left spacing h_- = x_i - x_{i-1} and right spacing
h_+ = x_{i+1} - x_i, Taylor-expand about node i:

    Eq-I:  alpha_L * f'_{i-1} + f'_i + alpha_R * f'_{i+1}
           = a_1/(h) * (f_{i+1} - f_{i-1}) + b_1*h * (f''_{i+1} - f''_{i-1})

    Eq-II: beta_L * f''_{i-1} + f''_i + beta_R * f''_{i+1}
           = a_2/h^2 * (f_{i-1} - 2*f_i + f_{i+1}) + b_2/h * (f'_{i+1} - f'_{i-1})

where h = (h_- + h_+)/2 and the 6 coefficients (alpha_L, alpha_R, a_1, b_1,
beta_2, a_2) are determined by a 6x6 Taylor matching system that depends on
rho = h_+/h_-.

### 5.2 Properties

- **Formal order**: O(h_bar^6) where h_bar is the local average spacing
- **Block-tridiagonal**: 2x2 blocks, same Thomas algorithm, but blocks are
  node-dependent (must be assembled per grid configuration)
- **No metric**: operates directly in physical space; J, dJ/d(xi) not needed
- **Cost**: O(N) solve (same asymptotic), but refactorization at grid rebuilds

### 5.3 Challenges

- Coefficient derivation requires per-node 6x6 system solve
- Boundary stencil needs asymmetric extension
- Condition number grows as rho departs from 1 (manageable for alpha <= 4)

## 6. Conclusion

The xi-space CCD + metric transform approach is fundamentally incompatible with
localized grid refinement. The incompatibility is not in the cross-term formula
but in the resolution of the metric itself: the density transition spans O(1)
cells in xi-space regardless of N, making all metric-dependent computations
non-convergent. The Two-Pass reformulation, while algebraically elegant, fails
for the same reason -- it removes the cross-term from the formula but not from
the data. Direct non-uniform CCD with node-dependent physical-space coefficients
is the necessary and sufficient path forward.

## References

- Chu, P.C. & Fan, C. (1998). A three-point combined compact difference scheme.
  J. Comput. Phys., 140(2), 370-399.
- WIKI-T-037: Grid remap interpolation order limit
- WIKI-T-038: Bandwidth constraint for non-uniform grid rebuild
- WIKI-T-039: xi-space CCD metric limitation (this work)
