# Review CHK-RA-CH13-V7-IMEX-001

Date: 2026-05-03
Role: ResearchArchitect
Branch: `ra-ch13-v7-imex-bdf2-rca-20260503`
Worktree: `.claude/worktrees/ra-ch13-v7-imex-bdf2-rca-20260503`
Lock: `docs/locks/ra-ch13-v7-imex-bdf2-rca-20260503.lock.json`

## Verdict

V7 の低次数は IMEX-BDF2 単体の係数ミスではなく，§14 stack の
capillary pressure-jump / affine FCCD projection が界面帯で作る低正則性・分裂誤差が
支配している。再初期化 cadence と参照解品質は係数を変えるが，観測指数を 2 へ戻す
主因ではない。

## Evidence Summary

Baseline V7 rerun reproduced the paper value:

- `make run EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py`
- ref `n=64`, rows `n=8,16,32`
- finest local slope: `1.48`

New diagnostic script:

- `experiment/ch13/diagnose_V7_imex_bdf2_order.py`
- ref `n=128`, rows `n=8,16,32,64`
- variants: `each_step`, `fixed_reinit_count`, `no_reinit`, `static_interface`,
  `static_no_capillary`, `uniform_static_capillary`, `uniform_static_no_capillary`

Key measured outcomes:

| Variant | Changed factor | finest velocity slope | `n=64` velocity `L_inf` vs ref128 | Interpretation |
|---|---:|---:|---:|---|
| `each_step` | original `reinit_every=1` | `1.59` | `3.666e-03` | ref64 slightly under-resolves, but not enough to recover 2nd order |
| `fixed_reinit_count` | 3 reinitializations for every run | `1.50` | `9.358e-04` | cadence changes constant, not exponent |
| `no_reinit` | no reinitialization | `1.57` | `1.670e-03` | reinit is not the primary order limiter |
| `static_interface` | no interface advection/reinit | `1.58` | `1.870e-03` | TVD-RK3/IMEX Lie splitting is not necessary for the low order |
| `static_no_capillary` | static interface, `sigma=0` | `1.54` | `6.831e-08` | removing capillary jump collapses the error by 4--5 orders |
| `uniform_static_capillary` | `rho,mu` uniform, `sigma=1` | `1.59` | `8.198e-03` | capillary jump alone is sufficient to reproduce large error |
| `uniform_static_no_capillary` | uniform coefficients, `sigma=0` | `1.58` | `7.302e-08` | density/viscosity jumps are not the amplitude source |

Localization check:

- baseline max velocity error at `n=64` occurs at `psi_ref ~= 0.47`, i.e. the interface band.
- static capillary max error occurs at `psi_ref = 0.5`.
- bulk `L_inf` is orders smaller than interface-band `L_inf`.
- volume drift remains at round-off in baseline V7; mass conservation is not the cause.

## Hypothesis Audit

| ID | Hypothesis | Result | Evidence |
|---|---|---|---|
| H01 | `n_ref=64` is too coarse | Secondary | ref128 changes finest slope from `1.48` to `1.59`, not to `2` |
| H02 | step-based reinit cadence is the root cause | Rejected as primary | fixed reinit count still gives slope `1.50` |
| H03 | reinitialization itself is the root cause | Rejected as primary | no-reinit still gives slope `1.57` |
| H04 | TVD-RK3 interface transport / IMEX-BDF2 Lie split is required for the low order | Rejected as necessary | static-interface slope remains `1.58` |
| H05 | capillary pressure-jump projection dominates | Supported | `sigma=0` collapses error from `1e-3--1e-2` to `1e-7` |
| H06 | density ratio drives the amplitude | Rejected as primary | uniform coefficients with `sigma=1` still gives `8.198e-03` |
| H07 | viscosity ratio drives the amplitude | Rejected as primary | same as H06 |
| H08 | `L_inf` norm alone creates the verdict | Partly supported | `L2` has similar finest slopes, but max error is interface-local |
| H09 | bulk velocity dynamics are the limiter | Rejected | bulk errors are orders smaller than band errors |
| H10 | IMEX-BDF2 coefficient implementation is wrong | Rejected | U8 BDF2 unit checks pass; `sigma=0` variants are near machine-small |
| H11 | affine pressure-history face contract is the old nodal-gradient bug | Rejected for current code | current code uses projection-native face acceleration; remaining error is capillary jump band |
| H12 | BDF1 startup is the dominant source | Not supported as primary | all controls retain similar exponent, while capillary controls change amplitude by orders |
| H13 | spatial grid `N=24` is the only issue | Secondary | same grid with `sigma=0` has tiny error; grid/interface band affects constants and norm |
| H14 | PPE solver tolerance/DC iteration is the source | Not indicated | removing capillary jump collapses error without changing solver settings |
| H15 | curvature/reinit update frequency is the source | Rejected as primary | static interface keeps the same curvature and still shows capillary-limited behavior |
| H16 | pressure discontinuity low regularity limits max-norm temporal convergence | Supported | max error sits at `psi ~= 0.5`; capillary jump is sufficient |
| H17 | wall boundary condition dominates | Rejected | max error is on the circular interface, not the wall |
| H18 | volume/mass drift contaminates the velocity norm | Rejected | baseline volume drift is round-off |
| H19 | GPU/CPU path mismatch is responsible | Not indicated | remote production path is stable and reproduces paper values |
| H20 | V7 should be read as pure BDF2 order verification | Rejected | V7 is a capillary pressure-jump coupled-stack diagnostic; U8 remains the pure BDF2 evidence |

## Root Cause

The active V7 error is a capillary jump/projection interface-band error:

1. The pressure field has an imposed Laplace jump represented through the affine FCCD PPE contract.
2. The velocity correction and pressure-history acceleration close on cut faces, where the solution is low-regularity even when the interface is frozen.
3. The max and RMS velocity differences are dominated by the smeared interface band, not by the bulk.
4. Removing only the capillary jump reduces the velocity error by 4--5 orders while keeping the same time integrator, grid, projection machinery, and initial velocity.

Therefore the theoretically faithful interpretation is Type-D: V7 measures the effective temporal behavior of the full capillary pressure-jump stack, not the standalone IMEX-BDF2 design order. A legitimate path to order `2` would require a structural capillary-jump/projection time-discretization upgrade or a different verification problem that isolates BDF2; changing constants, disabling reinit, or retuning thresholds is not a root fix.

## Validation

- `py_compile` PASS for `experiment/ch13/diagnose_V7_imex_bdf2_order.py`.
- `git diff --check` PASS before diagnostic commits.
- Baseline remote V7 PASS.
- Diagnostic remote run PASS after `make push`.
- Targeted `rsync` pulled `experiment/ch13/results/diagnose_V7_imex_bdf2_order/data.npz`.

Note: a broad `make pull` was stopped after `ch13/results` completed because it hung on unrelated `ch14/results` rsync; final V7 diagnostic data was pulled by targeted rsync.

## SOLID Audit

[SOLID-X] no production boundary violation found. Changes add an experiment diagnostic and paper/audit text only; no tested implementation was deleted, no FD/WENO/PPE fallback was introduced, and no numerical workaround was applied.
