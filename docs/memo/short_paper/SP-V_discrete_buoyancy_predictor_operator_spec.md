# SP-V — Discrete Operator Specification for the Buoyancy Predictor Redesign

Date: 2026-04-25  
Status: ACTIVE  
Author: ResearchArchitect

## 1. Purpose

This note turns the redesign theory of `SP-U` and `SP-T` into a discrete
operator contract that can be implemented and audited against code.

The objective is to specify:

1. which discrete state is primary,
2. which operators are allowed to act on that state,
3. which invariants the redesigned algorithm must respect,
4. how the buoyancy-carrying predictor substate connects NS, LS, and CFD.

The resulting specification is meant to be the mathematical contract for the
next solver-side redesign.

## 2. Discrete Fields and Material Maps

Let

- `ψ_h^n` be the CLS/LS state on the active grid at time `t^n`,
- `φ_h^n = H_\varepsilon^{-1}(ψ_h^n)` the inverse-mapped level-set field,
- `ρ_h^n = ρ(ψ_h^n)`,
- `μ_h^n = μ(ψ_h^n)`.

These are nodal or cell-centered state carriers depending on the active module,
but they are all induced by the same interface field `ψ_h^n`.

The key interface support is the **dilated interface band**

\[
I_{1,h} = \mathcal{D}_h\!\left(\{\,0 < \psi_h^n < 1\,\}\right),
\]

where `D_h` denotes the one-cell, two-axis dilation used by the successful
full-band repair.

We define a band mask

\[
M_{I_1,h}(x) =
\begin{cases}
1, & x \in I_{1,h}, \\
0, & \text{otherwise}.
\end{cases}
\]

This mask is not an arbitrary smoothing device. It is the discrete support on
which the successful local equilibrium reconstruction is observed.

## 3. Discrete NS Operator Chain

We denote by

- `C_h(u_h^n)` the explicit convective contribution,
- `V_h(u_h^n)` the explicit viscous predictor contribution,
- `B_h(ψ_h^n)` the explicit buoyancy contribution.

For the present model,

\[
B_h(\psi_h^n)
=
- \frac{\rho_h^n - \rho_{\mathrm{ref}}}{\rho_h^n}\, g\, \mathbf{e}_y.
\]

The raw predictor assembly is then

\[
u_{\mathrm{pred},h}^{\mathrm{raw}}
=
u_h^n
+
\Delta t \left(
C_h(u_h^n) + V_h(u_h^n) + B_h(\psi_h^n)
\right).
\]

The CN/Picard-style corrector subsequently evaluates

\[
V_h\!\left(u_{\mathrm{pred},h}\right)
\]

and feeds the corrected state into the projection stage.

The pressure/projection side is abstracted as

\[
L_h p_h = D_h\!\left(\beta_h G_h p_h\right),
\qquad
\beta_h = 1/\rho_h,
\]

with `G_h` the discrete pressure gradient and `D_h` the discrete divergence on
the pressure-correction locus.

## 4. Fundamental Structural Requirement

The redesign is required to satisfy the following compatibility statement:

> the state seen by `V_h`, `G_h`, `D_h`, and `β_h` must be assembled on a
> common effective support in the interface band.

This is the exact place where the current failure originates: not from the
continuous equations alone, but from a mismatch between the effective support of
the buoyancy-carrying substate and the later pressure/divergence closure.

## 5. Stage-Split Discrete Operators

We define two local repair operators.

### 5.1 Vertical assembly repair

Let

\[
T_{y,h}^{I_1}: \mathbb{R}^{2N} \to \mathbb{R}^{2N}
\]

be the operator that repairs the buoyancy-carrying predictor substate on the
full dilated band `I_{1,h}`, acting primarily on the vertical component.

Its contract is:

\[
T_{y,h}^{I_1}(w_h) = w_h
\quad \text{outside } I_{1,h},
\]

and on `I_{1,h}` it replaces the vertical component by the face-consistent,
full-band reconstructed value while preserving the consistent two-component
state needed by the local stencil family.

We do **not** require `T_{y,h}^{I_1}` to be a linear projector. The PoC ladder
shows the good operator is local, nonlinear, and support-sensitive.

### 5.2 Horizontal post-stage repair

Let

\[
S_{x,h}^{I_1}: \mathbb{R}^{2N} \to \mathbb{R}^{2N}
\]

be a local x-side post-transform applied to the intermediate state *before*
evaluating `V_h(u_pred)`.

Its contract is:

\[
S_{x,h}^{I_1}(w_h) = w_h
\quad \text{outside } I_{1,h},
\]

and on `I_{1,h}` it restores the missing horizontal/cross-component coupling
that the assembly-side vertical repair does not fully capture.

The current data show:

- a full-band x operator is strongest,
- a sharp-local x operator is a plausible cheaper approximation,
- a mapped/global x operator is weaker.

## 6. Discrete Redesign Formula

The admissible discrete predictor is

\[
u_{B,h}^{\dagger}
=
T_{y,h}^{I_1}
\left(
u_h^n + \Delta t\,B_h(\psi_h^n)
\right),
\]

\[
u_{\mathrm{pred},h}^{(0)}
=
u_{B,h}^{\dagger}
+
\Delta t\left(
C_h(u_h^n) + V_h(u_h^n)
\right),
\]

\[
u_{\mathrm{pred},h}^{(1)}
=
S_{x,h}^{I_1}
\left(
u_{\mathrm{pred},h}^{(0)}
\right),
\]

and then

\[
u_{\star,h}
=
u_h^n
+
\Delta t\left(
C_h(u_h^n)
+
\tfrac12 V_h(u_h^n)
+
\tfrac12 V_h\!\left(u_{\mathrm{pred},h}^{(1)}\right)
+
B_h(\psi_h^n)
\right).
\]

This formula is not arbitrary. It is the narrowest operator form consistent
with:

- the best in-repo PoC branch,
- the stage-separation verdict,
- pressure-robustness theory,
- well-balanced source treatment,
- and mass-momentum consistency.

## 7. Discrete Invariants

The redesign must preserve the following invariants.

### I1. Support invariance

Outside `I_{1,h}`, both `T_{y,h}^{I_1}` and `S_{x,h}^{I_1}` are the identity.

### I2. Same-locus closure

The repaired state passed to `V_h` must be compatible with the same `β_h`,
`G_h`, and `D_h` family used by projection.

### I3. Gradient-compatibility protection

If a local component of the buoyancy forcing is pressure-compatible in the
sense of being representable as a discrete gradient on the effective support,
then the redesigned predictor should not convert that component into spurious
velocity error.

This is the discrete analogue of pressure robustness.

### I4. Multidimensional interface consistency

The repair cannot be reduced to x-only, y-only, edge-only, corner-only, or
simple scalar weighting without measurable loss.

### I5. Stage separation

The algorithm must distinguish between:

- assembly-borne vertical mismatch,
- `V_h`-stage horizontal coupling.

Any redesign that collapses these into one uniform patch contradicts the current
evidence.

## 8. Relation to Code

The current code-level realization of the design space lives in:

- `src/twophase/simulation/ns_predictor_assembly.py`
- `src/twophase/simulation/ns_step_services.py`
- `src/twophase/time_integration/cn_advance/picard_cn.py`
- `src/twophase/time_integration/cn_advance/richardson_cn.py`

The existing first-class modes

- `buoyancy_stagesplit_fullbandx`
- `buoyancy_stagesplit_sharpx`

are faithful realizations of the stage-split formula above:

- vertical repair in assembly,
- horizontal repair before `V_h(u_pred)`.

## 9. What a Correct Next Implementation Must Change

The next redesign should not just add another flag. It should promote

\[
(T_{y,h}^{I_1},\, S_{x,h}^{I_1})
\]

to explicit operator-level objects with clearly documented semantics.

The main open problem is then:

> can `S_{x,h}^{I_1}` be simplified without losing the beneficial coupling seen
> in the full-band x version?

That is now a focused operator-design problem, not a vague stability search.

## 10. Verdict

The mathematically precise solution class is:

> a discrete, interface-band-local, stage-split buoyancy predictor in which the
> vertical buoyancy substate is repaired during assembly and the residual
> horizontal coupling is repaired before the viscous corrector evaluates
> `V(u_pred)`.

This is the discrete operator contract implied by the present evidence.
