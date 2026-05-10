# CHK-RA-CH14-REALPARAM-004 — ch14 capillary/droplet paper refresh

## Scope

User requests covered:

- Recompute the ch14 capillary-wave period theoretically.
- Use `interface.reinitialization.schedule.every_steps: 1`.
- Rerun the ch14 capillary-wave and oscillating-droplet YAMLs on the remote GPU.
- Refresh chapter 14 paper text and figures from the reruns.
- For the capillary-wave 2-D paper snapshots, publish five points spanning one
  signed computed cycle: start, upper-to-flat, lower extremum, lower-to-flat,
  and return to the upper extremum.

Main was not merged.

## Capillary Wave

YAML geometry:

- `L_x = L_y = 0.02 m`
- `mode = 2`
- `lambda = L_x / mode = 0.01 m`
- `A_0 = 0.0002 m`
- water-air at about 20 C, `sigma = 0.0728 N/m`

Finite-depth two-layer inviscid reference:

```text
k = 2 pi mode / L_x = 628.318530718 1/m
h_l = h_g = 0.01 m
omega^2 = sigma k^3 / (rho_l coth(k h_l) + rho_g coth(k h_g))
omega = 134.419859151 1/s
T_ref = 2 pi / omega = 0.046742983863 s
```

The nonnegative `interface_amplitude` folds the sign and must not be used to
count periods.  The paper-facing snapshots use the signed mode-2 diagnostic
`signed_interface_amplitude`:

```text
0.000000000000 s  start, upper extremum
0.008899695230 s  first signed-amplitude zero crossing
0.017677817828 s  lower signed-amplitude extremum
0.026630729902 s  second signed-amplitude zero crossing
0.035379718894 s  return to upper extremum
```

Remote GPU command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config ch14_capillary"
```

Result:

- PASS, `real 14m45.569s`
- `1623` samples, final `t = 0.035379718894 s`
- signed amplitude: start `2.005765588083e-04`, minimum
  `-1.973360448569e-04` at `t = 0.017677817828 s`, final
  `1.919507916231e-04`
- kinetic energy: max `1.717755312868e-05`, final `9.209986571943e-06`
- sharp volume drift: max `5.504371304967e-04`, final
  `3.237634367317e-05`

Paper figures refreshed from `experiment/ch14/results/ch14_capillary/`,
including the new
`paper/figures/ch14_capillary_signed_interface_amplitude.pdf`.

## Oscillating Droplet

YAML geometry:

- `L_x = L_y = 0.02 m`
- ellipse center `(0.01, 0.01) m`
- semi-axes `a = 0.0055 m`, `b = 0.0045 m`
- `R_eq = sqrt(ab) = 0.004974937 m`
- `D_0 = 0.10`

Rayleigh--Lamb reference:

```text
omega0 = sqrt(n(n^2-1)sigma / ((rho_l + rho_g) R_eq^3))
       = 59.578473371 1/s
T_RL = 2 pi / omega0 = 0.105460663082 s
```

The user-requested `every_steps: 1` is kept.  The dynamic droplet uses
`volume_constraint: diffuse_mass`; the sharper `sharp_phase_volume` constraint
failed closed at step 400 because it could not bracket a diffuse-mass profile
correction after preserving sharp area without moving the interface.

Remote GPU command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet"
```

Result:

- PASS, `real 39m39.157s`
- `3658` samples, final `t = 0.105460663082 s`
- signed deformation: start `7.617534118366e-02`, minimum
  `-3.515507407615e-02` at `t = 0.046716249913 s`, final
  `1.619266828946e-02`
- kinetic energy: max `4.027545431676e-05`, final `2.072510672326e-05`
- sharp volume drift: max `1.132813336313e-02`, final
  `1.121766765324e-02`

Paper figures refreshed from
`experiment/ch14/results/ch14_oscillating_droplet/`.

## Paper Updates

- `paper/sections/14_benchmarks.tex` now states the SI water-air geometry,
  material constants, theoretical reference periods, and rerun diagnostics.
- The capillary history figure now uses
  `ch14_capillary_signed_interface_amplitude.pdf`.
- The capillary 2-D figure captions describe the five signed-cycle paper
  snapshots rather than a longer interval.
- The oscillating-droplet text explicitly reports the dynamic
  `diffuse_mass` reinitialization route and the observed sharp volume drift.
- The summary table now reports SI-scale final times for the two target YAMLs.

## Validation

- Targeted config tests after the reinitialization constraint update:
  `2 passed, 74 deselected`.
- Remote GPU capillary run: PASS.
- Remote GPU oscillating-droplet run: PASS.
- `git diff --check`: PASS before paper build.
- Targeted paper build: `make -C paper` PASS, producing
  `paper/main.pdf` with 263 pages.
- Fatal/error/undefined scan of `paper/main.log`: PASS.
- Overfull/underfull hbox scan of `paper/main.log`: PASS.

## SOLID

[SOLID-D] Added a signed capillary diagnostic and changed YAML/paper/reporting
around physical parameters and diagnostics.  No solver numerical operator,
pressure/PPE route, damping/CFL workaround, smoothing, curvature cap, benchmark
branch, blanket projection, QP-as-physics path, hidden DCCD/UCCD damper, or
tested implementation deletion was introduced.
