# CHK-RA-CH14-CONS-ENDPOINT-THEORY-001

## Question

After `CHK-RA-CH14-ENDPOINT-POLICY-001`, the selected production direction for
the current LevelSet/CLS solver is the conservative face-psi transport endpoint
VJP.  The open theoretical question is what exact discrete law this implies.

The answer must be independent of shape names such as circle or ellipse.  It
must define static and dynamic states by finite-dimensional variational
criticality, use the same pressure/Hodge complex as the corrector, and keep
reinitialization/profile projection outside capillary work.

## State and Endpoint

The current solver state is the nodal level-set carrier

```text
q = psi on grid nodes.
```

For one physical transport leg, before reinitialization, the implemented
conservative endpoint differential is

```text
T_f(q) u_f = -D_f( P_f q * u_f ).
```

Here `u_f` is the normal face velocity, `P_f` is the FCCD face interpolation
used by the transport code, and `D_f` is the FCCD face divergence used by the
projection complex.  Therefore the force law must be adjoint to this `T_f(q)`.
Using a trace endpoint with a different map `C_K` is mathematically valid only
for a trace-primary transport update; it is not the VJP of the present solver.

## Surface Energy and Component Volumes

On a regular fixed stratum, define discrete functionals of the same state:

```text
S_h(q)      = P1 marching-squares interface length,
V_m,h(q)   = signed area/volume of connected component m,
E_h(q)      = sigma S_h(q).
```

The finite-grid static equation is not "is this a circle?".  It is

```text
d_q E_h(q) = sum_m lambda_m d_q V_m,h(q).
```

If this equation holds, every volume-preserving admissible virtual velocity has
zero first-order surface-energy release.  If it fails, the Hodge part of the
capillary cochain is physical even when the visual shape is not recognizable as
an ellipse or a standard Fourier mode.

## Transport-Adjoint Riesz Cochains

The metric for face velocities is the same face mass metric used in the
projection/corrector:

```text
<a_f, u_f>_M = sum_f M_f a_f u_f.
```

The surface acceleration cochain `s` is the Riesz representative of negative
surface-energy virtual work:

```text
<s, u>_M = - d_q E_h(q)[ T_f(q)u ],
s        = - M_f^{-1} T_f(q)^T d_q E_h(q)^T.
```

Component-volume reaction directions are

```text
<B_m, u>_M = d_q V_m,h(q)[ T_f(q)u ],
B_m        =  M_f^{-1} T_f(q)^T d_q V_m,h(q)^T.
```

The signs are fixed by release from rest: if `u` is aligned with `s`, then

```text
d_q E_h(q)[ T_f(q)u ] = - <s,u>_M < 0.
```

Thus the force performs positive kinetic-energy work by decreasing surface
energy.  A sign convention in the corrector may store the same object as a
pressure-jump component, but the virtual-work identity above is the invariant.

## Pressure and Component Hodge Decomposition

Let the pressure range in the same face complex be

```text
R = range(M_f^{-1} D_f^T).
```

Let `B=[B_1,...,B_M]` be the component-volume reaction matrix.  The augmented
reaction space is

```text
X = [ R, B ].
```

The admissible capillary drive is the `M_f`-orthogonal complement of the
pressure and component reactions:

```text
h = (I - Pi_X^M) s,
Pi_X^M s = X (X^T M_f X)^+ X^T M_f s.
```

This is a reaction removal, not force deletion.  The full conservative surface
cochain `s` is first constructed from virtual work; only the pressure gauge and
component-volume Lagrange multipliers are projected out.  Replacing `s` by
`Pi_R s` in the production corrector is forbidden because it deliberately
removes `h`, including noncritical capillary modes.

Static and dynamic gates are therefore:

```text
static discrete equilibrium:  ||h||_M ~= 0 for a q satisfying the
                              finite-dimensional criticality equation;
dynamic noncritical mode:     ||h||_M above the static consistency floor.
```

The test object may be a constructed critical stratum, a perturbed stratum, or
a manufactured covector.  It is never a shape-name branch.

## Corrector Coupling

The pressure solve sees the capillary cochain through the same divergence:

```text
D_f( u_f^* + dt s - dt M_f^{-1}D_f^T p - dt B lambda ) = 0.
```

Equivalently, the Schur/Hodge solve determines only the pressure and component
reaction part.  The corrected physical face acceleration is `h`.  The
production corrector must therefore receive the full constrained cochain in the
same sign convention as `pressure_fluxes(..., capillary_jump_components=...)`;
diagnostic range projections may report `Pi_X^M s`, but must not replace the
capillary force by it.

This keeps the old zero-drive theorem visible:

```text
if production uses s_prod = Pi_R s,
then h_prod = s_prod - Pi_R s_prod = 0.
```

That algebra explains why the previous `range_projected` oscillating droplet
had `KE ~ 1e-37` despite a nonzero capillary jump.

## Reinitialization and Profile Gauge

The work theorem covers only

```text
q^n -> q_T = q^n + dt T_f(q^n) u_f
```

before reinitialization.  The later map

```text
q_T -> q^{n+1}
```

is a profile/reinitialization/mass-closure projection.  Its changes in
`S_h`, `V_h`, phase, or deformation must be ledgered as projection work or
profile-control defect, not as capillary work.  Any experiment that reads
deformation after reinitialization as capillary oscillation is mixing two
arrows.

Because the present endpoint is face-psi transport, the theorem is also profile
dependent: changing the level-set gauge changes `P_f q` and therefore
`T_f(q)`.  This is not an implementation loophole.  It means:

1. the current solver can be made self-adjoint only for its own `psi` endpoint,
2. profile sensitivity must be reported fail-close,
3. if gauge invariance is required as the primary physics contract, the solver
   must be redesigned around a trace-primary state and a CCD-family trace map.

## CCD/FCCD/UCCD Compatibility

The conservative endpoint is compatible with the active discretization stack:

```text
P_f      = FCCD face interpolation of psi,
D_f      = FCCD face divergence,
R        = same pressure/corrector face range,
M_f      = same kinetic face mass pairing,
u_f      = projected face velocity passed to UCCD6 momentum,
CCD      = viscosity sees the corrected velocity, not a separate capillary law.
```

Therefore no new off-complex trace-to-face reconstruction is introduced.  The
trace-vertex route remains a future option only if its map becomes a compact or
mimetic CCD-family trace map and the interface state itself is advanced by that
endpoint.

## Required Gates Before Production Promotion

1. Fixed-stratum gate: reject virtual-work checks that cross a topology/stratum
   boundary.
2. Surface Riesz gate: verify
   `d_q E_h[T_f u] + <s,u>_M = roundoff` for random and structured `u_f`.
3. Volume Riesz gate: verify
   `d_q V_m,h[T_f u] - <B_m,u>_M = roundoff`.
4. Manufactured pressure-range gate: for `c=M_f^{-1}D_f^T p`, recover
   `h=0`, `D_f h=0`, and `Pi_R c=c`.
5. Component-reaction gate: after augmenting by `B`, verify
   `X^T M_f h=0` and `D_f h=0`.
6. Static criticality gate: static references must be finite-grid constrained
   critical states of the selected `S_h,V_h,T_f,M_f`, or explicitly reported as
   convergence probes.
7. Dynamic completeness gate: resolved noncritical perturbations, including
   non-elliptic modes, must produce nonzero `h`.
8. Corrector sign-power gate: release from rest must convert decreasing
   surface energy into positive kinetic work.
9. Reinit ledger gate: store and analyze `q^n`, `q_T`, and `q^{n+1}`
   separately.
10. Profile sensitivity gate: changes in SDF/gauge/profile must be quantified;
    failure is fail-close, not silent fallback.

## Consequence

The remaining nonzero Hodge norm is not a request for damping, smoothing,
curvature caps, CFL tuning, or another range projection.  The problem is solved
only when the production capillary cochain is the Riesz representative of
surface-energy virtual work for the same pre-reinit endpoint that transports
the solver state, and when static tests use discrete constrained criticality
instead of shape names.

[SOLID-X] Theory artifact only.  No production solver/config/result behavior is
changed, no tested implementation is deleted, and no FD/WENO/PPE fallback,
damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket
projection, or QP-as-physics route is introduced.
