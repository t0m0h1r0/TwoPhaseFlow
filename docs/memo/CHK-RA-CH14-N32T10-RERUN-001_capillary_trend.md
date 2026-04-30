# CHK-RA-CH14-N32T10-RERUN-001 — Capillary Wave N=32, T=10 Rerun

Date: 2026-04-30

## Setup

- Base YAML: `experiment/ch14/config/ch14_capillary.yaml`
- Run variant: temporary untracked copy `_tmp_ch14_capillary_n32_t10.yaml`
- Changes from base: `grid.cells=[32,32]`, `run.time.final=10.0`
- Command:
  `make cycle EXP=experiment/run.py ARGS="--config _tmp_ch14_capillary_n32_t10"`
- Result path:
  `experiment/ch14/results/_tmp_ch14_capillary_n32_t10/data.npz`
- Cleanup: temporary YAML removed locally and by `make push`; checked-in capillary YAML remains only `experiment/ch14/config/ch14_capillary.yaml`.

## Result Summary

- Completed to `t=10.0` with `1792` steps; no BLOWUP / NaN stop.
- `kinetic_energy`: `1.3827e-09 -> 2.6867e-03`, max `2.6903e-03` at `t=9.9695`.
- `interface_amplitude`: `1.1970e-02 -> 7.8471e-02`, max `7.9242e-02` at `t=9.4894`.
- `volume_conservation`: final `6.3666e-04`, max absolute `6.7475e-04`.
- `div_u_max`: final `2.6695e-04`, max `4.8288e-02` at `t=0.1116`.
- `ppe_rhs_max`: final `1.3670e+00`, max `1.3071e+01`.
- `bf_residual_max`: final `1.6656e+01`, max `3.1796e+01`.
- `kappa_max`: cap `5.0` hit on `1536/1792` steps.
- PPE route: `affine_jump=1`, legacy jump decomposition `0`, `ppe_phase_count=1`, `ppe_pin_count=1`, `ppe_mean_gauge=0`.
- Time-step limiter: capillary limiter for all `1792` steps.

## Expected Trend Check

The expected short-time Young--Laplace restoring trend is present.
Signed `m=2` interface-mode fits from saved `psi` snapshots give:

| Fit window | observed `A''` | theory `A''=-1.4271e-03` | ratio |
|---|---:|---:|---:|
| first 6 snapshots (`t<=0.251`) | `-1.4396e-03` | `-1.4271e-03` | `1.009` |
| first 8 snapshots (`t<=0.352`) | `-1.4098e-03` | `-1.4271e-03` | `0.988` |
| first 10 snapshots (`t<=0.452`) | `-1.3160e-03` | `-1.4271e-03` | `0.922` |

This confirms the desired sign: the initial capillary acceleration is restoring, not anti-restoring.

## Interpretation

The rerun reproduces the desired qualitative trend:

1. The run reaches `T=10` without blow-up.
2. The affine pressure-jump route is active for the full run.
3. The initial signed-mode acceleration has the Young--Laplace restoring sign and near-theory magnitude.

Remaining issue:

- The run is not yet a clean physical capillary-wave benchmark over the whole interval.
  The interface amplitude grows substantially, kinetic energy grows to `O(10^-3)`,
  and curvature cap saturation is persistent after early time.
  This points to the already known geometry/curvature/long-time energy-stability bottleneck,
  not the old wrong-sign affine jump failure.

[SOLID-X] experiment execution and memo only; no production code change.
