# CHK-RA-CH14-ENDPOINT-POLICY-001

## Question

Which production policy is theoretically appropriate after identifying the
remaining nonzero Hodge norm?

```text
A. Keep the current conservative face-psi transport endpoint and use its VJP
   as the capillary cochain.
B. Change interface transport itself to the trace-vertex endpoint C_K and use
   the trace-vertex VJP.
```

The decision must be made from physics and mathematics, not from convenience.
The forbidden alternatives remain damping, CFL tuning, smoothing, curvature
caps, fallback operators, benchmark branches, blanket projection, or
QP-as-physics.

## Principle

The discrete capillary law is a variational coupling, not an isolated force
formula.  If the interface degrees of freedom are updated by a map

```text
q_t = T(q) u_f,
```

then the capillary acceleration must be the Riesz pullback of the same map:

```text
s = -M_f^{-1} T(q)^T dS_h(q)^T.
```

For a trace-primary state with trace map

```text
z_t = C_K u_f,
```

the corresponding law is instead

```text
s_K = -M_f^{-1} C_K^T d_z S_h(z)^T.
```

Either theorem can be correct, but mixing `T` for transport and `C_K^T` for
force is not a physical discretization.  It breaks the discrete virtual-work
identity.

## Hypotheses

| ID | Hypothesis | Verification | Verdict |
|---|---|---|---|
| H01 | Trace-vertex force is best because continuum capillarity is a sharp-interface geometry law. | True at continuum level, but only if the trace is the evolved state. | conditional |
| H02 | Conservative-endpoint force is best for the current solver because the actual evolved state is `psi`. | Riesz work residual against actual conservative endpoint is roundoff. | supported |
| H03 | Trace-vertex force can be used with current conservative transport because both converge to the same continuum motion. | Work residual remains `O(1e-1)` and endpoint velocity mismatch remains `O(1)` in tested N16--N128 probes. | falsified for current N32 use |
| H04 | Conservative endpoint is unacceptable because it is profile/gauge sensitive. | Hodge ratio changes with interface thickness. | supported as a defect, not enough to justify endpoint mixing |
| H05 | Trace endpoint eliminates profile/gauge dependence. | It depends mainly on trace geometry and `C_K`, less on profile thickness. | supported |
| H06 | Trace endpoint requires a new transport/retraction theorem for the full CLS field. | Moving only trace vertices does not update the scalar state, diffuse mass, profile, or reinit ledger. | supported |
| H07 | Current no-reinit transport already uses conservative face-psi flux, so endpoint consistency has priority over geometric taste. | `advance_with_face_velocity` applies `-D_f(P_f psi u_f)` by TVD-RK3. | supported |
| H08 | A discrete static condition should be shape-name based. | `TraceStaticCriticality` gives a shape-free `dS_h in span(dV_m)` gate. | falsified |
| H09 | The proper solution is to make force and transport share one endpoint theorem. | Direct consequence of discrete Lagrange-d'Alembert / virtual work. | supported |
| H10 | CCD/FCCD/UCCD coupling favors the current conservative endpoint for near-production. | Conservative endpoint uses FCCD face interpolation/divergence and the same face-native pressure complex; current trace endpoint uses simple face-to-node reconstruction plus P1 trace and is not yet a compact/mimetic CCD-family trace map. | supported |

## Measurements

### Work Identities

Using the trace-surface cochain as a probe velocity:

| case | N | conservative endpoint work residual | trace self-residual | trace force vs actual conservative endpoint |
|---|---:|---:|---:|---:|
| circle | 16 | `8.494e-17` | `0.000e+00` | `5.106e-01` |
| circle | 32 | `8.629e-17` | `1.055e-16` | `2.414e-01` |
| circle | 64 | `7.752e-17` | `2.120e-16` | `1.880e-01` |
| ellipse | 16 | `4.357e-16` | `2.213e-16` | `6.363e-01` |
| ellipse | 32 | `8.994e-17` | `1.032e-16` | `2.709e-01` |
| ellipse | 64 | `8.449e-17` | `1.059e-16` | `2.295e-01` |

Interpretation: each cochain is internally valid for its own endpoint, but the
trace-vertex cochain is not the adjoint of the current conservative `psi`
transport endpoint.

### Endpoint Velocity Mismatch

Using a streamfunction-derived face velocity with discrete divergence at
roundoff:

| case | N | relative trace-velocity mismatch | `||D_f u_f||_inf` |
|---|---:|---:|---:|
| circle | 16 | `5.428345e-01` | `3.996803e-15` |
| circle | 32 | `8.455652e-01` | `7.105427e-15` |
| circle | 64 | `1.177267e+00` | `1.820766e-14` |
| circle | 128 | `1.427231e+00` | `3.819167e-14` |
| ellipse | 16 | `9.672546e-01` | `3.996803e-15` |
| ellipse | 32 | `1.461963e+00` | `7.105427e-15` |
| ellipse | 64 | `1.410831e+00` | `1.820766e-14` |
| ellipse | 128 | `1.591989e+00` | `3.819167e-14` |

This rejects the idea that `C_K` can be silently substituted while the scalar
transport remains conservative face-`psi` transport.

### Profile Sensitivity

At N32:

| case | eps factor | conservative Hodge ratio | trace Hodge ratio |
|---|---:|---:|---:|
| circle | `0.75` | `7.005624e-01` | `1.198112e-01` |
| circle | `1.50` | `2.700926e-01` | `3.611950e-02` |
| circle | `3.00` | `1.355437e-01` | `1.855209e-02` |
| ellipse | `0.75` | `8.191481e-01` | `1.349164e-01` |
| ellipse | `1.50` | `7.190677e-01` | `1.035021e-01` |
| ellipse | `3.00` | `7.116038e-01` | `1.022948e-01` |

This is the strongest argument against treating the conservative endpoint as a
final geometric ideal.  It is, however, not an argument for mixing endpoints.
It says that if profile/gauge sensitivity is unacceptable, the whole interface
representation must become trace-primary, including transport and projection.

## CCD/FCCD/UCCD Coupling

This criterion strengthens the near-production choice.  The current solver is
not an abstract interface mover; it is a CCD-family discretization stack:

```text
interface transport:  FCCD face_value + FCCD face_divergence
pressure projection:  FCCD face divergence/gradient and affine face history
momentum convection:  UCCD6 skew/upwind compact operator
viscosity:            CCD implicit operator
```

The conservative endpoint lives directly in that stack:

```text
T_f(q)u_f = -D_f(P_f q u_f),
```

where `P_f` and `D_f` are the FCCD face operators already used by
`advance_with_face_velocity`, PPE RHS construction, and face-native correction
history.  Its VJP therefore preserves the same face degrees of freedom and the
same divergence complex that couples to UCCD6/CCD momentum through the
projected face state.

The current trace endpoint is not yet such a CCD-family endpoint.  The present
proof candidate reconstructs nodal vectors from face components by averaging
and then P1-interpolates to trace vertices.  That is useful as a theorem probe,
but it is not an FCCD compact reconstruction, not a UCCD6-compatible momentum
flux map, and not a mimetic trace operator with a proven transpose in the same
face complex.  Using it as a force while keeping FCCD transport and UCCD6
momentum would introduce a new cross-family coupling error.

Therefore the CCD/FCCD/UCCD criterion does not merely favor the conservative
endpoint by implementation convenience.  It favors it by operator coherence:
near-production capillarity should be a VJP of the same FCCD endpoint that
advects the scalar and supplies the face-native projection state.

The trace endpoint remains a legitimate long-form research direction only
after defining a CCD-family trace map, for example a direct FCCD face-to-trace
interpolation or a mimetic/Whitney/RT-style face trace with an explicit
transpose and compatibility gates against UCCD6 projected momentum.

## Decision

For the current LevelSet/CLS solver, the appropriate production policy is:

```text
Use the conservative face-psi transport endpoint VJP as the capillary cochain.
```

This is the only option that preserves the discrete virtual-work identity for
the state that the solver actually advances today.  It is also the only option
that is already coherent with the CCD/FCCD/UCCD operator stack: FCCD scalar
transport, FCCD pressure projection, UCCD6 momentum prediction, and CCD
viscosity all continue to exchange data through the face-native projected
state.  It also keeps reinit work separable through the existing pre-reinit
endpoint ledger.

The trace-vertex endpoint is the more geometric sharp-interface theorem, but
it is not appropriate as a drop-in force source while transport remains
conservative `psi` transport.  It becomes appropriate only after a deliberate
trace-primary redesign:

```text
state variable includes the trace geometry,
transport moves trace vertices by C_K u_f,
the scalar CLS field is reconstructed as a projection/retraction with its own
mass/profile/energy ledger,
capillary force uses -M_f^{-1} C_K^T d_z S_h.
```

Until that redesign exists, using trace force with conservative transport is a
theorem mismatch.  The nonzero Hodge norm would then be hidden, not solved.

## Implementation Consequence

The next production implementation should not use the current trace-Riesz
cochain as a force while retaining the existing transport.  Instead it should
promote the already verified conservative endpoint object:

```text
T_f(q)u_f = -D_f(P_f q u_f)
s_f       = -M_f^{-1} T_f(q)^T dS_h(q)^T
B_f       =  M_f^{-1} T_f(q)^T dV_h(q)^T
h_f       = component/pressure constrained Hodge quotient of s_f
```

Acceptance gates:

- fixed-stratum virtual work for the actual pre-reinit transport endpoint;
- component-volume Riesz identity in the same endpoint;
- static-criticality diagnostic reported separately from Hodge projection;
- profile/gauge sensitivity measured, not hidden;
- reinit endpoint work excluded from capillary work;
- dynamic nonconstant modes retain nonzero drive.

## Verdict

The conservative endpoint VJP is the correct near production theorem for the
current solver.  The trace-vertex endpoint is a valid future theorem only if
transport, state representation, and CCD-family trace coupling are changed
together.  Choosing trace force alone would repeat the original error in a
subtler form: replacing the actual force law by a mathematically elegant
cochain attached to a different dynamical system and a different operator
family.

[SOLID-X] Theory/decision artifact only; no production source/config/result
changed, no tested implementation deleted, no FD/WENO/PPE fallback, damping,
CFL workaround, curvature cap, smoothing, benchmark branch, blanket projection,
or QP-as-physics route introduced.
