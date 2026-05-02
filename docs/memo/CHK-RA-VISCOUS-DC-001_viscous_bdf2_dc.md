# CHK-RA-VISCOUS-DC-001: implicit-BDF2 viscous Helmholtz via defect correction

## Question

Can the implicit-BDF2 viscous solve

```math
A_H u^* = b,\qquad A_H = I - \tau L_{\nu,H},\quad \tau=\gamma\Delta t
```

be solved by defect correction (DC), rather than by GMRES, without losing the
BDF2 time accuracy or the CCD-family spatial accuracy?

## Verdict

Yes, with one important distinction from the PPE case:

- PPE DC can use a low-order Poisson operator as `L_L`.
- Viscous-BDF2 DC must use a low-order Helmholtz correction operator
  `A_L = I - τ L_{\nu,L}` that shares the same `μ`, `ρ`, boundary topology, and
  interface-band closure as the high operator.

Using a constant-density Poisson surrogate is not the safe analogue for
viscosity.  It loses the mass-weighted elliptic structure that makes
`A_H` close to `A_L`.

## Formulation

For each implicit viscous substep define

```math
A_H u = u - \tau L_{\nu,H}(u),
\qquad
L_{\nu,H} = \rho^{-1}\nabla\cdot[\mu(\nabla u+\nabla u^T)]_H/Re .
```

The DC iteration is

```math
r^{(m)} = b - A_H u^{(m)},
\qquad
A_L \delta u^{(m+1)} = r^{(m)},
\qquad
u^{(m+1)} = u^{(m)} + \omega\delta u^{(m+1)} .
```

The low operator is

```math
A_L = I-\tau L_{\nu,L},
```

where `L_{\nu,L}` is a second-order, diagonally split stress-diffusion operator:

```math
[L_{\nu,L} u_\alpha]_i =
{1\over Re\,\rho_i}
\sum_\beta c_{\alpha\beta}\,
\partial_\beta\!\left(\mu\,\partial_\beta u_\alpha\right)_i,
\qquad
c_{\alpha\beta} =
\begin{cases}
2, & \alpha=\beta,\\
1, & \alpha\ne\beta.
\end{cases}
```

This keeps the dominant symmetric positive viscous stiffness in `A_L`, while
leaving off-diagonal cross-stress coupling and high-order CCD/normal-tangent
details in the high residual `r^{(m)}`.

## Why this preserves accuracy

The fixed point of the iteration is still the high-order equation:

```math
r^{(m)}=0 \quad\Longleftrightarrow\quad A_H u^{(m)}=b .
```

Therefore the low-order operator affects only the convergence path, not the
target equation.  With a direct or tightly solved `A_L`, the remaining algebraic
error is controlled by the high residual tolerance.  The BDF2 truncation error
is unchanged because `τ=2Δt/3` and the same BDF2 right-hand side are used.

## Convergence condition

The linear DC error propagator is

```math
e^{(m+1)} = \left(I-\omega A_L^{-1}A_H\right)e^{(m)} .
```

The useful regime is therefore

```math
\rho\!\left(I-\omega A_L^{-1}A_H\right) < 1 .
```

For viscous Helmholtz this is more favorable than PPE in one respect:
the identity term in `A_H = I - τL_{\nu,H}` damps the low-frequency nullspace
problem that appears in Poisson systems.  The risky cases are large `τ`,
very sharp `μ/ρ` jumps, and interface bands where the high operator switches
from bulk CCD Laplacian to normal-tangent stress closure.  These are exactly
the cases where `A_L` must share `μ`, `ρ`, BCs, and the same interface-band
mask rather than using a constant-coefficient surrogate.

## Implementation design

1. Keep the existing GMRES path as an explicit YAML-selectable solver.
2. Add a `ViscousHelmholtzDCSolver` that owns only the algebraic solve.
3. Evaluate the high residual with the existing `ViscousTerm._evaluate`.
4. Build one sparse low-order scalar Helmholtz matrix per velocity component.
5. Factor each `A_L` once per viscous solve and reuse it for all DC corrections.
6. Enforce periodic image rows as quotient constraints in the low solve.
7. Expose residual history for validation and performance comparison.

YAML selection:

```yaml
viscosity:
  spatial: ccd
  time_integrator: implicit_bdf2
  solver:
    kind: defect_correction
    tolerance: 1.0e-8
    max_iterations: 80
    restart: 40
    corrections:
      max_iterations: 3
      relaxation: 0.8
```

GMRES remains available as the explicit comparison path:

```yaml
viscosity:
  spatial: ccd
  time_integrator: implicit_bdf2
  solver:
    kind: gmres
    tolerance: 1.0e-8
    max_iterations: 80
    restart: 40
```

## SOLID audit

[SOLID-X] No violation found in the design.  The viscous physics remains owned
by `ViscousTerm`; the new solver owns only the Helmholtz algebra.  The existing
GMRES implementation is retained as an explicit selectable solver, so no tested
code is deleted.
