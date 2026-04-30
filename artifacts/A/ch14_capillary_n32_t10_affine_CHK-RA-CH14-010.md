# CHK-RA-CH14-010 — ch14 capillary-wave N32 T10 affine run

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch: `ra-ch14-capillary-rootcause-20260430`
- Main incorporated: local `main` at `c8b40fee`, merged into this branch as `a2c8ec4`
- User request: 最新の `main` を取り込んだうえ，`N=32`, `T=10` の毛管波実験を行う。
- Temporary config: `experiment/ch14/config/ch14_capillary_n32_t10_affine.yaml` (not committed; removed after run)
- Result directory: `experiment/ch14/results/ch14_capillary_n32_t10_affine/` (gitignored)

## Config

- Base: `experiment/ch14/config/ch14_capillary.yaml` after latest `main`
- Grid: `32 x 32`
- Requested final time: `10.0`
- Output: `results/ch14_capillary_n32_t10_affine`
- Print cadence: `100`
- Interface stress: `pressure_jump` + `interface_coupling: affine_jump`
- Stack: FCCD PPE + HFE curvature + UCCD6 convection

## Execution

- Command: `make cycle EXP=experiment/run.py ARGS="--config ch14_capillary_n32_t10_affine"`
- Remote environment: `TWOPHASE_USE_GPU=1` via `remote.sh run`
- Wall time: `real 21m57.037s`
- Outcome: did not reach `T=10`; runner stopped at BLOWUP guard.
- BLOWUP guard: `src/twophase/simulation/runner.py` stops when `kinetic_energy` is `NaN` or `> 1e6`.
- Stop point: `step=884`, `t=4.8825421616`

## Diagnostics

- `times`: `n=884`, first `5.5820240448e-03`, final `4.8825421616`
- `interface_amplitude`: `1.1969774732e-02 -> 7.4962298424e-02`, max `7.4982011377e-02`
- `kinetic_energy`: `1.3826117332e-09 -> 4.6036847916e+06`, max `4.6036847916e+06`
- `volume_conservation`: final `1.6604080212e-05`, max `5.1135973387e-05`
- `dt_limit`: max `5.5820240448e-03`, min `5.8676393869e-05`, final `1.4851490591e-03`
- `dt_limiter_code`: capillary initially (`3`), advective near failure (`1`)
- First advective-limited step: `step=869`, `t=4.8489940568`
- `kappa_max`: cap hit first at `step=101`, `t=0.5637844285`; max `5.0`
- `ppe_rhs_max`: final `1.5466937883e+07`, max `2.4386901085e+07`
- `bf_residual_max`: final `2.0672922869e+07`, max `3.3685626110e+07`
- `div_u_max`: final/max `4.0251579070e+02`
- Affine path: `ppe_interface_coupling_affine_jump = 1` all steps; legacy `jump = 0` all steps
- Snapshot max velocity: `|velocity|_max = 9.3397850977e-01`

## Modal Check

- Snapshots: `98`, from `t=5.5820240448e-03` to `t=4.8527137019`
- Signed `m=2` coefficient: `1.0019054776e-02 -> 2.4172757568e-02`
- Signed `m=2` range: min `1.0019054776e-02`, max `2.7580730013e-02`
- Zero crossings: `0`
- High-mode / `m=2` spectral ratio: `1.7619619158e-03 -> 2.0000824303e+00`

## Interpretation

- Execution verdict: run performed after latest `main` merge, but `T=10` was not reached.
- Physical/numerical verdict: not a successful capillary-wave benchmark. The interface remains same-sign in the signed `m=2` mode, does not show the expected quarter-period sign reversal near `t≈4.16`, and high-mode content grows until the run fails.
- Conservation remains moderate before failure (`|ΔV|/V0 <= 5.2e-05`), so the immediate failure is not bulk volume loss; it is dominated by kinetic-energy growth, divergence growth, curvature-cap saturation, and large PPE/BF residuals.
- Main-route affine closure is active throughout; therefore this failure is downstream of the affine closure being selected, not a reversion to legacy jump decomposition.

[SOLID-X] Experiment execution + artifact only; no production class/module boundary change.
