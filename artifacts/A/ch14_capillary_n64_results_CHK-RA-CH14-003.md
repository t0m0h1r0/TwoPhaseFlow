# CHK-RA-CH14-003 — ch14 capillary-wave N64 result

- Worktree: `ra-ch14-capillary-wave-retry-20260429`
- Config: `experiment/ch14/config/ch14_capillary.yaml`
- Change: capillary-wave grid halved from `128 x 128` to `64 x 64`
- Execution: remote detached run, `TWOPHASE_USE_GPU=1`, `python3 experiment/run.py --config ch14_capillary`
- Result directory: `experiment/ch14/results/ch14_capillary/` (gitignored)

## Run Summary

- Final time: `T = 35.0`
- Steps: `19524`
- Time step: `dt_capillary = 1.792640597e-03` throughout; limiter was capillary
- Theoretical inviscid capillary-wave period:
  - `k = 4 pi`
  - `omega = 0.377764048`
  - `2 pi / omega = 16.632565583`

## Diagnostics

- `interface_amplitude`: initial `1.051024891e-02`, final `2.315156254e-02`, max `2.350395332e-02`
- Signed `m=2` interface coefficient from snapshots:
  - initial `1.000309017e-02`
  - final `1.046636717e-02`
  - no zero crossing over `0 <= t <= 35`
- `volume_conservation`: final `1.092484115e-05`, max absolute `1.217103069e-05`
- `kinetic_energy`: max/final `8.064808510e-09`
- `div_u_max`: max `1.604517663e-05`, final `8.631750669e-06`
- `kappa_max`: reached cap `5.0`

## Verdict

- Conservation: pass for the paper's `O(1e-4)` long-run volume criterion.
- Period response: not demonstrated; the signed mode did not cross zero despite `T=35` covering about `2.10` inviscid periods.
- Paper handling: record as a completed N64 run with conservation pass and period-response failure, not as a capillary-wave benchmark success.

[SOLID-X] Experiment YAML + paper/artifact update only; no production class/module boundary change.
