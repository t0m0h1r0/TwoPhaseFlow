# Review CHK-RA-CH13-001

Date: 2026-05-03
Scope: `experiment/ch13/*`, `paper/sections/13*.tex`, `paper/figures/ch13_*.pdf`, with consistency checked against the latest Chapters 4--12 contracts.
Branch: `ra-ch13-experiment-audit-20260503`
Worktree: `.claude/worktrees/ra-ch13-experiment-audit-20260503`
Lock: `docs/locks/ra-ch13-experiment-audit-20260503.lock.json`

## Verdict

PASS after Chapter 13 experiment refresh. Open FATAL: 0. Open MAJOR: 0. Open MINOR: 0.

## Contract Audit Against Chapters 4--12

- No active Chapter 13 production script uses retired CCD-LU PPE, LGMRES/BiCGSTAB PPE, WENO production transport, or stale CN/ADI time-integration framing.
- V6/V7/V9 use the current §14 stack subset: FCCD interface/pressure gradient, UCCD6 convection, HFE/direct-ψ curvature, pressure-jump surface tension, phase-separated PPE/DC, and face-flux projection.
- V8 remains explicitly scoped as a reduced CSF/nonuniform static-droplet diagnostic, not a production pressure-jump/HFE long-time moving-interface claim.
- V10 remains explicitly scoped to fixed uniform-grid CLS advection; nonuniform moving-interface advection is still a future gate, not a current Chapter 13 guarantee.

## Reviewer Findings And Fixes

### MAJOR-1: Paper tables drifted from the rerun data

Finding: V5--V10 values in the paper no longer matched the latest Chapter 13 rerun. The largest changes were V6 density-ratio diagnostics, V7 coupled-stack time slope, V8 nonuniform pressure/velocity values, V10 mass drift, and V10-b reversal error.

Fix: Updated `paper/sections/13b_twophase_static.tex`, `paper/sections/13d_density_ratio.tex`, `paper/sections/13e_nonuniform_ns.tex`, and `paper/sections/13f_error_budget.tex` to the rerun values. Representative refreshed values:

- V5: CCD $u_\infty^{end}=1.93\times10^{-2}$ at $\rho_r=1,N=32$; FD ratio $1/5.44$.
- V6: all 8 density-ratio cases stable; CLS volume drift $\le 6.4\times10^{-16}$; pressure-corrector ratio $0.73$--$1.00$.
- V7: coupled-stack finest local slope $1.04$, aligned with the Lie-splitting lower limit.
- V8: $\alpha=2,N=96$ pressure error $2.86\%$.
- V10-a: Zalesak $N=128$ mass drift $4.70\times10^{-4}\%$, centroid order $1.22$.
- V10-b: single-vortex mass drift $0.0428\%$, $L^1$ reversal error $2.248\times10^{-2}$.

### MAJOR-2: V9 overstated local-epsilon efficacy

Finding: The current V9 rerun shows B (nonuniform nominal) and C (nonuniform local) are numerically identical in the direct-ψ/HFE short static probe. The old paper text claimed C was quieter than nominal, which is not supported by the current data.

Fix: Reframed V9 as a nominal/local $\varepsilon$ switch diagnostic rather than a local-epsilon superiority test. `paper/sections/13e_nonuniform_ns.tex`, `paper/sections/13_verification.tex`, and `paper/sections/13f_error_budget.tex` now state that B/C equality is a valid diagnostic outcome: the local switch does not degrade the §14-stack short static probe, but it is not evidence of improvement. `experiment/ch13/exp_V9_local_eps_nonuniform.py` docstrings, figure title, and summary text were updated accordingly, and V9 figures were regenerated from cached data.

### MINOR-1: Type-D wording implied unsupported near-optimality

Finding: After the V7 rerun, slope $1.04$ is Lie-limited, not near-optimal above the Lie lower bound.

Fix: Updated Type-D wording in `paper/sections/13_verification.tex`, `paper/sections/13d_density_ratio.tex`, and `paper/sections/13f_error_budget.tex` to say “theoretical hard limit と整合” / “Lie-limited” instead of near-optimal for V7.

## Sufficiency Review

- The current V1--V10 suite is necessary and sufficient for Chapter 13’s bounded claim: integrated verification of the Chapter 4--12 equation/discretization/code chain under reduced static, density-ratio, time-coupled, nonuniform-static, and uniform-CLS advection diagnostics.
- No additional experiment is required for the current Chapter 13 claim after V9 is narrowed to a switch/stability diagnostic.
- The following remain explicit future gates, not missing current requirements: nonuniform moving-interface Zalesak/single-vortex, long-time pressure-jump/HFE nonuniform moving-interface statistics, and a reinitialization-active local-thickness efficacy test.

## Final Checks

- Remote-first experiment refresh: `make run-all CH=ch13` PASS; `make pull` PASS.
- V9 plot refresh: `make plot EXP=experiment/ch13/exp_V9_local_eps_nonuniform.py` failed locally because plain `python3` lacked `matplotlib`; fallback `.venv` plot-only run PASS and regenerated `paper/figures/ch13_v9_local_eps.pdf` plus `paper/figures/ch13_v9_ch14_stack_field.pdf`.
- Paper build: `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` PASS (`paper/main.pdf`, 244 pp).
- Log guard: no fatal undefined/citation/multiply-defined warnings found; only the package-name occurrence of `rerunfilecheck`.
- Static checks: `git diff --check` PASS; targeted `py_compile` for `experiment/ch13/exp_V9_local_eps_nonuniform.py` PASS.
- SOLID audit: [SOLID-X] paper/script/figure refresh only; no production boundary changed, no tested code deleted, no FD/WENO/PPE fallback introduced, and PR-4 `--plot-only` workflow remains intact.

## Merge Status

Not merged to `main`. Per user instruction, the work continues on `ra-ch13-experiment-audit-20260503` until an explicit main-merge request is given.
