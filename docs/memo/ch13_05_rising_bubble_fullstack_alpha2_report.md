# CHK-170: ch13_05 rising bubble fullstack alpha=2 report

Date: 2026-04-21
Branch: `worktree-rising-bubble`
Execution: remote GPU via `./remote.sh run`

## Setup

Primary config:
`experiment/ch13/config/ch13_05_rising_bubble_fullstack_alpha2.yaml`

Base numerical stack follows `ch13_04_capwave_fullstack_alpha2.yaml`:

- `alpha_grid: 2.0`
- `reinit_method: ridge_eikonal`
- `advection_scheme: fccd_flux`
- `convection_scheme: fccd_flux`
- `reproject_mode: consistent_gfm`
- `phi_primary_transport: true`

Rising-bubble deltas:

- vertical water/air domain: `NX=64`, `NY=128`, `LX=1`, `LY=2`
- gas bubble: `center=[0.5, 0.5]`, `radius=0.25`
- buoyancy: `g_acc=0.001`
- diagnostics: `bubble_centroid`, `kinetic_energy`, `volume_conservation`

## Remote GPU results

Primary run:

- command: `./remote.sh run experiment/ch13/run.py ch13_05_rising_bubble_fullstack_alpha2`
- output: `experiment/ch13/results/ch13_05_rising_bubble_fullstack_alpha2/data.npz`
- result: BLOWUP at step 27, `t=0.007014074555814029`
- final `kinetic_energy`: `1.823380739e6`
- final `volume_conservation`: `2.406866802e-16`
- final `yc`: `0.4981017003`
- final `vc`: `-634.2226633`

Debug run:

- command: `./remote.sh run experiment/ch13/run.py ch13_05_rising_bubble_fullstack_alpha2_debug`
- output: `experiment/ch13/results/ch13_05_rising_bubble_fullstack_alpha2_debug/data.npz`
- result: BLOWUP at step 27, `t=0.007014074555801253`
- first `bf_residual_max`: `4.404543834e2`
- max `bf_residual_max`: `1.519214695e12`
- max `ppe_rhs_max`: `3.871689484e11`
- max `div_u_max`: `1.595834349e5`
- max `kappa_max`: `8.365443994e3`

Comparison run:

- command: `./remote.sh run experiment/ch13/run.py ch13_02_waterair_bubble`
- output: `experiment/ch13/results/ch13_02_waterair_bubble/data.npz`
- result: BLOWUP at step 2083, `t=1.277237017526077`
- final `kinetic_energy`: `1.011701489e6`
- final `volume_conservation`: `4.813733605e-16`
- final `yc`: `0.5042208004`
- final `vc`: `0.1071108645`

## Interpretation

The fullstack alpha=2 rising-bubble case conserves volume to roundoff but
fails immediately through the momentum/pressure path. The debug run shows
`bf_residual_max` growing from `4.4e2` at step 1 to `1.5e12` by the BLOWUP
step, while `ppe_rhs_max` and `div_u_max` grow in lockstep. This matches the
known H-01 balanced-force residual failure mode more than a CLS mass-loss
failure.

## Next gate

Before using the fullstack alpha=2 rising-bubble case as a production
benchmark, run a two-case control:

- `sigma=0` with all other fullstack settings fixed, to confirm surface-tension
  coupling as the trigger.
- `sigma=1` with a balanced-force/FCCD corrective path, to test whether the
  residual is removed without relaxing the target physics.
