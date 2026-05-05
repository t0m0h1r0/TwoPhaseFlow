# CHK-RA-OSC-N64-019 — N64 alpha-2 oscillating droplet after pressure-history fix

## Question

After the static-droplet affine pressure-history face fix, does the analogous
N64 oscillating-droplet route complete under the same alpha-2 fitted-grid
conditions?

## Setup

Added `experiment/ch14/config/ch14_oscillating_droplet_n64_alpha2_like_static.yaml`.
It follows the static alpha-2 control stack and replaces the circular
interface with the static-size ellipse:

- grid `64 x 64`, periodic
- fitted-grid rebuild every step
- interface monitor `alpha=2.0`
- local interface thickness, `psi_direct_filtered` curvature
- pressure-jump surface tension, phase-separated affine FCCD PPE + DC
- projection-native face state, face-native predictor state, and affine
  pressure-history face contract from CHK-018
- ellipse semi-axes `[0.275, 0.225]`, area-equivalent radius `0.24875`
- final time `T=1.5`, capillary CFL `0.2`

## Run

Command:

`make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet_n64_alpha2_like_static'`

Remote was unavailable from the sandboxed path, so the documented local CPU
fallback ran.  The route completed to `T=1.5`.

## Metrics

| metric | value |
|---|---:|
| steps | `2430` |
| final time | `1.500000` |
| KE initial | `1.457659e-11` |
| KE final/max | `2.583703e-04` |
| `KE >= 1e-3` | never |
| `KE >= 1e-2` | never |
| volume drift final/max | `7.224864e-05` |
| deformation initial/final | `6.856642e-02` / `6.885189e-02` |
| signed deformation initial/final | `9.226674e-02` / `8.791287e-02` |
| final speed `L_inf` | `6.199446e-03` |
| pressure contrast initial/final | `3.807939e-01` / `5.871051e-01` |

## Figures

Generated summary figure:

`experiment/ch14/results/ch14_oscillating_droplet_n64_alpha2_like_static/oscillating_droplet_summary_CHK019.pdf`

The runner also produced `signed_deformation.pdf`, `kinetic_energy.pdf`,
`volume_drift.pdf`, and snapshot PDFs in the same result directory.

## Verdict

PASS for the `T=1.5` N64 alpha-2 oscillating-droplet smoke/benchmark route.
The previous alpha-4 static-size oscillating route blew up around `t=0.9495`;
with the static-proven alpha-2 fitted-grid strength and the CHK-018 affine
pressure-history face contract, the corresponding oscillating route completes
without crossing the `KE >= 1e-3` threshold.

[SOLID-X] no production code changed.  This unit adds one config and records
the run; no damping/CFL/smoothing/curvature-cap workaround was introduced.
