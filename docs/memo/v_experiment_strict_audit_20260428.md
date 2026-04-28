# V* Experiment Strict Audit — 2026-04-28

Scope: `experiment/ch13/exp_V1_*.py` through `exp_V10_*.py`, excluding V9 because it was just reworked onto the §14 stack.  
Audit standard: paper claim ↔ numerical problem ↔ solver/operator path ↔ diagnostic/figure fidelity.

## Executive Verdict

| ID | Verdict | Reason |
|---|---|---|
| V1 | **FAIL as written** | Paper claims CCD + AB2/IMEX-BDF2 + PPE, but implementation is FFT spectral TGV with spectral projection. |
| V2 | **FATAL mismatch** | Paper says Kovasznay residual; script solves a manufactured periodic Taylor--Green-like residual. |
| V3 | **Usable reduced test** | Paper settings match code, but script docstring overclaims split-PPE/FCCD/HFE and has stale We text. |
| V4 | **Conditionally aligned** | Paper correctly demotes Galilean/RT claims; code is reduced/stale-commented, not a production invariance proof. |
| V5 | **Usable reduced test, diagnostics stale** | Final-time table aligns with cache, but script/figure still use peak ratio and a stale 20x pass line. |
| V6 | **FATAL mismatch** | Paper claims split-PPE + DC + HFE; code uses smoothed density, `PPEBuilder`, direct sparse solve, no split/DC/HFE. |
| V7 | **FATAL/major mismatch** | Paper causal story cites CLS reinitialization; code has no reinit or interface transport and uses a hand-rolled BDF2/PPE loop. |
| V8 | **Usable reduced nonuniform static test** | Nonuniform grid + CCD/PPE static droplet is real, but script overclaims FCCD/Ridge-Eikonal/production stack. |
| V10 | **Mostly correct FCCD/TVD-RK3 path** | Uses FCCD flux + TVD-RK3, but volume metric is thresholded area and saved `psi0` is stale for `alpha>1`. |

## Blocking Issues

### V1: spectral proxy, not CCD/PPE validation

- Paper says TGV is solved by CCD spatial discretization, AB2/IMEX-BDF2 time discretization, and PPE projection: `paper/sections/13a_single_phase_ns.tex:12`.
- Script builds FFT wavenumbers and uses spectral projection: `experiment/ch13/exp_V1_tgv_energy_decay.py:63`, `experiment/ch13/exp_V1_tgv_energy_decay.py:76`.
- The RHS explicitly uses spectral derivatives, only described as “equivalent to high-order CCD in the limit”: `experiment/ch13/exp_V1_tgv_energy_decay.py:87`.
- Required action: either relabel V1 as a spectral reference/time-order proxy or reimplement via the actual CCD/PPE path.

### V2: Kovasznay paper claim does not match script

- Paper states Kovasznay analytic solution and 6th-order CCD residual: `paper/sections/13a_single_phase_ns.tex:76`.
- Script title and docstring state manufactured periodic NS, not Kovasznay: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:2`.
- Implemented field is `sin(x)cos(y)` / `-cos(x)sin(y)`: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:70`.
- Residual target uses Taylor--Green-like pressure terms, not Kovasznay: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:93`.
- Required action: implement true Kovasznay residual or rewrite paper/table/figure labels as manufactured periodic NS.

### V6: split-PPE/DC/HFE claim is unsupported

- Paper explicitly claims “分相 PPE + DC + HFE 統合”: `paper/sections/13d_density_ratio.tex:13`.
- Code imports and instantiates `PPEBuilder`, `CCDSolver`, `CurvatureCalculator`; no split-PPE/DC/HFE path: `experiment/ch13/exp_V6_density_ratio_convergence.py:43`, `experiment/ch13/exp_V6_density_ratio_convergence.py:122`.
- PPE solve calls `ppe_builder.build(rho)` and direct sparse solve: `experiment/ch13/exp_V6_density_ratio_convergence.py:76`.
- Paper says `Δt = h/2`; code uses `CFL_FACTOR = 0.20`: `paper/sections/13d_density_ratio.tex:24`, `experiment/ch13/exp_V6_density_ratio_convergence.py:68`.
- Required action: reimplement V6 via the §14/production split-PPE + HFE/DC chain, or demote paper wording to a smoothed-density reduced sweep.

### V7: no CLS reinitialization despite paper explanation

- Paper explains the poor slope by per-step CLS reinitialization frequency differences: `paper/sections/13d_density_ratio.tex:131`.
- Code computes `phi`, `psi`, `rho`, curvature, and CSF force once; the loop only advances velocity with a static force: `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:132`, `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:152`.
- There is no reinitializer, no level-set advection, no split-PPE, no HFE, and no `TwoPhaseNSSolver`; PPE is direct `PPEBuilder`: `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:82`, `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:126`.
- Paper says `N=64`; code uses `N_GRID=128`: `paper/sections/13d_density_ratio.tex:94`, `experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:72`.
- Required action: either run the real production IMEX/two-phase path with interface transport/reinit, or remove the reinit-based causal explanation.

## Non-Blocking but Needs Cleanup

### V3

- Paper settings match code: `sigma=1`, `rho_l=10`, `rho_g=1`, `dt=h/4`, `200` steps: `paper/sections/13b_twophase_static.tex:20`, `experiment/ch13/exp_V3_static_droplet_longterm.py:66`.
- Script docstring says split-PPE/FCCD/HFE and `We=10`; code uses plain `PPEBuilder` and `WE=1`: `experiment/ch13/exp_V3_static_droplet_longterm.py:6`, `experiment/ch13/exp_V3_static_droplet_longterm.py:69`.
- Required action: fix script contract/docstring unless V3 is reimplemented on the production stack.

### V4

- Paper now correctly frames V4-a as fixed-wall/Galilean-offset residual, not exact Galilean invariance: `paper/sections/13c_galilean_rt.tex:11`.
- Code docstring still says “Galilean invariance + RT”, and `U_frame` is stale/unused: `experiment/ch13/exp_V4_galilean_rt.py:2`, `experiment/ch13/exp_V4_galilean_rt.py:103`.
- V4-b is explicitly first-order level-set update in code and paper demotes it to a conditional setting check: `experiment/ch13/exp_V4_galilean_rt.py:245`, `paper/sections/13c_galilean_rt.tex:76`.
- Required action: cleanup wording only; do not cite V4 as a solver-invariance proof.

### V5

- Paper table says each cell is `u_inf_end`: `paper/sections/13b_twophase_static.tex:94`.
- Cached values confirm the table is final-time, not peak, for listed cells.
- Script figure/summary use `u_inf_peak_all` and still draw a stale “pass: 20x” line: `experiment/ch13/exp_V5_spurious_current_multistep.py:189`, `experiment/ch13/exp_V5_spurious_current_multistep.py:195`.
- Script docstring still claims split-PPE/HFE lineage and a 20x expectation: `experiment/ch13/exp_V5_spurious_current_multistep.py:6`, `experiment/ch13/exp_V5_spurious_current_multistep.py:24`.
- Required action: align figure labels/pass line with the paper’s weaker, data-supported conclusion.

### V8

- Code genuinely exercises nonuniform `alpha_grid=2` and static droplet CCD/PPE diagnostics: `experiment/ch13/exp_V8_nonuniform_ns_static.py:100`.
- Script docstring overclaims FCCD, nonuniform Ridge-Eikonal, and simultaneous production-stack validation: `experiment/ch13/exp_V8_nonuniform_ns_static.py:6`.
- Code path is CCD + `PPEBuilder` + static CSF, not FCCD/Ridge-Eikonal: `experiment/ch13/exp_V8_nonuniform_ns_static.py:47`, `experiment/ch13/exp_V8_nonuniform_ns_static.py:77`.
- Required action: demote docstring/claims or reimplement with the intended §14 operators.

### V10

- Code uses `FCCDLevelSetAdvection(mode="flux")`: `experiment/ch13/exp_V10_cls_advection_nonuniform.py:165`.
- `FCCDLevelSetAdvection.advance()` calls `tvd_rk3`, so the paper’s FCCD/TVD-RK3 claim is supported: `src/twophase/levelset/fccd_advection.py:82`, `src/twophase/levelset/fccd_advection.py:114`.
- “Volume” is thresholded `{psi > 0.5}` area, not conservative `∫psi dV`: `experiment/ch13/exp_V10_cls_advection_nonuniform.py:114`.
- For `alpha>1`, returned `psi0` is computed before grid rebuild, while `X/Y` are after rebuild: `experiment/ch13/exp_V10_cls_advection_nonuniform.py:135`, `experiment/ch13/exp_V10_cls_advection_nonuniform.py:153`, `experiment/ch13/exp_V10_cls_advection_nonuniform.py:178`.
- Required action: rename metric to thresholded area drift or add `∫psi dV`; recompute stored `psi0` after grid rebuild for nonuniform rows.

## SOLID / Process Findings

- `[SOLID-1]` V3/V5/V6/V7/V8 duplicate hand-rolled Predictor--PPE--Corrector loops instead of using one production NS pipeline. This is the root cause of several claim/implementation drifts.
- `[SOLID-2]` Experiment docstrings are being treated as contracts but are stale relative to both code and paper. Add a lightweight audit check for “claimed operators” vs imports/instantiated classes before publishing tables.
- `[A3-FIDELITY]` V2/V6/V7 violate Equation → Discretization → Code traceability; the paper references one chain while the code executes another.

## Recommended Fix Order

1. Fix or demote V6 and V7 first; they directly claim §14-style split-PPE/HFE/IMEX behavior.
2. Fix V2 next; the problem identity is wrong, not merely a label.
3. Reframe or reimplement V1; decide whether it is a spectral reference or actual CCD/PPE validation.
4. Cleanup V3/V4/V5/V8 docstrings and figure labels to match reduced-test reality.
5. Patch V10 diagnostics (`psi0` after grid rebuild, `thresholded area` vs `∫psi dV`) before citing volume preservation strongly.
