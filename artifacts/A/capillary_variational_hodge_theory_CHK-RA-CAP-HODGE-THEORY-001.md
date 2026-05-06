# CHK-RA-CAP-HODGE-THEORY-001 - Generic Variational-Hodge Capillary Theory

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`

## Purpose

Establish a generic theory for capillary pressure-jump/projection coupling.
The theory must not depend on special cases such as "static droplet",
"circle", "ellipse", or "oscillating droplet".  Those are verification
instances only.  The production rule must be a single variational law.

## Continuum Contract

For an incompressible two-phase flow with surface energy

```text
E_sigma(Gamma) = sigma |Gamma|,
```

surface tension is the force covector defined by the shape derivative

```text
<F_sigma, u> = - dE_sigma(Gamma)[u]
```

for every admissible incompressible velocity `u`.  Pressure is a Lagrange
multiplier for incompressibility.  It may absorb gradient components of force,
but it may not erase the projected force that acts on divergence-free velocity.

Static equilibrium is therefore not "a circle" as a code branch.  It is the
condition

```text
dE_sigma(Gamma)[u] = 0
```

for all volume-preserving admissible variations `u`, with body potentials and
contact constraints included when present.  In the simplest closed, no-gravity
case this reduces to constant curvature on each connected component.  The
circle is only one verification example of the generic critical-point rule.

## Discrete Face-Space Contract

Let:

- `u_f` be normal face velocity,
- `D_f` be the face divergence,
- `A_f G_f p` be the pressure-gradient face acceleration,
- `c_f` be the capillary face cochain, in the same face space and units as
  `A_f G_f p`.

The pressure-jump projection step with capillarity is:

```text
D_f A_f G_f p = r_h + D_f c_f,
a_f(p;c) = A_f G_f p - c_f,
u_f^{n+1} = u_f^* - dt a_f(p;c).
```

For zero predictor and zero external forcing, the PPE removes only the
divergent part of `c_f`.  The remaining `a_f` is the discrete Hodge/Leray
component of the capillary force.  It is exactly the component that can change
incompressible kinetic energy.

Thus:

```text
P_h c_f = 0       <=> no capillary acceleration in incompressible space
P_h c_f != 0     <=> capillary release must generate velocity
```

where `P_h` denotes the face-space projection onto the admissible
divergence-free velocity space, with the same mass/coefficient pairing as the
projection operator.

## Range Projection Is Diagnostic, Not a Generic Corrector Replacement

The algebraic range projection solves

```text
D_f A_f G_f pi_h = D_f c_f,
Pi_R c_f = A_f G_f pi_h,
c_f = Pi_R c_f + h_f,
D_f h_f = 0.
```

This decomposition is valuable as a diagnostic: it measures how much of the
capillary cochain is pressure-range versus divergence-free/Hodge.  But the
following theorem is decisive:

```text
If the corrector replaces c_f by Pi_R c_f, then for zero predictor
p = pi_h gives a_f = A_f G_f p - Pi_R c_f = 0.
```

This holds for every interface geometry.  It is not a static-equilibrium test.
It is a dynamic kill switch.  It suppresses the physical capillary release of
any non-equilibrium interface whose force lies partly in the divergence-free
face space.

Therefore blanket replacement

```text
c_f -> Pi_R c_f
```

is not a generic production law.

## Correct Generic Production Law

The production capillary cochain must be constructed from a discrete surface
energy and the same face-velocity transport map used by the interface update:

```text
<c_f, w_f>_f = - delta E_h[psi; w_f]
```

for every admissible face velocity `w_f`.  Equivalently, `c_f` must be the
transport-adjoint or discrete-gradient pullback of `E_h = sigma |Gamma_h|`.

For a time-discrete energy method, use a discrete gradient:

```text
E_h(psi^{n+1}) - E_h(psi^n)
  = <grad_d E_h, psi^{n+1} - psi^n>,
c_f = - T_h(psi)^* grad_d E_h,
```

where `T_h(psi)^*` is the adjoint of the face-flux transport linearization that
maps face velocity to interface change.  Explicit variants may use the same
identity to first order; implicit/semi-implicit variants must preserve it at
the chosen time level.

Then the pressure projection uses the full `c_f`:

```text
D_f A_f G_f p = r_h + D_f c_f,
u_f^{n+1} = u_f^* - dt (A_f G_f p - c_f).
```

The range/Hodge decomposition remains reported:

```text
Pi_R c_f,  h_f = c_f - Pi_R c_f,
```

but it does not replace the force in the corrector.

## Generic Equilibrium Gate

The static gate is not shape-specific.  It is:

```text
||P_h c_f|| / max(||c_f||, eps) <= tolerance
```

for the same admissible velocity space, boundary conditions, density
coefficient, and grid metrics as the production projection.  Passing this gate
means the discrete surface-energy first variation is zero in the incompressible
subspace.  Failing it means either:

1. the geometry is not an equilibrium and must move, or
2. the capillary cochain is not a faithful discrete variational derivative.

The gate may be tested on circles, static droplets, capillary waves,
perturbed circles, bubbles, walls, or multiple components, but the criterion is
identical in all cases.

## Implementation Consequences

Allowed:

- one capillary cochain builder based on discrete surface energy and transport
  adjoints;
- one pressure/corrector path using the full cochain;
- range/Hodge projection as diagnostics and static-equilibrium verification;
- equilibrium tests expressed as variational residuals.

Banned:

- `if static_droplet`, `if circle`, `if oscillating_droplet`, or
  benchmark-name logic;
- deleting the Hodge component because a static circular test dislikes it;
- treating reinitialization as surface-energy relaxation;
- damping, CFL reduction, curvature caps, smoothing, or FD/WENO substitution
  as capillary physics fixes;
- pressure-only fixes that do not satisfy the virtual-work identity.

## Required Verification Gates

1. **Virtual-work gate**: for sampled admissible face velocities `w_f`,
   compare `<c_f,w_f>_f` with `-delta E_h[w_f]`.
2. **Static critical-point gate**: equilibria with constant generalized
   curvature have `||P_h c_f||` at tolerance.
3. **Dynamic release gate**: non-equilibrium perturbations released from rest
   have `||P_h c_f|| > 0` and early kinetic-energy growth
   proportional to `dt^2 ||P_h c_f||^2`.
4. **Projection consistency gate**: PPE residual and velocity divergence are
   small while the Hodge component is preserved when physically nonzero.
5. **Reinitialization separation gate**: changes in deformation caused by
   reinitialization alone are measured separately from physical capillary
   motion.

## Relation to the N=32 Oscillating-Droplet RCA

The N=32 oscillating-droplet zero-drive result follows immediately from the
theorem above.  The range-projected corrector replaced `c_f` by `Pi_R c_f`, so
`a_f=0` by construction for the zero-predictor release.  The result was not a
viscosity, CFL, pressure residual, curvature, or initial-velocity issue.

The next implementation must therefore change the generic capillary cochain
construction and corrector contract.  It must not add a special oscillating
droplet exception.

[SOLID-X] theory/docs only; no solver/config production change; no tested
implementation deleted; no FD/WENO/PPE fallback or alternate numerical route
introduced.
