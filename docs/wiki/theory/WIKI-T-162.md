---
ref_id: WIKI-T-162
title: "Closed-Interface Capillary Discretization Policy"
domain: theory
status: ACTIVE
tags: [capillary, discrete_variational, hodge_projection, pressure_jump, closed_interface, implementation_policy]
sources:
  - path: docs/memo/short_paper/SP-AI_closed_interface_capillary_discretization_policy.md
  - path: artifacts/A/capillary_variational_rigor_CHK-RA-CH14-CAP-VARIATIONAL-RIGOR-001.md
  - path: artifacts/A/capillary_variational_theory_closure_CHK-RA-CH14-CAP-VARIATIONAL-THEORY-001.md
  - path: artifacts/A/capillary_remedy_candidates_CHK-RA-CH14-CAP-REMEDY-001.md
  - path: artifacts/A/capillary_closed_interface_cochain_rca_CHK-RA-CH14-CAP-VOL-001.md
  - path: artifacts/A/capillary_virtual_work_gate_rca_CHK-RA-CH14-CAP-VW-001.md
  - path: artifacts/A/ch14_trace_vertex_transport_theory_CHK-RA-CH14-TRACE-VJP-THEORY-001.md
  - path: artifacts/A/ch14_trace_vertex_impl_ux_CHK-RA-CH14-TRACE-IMPL-UX-001.md
  - path: docs/02_ACTIVE_LEDGER.md
depends_on:
  - "[[WIKI-T-155]]"
  - "[[WIKI-T-156]]"
  - "[[WIKI-T-157]]"
  - "[[WIKI-T-159]]"
  - "[[WIKI-T-160]]"
  - "[[WIKI-T-161]]"
  - "[[WIKI-X-041]]"
---

# Closed-Interface Capillary Discretization Policy

## Claim

The accepted closed-interface capillary discretization is not a curvature
formula, range-projection option, or benchmark branch.  It is the
finite-dimensional weighted variational construction:

```text
s      = -M_f^{-1} C_K^T d_z(sigma S_h)^T
B      =  M_f^{-1} C_K^T [d_z V_1 ... d_z V_M]^T
K      = ker D intersection ker(B^T M_f)
R_aug  = K^{perp_M} = range(A G) + range(B)
Pi_aug = M_f-orthogonal projection onto R_aug
h      = s - Pi_aug s
```

`h` is the physical incompressible capillary drive, up to the code sign
convention.  The pressure reaction is `Pi_aug s`.

## Discretization Policy

Start from a fixed-topology trace stratum:

```text
component labels,
crossing edges,
cut points,
polygon adjacency,
orientation,
stratum id.
```

Define the geometry on that stratum:

```text
S_h(q)    = trace length/area,
V_m,h(q) = component volume/area.
```

Differentiate those exact discrete functionals, then pull them back to faces
through the pre-reinit transport Jacobian:

```text
T w = trace displacement induced by face velocity w.
```

Curvature samples are admissible only if they are proven equal to this Riesz
pullback in the production face metric.

## Projection Rule

Let:

```text
R = A G,
X = [R B].
```

The augmented pressure/component reaction must be the weighted normal
projection:

```text
X^T M_f X z = X^T M_f s.
```

Solving only:

```text
D(Rp + Bmu) = D s
```

is not enough unless the missing component orthogonality is proven redundant.
The required side condition is:

```text
B^T M_f (Rp + Bmu - s) = 0.
```

## Solver-Oriented Schur Form

Using the existing PPE solve:

```text
L = D R,
C = D B,
r = D s.
```

For component coefficient `mu`:

```text
p(mu) = L^+ (r - C mu),
q(mu) = R p(mu) + B mu - s.
```

The small component system is:

```text
S_B mu = y_B,
S_B = B^T M_f [B - R L^+ C],
y_B = B^T M_f [s - R L^+ r].
```

Then:

```text
h = s - R p - B mu.
```

This is the normal equation reduced to the component subspace, not a fallback.

## Reinit Rule

The theorem applies only to the physical transport arrow:

```text
q^n -> q_T.
```

The reinit arrow:

```text
q_T -> q^{n+1}
```

must report trace, surface-energy, volume, and topology-stratum changes
separately.  Reinit changes are not reversible capillary work.

## Required Gates

Before production use:

```text
1. Riesz pullback:
   <s,w>_M + d(sigma S_h)[T w] = 0
   <b_m,w>_M - dV_m[T w] = 0.

2. SBP:
   <A G p,w>_M + <p,Dw>_C = boundary(p,w).

3. Component range:
   ||H_R b_m||_M / ||b_m||_M is measured for every component.

4. Projection equivalence:
   implemented residual equals s - X(X^T M_f X)^+X^T M_f s.

5. Fixed-stratum derivatives:
   dS_h and dV_m pass centered finite-difference sweeps.

6. Noncritical completeness:
   arbitrary resolved admissible modes with nonzero first variation give h != 0.

7. Reinit ledger:
   S_h and V_m are split between q^n->q_T and q_T->q^{n+1}.
```

## Negative Knowledge

Do not use as production fixes:

```text
blanket c -> Pi_R c,
capillary_range_projection:none without Riesz proof,
curvature mean/null-mode calibration without variational equivalence,
component DOF in diagnostics only,
divergence-only augmented solve without B^T M_f orthogonality,
damping/CFL/caps/smoothing,
FD/WENO/PPE fallback,
benchmark-name branching.
```

## Component-Augmented Implementation Slice

The first implemented production candidate is the one-component version of the
augmented Hodge theorem.  It does not identify a shape as circular or
elliptical.  It constructs the component reaction directly in the same
face-cochain complex as the pressure jump:

```text
c      = current capillary jump cochain
b      = unit constant component pressure-jump cochain
h_c    = c - Pi_R c
h_b    = b - Pi_R b
beta   = <h_c,h_b>_M / <h_b,h_b>_M
c_aug  = c - beta h_b
```

This is algebraically the projection onto `range(A G)+span(b)` because the
range part of `b` is already in `range(A G)` and only `h_b` expands the
pressure-range complement.  Consequences:

```text
static constant component reaction: h_c parallel h_b, so c_aug has no Hodge drive;
resolved nonconstant mode: only the unit reaction component is removed;
range_projected control: c -> Pi_R c remains a deletion of all Hodge drive.
```

The runtime mode is `capillary_range_projection: component_hodge_augmented`.
It uses the same `D_f,A_f,G_f`, affine-jump coefficient, pressure history, and
corrector face space as the production pressure stage.  It is still a first
slice, not the final trace/Riesz construction, because the raw `c` must still
be replaced by or verified against the full trace-vertex pullback
`s=-M_f^{-1}C_K^Td_z(sigma S_h)^T` on a fixed trace stratum.

## N32 T1 Validation Note

Remote-first checks on the ch14 stack used `N=32,T=1`, debug diagnostics, and
0.2-time snapshot figures.

| Case | Final KE | Max snapshot velocity Linf | Max corrected Hodge weighted L2 | Volume drift max | Reading |
|---|---:|---:|---:|---:|---|
| static droplet | `5.284015e-09` | `1.833331e-05` | `2.814614e-04` | `1.903440e-15` | bounded but not roundoff static |
| oscillating droplet | `3.643971e-04` | `9.417805e-03` | `4.477470e-02` | `2.428289e-15` | capillary drive restored |

The old `range_projected` production path produced essentially zero velocity
on the oscillating droplet because it replaced `c` by `Pi_R c`.  The new
one-component augmented mode restores nonzero Hodge drive while preserving
volume and PPE convergence.  The static residual is a remaining theorem
obligation, not a tuning target: it says the current scalar face-implicit
curvature cochain is still not the full transport-adjoint surface-energy
Riesz representative.

## Long Validation Note

The N32/T10 and N32/T20 validation separates three questions:

```text
1. Does the old zero-drive failure remain?          no
2. Is the static component reaction fully silent?  not yet at theorem level
3. Does the dynamic phase match Rayleigh-Lamb?     not yet
```

For the static droplet, `N=16,32,64` at `T=1` gave:

| N | final KE | max KE | max snapshot speed | max corrected Hodge weighted L2 | max volume drift |
|---:|---:|---:|---:|---:|---:|
| 16 | `1.490637e-07` | `1.490637e-07` | `9.070593e-05` | `8.428385e-04` | `1.223563e-15` |
| 32 | `5.284015e-09` | `5.284015e-09` | `2.492200e-05` | `2.814614e-04` | `1.903440e-15` |
| 64 | `1.138320e-09` | `2.542873e-09` | `1.941430e-05` | `5.893873e-04` | `3.159875e-15` |

The kinetic leakage improves strongly, but the corrected Hodge residual is
not monotone in `N`.  This means the current component-augmented scalar
cochain is a useful first slice, not a proof that the force is exactly
`T_h^* dS_h`.

For the oscillating droplet, reinit changes the physics-level judgement.  With
reinit every step at `N=32,T=10`, the first signed-deformation zero crossing
is `7.578596`, earlier than the Rayleigh-Lamb reference `9.381529`, and the
max corrected Hodge weighted L2 reaches `9.018738e-02`.  With reinit disabled,
there is no zero crossing by `T=10`; by `T=20`, the first zero crossing is
`13.393564`, later than the same reference, and the final signed deformation
is `-2.228711e-02` while the reference is `-7.454746e-02`.

Therefore the visually coherent pressure/velocity snapshots are not enough to
accept the method as final.  The old algebraic freeze is fixed, but the
remaining physical error is phase/amplitude fidelity and reinit work
contamination.  The next accepted route remains the fixed-stratum
transport-adjoint Riesz cochain:

```text
s = -M_f^{-1} C_K^T d_z(sigma S_h)^T
B =  M_f^{-1} C_K^T [d_z V_m]^T
```

and a stored `q^n -> q_T -> q^{n+1}` ledger that separates capillary transport
from reinitialization.

## Endpoint Ledger Implementation Slice

The first diagnostic implementation of the split ledger stores the endpoint
fields at snapshot steps:

```text
fields/psi_before_transport
fields/psi_after_transport_before_reinit
fields/psi_after_reinit
```

The same fields are preserved in checkpoint snapshots and reconstructed by the
plot-only runner.  This is not a force change.  It simply makes the state split
observable so later checks can measure

```text
q^n -> q_T      physical transport
q_T -> q^{n+1} reinit/profile/mass-closure projection
```

separately.  On a remote `N=16,T=0.04` endpoint smoke with reinit every step,
the exported NPZ contained all three arrays with shape `(3,17,17)`.  The
maximum physical-transport field delta was `6.436583e-07`, while the maximum
reinit-leg delta was `1.778247e-01`.  This confirms that reinit can dominate
the apparent shape change and must not be counted as capillary work.

## Phase-Error RCA

The remaining phase/static error is not caused by the one-component projection
removing the dynamic mode.  A remote `N=32,T=1` no-reinit probe with
`capillary_range_projection:none` gave the same early Rayleigh-Lamb stiffness
as `component_hodge_augmented`: `omega≈0.14017`, or about `70%` of the
reference stiffness.  The projection is still necessary for the static
component reaction: static `none` produced KE `5.026189e-06`, while static
component mode gave `5.284015e-09`.

The slow no-reinit phase is also not an early grid-remap artifact.  A
static-grid no-reinit `N=32,T=4` component probe gave `omega≈0.13976`, matching
the dynamic-grid no-reinit result through `T=4`.

The current cause is therefore force-side: the scalar `face_implicit`
capillary cochain, even after component augmentation, is not yet the
fixed-stratum Riesz representative of `d(sigma S_h)`.  It removes the constant
component reaction but does not provide the correct surface-energy Hessian for
resolved nonconstant modes.  Reinit is a separate measurement/energy
contaminant: it can shift phase and energy strongly, but it does not explain
the no-reinit under-stiffness.

## Remedy Theory Selection

The remedy space was expanded in `CHK-RA-CH14-REMEDY-THEORY-001`.  The
selection rule is not near/middle/long-term priority and not a
circle/ellipse decision.  A candidate survives only if it satisfies the finite
dimensional virtual-work diagram on an arbitrary fixed closed-interface
stratum:

```text
<s,w>_M   = -d(sigma S_h)[T w]
<b_m,w>_M =  dV_m,h[T w]
X         = [A_f G_f  B]
h         = (I - Pi_X) s
Pi_X s    = X (X^T M_f X)^+ X^T M_f s.
```

This rejects scalar Rayleigh rescaling, density/inertia scaling, damping,
CFL tuning, curvature caps/smoothing, shape-name branches, raw `none` as a
production law, blanket `range_projected`, QP-as-physics, and PPE-tolerance
workarounds.  They either tune one symptom or delete the quotient force
without proving the surface-energy covector.

The surviving construction is:

```text
1. fixed-stratum trace geometry for S_h and V_m,h,
2. transport VJP T^T for the pre-reinit endpoint,
3. M_f Riesz representatives s and B,
4. weighted projection onto range(A_fG_f)+range(B),
5. full s in the corrector, with projection used only to remove reactions,
6. q^n -> q_T -> q^{n+1} endpoint ledger so reinit work is separate.
```

Rayleigh-Lamb remains a Hessian acceptance test, not a calibration target.
Static droplet tests must be phrased as constrained criticality of the same
`S_h,V_h` pair, not as "is this trace a circle?"  Dynamic tests must include
arbitrary noncritical perturbations so the implementation proves it computes
the quotient force for nonconstant modes in general.

## Rigorous Contract Decomposition

`CHK-RA-CH14-RIGOR-THEORY-001` refines the selected remedy into separable
contracts.  A fixed trace stratum `K` contains the cut graph, oriented
segments, host grid edges for trace points, component labels, and topology
hash.  Local coordinates `q_i in (0,1)` place trace points on their host edges:

```text
x_i(q_i) = (1-q_i)a_i + q_i b_i.
```

Derivatives are valid only while the same `K` remains active.  Length and
volume are differentiated as geometry functionals, not as sampled curvature:

```text
S_h(q) = sum_(i->j) |x_j-x_i|,
V_m,h(q) = C_m(K) + 0.5 sum_(i->j in m) cross(x_i,x_j).
```

The transport differential is the derivative of the actual pre-reinit endpoint
map:

```text
q_T = Phi_K(q,u,dt),
T_K = partial Phi_K / partial u.
```

The VJP gate is the dot-product identity

```text
(T_K^T g)^T w = g^T (T_K w).
```

The face cochain is accepted only if the Riesz residuals vanish:

```text
s^T M_f w + d(sigma S_h)[T_K w] = 0,
b_m^T M_f w - dV_m,h[T_K w] = 0.
```

Projection is then purely a reaction removal:

```text
X=[A_fG_f B],
h=s-X(X^TM_fX)^+X^TM_f s,
X^TM_fh=0.
```

Finally, the corrector sign is locked by energy power on release from rest:

```text
d(sigma S_h)[T_K a_cap] = -||h||_M^2 + higher-order terms.
```

This gate catches sign mistakes even when the projection residual is small.
Reinit remains a separate map and ledger entry:

```text
Delta E_total =
  [E_h(q_T)-E_h(q^n)] + [E_h(q^{n+1})-E_h(q_T)].
```

## Implementation Method

`CHK-RA-CH14-IMPL-METHOD-001` maps the rigorous contract onto current code.
The selected force law should not be encoded as a fake curvature method.
Introduce an explicit capillary source selector under the existing pressure
jump formulation:

```yaml
numerics:
  physical_time:
    momentum:
      capillary_force:
        formulation: pressure_jump
        source: closed_interface_riesz
```

`curvature` remains the legacy scalar-jump source.  `source` chooses how the
raw face cochain is constructed.  `capillary_range_projection` remains a
reaction/projection policy.

The implementation should be split into proof-sized objects:

```text
ClosedInterfaceStratum
TraceGeometryFunctional
TransportLinearization
CapillaryRieszCochain
AugmentedCapillaryHodgeProjector
CorrectorSignLock
ReinitEnergyLedger
```

The first code commit should implement only stratum/geometry diagnostics:

```text
closed_interface_stratum.py
closed_interface_geometry.py
test_closed_interface_geometry.py
```

and prove finite-difference consistency of `S_h` and `V_h` on unchanged
strata.  Production coupling comes later, after transport VJP, Riesz residual,
augmented projection, and corrector sign-lock tests pass.

## YAML UX Policy

`CHK-RA-CH14-YAML-UX-001` defines the user-facing configuration contract.  The
new law must not be hidden behind `curvature`, and reaction projection must not
reuse the old force-deleting name.  The readable form is:

```yaml
capillary_force:
  formulation: pressure_jump
  source: closed_interface_riesz
  closed_interface:
    topology: fail_closed
    transport_adjoint:
      endpoint: before_reinit
poisson:
  operator:
    capillary_reaction_projection: pressure_component_hodge
```

Meaning:

```text
source
  chooses the raw capillary cochain construction.

closed_interface
  chooses the fixed-stratum geometry and transport-adjoint contract.

capillary_reaction_projection
  removes only pressure/component reactions in the same M_f metric.
```

Legacy scalar pressure-jump configs may keep:

```yaml
capillary_force:
  source: curvature_jump
  curvature: face_implicit
poisson:
  operator:
    capillary_range_projection: component_hodge_augmented
```

For `source: closed_interface_riesz`, the parser should reject `curvature`,
`capillary_range_projection`, boolean aliases, benchmark names, Rayleigh
rescaling knobs, damping fixes, curvature caps, and smoothing workarounds.
Diagnostics should be theorem gates such as Riesz-work residual, Hodge
orthogonality, corrector sign power, and reinit energy split, not
shape-specific labels.

## Geometry Implementation Slice

`CHK-RA-CH14-GEOM-IMPL-001` implements the first code slice without changing
production capillary physics:

```text
closed_interface_stratum.py
closed_interface_geometry.py
test_closed_interface_geometry.py
```

It exposes fixed-stratum hashing and sharp P1 geometry diagnostics:

```text
K hash from cell sign cases and edge crossing counts,
S_h = P1 marching-squares trace length,
V_h = sharp area of psi >= threshold,
dS_h = existing P1 marching-squares length gradient,
dV_h = analytic shoelace/edge-crossing area derivative.
```

The derivative checker verifies centered directional differences only when
`psi+eps*r` and `psi-eps*r` keep the same stratum hash.  Exact threshold
touches are irregular and fail closed.  Remote validation:

```text
598 passed, 32 skipped in 43.43s
```

The follow-up N32/T1 ch14 regression gate completed remotely with visualization
for both static and oscillating droplets:

```text
static:      final KE 5.284015367708e-09, max |Delta V| 2.918607938522e-15,
             deformation 0 -> 0, max speed Linf 2.546460883371e-05
oscillating: final KE 3.643971286909e-04, max |Delta V| 2.428288862556e-15,
             signed deformation 7.617534118366e-02 -> 4.334636515834e-02,
             max speed Linf 1.321312837017e-02
```

The result is a regression pass for the geometry slice and confirms that the
current component-Hodge production path still has nonzero capillary drive for
the oscillating droplet.  It is not the final theorem gate: the force-side VJP,
`M_f` Riesz cochain, augmented Hodge projection for the new cochain, corrector
sign-lock, and YAML runtime mode remain separate implementation slices.

The same current-production probe at `N=32,T=4` gives:

```text
static:      final KE 3.168855531975e-09, max |Delta V| 3.172399933176e-15,
             deformation 0 -> 0, max speed Linf 3.240408584682e-05
oscillating: final KE 2.479811774672e-03, max |Delta V| 3.961944986275e-15,
             signed deformation 7.617534118366e-02 -> 2.894198501011e-02,
             max speed Linf 2.333385447203e-02
```

The analytical overlay in the canonical YAML is
`0.10 cos(0.167435 t)`, giving approximately `7.838e-02` at `t=4`; the
simulated signed deformation is therefore far too small.  This longer run
strengthens the conclusion that the zero-drive pathology is gone, but the
current scalar curvature-jump production cochain plus reinit-contaminated shape
ledger is not yet final Rayleigh-Lamb physics.

## Riesz Verification Slice

`CHK-RA-CH14-RIESZ-VERIFY-001` implements the proof diagnostic layer:

```text
closed_interface_riesz.py
test_closed_interface_riesz.py
```

The tested candidate is

```text
T(u) = -D_f(psi_f u_f)
s    = -M_f^{-1} T^T d(sigma S_h)^T
B    =  M_f^{-1} T^T dV_h^T
```

with Hodge projection performed by a dense diagnostic matrix for the same
`D_f` and `M_f`.  The result is split:

```text
Riesz virtual work for T_c:             PASS
sampled-circle finite-N residual:       nonzero; convergence data, not oracle
dynamic nonconstant-mode drive:         PASS
production acceptance for final force:  not yet
```

For an N12 ellipse, the fixed-stratum virtual-work check gives:

```text
finite_difference    -3.550367776828e+01
gradient_action      -3.550367702084e+01
capillary_power       3.550367702084e+01
Riesz residual        0
```

Thus `d(sigma S_h)[T(u)] + <s,u>_M = 0` is algebraically correct for the
chosen transport map.

The finite-grid static reading is now sharpened by
`CHK-RA-CH14-TRACE-VJP-THEORY-001`.  A continuum circle sampled by a P1
marching-squares polygon is not automatically an exact discrete
area-constrained minimizer of `S_h`.  Therefore the sampled-circle residual
from N10--N24 is a convergence gate, not a roundoff static gate.

The theorem-level conclusion is still negative for production acceptance, but
it is more precise:

```text
T(u)=-D_f(psi_f u_f) is Riesz-correct for conservative nodal indicator transport.
It has not been proven to be the sharp trace-vertex transport differential.
```

The next implementation candidate must therefore use the VJP of the actual
marching-squares trace vertices under face velocities, not damping, smoothing,
CFL tuning, curvature caps, projection deletion, or a shape-name branch.

## Trace-Vertex Transport Contract

On a fixed trace stratum `K`, each cut edge `e=(i,j)` has a vertex

```text
alpha_e = (tau - q_i)/(q_j - q_i),
z_e     = x_i + alpha_e (x_j - x_i).
```

The discrete geometric primitives are the polygonal trace functionals:

```text
S_h(z) = sum_segments |z_b-z_a|,
V_h(z) = shoelace area of each component.
```

For segment `a -> b`,

```text
ell = |z_b-z_a|,
t   = (z_b-z_a)/ell,
delta S_segment = sigma t . (delta z_b - delta z_a).
```

For an oriented polygon,

```text
delta V = sum_k delta z_k . 0.5 R_-90 (z_{k+1}-z_{k-1}),
```

with the sign fixed by the implementation's shoelace convention.

The missing theorem object is the fixed-stratum trace velocity map:

```text
C_K : face velocities -> trace vertex velocities,
delta z = C_K u_f.
```

The production-grade cochains must then be:

```text
s_K = -M_f^{-1} C_K^T d_z(sigma S_h)^T
B_K =  M_f^{-1} C_K^T d_z V_h^T.
```

This is shape-free.  It does not ask whether the component is a circle,
ellipse, or a deeper nonconstant mode.  A static component is defined only as
a discrete constrained critical point; a dynamic mode is defined by nonzero
component-constrained Hodge residual.

## Theory Gates Before Production

The next implementation is accepted only after these gates:

```text
fixed-stratum topology unchanged under probes,
vertex finite differences of S_h and V_h match d_z forms,
face Riesz identities hold for s_K and B_K,
weighted Hodge residual equals s - X(X^T M_f X)^+X^T M_f s with X=[A_fG_f B],
sampled analytic circle is treated as convergence data, not a finite-N oracle,
constructed discrete critical traces give h ~= 0 if available,
resolved nonconstant perturbations give h != 0 above the static floor,
constant translations give delta S_h ~= delta V_h ~= 0,
zero-normal trace velocities give no first-order work up to C_K interpolation error,
pre-reinit and reinit geometry changes are ledgered separately.
```

The first concrete `C_K` may be `reconstructed_nodal_p1`: reconstruct nodal
vector velocity from face DOFs and P1-interpolate it to trace vertices.  It is
only a proof candidate.  If it fails the gates, the theory points to direct
face interpolation or a mimetic/Whitney trace map, not to scalar tuning.

## Full Implementation Target

The full implementation should expose:

```text
ClosedInterfaceStratum
CapillaryVariationalCochain
M_f, D, R, C_K, S_h, V_m, s_K, B_K
Riesz residuals
component range residuals
normal-equation projection residuals
reinit stratum ledger
```

Production may use the cochain only after those gates pass.

## Trace VJP Implementation And UX

`CHK-RA-CH14-TRACE-IMPL-UX-001` maps the trace-vertex theorem onto the
current solver seams.

Code objects:

```text
closed_interface_trace.py
  TraceGraph2D, TraceVertex2D, TraceSegment2D, TraceComponent2D.

closed_interface_trace_velocity.py
  TraceVelocityMap and ReconstructedNodalP1TraceVelocityMap.

closed_interface_trace_riesz.py
  ClosedInterfaceTraceRieszCochain from C_K^T d_zS_h and C_K^T d_zV_h.

weighted_augmented_hodge_projection
  multi-component M_f projection for X=[A_fG_f B].
```

The old `closed_interface_riesz.py` remains a conservative-transport
diagnostic until the new path passes the theorem gates.

Runtime wiring must use the existing face-cochain seam:

```text
div_op.pressure_fluxes(..., capillary_jump_components=corrected_capillary_components)
```

For `source: closed_interface_riesz`, the solver should:

```text
choose psi_transport_endpoint before reinit;
build s_K and B_K from the trace graph and C_K;
compute corrected_capillary_components = s_K - B_K mu;
add D_f(corrected_capillary_components) to the PPE RHS;
pass the same corrected_capillary_components to pressure_fluxes;
store pressure-face history in the existing affine-jump face state.
```

The YAML contract is explicit:

```yaml
capillary_force:
  formulation: pressure_jump
  source: closed_interface_riesz
  closed_interface:
    trace_space: p1_marching_squares
    topology: fail_closed
    ambiguous_cells: fail
    surface_energy: sharp_length
    component_volume: oriented_area
    trace_velocity:
      map: reconstructed_nodal_p1
      endpoint: before_reinit
    diagnostics:
      gates: strict
poisson:
  operator:
    capillary_reaction_projection: pressure_component_hodge
```

Legacy scalar-jump configs keep:

```yaml
capillary_force:
  formulation: pressure_jump
  source: curvature_jump
  curvature: face_implicit
poisson:
  operator:
    capillary_range_projection: component_hodge_augmented
```

For `closed_interface_riesz`, the parser should fail closed on `curvature`,
`curvature_cap`, smoothing, damping, Rayleigh scaling, benchmark names,
`capillary_range_projection`, and boolean projection aliases.  It should
require `pressure_jump`, `phase_separated`, `affine_jump`, face-native state,
and `capillary_reaction_projection: pressure_component_hodge`.

## Trace-Riesz Runtime Gate

`CHK-RA-CH14-TRACE-RIESZ-N32T1-001` implemented the runtime slice of the
trace-vertex theorem.  The new `surface_tension.source:
closed_interface_riesz` route:

1. records the transport endpoint before reinit/profile projection,
2. builds `s_K=-M_f^{-1}C_K^Td_z(sigma S_h)` and
   `B_K=M_f^{-1}C_K^Td_zV_m`,
3. computes the component-reaction-corrected cochain `c_K`,
4. adds `D_f c_K` to the PPE RHS, and
5. passes the same `c_K` through
   `div_op.pressure_fluxes(..., capillary_jump_components=c_K)`.

The scalar affine Young-Laplace jump is disabled for this source, so curvature
does not double count the trace-Riesz force.  `capillary_range_projection`
remains illegal under the new source; the allowed reaction operation is
`capillary_reaction_projection: pressure_component_hodge`.

The Hodge linear algebra now uses the same `M_f,D_f` theorem object with an
analytic sparse FCCD divergence matrix.  The normal equation
`D_f M_f^{-1}D_f^T p = D_f c` is singular by pressure gauge, so the
implementation solves it with an explicit gauge pin instead of an unconstrained
least-squares iteration.  This is part of the theorem object: the residual
cochain must satisfy `D_f h` to roundoff before any physical interpretation is
made.

N=32/T=1 remote validation:

| case | KE first -> last | speed Linf final | shape metric | max volume drift | verdict |
|---|---:|---:|---:|---:|---|
| static circle | `1.270e-10 -> 8.882e-07` | `1.347e-03` | deformation `0 -> 0` | `2.030e-15` | stable, not roundoff-static |
| oscillating droplet | `2.302e-09 -> 9.657e-05` | `5.405e-03` | signed deformation `7.618e-02 -> 4.349e-02` | `1.917e-15` | zero-drive removed |

The key regression is decisive: the old N=32/T=1 `range_projected` path had
`KE ~1e-37` and velocity Linf `3.57e-19`, while the trace-Riesz route produces
finite capillary motion.  The static circle still carries finite-grid spurious
current; it should be treated as a convergence gate, not an exact equilibrium
oracle for a sampled continuum circle.

`CHK-RA-CH14-HODGE-SOLVE-FIX-001` tightened the implementation check.  A
manufactured analytic pure-range cochain
`c=M_f^{-1}D_f^T p(x,y)` is recovered with Hodge weighted norm
`7.06e-13`, range Linf error `2.27e-12`, and relative divergence residual
`7.67e-16`.  The N32 wall trace projection now gives `||D_f h||_inf =
2.04e-11` and component-reaction orthogonality `2.60e-18`.  Therefore the
previous `O(1e-2..1e-1)` trace Hodge divergence was a linear-solve contaminant,
while the remaining nonzero Hodge norm is the force-cochain/static-critical
problem, not a projection algebra failure.

`CHK-RA-CH14-HODGE-NORM-001` adds the missing static-criticality gate.  The
gate is the finite-dimensional Euler--Lagrange residual

```text
d_z(sigma S_h) - projection_span{d_z V_m} d_z(sigma S_h).
```

It is shape-free: it never asks whether a component is a circle or ellipse.
The N32 sampled analytic circle has vertex criticality ratio
`1.568664e-01`, so it is not a roundoff static oracle for the P1 trace
geometry.  The trace-Hodge residual is also not an affine-weight or boundary
artifact: periodic and wall probes match, and affine cut-face weights leave the
N32 static Hodge ratio unchanged (`3.732547e-02` vs `3.736686e-02`).

The same checkpoint separates endpoint theorems.  The trace-vertex cochain has
self Riesz residual `1.054671e-16` under its own `C_K`, but against the
solver's conservative `psi` transport endpoint the work residual is
`2.413967e-01`.  The conservative transport Riesz cochain matches that same
endpoint with residual `5.761773e-09`.  Therefore production must make the
transport endpoint and capillary VJP identical: either use the conservative
endpoint VJP for the current transport, or change transport to the trace-vertex
endpoint.  The static residual must not be hidden by projection, damping,
smoothing, or curvature clipping.
