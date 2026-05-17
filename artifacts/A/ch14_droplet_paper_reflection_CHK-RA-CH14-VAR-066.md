# CHK-RA-CH14-VAR-066 — Droplet YAML Route Paper Reflection

Date: 2026-05-18

## Claim

The canonical reduced PhaseRegion closed-chart oscillating-droplet one-period
route from `experiment/ch14/config/ch14_oscillating_droplet.yaml` is now
reflected in the paper.  The paper-facing evidence is the YAML-owned output,
not ad hoc figures or stale short-step diagnostics.

## Paper Changes

- Rewrote `paper/sections/14b_oscillating_droplet.tex` around the
  PhaseRegion-primary route:
  `X(theta; A) -> q_l=Q_h(X)`, `q_g=|C|-q_l`,
  and `E_h[X]=sigma Per(X)`.
- Recorded the one-period Rayleigh--Lamb exact comparison:
  `steps=3977`, `dt=2.651764221323e-05`,
  `t_final/T_RL=9.999999999903e-01`,
  `max_amplitude_error=2.503547743871e-10`,
  `max_velocity_error=2.046056174314e-08`,
  `max_energy_drift=6.240056085825e-07`,
  `max_residual_l2=0`,
  `max_volume_drift=1.084202172486e-19`,
  `max_q_volume_closure_raw_abs=1.822318492916e-07`,
  `max_q_volume_closure_closed_abs=2.710505431214e-20`,
  and `force_admissible=0`.
- Added YAML-output figures under `paper/figures/ch14_droplet_yaml/` plus
  `paper/figures/ch14_phase_region_oscillating_droplet_yaml_snapshots.pdf`.
- Updated `paper/sections/14e_benchmark_summary.tex` and
  `paper/sections/14_benchmarks.tex` so the Chapter 14 benchmark summary cites
  the one-period closed-chart YAML result rather than short-step evidence.
- Updated `docs/wiki/paper/WIKI-P-019.md` to make the paper contract explicit:
  raw P1 closed-radial gauge volume and owned PhaseRegion volume are distinct,
  and the total-volume-closed measurement is a state-ownership correction.

## Theory Boundary

This paper update keeps the reduced-route boundary visible.  The closed-chart
one-period run validates the PhaseRegion measure/energy/chart path against the
linear Rayleigh--Lamb oracle, but it does not admit a production
pressure/velocity force consumer.  Therefore `force_admissible=0` remains part
of the pass condition, and V12 remains the production negative control.

## Validation

- `git diff --check`: PASS.
- Targeted stale-claim scan for `short-step`, `few-step`, `短時間`, and related
  old droplet-route phrases in the touched paper/wiki files: PASS.
- Targeted LaTeX scan for math in section/caption titles in the touched Chapter
  14 files: PASS.
- `make -B -C paper`: PASS (`paper/main.pdf`, 287 pages).
- Targeted `paper/main.log` scan: no fatal errors, undefined control sequences,
  undefined references, LaTeX warnings, or overfull boxes.

[SOLID-X] Paper/wiki/artifact/figure reflection only.  No solver source,
experiment YAML, result data, physical parameter, CFL policy, smoothing,
damping, tolerance weakening, rebuild skipping, FD/WENO/PPE fallback, hidden CPU
fallback, production force consumer, main merge, origin push, branch deletion,
or worktree removal was changed.
