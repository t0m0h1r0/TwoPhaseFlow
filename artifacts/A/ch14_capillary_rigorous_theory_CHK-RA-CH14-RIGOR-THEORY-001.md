# CHK-RA-CH14-RIGOR-THEORY-001: rigorous capillary-force contract

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: refine the selected ch14 remedy into smaller mathematical objects,
lemmas, residuals, and implementation-facing proof obligations.  This is a
theory/documentation slice only.

## Objective

The previous remedy selection identified the only acceptable family:

```text
fixed trace stratum
+ S_h,V_h geometry
+ pre-reinit transport VJP
+ M_f Riesz representatives s,B
+ weighted projection onto range(A_fG_f)+range(B)
+ full quotient force in the corrector
+ reinit-separated energy ledger.
```

This document turns that family into a set of precise contracts.  The goal is
not to make a circle or ellipse detector.  The goal is to define capillarity
for an arbitrary closed discrete interface on a fixed trace stratum.

## Layer 0: Discrete Spaces And Signs

Let

```text
U_h  = face velocity space,
P_h  = cell pressure space,
Q_hK = trace-coordinate space on stratum K.
```

The face metric is a symmetric positive definite matrix `M_f`.  The pressure
gradient range is represented by

```text
R = A_f G_f : P_h -> U_h.
```

Only `range(R)` matters; pressure nullspaces do not.  Any solver form must be
equivalent to the `M_f`-orthogonal projection onto that range, possibly
augmented by component reactions.

The capillary force convention used in this document is:

```text
<s,w>_M = -dE_h[T w].
```

Thus `s` is the force direction that lowers surface energy.  If production code
stores the opposite sign as a pressure jump, an adapter is allowed, but it must
pass the sign-lock gate:

```text
dE_h[T a_cap] = -||h||_M^2 + higher-order terms
```

for a zero-velocity release after reaction removal.  This gate is more
important than the variable name.

## Layer 1: Fixed Trace Stratum

A stratum `K` is the discrete topological data that makes the geometry
differentiable:

```text
K = (
  cut cells,
  cut edges/faces,
  ordered interface segments,
  component labels,
  segment orientations,
  host grid edge for each trace point,
  full/empty cell labels adjacent to the trace,
  pressure/face incidence used by the transport map
).
```

The trace coordinates are local parameters

```text
q_i in (0,1)
```

on host grid edges.  A trace point is

```text
x_i(q_i) = (1-q_i) a_i + q_i b_i,
```

where `a_i,b_i` are the host-edge endpoints.  The admissible coordinate set is
an open polytope:

```text
Omega_K = { q : 0 < q_i < 1, no segment degeneracy, same connectivity }.
```

All derivatives below are valid only in `Omega_K`.  If a perturbation crosses
the boundary of `Omega_K`, the derivative is undefined for this stratum and
the variational path must fail closed.

### Stratum Lemma

On `Omega_K`, the trace point map `q -> x(q)`, length `S_h(q)`, component
volumes `V_m,h(q)`, and frozen-stratum transport endpoint `q_T(q,w)` are
piecewise smooth.  Across the boundary of `Omega_K`, the formulas may jump
because the cut graph changed.  Therefore every finite-difference derivative
probe must assert:

```text
hash(K(q+eps r)) = hash(K(q)) = hash(K(q-eps r)).
```

No fallback derivative is permitted when this check fails.

## Layer 2: Geometry Functionals

Let an oriented interface component consist of directed segments

```text
e = (i -> j),  x_i=x_i(q_i),  x_j=x_j(q_j).
```

The discrete surface length is

```text
S_h(q) = sum_e |x_j - x_i|.
```

For a perturbation `delta q`, define

```text
delta x_i = J_i delta q_i,
J_i = b_i - a_i.
```

For one segment,

```text
tau_e = (x_j - x_i) / |x_j - x_i|,
delta |x_j-x_i| = tau_e dot (delta x_j - delta x_i).
```

Thus `dS_h` is assembled by adding `-tau_e` to the tail trace point and
`+tau_e` to the head trace point, followed by multiplication by each host-edge
Jacobian `J_i`.

For oriented area in two dimensions, use the shoelace form for the cut
boundary plus full-cell constants:

```text
V_m,h(q) = C_m(K) + 0.5 sum_(i->j in boundary m) cross(x_i, x_j).
```

The constant `C_m(K)` contains the area of fully assigned cells and has zero
derivative on the stratum.  The variation of one oriented segment is

```text
delta [0.5 cross(x_i,x_j)]
  = 0.5 cross(delta x_i, x_j) + 0.5 cross(x_i, delta x_j).
```

This gives `dV_m,h`.  The sign is fixed by component orientation; reversing the
boundary orientation reverses both `V_m,h` variation and the corresponding
component multiplier.  The projection residual is orientation invariant if the
same orientation is used consistently in `B`.

### Geometry Lemma

The geometry layer never samples curvature as primitive force data.  Curvature
is a possible interpretation of the length derivative after assembly.  The
force law uses `dS_h` and `dV_m,h` directly.

This avoids two common errors:

```text
1. a sampled curvature field that is not the derivative of S_h,
2. a mean-curvature subtraction that is not the derivative of V_m,h.
```

## Layer 3: Transport Differential

Let the physical advection endpoint before reinit be

```text
q_T = Phi_K(q, u, dt),
```

where `u in U_h` is the face velocity used by the actual transport path.  The
transport differential is

```text
T_K(q,dt) = partial Phi_K / partial u.
```

For infinitesimal release from rest, `T_K` may be evaluated at the predictor
velocity used by the scheme.  For finite-step energy ledgers, the transport
path must match the actual `q^n -> q_T` path, not a simplified geometry-only
path.

The VJP contract is:

```text
for every trace covector g and face direction w,
  (T_K^T g)^T w = g^T (T_K w).
```

The first diagnostic implementation may verify this by centered finite
differences:

```text
T_K w ~= [Phi_K(q, eps w, dt) - Phi_K(q, -eps w, dt)] / (2 eps)
```

provided the stratum hash is unchanged.  Production should replace the probe
with an analytic local VJP, but the analytic path inherits this same identity.

### Transport Lemma

If `T_K` is not the differential of the actual pre-reinit transport endpoint,
then even an exact `dS_h` produces the wrong face cochain.  Therefore the
transport VJP is part of the force definition, not a diagnostic afterthought.

## Layer 4: Face Riesz Pullback

Let

```text
E_h(q) = sigma S_h(q),
G_S(q) = dE_h(q)^T,
G_V(q) = [dV_1,h(q)^T ... dV_k,h(q)^T].
```

The face-space force and component-reaction columns are defined by Riesz
representation:

```text
s = -M_f^{-1} T_K^T G_S,
B =  M_f^{-1} T_K^T G_V.
```

Equivalently, for arbitrary `w in U_h`,

```text
s^T M_f w   = -G_S^T T_K w,
b_m^T M_f w =  G_V,m^T T_K w.
```

These equations are the capillary source of truth.  A pressure jump, curvature
sample, or surface-stress divergence can be used only after proving that its
assembled face cochain satisfies these equations in the same `M_f`.

### Riesz Residuals

Use random and structured face directions `w_j` and report

```text
rho_S(w_j) =
  |s^T M_f w_j + dE_h[T_K w_j]|
  / (|s^T M_f w_j| + |dE_h[T_K w_j]| + eps_abs),

rho_V(m,w_j) =
  |b_m^T M_f w_j - dV_m,h[T_K w_j]|
  / (|b_m^T M_f w_j| + |dV_m,h[T_K w_j]| + eps_abs).
```

No production force should be accepted until these residuals converge under
mesh refinement and finite-difference epsilon refinement on unchanged strata.

## Layer 5: Augmented Hodge Projection

The silent reaction space is

```text
X = [R  B] = [A_fG_f  B].
```

The reaction component of `s` is the `M_f`-orthogonal projection

```text
Pi_X s = X z,
z = (X^T M_f X)^+ X^T M_f s.
```

The quotient capillary force is

```text
h = s - Pi_X s.
```

It satisfies

```text
X^T M_f h = 0
```

and minimizes `||s-x||_M` over `x in range(X)`.

### Schur Form

If `R` is not explicitly formed, the same projection can be expressed by the
normal equations:

```text
[R^T M_f R  R^T M_f B] [p ] = [R^T M_f s]
[B^T M_f R  B^T M_f B] [mu]   [B^T M_f s].
```

The coefficients `(p,mu)` are not unique when pressure has a nullspace or when
some component column lies in `range(R)`.  The projected vector `Xz` is unique.
Therefore the implementation must rank-reveal or pseudoinvert the normal
system and test the vector residual, not the raw coefficient values.

### Projection Residuals

The required reports are:

```text
rho_X      = ||X^T M_f h|| / ((||X^T M_f|| ||h||) + eps_abs),
rho_min    = | ||s-Pi_Xs||_M^2 - min_x ||s-x||_M^2 | diagnostic,
rho_static = ||h||_M / (||s||_M + eps_abs) on constrained critical traces.
```

`rho_static` is meaningful only when the trace has independently passed the
geometry criticality check for the same `S_h,V_h`; it must not be defined by
shape name.

## Layer 6: Static And Dynamic Theorems

### Static Theorem

Assume the trace is a constrained critical point:

```text
dE_h[T_K w] = sum_m lambda_m dV_m,h[T_K w] + pressure reaction
```

for all face directions `w`.  Then, by the Riesz definitions,

```text
s in range([R B]),
```

and therefore `h=0`.

Conversely, if `h=0` and the transport image spans the trace tangent directions
modulo the pressure and volume constraints, then the trace is constrained
critical for the discrete energy.  The converse requires this rank condition;
without it, a transport map could hide an unresolved mode.

### Noncritical-Mode Theorem

If there exists a face direction `w` such that

```text
dE_h[T_K w] != sum_m lambda_m dV_m,h[T_K w] + pressure reaction
```

for all multipliers, then `s` is not in `range(X)` and `h != 0`.  This is the
general statement behind "nonconstant curvature modes move."  It does not
refer to ellipses.  Any resolved arbitrary perturbation with nonzero quotient
energy gradient must produce acceleration from rest.

## Layer 7: Rayleigh-Lamb As A Hessian Gate

Rayleigh-Lamb is a consistency gate around one constrained critical trace, not
a source-term calibration.  Let `q0` be the discrete circular critical trace
and let `eta` be a resolved tangent perturbation satisfying the component
volume constraint to first order:

```text
dV_h(q0)[eta] = 0.
```

The constrained Hessian is

```text
K_h eta = d^2(E_h + lambda^T V_h)(q0)[eta].
```

The effective inertial metric induced by face velocities is

```text
M_eff(eta) = min_{w : T_K w = eta} ||w||_M^2.
```

For a small mode,

```text
omega_h^2 = (eta^T K_h eta) / M_eff(eta).
```

The acceptance condition is that `omega_h` converges to Rayleigh-Lamb for
resolved modes as the grid is refined.  The force must not be scaled to make
this true for one benchmark; it must follow from `S_h,V_h,T_K,M_f`.

## Layer 8: Corrector Sign And Energy Power

After projection, the physical quotient force is `h` under the sign convention
of this document.  The acceleration used by the code, `a_cap`, must satisfy

```text
a_cap = h + reaction-free higher-order/time-discretization terms
```

or the same statement with all stored capillary source signs reversed.  The
sign is locked by energy power:

```text
dE_h[T_K a_cap] = -||h||_M^2
```

to leading order for release from rest.  A sign convention that gives
`+||h||_M^2` is physically wrong even if it produces motion.

This gate catches a subtle implementation error: a projection vector can be
mathematically correct while the corrector subtracts it with the wrong sign.

## Layer 9: Reinit-Separated Energy Ledger

One step has two distinct maps:

```text
q^n --physical transport--> q_T --profile/reinit projection--> q^{n+1}.
```

The energy split is

```text
Delta E_total
  = [E_h(q_T) - E_h(q^n)]
  + [E_h(q^{n+1}) - E_h(q_T)].
```

Only the first bracket is capillary transport work.  The second bracket is a
numerical projection ledger entry.  It can be stabilizing, destabilizing, or
shape-changing, but it must not be folded into capillary work or Rayleigh phase
evidence.

For finite-step energy accounting, introduce a discrete gradient

```text
bar_G_S(q^n,q_T)
```

such that

```text
bar_G_S^T (q_T-q^n) = E_h(q_T)-E_h(q^n).
```

An average-vector-field or Gonzalez gradient is acceptable only on the same
stratum.  It complements the infinitesimal `dE_h`; it does not replace the
one-step acceleration gates.

## Acceptance Residual Matrix

| Layer | Residual | Failure interpretation |
|---|---|---|
| Stratum | hash changes under derivative probe | derivative invalid, fail closed |
| Geometry | centered `dS_h,dV_h` mismatch | length/area derivative bug |
| Transport | VJP dot-product mismatch | force not adjoint to actual advection |
| Riesz | `rho_S,rho_V` nonconvergent | face cochain not virtual-work representative |
| Projection | `X^TM_f h` nonzero | pressure/component reaction not correctly removed |
| Static | critical trace has nonzero `h` | false static current |
| Noncritical | arbitrary quotient perturbation has zero `h` | physical drive deleted |
| Sign | `dE[T a_cap] > 0` on release | corrector sign/source convention wrong |
| Rayleigh | Hessian frequency nonconvergent | wrong stiffness/inertia diagram |
| Reinit | large unreported `E(q^{n+1})-E(q_T)` | projection work contaminates physics |

## Implementation Decomposition

The implementation should be split along the same boundaries:

```text
ClosedInterfaceStratum
  owns K, q, orientations, component labels, topology hash.

TraceGeometryFunctional
  returns S_h, V_h, dS_h, dV_h and geometry residuals.

TransportLinearization
  returns T_K w probes and analytic VJP T_K^T g.

FaceMetricRiesz
  maps trace covectors to face vectors s and B using M_f.

AugmentedHodgeProjector
  computes Pi_X s, h, rank diagnostics, and projection residuals.

CorrectorSignLock
  verifies that the solver convention applies the quotient force with
  energy-lowering sign.

ReinitEnergyLedger
  reports q^n -> q_T and q_T -> q^{n+1} separately.
```

No object in this list should know the benchmark name.  The benchmark enters
only through validation data.

## Open Mathematical Risks

1. Transport rank: if `T_K` does not span enough trace tangent directions, a
   zero Hodge residual can be a transport degeneracy rather than true
   equilibrium.
2. Metric mismatch: using one face metric in the Riesz step and another in the
   projection breaks the theorem.
3. Component rank: some volume columns may be redundant with pressure range or
   with each other; only projected vectors are unique.
4. Stratum boundary: high curvature or thin necks can move derivative probes
   outside `Omega_K`; the correct response is fail closed, not smoothing.
5. Reinit dominance: if the profile projection changes `S_h` more than the
   transport leg, the step cannot be interpreted without the split ledger.
6. Diffuse/sharp mismatch: diffuse surface-energy derivatives are admissible
   only if the validation uses that same diffuse `S_h`; they cannot be mixed
   silently with sharp trace acceptance.

## Final Contract

The capillary force is accepted only when the code can state and verify:

```text
K fixed,
E_h=sigma S_h,
V_h=(V_1,h,...,V_k,h),
T_K=partial_u Phi_K before reinit,
s=-M_f^{-1}T_K^T dE_h^T,
B= M_f^{-1}T_K^T dV_h^T,
X=[A_fG_f B],
h=(I-X(X^TM_fX)^+X^TM_f)s,
dE_h[T_K h] = -||h||_M^2,
Delta E_total = Delta E_transport + Delta E_reinit.
```

Every admissible implementation detail is subordinate to these equations.

[SOLID-X] Theory artifact only; no production source/config/result change, no
tested implementation deleted, no FD/WENO/PPE fallback, damping, CFL
workaround, curvature cap, smoothing, blanket `c -> Pi_R c`, benchmark-name
branch, or QP-as-physics path introduced.
