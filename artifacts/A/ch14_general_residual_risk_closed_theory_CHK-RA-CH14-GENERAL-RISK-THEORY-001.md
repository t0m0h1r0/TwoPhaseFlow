# CHK-RA-CH14-GENERAL-RISK-THEORY-001

Date: 2026-05-07

Scope: deepen the general capillary residual theory by making remaining risks
part of the theorem.  The target remains a non-static-specific scheme:
declared equilibria must be quiet, noncritical modes must keep physical drive,
and residuals caused by endpoint/metric/constraint/operator mismatch must be
eliminated or fail closed.

## 1. Risk-Closed Principle

The earlier theory gives the desired physical drive:

```text
s      = -M_A^{-1} T_h^* dE_h,
B_i    =  M_A^{-1} T_h^* dC_i,
h      = s - G_A p - B mu,
D_f h  = 0,
B^T M_A h = 0.
```

The risk-closed refinement is:

```text
This formula is production-meaningful only if every symbol is the active
implementation object and the required adjoint/constraint identities pass.
```

If any symbol is substituted by a nearby diagnostic object, the theorem being
solved changes.  The correct behavior is not fallback.  It is fail-close or a
separately named experimental theorem.

## 2. Acceptance Predicate

At an endpoint `q_c`, the production theorem is admissible only if the
following predicates pass:

```text
A0 regularity:
  q_c lies on a regular stratum for E_h, C_h, and T_h.

A1 endpoint identity:
  force, material coefficients, pressure action, and corrector all use q_c
  or pass an endpoint-equivalence ledger.

A2 pressure adjointness:
  <G_A p,w>_{M_A} = <p,D_f w>_{W_p} to tolerance.

A3 energy VJP:
  dE_h[T_h u] + <s,u>_{M_A} = 0 to tolerance.

A4 constraint VJP:
  dC_i[T_h u] - <B_i,u>_{M_A} = 0 to tolerance.

A5 constraint rank:
  active B columns satisfy LICQ/rank gates after pressure quotient.

A6 saddle solve:
  D_f h = 0 and B^T M_A h = 0 to tolerance.

A7 sign power:
  dE_h[T_h h] + ||h||_{M_A}^2 = 0 to tolerance.

A8 CCD/FCCD/UCCD closure:
  the same projected face state carrying h is consumed by UCCD convection
  and CCD viscosity.

A9 auxiliary map ledger:
  reinit/remap/profile/grid rebuild work is either endpoint-equivalent,
  separately ledgered, or fail-closed.
```

Only if `A0` through `A9` pass may a nonzero `h` be interpreted as physical
drive and a zero `h` as a discrete equilibrium.

## 3. Risk Register

| Risk | Failure mode | Closure condition | Fail-close action |
|---|---|---|---|
| R1 endpoint mismatch | `s,B` are VJPs of `q_T`, while `rho,G_A,M_A` use post-reinit `q_R`. | Explicit endpoint label for every object; equivalence ledger below tolerance. | Reject production interpretation for that step. |
| R2 pressure metric ambiguity | `M_A` is guessed from kinetic mass, not induced by `pressure_fluxes`. | Randomized and structured adjoint probes pass for active `G_A,D_f,M_A`. | Do not run saddle as physical; report metric defect. |
| R3 non-positive face weights | cut-face or phase-separated coefficients produce zero/negative metric entries. | Active face set has positive metric on the velocity space being projected. | Remove inactive faces by theorem or fail closed. |
| R4 pressure range mismatch | diagnostic `M^{-1}D^T` range differs from actual affine `pressure_fluxes` range. | `G_A` is always `pressure_fluxes(... zero jump ...)` in gates and saddle. | No dense diagnostic range in production. |
| R5 component rank loss | volume/contact constraints become dependent after pressure quotient. | Schur matrix rank/condition passes with declared tolerance. | Drop only explicitly redundant constraints with certificate, or fail. |
| R6 topology/stratum change | marching-squares graph or component count changes under derivative probes. | Fixed-stratum gate passes for VJP/JVP and nonlinear solves. | Stop local theorem; switch stratum only via new theorem state. |
| R7 over-elimination | projection removes true dynamic capillary drive. | Non-equilibrium gates require measurable `h` and correct sign power. | Reject projection rule. |
| R8 under-elimination | scheme defects remain and appear as physical velocity rings. | Defect probes isolate endpoint/metric/corrector/auxiliary terms below budget. | Report defect; do not call it physical. |
| R9 corrector cochain split | PPE RHS uses `s-Bmu`, corrector recomputes a different cochain. | Stored `c_corrected` is passed identically to RHS and `pressure_fluxes`. | Runtime error. |
| R10 UCCD path split | convection sees a velocity not carrying the same projected face state. | projected face state identity check passes. | Runtime error or diagnostic fail-close. |
| R11 CCD path split | viscosity reconstructs from a different velocity complex. | CCD receives velocity reconstructed from the same projected faces. | Diagnostic fail-close. |
| R12 finite-step drift | differential work theorem passes but step energy drifts. | Discrete-gradient identity or declared time-discretization error budget. | Do not claim exact energy exchange. |
| R13 auxiliary work mixing | reinit/remap/profile changes are counted as capillary work. | auxiliary ledger reports separate `Delta E`, `Delta C`, and endpoint defect. | Do not use post-auxiliary metrics as capillary validation. |
| R14 nonconservative physics | dissipative or forced terms are forced into `E_h`. | Each nonconservative term has separate forcing/dissipation theorem. | Exclude from capillary residual theorem. |
| R15 GPU/CPU divergence | GPU hot path differs from CPU diagnostic formulas. | backend parity tests for `dE,dC,T^*,B,s,h` pass within tolerance. | Keep CPU path diagnostic only; fail GPU production if unproven. |
| R16 solver/gauge residual | pressure or saddle solves leave residual comparable to capillary signal. | gauge, RHS compatibility, and solve residuals below force budget. | fail-close or refine solver; no force clipping. |

## 4. Endpoint-Material Ledger

The riskiest hidden mismatch is using one interface for geometry and another
for material coefficients.  Define

```text
q_T  physical transport endpoint before reinit,
q_R  post-reinit/profile/remap state.
```

The theorem allows material coefficients from `q_R` only if a ledger proves

```text
||q_R - q_T||,
|E_h(q_R)-E_h(q_T)|,
|C_h(q_R)-C_h(q_T)|,
||G_A(q_R)-G_A(q_T)||_probe,
||M_A(q_R)-M_A(q_T)||_probe
```

are below declared tolerances.  Otherwise the capillary step must either build
`rho,G_A,M_A` from `q_T` or fail closed.

This closes a subtle loophole: a run may conserve volume and still inject a
velocity ring if the force is derived at `q_T` but pressure reactions are
computed with `q_R`.

## 5. Pressure-Adjoint Metric Risk

The active pressure action may include nonuniform geometry, phase-separated
coefficients, affine-jump corrections, boundary topology, and inactive faces.
Therefore the metric cannot be selected by preference.

Finite-dimensional test:

```text
epsilon_A(p,w) =
  |<G_Ap,w>_{M_A} - <p,D_fw>_{W_p}|
  / (||G_Ap||_{M_A} ||w||_{M_A} + ||p||_{W_p} ||D_fw||_{W_p} + eps).
```

Required probes:

```text
random p and w,
smooth Fourier-like p and w,
near-interface localized p and w,
divergence-free w,
component-reaction-like w,
boundary-touching w when walls exist.
```

If these do not pass, the Hodge complement `Z_A` is only algebraic, not an
energy-orthogonal pressure quotient.  Physical interpretation must stop there.

## 6. Constraint Rank and LICQ

For constraints `C_i`, define the pressure-quotient reaction columns

```text
z_i = Z_A(B_i).
```

The component/contact constraint saddle uses

```text
C_ij = B_i^T M_A z_j,
r_i  = B_i^T M_A z_s.
```

The risk is not only singularity.  Near-singularity means a small numerical
perturbation can decide which physical constraint reaction is removed.

Acceptance:

```text
rank(C) = declared active constraint count,
cond(C) <= condition budget,
||C mu - r|| / ||r|| <= solve budget,
B^T M_A h <= orthogonality budget.
```

If two constraints are physically redundant, redundancy must be detected and
recorded as a constraint-set reduction.  Silent pseudo-inversion is not a
physical decision.

## 7. Dynamic Preservation Risk

The strongest guard against over-elimination is a dynamic theorem gate.  For
any resolved noncritical perturbation,

```text
dE_h[T_h u] - sum_i mu_i dC_i[T_h u] != 0
```

for some admissible `u`, so the saddle drive must satisfy

```text
||h||_{M_A} > physical floor,
dE_h[T_h h] < 0.
```

This applies to oscillating droplets, non-elliptic perturbations, multipole
shape modes, and other systems.  If a residual-cleaning method makes all such
states quiet, it has proven itself wrong.

## 8. CCD/FCCD/UCCD Closure Risk

The theory must survive handoff to momentum:

```text
FCCD produces h on faces,
pressure projection returns projected face velocity,
UCCD convection consumes that face velocity,
CCD viscosity consumes the reconstructed velocity from the same face state.
```

Risk tests:

```text
FCCD closure:
  pressure_faces and capillary cochain are evaluated on the same face arrays.

UCCD closure:
  predictor/corrector face state entering UCCD equals stored projected faces.

CCD closure:
  nodal velocity used by viscosity reconstructs from stored projected faces.

history closure:
  affine pressure history subtracts/adds the same face cochain convention.
```

Any mismatch here can create residuals even when the capillary saddle is
mathematically correct.  Thus CCD/FCCD/UCCD closure is not a later integration
detail.  It is an acceptance predicate.

## 9. Auxiliary Map Risk

Reinit, remap, and fitted-grid rebuilds can improve representation while
breaking work accounting.  They must be treated as separate maps:

```text
R_h: q_T -> q_R.
```

Allowed categories:

```text
identity-equivalent:
  theorem object unchanged to tolerance.

projective:
  changes E_h or C_h but ledger records the change outside capillary work.

nonregular:
  changes topology/stratum; local theorem ends and production interpretation
  fails closed for that step.
```

This is where a general scheme avoids static-special handling: every system,
static or dynamic, must keep auxiliary maps out of capillary force work unless
equivalence is proven.

## 10. Implementation Readiness

The theory is implementable, but only in staged order:

```text
Stage 1 diagnostics only:
  M_A extraction/probes, pressure-adjointness, endpoint ledger,
  CCD/FCCD/UCCD closure, auxiliary ledger.

Stage 2 theorem cochain:
  build s and B with active M_A and T_h; no production force change until
  VJP gates pass.

Stage 3 saddle integration:
  solve coupled pressure/constraint reaction using G_A and c_corrected,
  verify sign power and dynamic preservation.

Stage 4 equilibrium constructors:
  for declared steady states, solve h=0 and C=C0 as initial-condition
  construction, not force correction.

Stage 5 finite-step refinement:
  introduce discrete gradients if exact stepwise energy accounting is needed.
```

Skipping Stage 1 is the main risk.  It would let a theorem-looking formula run
on the wrong metric, endpoint, or face state.

## 11. What Remains Unproven

The following are not yet closed:

```text
P1/P2 geometry choice:
  which E_h should be production SSoT for all target systems.

GPU VJP exactness:
  vectorized GPU formulas must be proven identical to the declared geometry.

nonregular events:
  breakup/merge/contact topology changes need a new stratum theorem.

finite-step energy:
  differential sign-power is not exact time-discrete conservation.

nonconservative physics:
  viscosity is handled by CCD momentum, not by this capillary energy theorem.

multi-constraint policies:
  contact angle, wall volume, or external constraints require rank policies.
```

These are real risks.  The theory handles them by refusing production
interpretation until their gates exist; it does not pretend they are solved.

## Verdict

Risk consideration strengthens the chosen direction rather than weakening it.
The only viable general residual scheme is a risk-closed variational saddle:

```text
active endpoint + pressure-adjoint metric + declared constraints
-> physical drive h
-> same FCCD face state
-> UCCD/CCD momentum path
```

It can eliminate scheme defects across static and dynamic systems because it
does not eliminate all Hodge content.  It eliminates only what fails to be a
pressure/constraint reaction or a proven variational drive.  The remaining
risks are not showstoppers, but they force the implementation order:
diagnostics and fail-close gates first, production force changes second.

[SOLID-X] Theory/risk closure only.  No production behavior changed; no tested
code deleted; no FD/WENO/PPE fallback, damping/CFL workaround, smoothing,
curvature cap, benchmark branch, blanket projection, or QP-as-physics path
introduced.
