# CHK-RA-CH14-VARIATIONAL-PRESSURE-COMPLEX-001

## Purpose

This note pushes the selected pressure-adjoint remedy to a stricter production
theory.  The selected direction is:

```text
Make the production FCCD pressure face API expose the variational pressure
reaction G = -M_A^{-1}D_f^T W_p, not an independently chosen face gradient.
```

The goal is not to make the static droplet look quiet by a local adjustment.
The goal is to restore the discrete mechanics theorem: pressure is a constraint
reaction that does no work on admissible incompressible face velocities, and
capillarity is projected in the same kinetic metric.

## Objects and Quotient Spaces

The production theorem must be stated on physical degrees of freedom, not on
storage arrays with duplicated periodic images.

Let:

```text
P_h      pressure scalar space after quotienting periodic image nodes and gauge;
V_h      normal face velocity/acceleration space after quotienting periodic
         face images and applying wall/periodic admissibility;
D        V_h -> P_h, the production face divergence;
W        SPD pressure test metric, normally nodal control volumes on P_h;
alpha_f  positive face inverse-density coefficient, including active
         phase-separated or affine-jump coefficients;
Q_f      positive face measure for the production face space;
M        SPD kinetic face metric, M_f = Q_f / alpha_f on active faces;
G        P_h -> V_h, the production pressure reaction map.
```

For wall boundaries, `V_h` is already the space of admissible normal face
unknowns and `D` includes the retained boundary control-volume rows.  For
periodic boundaries, pressure images are not independent test functions and
face images are not independent trial functions.  Any diagnostic that tests
unrestricted storage arrays is testing a larger, nonphysical complex.

The pressure gauge is separate.  Constants are removed from `P_h`, or a gauge
row is added, but the pressure reaction theorem is imposed on the quotient.

## Variational Pressure Theorem

Given a predicted face velocity `u*`, the incompressible pressure step is the
finite-dimensional constrained minimization

```text
minimize_u  1/2 ||u - u*||_M^2
subject to  D u = 0.
```

The Lagrangian with pressure multiplier `p` is

```text
L(u,p) = 1/2 (u-u*)^T M (u-u*) + p^T W D u.
```

Stationarity with respect to `u` gives

```text
M(u-u*) + D^T W p = 0,
u = u* - M^{-1}D^T W p.
```

Therefore the pressure reaction is uniquely

```text
G p = M^{-1}D^T W p
```

if the projection update is written `u = u* - Gp`, or equivalently

```text
G_signed p = -M^{-1}D^T W p
```

if `G_signed` denotes the force added to `u*`.  The code contract must state
which sign it returns.  The invariant identity is independent of naming:

```text
<Gp, w>_M = <p, D w>_W
```

for the subtractive projection convention, or with both signs flipped for the
additive-force convention.  A production implementation must pick one sign and
make every diagnostic use the same convention.

The corresponding scalar pressure operator is

```text
L = D G = D M^{-1}D^T W
```

up to the same sign convention.  It is self-adjoint in the `W` metric and
positive semidefinite on the pressure quotient:

```text
<p, Lp>_W = ||Gp||_M^2 >= 0.
```

This theorem is stronger than scalar PPE symmetry.  Scalar symmetry constrains
`D G`; it does not determine the face representative `G`.

## Representative Uniqueness

Suppose another pressure face map satisfies the same scalar divergence:

```text
D G_alt = D G,
G_alt = G + Z,
D Z = 0.
```

Then the scalar PPE cannot detect `Z`.  But for an admissible incompressible
velocity `w in ker(D)`,

```text
<G p, w>_M = <p, D w>_W = 0,
<G_alt p, w>_M = <Zp, w>_M.
```

Unless `Z=0` in the kinetic metric, `G_alt` permits pressure to do work on
incompressible motions.  This violates the discrete d'Alembert principle and
breaks the capillary Hodge theorem.  Thus `range(G_alt)` is not the pressure
reaction range merely because `D G_alt` is an acceptable scalar PPE operator.

The RCA measured exactly this case for current FCCD:

```text
D G_FCCD is scalar-symmetric to roundoff,
G_FCCD != M^{-1}D^T W by about 20.9 percent on the physical quotient.
```

## Capillarity and Component Constraints

Let `q` be the pre-reinit transport endpoint, `E_h(q)=sigma S_h(q)` the
discrete surface energy, and `T(q): V_h -> Q_h` the face transport Jacobian
used by the phase field endpoint.  The face Riesz representative of capillary
virtual work is

```text
s = -M^{-1} T(q)^T dE_h(q)^T.
```

For component volumes `V_m(q)`, define

```text
B_m = M^{-1}T(q)^T dV_m(q)^T.
```

The physical capillary release is the `M`-orthogonal projection of `s` onto

```text
K = ker(D) intersection {h | B_m^T M h = 0 for all m}.
```

Equivalently, with

```text
X = [G, B_1, ..., B_k],
h = s - X z,
```

the coefficients `z` solve the normal equations

```text
X^T M X z = X^T M s
```

on the pressure quotient and component-rank quotient.  The pressure block of
these normal equations is exactly `D h = 0`, because

```text
G^T M h = W D h.
```

This identity is the reason the pressure API must expose the variational
representative.  If the production split uses `G_FCCD` with a solenoidal
defect, then `X^T M h = 0` is no longer equivalent to the intended divergence
and component constraints.

The energy theorem then closes:

```text
dE_h[T h] = -<s, h>_M = -||h||_M^2 <= 0
```

because `h` is the `M`-orthogonal projection of `s` onto admissible motions.
This is the discrete statement that surface energy converts into kinetic
energy through the admissible capillary drive, while pressure and component
volume reactions do no admissible work.

## Interface Jumps as Affine Shifts

Affine pressure jumps and closed-interface capillary cochains must be handled
as shifts in the same variational pressure complex:

```text
pressure_face_reaction(p; c) = Gp - c
projection_update            = u* - dt (Gp - c)
```

where `c` may be a Young-Laplace jump cochain, a closed-interface Riesz
cochain, or a component-corrected capillary cochain.  The scalar RHS is then
formed with the same `D`:

```text
D(Gp - c) = D u* / dt
```

up to the solver's sign convention.  It is invalid to solve a scalar equation
with one face map and apply the face correction of another.  That half-fix
would reintroduce a hidden `Z` channel.

For phase-separated coefficients, faces with `alpha_f = 0` are not ordinary
finite kinetic metric entries.  The theory must either remove them from the
active face space or fail close.  Setting `M_f = Q_f/alpha_f` with zero
`alpha_f` is not an SPD metric.  Therefore the active-space definition is part
of the theorem, not a numerical afterthought.

## Existing Scalar PPE Reuse Criterion

Let the existing FCCD scalar operator be

```text
L_old p = D G_old p.
```

The variational scalar operator is

```text
L_var p = D G p = D M^{-1}D^T W p.
```

There are only two valid cases.

Case A:

```text
L_old = L_var
```

on the physical quotient, with the active grid, density, phase-separated, and
affine-jump coefficients.  Then the old scalar solve may be reused, but the
face correction still must be `G p`, not `G_old p`.

Case B:

```text
L_old != L_var.
```

Then both the scalar solve and the face correction must move to the
variational complex.  Solving `L_old p = rhs` and applying `G p` is not a
projection for either operator.

This criterion must be checked by an operator gate before droplet runs.

## High-Order FCCD Interpretation

The variational representative is not a low-order fallback.  Its order is tied
to the chosen divergence and metric complex.

If production chooses a compact fourth-order divergence `D^{(4)}`, the matching
pressure reaction is

```text
G^{(4)} = M^{-1}D^{(4)T}W,
L^{(4)} = D^{(4)}G^{(4)}.
```

If that pair has inadequate pointwise pressure-gradient accuracy, the remedy
is to redesign the compact mimetic pair, not to replace the face reaction by an
independent compact gradient.  The correct high-order target is an SBP/Riesz
pair:

```text
<G^{(4)}p,w>_M = <p,D^{(4)}w>_W
```

plus consistency of `D^{(4)}` and the face transport operators.  Pointwise
gradient order is subordinate to the pressure-work theorem for projection
forces.

## Boundary and Gauge Rules

1. Periodic image nodes and faces are storage conveniences only.  Adjointness
   and operator norms are measured on quotient DOFs.
2. Gauge rows enforce uniqueness of `p`; they are not physical pressure-work
   rows and must not enter the face reaction identity.
3. Wall boundary rows are physical only insofar as the chosen `V_h` and `D`
   include their admissible boundary fluxes.  The transpose defining `G` must
   be taken after that boundary-space choice.
4. If a phase gauge is used for phase-separated PPE, the quotient must be
   compatible with disconnected pressure components and with the active face
   graph.

These rules are fail-close conditions.  If the quotient is ambiguous, the
pressure-adjoint residual has no physical meaning.

## CCD/FCCD/UCCD Consequences

The selected theory gives a single face-complex SSoT:

```text
face velocity space V_h
    -> D for incompressibility and PPE RHS
    -> G = M^{-1}D^TW for pressure reactions
    -> T(q) for phase transport virtual work
    -> UCCD/viscosity consume the corrected face state
```

This is compatible with CCD-family methods because all couplings happen on
face objects.  A non-adjoint FCCD pressure gradient may remain as a diagnostic
or reconstruction primitive, but it cannot be the projection force.  If UCCD
or viscosity require a higher-order reconstructed nodal velocity, that
reconstruction is downstream of the face projection and must not redefine the
pressure range.

## GPU-First Consequences

The variational complex should be implemented as device-local operator
applications:

```text
apply_D(face_components)
apply_G(p) = metric_inverse_faces(transpose_D(weighted_pressure(p)))
apply_L(p) = apply_D(apply_G(p))
```

For the current FVM-like wall rows this is an axis-local stencil.  For periodic
axes it must operate on synchronized physical quotient DOFs.  For compact FCCD
variants it may involve transpose applications of compact line operators, but
it should remain sparse/line-local.  Dense quotient matrices are diagnostic
objects only unless a separate GPU theorem and implementation are provided.

The GPU objective is therefore not "keep the existing fast gradient."  It is
"make the fast path and theorem path the same path."

## Failure Modes Now Ruled Out

The following are not valid theory-preserving remedies:

- pressure damping or viscosity inflation;
- CFL reduction as a capillary-pressure fix;
- curvature smoothing, curvature caps, or benchmark-specific static gates;
- FD/WENO/PPE fallback as production capillarity;
- blanket projection of capillary cochains into the old `range(G_FCCD)`;
- diagonal face metric tuning of `G_FCCD`;
- solving `L_old` while applying `G_var` without proving `L_old=L_var`;
- keeping capillary Hodge on `G_var` while projection uses `G_FCCD`.

Each of these either hides `Z`, changes the physics, or leaves multiple
incompatible pressure ranges in the code.

## Theoretical Implementation Contract

The production pressure API should satisfy the following contract.

```text
pressure_fluxes(p, rho, ..., capillary_shift=None)
    returns Gp - capillary_shift

where G is the Riesz-adjoint pressure reaction for the active D, M, W complex.
```

If raw FCCD face gradients are still needed, they should be exposed under a
name that cannot be mistaken for a projection force, for example
`raw_compact_pressure_gradient_faces`.  The public projection path, capillary
Hodge diagnostics, component saddle, and pressure correction history must all
use the variational reaction.

The scalar PPE solver must expose or certify:

```text
apply(p) = D(pressure_fluxes(p, rho, zero_shift))
```

on the physical quotient, including active coefficient and boundary rules.  If
this equality cannot be certified, the solver is not paired with the pressure
API.

## Validation Gates

The next implementation must pass these gates before physical interpretation.

```text
G0. Quotient construction:
    pressure images, face images, gauge rows, and active phase components are
    explicit.

G1. Green identity:
    random and deterministic probes satisfy
    <Gp,w>_M - <p,Dw>_W = 0
    to roundoff on CPU and GPU.

G2. Scalar identity:
    PPE apply(p) equals D(Gp) to roundoff for active coefficients.

G3. Positivity:
    <p,Lp>_W = ||Gp||_M^2 >= 0 on the pressure quotient.

G4. Capillary saddle:
    h = projection_K(s) satisfies D h = 0,
    B^T M h = 0, and <Gp,h>_M = 0.

G5. Static constrained criticality:
    if dE_h is in span(D^TW, dV_m), then h = 0 without shape classifiers.

G6. Dynamic release:
    arbitrary resolved noncritical modes give h != 0 and
    dE_h[T h] = -||h||_M^2.

G7. Reinit separation:
    all work identities use the pre-reinit transport endpoint; reinit changes
    are ledgered separately.
```

Only after these gates should N32/T1 or T10 droplet pictures be used as
physics evidence.

## Verdict

The pressure-adjoint residual is solved at the theory level only when the
production pressure complex is variational:

```text
(D, M, W) determines G;
G determines L = D G;
capillarity and component reactions are projected against range(G) in M;
the same G is used by projection, diagnostics, and CCD/FCCD/UCCD coupling.
```

This is the rigorous form of the selected direction.  The standalone
`G_var` formula is the theorem.  The FCCD pressure API redesign is the
production contract that prevents the theorem from becoming a capillary-only
side calculation.
