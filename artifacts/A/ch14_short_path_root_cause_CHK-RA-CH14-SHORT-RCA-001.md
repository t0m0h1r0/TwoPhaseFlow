# CHK-RA-CH14-SHORT-RCA-001 — ch14 droplet problem short-path RCA

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`

## Question

問題解決の近道を探るため、ch14 の静止/振動液滴で何が支配的な原因かを、物理・数学の保存則と離散変分条件から仮説化し、できるだけ多く検証する。

## Short verdict

The fastest path is not to tune the flow solver. The present evidence separates the problem into two theorem-level defects.

1. **Sharp interface volume is not the conserved quantity currently enforced.**
   Runtime diagnostics and reinitialization preserve the diffuse mass
   `M_psi = sum_i psi_i dV_i`, with physical nonuniform cell volumes. They do not preserve the sharp liquid volume
   `V_Gamma = |{x: psi(x) >= 1/2}|`.
   Ridge-Eikonal/profile reinitialization is the primary cause of the apparent liquid-volume loss in oscillating T10 visualizations.

2. **The capillary cochain is still not a discrete constrained critical point for a static droplet.**
   Even with reinitialization disabled, the static circle has a nonzero Hodge residual in the same face complex. Therefore a static droplet is still being given a small physical-time capillary drive. This is separate from the sharp-volume loss.

The near-singular pressure/Hodge normal solve is a third issue in implementation hygiene. It should become a declared singular/gauge solve or a reduced pressure-space solve. It does not explain the sharp area collapse, but hidden direct-to-LSMR recovery is not the desired fail-close contract.

## Theory used for discrimination

Let `q = psi` be the CLS indicator and `dV` the physical cell volume. The diagnostic volume currently measured is

```text
M_psi(q) = sum_i q_i dV_i.
```

The visually relevant liquid area is instead the sharp sublevel/level-set volume

```text
V_Gamma(q) = measure({x : q(x) >= 1/2}),
```

estimated by P1 crossing reconstruction in `liquid_area_2d`.

The reinitialization map is not a physical-time interface transport map:

```text
q^n --T_h(u_f)--> q_T --Pi_h--> q^{n+1}.
```

Capillary work belongs to `T_h`; any `Delta S(Pi_h)` or `Delta V_Gamma(Pi_h)` is representation/projection work unless the projection is itself formulated as a conservative physical profile-control flux.

For a static droplet, the discrete capillary cochain must satisfy the constrained equilibrium gate

```text
P_h(c_sigma + lambda c_V) = 0
```

in the same face metric and divergence complex used by production. A nonzero static Hodge component means the discretization is not at a constrained critical point, independent of whether the continuum shape is called a circle, ellipse, or something else.

## Key evidence

### Code-level conservation target

`DiagnosticCollector.collect` stores volume as `sum(psi * dV)`, not sharp interface area:

- `src/twophase/tools/diagnostics/collector.py:207-209`

For dynamic grid rebuilds, `dV` is refreshed from the current physical grid before collecting diagnostics:

- `src/twophase/simulation/runner.py:157-164`

Therefore the "nonuniform computational-coordinate volume" hypothesis is falsified for the existing volume diagnostic. It is physical `dV`.

Ridge-Eikonal mass correction also targets diffuse mass through a global level-set/profile correction:

- `src/twophase/levelset/ridge_eikonal_reinitializer.py:146-166`

That proves the important point: perfect reported volume conservation can coexist with sharp-interface volume loss.

### Corrected T10 visualization audit

The custom `overview_t10.png` previously generated from `data.npz` was not safe for dynamic-grid visual judgment, because `data.npz` stores only `snaps[0]["grid_coords"]`:

- `experiment/runner/handlers/ns_simulation.py:74-76`

After recomputing the montage from `snapshots.pkl`, using per-snapshot physical coordinates:

- static T10: `integral psi dV` relative drift `~5e-16`, sharp P1 area `0.1953767 -> 0.19503018`, relative `-1.77e-3`
- oscillating T10: `integral psi dV` relative drift `~3e-15`, sharp P1 area `0.19340088 -> 0.15668583`, relative `-1.898e-1`

The user's visual suspicion is therefore physically meaningful: the sharp liquid area changes substantially in the oscillating case, even though the diffuse mass diagnostic is machine-constant.

### 2x2 N32/T1 cause isolation

Remote short probes crossed dynamic grid schedule and reinit cadence:

| Case | grid schedule | reinit every step | final KE | sharp area rel. drift | surface rel. drift |
|---|---:|---:|---:|---:|---:|
| oscillating | 0 | 0 | `2.3006e-05` | `-3.97e-05` | `-2.29e-04` |
| oscillating | 0 | 1 | `9.2060e-05` | `-2.3887e-01` | `-1.2543e-01` |
| oscillating | 1 | 0 | `2.3486e-05` | `-4.74e-05` | `-2.34e-04` |
| oscillating | 1 | 1 | `9.7046e-05` | `-1.9244e-01` | `-9.9688e-02` |

This is the strongest localization so far.

- Grid rebuild/remap is not the primary sharp-volume-loss mechanism.
- Physical transport plus trace-Riesz force does not by itself destroy sharp area over T1.
- Reinitialization/profile projection is the dominant sharp-area loss mechanism.

Stage fields in the reinit-on T1 run show the same result: `psi_before_transport`, `psi_after_transport_before_reinit`, and `psi_after_reinit` preserve `sum psi dV`, while sharp area collapses to the post-reinit geometry.

### Static Hodge gate

Recomputed weighted Hodge gates from saved T10 snapshots:

| Case | time | `||surface||` | `||corrected||` | Hodge residual | ratio |
|---|---:|---:|---:|---:|---:|
| static | `0.00988` | `6.9058e-02` | `6.8668e-02` | `2.3918e-03` | `3.46e-02` |
| static | `1.00888` | `6.9158e-02` | `6.8766e-02` | `1.8195e-03` | `2.63e-02` |
| static | `10.0` | `6.9506e-02` | `6.9042e-02` | `2.4831e-03` | `3.57e-02` |
| oscillating | `0.00944` | `7.1460e-02` | `7.1100e-02` | `7.4231e-03` | `1.04e-01` |
| oscillating | `1.00515` | `7.4665e-02` | `7.4564e-02` | `1.6674e-02` | `2.23e-01` |
| oscillating | `10.0` | `7.3169e-02` | `7.2979e-02` | `1.0780e-02` | `1.47e-01` |

The dynamic case has a larger residual, as expected. But the static case is not zero. That rules out a purely reinit-only explanation for static KE growth.

## Hypothesis matrix

| ID | Hypothesis | Verdict | Reason |
|---|---|---|---|
| H01 | Reported volume uses computational coordinate volume on a nonuniform grid. | Falsified | Diagnostics use physical `dV`, refreshed after rebuild. |
| H02 | The visual volume change is only a plotting-coordinate artifact. | Partly falsified | Earlier custom `data.npz` montage was flawed, but corrected `snapshots.pkl` physical-coordinate area still shrinks by `~19%` at T10. |
| H03 | Diffuse mass conservation is being mistaken for sharp-interface volume conservation. | Confirmed | `sum psi dV` is machine-constant while P1 sharp area changes strongly. |
| H04 | Ridge-Eikonal reinit/profile projection is the primary sharp-area loss. | Confirmed | T1 cross test: reinit off gives `~4e-5` area drift; reinit on gives `~19-24%` drift. |
| H05 | Dynamic grid rebuild/remap is the primary sharp-area loss. | Falsified as primary | Reinit-off with schedule on/off gives nearly identical tiny sharp-area drift. |
| H06 | FCCD transport/Riesz force alone destroys sharp area. | Falsified as primary over T1 | Reinit-off T1 runs retain sharp area to `O(1e-5)`. |
| H07 | Static droplet is a discrete constrained equilibrium under the current cochain. | Falsified | Static Hodge residual remains `2.6-3.6%` of the surface cochain. |
| H08 | Oscillating motion is purely reinit artifact. | Falsified/nuanced | Reinit-off still gives nonzero KE and capillary drive; reinit contaminates amplitude and geometry strongly. |
| H09 | The current volume reaction projection enforces sharp area. | Falsified | The reaction lives in the capillary/PPE cochain; the post-transport reinit projection enforces diffuse mass instead. |
| H10 | The old `range_projected` zero-drive bug is still the current T10 cause. | Falsified for current branch | Current trace-Riesz path moves; zero-drive theorem remains historical negative knowledge. |
| H11 | The capillary cochain is the exact adjoint of actual FCCD transport endpoint. | Not proved; likely false enough to matter | Prior VJP probes showed large mismatch between P1 trace cochain prediction and actual `FCCDLevelSetAdvection.advance_with_face_velocity` finite-difference surface derivative. |
| H12 | Pressure normal near-singularity is physical evidence against the model. | Falsified as physics | It is a gauge/redundant periodic pressure-space issue. It needs a declared solve contract, not physical tuning. |
| H13 | Direct-to-LSMR recovery is acceptable because the equation is singular. | Rejected by policy | Mathematically it may compute a residual-certified solution, but UX/contract should be explicit fail-close or reduced full-rank space. |
| H14 | Static KE growth is caused only by solver residual/fallback. | Falsified | Recomputed Hodge residual remains nonzero as a force/cochain property. |
| H15 | Viscosity, CFL, damping, or curvature smoothing can solve the issue. | Rejected | These address symptoms or stability, not the violated conservation/variational gates. |
| H16 | Finite-resolution threshold-area estimator alone explains the 19% area loss. | Falsified | Multiple sharp estimates and visual snapshots agree in sign and magnitude; reinit-on/off cross test isolates mechanism. |
| H17 | Name-based circle/ellipse classification is needed. | Rejected | Static/dynamic classification must be by `P_h(c_sigma + lambda c_V)`, not by assumed shape family. |
| H18 | The short path is to disable reinit permanently. | Rejected as final remedy | It is a useful diagnostic, but the theory needs a conservative profile-control/reinit map or a reinit-free CLS carrier with explicit energy/volume ledger. |

## Problem localization

The present root cause is not a single line. The shortest useful decomposition is:

```text
sharp-volume symptom:
    Pi_h reinitialization/profile projection conserves M_psi, not V_Gamma

static-spurious-motion symptom:
    current capillary cochain is not a constrained stationary point
    in the production face metric/divergence complex

solver-contract symptom:
    pressure/Hodge normal solve has gauge singularity and duplicated periodic rows
    but the implementation path should expose that theorem explicitly
```

## Recommended short path

1. Add first-class diagnostics/gates for `V_Gamma`, `S_Gamma`, and `M_psi` at every split stage:
   `before_transport`, `after_transport_before_reinit`, `after_reinit`, `after_grid_remap`.
   This immediately prevents diffuse-mass conservation from masking sharp-volume loss.

2. Treat Ridge-Eikonal/profile reinit as a projection operator with its own ledger:
   `Delta V_Gamma(Pi_h)`, `Delta S_Gamma(Pi_h)`, and `Delta M_psi(Pi_h)`.
   It must not be charged to capillary work.

3. For validation runs of the capillary cochain, run reinit-off or reinit-gated experiments until the projection map can satisfy sharp-volume/profile identity gates. This is not a production fix; it is the cleanest way to verify the force theorem without a contaminating projection.

4. Replace the hidden GPU direct-to-LSMR recovery contract with either:
   - a reduced full-rank periodic pressure space, or
   - an explicitly named singular least-squares/gauge solver with residual certificate and fail-close threshold.

5. Continue the capillary-force proof at the actual transport endpoint:
   construct or verify `T_h^* dS_h` against `FCCDLevelSetAdvection.advance_with_face_velocity`, then require the same Hodge static/dynamic gates. Do not use circle/ellipse-specific logic.

## Current answer to "what is the cause?"

For the T10 visual volume loss, the cause is **not** nonuniform-coordinate volume accounting and not the physical capillary transport. It is the mismatch between the conserved diffuse CLS mass and the sharp-interface volume, amplified by Ridge-Eikonal/profile reinitialization.

For the residual static motion, the cause is **not** reinitialization alone. The current capillary cochain still fails the discrete constrained-equilibrium Hodge gate, so the static case is not a true discrete critical point.

These two defects interact in oscillating runs: the capillary force can move the interface, but the reinit projection then changes the represented geometry in a way that looks like liquid-volume loss and contaminates the Rayleigh-Lamb comparison.
