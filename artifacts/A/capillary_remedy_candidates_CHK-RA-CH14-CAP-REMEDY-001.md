# CHK-RA-CH14-CAP-REMEDY-001 - Remedy Candidates for Closed-Interface Capillary Cochain Mismatch

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Problem Restatement

Previous RCA established:

```text
local cut-face B_Gamma(j) notin range(A_f G_f)
```

for curved closed interfaces.  The static-circle and oscillating-ellipse
experiments are only diagnostic probes.  They must not become branch conditions
or theoretical categories: a production method must handle arbitrary closed
interfaces, including nonconstant, high-frequency, non-elliptic, and poorly
parameterized curvature modes.

The current affine jump/FCCD complex is exact for compatible flat jumps, but
its local closed-interface cochain can contain a spurious Hodge component.
Production `range_projected` then removes that component by replacing the whole
cochain with its range part, which also deletes genuine capillary drive for any
noncritical shape.

The remedy must satisfy:

```text
G1 variational identity: face work equals -delta(sigma S_h - sum lambda_m V_m,h)
G2 equilibrium nullity:  P_h c = 0 exactly for discrete constrained critical shapes
G3 noncritical release:  P_h c != 0 for arbitrary noncritical closed-interface modes
G4 same complex:         same D_f, A_f, G_f and face metric as PPE/corrector
G5 component topology:   per-component constraints, not a global shape classifier
G6 no shortcuts:         no damping/CFL/caps/smoothing/FD/WENO/PPE fallback
G7 reinit separation:    do not mix Pi_h reinitialization work with capillary work
```

## Key Theorem For Selection

The shape-agnostic theorem is the constrained virtual-work statement.  For
interface configuration `q`, discrete surface energy `S_h(q)`, component
volumes `V_m,h(q)`, and face-transport map `T_h`, the capillary covector must
be

```text
c_sigma = T_h^* d_q [ sigma S_h(q) - sum_m lambda_m V_m,h(q) ].
```

The multipliers `lambda_m` are not recognized by asking whether the shape looks
like a circle or ellipse.  They are the discrete Lagrange multipliers selected
by the stationarity equation on each connected component.  The pressure
projection may absorb only the exact constraint-reaction part represented by
the same pressure complex.  The remaining Hodge component is physical
capillary acceleration if and only if it is the above virtual-work covector.

Thus a valid production cochain must derive all modes from one energy
functional.  This is the narrow path between the two known failures:

```text
raw local jump           -> can move, but may include nonvariational Hodge work
blanket range projection -> removes all drive, including physical modes
```

## Candidate List And Theory Verdicts

| ID | Idea | Theory verdict |
|---|---|---|
| R01 | Set `capillary_range_projection:none`. | Reject. Restores motion but applies the static-circle parasitic Hodge residual. |
| R02 | Keep `range_projected` only for static droplet YAMLs and `none` for oscillating YAMLs. | Reject. Benchmark-name branch, not physics. |
| R03 | Damping, smaller CFL, curvature cap, or smoothing. | Reject. These hide energy/cochain errors and violate the problem contract. |
| R04 | FD/WENO/PPE fallback. | Reject. Violates project algorithm fidelity and does not repair the cochain complex. |
| R05 | Use current `transport_variational_p2` with a volume multiplier. | Reject. RCA showed relative Hodge about 1 for static circle even with `lambda`; it fails before dynamics. |
| R06 | Use diffuse nodal pressure `q ~ psi` or phase-step `q ~ 1_phase` as the exact jump lifting. | Reject as exact fix. Best phase-step mismatch is about 20%; diffuse candidates are O(1). |
| R07 | Make every capillary jump exact by defining `c = A_f G_f q_lift(j)`. | Reject. If all nonconstant jumps are range, dynamic capillary drive is killed. |
| R08 | Subtract the component-wise mean curvature from curvature before building the affine jump: `kappa' = kappa - kappa_bar`. | Reject as final law. It is a continuum mnemonic, not a discrete virtual-work derivation, unless `kappa_bar` and the residual cochain are obtained from `d(S_h-lambda V_h)`. |
| R09 | Build `c_dyn = B_Gamma(sigma(kappa-kappa_bar))` and store `lambda=sigma*kappa_bar` as diagnostic pressure contrast only. | Reject as production. This preserves some motion but still assumes the local jump cochain is the adjoint transport gradient. |
| R10 | Range-calibrated Young--Laplace null mode: `c = Pi_R c_bar + (c_raw(kappa) - c_raw(kappa_bar))`. | Conditional diagnostic surrogate only. It is admissible only if proven algebraically identical to the discrete virtual-work cochain; otherwise it is a calibrated patch. |
| R11 | Hodge-null calibration form: `c = c_raw(kappa) - H(c_raw(kappa_bar))`, where `H=I-Pi_R`. | Conditional diagnostic surrogate only, equivalent to R10. It cannot be the final theory unless `H(c_raw(kappa_bar))` is derived from the discrete energy/constraint complex. |
| R12 | Choose `kappa_bar_h` by interface quadrature mean curvature. | Reject as principle. Useful for probes, but not a production multiplier unless it equals the discrete constrained variation. |
| R13 | Choose `kappa_bar_h` by discrete constrained variation `delta S_h / delta V_h`. | Required ingredient, but not sufficient alone. The whole face covector, not only the scalar multiplier, must come from the same variation. |
| R14 | Choose `kappa_bar_h` as scalar minimizing `||P_h B_Gamma(kappa-kappa_bar)||_{A^-1}`. | Reject as physics. It is a residual fit unless independently derived from the discrete Euler-Lagrange equations. |
| R15 | Component-wise version for multiple droplets: one `kappa_bar_m` per connected interface component. | Required for generality. A single global mean is physically wrong for multiple radii. |
| R16 | Use a harmonic/cohomology basis and remove only the constant Young--Laplace harmonic residue per component. | Promising theoretical framing for R10/R11; useful if the residual is a closed-interface harmonic artifact. |
| R17 | Enrich the pressure space with one Heaviside/jump DOF per connected component. | Required if the current pressure complex cannot represent `dV_m,h` reactions exactly. This is not optional polish; it is part of the variational complex. |
| R18 | Full GFM/HFE pressure-jump lifting with a component jump unknown and variable residual along interface. | Promising only as an implementation of the variational complex, with the component jump and variable residual sharing the same operator. |
| R19 | Interface-fitted/cut-cell pressure operator where constraint reactions are exact by construction. | Promising if it realizes the same discrete variational complex. Implementation cost is irrelevant to the selection principle. |
| R20 | Build capillarity as a discrete surface-stress divergence rather than scalar pressure jump. | Promising only if derived as `T_h^* dS_h` in the same face space; otherwise it risks becoming CSF fallback. |
| R21 | Polygonal interface virtual-work cochain: define `S_h` and `V_m,h` from the reconstructed closed curve and differentiate them with respect to face-normal transport. | Selected physical/mathematical target. This is the only candidate in this list that directly defines all modes by one constrained energy. |
| R22 | Finite-step Gonzalez/discrete-gradient version of R21 for time integration. | Required extension for theorem-grade finite-step energy accounting, not a schedule-based later option. |
| R23 | Use `range_projected` as an equilibrium/range-membership diagnostic only. | Required diagnostic, not a remedy alone. It must never define production capillarity. |
| R24 | Let reinitialization absorb residual geometry errors. | Reject. Reinit is a representation projection, not capillary work. |
| R25 | Gate-first rollout: compute candidate cochains diagnostically on arbitrary closed interfaces before enabling corrector. | Required process. Test shapes are probes only; success requires variational identity and constrained criticality, not circle/ellipse recognition. |

## Theoretical Screening

### Gate G1 - Variational Identity

The production cochain must be the adjoint of the same transport map that
moves the interface:

```text
<c_sigma, u_f>_faces
  = - d_q [ sigma S_h(q) - sum_m lambda_m V_m,h(q) ][ T_h u_f ]
```

for arbitrary admissible face velocities `u_f`.  This is the central test.
It does not ask whether the reconstructed interface is a circle, ellipse,
square, or anything else.

R21 satisfies the gate by definition if `S_h`, `V_m,h`, and `T_h` are the
actual discrete objects used by transport.  R17/R18/R19 can satisfy it only if
their augmented pressure/jump variables are part of the same variational
operator.  R08-R14 fail as standalone laws because they alter curvature
scalars or Hodge residues without first proving the full face covector is the
transport-adjoint energy gradient.

### Gate G2 - Constrained Equilibrium Nullity

For each connected component, equilibrium means constrained stationarity:

```text
d_q [ sigma S_h - sum_m lambda_m V_m,h ] = 0
```

on all admissible interface variations.  The test is not "is the shape a
circle?"  A circle is only a convenient manufactured equilibrium for a
particular `S_h,V_h`; if the discrete geometry admits another constrained
critical shape, that shape must also produce zero Hodge drive.  Conversely, a
shape that merely resembles a known benchmark must not be silenced unless the
discrete stationarity equations say so.

This gate rejects blanket range projection because it forces nullity by
algebra, not by constrained energy criticality.  It also rejects benchmark-name
switching and hand-picked `kappa_bar` fits.

### Gate G3 - Noncritical Release For Arbitrary Modes

For any perturbation direction with nonzero constrained first variation, the
Hodge residual must remain nonzero:

```text
P_h c_sigma != 0
```

unless the variation is a pure pressure/gauge reaction in the same complex.
This includes non-elliptic modes, high wavenumbers, asymmetric deformations,
component interactions, and noisy but resolved interface modes.  The method
must compute the force from the energy gradient, not from a named modal family.

R07 and blanket `range_projected` fail because they can erase physical
noncritical modes.  Raw local jumps fail if their Hodge residual contains
nonvariational work.  R21 is the selected target because all modes are
generated by one scalar energy.

### Gate G4 - Same PPE Complex

The pressure reaction and capillary residual must live in the same weighted
face complex:

```text
D_f A_f G_f p = D_f c_sigma
a_f = A_f G_f p - c_sigma
```

If the current pressure space cannot represent the component volume
constraint reactions `dV_m,h` exactly, the mathematically correct repair is to
augment the operator, for example with one component jump/Heaviside DOF per
closed interface component.  This is a structural requirement, not a
medium-term convenience.

### Gate G5 - Reinitialization Separation

The virtual-work identity is evaluated on the transport step.  Any
reinitialization map `Pi_h` has a separate representation-change ledger:

```text
psi_before_transport -> psi_after_transport_before_reinit
psi_after_transport_before_reinit -> psi_after_reinit
```

No capillary remedy is valid if it relies on reinitialization to remove,
create, or hide capillary work.

## Extracted Physically Correct Set

### A. Selected Target: Discrete Surface-Energy Virtual-Work Cochain

Definition:

```text
c_sigma = T_h^* d_q [ sigma S_h(q) - sum_m lambda_m V_m,h(q) ]
```

where:

```text
q        = reconstructed closed-interface degrees of freedom
S_h      = discrete surface length/area used by the solver
V_m,h    = discrete volume of component m
lambda_m = discrete Lagrange multiplier from constrained stationarity
T_h      = face-velocity-to-interface transport map
```

This is the selected remedy because it is the only candidate here whose force,
null space, and noncritical modes all come from the same variational object.
It has no circle/ellipse detector and no time-horizon classification.

Required verification:

```text
virtual_work_rel_error(u_f) =
  | <c_sigma,u_f>_faces + delta E_h[T_h u_f] |
  / max(|delta E_h[T_h u_f]|, eps)
```

must be small for arbitrary sampled face velocities and arbitrary closed
interfaces within the resolved geometry class.

### B. Required Operator Compatibility: Component Constraint Reactions

If `dV_m,h` or the associated pressure jump reaction is not exactly
representable by the current pressure range, augment the pressure/jump complex
so that constrained equilibria are represented structurally:

```text
range(A_f G_f)  <-  range(A_f G_f) + span{component jump reactions}
```

The augmented DOFs are not a fallback and not a pressure postprocess.  They
must be consumed by the PPE, corrector, HFE history, gauge handling, and
diagnostics as one operator.

### C. Finite-Step Energy Version

For production time integration, the infinitesimal covector should be extended
to a finite-step discrete gradient, for example a Gonzalez-type construction:

```text
<c_sigma^{n+1/2}, Delta x_f>
  = -[ E_h(q^{n+1}) - E_h(q^n) ]
```

with the same component-volume constraints and the same reinit separation.
This is not a later convenience; it is the finite-step version of the same
energy theorem.

### D. Diagnostic Surrogates Only

R10/R11 can remain useful as diagnostic surrogates:

```text
c = c_raw(kappa) - H(c_raw(kappa_bar))
```

but only to falsify or approximate the theorem.  They must not be adopted as
production physics unless proven equal to `T_h^* d(S_h-lambda V_h)` in the
same discrete complex.  The same restriction applies to quadrature mean
curvature, residual-minimizing `kappa_bar`, and any scalar null-mode
calibration.

## Required Gates

The gates are shape-agnostic.  Named geometries are manufactured probes, not
logic branches.

```text
1. Variational work gate:
   arbitrary closed interface + arbitrary sampled u_f must satisfy
   <c_sigma,u_f> = -delta E_h[T_h u_f].

2. Constrained criticality gate:
   any manufactured or numerically found constrained critical shape must have
   ||P_h c_sigma||_w near solver tolerance.

3. Noncritical release gate:
   random resolved perturbations, non-elliptic modes, high modes, and
   multi-component interactions with nonzero constrained first variation must
   have nonzero ||P_h c_sigma||_w.

4. Operator compatibility gate:
   PPE, corrector, HFE history, and diagnostics use the same augmented or
   non-augmented `(D_f,A_f,G_f)` complex.

5. Reinit separation gate:
   transport work and representation-projection work are reported separately.
```

## Final Selection

Adopt the physically and mathematically strongest construction:

```text
Discrete closed-interface surface-energy virtual-work cochain
  c_sigma = T_h^* d_q [ sigma S_h - sum_m lambda_m V_m,h ]
```

and, if the existing pressure complex cannot represent the component constraint
reactions, repair the pressure/jump complex with component-wise constraint DOFs
so the same theorem holds inside the PPE/corrector.

Rejected explicitly:

```text
circle/ellipse shape classification,
near/mid/long-term selection as a correctness criterion,
range-calibrated null mode as production without variational proof,
blanket range projection,
none-only production,
damping/CFL/caps/smoothing,
FD/WENO/PPE fallback,
QP/range projection as physical capillarity,
current P2 route with only lambda patched in.
```

[SOLID-X] Theory/design artifact only; no production solver/config/YAML
behavior changed; no tested implementation deleted; no FD/WENO/PPE fallback
introduced.
