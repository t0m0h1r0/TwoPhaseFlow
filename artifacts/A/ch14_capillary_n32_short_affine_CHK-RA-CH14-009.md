# CHK-RA-CH14-009 — ch14 capillary-wave N32 short affine smoke

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch: `ra-ch14-capillary-rootcause-20260430`
- User request: `N=32` で短時間の毛管波実験を行い，正しく動作するか検証する。
- Temporary config: `experiment/ch14/config/ch14_capillary_n32_short_affine.yaml` (not committed; `--all` collects every YAML)
- Result directory: `experiment/ch14/results/ch14_capillary_n32_short_affine/` (gitignored)

## Config

- Grid: `32 x 32`
- Final time: `0.05`
- Step cap: `max_steps = 10`
- Interface stress: `surface_tension.formulation = pressure_jump`, `projection.poisson.operator.interface_coupling = affine_jump`
- Stack: FCCD PPE + HFE curvature + UCCD6 convection

## Execution

- First attempt: `T=2.0` short probe was too expensive for an immediate smoke; it was stopped after about 10 minutes.
- Final command: `make cycle EXP=experiment/run.py ARGS="--config ch14_capillary_n32_short_affine"`
- Final run: completed successfully, `real 0m39.536s`
- Steps: `9`
- Final time: `t = 0.05`
- Time step: capillary-limited, `dt_cap = 5.5820240448e-03`; final clipped step reached `t = 0.05`

## Diagnostics

- `times`: `n=9`, first `5.5820240448e-03`, final `5.0000000000e-02`
- `interface_amplitude`: `1.1969774732e-02 -> 1.1971446322e-02`
- `kinetic_energy`: `1.3690167218e-09 -> 9.9068736496e-08`
- `volume_conservation`: final/max `7.7200660201e-08`
- `kappa_max`: `1.7067544383 -> 1.7099462654`
- `ppe_rhs_max`: `0 -> 3.9105031381`
- `bf_residual_max`: min/max `2.9946216716 / 3.0859121840`
- `div_u_max`: `2.6047675412e-03 -> 1.5547194921e-02`
- `ppe_interface_coupling_affine_jump`: all `1`
- `ppe_interface_coupling_jump`: all `0`
- Snapshot fields: all finite; `|u|_max = 6.9049262030e-05`, `|v|_max = 1.6275678529e-04`, `|velocity|_max = 1.6275678529e-04`

## Interpretation

- Smoke verdict: pass. The affine interface-stress path is active, the legacy jump-decomposition path is inactive, no NaN/blow-up occurred, snapshots and PDFs were generated, and capillary forcing produces nonzero velocity/kinetic energy instead of the earlier algebraic cancellation.
- Conservation at this short horizon is good: `|ΔV|/V0 <= 7.8e-08`.
- This is not a Prosperetti-period validation. Using the previous inviscid period `T_omega = 16.632565583`, this run covers only `0.05 / T_omega = 3.0e-03` periods.
- Follow-up risk: `div_u_max` grows to `1.55e-02` by `t=0.05`; acceptable for a smoke confirmation of motion, but not yet acceptable as a paper-grade incompressibility/period benchmark without a longer targeted validation and PPE/correction audit.

[SOLID-X] Experiment execution + artifact only; no production class/module boundary change.
