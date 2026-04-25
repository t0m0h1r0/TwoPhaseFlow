# SP-T — Stage-Split Buoyancy Predictor Redesign for ch13 Rising-Bubble Closure

Date: 2026-04-25  
Status: ACTIVE  
Author: ResearchArchitect

## 1. Abstract

This note updates the ch13 redesign theory after the latest predictor-side PoC
ladder. The key new result is a **stage separation**:

> the dominant vertical buoyancy mismatch is born in predictor assembly, while
> the residual horizontal coupling becomes important mainly at the
> `V(u_pred)` stage.

This is stronger than the earlier statement “the defect lives in `u_pred`”.
The new evidence shows that the repair need not be uniform across stages or
components. The minimal admissible redesign is therefore not a single global
repair operator, but a **stage-split buoyancy predictor**:

1. repair the buoyancy-carrying predictor substate in the full two-axis
   dilated interface band, with emphasis on the vertical component, during
   predictor assembly;
2. apply a lighter horizontal post-transform to the intermediate state seen by
   `V(u_pred)`;
3. keep the final projection/corrector unchanged.

## 2. Problem Statement

The failure remains a short-time rising-bubble blowup on the static `α=2` FCCD
stack. The unstable observables are

- `ppe_rhs_max`,
- `bf_residual_max`,
- `div_u_max`,

not primary `volume_conservation`.

So the failing contract is the variable-density **predictor → viscous-evaluate
→ projection** closure, not the level-set transport itself.

The new question is:

> does the missing cross-component signal belong to the predictor assembly
> itself, or to the later state seen by `V(u_pred)`?

## 3. Discrete CN Structure

The current CN/Picard-style predictor is structurally

\[
\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}}
=
\mathbf{u}^n
+
\Delta t\left(
\mathbf{C}^n + \mathbf{V}(\mathbf{u}^n) + \mathbf{B}^n
\right),
\]

followed by

\[
\mathbf{u}_\star
=
\mathbf{u}^n
+
\Delta t \left(
\mathbf{C}^n
+\tfrac12 \mathbf{V}(\mathbf{u}^n)
+\tfrac12 \mathbf{V}\!\left(\mathbf{u}_{\mathrm{pred}}\right)
+\mathbf{B}^n
\right),
\]

up to the exact in-repo splitting conventions. The important point is that
`u_pred` is a **composed state**.

We now refine the mismatch model:

\[
\mathbf{u}_{\mathrm{pred}}^{\mathrm{raw}}
=
\mathbf{u}_{\mathrm{pred}}^\star
+
\delta \mathbf{u}_y
+
\delta \mathbf{u}_x^{(V)},
\]

where:

- `u_pred^*` is the hypothetical well-balanced predictor state,
- `δu_y` is the dominant vertical buoyancy mismatch generated in assembly,
- `δu_x^(V)` is the residual horizontal/cross-component mismatch whose effect
  becomes strong mainly when `V(u_pred)` is evaluated.

This decomposition is motivated by the latest PoC ladder, not assumed a priori.

## 4. Empirical Constraints

The following measured branches are the crucial constraints.

### 4.1 Full buoyancy-local reference

\[
\texttt{buoyancy\_fullband\_local}
\;\to\;
3.021\times10^9 / 6.000\times10^{10} / 1.505\times10^6
\]

for

\[
(\texttt{ppe\_rhs},\texttt{bf\_res},\texttt{div\_u}).
\]

### 4.2 Vertical-only assembly

\[
\texttt{buoyancy\_fullband\_local\_y}
\;\to\;
3.330\times10^9 / 6.607\times10^{10} / 1.583\times10^6.
\]

So the vertical component captures most of the good signal, but not all of it.

### 4.3 Light horizontal assembly patches fail

\[
\texttt{buoyancy\_fullbandy\_mappedx}
\;\to\;
3.369\times10^9 / 6.883\times10^{10} / 1.636\times10^6,
\]

\[
\texttt{buoyancy\_fullbandy\_sharpx}
\;\to\;
3.411\times10^9 / 6.758\times10^{10} / 1.606\times10^6.
\]

Hence the missing horizontal signal is **not** recovered by a shallow x-side
patch during predictor assembly itself.

### 4.4 Horizontal post-stage repair succeeds

\[
\texttt{buoyancy\_fullbandy\_postfullbandx}
\;\to\;
3.181\times10^9 / 6.129\times10^{10} / 1.503\times10^6,
\]

\[
\texttt{buoyancy\_fullbandy\_postmappedx}
\;\to\;
3.250\times10^9 / 6.564\times10^{10} / 1.591\times10^6,
\]

\[
\texttt{buoyancy\_fullbandy\_postsharpx}
\;\to\;
3.209\times10^9 / 6.455\times10^{10} / 1.572\times10^6.
\]

This is the decisive stage-separation result.

## 5. Derived Interpretation

The latest ladder supports the following reading.

### P1. The dominant mismatch is vertical and assembly-borne

The vertical buoyancy-carrying signal is already present before `V(u_pred)` is
evaluated, because `y-only` assembly moves strongly in the right direction.

### P2. The missing residual is not a purely assembly-local x patch

The failure of `mappedx` and `sharpx` in assembly shows that the missing
horizontal signal is not recovered by simply injecting a light x correction into
the raw buoyancy sub-assembly.

### P3. The residual horizontal signal matters mainly at `V(u_pred)`

The success of `postfullbandx` and the partial success of `postsharpx` imply
that the missing x-side coupling is revealed mainly through the state seen by
the viscous evaluator.

### P4. The best redesign is therefore stage-split

The evidence rejects both extremes:

- one uniform global repair at assembly time,
- one late uniform repair after the whole predictor.

Instead, the consistent design is **stage-split and component-aware**.

## 6. Redesign Theorem

Let `I₁` be the full two-axis dilated interface band (the hard 3×3 band found
in the PoC ladder). Let `T_y^{I₁}` be a full-band vertical assembly transform,
and `S_x^{I₁}` a local horizontal post-transform applied before evaluating
`V(u_pred)`.

Then the minimal redesign class consistent with all current verdicts is:

\[
\mathbf{u}_{B}^{\dagger}
=
T_y^{I_1}\!\left(
\mathbf{u}^n + \Delta t\,\mathbf{B}^n
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(0)}
=
\mathcal{A}\!\left(
\mathbf{u}^n,\,
\mathbf{C}^n,\,
\mathbf{V}(\mathbf{u}^n),\,
\mathbf{u}_{B}^{\dagger}
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(1)}
=
S_x^{I_1}\!\left(
\mathbf{u}_{\mathrm{pred}}^{(0)}
\right),
\]

and then

\[
\mathbf{u}_\star
=
\mathbf{u}^n
+
\Delta t\left(
\mathbf{C}^n
+
\tfrac12 \mathbf{V}(\mathbf{u}^n)
+
\tfrac12 \mathbf{V}\!\left(\mathbf{u}_{\mathrm{pred}}^{(1)}\right)
+
\mathbf{B}^n
\right).
\]

Here `A` is the standard predictor composition map. The key design restriction
is that `T_y^{I₁}` and `S_x^{I₁}` are **not interchangeable**:

- replacing `T_y^{I₁}` by a weaker vertical repair loses too much signal;
- moving the x correction into assembly fails;
- removing `S_x^{I₁}` from the `V(u_pred)` stage leaves a substantial residual.

## 7. Algorithm Spec

The resulting algorithmic spec is:

1. build the raw explicit buoyancy substate,
2. apply full-band vertical repair on `I₁`,
3. compose the predictor state with convection and `V(u^n)`,
4. apply x-side post-transform to the intermediate state used by `V(u_pred)`,
5. evaluate `V(u_pred)` and continue the CN corrector,
6. project as usual.

This suggests two admissible implementation variants.

### Variant A: strongest

- `T_y^{I₁}` = full-band y repair,
- `S_x^{I₁}` = full-band x repair.

This corresponds to `postfullbandx` and is the current best stage-split branch.

### Variant B: cheaper approximation

- `T_y^{I₁}` = full-band y repair,
- `S_x^{I₁}` = sharp-local x repair.

This does not match Variant A, but it recovers a large fraction of the missing
signal and is a plausible cheaper approximation.

Both variants are now reproducible as first-class solver-side modes rather than
ad hoc flag combinations:

- `predictor_assembly: buoyancy_stagesplit_fullbandx`
- `predictor_assembly: buoyancy_stagesplit_sharpx`

and these first-class modes are bit-identical to the earlier two-flag
implementations.

## 8. Consequences for Future Work

The next engineering question is no longer “where should buoyancy go in
general?”, but:

> how should the x-side post-stage operator `S_x^{I₁}` be constructed so that
> it captures the missing coupling with minimal stencil cost?

In other words, the remaining uncertainty has narrowed from a global predictor
closure problem to a **specific operator-design problem at the `V(u_pred)` stage**.

## 9. Verdict

The current best-supported diagnosis is now:

> the dominant vertical buoyancy mismatch is born in predictor assembly, while
> the missing horizontal coupling emerges mainly at the `V(u_pred)` stage.

This is the most concrete redesign-ready statement obtained so far.
