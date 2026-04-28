# ResearchArchitect strict rereview: chapter 8

Date: 2026-04-28
Branch: `worktree-ra-ch8-review`
Scope: post-CHK-253 rereview of `paper/sections/08*.tex`

## Verdict

FAIL until the residual Major below is fixed. CHK-253 closed the coefficient, IPC time-width, and reference issues, but the hydrostatic BF diagnostic still defines a metric that cannot vanish under the stated gravity problem.

## Findings

### MAJOR-1: hydrostatic BF metric omits the gravity term it is supposed to balance

- Location: `paper/sections/08e_fccd_bf.tex:96`
- Problem: The section defines a gravity hydrostatic test, but measures `max |u_f^{n+1}|` after one IPC step with `u^*=0, p=p_stat`. With the corrector `u_f^{n+1}=u_f^*-\Delta t_{\mathrm{proj}}\betaf p'_f`, this setup omits the gravitational acceleration term and therefore cannot represent hydrostatic balance by itself.
- Evidence: Chapter 7 says hydrostatic components are absorbed/cancelled by balanced-buoyancy, with only residual acceleration entering the predictor (`paper/sections/07_time_integration.tex:823`, `paper/sections/07_time_integration.tex:850`). Chapter 13's hydrostatic verification explicitly tests the Predictor--PPE--Corrector balance between gravity and pressure gradient (`paper/sections/13b_force_balance.tex:18`).
- Required fix: Define the diagnostic as a discrete force/acceleration residual, e.g. `a^g_f-\betaf(G_h^\text{bf}p_\text{stat})_f`, or explicitly include the balanced gravity predictor contribution before measuring the post-corrector velocity.

### MINOR-1: projection derivation still reads like a full NS time step

- Location: `paper/sections/08b_pressure.tex:24`
- Problem: The text says it extracts only the projection stage, but the displayed equation still looks like the full discrete NS equation with `\Delta t_{\mathrm{proj}}`. This is acceptable as algebraic shorthand but brittle for reviewers.
- Required fix: Rename the residual to a projection-stage residual and state that non-pressure terms are those already assembled by the time integrator in Chapter 7.

## SOLID audit

[SOLID-N/A] No `src/twophase/` code changes are in scope. This is paper-domain P3/A3 consistency only.
