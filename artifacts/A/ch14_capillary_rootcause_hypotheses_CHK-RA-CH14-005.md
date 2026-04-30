# CHK-RA-CH14-005 — capillary-wave failure root-cause hypotheses

## Executive conclusion

The failed `ch14_capillary` run is not primarily a CFL, run-time, viscosity,
or wall-depth problem.  The root cause is mathematical:

> The pressure-jump path represents the capillary jump as a regular nodal
> pressure field `J = sigma kappa (1 - psi)`, subtracts `L(J)` from the PPE
> right-hand side, solves `L(p_base)=rhs-L(J)`, and then returns
> `p_total=p_base+J`.  For an initially stationary capillary wave,
> `rhs≈0`, so the elliptic solve finds `p_base≈-J`; the velocity correction
> sees almost no capillary pressure gradient.

The one-step probe confirms this algebraic cancellation:

| Quantity | Value |
|---|---:|
| represented jump range `ptp(J)` | `2.371575e-01` |
| returned pressure range `ptp(p_total)` | `2.139760e-04` |
| cancellation ratio | `9.022527e-04` |
| one-step `||u||_inf` | `3.866137e-09` |

Thus the capillary restoring force is present as a constructed jump proxy,
but it is almost exactly nulled before it can accelerate the interface.

## Physical and mathematical reference

For a small-amplitude inviscid two-fluid capillary wave with `g=0`,

```text
omega^2 = sigma k^3 / (rho_l + rho_g),
k = 4 pi,
A0 = 0.01.
```

The run parameters give

```text
omega = 0.377764048,
T_omega = 16.632565583,
A0 omega = 3.777640e-03,
sigma A0 k^2 = 1.136978e-01.
```

The computed run has `T=35`, i.e. about `2.10` inviscid periods and about
`9278` steps per period.  If the capillary mechanism were dynamically active,
the signed `m=2` mode should cross zero near `t≈4.16` and change sign near
`t≈8.32`.  It does neither.

## Observed evidence

Source: `/Users/tomohiro/Downloads/TwoPhaseFlow/experiment/ch14/results/ch14_capillary/data.npz`

| Evidence | Observation | Implication |
|---|---:|---|
| signed `m=2` mode | `1.000258e-02 -> 1.046510e-02`, zero crossings `0` | no capillary oscillation |
| max `||u||_inf` | `1.061779e-04` | only `2.811%` of `A0 omega` |
| initial pressure range | `2.139760e-04` | only `0.188%` of smooth jump amplitude |
| volume drift max | `1.217103e-05` | conservative but physically under-driven |
| kinetic energy max | `8.064809e-09` | velocity response nearly absent |
| `kappa_max` cap hits | `17575 / 19525` | later-time curvature pollution exists |
| high-mode/m=2 ratio | `1.492e-03 -> 4.774e-01` | grid-scale interface corrugation grows |
| phase-separated cross-face flux | exactly `0` by construction | interfacial flux path is masked |

## Hypothesis set and verdicts

Verdicts:

- `PRIMARY`: explains the failure and is directly verified.
- `CONTRIB`: contributes or amplifies, but does not alone explain the first-step failure.
- `REJECT`: inconsistent with the measured evidence.
- `OPEN`: plausible but not needed for the current root-cause identification.

| ID | Hypothesis | Theory basis | Verification | Verdict |
|---|---|---|---|---|
| H01 | Run time too short | Need at least a fraction of `T_omega` | `T/T_omega=2.10`; no zero crossing | REJECT |
| H02 | Time step too large | Capillary waves require small `dt` | `~9278` steps per period | REJECT |
| H03 | Capillary CFL instability | `dt < C sqrt(rho h^3/sigma)` | stable completion, tiny KE | REJECT |
| H04 | Viscous overdamping | damping scale `nu k^2` | water `nu k^2≈1.58e-4 s^-1`; negligible over `35 s` | REJECT |
| H05 | Density ratio lowers frequency to near zero | `omega^2=sigma k^3/(rho_l+rho_g)` | `omega=0.377764`, not small | REJECT |
| H06 | Gravity omission invalidates benchmark | capillary-only case sets `g=0` | dispersion relation used is `g=0` | REJECT |
| H07 | Wall depth suppresses wave | finite-depth factor `tanh(kh)` | `kh≈6.28`, `tanh(kh)≈0.999993` | REJECT |
| H08 | No-slip walls overdamp immediately | wall boundary layer could damp | one-step pressure already cancelled before wall damping matters | REJECT |
| H09 | Initial condition has wrong mode | expected `m=2` | extracted `a2(0)≈0.0100`; correct | REJECT |
| H10 | Amplitude too nonlinear | linear theory requires small `A0 k` | `A0 k≈0.126`; acceptable for first diagnostic | REJECT |
| H11 | Interface amplitude metric is wrong | unsigned max deviation can hide phase | signed mode confirms no oscillation | CONTRIB |
| H12 | Initial velocity zero prevents oscillation | oscillator may start at rest | physical capillary wave starts from displacement with zero velocity and accelerates | REJECT |
| H13 | Surface tension coefficient is zero | no capillary force if `sigma=0` | one-step `J` has `ptp=0.237` | REJECT |
| H14 | Curvature is identically zero | no jump if `kappa=0` | one-step `max|kappa|=1.951` | REJECT |
| H15 | Curvature sign is reversed | anti-restoring force grows amplitude | observed first-step force is nearly zero, not strong anti-restoring | REJECT as primary |
| H16 | Curvature cap `5.0` suppresses smooth mode | cap below physical curvature would under-drive | smooth `A0 k^2≈1.58 < 5`; first step not capped | REJECT as primary |
| H17 | Curvature cap later damages interface | cap active `90.0%` later | explains high-mode pollution after under-driving begins | CONTRIB |
| H18 | HFE curvature creates grid-scale noise | high derivatives amplify interface noise | high-mode/m=2 grows to `0.477` | CONTRIB |
| H19 | Ridge--Eikonal reinit damps the mode | reinit can alter interface geometry | first-step cancellation occurs before long reinit history | REJECT as primary |
| H20 | Local thickness too wide/narrow | thickness affects curvature and transport | cannot explain one-step `J -> p_total` cancellation | REJECT as primary |
| H21 | Nonuniform grid distorts dispersion | nonuniform spacing changes discrete `k` | may affect phase error, not zero first-step acceleration | CONTRIB/OPEN |
| H22 | Pressure-jump context not set | PPE would ignore jump | one-step constructed `J` is active in operator | REJECT |
| H23 | Returned pressure omits jump only in output | diagnostic artifact | velocity also remains `3.9e-09`; not just output | REJECT |
| H24 | Pressure-jump volume-field decomposition cancels itself | `L(p_base)=rhs-L(J)`, `p=p_base+J` | `ptp(p)/ptp(J)=9.0e-4` | PRIMARY |
| H25 | Jump is represented in same discrete pressure space, not as interface constraint | a regular field can be absorbed by base pressure | one-step `p_base≈-J` behavior | PRIMARY |
| H26 | Phase-separated coefficient disconnects interfacial faces | cross-interface coefficient is zero | cross-phase flux exactly `0` by construction | CONTRIB |
| H27 | PPE solves only divergence constraint, not stress-jump condition | pressure Poisson equation needs jump BC/IIM/GFM condition | current solve returns near-zero total pressure for nonzero jump proxy | PRIMARY |
| H28 | Phase-mean gauge removes jump | two phase gauges remove constants | cancellation is spatial and `~1e-3`, beyond mean-only gauge | CONTRIB/OPEN |
| H29 | Base GMRES tolerance too loose | under-solved pressure could be small | cancellation is too coherent and stable; not random residual | REJECT |
| H30 | Defect correction iteration count too low | incomplete correction may leave wrong pressure | first base solve already cancels represented `J`; more correction preserves same equation | REJECT as primary |
| H31 | Face-flux projection ignores singular jump gradient | velocity correction uses regular pressure fluxes | interfacial face flux masked by phase-separated coefficient | CONTRIB |
| H32 | Surface tension as `NullSurfaceTensionForce` is incompatible with dynamic capillary waves | predictor has no capillary forcing | acceptable only if PPE jump enforces stress jump; current PPE does not | PRIMARY/CONTRIB |
| H33 | Pressure-gradient sign error | wrong sign gives anti-restoring acceleration | measured acceleration is near zero | REJECT as primary |
| H34 | Predictor velocity is overwritten by wall BC | wall BC can zero boundary velocities | interior speed also near zero; pressure range already tiny | REJECT |
| H35 | Projection short-circuit zeroes the step | zero shortcut could skip correction | p_corrector is nonzero path; one-step algebra shows solve occurs | REJECT |
| H36 | Volume conservation success masks physical failure | incompressibility can pass without correct capillary stress | volume drift pass with no oscillation | CONTRIB diagnostic lesson |
| H37 | Pressure range too small relative to Laplace scale | pressure should be `O(sigma A k^2)` | initial `p` is `0.188%` of expected | PRIMARY evidence |
| H38 | High-density liquid inertia alone makes velocity tiny | water inertia reduces omega | expected `A0 omega=3.78e-3`, observed max `2.8%` | REJECT |
| H39 | Mode energy transfers to high modes instead of oscillating | nonlinear/numerical corrugation | high-mode ratio grows, but after force under-drive | CONTRIB |
| H40 | The benchmark theory is wrong for CLS variables | theory is for sharp interface | first-step stress-jump consistency should still produce nonzero acceleration | REJECT |

## Problem identification

The failure mechanism is:

1. The physical capillary wave requires a nonzero pressure jump/stress condition
   with variation along the interface.
2. The implementation creates a nodal jump proxy
   `J = sigma kappa (1 - psi)`.
3. The defect-correction PPE subtracts the same operator applied to this proxy:
   `rhs <- rhs - L(J)`.
4. With the initially stationary wave, `rhs≈0`, so the elliptic solve computes
   `p_base≈-J`.
5. The returned pressure `p_total=p_base+J` is nearly zero.
6. Velocity correction sees almost no pressure gradient and therefore cannot
   start the capillary oscillation.
7. The interface is then transported by a tiny residual velocity; meanwhile
   curvature noise and the cap cause grid-scale corrugation, increasing the
   unsigned amplitude without producing a signed-mode oscillation.

This is a discrete mathematical inconsistency, not a parameter-tuning problem.

## What is explicitly not a valid fix

The following would be small technical tricks and should not be treated as root
fixes:

- decreasing `dt` or the CFL multiplier without changing the stress-jump equation;
- increasing `T`;
- raising the curvature cap to hide `kappa_max` saturation;
- smoothing curvature until the plot looks calmer;
- changing only the plotting metric from unsigned amplitude to signed mode;
- switching to a different pressure warm start;
- increasing GMRES iterations while solving the same cancelled equation.

## Theory-faithful next verification

The next step should be a mathematical verification before any production fix:

1. Construct a discrete operator test with zero predictor velocity and a known
   sinusoidal interface jump.  The test should assert that the pressure/velocity
   correction does not collapse to `p_total≈0`.
2. Compare two formulations:
   - sharp-interface jump condition imposed as an operator/interface constraint
     (IIM/GFM-style);
   - equivalent balanced singular/regularized force with a proven discrete
     energy law.
3. Only after that, rerun capillary waves with the same `A0`, `m`, `rho`, and
   `sigma`, first on uniform periodic/deep-wall controls, then on the current
   interface-fitted grid.

The acceptance criterion should be signed-mode phase response, not only volume
conservation.

[SOLID-X] Analysis artifacts only; no production code changed.
