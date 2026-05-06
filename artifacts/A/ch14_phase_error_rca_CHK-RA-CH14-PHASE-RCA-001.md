# CHK-RA-CH14-PHASE-RCA-001: remaining phase/static-error RCA

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: identify the cause of the remaining `component_hodge_augmented`
problem after the zero-drive fix: static corrected-Hodge residual is small but
nonmonotone, no-reinit oscillation is too slow/damped, and reinit-on
oscillation is too fast/energetic.

## Problem Statement

The old production bug was algebraic: `range_projected` replaced the capillary
cochain by `Pi_R c`, deleting all Hodge drive.  That is fixed.  The current
problem is subtler:

```text
static droplet:    small but nonzero/nonmonotone corrected Hodge residual
no-reinit ellipse: Rayleigh-Lamb phase too slow and amplitude too damped
reinit-on ellipse: phase too fast and energy/Hodge norms too large
```

This RCA treats the interface as an arbitrary closed component, not as a
circle/ellipse classifier.  The physical object is the surface-energy
virtual-work cochain in the face-space Hodge quotient.

## Theoretical Test Frame

For a closed component, admissible capillary work should satisfy

```text
s = -M_f^{-1} T^T d(sigma S_h)^T
B =  M_f^{-1} T^T [dV_m]^T
h = s - X (X^T M_f X)^+ X^T M_f s,  X=[A G B].
```

The static component reaction is removed by `B`; nonconstant resolved shape
modes must remain in `h`.  Rayleigh-Lamb then tests the Hessian of `S_h` on an
`n=2` mode.  Reinit must be measured separately:

```text
q^n -> q_T      physical transport
q_T -> q^{n+1} reinit/profile projection
```

## Existing Data Tests

| Case | Observed fact | Inference |
|---|---|---|
| no-reinit N32/T20 | first zero `13.393564` vs Rayleigh `9.381529` | late phase is too slow |
| no-reinit N32/T20 | early acceleration gives `omega=0.140166`, stiffness ratio `0.700797` | force Hessian is already too weak before long-time damping |
| no-reinit N32/T20 | damped fit gives `gamma=0.054`, `omega=0.147` | damping is far above physical water-air viscosity |
| reinit-on N32/T10 | first zero `7.578596`, zero-derived stiffness ratio `1.532392` | reinit/profile projection injects effective work/stiffness |
| reinit endpoint smoke | `max|q_T-q^n|=6.436583e-07`, `max|q^{n+1}-q_T|=1.778247e-01` | apparent shape change can be dominated by reinit |
| static N16/32/64 | Hodge residual `8.428385e-04`, `2.814614e-04`, `5.893873e-04` | current cochain is not theorem-grade static |

## Additional Probes

All probes were remote-first via
`SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle ...`.
Temporary YAMLs were deleted after use.

| Probe | Purpose | Key result |
|---|---|---|
| `_tmp_ch14_osc_n32_t4_component_noreinit_staticgrid` | test whether every-step grid rebuild/remap causes slow phase | same early acceleration as dynamic-grid no-reinit: `omega=0.139755`, stiffness ratio `0.696697` |
| `_tmp_ch14_osc_n32_t1_none_noreinit` | test whether component projection over-removes the dynamic mode | same early acceleration as component mode: `omega=0.140172`, stiffness ratio `0.700858` |
| `_tmp_ch14_static_n32_t1_none_noreinit` | test whether raw `none` keeps a spurious static reaction | static KE `5.026189e-06` vs component static `5.284015e-09` |

Figures:

```text
experiment/ch14/results/ch14_phase_rca_projection_grid_probe.png
experiment/ch14/results/ch14_phase_rca_projection_grid_probe.pdf
experiment/ch14/results/ch14_phase_rca_static_none_vs_component.png
experiment/ch14/results/ch14_phase_rca_static_none_vs_component.pdf
```

## Hypothesis Matrix

| ID | Hypothesis | Test | Verdict |
|---|---|---|---|
| H01 | Rayleigh-Lamb reference is simply wrong | reinit-on and no-reinit shift in opposite directions | falsified as sole cause |
| H02 | D0 overlay mismatch causes phase error | measured `D0=0.076175` used in acceleration/zero tests | falsified for phase |
| H03 | signed deformation diagnostic creates false phase | zero crossing and early curvature use same sign; diagnostic is post-step | low likelihood |
| H04 | physical viscosity damps the motion | observed `gamma~0.054`; water `nu_l=1e-6`, `R~0.25` implies O(`1e-4`) damping | falsified |
| H05 | capillary time step is too large | `dt*omega_ref ~ 1.6e-3`; early phase error is O(30%) | falsified |
| H06 | PPE/DC residual dominates phase | PPE relative residual is O(`1e-9`) in prior validations | falsified |
| H07 | component projection over-removes dynamic mode | `none` and component no-reinit T1 have same `omega~0.14017` | falsified |
| H08 | component projection is unnecessary | static `none` KE is `5.026e-06`, component KE `5.284e-09` | falsified |
| H09 | dynamic grid rebuild/remap causes early under-stiffness | static-grid no-reinit T4 matches dynamic-grid no-reinit through T4 | falsified for early stiffness |
| H10 | reinit is harmless | endpoint and T10 phase show large `q_T->q^{n+1}` and early zero | falsified |
| H11 | reinit explains no-reinit slow phase | no-reinit still has stiffness ratio `0.70` and late zero `13.39` | falsified |
| H12 | raw face-implicit cochain has wrong surface-energy Hessian | no-reinit early stiffness is `0.70` even with `none`, static grid, no reinit | supported |
| H13 | raw cochain is not static-exact | static residual nonmonotone and `none` static current large | supported |
| H14 | affine component reaction is missing | component projection removes static current by ~3 orders | falsified as current problem |
| H15 | pressure range projection should be restored | prior `range_projected` produces zero drive | falsified |
| H16 | curvature cap/smoothing/damping would fix it | would alter symptoms without proving `T^T dS_h` | rejected by theory |
| H17 | high-mode contamination is primary | early `n=2` acceleration already under-stiff before large deformation | secondary at most |
| H18 | interface transport numerical diffusion causes late damping | no-reinit T20 damped strongly after early under-stiffness | plausible secondary |
| H19 | density/inertia is globally mis-scaled | static current and dynamic stiffness errors are mode-dependent, not one scalar | not primary |
| H20 | missing fixed-stratum Riesz pullback is root | explains static residual, under-stiff dynamic Hessian, and need for endpoint split | primary cause |

## Cause Identification

There are two causes at different levels.

Primary force-side cause:

```text
The current scalar face_implicit capillary cochain, even after the
one-component Hodge augmentation, is not the fixed-stratum transport-adjoint
Riesz representative of surface-energy variation.
```

Evidence:

```text
1. Early no-reinit acceleration gives only ~70% of Rayleigh-Lamb stiffness.
2. This persists with static grid, so grid remap is not the early cause.
3. This persists with capillary_range_projection:none, so component projection
   is not over-removing the dynamic mode.
4. Static residual is nonmonotone with N, so the cochain is not static-exact.
```

Secondary measurement/long-time cause:

```text
Ridge-Eikonal/profile reinit changes the interface state by a nonphysical
projection leg that can dominate physical transport and shifts phase/energy.
```

Evidence:

```text
1. Reinit-on zero crossing is too early while no-reinit is too late.
2. Endpoint smoke shows |q^{n+1}-q_T| >> |q_T-q^n|.
3. Reinit-on Hodge norm and KE are much larger than no-reinit.
```

Late no-reinit damping remains a secondary open mechanism, likely from
transport/numerical dissipation and non-variational capillary work over long
time.  It is not physical viscosity and not the initial phase cause.

## What This Rules Out

Do not fix the problem by:

```text
damping,
CFL reduction,
curvature caps,
curvature smoothing,
FD/WENO/PPE fallback,
benchmark-name branching,
range projection of the production force,
scalar rescaling of the Rayleigh frequency,
turning reinit into capillary work.
```

Those would tune symptoms while leaving the failed virtual-work identity
unproved.

## Next Theorem-Grade Work

The next implementation target is still:

```text
1. construct fixed-stratum trace geometry S_h and component volumes V_m,h,
2. compute/verify dS_h and dV_m,h by centered finite differences on the same stratum,
3. implement the transport VJP T^T,
4. form s=-M_f^{-1}T^Td(sigma S_h)^T and B=M_f^{-1}T^T[dV_m]^T,
5. project with X=[A G B] in the same M_f face metric,
6. use q^n->q_T only for capillary work; report q_T->q^{n+1} separately.
```

## Validation

Remote tests after removing temp YAMLs:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_ns_simulation_runner_outputs.py \
  twophase/tests/test_simulation_checkpoint.py -q'
```

The wrapper expanded to the full CPU suite:

```text
592 passed, 32 skipped in 42.90s
```

[SOLID-X] RCA plus diagnostic-output robustness only; no production capillary
force, PPE/corrector equation, CFL, damping, smoothing, curvature cap, fallback,
benchmark-name branch, blanket `c -> Pi_R c`, or QP-as-physics path introduced.
