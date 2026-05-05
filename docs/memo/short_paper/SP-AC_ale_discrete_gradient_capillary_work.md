# SP-AC — ALE Discrete Gradient and Transport/Remap-Adjoint Capillary Work

- **Status**: ACTIVE / theory foundation
- **Compiled by**: Codex
- **Compiled at**: 2026-05-05
- **Scope**: ch14 N64 oscillating droplet, dynamic fitted grids, pressure-jump surface tension, variational capillarity
- **Primary consumers**: paper §3, §5, §8, §9, §10, §14; `src/twophase/coupling/transport_variational_capillary.py`
- **Depends on**: SP-AA, SP-AB, SP-J, SP-M, SP-W, SP-Y
- **Public-citation policy**: this SP is an internal research memo. The paper
  should cite external literature on discrete gradients, ALE geometric
  conservation, variational surface tension, GFM/IIM pressure jumps, and
  energy-stable two-phase schemes rather than this memo directly.

---

## 1. Abstract

The N64 alpha-2 oscillating-droplet investigation exposes a distinction that
ordinary curvature refinement does not address. Surface tension is not
fundamentally a pointwise curvature formula. It is the variational derivative
of interfacial area. A pressure-jump implementation is physically correct only
when the discrete pressure work is the negative finite-step change of the same
discrete surface energy used to define the interface geometry.

For fixed grids, the relevant surface energy can be written as

```text
S_h(psi) = sigma |Gamma_h(psi)|.
```

For dynamic interface-fitted grids, this is incomplete. The grid coordinates
are part of the discrete geometric state:

```text
q = (psi, X),
S_h(q) = S_h(psi, X) = sigma |Gamma_h(psi, X)|.
```

Therefore a discrete capillary closure must satisfy a finite-step chain rule
in the full ALE state space:

```text
S_h(q^{n+1}) - S_h(q^n)
  = Gbar_psi [psi^{n+1} - psi^n]
  + Gbar_X   [X^{n+1}   - X^n].
```

The capillary face force must then be obtained by pulling this covector back
through the adjoint of the actual transport/remap map used by the code. The
correct object is not "a better kappa" but

```text
F_cap = - K_h^* Gbar_q,
```

where `K_h` is the actual discrete kinematic map from face velocity to
interface-state change. A scalar pressure jump is admissible only if its jump
operator gives the same face work as this variational force.

The central hypothesis is that the current P2 discrete-gradient route closes
the `psi` part of the surface-energy difference but not the dynamic-grid
geometric work. The missing term is

```text
Gbar_X [Delta X],
```

plus any remap/mass-correction contribution that changes `S_h` without
physical interface motion. Such a residual can be small per step, invisible in
short runs, and still feed high-frequency interface modes over a long
Rayleigh--Lamb period. Hyperviscosity, smoothing, curvature caps, or CFL
tuning can hide the symptom but do not close the variational identity.

This memo completes the theory needed to close the discrete variational
principle: the state space, the finite-step ALE discrete gradient, the
interface-energy geometric conservation law, the transport/remap adjoint
pressure-work construction, pressure-jump representability, falsifiable
diagnostics, and the implementation contract.

## 2. Empirical trigger and research question

The relevant one-period control is

```text
experiment/ch14/config/ch14_oscillating_droplet_n64_alpha2_one_period.yaml
```

with

```text
N = 64,
alpha = 2,
surface_tension = 0.072,
T_period = 37.52611644626026,
curvature.method = transport_variational_p2_discrete_gradient.
```

Short gates are benign. For example the `T = 0.25` P2 discrete-gradient route
reaches the final time with small kinetic energy, small volume drift, and a
single connected interface. The pulled one-period data, however, terminates
around `t = 19.23735848673442` with kinetic energy exceeding `1e6`, while
the saved fields remain bounded until the late-time acceleration. This is
typical of a small but systematic energy leak into unresolved or weakly
resolved capillary modes.

The research question is therefore:

```text
What exact discrete variational identity must a dynamic fitted-grid
pressure-jump surface-tension route satisfy so that the surface-energy
difference and the pressure work are the same mathematical object?
```

The answer cannot be a local damping or filtering rule. It must be a closed
energy-work theorem.

## 3. Continuum foundation

Let `Gamma(t)` be a closed material interface in a two-phase incompressible
flow, and let

```text
S(t) = sigma |Gamma(t)|
```

be the surface energy. For a normal interface velocity

```text
V_n = u · n,
```

the first variation of length/area gives

```text
dS/dt = - ∫_Gamma f_sigma · u ds
```

or, with a sign convention for curvature,

```text
dS/dt = sigma ∫_Gamma kappa V_n ds.
```

The sign of `kappa` and the sign of the pressure jump depend on orientation,
but the invariant physical statement is

```text
surface-energy decrease + capillary work on the fluid = 0
```

in the inviscid capillary part. With viscosity, physical dissipation adds a
non-positive kinetic-energy contribution, but it does not alter the capillary
work identity itself.

For an oriented pressure jump, SP-AB fixes the convention

```text
psi = 1 liquid, psi = 0 gas,
n_lg = normal from liquid to gas,
j_gl = p_gas - p_liquid = - sigma kappa_lg.
```

This is a continuum stress law. It is not yet an energy-stable discrete law.
Energy stability requires that the discrete pressure jump be the work-equivalent
image of a discrete surface-energy derivative.

## 4. Discrete geometric state

On a dynamic fitted grid, the discrete interface geometry is not determined by
nodal `psi` alone. It is determined by the pair

```text
q = (psi, X),
```

where

- `psi` is the nodal phase/Heaviside field,
- `X` is the collection of grid coordinates,
- `Gamma_h(q)` is the reconstructed `psi = psi_*` interface, typically with
  `psi_* = 1/2`,
- `S_h(q)` is the discrete surface energy.

For the P2 trace route,

```text
S_h(psi, X) = sigma sum_K |Gamma_h(psi, X) ∩ K(X)|_{P2}.
```

Each cell contribution depends on

1. the four nodal values of `psi`,
2. the local cell coordinates from `X`,
3. the edge crossings,
4. the midpoint or transverse P2 crossing,
5. the quadrature rule used to approximate the P2 segment length.

Thus the mathematically correct differential is

```text
dS_h(q)[dq]
  = partial_psi S_h(psi, X)[dpsi]
  + partial_X   S_h(psi, X)[dX].
```

If `X` changes every physical step, omitting the second term is not a small
implementation detail. It changes the variational problem.

## 5. Fixed-grid discrete-gradient identity

On a fixed grid, a finite-step discrete gradient `Gbar_psi` is any covector
satisfying

```text
S_h(psi^{n+1}, X^n) - S_h(psi^n, X^n)
  = Gbar_psi [psi^{n+1} - psi^n].
```

The current P2 Gonzalez route belongs to this family. In abstract form, for
`m = (psi^n + psi^{n+1})/2`,

```text
Gbar_psi
  = grad_psi S_h(m, X)
  + ((Delta S_h - grad_psi S_h(m, X)[Delta psi])
     / ||Delta psi||_M^2) M Delta psi.
```

This construction enforces the finite-step chain rule for the chosen fixed-grid
energy and chosen inner product. It is stronger than using midpoint curvature,
because the discrete surface-energy difference is matched exactly in the
`psi` direction.

However, for dynamic grids it proves only the restricted identity

```text
Delta S_h at fixed X = Gbar_psi [Delta psi].
```

It does not prove

```text
Delta S_h with X^{n+1} != X^n = Gbar_psi [Delta psi].
```

Therefore fixed-grid energy closure is necessary but not sufficient for the
N64 dynamic fitted-grid route.

## 6. ALE discrete-gradient identity

For dynamic grids, define the full finite-step increment

```text
Delta q = q^1 - q^0 = (Delta psi, Delta X).
```

The ALE discrete gradient is a covector

```text
Gbar_q = (Gbar_psi, Gbar_X)
```

such that

```text
S_h(q^1) - S_h(q^0) = Gbar_q [Delta q].
```

Equivalently,

```text
S_h(psi^1, X^1) - S_h(psi^0, X^0)
  = Gbar_psi [psi^1 - psi^0]
  + Gbar_X   [X^1   - X^0].
```

Two standard constructions are admissible.

### 6.1 AVF discrete gradient

The average-vector-field discrete gradient is

```text
Gbar_q
  = ∫_0^1 grad_q S_h(q^0 + theta Delta q) dtheta.
```

Then the fundamental theorem of calculus gives

```text
Gbar_q[Delta q]
  = ∫_0^1 grad_q S_h(q(theta))[Delta q] dtheta
  = S_h(q^1) - S_h(q^0).
```

This is the cleanest theoretical definition. Its implementation requires
quadrature in `theta` and derivatives of `S_h` with respect to both `psi` and
`X`.

### 6.2 Gonzalez full-state discrete gradient

Let

```text
q_m = (q^0 + q^1)/2,
Delta S = S_h(q^1) - S_h(q^0).
```

Choose a positive definite metric `M_Q` on the full state space. Then

```text
Gbar_q
  = grad_q S_h(q_m)
  + ((Delta S - grad_q S_h(q_m)[Delta q])
     / ||Delta q||_{M_Q}^2) M_Q Delta q.
```

This also satisfies

```text
Gbar_q[Delta q] = Delta S.
```

The metric must include both `psi` and grid-coordinate components. If the
metric ignores `X`, the construction degenerates back to a fixed-grid
identity and cannot close dynamic-grid work.

### 6.3 Non-smooth cut-cell events

`S_h` is piecewise smooth. It can be non-smooth when cut topology changes,
when a contour passes through a vertex, or when an ambiguous four-crossing cell
changes branch. The finite-step identity remains meaningful as long as the
discrete gradient is defined for the finite pair `(q^0, q^1)`. At such events,
the AVF path may cross non-differentiable loci; the practical options are:

```text
1. use a generalized/subgradient finite-step construction,
2. split the step at the event,
3. define S_h with a branch-continuous cell energy and audit the branch jump.
```

These are mathematical branch choices, not smoothing. A production route must
record which convention is used because high-frequency interface failure can
be seeded by unresolved branch changes.

## 7. ALE kinematics and state update maps

Let `U_f` be the face velocity used by the projection/corrector work inner
product, and let `W` be the grid velocity. In continuous ALE form,

```text
partial_t psi |_xi + (U - W) · grad_X psi = 0,
partial_t X = W.
```

In a discrete code, the actual update is not this differential equation in
isolation. It is a composed map:

```text
q^n
  -- A_h --> q^-       pure adaptation / rebuild / remap
  -- T_h --> q^{n+1}  physical transport with U_f
  -- C_h --> q^{n+1,*} optional mass/profile correction.
```

The ordering may differ in a specific algorithm, but the theory requires that
the same ordering be used in the work identity. An abstract increment is

```text
Delta q
  = Delta q_A
  + Delta q_T
  + Delta q_C.
```

The physical capillary pressure work may close only the part of `Delta S_h`
caused by physical interface motion. Pure grid adaptation and purely numerical
corrections must either preserve `S_h` or appear as separate numerical work
terms.

## 8. Interface-energy geometric conservation law

Classical ALE schemes require a geometric conservation law: uniform flow should
remain uniform under grid motion. For capillary interfaces, the analogous
requirement is:

```text
pure representation changes must not create physical surface energy.
```

If a remap/adaptation map `A_h` changes

```text
q^n = (psi^n, X^n)
```

to

```text
q^- = (psi^-, X^-)
```

without physical interface motion, then the ideal interface-energy GCL is

```text
S_h(q^-) = S_h(q^n).
```

In finite-step variational form:

```text
Gbar_A,psi [psi^- - psi^n]
  + Gbar_A,X [X^- - X^n] = 0.
```

If this identity is violated, the adaptation stage injects or removes
interfacial energy without physical work. In a long oscillating-droplet run,
such a defect can behave like a parametric high-frequency forcing.

There are three theory-valid choices:

```text
A. construct an energy-preserving remap A_h so S_h(q^-) = S_h(q^n);
B. keep the adaptation energy Delta S_A as an explicit numerical-work term;
C. disable dynamic adaptation for the proof run and close the fixed-grid theory first.
```

Choice C is an admissible diagnostic isolation, not a final claim that dynamic
grids are wrong. Choice A or B is required for a complete dynamic fitted-grid
production theory.

## 9. Physical transport work and adjoint pullback

Consider the physical transport substep

```text
q^- -> q^{n+1}.
```

Let the actual discrete map be parameterized by the face velocity:

```text
q(theta) = T_h(q^-, theta U_f),
q(0) = q^-,
q(1) = q^{n+1}.
```

Define the linearized kinematic action

```text
dq/dtheta = Delta t K_h(theta) U_f.
```

Then

```text
S_h(q^{n+1}) - S_h(q^-)
  = ∫_0^1 grad_q S_h(q(theta))[dq/dtheta] dtheta
  = Delta t ∫_0^1 <K_h(theta)^* grad_q S_h(q(theta)), U_f>_F dtheta.
```

Therefore the energy-consistent capillary face force is

```text
F_cap
  = - ∫_0^1 K_h(theta)^* grad_q S_h(q(theta)) dtheta.
```

This is the continuous-in-the-step AVF form. With a finite-step discrete
gradient and an averaged kinematic operator,

```text
q^{n+1} - q^- = Delta t Kbar_h U_f,
```

the corresponding discrete force is

```text
F_cap = - Kbar_h^* Gbar_q.
```

Then the exact transport-work identity follows:

```text
S_h(q^{n+1}) - S_h(q^-)
  + Delta t <F_cap, U_f>_F = 0.
```

This is the core theorem. A pressure-jump scheme is correct only if it realizes
the same work.

## 10. What is K_h?

`K_h` must describe the actual update used by the code, not an idealized
transport equation.

For a conservative face-flux update on a fixed grid, a schematic form is

```text
Delta psi = - Delta t D_f (psi_f U_f),
```

so

```text
K_h U_f = - D_f (psi_f U_f).
```

The adjoint pullback is then

```text
K_h^* Gbar_psi
  = - psi_f D_f^* Gbar_psi
```

modulo face interpolation, density/metric inner products, and boundary terms.

For TVD-RK3, `K_h` is not a single frozen operator unless the stages are
linearized consistently. The exact finite-step adjoint is the reverse-mode
composition of the three RK stages:

```text
K_h^*
  = K_1^* R_2^* R_3^* + K_2^* R_3^* + K_3^*
```

schematically, where `R_i^*` propagate covectors backward through later stage
states. If the pressure jump uses only a single face value from the final
state, it is an approximation to the true transport adjoint. The work gate must
measure the resulting residual.

For remap/mass correction, `K_h` must include the derivative of that map if
the correction is treated as part of physical transport. If the correction is
not physical, its energy change must be excluded from pressure work and
reported separately.

## 11. Face-work inner product

The force identity is meaningful only after fixing the face work inner product.
Let

```text
<a, b>_F = sum_f m_f a_f b_f
```

where `m_f` is the face measure/metric weight used by the projection-native
velocity state. The divergence and gradient operators must satisfy the same
discrete adjoint convention:

```text
<p, D_f U>_C = - <G_f p, U>_F + boundary terms.
```

On periodic domains, the boundary terms vanish. On walls, the wall terms must
match the physical boundary work.

This requirement links capillary stability to the PPE contract. It is not
enough for `F_cap` to look like `sigma kappa n delta`. It must live in the
same face space and inner product as the pressure correction.

## 12. Pressure-jump representability

Let `J_h` be the scalar interface jump space and let `B_h` map a jump to a
face pressure-gradient correction. The affine pressure-gradient route has the
form

```text
G_Gamma(p; j)_f = G(p)_f - B_h(j)_f.
```

A variational capillary force `F_cap` is exactly representable by a scalar jump
if there exists `j_h in J_h` such that

```text
B_h(j_h) = F_cap.
```

If exact equality is too strong, the minimal energy requirement for the actual
velocity is

```text
<B_h(j_h), U_f>_F = <F_cap, U_f>_F.
```

For all admissible face velocities, this again implies equality in the
work-dual subspace. If `F_cap` has components outside the pressure-jump range,
then a scalar jump alone cannot represent the full variational force. The
solver must then either:

```text
1. enlarge the jump/interface-stress space;
2. add a separate projection-native face force for the orthogonal residual;
3. change the discrete geometry so F_cap lies in range(B_h).
```

The current pressure-jump route should therefore be audited by the residual

```text
R_jump(U) = <B_h(j_h) - F_cap, U>_F.
```

The residual must be small in the actual corrected face velocity and in a
basis of admissible test velocities.

## 13. Complete one-step theorem

Let a full step be decomposed as

```text
q^n --A_h--> q^- --T_h(U_f)--> q^{n+1}.
```

Assume:

1. `S_h(q)` is the sole discrete surface-energy source of truth.
2. The adaptation map satisfies the interface-energy GCL:

   ```text
   S_h(q^-) = S_h(q^n).
   ```

3. The transport substep admits a discrete gradient and kinematic operator:

   ```text
   S_h(q^{n+1}) - S_h(q^-)
     = Gbar_q [q^{n+1} - q^-],
   q^{n+1} - q^- = Delta t Kbar_h U_f.
   ```

4. The capillary face force is

   ```text
   F_cap = - Kbar_h^* Gbar_q.
   ```

5. The pressure-jump implementation realizes the same face work:

   ```text
   <B_h(j_h), U_f>_F = <F_cap, U_f>_F.
   ```

Then

```text
S_h(q^{n+1}) - S_h(q^n)
  + Delta t <B_h(j_h), U_f>_F = 0.
```

This is the closed discrete variational principle for capillary pressure work
on a dynamic fitted grid.

If viscosity is included and the viscous operator is negative semidefinite in
the kinetic-energy inner product, the total mechanical energy satisfies

```text
Delta E_kin + Delta S_h
  = - Delta t D_visc
    + splitting/PPE residuals,
```

where `D_visc >= 0`. Any capillary residual must be reported separately; it
must not be hidden by artificial high-frequency dissipation.

## 14. Residual taxonomy

The full residual for one step is

```text
R_total
  = S_h(q^{n+1}) - S_h(q^n)
    + Delta t <B_h(j_h), U_f>_F.
```

For diagnosis it should be decomposed into:

```text
R_A
  = S_h(q^-) - S_h(q^n)
```

adaptation/remap energy error;

```text
R_DG
  = S_h(q^{n+1}) - S_h(q^-)
    - Gbar_q[q^{n+1} - q^-]
```

discrete-gradient chain-rule error;

```text
R_K
  = Gbar_q[q^{n+1} - q^-]
    - Delta t <Kbar_h^* Gbar_q, U_f>_F
```

transport-adjoint error;

```text
R_J
  = Delta t <B_h(j_h) - F_cap, U_f>_F
```

pressure-jump representability/projection error.

Thus

```text
R_total = R_A + R_DG + R_K + R_J.
```

This decomposition turns the vague claim "surface tension is unstable" into
four falsifiable mathematical defects.

## 15. Hypothesis matrix for the N64 failure

### H1: missing ALE geometric work

If `R_A` or the `X` component of `R_DG` grows before kinetic blow-up, the root
cause is dynamic fitted-grid energy injection:

```text
Gbar_X[Delta X] is not closed.
```

This is the leading hypothesis because short fixed-grid-like gates are stable
while long dynamic fitted-grid runs fail late.

### H2: physical transport adjoint mismatch

If `R_K` dominates, the pressure jump is using an approximate transport
adjoint that does not match TVD-RK3, face interpolation, or the mass/profile
correction. The fix is not smoothing; it is reverse-mode construction of the
actual update map's adjoint.

### H3: scalar jump range deficiency

If `R_J` dominates, the variational face force cannot be represented by the
current scalar affine jump on the chosen cut-face space. The remedy is an
interface-stress space or face-force residual that is still projection-native
and work-equivalent.

### H4: non-smooth cut-cell branch work

If residual spikes correlate with changes in cut-face count, four-crossing
cells, or connected components, the P2 trace energy branch itself is injecting
finite-step work. The remedy is a branch-continuous finite-step energy rule or
event splitting.

### H5: PPE/kinetic inner-product mismatch

If capillary residuals are small but kinetic energy still grows incorrectly,
the problem moves to the pressure/velocity coupling: the face work used in the
capillary theorem is not the same work done by the actual projection/corrector.

### H6: real under-resolution after energy closure

Only after `R_A`, `R_DG`, `R_K`, and `R_J` are controlled should spatial
under-resolution be blamed. Under-resolution then appears as a convergent
resolution study issue, not as unexplained nonphysical energy creation.

## 16. Diagnostic gates

The following gates must be run before a long one-period production run:

### 16.1 Static-grid variational gate

Run the same P2 discrete-gradient pressure-jump route with `X` fixed. Require:

```text
|R_DG_psi| / max(|Delta S|, S_scale) << 1,
|R_K|      / max(|Delta S|, S_scale) small,
|R_J|      / max(|Delta S|, S_scale) small.
```

If this fails, the dynamic-grid theory is irrelevant; the fixed-grid capillary
route is not closed.

### 16.2 Pure adaptation gate

Apply one grid rebuild/remap with `U_f = 0`. Require either:

```text
S_h(q^-) - S_h(q^n) = 0
```

or record the nonzero value as `R_A`. If `R_A` is systematic, dynamic grid
adaptation is a capillary energy source.

### 16.3 Dynamic-grid ALE gate

Run a short dynamic fitted-grid step and report:

```text
R_A, R_DG_psi, R_DG_X, R_K, R_J, R_total.
```

The first residual to grow determines the root cause.

### 16.4 Spectral interface gate

Extract `r(theta)` from `Gamma_h` and monitor low and high Fourier modes:

```text
E_low  = sum_{m <= 3} |r_m|^2,
E_high = sum_{m >= 4} |r_m|^2.
```

A rise in `E_high` following a rise in `R_A` or `R_K` supports the
energy-injection hypothesis.

### 16.5 Pressure-jump range gate

Test representative face velocities `U_test` and measure:

```text
<B_h(j_h) - F_cap, U_test>_F.
```

If the residual is small only for the realized velocity but large for nearby
admissible velocities, the method is step-specific rather than operator-stable.

## 17. Implementation contract

The production implementation must follow these contracts.

### 17.1 Geometry SSoT

All capillary geometry must derive from

```text
S_h(psi, X)
```

not from an independently computed curvature field. Curvature can be reported
as a diagnostic or recovered derivative, but it is not the primary force
definition.

### 17.2 Full-state discrete gradient

The discrete-gradient API must support:

```text
input:  psi0, X0, psi1, X1, sigma
output: Gbar_psi, Gbar_X, Delta S, chain-rule residual
```

The fixed-grid specialization is obtained by setting `X1 = X0`, not by
changing the mathematical object.

### 17.3 Transport/remap adjoint

The capillary force API must accept the actual transport/remap operator:

```text
F_cap = - Kbar_h^*(Gbar_psi, Gbar_X).
```

For staged time integration, `Kbar_h^*` must be the adjoint of the stage
composition, not a heuristic final-state flux.

### 17.4 Pressure-jump projection

The jump solver must solve or project:

```text
B_h(j_h) ~= F_cap
```

in the face-work metric. The residual must be exposed as a diagnostic.

### 17.5 Remap accounting

Any grid rebuild, interpolation, mass correction, or profile correction must
declare one of:

```text
energy_preserving_remap,
reported_numerical_work,
not_part_of_capillary_step.
```

Silent changes to `S_h` are forbidden.

## 18. What this theory forbids

This theory rules out several tempting but invalid "fixes" as primary
solutions:

- damping chosen to erase high-frequency modes,
- hyperviscosity used to hide capillary energy injection,
- curvature caps,
- smoothing the interface until residuals disappear,
- reducing CFL as a substitute for work closure,
- replacing P2 geometry with a lower-order geometry because it is quieter,
- changing material parameters to mask the residual.

Such tools may be used as diagnostics only when their effect is explicitly
separated from the capillary work identity. They cannot certify correctness.

## 19. Minimal path to a correct algorithm

The shortest theory-valid path is:

1. Prove and implement the fixed-grid identity:

   ```text
   S_h(psi^{n+1}, X) - S_h(psi^n, X)
     + Delta t <B_h(j_h), U_f>_F = 0.
   ```

2. Add the pure adaptation gate:

   ```text
   S_h(A_h(q)) - S_h(q).
   ```

3. If pure adaptation is not energy preserving, either redesign `A_h` or carry
   its numerical work explicitly.

4. Extend the discrete gradient to full state:

   ```text
   Gbar_q = (Gbar_psi, Gbar_X).
   ```

5. Build the actual transport/remap adjoint:

   ```text
   F_cap = -Kbar_h^*Gbar_q.
   ```

6. Project `F_cap` into the affine pressure-jump space and report `R_J`.

7. Run the one-period problem only after the short gates show bounded
   `R_total` and no systematic high-mode energy injection.

## 20. Relation to curvature and implicit solves

Curvature is still physically meaningful:

```text
delta S = - sigma ∫_Gamma kappa n · delta x ds.
```

But in the discrete scheme, curvature is secondary. It is a representation of
the surface-energy derivative after the discrete energy and inner product have
been chosen. A CCD or implicit curvature solve can be useful if it computes a
component of `grad_q S_h` accurately. It is not sufficient if the resulting
force is not the adjoint pullback of the actual transport/remap map.

Therefore the correct order is:

```text
S_h(psi, X)
  -> finite-step discrete gradient
  -> actual transport/remap adjoint
  -> pressure-jump/face-work representation
  -> energy residual gate.
```

The incorrect order is:

```text
compute kappa_h
  -> form sigma kappa_h n_h delta_h
  -> hope that pressure work matches Delta S_h.
```

The second route may be high-order accurate on smooth manufactured fields yet
still fail the nonlinear finite-step energy identity.

## 21. Main conclusion

The discrete variational principle is closed when, and only when, the following
single statement is true for the actual numerical step:

```text
S_h(q^{n+1}) - S_h(q^n)
  + Delta t <B_h(j_h), U_f>_F = 0,
q = (psi, X).
```

Everything else is subordinate:

- the P2 trace defines `S_h`,
- the ALE discrete gradient enforces the finite-step chain rule,
- the transport/remap adjoint maps geometry covectors to face work,
- the affine jump represents that face work in the pressure solve,
- the diagnostic residuals identify which part of the theorem fails.

The most plausible explanation for the N64 one-period failure is that the
current P2 route improved the fixed-grid `psi` part of this theorem but left
the dynamic fitted-grid `X`/remap part open. Completing the theory therefore
requires `Gbar_X`, an interface-energy GCL for remap/adaptation, and a
pressure-work operator built from the adjoint of the actual update map.

