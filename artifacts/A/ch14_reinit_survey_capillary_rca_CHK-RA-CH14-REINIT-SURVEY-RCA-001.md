# CHK-RA-CH14-REINIT-SURVEY-RCA-001 - Capillary/Reinit RCA after latest main survey

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Question

Latest `main` adds the reinitialization-free LS/CLS survey
`CHK-RA-CLS-001`.  Use that survey and identify the current ch14 droplet
problem by physics/math hypotheses, not by tuning.

The current state is:

1. the original `range_projected` zero-drive failure is fixed;
2. the `component_hodge_augmented` route moves the oscillating droplet but is
   not a theorem-grade capillary force;
3. the newer `closed_interface_riesz` route removes the old zero-drive symptom
   but worsens the N32/T1 static-current gate relative to the component route;
4. Ridge-Eikonal reinit still changes the interface trace/profile as a
   nonphysical representation leg.

## Theory Frame

For any closed interface component, not only circles or ellipses, the force must
be the face-space Riesz representative of surface-energy virtual work:

```text
<M_f c_sigma, u_f> = -d(sigma S_h)[T_h u_f]
```

The pressure and component reactions are constraints, not force replacement:

```text
R = A_f G_f
B = M_f^{-1} T_h^T dV_h^T
K = ker(D_f) intersection ker(B^T M_f)
h = c_sigma - X (X^T M_f X)^+ X^T M_f c_sigma,  X=[R B]
```

The production corrector must receive the full physical cochain and the same
cochain must appear in the PPE source/corrector pairing.  Replacing `c_sigma`
by a pressure-range representative is mathematically a projection of the force
away from the physical quotient.

The reinit survey adds a second theorem constraint.  Reinitialization-free does
not mean `reinit_every=0`.  A valid route must either put profile control into
the physical-time conservative flux, or change the carrier/geometry split.  Any
post-transport profile projection

```text
q^n -> q_T      physical transport
q_T -> q^{n+1} profile/representation repair
```

that changes trace or surface energy must be measured as profile-control work,
not mixed into capillary work.

## Evidence Used

### Existing direct observations

| Case | Observation | Meaning |
|---|---|---|
| old `range_projected` N32/T1 | KE `~1e-37`, velocity Linf `3.57e-19` | old production force was algebraically deleted |
| component route static N32/T1 | KE last `5.284e-09`, Hodge L2 max `2.815e-04` | component reaction removes most static pressure mode |
| component route oscillating N32/T1 | KE last `3.644e-04`, signed D `7.618e-02 -> 4.335e-02` | nonzero drive exists, but not final physics |
| trace-Riesz static N32/T1 | KE last `8.882e-07`, Hodge L2 max `6.397e-03` | trace route is stable but significantly less static-balanced |
| trace-Riesz oscillating N32/T1 | KE last `9.657e-05`, signed D `7.618e-02 -> 4.349e-02` | zero-drive is removed, but drive is weaker than component route |
| oscillating reinit diagnostics | max `Delta S_reinit=1.271e-02`, max `linf=1.803e-01`, zero-crossing change count `144` | reinit/profile repair changes the represented interface |
| endpoint smoke from previous ledger | `max|q_T-q^n|=6.44e-07`, `max|q^{n+1}-q_T|=1.78e-01` | apparent motion can be dominated by profile projection |

### Code facts

The current trace-Riesz implementation uses a reconstructed nodal P1 trace
velocity map:

```text
src/twophase/coupling/closed_interface_trace_velocity.py:24-56
```

It then pulls surface and component vertex covectors back through that map:

```text
src/twophase/coupling/closed_interface_trace_riesz.py:96-125
```

This proves adjointness for the chosen map `C_K`, but it does not prove that
`C_K` is the derivative of the actual FCCD/RK3 conservative transport endpoint
`q_T`.

The trace route also builds `M_f` with arithmetic face density:

```text
src/twophase/coupling/closed_interface_riesz.py:111-123
```

while the production pressure-jump Hodge diagnostics use the PPE-consistent
`measure / alpha_f` weights, including affine cut-face inverse density:

```text
src/twophase/simulation/interface_projection_diagnostics.py:512-573
```

The mismatch is not the largest measured error by itself, but it violates the
same-`M_f`, same-`A_f`, same-`D_f` theorem.  A probe on the N32 initial fields
found cut-face weight ratios of about `0.886..1.050` for the static droplet and
`0.899..1.113` for the oscillating droplet.

The force geometry is intentionally taken from the pre-reinit endpoint:

```text
src/twophase/simulation/ns_pipeline.py:803-810
src/twophase/simulation/ns_step_services.py:237-243
```

but the cochain is paired with `state.rho`:

```text
src/twophase/simulation/ns_step_services.py:896-902
src/twophase/simulation/ns_pipeline.py:865-885
```

For reinit-on cases this can pair pre-reinit geometry with post-reinit material
fields.  Static no-reinit does not suffer this particular mismatch.

Scalar Young-Laplace double counting is not the current cause; the closed
interface source sets interface sigma to zero for the scalar pressure jump:

```text
src/twophase/simulation/ns_step_services.py:1159-1167
```

## Hypothesis Matrix

| ID | Hypothesis | Verification | Verdict |
|---|---|---|---|
| H01 | The old problem was simply weak oscillation | KE `~1e-37`, velocity `3.57e-19` under old `range_projected` | falsified; it was zero drive |
| H02 | `range_projected` is a valid production force | Hodge theorem gives `a_f=A_fG_fp-c`; replacing `c` by `Pi_R c` makes release acceleration zero | falsified |
| H03 | Using `none` is the final fix | `none` moves the droplet but lacks proof that raw curvature is `T_h^*dS_h` | falsified |
| H04 | Component reaction is unnecessary | static `none` KE was `5.026e-06`, component route `5.284e-09` | falsified |
| H05 | Component projection over-removes the dynamic mode | no-reinit `none` and component routes had the same early `omega~0.14017` | falsified |
| H06 | Component route is final because static N32 is quiet | no-reinit phase has only about 70% Rayleigh stiffness and long-time damping | falsified |
| H07 | Rayleigh-Lamb reference is wrong | reinit-on and no-reinit shift phase in opposite directions | falsified as sole cause |
| H08 | Physical viscosity explains damping | observed fitted damping is orders above water-air viscosity scaling | falsified |
| H09 | CFL/time-step tuning explains phase | `dt*omega_ref~1.6e-3`, but early stiffness error is O(30%) | falsified |
| H10 | PPE residual dominates | prior PPE residuals are around solver tolerance and sign of errors differs by reinit | falsified |
| H11 | Grid rebuild/remap causes early under-stiffness | static-grid no-reinit matched dynamic-grid no-reinit through T4 | falsified for early cause |
| H12 | Scalar pressure jump double-counts trace-Riesz force | code zeros scalar sigma for `closed_interface_riesz` | falsified |
| H13 | The reported deformation metric alone can diagnose physics | reinit can change D while KE is zero or nearly zero | falsified |
| H14 | Circle/ellipse recognition is an acceptable static/dynamic classifier | user constraint and theory require arbitrary nonconstant closed-interface modes | falsified |
| H15 | Reinit is harmless if volume is conserved | max `Delta S_reinit=1.271e-02`, max zero-level displacement `9.72e-03` | falsified |
| H16 | Turning reinit off is the survey-backed solution | survey says successful routes absorb profile control into physical-time flux or carrier split | falsified |
| H17 | Reinit is the sole current problem | static no-reinit trace-Riesz still has Hodge L2 `6.397e-03` and KE `8.882e-07` | falsified |
| H18 | Trace-Riesz is correct because its VJP test passes | the test proves `C_K^T` adjointness for P1 trace velocity, not `T_h^*` for actual FCCD transport | falsified |
| H19 | P1 reconstructed trace velocity is the true transport derivative | code shows `C_K` is reconstructed nodal interpolation, while physical transport is conservative FCCD/RK3 | supported as a root defect |
| H20 | Trace surface derivative is not static-exact on sampled closed components | static trace-Riesz Hodge L2 `6.397e-03`, much larger than component route `2.815e-04` | supported |
| H21 | The trace component reaction is not the correct pressure/component reaction space yet | trace static component-Hodge norm `1.42e-01`, denominator `2.02e-02`, residual still `4.69e-03` | supported |
| H22 | Trace-Riesz metric differs from production pressure metric | trace uses arithmetic rho weights; production diagnostics use affine `measure/alpha_f` weights | supported, likely secondary |
| H23 | Pre-reinit geometry is paired with post-reinit material fields | code uses `psi_transport_endpoint` for geometry and `state.rho` for weights/PPE | supported for reinit-on |
| H24 | Density/inertia is globally mis-scaled | static, dynamic, and reinit effects have different signs/magnitudes | not primary |
| H25 | High-mode contamination is primary | early `n=2` acceleration is already wrong before long-time distortion | secondary |
| H26 | Transport numerical diffusion explains late no-reinit damping | no-reinit T20 damping remains after early force error is isolated | plausible secondary |
| H27 | Topology/stratum changes during reinit matter | zero-crossing change count reaches `144` in N32/T1 reinit-on runs | supported for reinit-on |
| H28 | Existing static gate should demand roundoff zero for sampled continuum circles | sampled circle is not guaranteed a discrete constrained critical trace | falsified; use convergence/discrete-critical gates |
| H29 | A scalar frequency rescale can repair all observations | static current, no-reinit under-stiffness, and reinit-on over-stiffness cannot be one scalar | falsified |
| H30 | Damping/caps/smoothing/CFL changes are valid fixes | they do not prove `c_sigma=T_h^*dS_h` or separate `Delta S_profile` | rejected by theorem |

## Cause Identification

The current problem is not one bug but two coupled theorem failures.

Primary force-side cause:

```text
The capillary cochain used by production is still not the surface-energy
transport-adjoint Riesz representative for the actual physical transport
endpoint and the actual pressure/corrector metric.
```

For the component route this appears as good static cancellation but wrong
dynamic stiffness.  For the trace-Riesz route it appears more honestly: the
chosen `C_K` is an internally adjoint P1 trace velocity map, but not yet the
VJP of the actual FCCD/RK3 transport endpoint.  Therefore it can pass local
adjoint tests and still fail the static Hodge quotient.

Secondary representation-side cause:

```text
Ridge-Eikonal reinit/profile repair is a separate representation projection
that can move the trace and surface energy.  The latest survey says this is not
removed by disabling reinit; it must either become a physical-time conservative
profile-control flux or be kept as a separate defect ledger.
```

This explains why reinit-on and no-reinit phase behavior diverge in opposite
directions.  The force can be under-stiff without reinit, while reinit can still
inject or remove apparent surface energy after the physical transport leg.

## What Is Now Ruled Out

Do not fix this by:

```text
range projection of the production force,
raw `capillary_range_projection:none` as final physics,
damping,
CFL reduction,
curvature caps,
curvature smoothing,
FD/WENO/PPE fallback,
benchmark-name branches,
scalar Rayleigh rescaling,
turning reinit/profile repair into unlabelled capillary work.
```

Those may improve a plot while leaving the failed virtual-work identity
unproved.

## Required Next Theorem Work

1. Define `T_h` as the derivative of the actual physical transport endpoint
   `q^n -> q_T` with the same FCCD face flux, time integrator, boundary
   handling, and face projection used in production.
2. Build `c_sigma=-M_f^{-1}T_h^T d(sigma S_h)^T` and
   `B=M_f^{-1}T_h^T dV_h^T` with the production `M_f=A_f^{-1}` metric,
   including affine cut-face coefficients.
3. Project with the actual `X=[A_fG_f B]` normal equations or a proven
   equivalent Schur form.  The equivalence must use the same `M_f,D_f,A_f,G_f`.
4. For reinit-on routes, compute capillary work only on `q_T`; report
   `Delta S_profile_control`, `Delta V_profile_control`, trace displacement,
   and stratum changes for `q_T -> q^{n+1}`.
5. If pursuing the survey route, implement profile control as a conservative
   physical-time face flux, not as a hidden pseudo-time projection.  The first
   candidate is monolithic conservative anti-diffusion CLS; the second is a
   THINC/CSLS mass carrier with LS geometry.

## Verification Performed In This Session

Local deterministic probes on existing N32 result NPZs:

```text
static_trace:     KE last 8.881600e-07, Hodge L2 max 6.397429e-03
osc_trace:        KE last 9.657244e-05, Hodge L2 max 2.012734e-02
static_component: KE last 5.284015e-09, Hodge L2 max 2.814614e-04
osc_component:    KE last 3.643971e-04, Hodge L2 max 4.477470e-02
```

Reinit diagnostics from N32/T1 oscillating runs:

```text
max |Delta S_reinit|      1.27103e-02
max reinit Linf delta     1.80338e-01
max zero-level movement   9.72e-03
zero-crossing changes     144
```

Cut-face metric probe on N32 initial snapshots:

```text
static trace weight ratio arithmetic/affine:      0.886 .. 1.050
oscillating trace weight ratio arithmetic/affine: 0.899 .. 1.113
```

Validation command:

```text
git diff --check
```

[SOLID-X] RCA/docs only; no production solver/config/experiment physics was
changed, no tested implementation was deleted, and no FD/WENO/PPE fallback,
damping, CFL workaround, curvature cap, smoothing, benchmark branch, blanket
`c -> Pi_R c`, or QP-as-physics path was introduced.
