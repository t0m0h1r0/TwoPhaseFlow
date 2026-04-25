---
ref_id: WIKI-E-031
title: "ch13 Static α=2 Rising-Bubble Diagnosis: Hypothesis Matrix and Verdicts"
domain: experiment
status: RESOLVED
superseded_by: null
sources:
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_debug/data.npz
    git_hash: f91e314
    description: baseline debug run with full step diagnostics
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceproj_debug/data.npz
    git_hash: 4b0c245
    description: explicit face-flux projection debug comparison
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug/data.npz
    git_hash: f91e314
    description: PoC A — preserve projected faces
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug/data.npz
    git_hash: f91e314
    description: PoC B — projection-consistent buoyancy injection
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facecanonical_debug/data.npz
    description: PoC C — explicit face-canonical state carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facegate_debug/data.npz
    description: PoC D — face-divergence acceptance gate
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facepredictor_debug/data.npz
    description: PoC E — face-native predictor RHS assembly
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_debug/data.npz
    description: PoC F — face-native predictor state carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_incremental_debug/data.npz
    description: PoC G — incremental face-base predictor carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_incremental_force_debug/data.npz
    description: PoC H — incremental carry plus face-force RHS
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_noslip_debug/data.npz
    description: PoC I — no-slip-consistent face carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_cfl_debug/data.npz
    description: PoC J — face-aware CFL control
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_primitive_debug/data.npz
    description: PoC K — face-primitive predictor synchronisation
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_fccdflux_debug/data.npz
    description: PoC L — FCCD-flux convection on top of incremental face carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_debug/data.npz
    description: PoC M — explicit viscous predictor on top of incremental face carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_buoyancyproj_debug/data.npz
    description: PoC N — explicit viscous predictor plus projection-consistent buoyancy
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_richardson_debug/data.npz
    description: PoC O — Richardson(Picard) viscous predictor on top of incremental face carry
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_constress_debug/data.npz
    description: PoC P — explicit viscous predictor with conservative-stress operator
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_ccdlegacy_debug/data.npz
    description: PoC Q — explicit viscous predictor with CCD-legacy stress operator
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_richardson_buoyancyfaceresidualstagesplit_debug/data.npz
    description: phase-separated projection closure — stable to T=0.05
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_richardson_buoyancyfaceresidualqjumpstagesplit_debug/data.npz
    description: q-jump PoC after phase-separated projection closure — stable to T=0.05
depends_on:
  - "[[WIKI-T-063]]: FCCD face-flux PPE"
  - "[[WIKI-T-066]]: body-force discretization in variable-density NS"
  - "[[WIKI-T-068]]: FCCD face-flux projector"
  - "[[WIKI-T-070]]: projection-closure diagnosis"
  - "[[WIKI-T-071]]: face-canonical survey and PoC ladder"
tags: [ch13, rising_bubble, alpha_2, wall_bc, blowup, projection_closure, buoyancy]
compiled_by: ResearchArchitect
compiled_at: "2026-04-24"
---

# ch13 Static α=2 Rising-Bubble Diagnosis: Hypothesis Matrix and Verdicts

## Resolution update — 2026-04-25

The dominant defect is now identified: FCCD PPE used the phase-separated
coefficient space, but the projection corrector and face-native buoyancy
residual still used harmonic mixture-density pressure fluxes. This mixed
operators:

- PPE: `D_f[(1/rho)_f^sep G_f(p)]`, cross-phase faces cut
- corrector/residual: `D_f[(1/rho)_f^mix G_f(p)]`, cross-phase faces coupled

After making `FCCDDivergenceOperator.pressure_fluxes()` accept
`coefficient_scheme="phase_separated"` and passing that policy from the NS
pipeline into the predictor residual and corrector, the Richardson face-residual
case reaches `T=0.05` without blowup.

| Run | Verdict | Final snapshot |
|---|---|---|
| `...buoyancyfaceresidualstagesplit_debug` | PASS to `T=0.05` | `KE=1.119e-05`, `ppe_rhs=1.174e+02`, `bf_res=1.777e+02`, `div_u=4.353e-01` |
| `...buoyancyfaceresidualqjumpstagesplit_debug` | PASS to `T=0.05` | `KE=1.125e-05`, `ppe_rhs=1.192e+02`, `bf_res=1.077e+02`, `div_u=4.190e-01` |
| `...buoyancyfaceresidualstagesplit_longviz` | PASS to `T=0.5` | `KE=9.491e-04`, `ppe_rhs=6.565e+02`, `bf_res=1.704e+02`, `div_u=1.241e+00`; `psi`/velocity/pressure PDFs every `0.05` |

The q-jump hypothesis is therefore not the primary cause. It is a useful
consistency check, but the necessary stabilising fix is identical phase
separation in PPE, residual assembly, and projection.

## Baseline observation

The baseline debug case blows up at `step=6`, `t=0.0148`.

What fails first is not mass conservation but the projection chain:

- `volume_conservation ~ 7e-08`
- `ppe_rhs_max: 1.33e+01 → 9.06e+09`
- `bf_residual_max: 2.36e+00 → 1.98e+11`
- `div_u_max: 2.48e-03 → 6.54e+05`

## Hypothesis matrix

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Surface tension is the primary cause | Rejected | `sigma=0` still blows up |
| Gravity is the required trigger | Supported | `g=0` stays stable in short-horizon probe |
| Reinitialization causes the instability | Rejected | disabling reinit makes the run worse |
| Non-uniform `α=2` grid is the only cause | Rejected | `alpha=1` delays but does not remove blowup |
| Face-flux projection is absent | Rejected | FCCD path already enables it; forcing it off worsens the run |
| Wall zeroing after the corrector is the dominant cause | Weakened | face-preserve PoC does not improve stability |
| Buoyancy placement alone is the dominant cause | Rejected | projection-consistent buoyancy PoC is worse |
| Nodal/face source-of-truth mismatch is the dominant cause | Most plausible | all tests align with this interpretation |

## PoC verdicts

### PoC A — preserve projected faces

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug.yaml`

Result:

- blowup remains at `step=6`, `t=0.0147`
- `div_u_max` worsens to `2.31e+06`

Verdict:

Preserving projected faces inside the step is not enough if the wider runtime
still treats nodal velocity as the canonical state.

### PoC B — projection-consistent buoyancy

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug.yaml`

Result:

- blowup moves earlier to `step=6`, `t=0.0118`
- `ppe_rhs_max` worsens to `3.31e+12`
- `bf_residual_max` worsens to `4.28e+13`

Verdict:

Changing the buoyancy injection path without changing the canonical projection
state aggravates the instability.

### PoC C — explicit face-canonical carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facecanonical_debug.yaml`

Result:

- blowup moves to `step=3`, `t=0.0164`
- `ppe_rhs_max` at the blowup step is lower than the baseline end state, but
  `div_u_max` jumps much earlier and much harder
- same-step comparison against the baseline prefix shows:
  - `ppe_rhs_max`: `6.29e+01 → 6.79e+06`
  - `bf_residual_max`: `1.55e+04 → 7.05e+08`
  - `div_u_max`: `2.42e+01 → 2.65e+07`

Verdict:

Making face state explicit across the step contract is a useful architectural
move, but by itself it is not a stabilising fix. The result supports the idea
that explicit carry must be paired with a stronger face-side divergence gate and
same-locus closure, not only with a better state handoff.

### PoC D — face-divergence acceptance gate

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facegate_debug.yaml`

Result:

- blowup remains at `step=3`, `t=0.0163`
- `face_divergence_gate_passed = 0` on every recorded step
- `face_div_u_max` stays larger than `node_div_u_max` on every recorded step

Verdict:

The gate is diagnostically useful but does not improve stability. It shows that
the carried face state is not yet the better incompressibility witness on this
path. This pushes the likely defect upstream, toward the predictor/corrector
construction itself rather than the carry policy alone.

### PoC E — face-native predictor RHS assembly

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facepredictor_debug.yaml`

Result:

- blowup remains at `step=3`, `t=0.0164`
- all tracked arrays are bit-identical to PoC C

Verdict:

This PoC is a useful no-op result. It shows that, on the current FCCD path, the
predictor RHS is already effectively face-native enough that this refactor does
not change the trajectory. The missing ingredient therefore lies deeper than
RHS assembly alone.

### PoC F — face-native predictor state carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_debug.yaml`

Result:

- the first run appeared stable only because the YAML had accidentally omitted
  the `initial_condition` block, leaving a uniform gas field
- after restoring the bubble initial condition and re-running, blowup occurs at
  `step=6`, `t=0.0116`
- the corrected run ends with `ppe_rhs_max = 4.58e+12`,
  `bf_residual_max = 6.23e+13`, and `div_u_max = 3.65e+7`

Verdict:

Promoting `u*_face` into the grouped step state is not enough. With the correct
problem definition restored, this PoC is actually worse than the baseline. The
campaign therefore moves from "make the predictor face state explicit" to the
stricter requirement of a more completely face-native predictor/corrector chain
that stays consistent with the transported interface state.

### PoC G — incremental face-base predictor carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_incremental_debug.yaml`

Result:

- blowup occurs at `step=5`, `t=0.0111`
- `ppe_rhs_max = 3.06e+09`
- `bf_residual_max = 7.99e+10`
- `div_u_max = 1.78e+06`

Verdict:

This slice is directionally better than PoC F: evolving the predictor faces
from the carried canonical face state plus a face-native increment clearly
reduces the residual growth relative to the naive `u*_face` carry path. But it
still blows up earlier than the baseline, and `div_u_max` remains too large.
The next defect therefore lies beyond the predictor-base choice alone.

### PoC H — incremental carry plus face-force RHS

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_incremental_force_debug.yaml`

Result:

- the tracked arrays are bit-identical to PoC G
- blowup remains at `step=5`, `t=0.0111`

Verdict:

On the current FCCD path, moving the explicit force RHS from nodal divergence
to face divergence does not change the trajectory once the incremental
face-base predictor path is active. This points away from the force-RHS
assembly site and back toward the deeper predictor/corrector state evolution.

### PoC I — no-slip-consistent face carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_noslip_debug.yaml`

Result:

- the tracked arrays are bit-identical to PoC G
- blowup remains at `step=5`, `t=0.0111`

Verdict:

Boundary-order consistency was a reasonable suspicion, but this PoC rules it
down. Enforcing no-slip directly on the carried face state does not change the
trajectory on the current stack.

### PoC J — face-aware CFL control

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_cfl_debug.yaml`

Result:

- the timestep controller does react: the step-4 timestep is cut roughly in half
- nevertheless blowup remains at `step=5`, now at `t=0.0109`
- diagnostics worsen to `ppe_rhs_max = 5.75e+10`,
  `bf_residual_max = 3.89e+12`, and `div_u_max = 9.47e+06`

Verdict:

Face-aware CFL control is not the cure. It changes the schedule, but it does
not prevent divergence and in this short debug benchmark it makes the failure
sharper.

### PoC K — face-primitive predictor synchronisation

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_primitive_debug.yaml`

Result:

- the tracked arrays are bit-identical to PoC G
- blowup remains at `step=5`, `t=0.0111`

Verdict:

This rules out a subtler reconciliation issue: synchronising nodal `u*` from
`u*_face` and skipping the separate nodal BC application still does not change
the trajectory. The remaining defect is deeper than the final predictor-state
sync point.

### PoC L — FCCD-flux convection on top of incremental face carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_fccdflux_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0111`
- the failure-time diagnostics are substantially worse than PoC G:
  `ppe_rhs_max = 1.16e+11`, `bf_residual_max = 1.26e+13`,
  `div_u_max = 2.94e+07`

Verdict:

Changing the momentum-convection operator to the existing FCCD face-flux form
is not enough. On this benchmark it makes the predictor/corrector loop more
violent, which suggests that the unresolved defect is not "just use a
face-flux convection scheme" but a deeper mismatch in how the full
variable-density predictor/corrector state evolves.

### PoC M — explicit viscous predictor on top of incremental face carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0112`
- compared with PoC G, the failure-time diagnostics improve slightly:
  `ppe_rhs_max = 2.88e+09`, `bf_residual_max = 6.83e+10`,
  `div_u_max = 1.63e+06`

Verdict:

This is the first predictor-side slice that helps after PoC G without being a
pure no-op. It does not stabilise the benchmark, but it suggests that the
viscous predictor time update contributes to the closure defect.

### PoC N — explicit viscous predictor plus projection-consistent buoyancy

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_buoyancyproj_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0111`
- compared with PoC M, the diagnostics move only marginally and not in a
  clearly better direction:
  `ppe_rhs_max = 3.32e+09`, `bf_residual_max = 7.88e+10`,
  `div_u_max = 1.75e+06`

Verdict:

Once the viscous predictor is made explicit, moving buoyancy into the
projection-consistent force channel does not buy further stability. The
remaining problem is therefore not buoyancy locus alone.

### PoC O — Richardson(Picard) viscous predictor on top of incremental face carry

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_richardson_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0112`
- compared with PoC G, the diagnostics improve only partially:
  `ppe_rhs_max = 3.42e+09`, `bf_residual_max = 6.93e+10`,
  `div_u_max = 1.63e+06`
- enabling viscous CFL bookkeeping for `richardson_picard` does not alter the
  trajectory on this benchmark, which means viscous CFL is not the active
  limiter here

Verdict:

`Richardson(Picard)` is directionally better than the raw Picard/Heun path, but
not as effective as the fully explicit viscous slice. This keeps the focus on
the viscous predictor update law, while also showing that timestep bookkeeping
is not the binding issue in this rising-bubble case.

### PoC P — explicit viscous predictor with conservative-stress operator

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_constress_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0111`
- the diagnostics are worse than PoC M:
  `ppe_rhs_max = 4.14e+09`, `bf_residual_max = 8.23e+10`,
  `div_u_max = 1.77e+06`

Verdict:

The fully conservative low-order stress operator is not the cure. In this
benchmark it gives back some of the gain that came from the explicit-viscous
predictor slice.

### PoC Q — explicit viscous predictor with CCD-legacy stress operator

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_faceustar_explicitvisc_ccdlegacy_debug.yaml`

Result:

- blowup remains at `step=5`, `t=0.0111`
- the diagnostics are slightly worse than PoC M, but better than PoC P:
  `ppe_rhs_max = 3.04e+09`, `bf_residual_max = 7.22e+10`,
  `div_u_max = 1.67e+06`

Verdict:

`ccd_stress_legacy` is not better than the current `ccd_bulk` hybrid either.
Among the tested viscous-spatial options, the current `ccd_bulk` slice remains
the least bad.

## Experimental takeaway

The experimental campaign rules out several nearby explanations and leaves one
dominant reading:

> The face-stable object solved by the FCCD PPE is not preserved as the solver's
> canonical post-corrector state, and buoyancy repeatedly excites that closure
> gap.

This result raises the priority of a face/staggered canonical-state design for
the next implementation round. It also adds an operational lesson: PoC
experiments need config-invariant checks for initial-condition completeness, or
they can generate convincing but invalid false positives.

The newest experiment adds one numerical lesson:

> the carried face state should evolve by face-native increments, but that
> alone still does not deliver a stable variable-density projection loop.

The newest no-op result adds one more refinement:

> after the incremental face-base carry is in place, the explicit force RHS is
> already effectively same-locus enough that moving it fully to face space does
> not change the instability.

The newest pair of probes narrows the cause again:

> neither boundary-order consistency of the carried face state nor face-aware
> CFL control explains the instability; the defect is deeper in the state
> evolution itself.

The latest no-op strengthens that conclusion:

> even a face-primitive predictor synchronisation step does not help, so the
> unresolved defect is likely inside the predictor update operator rather than
> in later state reconciliation.

The newest operator-level probe tightens the reading further:

> swapping the momentum convection term itself to FCCD flux form still does not
> stabilise the bubble path; the remaining defect is broader than convection
> locus alone and likely lives in the coupled variable-density
> predictor/corrector evolution.

The latest two slices refine the same reading:

> making the viscous predictor explicit does help a little, which points to the
> predictor time update as a real part of the defect, but re-routing buoyancy
> through the projection-consistent force channel on top of that does not add
> meaningful benefit.

The newest CN-strategy slice adds one more refinement:

> replacing Picard/Heun with `Richardson(Picard)` also helps a little, but not
> enough to stabilise the run, and correcting the viscous CFL bookkeeping for
> that strategy does not change the trajectory. The benchmark is therefore not
> limited by viscous CFL; the deeper issue remains inside the predictor update
> law itself.

The newest viscous-spatial pair sharpens that again:

> neither `conservative_stress` nor `ccd_stress_legacy` beats the current
> `ccd_bulk` hybrid when the predictor is made explicit. So the remaining
> defect is not simply that the wrong viscous spatial operator is selected.

The newest CN-intermediate-state probe narrows the cause one step further:

> even when the Picard/Richardson intermediate predictor state is explicitly
> wall-constrained before evaluating `V(u_pred)`, the rising-bubble run still
> blows up at the same outer step and the failure diagnostics get worse. So the
> unresolved defect is not just missing wall BC on the intermediate nodal
> state; it is deeper in the variable-density CN predictor coupling itself.

The newest face-reconstruction probe adds the first positive CN-side signal:

> when the Picard/Richardson intermediate state is reconstructed from the
> carried face state before evaluating `V(u_pred)`, the run still blows up, but
> `KE`, `bf_res`, and `div_u` all improve relative to the Richardson baseline.
> This supports the view that the remaining defect is in the state-to-operator
> coupling of the variable-density CN predictor, and that face-consistent
> intermediate states are a promising direction.

The newest endpoint-reconstruction probe refines that signal:

> reconstructing **both** CN endpoint evaluations from the carried face state
> makes the run worse again. So the useful part is not replacing the nodal base
> state wholesale; it is the targeted coupling of the *intermediate / defect*
> state back to the carried face state.

The newest viscous-increment probe narrows it even further:

> reconstructing only the viscous increment branch from the carried face state
> also makes the run worse. So the helpful mechanism is not a viscous-only face
> correction; it is the face-consistent coupling of the **full intermediate
> predictor state** before evaluating `V(u_pred)`.

The newest one-step iterate probe adds an important refinement:

> if the PoC S intermediate face reconstruction is wrapped in one extra
> fixed-point-style iterate, `ppe_rhs` improves substantially, but the better
> `bf_res` and `div_u` seen in PoC S mostly disappear again. So the missing
> repair is not simply “iterate the same face-coupled predictor law once more”.
> The useful mechanism in PoC S is more specific than naive fixed-point
> iteration.

The newest relaxed-iterate probe closes off another tempting shortcut:

> taking the extra face-coupled intermediate iterate from PoC V and simply
> relaxing it with a convex blend (`ω=0.5`) performs worse than both the
> one-shot PoC S and the full-iterate PoC V. So the missing repair is not a
> monotone iterate-strength issue that can be tuned by damping the same map.

The newest bulk-only probe rules out another attractive interpretation:

> if the face-consistent correction is applied only to the bulk part of the
> `ccd_bulk` viscous response, the run becomes almost baseline-like and does
> not reproduce the PoC S improvement. So the useful mechanism in PoC S is not
> a bulk-only / divergence-sensitive repair by itself.

The newest interface-band defect probe is the strongest positive structural
signal so far:

> if we keep the raw nodal intermediate state, but replace only the
> interface-band part of `V(u_pred)` with the response from a face-consistent
> transformed copy, we recover almost all of the PoC S benefit. This strongly
> suggests that the remaining instability is tied to an interface-band
> operator defect, not to a whole-state mismatch or a bulk-only inconsistency.

The newest normal-only follow-up tightens that diagnosis:

> if we take the same interface-band operator defect but project it onto the
> local interface normal before reinjection, the improvement disappears and the
> run falls back toward baseline behaviour. So the useful signal in the
> interface-band correction is not the normal / pressure-sensitive part alone;
> some tangential or full-vector structure is required.

The newest tangential-only follow-up closes the complementary branch:

> if we instead remove the normal part and reinject only the tangential
> remainder of the same interface-band operator defect, the run gets worse than
> baseline. So the useful signal is not the tangential / shear-coupled part in
> isolation either. The best current interpretation is that the stabilizing
> correction requires the full vector interface-band defect, not either
> projected component alone.

The newest operator-family split changes that picture in an important way:

> if we split the interface-band defect by viscous-operator family instead of
> by geometric projection, the diagonal-family correction nearly reproduces the
> full interface-band benefit, while the shear-family correction does not. So
> the useful signal is not “normal vs tangential geometry”, but rather
> “diagonal vs off-diagonal operator family”, with the diagonal family carrying
> most of the stabilizing effect.

The newest axis split of the diagonal-family correction adds another bound:

> if the diagonal-family correction is restricted to either `u` alone or `v`
> alone, the benefit is lost. The `v`-only case is somewhat less bad than the
> `u`-only case, which matches the buoyancy direction, but neither reproduces
> the full diagonal-family improvement. So the useful signal is not a
> single-component one; it is a coupled two-component diagonal-family effect.

The newest trace-like follow-up rules out a narrower divergence-style reading:

> if the interface-band diagonal-family correction is reduced further to a
> trace-like / divergence-like coupled block, its benefit disappears and the
> run worsens relative to the full diagonal-family correction. So the useful
> signal is not captured by a pure `∇(μ ∇·u)`-style repair; it still requires a
> broader coupled diagonal-family correction.

The newest inverse-density weighting follow-up rules out a simple `1/ρ`
explanation:

> if the successful diagonal-family interface defect is merely reweighted
> toward the low-density side using a bounded normalized `1/ρ` factor, the run
> gets worse, not better. So the remaining stabilizing signal is not just
> “apply more correction where `1/ρ` is large”.

The newest pressure-sensitive weighting follow-up rules out the simplest
pressure-amplitude reading too:

> if the diagonal-family interface defect is weighted by a previous-step
> pressure/force mismatch witness `|∇p^n - f/ρ|`, the run keeps roughly the
> same `ppe_rhs` level but loses the best `bf_res` / `div_u` improvement of
> the plain diagonal-family correction. So the remaining useful signal is not
> captured by a scalar pressure-sensitive weight either; it still looks like a
> more structural coupled diagonal-family mismatch.

The newest nontrace follow-up rules out a simple “diagonal minus trace”
decomposition:

> if we subtract the trace-like block from the successful diagonal-family
> interface defect and keep only the residual nontrace part, the run gets
> worse again. So the useful stabilizing signal is not carried by a separable
> nontrace diagonal block; it requires the broader **coupled full
> diagonal-family** correction.

The newest conservative-generation follow-up shifts the focus upstream:

> if the diagonal-family defect is regenerated with the conservative
> low-order family instead of the native `ccd_bulk` mixed operator, the run
> remains close to the best full diagonal-family result. So the key signal is
> probably not a very specific mixed normal/tangent stencil; it looks more
> like a **state-generated interface-band defect** that survives across
> operator families.

The newest transformed-state split gives the strongest upstream clue so far:

> if the face-consistent transformed intermediate state is projected onto the
> local interface **normal** *before* the diagonal-family operator is
> evaluated, the run reproduces the best diagonal-family result almost exactly.
> But the same split onto the **tangent** direction is much worse than
> baseline. So the useful stabilizing signal is not a tangential/shear-like
> transformed-state effect; it is carried primarily by the
> **normal-projected transformed intermediate state**, and only then expressed
> through the coupled diagonal-family operator.

The newest upstream value/density follow-ups refine that picture:

> if the full viscous operator is evaluated directly on the
> normal-projected transformed intermediate state, most of the gain is
> preserved. So the useful signal is already present at the transformed-state
> level, before diagonal-family isolation. But adding the old bounded `1/ρ`
> weighting on top of the successful normal-state diagonal-family correction
> does not help and slightly degrades the run. So the remaining effect is not
> well explained as a missing scalar density-coupled amplitude; it looks more
> like a state-generated normal-side signal that the diagonal-family operator
> simply extracts a little more cleanly.

The newest interface-local value-transform follow-up narrows that again:

> if the face-consistent transformed intermediate state is kept only inside the
> interface band, most of the gain from the older full-field face-consistent
> transform survives. So the upstream value-level signal is indeed primarily
> **interface-local**. The normal-projected version is only slightly different
> from the interface-band full-vector version, which suggests that interface
> localization is the dominant ingredient at the value-transform stage, while
> the normal projection is a smaller refinement.

The newest value+trace combo closes the next branch:

> if a trace-like / divergence-like witness is layered on top of the already
> good interface-local value transform, the run gets much worse. So the
> remaining benefit is not coming from a missing trace-style derived witness.
> At this point the evidence says the main useful upstream signal is the
> **interface-local value/state transform itself**, while trace-like witness
> corrections are counterproductive.

The newest value+diagonal combo closes the adjacent branch too:

> if a diagonal-family witness is layered on top of the already-good
> interface-local value transform, the run also gets worse
> (`ppe_rhs=3.76e9`, `bf_res=7.60e10`, `div_u=1.72e6`). So the remaining
> benefit is not “interface-local value transform plus a helpful
> diagonal-family witness.” The best current reading is still that the
> **interface-local transformed intermediate state itself** is the useful
> upstream repair, while added derived witnesses over-correct it.

The newest Picard-vs-Richardson comparison adds one more useful cut:

> if the same interface-local transformed-state repair is run under plain
> `picard` instead of `richardson_picard`, the run is still improved relative
> to the old baseline, but it is clearly worse than the Richardson version
> (`ppe_rhs=3.65e9`, `bf_res=8.30e10`, `div_u=1.76e6` vs
> `3.36e9`, `6.73e10`, `1.61e6`). So the repair is not “just Richardson,” but
> the NS-side viscous time advance still matters. This pushes suspicion further
> toward the CN predictor closure rather than the level-set TVD-RK3 path.

The newest matrix-free implicit CN PoC gives a more nuanced answer:

> replacing the viscous predictor with a full-block matrix-free implicit CN
> solve while keeping the same interface-local transformed-state repair does
> **not** beat the Richardson branch. It lands at
> `ppe_rhs=3.84e9`, `bf_res=7.83e10`, `div_u=1.75e6`, and the GMRES solve
> reports non-convergence (`info=80`). So a naive implicit solve is not a
> short path to stability here; the coupling still matters, and this specific
> implicit PoC is solver-limited.

The newest diagonal-implicit split closes the obvious follow-up:

> making only the diagonal family implicit and keeping the shear family
> explicit does not rescue the result either. The run lands at
> `ppe_rhs=4.07e9`, `bf_res=8.20e10`, `div_u=1.78e6`, again with a non-converged
> GMRES warning (`info=80`). So even the memo-aligned diagonal-implicit split is
> not a short path in the current implementation; the best branch still remains
> `richardson_picard` plus the interface-local transformed intermediate state.

Alias standardization follow-up:

> introducing `intermediate_state_repair: interface_local` as a cleaner config
> alias reproduces the current best branch exactly. The candidate YAML is
> bit-identical to the earlier
> `richardson_picard + intermediate_state_interface_reconstruct=true` branch for
> `times`, `kinetic_energy`, `ppe_rhs_max`, `bf_residual_max`, and `div_u_max`.
> So this is a usability/standardization step, not a new numerical result; the
> best current practical repair is now cleanly expressible via the alias.

The newest upstream-localization cut sharpens the diagnosis:

> moving the same interface-local transformed-state repair upstream does **not**
> reproduce the improvement. Applying it already at `V(u^n)` yields
> `ppe_rhs=3.67e9`, `bf_res=7.55e10`, `div_u=1.71e6`; applying it only to the
> pre-explicit viscous increment state is worse again
> (`4.12e9`, `8.10e10`, `1.74e6`). The best branch remains the repair applied to
> the fully composed raw intermediate state `u_pred`. So the useful signal is
> not “fix the viscous branch early,” but rather “repair the complete
> interface-local intermediate state before evaluating `V(u_pred)`.”

The newest explicit-branch split sharpens that result:

> the previous cut only ruled out **viscous-side** upstream pieces. Repairing
> the explicit-side intermediate state `u_old + dt(explicit_rhs / rho)` almost
> reproduces the best branch (`3.34e9`, `6.71e10`, `1.61e6`), while
> convection-only repair is clearly bad (`4.09e9`, `8.35e10`, `1.80e6`). Most
> importantly, buoyancy-only repair is now the best observed branch
> (`3.02e9`, `6.00e10`, `1.51e6`). So the dominant useful signal is no longer
> best described as “full raw `u_pred` only”; it is more specifically an
> **interface-local mismatch injected by the buoyancy-driven explicit
> contribution to `u_pred`**.

Non-debug candidate audit:

> a later attempt to lift this branch into a non-debug candidate first appeared
> to run much longer, but that turned out to be a configuration false positive:
> the candidate YAML had lost the bubble `initial_condition`, so `psi` became a
> nearly uniform tiny positive field instead of a real bubble. After restoring
> the circular gas-bubble IC, the candidate again blows up at `step=5`,
> `t=0.0112`. So `buoyancy_local` remains an important diagnostic signal, but
> it is **not yet** a validated production fix.

Face-density buoyancy assembly follow-up:

> a more structural PoC then assembled the buoyancy-only predictor substate
> directly on face density before reconstructing nodes. This did **not**
> outperform the simpler buoyancy-local state repair. The result
> (`3.40e9`, `6.76e10`, `1.60e6`) is only marginally different from the control
> branch and clearly weaker than buoyancy-local repair (`3.02e9`, `6.00e10`,
> `1.51e6`). So the remaining defect is not captured by the simple statement
> “the buoyancy coefficient must be evaluated on faces”; the stronger clue is
> still the assembled interface-local buoyancy state itself.

Latest upstream split:

> three additional probes then asked whether the strongest buoyancy-local clue
> is really a buoyancy-only value repair, or whether it reflects a more
> structural assembly issue. Repairing only the **vertical component** of the
> buoyancy-local state already almost reproduces the best buoyancy-local branch
> (`3.33e9`, `6.61e10`, `1.58e6`). Repairing the coupled
> `u_old + dt * (B/rho + V(u^n))` state is also clearly helpful
> (`3.26e9`, `6.37e10`, `1.54e6`) and outperforms the generic full-`u_pred`
> repair. This means the remaining instability is not just “bad density
> sampling” or “bad witness choice”; it is now most plausibly a
> **buoyancy-driven vertical interface-band mismatch, with a secondary but real
> buoyancy–viscous assembly coupling**.

See also:

> `docs/memo/ch13_10_literature_backed_hypothesis_matrix.md` for the full
> literature-backed hypothesis matrix and current ranked next steps.

Reduced-pressure proxy follow-up:

> the next structural check combined the existing
> `projection_consistent_buoyancy` path with the current strongest branches
> (`buoyancy_local`, `buoyancy_local_y`, `buoyancy_viscous_local`). All three
> combinations were negative: for example,
> `projection-consistent + buoyancy-local` gave
> `3.28e9`, `7.80e10`, `1.74e6`, much worse than plain `buoyancy_local`
> (`3.02e9`, `6.00e10`, `1.51e6`). So the current in-repo projection-side
> buoyancy treatment is **not** the missing hydrostatic cure; the remaining
> defect still points more strongly to the predictor-side buoyancy state
> assembly itself.

Structural hydrostatic predictor split follow-up:

> a stronger hydrostatic test then replaced the buoyancy-only predictor
> substate by a column-wise hydrostatic-pressure reconstruction before the CN
> corrector. This was more structural than the projection-side proxy, but it
> still did **not** beat `buoyancy_local`. Hydrostatic-only was clearly worse
> (`3.47e9`, `8.15e10`, `1.82e6`), and even hydrostatic plus buoyancy-local
> repair (`3.27e9`, `6.60e10`, `1.60e6`) remained behind plain
> `buoyancy_local` (`3.02e9`, `6.00e10`, `1.51e6`). So the best current clue
> remains the assembled interface-local buoyancy state mismatch itself, not a
> standalone hydrostatic-pressure substate replacement.

Reduced-pressure corrector follow-up:

> a further structural check suppressed raw predictor buoyancy and instead
> added a hydrostatic field directly to the **final corrector pressure**. This
> also failed badly. The reduced-pressure branches reached about `t≈0.0132`,
> but the diagnostics degraded to `bf_res≈1.14e9` and `div_u≈7.5e6`, far worse
> than both the control repair and `buoyancy_local`. So the missing fix is not
> “take buoyancy out of the predictor and compensate it in the final
> corrector”; the strongest clue remains predictor-side interface-local
> buoyancy mismatch in raw `u_pred`.

Predictor-side buoyancy–pressure co-balance follow-up:

> a more local predictor-side variant then tried to co-balance buoyancy with
> the **previous-step pressure gradient inside the interface band** before
> applying the same interface-local state repair. This also failed. The
> full-vector branch degraded to `3.84e9`, `7.57e10`, `1.69e6`, and the
> vertical-only branch was even worse (`4.05e9`, `8.10e10`, `1.76e6`), both
> behind plain `buoyancy_local` (`3.02e9`, `6.00e10`, `1.51e6`). So the
> missing predictor-side fix is not a shallow “buoyancy minus previous
> pressure gradient” co-balance; the strongest clue still remains raw
> buoyancy-driven interface-local state mismatch itself.

Redesign handoff:

> this diagnosis is now carried forward as an implementation target in
> `WIKI-X-034` and `docs/memo/ch13_11_buoyancy_predictor_redesign_spec.md`.
> The next meaningful solver change is therefore not another late witness term,
> but a buoyancy-aware predictor assembly in which the buoyancy-carrying
> intermediate substate is constructed and transformed before the final raw
> `u_pred` composition.

Theory formalisation:

> the strict theoretical construction of this result is now captured in
> `WIKI-T-072` and `SP-Q`. The current best reading is that the unstable object
> is the **fully assembled raw intermediate state** `u_pred`, not buoyancy,
> pressure, or viscous witnesses taken in isolation. In other words, the
> leading defect is a buoyancy-driven interface-band state mismatch that enters
> `V(u_pred)` before the projection stage has a chance to regularise it.

Assembly-order commutator follow-up:

> a first-class `predictor_assembly: viscous_local` mode was then added to
> evaluate the remaining `B + Repair(V)` branch directly in the predictor
> assembly. This branch is **better** than the older
> `viscous_increment_interface_reconstruct` path, but still clearly behind
> `buoyancy_local`. The new viscous-only assembly lands near
> `3.42e9`, `6.93e10`, `1.63e6`, whereas `buoyancy_local` stays at
> `3.02e9`, `6.00e10`, `1.51e6`. So assembly order matters, but the dominant
> instability signal still follows the buoyancy-carrying substate, not the
> viscous-only substate.

Split dual-substate follow-up:

> a first-class `predictor_assembly: buoyancy_viscous_split_local` mode then
> tested the remaining commutator branch `Repair(B) + Repair(V)`. In practice
> it was **bit-identical** to `viscous_local`: the run ended at the same
> `3.42e9`, `6.93e10`, `1.63e6`, and the sampled diagnostics matched exactly.
> So the useful `buoyancy_local` signal does not survive when buoyancy and
> viscous substates are repaired independently and then re-added. The dominant
> clue still points to the buoyancy-carrying substate as a composed object.

Mapped-state follow-up:

> a first-class `predictor_assembly: buoyancy_mapped` branch then tested whether
> the useful `buoyancy_local` signal comes from the mapped face-consistent
> buoyancy substate itself, or from the interface-band localisation step. The
> answer is now clear: `buoyancy_mapped` is **bit-identical** to
> `viscous_local`, finishing at roughly `3.42e9`, `6.93e10`, `1.63e6`. So the
> mapped buoyancy state alone is not the cure. The useful signal appears only
> once that buoyancy-carrying substate is **localised to the interface band**.

Sharp-band follow-up:

> a strict-mask branch `predictor_assembly: buoyancy_sharp_local` then removed
> the one-cell band dilation and kept only the literal `0 < psi < 1` interface
> set. This branch is **bit-identical** to `buoyancy_mapped` and
> `viscous_local`, finishing again at roughly `3.42e9`, `6.93e10`, `1.63e6`.
> Thus, the useful `buoyancy_local` effect is not caused by mere interface
> localisation; it depends specifically on the **dilated interface band**.

Axis-dilated band follow-up:

> x-only and y-only one-cell dilation were then tested separately via
> `predictor_assembly: buoyancy_xband_local` and
> `predictor_assembly: buoyancy_yband_local`. Both are **bit-identical** to the
> `sharp_local` / `buoyancy_mapped` / `viscous_local` trajectory. So the useful
> `buoyancy_local` effect is not tied to a single dilation direction; it depends
> on the **full two-axis dilated interface band**.

The explicit full-band baseline was then checked directly:

> a solver-side branch `predictor_assembly: buoyancy_fullband_local` rebuilt the
> full two-axis dilated interface-band transform explicitly, without routing
> through the viscous blend helper. Surprisingly, this branch is
> **bit-identical** to `buoyancy_mapped`, not to the stronger
> `buoyancy_state_interface_reconstruct` signal. So the decisive signal is not
> just “full-band predictor localisation” as a standalone assembly mode; it
> still sits in the older composed-state buoyancy repair path.

That ambiguity is now reduced further:

> a dedicated `predictor_assembly: buoyancy_local` debug branch is
> **bit-identical** to the older `buoyancy_state_interface_reconstruct: true`
> strongest-clue run. So the useful signal is reproducible as a first-class
> predictor assembly mode after all. The inconsistency is narrower: it is the
> explicit `buoyancy_fullband_local` reimplementation that fails to match, not
> the predictor-assembly formulation itself.

Stacking tests then clarified how fragile the good branch is:

> `predictor_assembly: buoyancy_local` plus a later `interface_local`
> intermediate-state repair falls back to about `3.36e9 / 6.74e10 / 1.61e6`,
> while the `normal_local` stack gives `3.12e9 / 6.31e10 / 1.56e6`. Both are
> worse than plain `buoyancy_local` (`3.02e9 / 6.00e10 / 1.51e6`). So the best
> buoyancy-local signal does **not** add linearly with later whole-`u_pred`
> repair; those later repairs over-correct the strongest branch.


Theory extension:

> the full NS–LS–CFD derivation of this diagnosis now lives in `WIKI-T-073` and `SP-R`, and the redesign theorem/algorithm spec now lives in `WIKI-X-035` and `SP-S`.

Gate-fix update (2026-04-25):

> a predictor-stage plumbing bug was then found: first-class
> `predictor_assembly` modes were not enough by themselves to activate the
> face-consistent transform closures in `compute_ns_predictor_stage`. After
> fixing that gate and rerunning the previously suspect buoyancy branches, the
> conclusions changed materially. `buoyancy_mapped`, `buoyancy_sharp_local`,
> `buoyancy_xband_local`, and `buoyancy_yband_local` remain weaker than the
> best branch, but `buoyancy_fullband_local` is now **bit-identical** to
> `buoyancy_local`, both landing at
> `3.021e9 / 6.000e10 / 1.505e6`. The strongest current clue is therefore a
> **full two-axis dilated interface-band buoyancy predictor assembly**.

Neighbourhood split update:

> splitting that successful full-band mask into an **edge-only** branch and a
> **strict-plus-corner** branch shows that neither partial neighbourhood is
> sufficient. `buoyancy_edgeband_local` lands at
> `3.373e9 / 6.776e10 / 1.617e6`, while `buoyancy_corneraug_local` lands at
> `3.411e9 / 6.654e10 / 1.580e6`. Both remain weaker than
> `buoyancy_fullband_local = 3.021e9 / 6.000e10 / 1.505e6`. The active clue is
> therefore not “edge cells only” or “corner cells only”, but a **cooperative
> full 3×3 interface-neighbourhood buoyancy repair**.

Weighted-band update:

> two weighted variants were then tested to see whether the full-band signal is
> just a tunable mixture of edge and corner contributions.
> `buoyancy_edgehalf_local` (`edge=0.5`, `corner=1.0`) lands at
> `3.536e9 / 7.017e10 / 1.633e6`, while `buoyancy_cornerhalf_local`
> (`edge=1.0`, `corner=0.5`) lands at `3.362e9 / 6.717e10 / 1.603e6`.
> Neither comes close to the full-band optimum. So the winning signal is not a
> simple scalar weighting of edge and corner terms; it behaves like a **hard,
> coupled full-neighbourhood assembly**.

Component-selective full-band update:

> two further probes then split that hard full-band repair by velocity
> component. `buoyancy_fullband_local_x` lands at
> `3.449e9 / 6.985e10 / 1.636e6`, while `buoyancy_fullband_local_y` lands at
> `3.330e9 / 6.607e10 / 1.583e6`. Since the y-only branch is materially better
> than the x-only branch, the dominant signal is vertical and buoyancy-carrying.
> But neither equals the full-band optimum
> `3.021e9 / 6.000e10 / 1.505e6`, so the effective object is not a pure
> y-component fix. It is a **vertical-dominant yet still cross-component
> coupled full-neighbourhood predictor repair**.

Axis-mixed refinement:

> two hybrid branches then tested whether that remaining gap can be closed by a
> lighter x-side repair. `buoyancy_fullbandy_mappedx` (full-band y + mapped x)
> lands at `3.369e9 / 6.883e10 / 1.636e6`, while
> `buoyancy_fullbandy_sharpx` (full-band y + sharp-local x) lands at
> `3.411e9 / 6.758e10 / 1.606e6`. Both are worse than the plain y-only branch
> `3.330e9 / 6.607e10 / 1.583e6`. Therefore the missing signal is not restored
> by a shallow x-side patch; it belongs to a **fully coupled two-component
> full-band assembly**.

Assembly-vs-corrector refinement:

> one further probe then separated predictor assembly from the later
> `V(u_pred)` evaluation. The branch kept
> `predictor_assembly: buoyancy_fullband_local_y` but added
> `intermediate_state_repair: fullband_x`, so only the x-component was repaired
> at the intermediate-state stage. This yielded
> `3.181e9 / 6.129e10 / 1.503e6`, much closer to the full optimum
> `3.021e9 / 6.000e10 / 1.505e6` than the plain y-only branch
> `3.330e9 / 6.607e10 / 1.583e6`. So the dominant y-signal is assembly-side,
> but the missing x-signal is recovered mainly **at the `V(u_pred)` stage**.

This stage separation is now formalised as a redesign spec in `WIKI-X-036` and
`SP-T`: the admissible next-step architecture is **vertical repair in predictor
assembly + horizontal post-transform before `V(u_pred)`**.

The broader mathematical/physical foundation is now captured in `WIKI-T-074`
and `SP-U`, which connect this redesign to pressure-robustness,
well-balancedness, mass-momentum consistency, and variable-density projection
theory.

The discrete operator contract for the redesign is now pinned in `WIKI-T-075`
and `SP-V`, making the stage-split predictor directly auditable as a CFD
algorithm contract rather than just a diagnosis memo.
>
> Two follow-up runs then checked whether the x-side post repair must itself be
> a hard full-band transform. With the same y-only predictor assembly,
>
> - `postmappedx` gives `3.250e9 / 6.564e10 / 1.591e6`;
> - `postsharpx` gives `3.209e9 / 6.455e10 / 1.572e6`;
> - `postfullbandx` remains best at `3.181e9 / 6.129e10 / 1.503e6`.
>
> Therefore the x-side residual is indeed a **`V(u_pred)`-stage** effect, but
> it is not all-or-nothing tied to a hard full-band x repair. A local x-side
> post transform already recovers much of the missing signal, especially the
> sharp-local variant, while the full-band version still gives the strongest
> improvement.
>
> These two stage-split branches have now been promoted to first-class solver
> modes:
>
> - `buoyancy_stagesplit_fullbandx`
> - `buoyancy_stagesplit_sharpx`
>
> and the resulting runs are bit-identical to the earlier composed-flag probes.
> So the stage-split diagnosis is stable under solver-side refactoring.
>
> We then isolated whether the x-side post-stage signal requires mutating the
> intermediate state or only the state fed to the viscous operator. Two
> operator-only branches,
>
> - `buoyancy_stagesplit_operatorfullbandx`
> - `buoyancy_stagesplit_operatorsharpx`
>
> apply the x-side repair only on a copy used for evaluating `V(u_pred)`. They
> produce exactly the same diagnostics as the earlier stage-split modes:
>
> - `operatorfullbandx`: `3.181e9 / 6.129e10 / 1.503e6`
> - `operatorsharpx`: `3.209e9 / 6.455e10 / 1.572e6`
>
> Both are bit-identical to `buoyancy_stagesplit_fullbandx` and
> `buoyancy_stagesplit_sharpx`. So the x-side residual is an
> **operator-evaluation-stage phenomenon**, not a canonical-state mutation
> requirement.
>
> The same redesign is now also exposed with **gravity-direction** naming:
>
> - `buoyancy_gravity_aligned_local`
> - `buoyancy_stagesplit_gravity_postfullband`
> - `buoyancy_stagesplit_gravity_postsharp`
>
> For the current benchmark they are bit-identical to the older `y/x`-named
> branches, confirming that the invariant is really gravity-aligned vs
> transverse coupling.

We then implemented a more theory-driven **pressure-compatible vs residual**
split of buoyancy at the predictor-assembly level:

- `buoyancy_residual_fullband_local`
- `buoyancy_residual_stagesplit_transversefullband`

These remove the discrete gradient-compatible part of buoyancy from the
predictor velocity update and retain only the interface-local residual.
However, neither branch beats the existing best closures:

- `residual_fullband`: `4.145e9 / 8.427e10 / 1.801e6`
- `residual_stage_split`: `3.785e9 / 7.727e10 / 1.733e6`

So the theoretical split is physically meaningful, but this **first discrete
proxy is too aggressive** as a direct replacement for the current predictor.
The current evidence suggests that the pressure-compatible part cannot simply
be removed from the predictor.

After enforcing PPE/projection metric identity on the FCCD face-flux path, a
more faithful face-native residual split was tested:

- `buoyancy_faceresidual_stagesplit_transversefullband`

2026-04-25 update: the production-facing name for this closure is now
`balanced_buoyancy`; the long name remains only as a legacy alias.  The later
clean integration in [WIKI-L-034](../code/WIKI-L-034.md) shows that the split
passes the full `t=0.5` rising-bubble run once canonical face-state carry and
FMM redistancing are enforced together. The older paragraph below is retained
as a historical pre-closure negative trial.

The face-space unit check passes on a nonuniform wall grid: constant density
excess makes `face(f_b/rho) + (1/rho)_f G_f((rho-rho_ref)Phi_g)` vanish to
roundoff.  However, the ch13 debug run worsens to step-4 blowup:

- `face_residual_stage_split`: `5.072e7 / 4.414e11 / 1.595e8`

This is a stronger negative result than the nodal residual split.  The likely
interpretation is not that the decomposition is wrong, but that the pressure
unknown now has to carry the hydrostatic jump `(rho_l-rho_g)Phi_g` together
with the capillary jump.  The current PPE jump decomposition only injects the
surface-tension term `sigma*kappa*(1-psi)`, so the residual predictor and the
PPE pressure family are still not closed as a single well-balanced system.
be removed from the predictor branch without a tighter co-design of the later
pressure closure.
