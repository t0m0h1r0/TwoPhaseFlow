# Short Paper: Variable-Density Projection, Face-Canonical State, and the ch13 Rising-Bubble PoC

Recent split-result update:

- the post-AW probes show that the useful signal is not just “buoyancy-local”
  in a generic vector sense. A vertical-only buoyancy-local repair already
  recovers most of the gain, while a repair applied to the coupled
  `u_old + dt * (B/rho + V(u^n))` state also improves markedly over the generic
  `u_pred` repair. This shifts the diagnosis from a vague face/nodal mismatch
  toward a more precise statement: the remaining instability is consistent with
  a **buoyancy-driven vertical interface-band mismatch plus a secondary
  buoyancy–viscous assembly coupling**.
Date: 2026-04-24  
Branch: `worktree-researcharchitect-src-refactor-plan`  
Compiled by: ResearchArchitect  
Status: ACTIVE

## Abstract

This short paper surveys prior work relevant to the ch13 rising-bubble
instability and turns the survey outcome into an implementation plan. The main
result is that the most credible cure is **not** another local patch around
buoyancy, pressure jump, or wall treatment. The literature instead points to a
structural change: the post-corrector velocity should be treated as a
**face/staggered canonical state** so that mass transport, momentum transport,
pressure correction, and body-force closure live on the same discrete locus.

## 1. Problem Restatement

The current ch13 rising-bubble stack uses an FCCD face-flux PPE and an FCCD
face-flux projector, but the authoritative runtime state after correction is
still nodal velocity. In short debug probes, this produces an early blowup with
rapid growth in `ppe_rhs_max`, `bf_residual_max`, and `div_u_max` while
`volume_conservation` remains small.

The immediate engineering question is therefore:

> What class of remedies is already supported by the variable-density,
> multiphase, staggered-grid literature?

## 2. Survey Scope

The survey focused on primary literature in four clusters:

1. **Variable-density projection and staggered discretisation**
2. **Consistent mass/momentum transport at large density ratio**
3. **Balanced-force and well-balanced force placement**
4. **Rising-bubble validation benchmarks**

The key papers consulted were:

- Almgren, Bell, Szymczak, Howell (1998), *A Conservative Adaptive Projection
  Method for the Variable Density Incompressible Navier–Stokes Equations*
- Brown, Cortez, Minion (2001), *Projection Method III: Spatial Discretization
  on the Staggered Grid*
- Guermond, Salgado (2009), *A Splitting Method for Incompressible Flows with
  Variable Density Based on a Pressure Poisson Equation*
- Rudman (1998), *A Volume-Tracking Method for Incompressible Multifluid Flows
  and Large Density Variations*
- Raessi, Pitsch (2012), *Consistent Mass and Momentum Transport for Simulating
  Incompressible Interfacial Flows with Large Density Ratios Using the Level Set
  Method*
- Dodd, Ferrante (2014), *A Fast Pressure-Correction Method for Incompressible
  Two-Fluid Flows*
- François et al. (2006), *A Balanced-Force Algorithm for Continuous and Sharp
  Surface Tension Models Within a Volume Tracking Framework*
- Popinet (2009), *An Accurate Adaptive Solver for Surface-Tension-Driven
  Interfacial Flows*
- Kumar, Natarajan (2017), *A Novel Consistent and Well-Balanced Algorithm for
  Simulations of Multiphase Flows on Unstructured Grids*
- Hysing et al. (2009), *Quantitative Benchmark Computations of Two-Dimensional
  Bubble Dynamics*

## 3. Survey Findings

### 3.1 Variable-density projection is a same-space closure problem

The Brown–Cortez–Minion line and the Almgren/Guermond variable-density line both
support the same discrete lesson:

> The divergence operator, pressure-gradient operator, density weighting, and
> post-corrector state must close in the same discrete space.

For the current FCCD stack, that space is naturally the face-flux space, not
the nodal reconstruction space.

### 3.2 Large density ratio requires consistency, not only stronger solvers

Rudman, Raessi–Pitsch, and Dodd–Ferrante all reinforce that strong density
contrast penalises inconsistency more than it penalises raw iteration count. In
other words, a “better PPE solve” cannot compensate for a mass/momentum or
pressure/velocity mismatch that is baked into the discrete state handoff.

### 3.3 Force placement must be well-balanced on the same locus

François, Popinet, and Kumar–Natarajan make a parallel point for capillary and
body-force terms:

> The pressure gradient, buoyancy term, and surface-tension term must be paired
> on the same geometric locus if equilibrium is to remain well balanced.

This strengthens the diagnosis that moving buoyancy alone was too local a PoC.

### 3.4 Hydrostatic split is a secondary stabiliser

The literature supports hydrostatic/residual-pressure splitting as a useful
conditioning aid, especially in gravity-dominated variable-density flows.
However, the same literature does **not** suggest it as the first cure when the
canonical post-corrector state itself is mismatched.

### 3.5 Benchmark implication

Hysing et al. provide the right downstream validation target once the PoC is in
place: the implementation should be judged not only by non-blowup but by
centroid rise, deformation, and stable pressure/velocity closure under
gravity-driven motion.

## 4. Synthesis Against the Current Diagnosis

The survey outcome aligns strongly with the in-repo hypothesis campaign:

| Observation | Literature reading | Design implication |
|---|---|---|
| `g=0` stabilises the short probe | buoyancy is the repeated excitation | keep gravity inside the same face closure |
| `sigma=0` still blows up | surface tension is not the sole trigger | do not treat capillarity as the only culprit |
| preserving faces inside one step is not enough | closure must survive the step-to-step handoff | expose and carry face state explicitly |
| moving buoyancy injection alone worsens the run | force placement alone cannot repair a mismatched canonical state | solve state ownership before local force tweaks |

The strongest shared conclusion is therefore:

> The next viable PoC is a **face-canonical state PoC**, not another
> source-term-only or boundary-only patch.

## 5. Proposed PoC Ladder

The recommended implementation sequence is intentionally staged.

### Phase P0 — Explicit face-state carry

- add an explicit grouped step result that carries corrected face fluxes
- allow the next request to consume that face state directly
- keep nodal velocity as a derived field for compatibility

This phase does **not** claim to fix the instability by itself. Its purpose is
to make the canonical state handoff explicit and testable.

### Phase P1 — Runner-level face-canonical transport

- let `runner.py` propagate face state between timesteps
- stop relying on solver-private hidden carry as the only mechanism

This phase upgrades the architecture from an internal cache to an explicit
runtime contract.

### Phase P2 — Face divergence as the primary incompressibility gate

- prefer face divergence whenever the canonical face state is available
- retain nodal diagnostics only as derived views

### Phase P3 — Same-locus force closure

- revisit buoyancy and pressure/surface-tension pairing only after P0–P2 land
- keep hydrostatic split as a secondary follow-up, not the first move

## 6. Engineering Knowledge Gained

This survey, combined with the existing in-repo experiments, yields the
following practical lessons.

### 6.1 What not to do first

- do not start with a larger PPE iteration budget
- do not start with a buoyancy-only patch
- do not start with a pressure-jump-only sign or magnitude tweak

### 6.2 What to do first

- make face state explicit
- make the state handoff auditable
- test the design on the short rising-bubble debug path before broader rollout

### 6.3 What to validate

The primary success metrics for the PoC ladder are:

- `ppe_rhs_max`
- `bf_residual_max`
- `div_u_max`
- `yc`
- `mean_rise_velocity`

`kinetic_energy` remains useful, but only as a late symptom.

## 7. Immediate Action

Based on this survey, the next concrete engineering step is:

> introduce an explicit face-canonical grouped step API and let the runner
> propagate that state as an opt-in PoC path.

That is the smallest implementation slice that matches both the survey and the
local hypothesis campaign.

## 8. Post-Survey PoC Update

After this survey, two follow-up PoC slices were executed.

- **PoC C**: explicit face-canonical state carry across the public step contract
- **PoC D**: conservative face-divergence acceptance gate on top of PoC C
- **PoC E**: face-native predictor RHS assembly on top of PoC C
- **PoC F**: face-native predictor state (`u*_face`) carry into the corrector
- **PoC G**: advance the predictor in face space by applying a face-native
  increment to the carried canonical face state
- **PoC H**: assemble the explicit force RHS on the same face locus as the
  incremental face-base predictor path
- **PoC I**: enforce no-slip consistency directly on the carried face state
- **PoC J**: derive the timestep limit from the carried face-state magnitude
- **PoC K**: synchronise nodal `u*` from `u*_face` and remove the redundant
  nodal predictor-BC step
- **PoC L**: keep the incremental face-base carry, but switch momentum
  convection to the existing `fccd_flux` face-flux operator
- **PoC M**: keep the incremental face-base carry, but switch the viscous
  predictor from Picard-CN to explicit forward Euler
- **PoC N**: keep PoC M and move buoyancy into the projection-consistent force
  channel
- **PoC O**: keep the face-carry path and switch the CN viscous advance to
  `richardson_picard`
- **PoC P**: keep the explicit-viscous path and switch the viscous spatial
  operator to `conservative_stress`
- **PoC Q**: keep the explicit-viscous path and switch the viscous spatial
  operator to `ccd_stress_legacy`

The outcome is informative:

- PoC C makes the face state explicit and auditable, but does not stabilise the
  rising-bubble path
- PoC D shows that the face witness is still worse than the nodal witness on
  every recorded step (`face_divergence_gate_passed = 0` throughout)
- PoC E is bit-identical to PoC C on the current FCCD stack, which means RHS
  face assembly alone is not the missing structural ingredient
- PoC F first appeared promising, but that signal was invalid: the initial
  debug YAML had accidentally dropped the `initial_condition` block, so the
  "stable" run started from a uniform gas field rather than a bubble
- after restoring the bubble initial condition, PoC F blows up at `step=6`,
  `t=0.0116`, with `ppe_rhs_max = 4.58e+12`, `bf_residual_max = 6.23e+13`, and
  `div_u_max = 3.65e+7`, which is worse than the baseline debug run
- PoC G improves the predictor-side contract by evolving `u*_face` from the
  carried face state plus a face-native increment; this lowers the failure-time
  residuals to `ppe_rhs_max = 3.06e+09`, `bf_residual_max = 7.99e+10`, and
  `div_u_max = 1.78e+06`, but the run still blows up at `step=5`, `t=0.0111`
- PoC H moves the explicit force RHS to the face locus on top of PoC G and is
  bit-identical to PoC G, which means the force-RHS assembly site is no longer
  the limiting inconsistency in the current stack
- PoC I enforces no-slip directly on the carried face state and is also
  bit-identical to PoC G, which means the wall-ordering suspicion is not the
  dominant defect either
- PoC J makes CFL control face-aware; the timestep reacts, but the run still
  blows up and the failure-time residuals worsen, which means nodal CFL
  underestimation is not the leading cause of the blowup
- PoC K makes the predictor explicitly face-primitive at the final sync stage,
  but it is bit-identical to PoC G, which means the missing ingredient is
  deeper than predictor-state reconciliation after the update
- PoC L changes the predictor operator itself by swapping convection from
  `uccd6` to `fccd_flux`, but the run still blows up at `step=5`, `t=0.0111`
  and the failure-time diagnostics worsen to `ppe_rhs_max = 1.16e+11`,
  `bf_residual_max = 1.26e+13`, and `div_u_max = 2.94e+07`
- PoC M keeps the safer `uccd6` convection but makes the viscous predictor
  explicit; the run still blows up, yet the failure-time diagnostics improve to
  `ppe_rhs_max = 2.88e+09`, `bf_residual_max = 6.83e+10`, and
  `div_u_max = 1.63e+06`, which is a modest but real gain over PoC G
- PoC N layers projection-consistent buoyancy on top of PoC M, but the
  diagnostics drift back to `ppe_rhs_max = 3.32e+09`,
  `bf_residual_max = 7.88e+10`, and `div_u_max = 1.75e+06`, so buoyancy locus
  still does not emerge as the dominant lever
- PoC O keeps CN viscosity but replaces Picard/Heun with
  `Richardson(Picard)`; the run still blows up, with mixed-but-better
  diagnostics than PoC G (`ppe_rhs_max = 3.42e+09`,
  `bf_residual_max = 6.93e+10`, `div_u_max = 1.63e+06`), which again points to
  the viscous predictor time update as a real part of the defect
- PoC P keeps the explicit-viscous slice but switches to
  `conservative_stress`; this is worse than PoC M, so the fully conservative
  low-order stress operator is not the missing ingredient
- PoC Q switches the explicit-viscous slice to `ccd_stress_legacy`; this is
  also slightly worse than PoC M, which means the current `ccd_bulk` hybrid is
  already the best-performing member of the tested viscous-spatial family

The survey conclusion therefore survives contact with implementation:

> making face state explicit is necessary, but not sufficient; the
> predictor/corrector pathway itself must become more face-native before the
> face witness can become the authoritative incompressibility gate.

One extra engineering lesson now joins the numerical one:

> projection-closure PoCs need config-completeness guards for defining inputs
> such as `initial_condition`; otherwise, a malformed benchmark can create a
> false positive that looks like numerical progress.

The newest slice refines the implementation guidance one step further:

> if a face-canonical design is pursued, predictor state should be advanced as
> a face-native increment on top of the carried face state, not reconstituted as
> an absolute face field from nodal `u*`; but even that is still not the full
> cure for the ch13 rising-bubble instability.

The latest no-op result narrows the target once more:

> after the incremental face-base carry is introduced, the next meaningful
> intervention is unlikely to be another RHS-locus tweak; it has to change the
> predictor/corrector state evolution more fundamentally.

The newest pair of probes narrows it again:

> once same-locus RHS and boundary-order effects are ruled down, and even
> face-aware CFL fails to help, the remaining target is the predictor/corrector
> state evolution operator itself, not its surrounding plumbing.

The newest no-op result sharpens the same lesson:

> even when nodal `u*` is forced to follow `u*_face`, the trajectory does not
> move; the next useful intervention has to change how the predictor update is
> *formed*, not merely how its outputs are synchronised.

The newest operator-level probe adds one more boundary to the search space:

> replacing the predictor convection term with an existing FCCD face-flux
> operator is still not enough; the unresolved instability is not convection
> locus alone, but the coupled variable-density predictor/corrector evolution.

The newest two slices refine the implementation guidance again:

> changing the viscous predictor time update helps slightly, which means the
> predictor integrator itself matters, but moving buoyancy into the
> projection-consistent force channel on top of that still does not provide the
> missing stability.

The newest CN-strategy slice sharpens the same message:

> even after correcting the viscous CFL bookkeeping, `Richardson(Picard)` only
> helps a little. So the problem is not that the run simply needs the proper
> viscous CFL gate; it is the underlying variable-density viscous predictor
> update law that still needs redesign.

The newest viscous-spatial pair narrows the search space again:

> neither `conservative_stress` nor `ccd_stress_legacy` outperforms the
> current `ccd_bulk` hybrid, so the remaining defect is not just a bad choice
> inside the existing viscous-spatial menu.

The newest CN-intermediate-state probe further refines the implementation
guidance:

> applying wall BC directly to the Picard/Richardson intermediate predictor
> state `u_pred` before evaluating `V(u_pred)` does change the trajectory, but
> it makes the blow-up diagnostics worse. Therefore the missing stability is
> not recovered by constraining the already formed nodal intermediate state;
> the remaining defect more likely lives in the state-to-operator coupling of
> the variable-density CN predictor itself.

The newest face-reconstruction probe sharpens that guidance in a useful way:

> rebuilding the Picard/Richardson intermediate predictor state from the
> carried face state before evaluating `V(u_pred)` still does not stabilise the
> run, but it improves `KE`, `bf_res`, and `div_u` against the Richardson
> baseline. This is the strongest evidence so far that the correct repair is
> not a boundary patch on a nodal state, but a more face-consistent CN
> predictor evolution.

The newest endpoint-reconstruction probe puts an important bound on that idea:

> if both CN endpoint evaluations are reconstructed from the carried face
> state, the blow-up diagnostics worsen again. So the face-consistent repair is
> likely an *incremental* coupling on the intermediate predictor state, not a
> wholesale replacement of the nodal base endpoint in the current CN update.

The newest viscous-increment probe adds a second bound:

> if only the viscous increment branch is reconstructed from the carried face
> state, the run gets worse again. Therefore the useful correction is not a
> viscous-only face remap. The evidence now points specifically to a
> face-consistent coupling of the **full intermediate predictor state**
> immediately before evaluating `V(u_pred)`.

The newest one-step iterate probe adds a useful bound on the repair space:

> starting from the best CN-side probe (intermediate face reconstruction), one
> extra fixed-point-style iterate reduces `ppe_rhs` further, but it does not
> preserve the stronger `bf_res` / `div_u` improvement of the one-shot PoC S.
> This suggests that the right redesign is not a naive repetition of the same
> face-coupled predictor map, but a more selective defect/intermediate-state
> coupling that keeps the improved face consistency without reopening the
> divergence pathway.

The newest relaxed-iterate probe adds a strong negative result:

> damping the extra face-coupled intermediate iterate with a simple convex
> blend (`ω=0.5`) is worse than both the one-shot face reconstruction and the
> full extra-iterate variant. This rules out a simple “iterate the same map,
> just more gently” interpretation. The useful mechanism in PoC S is therefore
> not captured by a scalar relaxation of the same fixed-point update.

The newest bulk-only probe adds another important bound:

> applying the face-consistent correction only to the bulk region of the
> `ccd_bulk` viscous operator does not recover the positive PoC S signal. This
> suggests the missing repair is not a purely bulk/divergence-sensitive one;
> the helpful defect likely involves the interface-band coupling itself, or a
> more selective operator-difference correction across both regions.

The newest interface-band operator-defect probe is the clearest structural
result yet:

> replacing only the interface-band part of `V(u_pred)` with the response from
> a face-consistent transformed state reproduces almost all of the benefit of
> full intermediate face reconstruction. This is strong evidence that the core
> defect is an interface-band-localised operator mismatch inside the
> variable-density CN predictor, rather than a purely bulk or whole-state one.

The newest normal-only follow-up adds an important exclusion:

> projecting that same interface-band operator defect onto the local interface
> normal removes the benefit and returns the run close to baseline. This means
> the helpful correction is not captured by a purely normal /
> pressure-sensitive component. The remaining candidate is a tangential or
> genuinely full-vector interface-band defect structure.

The newest tangential-only follow-up sharpens this further:

> removing the normal contribution and reinjecting only the tangential part of
> the same interface-band operator defect is even worse than baseline. This
> rules out a tangential-only explanation as well. The most consistent reading
> is now that the useful repair is inherently a **full-vector interface-band
> defect correction**, with the stabilizing signal lost when the defect is
> projected onto either component subspace.

The newest diagonal/shear family split adds the strongest structural clue yet:

> when the same interface-band defect is decomposed by viscous-operator family
> rather than by geometric projection, the diagonal-family correction nearly
> reproduces the full defect benefit, while the shear-family correction does
> not. This suggests the stabilizing signal is carried primarily by a
> **diagonal / pressure-like operator mismatch** inside the variable-density CN
> predictor, not by the off-diagonal shear family.

The newest component-axis split sharpens the diagonal-family reading:

> restricting the diagonal-family correction to either `u` or `v` alone fails
> to reproduce the full diagonal-family gain. The `v`-only correction is less
> harmful than the `u`-only one, consistent with buoyancy alignment, but the
> main benefit still requires a coupled two-component diagonal-family repair.

The newest trace-like coupled-block test narrows it further:

> reducing the interface-band diagonal-family correction to a trace-like /
> divergence-like coupled block does not retain the gain; it performs worse
> than the full diagonal-family correction. This argues against a pure
> `∇(μ ∇·u)` explanation and points instead to a broader coupled
> diagonal-family mismatch inside the CN predictor.

The newest inverse-density weighting test adds another exclusion:

> reweighting the successful diagonal-family interface defect toward the
> low-density side with a bounded normalized `1/ρ` factor makes the run worse,
> not better. This argues against the simplest “missing inverse-density
> weighting” explanation for the remaining instability.

The newest pressure-sensitive weighting test adds one more exclusion:

> weighting the successful diagonal-family interface defect by a previous-step
> pressure/force mismatch witness `|∇p^n - f/ρ|` does not preserve the best
> `bf_res` / `div_u` gains of the plain diagonal-family correction. This
> argues against the simplest “missing scalar pressure-sensitive amplitude”
> explanation and points instead to a more structural coupled
> diagonal-family/operator mismatch inside the CN predictor.

The newest nontrace split adds another useful exclusion:

> subtracting the trace-like block from the successful diagonal-family defect
> also makes the run worse. This argues that the stabilizing signal is not a
> clean “diagonal minus trace” remainder; it lives in the broader **coupled
> full diagonal-family block**, including interactions that look trace-like
> when isolated.

The newest conservative-generation test adds an important upstream clue:

> regenerating the successful diagonal-family defect with the conservative
> low-order family still preserves most of the gain. This suggests the useful
> signal is not tied to the exact `ccd_bulk` mixed normal/tangent operator
> itself; it is more likely **state-generated** in the transformed
> intermediate predictor and only then expressed through the diagonal-family
> operator.

The newest transformed-state normal/tangent split sharpens that interpretation:

> if the transformed intermediate state is projected onto the interface
> **normal** before evaluating the diagonal-family defect, the run matches the
> best diagonal-family result almost exactly; if the same split is applied to
> the **tangent** part instead, the run becomes much worse than baseline. This
> suggests the remaining useful stabilizing signal is generated in the
> **normal-projected transformed intermediate state**, rather than in a
> tangential/shear-like component, and is then carried into the CN predictor
> through the coupled diagonal-family operator.

The newest upstream value/density probes make that picture more specific:

> evaluating the full viscous operator directly on the
> normal-projected transformed intermediate state preserves most of the gain,
> so the useful signal is already present at the transformed-state level.
> But adding the old bounded `1/ρ` weighting on top of the successful
> normal-state diagonal-family correction slightly worsens the run. This
> suggests the remaining stabilizing effect is not primarily a missing scalar
> density-coupled amplitude; it is better understood as a
> **normal-side transformed-state signal** that the diagonal-family operator
> extracts more cleanly than the full operator does.

The newest interface-local value-transform test adds an important nuance:

> if the transformed intermediate state is restricted to the interface band but
> otherwise kept as a full-vector value field, most of the gain from the older
> full-field face-consistent transform survives. This suggests the dominant
> upstream signal is **interface-local at the value/state level**. The extra
> normal projection changes the result only slightly, so normal projection now
> looks like a refinement on top of the more important interface localization.

The newest value+trace combination resolves the next ambiguity:

> adding a trace-like / divergence-like witness on top of the strong
> interface-local value transform makes the run significantly worse. So the
> remaining beneficial effect is not a simple “value transform plus missing
> trace witness” story. The evidence now points more strongly to the
> **interface-local transformed state itself** as the key upstream ingredient,
> with trace-style derived witnesses acting as over-corrections rather than
> helpful supplements.

The newest value+diagonal combination reinforces that conclusion:

> adding a diagonal-family witness on top of the already-good interface-local
> value transform also worsens the run (`ppe_rhs=3.76e9`, `bf_res=7.60e10`,
> `div_u=1.72e6`). So the missing ingredient is not a diagonal-family witness
> layered on top either. The most consistent reading is still that the
> **interface-local transformed intermediate state itself** carries the useful
> upstream repair, while derived-witness additions tend to over-correct it.

The newest Picard-vs-Richardson comparison strengthens the time-integration
reading:

> running the same interface-local transformed-state repair under plain
> `picard` is still better than the older unrepaired branch, but clearly worse
> than `richardson_picard`
> (`ppe_rhs=3.65e9`, `bf_res=8.30e10`, `div_u=1.76e6` vs
> `3.36e9`, `6.73e10`, `1.61e6`). So the dominant gain is still coming from the
> **interface-local transformed intermediate state**, but the NS-side CN
> closure is also a real part of the story. This is consistent with the view
> that the main instability is in the viscous predictor / projection coupling,
> not in the level-set TVD-RK3 path.

The newest matrix-free implicit CN PoC refines that again:

> replacing the viscous predictor with a naive full-block matrix-free implicit
> CN solve, while keeping the same interface-local transformed-state repair,
> does not beat the Richardson branch and emits a non-converged GMRES warning.
> The run lands at `ppe_rhs=3.84e9`, `bf_res=7.83e10`, `div_u=1.75e6`, which is
> worse than `richardson_picard` and only mixed relative to `picard`. So the
> problem is not solved by “making the viscous step implicit” in a naive way;
> the closure/coupling structure still matters, and the present full-block
> implicit PoC is solver-limited.

The newest diagonal-implicit split strengthens that conclusion:

> making only the diagonal family implicit and keeping the shear family
> explicit does not help either. The run lands at
> `ppe_rhs=4.07e9`, `bf_res=8.20e10`, `div_u=1.78e6`, again with a non-converged
> GMRES warning. So even the memo-aligned diagonal-implicit split is not a
> short path here; the best current branch is still the explicit
> `richardson_picard` predictor plus the interface-local transformed
> intermediate state.

The newest alias-standardization follow-up is intentionally non-numerical:

> adding `intermediate_state_repair: interface_local` as a declarative alias
> reproduces the current best branch exactly. The candidate debug run is
> bit-identical to the older
> `richardson_picard + intermediate_state_interface_reconstruct=true` branch in
> `times`, `kinetic_energy`, `ppe_rhs_max`, `bf_residual_max`, and `div_u_max`.
> This matters because it separates “best currently known repair” from the
> legacy Boolean flag spelling without claiming a new stabilization result.

The newest upstream-localization check makes the current diagnosis more specific:

> applying the same interface-local transformed-state idea earlier in the CN
> map does not reproduce the gain. Transforming the state used for `V(u^n)`
> gives `ppe_rhs=3.67e9`, `bf_res=7.55e10`, `div_u=1.71e6`, and transforming
> only the pre-explicit viscous increment state is worse still
> (`4.12e9`, `8.10e10`, `1.74e6`). So the stabilizing signal does not belong to
> an upstream sub-piece of the predictor; it belongs to the fully composed raw
> intermediate state `u_pred` just before evaluating `V(u_pred)`.

The newest explicit-branch split refines that statement:

> what is ruled out is the **viscous-side** upstream localization, not every
> upstream localization. Repairing the explicit-side state
> `u_old + dt(explicit_rhs / rho)` already reproduces almost all of the gain
> (`3.34e9`, `6.71e10`, `1.61e6`), while convection-only repair is poor
> (`4.09e9`, `8.35e10`, `1.80e6`). The strongest result so far comes from
> buoyancy-only repair (`3.02e9`, `6.00e10`, `1.51e6`). So the best current
> reading is: the dominant closure defect is an **interface-local mismatch
> injected by the buoyancy-driven explicit contribution to the CN intermediate
> state**, rather than a generic whole-state mismatch or a viscous-side defect.

One cautionary follow-up matters here:

> a non-debug “candidate” branch briefly looked much more stable, but that
> turned out to be a configuration false positive caused by a missing bubble
> `initial_condition`. The run had effectively no real interface. After
> restoring the circular gas-bubble IC, the same non-debug candidate again
> blows up at `step=5`, `t=0.0112`. So the buoyancy-local result is still best
> understood as a **diagnostic localization signal**, not yet as a validated
> production remedy.

One more structural check narrows the interpretation further:

> assembling the buoyancy-only predictor substate directly on **face density**
> before reconstructing nodes does not improve on the simpler buoyancy-local
> state repair. The resulting branch (`3.40e9`, `6.76e10`, `1.60e6`) stays close
> to the control branch and clearly behind buoyancy-local repair
> (`3.02e9`, `6.00e10`, `1.51e6`). So the unresolved defect is not exhausted by
> “use face density for buoyancy”; it still looks more like an
> interface-local mismatch in the assembled buoyancy-driven intermediate state.

And the obvious reduced-pressure proxy has now also been checked:

> combining the existing `projection_consistent_buoyancy` path with the best
> current predictor-repair branches makes the run **worse**, not better.
> Therefore the missing fix is not simply “move buoyancy to the projection
> side”; if a hydrostatic split is still the right theory, it must be realised
> through a more structural predictor/pressure reformulation than the current
> switch provides.

The next obvious stronger test was then made explicit:

> the buoyancy-only predictor substate was replaced by a column-wise
> hydrostatic-pressure reconstruction before the CN corrector. This is more
> structural than the existing projection-side proxy, but it still does **not**
> beat the simpler `buoyancy_local` branch. Hydrostatic-only is clearly worse
> (`3.47e9`, `8.15e10`, `1.82e6`), and even hydrostatic plus buoyancy-local
> repair (`3.27e9`, `6.60e10`, `1.60e6`) remains behind plain buoyancy-local
> (`3.02e9`, `6.00e10`, `1.51e6`). So the remaining defect still looks more
> like an interface-local mismatch in the assembled buoyancy-driven state than
> a missing hydrostatic-pressure substate by itself.

An even more structural corrector-side variant has now also been rejected:

> suppressing raw predictor buoyancy and then adding a hydrostatic field to the
> **final pressure corrector** makes the run much more violent, not less. The
> reduced-pressure branches reach `t≈0.0132`, but `bf_res` rises to about
> `1.14e9` and `div_u` to about `7.5e6`, which is far worse than both the
> control repair and `buoyancy_local`. So the missing cure is not “move
> buoyancy from the predictor into the final corrector pressure”; the evidence
> still points to predictor-side, interface-local buoyancy mismatch in raw
> `u_pred`.

The corresponding predictor-side co-balance check is now also negative:

> assembling the buoyancy predictor substate as
> `u_old + dt*(B/rho - ∇p_prev/rho)` inside the interface band, then applying
> the same interface-local repair, is weaker than plain `buoyancy_local`.
> The full-vector branch gives `3.84e9`, `7.57e10`, `1.69e6`, and the
> vertical-only branch is worse still (`4.05e9`, `8.10e10`, `1.76e6`).
> Therefore the unresolved clue is not a shallow predictor-side
> buoyancy–previous-pressure co-balance; it still points more directly to the
> raw buoyancy-driven interface-local state mismatch itself.

A remaining commutator branch has now also been checked directly:

> the solver was extended with a first-class `predictor_assembly:
> viscous_local` mode, representing `B + Repair(V)` in the predictor assembly
> itself. This branch improves over the older
> `viscous_increment_interface_reconstruct` path, but still stays clearly
> behind `buoyancy_local`. Numerically it lands around
> `3.42e9`, `6.93e10`, `1.63e6`, versus the older viscous-increment branch at
> `4.12e9`, `8.10e10`, `1.74e6`, while `buoyancy_local` remains best at
> `3.02e9`, `6.00e10`, `1.51e6`. So assembly order matters, but the dominant
> unstable contribution still follows the buoyancy-carrying substate, not the
> viscous-only substate.

The fully split commutator branch then made that asymmetry even sharper:

> a first-class `predictor_assembly: buoyancy_viscous_split_local` mode was
> added to test `Repair(B) + Repair(V)` directly. In practice it is
> **bit-identical** to `viscous_local`. Thus, when buoyancy and viscous
> substates are repaired independently and re-added, the buoyancy-side repair
> signal disappears. The useful `buoyancy_local` effect is therefore not a
> separable additive correction; it belongs to the buoyancy-carrying substate
> as a composed predictor assembly object.

A further assembly split sharpens the diagnosis:

> the global mapped-state variant `predictor_assembly: buoyancy_mapped`, which
> keeps the face-consistent buoyancy substate but removes the interface-local
> blend, is **bit-identical** to `viscous_local`. Hence the effective repair is
> not “use the mapped buoyancy state everywhere.” The decisive ingredient is the
> **interface-local localisation** of the buoyancy-carrying predictor substate.

The localisation mechanism is now sharper still:

> replacing the dilated interface band with the strict mask `0 < psi < 1`
> (`predictor_assembly: buoyancy_sharp_local`) makes the branch collapse back to
> the `buoyancy_mapped` / `viscous_local` trajectory. Hence the decisive signal
> is not strict interface localisation by itself, but the **one-cell dilated
> interface band** used in the successful `buoyancy_local` repair.

The band geometry can now be pinned down further:

> splitting the successful one-cell dilation into x-only and y-only variants
> collapses both branches back to the `sharp_local` / `mapped` / `viscous_local`
> trajectory. Hence the effective localisation is neither purely horizontal nor
> purely vertical; it is the **full two-axis dilated interface band**.

The explicit theorem-backed baseline produces one more important constraint:

> a first-class solver-side mode `predictor_assembly: buoyancy_fullband_local`
> was introduced to encode that full two-axis dilated band directly in the
> predictor assembly. It is **bit-identical** to `buoyancy_mapped`, not to the
> stronger `buoyancy_state_interface_reconstruct` branch. Hence the best
> buoyancy signal is not recovered by standalone full-band assembly alone; it
> still depends on the older composed-state buoyancy repair path.

That older path is now reproducible in first-class form:

> a dedicated `predictor_assembly: buoyancy_local` debug branch is
> **bit-identical** to the historical `buoyancy_state_interface_reconstruct`
> strongest-clue run. Hence predictor assembly itself is not the obstacle. The
> obstacle is narrower and more interesting: the explicit `fullband`
> reimplementation does not capture whatever hidden coupled behaviour the
> working `buoyancy_local` path still carries.

The best branch also turns out not to stack with later state repair:

> combining first-class `buoyancy_local` with later `interface_local` or
> `normal_local` whole-`u_pred` repair does not improve the branch. The former
> collapses toward the weaker full-state interface repair, and the latter stays
> better than that but still worse than plain `buoyancy_local`. This means the
> strongest clue is not an additive “fix one more mismatch” effect; it is a
> narrow, easily over-corrected buoyancy-carrying predictor-state repair.

Gate-fix addendum (2026-04-25):

> a later audit found that several first-class `predictor_assembly` branches
> had been evaluated through an incomplete plumbing path: the predictor-stage
> transform closures were only instantiated when legacy boolean repair flags
> were active. After fixing that gate, the buoyancy-family branches separate as
> follows:
>
> - `buoyancy_mapped`: `3.615e9 / 7.287e10 / 1.679e6`
> - `buoyancy_sharp_local`: `3.499e9 / 6.768e10 / 1.585e6`
> - `buoyancy_xband_local`: `3.428e9 / 6.862e10 / 1.627e6`
> - `buoyancy_yband_local`: `3.489e9 / 6.969e10 / 1.634e6`
> - `buoyancy_fullband_local`: `3.021e9 / 6.000e10 / 1.505e6`
>
> Hence the older statement that `buoyancy_fullband_local` collapsed to
> `buoyancy_mapped` must be retracted. The corrected strongest clue is a
> **full two-axis dilated interface-band buoyancy predictor assembly**, which
> is now reproducible as a first-class solver mode and is bit-identical to the
> previous `buoyancy_local` strongest-clue run.

Neighbourhood-shape refinement:

> that corrected full-band clue was then split into two partial neighbourhood
> probes. `buoyancy_edgeband_local` keeps the strict interface band plus only
> the axis-adjacent neighbours from the original strict mask, while
> `buoyancy_corneraug_local` keeps the strict interface band plus only the
> corner augmentation inherited from the full two-axis dilation. The results,
> `3.373e9 / 6.776e10 / 1.617e6` and `3.411e9 / 6.654e10 / 1.580e6`
> respectively, are both weaker than the full-band branch
> (`3.021e9 / 6.000e10 / 1.505e6`). Hence the informative signal is not an
> edge-only or corner-only repair. It is a **cooperative full 3×3
> interface-neighbourhood assembly effect**.

Weighted full-band refinement:

> two weighted variants then tested whether that 3×3 effect is merely a soft
> mixture of edge and corner contributions. `buoyancy_edgehalf_local`
> (`edge=0.5`, `corner=1.0`) produced `3.536e9 / 7.017e10 / 1.633e6`, while
> `buoyancy_cornerhalf_local` (`edge=1.0`, `corner=0.5`) produced
> `3.362e9 / 6.717e10 / 1.603e6`. Both remain clearly worse than the full-band
> optimum `3.021e9 / 6.000e10 / 1.505e6`. Hence the strongest signal is not a
> linear edge/corner interpolation; it is tied to the **hard coupled
> full-neighbourhood mask** itself.

Component-selective full-band refinement:

> the next probe split that hard full-band repair by velocity component.
> `buoyancy_fullband_local_x` produced `3.449e9 / 6.985e10 / 1.636e6`, while
> `buoyancy_fullband_local_y` produced `3.330e9 / 6.607e10 / 1.583e6`.
> Therefore the stabilising signal is predominantly carried by the vertical
> buoyancy component, but not exclusively: the y-only branch remains weaker
> than the full two-component branch (`3.021e9 / 6.000e10 / 1.505e6`). The
> effective repair is thus **vertical-dominant yet still cross-component
> coupled**.

Axis-mixed refinement:

> two hybrid branches then asked whether the y-only gap can be closed by a
> cheaper x-side repair. `buoyancy_fullbandy_mappedx` gives
> `3.369e9 / 6.883e10 / 1.636e6`, and `buoyancy_fullbandy_sharpx` gives
> `3.411e9 / 6.758e10 / 1.606e6`. Both are worse than the plain y-only branch
> (`3.330e9 / 6.607e10 / 1.583e6`). Hence the missing signal is not recovered
> by a light x correction; it appears to belong to the **fully coupled
> two-component full-band predictor state** itself.

Assembly-vs-corrector refinement:

> a final probe in this slice separated predictor assembly from the later
> `V(u_pred)` evaluation. Keeping `predictor_assembly: buoyancy_fullband_local_y`
> but adding `intermediate_state_repair: fullband_x` yields
> `3.181e9 / 6.129e10 / 1.503e6`. This is substantially better than the plain
> y-only branch (`3.330e9 / 6.607e10 / 1.583e6`) and close to the full optimum
> (`3.021e9 / 6.000e10 / 1.505e6`). So the dominant vertical signal belongs to
> predictor assembly, while the missing x-side signal is recovered primarily at
> the **`V(u_pred)` stage**.
>
> Two additional probes tested whether that x-side post correction must itself
> remain a hard full-band object. Using the same y-only predictor assembly but
> switching the post repair to lighter x-only transforms gives
> `3.250e9 / 6.564e10 / 1.591e6` for `postmappedx` and
> `3.209e9 / 6.455e10 / 1.572e6` for `postsharpx`. Both improve over the plain
> y-only branch, and `postsharpx` recovers most of the lost performance, though
> `postfullbandx` remains best. This clarifies the stage separation:
>
> - the dominant y-side buoyancy mismatch is born in predictor assembly;
> - the residual x-side coupling emerges mainly at `V(u_pred)`;
> - the x-side residual does not require a unique hard full-band patch, though
>   a full-band x repair still captures the largest correction.
>
> A final operator-only variant makes this sharper. If the y-side repair is
> kept in predictor assembly but the x-side repair is applied **only** to a
> copied state used for evaluating `V(u_pred)`, the results remain
> bit-identical to the corresponding state-mutating stage-split modes:
>
> - `buoyancy_stagesplit_operatorfullbandx` = `3.181e9 / 6.129e10 / 1.503e6`
> - `buoyancy_stagesplit_operatorsharpx` = `3.209e9 / 6.455e10 / 1.572e6`
>
> Hence the x-side post signal is not carried by the canonical intermediate
> state itself. It is carried by the **evaluation state of the viscous
> operator**, confirming that the missing horizontal coupling is genuinely a
> `V(u_pred)`-stage effect.
>
> Recasting the same branches in gravity-direction language yields
> `buoyancy_gravity_aligned_local`,
> `buoyancy_stagesplit_gravity_postfullband`, and
> `buoyancy_stagesplit_gravity_postsharp`. In the current 2-D benchmark they
> are bit-identical to the historical `y/x`-named variants, so the true
> invariant is **gravity-aligned vs transverse coupling**, not literal
> coordinate labels.
