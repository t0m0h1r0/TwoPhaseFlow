# CHK-RA-CAP-STATIC-DYNAMIC-GATE-001 - Static/Dynamic Capillary Gate Verification

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`

## Question

Verify, from physics and mathematics, that the same capillary theory can:

1. prevent a genuinely oscillating/deformed droplet released from rest from
   being frozen by the pressure projection; and
2. keep a genuinely static Young-Laplace droplet in equilibrium.

The verification must not introduce benchmark-name logic such as
`if static_droplet` or `if oscillating_droplet`.

## Verdict

The theory gives a clean generic separation:

```text
static equilibrium        <=> P_h c_h = 0
dynamic capillary release <=> P_h c_h != 0
```

where `c_h` is the physical surface-energy force/acceleration cochain and
`P_h` is the pressure-projection Hodge/Leray projection in the same weighted
face space as the PPE and velocity corrector.

Therefore:

- a circular, closed, zero-gravity droplet must remain at rest because its
  Young-Laplace force is a pressure-range/Lagrange-multiplier force;
- a non-circular area-preserving perturbation, such as the ch14 ellipse, must
  have a nonzero incompressible capillary component and must begin moving when
  released from rest;
- replacing `c_h` by its pressure-range projection in the production corrector
  is not a valid equilibrium test, because it also forces the non-circular
  release to rest.

The existing ch14 production evidence is consistent with this warning:
`range_projected` keeps static droplets quiet, but it also keeps the N32
oscillating droplet at machine-zero velocity.  That is not a proof that the
static droplet is variationally balanced; it is proof that the applied Hodge
component has been deleted.  The next implementation must construct a
variational cochain whose static residual is zero while its deformed-interface
residual remains nonzero.

## Continuum Theory

For a closed incompressible two-phase system with no gravity and constant
surface tension,

```text
E_sigma(Gamma) = sigma |Gamma|.
```

Surface tension is the shape-derivative force covector:

```text
<F_sigma, u> = - dE_sigma[Gamma][u].
```

Pressure is the Lagrange multiplier enforcing incompressibility.  Hence
pressure may absorb forces that do no work on all volume-preserving admissible
velocities, but it may not absorb a nonzero variation of surface energy along
such velocities.

For a smooth closed planar interface, the first variation is

```text
dL[u_n] = - integral_Gamma kappa u_n ds,
dA[u_n] =   integral_Gamma u_n ds.
```

The constrained static condition is therefore

```text
d(L - lambda A)[u_n] = 0 for every u_n
<=> kappa = lambda = constant on each constrained component.
```

For an embedded closed curve in the plane, constant curvature implies a
circle.  Thus the circular droplet is the generic constrained critical point;
it is not a special code branch.

For a non-circular droplet, curvature is not constant.  Choosing
`u_n` proportional to `kappa - mean(kappa)` with the area-preserving mean
removed gives

```text
dL[u_n] = - integral_Gamma (kappa - mean(kappa))^2 ds < 0
```

up to sign convention.  Therefore the interface is not a critical point, and
there exists an admissible incompressible velocity direction with nonzero
capillary work.  A released droplet must accelerate.

At the exact initial instant, `u=0`, so the instantaneous power
`<F_sigma,u>` is zero.  This does not mean static equilibrium.  The decisive
quantity is acceleration:

```text
u_t(0) = P F_sigma / rho.
```

If `P F_sigma != 0`, then for a small step

```text
K(dt) = 1/2 dt^2 ||P F_sigma/rho||_M^2 + O(dt^3),
```

so kinetic energy grows quadratically from rest.

## Continuum Numerical Sanity Checks

Area-normalized radial modes

```text
r(theta) = s(eps) (1 + eps cos(n theta))
```

were checked by direct quadrature.  At the circle, all non-volume modes have
zero first variation, but positive second variation:

```text
fixed-area radial modes
n=2 dL/deps@0=+0.000e+00 d2L/deps2@0=9.424778e+00 dL/deps@0.1=9.262817e-01
n=3 dL/deps@0=+0.000e+00 d2L/deps2@0=2.513274e+01 dL/deps@0.1=2.424381e+00
n=4 dL/deps@0=+0.000e+00 d2L/deps2@0=4.712389e+01 dL/deps@0.1=4.437533e+00
n=5 dL/deps@0=+0.000e+00 d2L/deps2@0=7.539822e+01 dL/deps@0.1=6.897320e+00
```

Interpretation:

- the circle is a stationary constrained critical point;
- finite-amplitude perturbations are not stationary;
- the force is restoring because decreasing the perturbation reduces perimeter.

For the ch14 ellipse with `a=0.275`, `b=0.225`, and fixed area
`R=sqrt(ab)=0.2487468593`, write `a=R exp(s)`, `b=R exp(-s)`.
The benchmark corresponds to `s=0.1003353477`.

```text
area-preserving ellipse
dL/ds@0       = +0.000e+00
d2L/ds2@0     = 2.344384e+00
dL/ds@ch14    = 2.353246e-01
kappa_min/max = 2.975207e+00 / 5.432099e+00
kappa_span    = 2.456892e+00
```

The ellipse is therefore not a static Young-Laplace equilibrium.  It must have
a nonzero capillary acceleration when released from rest.

## Discrete Face-Space Theorem

Let face velocities use the kinetic/mass inner product `M_f`.  Let
`D_f u_f=0` define the admissible incompressible face space, and let the
pressure acceleration range be

```text
range(A_f G_f) = range(M_f^{-1} D_f^T)
```

with the actual PPE/corrector coefficients and adjoints.

For a capillary acceleration cochain `c_f`, the pressure projection solves

```text
D_f A_f G_f p = D_f c_f
```

and the physical post-projection capillary acceleration is

```text
h_f = c_f - A_f G_f p.
```

Then:

```text
D_f h_f = 0,
h_f = P_h c_f.
```

Thus:

- if `c_f` is purely pressure-range, then `h_f=0` and the system stays static;
- if `c_f` has a nonzero admissible/Hodge part, then `h_f!=0` and the released
  system starts moving;
- if production replaces `c_f` by `Pi_R c_f`, then `h_f` is forced to zero for
  every geometry, so the dynamic release is killed by algebra.

Weighted finite-dimensional checks confirmed this:

```text
static_range
  ||D h||_inf                  1.075e-14
  ||h||_M                      4.867792e-15
  K_growth_coeff=0.5||h||_M^2  1.184770e-29
  replaced_corrector_accel_norm 0

dynamic_range_plus_hodge
  ||D h||_inf                  7.522e-15
  ||h||_M                      3.570512e+00
  K_growth_coeff=0.5||h||_M^2  6.374276e+00
  replaced_corrector_accel_norm 0

pure_hodge
  ||D h||_inf                  4.441e-16
  ||h||_M                      3.570512e+00
  K_growth_coeff=0.5||h||_M^2  6.374276e+00
  replaced_corrector_accel_norm 0
```

This is the central separation test.  The correct Hodge gate accepts static
range forces and releases dynamic Hodge forces.  The replaced corrector cannot
distinguish them.

## Existing ch14 Evidence Under This Theory

Existing cached/recorded ch14 runs align with the theorem's warning.

For the N32/T1 oscillating droplet:

```text
kinetic_energy first/final/max 1.847565e-38 / 2.877473e-37 / 3.179823e-37
signed_deformation first/final 7.617534e-02 / 4.446894e-02
velocity Linf                 3.571025e-19
```

This is a deformed finite-amplitude droplet with theoretical nonzero restoring
force, yet the computed velocity remains machine-zero.  The one-step RCA found
the algebraic reason:

```text
range_projected:
  capillary_hodge_residual 1.813600e-03
  capillary_face_linf      0
  u_linf, v_linf           0, 0

none:
  capillary_hodge_residual 1.813600e-03
  capillary_face_linf      1.813600e-03
  u_linf, v_linf           1.235913e-05, 9.806495e-06
```

For the N32/T4 static droplet:

```text
kinetic_energy first/final/max 1.979181e-38 / 1.948632e-35 / 1.948632e-35
deformation final/max         0 / 0
volume drift final/max        1.776544e-15 / 1.776544e-15
```

This is operationally static under the current `range_projected` closure.
However earlier static diagnostics showed that the raw capillary cochain still
had a nonzero Hodge residual of about `1.1e-3` before the closure deleted it:

```text
capillary_jump_linf_max              2.780542e-02
capillary_range_projection_linf_max  2.784585e-02
capillary_hodge_residual_max         1.139486e-03
capillary_face_linf_max              3.816392e-17
```

Therefore the static run demonstrates that the applied acceleration was
zeroed.  It does not by itself prove that the raw capillary cochain is a
faithful discrete Young-Laplace equilibrium cochain.

## Required Generic Gate

The next capillary route must pass both gates using the same code path:

### Gate S - Static Young-Laplace Equilibrium

For a circle, or more generally any constrained constant-generalized-curvature
state:

```text
||P_h c_h||_M / max(||c_h||_M, eps) <= tol_static
```

with reinitialization/remap disabled or explicitly included in the transport
map.  Passing by replacing `c_h` with `Pi_R c_h` is invalid; the gate must be
computed on the physical variational cochain before production deletion.

### Gate D - Dynamic Release From Rest

For a non-equilibrium perturbation:

```text
||P_h c_h||_M / max(||c_h||_M, eps) >= tol_release
```

and the first-step kinetic energy must satisfy

```text
K^{1} = 1/2 dt^2 ||P_h c_h||_M^2 + higher-order/viscous terms.
```

The ch14 ellipse must fail the static gate and pass the dynamic-release gate.

### Gate R - Representation Separation

Ridge-Eikonal reinitialization, grid remap, and profile repair must not be
allowed to fake capillary relaxation.  For the oscillating droplet, the
existing N32 controls already showed that every-step reinit changes signed
deformation even when velocity is zero.  Thus dynamic verification must report
both:

```text
deformation change from physical face velocity
deformation change from representation repair
```

## What This Rules Out

The following fixes are theoretically invalid:

- benchmark-name branches for static vs oscillating droplets;
- blanket `c_f -> Pi_R c_f` production replacement;
- accepting zero velocity as a static proof when the cochain was deleted;
- accepting nonzero motion from `capillary_range_projection:none` before the
  raw cochain passes the virtual-work identity;
- reinitialization, smoothing, curvature caps, damping, or CFL reduction as a
  substitute for the static/dynamic variational gates.

## Conclusion

The physical/mathematical theory is internally consistent:

- static Young-Laplace droplets remain in equilibrium because their capillary
  force is pressure-range under the constrained variational principle;
- deformed oscillating droplets do not remain static because nonconstant
  curvature leaves a nonzero incompressible capillary component;
- the current `range_projected` production closure can satisfy the first
  behavior only by also destroying the second behavior.

The implementation target is therefore not "turn range projection off" and not
"keep range projection on".  The target is:

```text
construct c_h as a weighted transport-adjoint/discrete-gradient surface-energy
cochain; prove it has P_h c_h ~= 0 on constrained static equilibria; prove it
has P_h c_h != 0 on non-equilibrium perturbations; then apply the full cochain
in the pressure/corrector path.
```

[SOLID-X] theory/verification/docs only; no solver/config production change;
no tested implementation deleted; no FD/WENO/PPE fallback or alternate
numerical route introduced.
