# Review CHK-RA-CH13-V10-SHAPE-001

Date: 2026-05-03
Role: ResearchArchitect
Branch: `ra-ch13-v10-shape-rca-20260503`
Worktree: `.claude/worktrees/ra-ch13-v10-shape-rca-20260503`
Lock: `docs/locks/ra-ch13-v10-shape-rca-20260503.lock.json`

## Verdict

最新コードで V10-a/b の形状誤差は自然解消しなかった。baseline rerun は紙面値を再現した。

Root cause は小手先の mass correction / CFL / reinit cadence ではない。

- V10-a: fixed uniform grid 上の steep CLS 空間移流で、FCCD flux-form の位相/thresholded geometry 誤差に Zalesak slot/corner の under-resolution が重なる。slot は shape L1 を約 2 倍にするが、centroid 誤差の唯一原因ではない。
- V10-b: T=8 single-vortex の deformation が folded filament を grid-scale まで薄くし、固定 Eulerian grid では可逆復元できない。reinit/correction/time-step の小変更では救えない。

## Baseline Rerun

Command:

- `make cycle EXP=experiment/ch13/exp_V10_cls_advection_nonuniform.py`

Result:

| Test | Metric | Latest rerun |
|---|---:|---:|
| V10-a N=64 | centroid err | `1.145e-02` |
| V10-a N=64 | shape L1 | `1.457e-02` |
| V10-a N=64 | mass drift | `2.811e-04` |
| V10-a N=128 | centroid err | `4.911e-03` |
| V10-a N=128 | shape L1 | `8.307e-03` |
| V10-a N=128 | mass drift | `4.703e-06` |
| V10-b N=128,T=8 | reversal L1 | `2.248e-02` |
| V10-b N=128,T=8 | mass drift | `4.281e-04` |

Interpretation: latest code did not change the V10 shape verdict; analysis must explain the existing error.

## Diagnostic Experiment

Script:

- `experiment/ch13/diagnose_V10_shape_error.py`

Command:

- `make cycle EXP=experiment/ch13/diagnose_V10_shape_error.py`

Output:

- `experiment/ch13/results/diagnose_V10_shape_error/data.npz`

### V10-a Results

| Variant | Changed factor | centroid err | shape L1 | mass drift | Interpretation |
|---|---:|---:|---:|---:|---|
| `slot_N64` | baseline coarse | `1.145e-02` | `1.457e-02` | `2.811e-04` | reproduces paper |
| `slot_N128` | baseline fine | `4.911e-03` | `8.307e-03` | `4.703e-06` | reproduces paper |
| `circle_N128` | remove slot/corners | `5.461e-03` | `3.877e-03` | `2.388e-06` | slot drives L1 excess, not centroid alone |
| `wide_slot_N128` | slot/h from `6.4` to `12.8` | `7.191e-03` | `7.735e-03` | `8.283e-05` | width alone is not a monotone fix |
| `slot_N128_no_mc` | no mass correction | `4.688e-03` | `8.375e-03` | `1.464e-02` | mass drift worsens, shape unchanged |
| `slot_N128_mc1` | mass correction every step | `4.911e-03` | `8.307e-03` | `0.000e+00` | correction cadence not shape cause |
| `slot_N128_cfl_half` | half CFL | `4.911e-03` | `8.313e-03` | `0.000e+00` | TVD-RK3 time error not dominant |
| `slot_N128_eps1` | thinner interface | `8.003e-03` | `1.171e-02` | `4.478e-05` | simple sharpening worsens shape |

### V10-b Results

| Variant | Changed factor | reversal L1 | mass drift | width proxy / h | Interpretation |
|---|---:|---:|---:|---:|---|
| `sv_N64_T1` | mild deformation | `1.672e-03` | `2.616e-05` | `6.19` | resolved filament, small error |
| `sv_N64_T2` | standard stress | `2.227e-03` | `1.484e-04` | `3.81` | still modest |
| `sv_N64_T4` | stronger deformation | `1.213e-02` | `7.680e-04` | `2.01` | grid-scale onset |
| `sv_N64_T8` | production stress at coarse N | `5.013e-02` | `2.069e-03` | `1.62` | grid-scale filament dominates |
| `sv_N64_T8_no_reinit` | no reinit | `5.170e-02` | `4.228e-01` | `1.50` | reinit not root; mass fails |
| `sv_N64_T8_reinit1` | reinit every step | `6.055e-02` | `9.557e-04` | `1.75` | over-reinit worsens shape |
| `sv_N64_T8_mass_off` | no mass correction in reinit | `3.210e-02` | `2.029e-01` | `1.48` | lower L1 is bought by unacceptable mass loss |
| `sv_N64_T8_cfl_half` | half CFL | `5.294e-02` | `1.451e-03` | `1.67` | time step not dominant |
| `sv_N128_T2` | finer standard stress | `9.860e-04` | `4.562e-06` | `8.16` | refinement helps when feature resolved |
| `sv_N128_T4` | finer strong stress | `4.324e-03` | `3.135e-05` | `4.38` | error rises as filament thins |
| baseline `sv_N128_T8` | production | `2.248e-02` | `4.281e-04` | `2.03` | production error consistent with grid-scale folded filament |

## Hypothesis Audit

| ID | Hypothesis | Result | Evidence |
|---|---|---|---|
| H01 | Latest code already fixes V10 shape error | Rejected | baseline rerun exactly reproduces paper values |
| H02 | V10-a mass drift contaminates shape metrics | Rejected | no mass correction changes mass drift to `1.464%` but shape L1 stays `8.375e-03` |
| H03 | V10-a mass correction cadence causes geometry drift | Rejected | every-step correction gives same centroid/L1 as every 10 steps |
| H04 | V10-a TVD-RK3 time error dominates | Rejected | half CFL leaves centroid and L1 unchanged |
| H05 | V10-a slot/corner under-resolution is the only cause | Partly rejected | removing slot halves L1 but centroid remains `5.461e-03` |
| H06 | V10-a slot/corner under-resolution contributes to L1 | Supported | slot L1 `8.307e-03` vs circle L1 `3.877e-03` |
| H07 | V10-a smooth-body fixed-grid phase/threshold error contributes to centroid | Supported | smooth circle centroid error is same order as slotted disk |
| H08 | V10-a simple interface sharpening fixes shape | Rejected | `eps_ratio=1.0` worsens centroid and L1 |
| H09 | V10-a wider slot is a monotone fix | Rejected | width `0.10` lowers L1 only slightly and worsens centroid |
| H10 | V10-a nonuniform/moving mesh is required for the next improvement | Plausible future gate | current fixed uniform grid controls reject local retuning |
| H11 | V10-b is primarily a mass conservation failure | Rejected | baseline mass drift is `0.0428%`; no-reinit mass fails but L1 remains same order |
| H12 | V10-b reinitialization absence is the root cause | Rejected | no-reinit does not improve L1 and destroys mass |
| H13 | V10-b over-reinitialization fixes reversibility | Rejected | reinit every step worsens L1 to `6.055e-02` |
| H14 | V10-b mass correction itself causes all shape error | Rejected as remedy | mass-off lowers L1 only by losing `20.3%` mass |
| H15 | V10-b TVD-RK3 time step dominates | Rejected | half CFL does not improve L1 |
| H16 | V10-b deformation time controls shape error | Supported | N64 T1/T2/T4/T8 L1 grows `1.67e-03 -> 5.01e-02` |
| H17 | V10-b filament width relative to h controls error | Supported | width proxy/h drops `6.19 -> 1.62` as L1 rises |
| H18 | V10-b grid refinement helps while features are resolved | Supported | N128 T2/T4 errors are below N64 counterparts |
| H19 | V10-b production T=8 remains near the fixed-grid resolution limit | Supported | N128 T8 width proxy/h `2.03`, L1 `2.248e-02` |
| H20 | Local parameter retuning is an acceptable fix | Rejected by policy and evidence | all admissible local knobs fail or violate mass |

## Root Cause

### V10-a

Equation chain:

`paper/sections/06b_advection.tex` CLS advection and mass correction
-> `paper/sections/13e_nonuniform_ns.tex` V10-a setup
-> `experiment/ch13/exp_V10_cls_advection_nonuniform.py`
-> `experiment/ch13/diagnose_V10_shape_error.py`

The Zalesak test is not a smooth asymptotic-order test.  The transported field is a steep
logistic CLS profile over a non-smooth slotted disk.  Even without the slot, thresholded
centroid after one rigid rotation has an O(1e-3) fixed-grid phase/geometry error.  Adding the
slot doubles the L1 shape discrepancy because the slot width is only `6.4h` and `4.27 eps`.
Mass correction and CFL controls do not move the shape metrics.

### V10-b

Equation chain:

LeVeque/Rider-Kothe reversible single-vortex advection
-> FCCD/TVD-RK3 CLS transport
-> Ridge-Eikonal reinitialization + Olsson-Kreiss mass correction
-> fixed uniform Eulerian grid reversal diagnostic.

The T=8 stress case creates grid-scale folded filaments at maximum deformation.  Once the
interface feature is O(h), a fixed Eulerian grid cannot preserve a reversible geometric map.
Reinitialization and mass correction keep the representation bounded and conservative, but
they are not reversible geometry operators.  PLS/AMR/moving-mesh class changes would be
needed for a true shape-axis improvement; local retuning is not a theory-valid fix.

## Paper Updates

Updated:

- `paper/sections/13_verification.tex`
- `paper/sections/13e_nonuniform_ns.tex`
- `paper/sections/13f_error_budget.tex`
- `paper/sections/15_conclusion.tex`

Main correction: V10-a is no longer described as slot-only, and V10-b is no longer phrased as
a literal global `filament < h` assertion.  The text now records fixed-grid phase/threshold
error plus slot under-resolution for V10-a, and grid-scale folded filament limitation for V10-b.

## SOLID-X

No production solver boundary was changed.  The only code change parameterizes the existing
V10 experiment defaults and adds a diagnostic script.  No tested implementation was deleted,
and no FD/WENO/PPE fallback or tuning workaround was introduced.
