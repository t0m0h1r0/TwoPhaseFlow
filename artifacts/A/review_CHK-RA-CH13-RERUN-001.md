# Review CHK-RA-CH13-RERUN-001

Date: 2026-05-03
Role: ResearchArchitect
Branch: `ra-ch13-reexperiment-audit-20260503`
Worktree: `.claude/worktrees/ra-ch13-reexperiment-audit-20260503`
Lock: `docs/locks/ra-ch13-reexperiment-audit-20260503.lock.json`

## Verdict

Chapter 13 required a targeted rerun. The Chapter 4--11 narrative edits alone did
not invalidate Chapter 13 data, but two post-rerun code changes did touch the
Chapter 13 §14-stack subset:

- `79259adb` adds projection-native ψ transport from canonical face velocities.
- `210b579a` changes affine pressure-history consumption from nodal pressure gradients to projection-native face pressure acceleration.

These affect V6/V7/V9 because they run through `TwoPhaseNSSolver` and the
FCCD/UCCD6/HFE/pressure-jump phase-separated PPE stack. V10 was audited but not
rerun as a required dependency because it calls `FCCDLevelSetAdvection.advance()`
directly; the new `advance_with_face_velocity()` route is not used there.

## Rerun Scope

Remote-first runs were executed for:

- V6: `make run EXP=experiment/ch13/exp_V6_density_ratio_convergence.py`
- V7: `make run EXP=experiment/ch13/exp_V7_imex_bdf2_twophase_time.py`
- V9: `make run EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py`

Local sandbox attempts fell back to CPU and failed on missing `matplotlib`, so the
accepted runs are the remote runs. Results were pulled with `make pull`, and the
tracked paper figures were regenerated locally from pulled NPZ files using the
parent `.venv` plus `PYTHONPATH=src`.

## Result Changes

- V6 remains stable for all 8 density-ratio cases. The updated pressure-corrector diagnostic is `1.49--2.01`; the finest water-air case gives `u_final=2.421e-04`, and CLS volume drift remains at round-off floor (`<=6.4e-16`).
- V7 finest local slope changed from `1.04` to `1.48`. The paper now records this as a splitting/cadence-limited coupled-stack regime: above the Lie first-order lower bound but still below standalone BDF2 order `2.0`.
- V9 remains a no-regression switch diagnostic. B/C are still identical; at `N=32`, A/B/C are effectively equal (`C/A=1.00`, `C/B=1.00`), and max volume drift is now `3.79e-08`.
- Conclusion cross-references for V10-b were also synchronized to the already-current Chapter 13 table values: mass drift `0.0428%`, reversal `L^1=2.248e-02`.

## Paper/Figure Updates

- Updated V6 table, caption, pressure-corrector range, and field caption in `paper/sections/13d_density_ratio.tex`.
- Updated V7 table, caption, Type-D interpretation, front matter, introduction, summary table, and conclusion.
- Updated V9 table and no-regression ratios in `paper/sections/13e_nonuniform_ns.tex` and `paper/sections/13f_error_budget.tex`.
- Regenerated tracked figures:
  - `paper/figures/ch13_v6_density_ratio.pdf`
  - `paper/figures/ch13_v6_density_ratio_fields.pdf`
  - `paper/figures/ch13_v7_imex_bdf2_time.pdf`
  - `paper/figures/ch13_v9_local_eps.pdf`
  - `paper/figures/ch13_v9_ch14_stack_field.pdf`

## Validation

- `git diff --check` PASS.
- Targeted stale-value scan PASS for obsolete V7/V9/V10 values, excluding unrelated numeric matches and one explicit historical note about the previous V7 rerun.
- Remote reruns PASS for V6/V7/V9.
- `make pull` PASS.
- Plot-only regeneration PASS for V6/V7/V9 using pulled data.
- `make -C paper` PASS (`paper/main.pdf`, 243 pages). Remaining diagnostics are existing underfull hbox in `sections/09f_pressure_summary.tex:57` and Chapter 12 float-only page warning.

## SOLID Audit

[SOLID-X] no violation found. This CHK changes paper text, tracked figures, and
review/ledger bookkeeping only; no production code boundary changed, no tested
implementation was deleted, and no FD/WENO/PPE fallback was introduced.

## Merge Status

Not merged to `main`. Per user instruction, main merge requires an explicit later
request and must use no-ff.
