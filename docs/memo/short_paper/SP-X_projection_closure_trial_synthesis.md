# SP-X — Trial Synthesis and Theory of the ch13 Phase-Separated FCCD Projection Closure

**Date**: 2026-04-25  
**Status**: ACTIVE / clean-merge synthesis  
**Related**:
[SP-W](SP-W_phase_separated_projection_closure.md),
[WIKI-T-076](../../wiki/theory/WIKI-T-076.md),
[WIKI-E-032](../../wiki/experiment/WIKI-E-032.md),
[WIKI-L-033](../../wiki/code/WIKI-L-033.md),
[WIKI-L-032](../../wiki/code/WIKI-L-032.md),
[WIKI-E-031](../../wiki/experiment/WIKI-E-031.md)

---

## Abstract

The long ch13 rising-bubble investigation initially looked like a buoyancy,
time-integration, level-set, or predictor-assembly instability. Many plausible
repairs changed the symptom but did not remove the blowup. The successful fix
was narrower and more structural: the phase-separated FCCD pressure Poisson
equation, the pressure/velocity projection corrector, and the diagnostic
face-space divergence must be the same discrete Hodge projection. In the broken
state, the PPE solved with a phase-separated face coefficient that cut
cross-phase faces, while the corrector applied a harmonic mixture-density
coefficient across those same faces. This destroyed the algebraic projection
identity, leaving an interface-supported divergence residual. The clean merge
therefore retained only the operator-closure patch: same `D_f`, same `G_f`,
same wall control-volume metric, and same `A_f=(1/rho)_f` policy in PPE and
corrector. That minimal closure passes the full test suite and the clean-main
`faceproj_debug` ch13 probe to `T=0.05`.

The key lesson is methodological as much as numerical: in variable-density
two-phase projection methods, "physically reasonable" local fixes are not
enough. A proposed fix must close the exact discrete equation being solved.

---

## 1. Problem setting

The target problem is a static non-uniform `alpha=2` water-air rising bubble on
a wall-bounded grid:

- density ratio: `rho_l/rho_g ≈ 833`,
- pressure equation: FCCD matrix-free PPE,
- interface handling: `psi`-based CLS / ridge-eikonal reinitialisation,
- capillarity: pressure-jump formulation,
- projection: FCCD face-flux projection.

The observed failure was an early blowup in the pressure-projection chain. The
early signal was not primarily a mass-conservation failure; the explosive
quantities were `ppe_rhs`, balanced-force residual, and `div_u`.

---

## 2. Continuous reference equations

In one-fluid notation,

```text
rho(psi) (du/dt + u·grad u) =
    -grad p + div(2 mu(psi) D(u)) + sigma kappa delta_s n + rho g,
div u = 0.
```

A fractional-step variable-density projection advances an intermediate velocity
`u*` and then solves

```text
div((1/rho) grad p) = div(u*)/dt + div(f/rho),
u^{n+1} = u* - dt (1/rho) grad p + dt f/rho.
```

The continuous cancellation is exact only when the elliptic operator and
velocity correction use the same coefficient and gradient/divergence pairing.
The discrete method inherits the same condition, with an even stricter demand:
the exact same face space must be used.

---

## 3. Discrete projection theorem

Let

```text
G_f : nodal pressure -> normal-face pressure gradient,
D_f : normal-face flux -> nodal divergence,
A_f : normal-face inverse-density coefficient.
```

The pressure operator is

```text
L_h p = D_f A_f G_f p.
```

If the corrector is

```text
u_f^{n+1} = u_f^* - dt A_f G_f p + dt f_f,
```

and `p` solves

```text
D_f A_f G_f p = D_f u_f^*/dt + D_f f_f,
```

then `D_f u_f^{n+1}=0` up to solver tolerance and boundary/gauge choices.

If, however, the PPE uses `A_f^PPE` while the corrector uses `A_f^corr`, then

```text
D_f u_f^{n+1}
  = -dt D_f[(A_f^corr - A_f^PPE) G_f p].
```

This is not a small implementation detail. In phase-separated PPE,
`A_f^PPE=0` on cross-phase faces. If the corrector instead uses harmonic
mixture density, the residual lives exactly on the density interface. With a
water-air density jump and large pressure gradients, this residual can dominate
the timestep budget.

---

## 4. Why phase-separated PPE made the mismatch visible

The phase-separated FCCD PPE intentionally solves disconnected liquid/gas
Neumann blocks:

```text
A_f^sep =
  2/(rho_i + rho_j),  if face i-j is same phase,
  0,                 if face i-j crosses the interface.
```

This is consistent with a split pressure solve and one gauge per phase. But it
also creates a hard contract: every downstream use of the pressure correction
must respect the same cut faces. Using a mixture coefficient in the corrector
amounts to re-coupling the phases after solving a decoupled pressure equation.

This explains why "jump不足" was not the root cause. A missing pressure-jump
term can bias the pressure field, but it cannot restore a broken Hodge
projection if the correction is applied in a different coefficient space.

---

## 5. Hypothesis ladder and verdicts

The investigation produced many plausible hypotheses. The important ones are
summarised below.

| Hypothesis | Verdict | Reason |
|---|---|---|
| Level-set `psi` collapse is primary | Rejected as root cause | The explosive chain was already visible in PPE/BF/divergence diagnostics; `psi` issues can amplify but did not explain operator mismatch. |
| TVD-RK3 is the main culprit | Rejected for this failure | A time integrator can expose instability, but the algebraic residual remains for any explicit stage if PPE/corrector coefficients differ. |
| UCCD/FCCD advection stencil is the root cause | Weakened | The blowup locus followed projection residuals, not a pure convection CFL or upwind/central blending signature. |
| Gravity/buoyancy triggers the instability | Supported as trigger | `g=0` probes were stable over the short horizon; buoyancy excites the inconsistent projection mode. |
| Surface tension alone drives blowup | Rejected | `sigma=0` did not remove the relevant failure class in earlier probes. |
| Reinitialization causes the blowup | Rejected as primary | Disabling reinitialisation did not close the projection residual and could worsen interface quality. |
| Face-preserve / face-canonical carry alone is enough | Rejected | Preserving face velocity without coefficient closure changes the state carrier but not the operator defect. |
| Projection-consistent buoyancy injection alone is enough | Rejected | Moving buoyancy into a different path without matching `A_f` aggravated the residual. |
| q-jump/reduced pressure is required | Useful but not primary | q-jump PoCs were meaningful after closure, but no-q-jump also stabilised. |
| PPE and corrector use different `A_f` and wall rows | Accepted | Closing `D_f A_f G_f` across PPE and corrector removed the early blowup. |

---

## 6. What actually worked

The clean merge kept only the operator contract:

1. `FCCDDivergenceOperator.divergence_from_faces()` uses the same wall
   control-volume divergence rows as `PPESolverFCCDMatrixFree`.
2. `FCCDDivergenceOperator.pressure_fluxes()` accepts
   `coefficient_scheme="phase_separated"`.
3. Cross-phase pressure fluxes are zeroed when the PPE is phase-separated.
4. `correct_ns_velocity_stage()` forwards the PPE coefficient policy into the
   FCCD projection.
5. Regression tests verify operator equality on a non-uniform wall grid:
   `D_f A_f G_f` from projection equals the PPE matrix-free apply, excluding
   gauge pins.

Clean-main validation:

```text
commit 8682cf5: Align FCCD projection with phase-separated PPE
merge  977c834: Merge ch13 FCCD projection closure
pytest: 378 passed, 18 skipped, 2 xfailed
run: ch13_rising_bubble_water_air_alpha2_n128x256_faceproj_debug
     reached T=0.05
     final KE=1.283e-04
     final ppe_rhs=8.564e+01
     final bf_res=4.407e+03
     final div_u=4.642e-01
```

The research worktree also showed the richer face-residual branch reaching
`T=0.05` and a long visualisation probe reaching `T=0.5`. Those runs remain
important evidence, but the clean merge deliberately avoids importing the
experimental predictor-assembly branch.

---

## 7. Why the clean patch is mathematically sufficient

The successful patch is sufficient for the observed failure because it restores
the exact algebraic cancellation:

```text
P_h = I - G_h L_h^{-1} D_h
```

is a projection only if the `G_h`, `D_h`, and coefficient embedded in `L_h`
match the correction actually applied. Before the patch, the code solved with
one operator and corrected with another, so the map was not a projection.

The non-uniform grid matters because wall and interior rows carry physical
control-volume widths. Matching the symbolic operator name `FCCD` is not
enough; the discrete metric rows must also be identical. The clean patch
therefore changed both:

- coefficient closure: same phase-separated `A_f`,
- metric closure: same wall-control-volume `D_f`.

This explains why the fix is not a tuning trick. It enforces a discrete
identity required by the variable-density Navier-Stokes projection itself.

---

## 8. What remains open

This closure removes the explosive early projection defect. It does not prove
that the whole high-density-ratio rising-bubble benchmark is publication-ready.
Remaining items:

1. bound the long-time `div_u` budget under the final clean-main stack,
2. decide whether q-jump/reduced-pressure terms are needed for accuracy rather
   than stability,
3. determine whether the richer buoyancy face-residual predictor should be
   productionised after separate review,
4. compare against reference rising-bubble metrics after the projection closure
   is no longer the dominant failure.

---

## 9. Practical rule for future debugging

When a two-phase projection run blows up, do not first tune CFL, smoothing,
RK stages, or filters. First test the discrete identity:

```text
projection-side D_f A_f G_f  ==  PPE-side D_f A_f G_f
```

on the same grid, same boundary rows, same density field, same phase cuts, and
same gauge treatment. If this identity fails, all later physical reasoning is
contaminated by a non-projection.
