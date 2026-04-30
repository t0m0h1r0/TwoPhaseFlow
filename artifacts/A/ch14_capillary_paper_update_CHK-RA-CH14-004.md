# CHK-RA-CH14-004 — ch14 capillary paper update

- Worktree: `ra-ch14-capillary-wave-retry-20260429`
- Source result: `experiment/ch14/results/ch14_capillary/data.npz`
- Paper section: `paper/sections/14_benchmarks.tex`

## Data Used

- Final time: `T = 35.0`
- Recorded steps: `19525`
- Time step: `dt = 1.792640597e-03`
- Inviscid reference: `omega = 0.377764048`, `T_omega = 16.632565583`
- Signed `m=2` coefficient: `1.0003e-02 -> 1.0465e-02`, zero crossings `0`
- Unsigned `interface_amplitude`: initial `1.0510e-02`, final `2.3152e-02`, max `2.3504e-02`
- `volume_conservation`: final `1.0925e-05`, max absolute `1.2171e-05`
- `kinetic_energy`: max `8.0648e-09`
- Snapshot `||u||_inf`: max `1.0618e-04`
- `div_u_max`: max `1.6045e-05`
- `kappa_max`: reached cap `5.0` in `17575 / 19525` steps (`90.0%`)

## Paper Changes

- Rewrote the capillary subsection as a result-first analysis rather than a placeholder.
- Separated the verdict into conservation/boundedness pass and Prosperetti-period response failure.
- Added `paper/figures/ch14_capillary_result_dashboard.pdf`.
- Added `paper/figures/ch14_capillary_velocity_snapshots.pdf`.
- Updated `tab:ch14_summary` and the §14 summary bullets.

## Validation

- `cd paper && latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` passed.
- `git diff --check` passed.
- Final `main.log` diagnostic grep had no hits for LaTeX warnings, hbox warnings, undefined control sequences, emergency stops, or fatal errors.

[SOLID-X] Paper and figure update only; no `src/twophase/` or production module boundary change.
