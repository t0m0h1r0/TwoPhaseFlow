# CHK-RA-OSC-N64-005 — N64 static droplet alpha-2 control

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

Change the static-droplet control from alpha=4 to alpha=2 and rerun the
experiment.

## Setup

Added `experiment/ch14/config/ch14_static_droplet_n64_alpha2_like_oscillating.yaml`.
It preserves the alpha-4 static control except for the fitted-grid monitor
strength:

- `cells=[64,64]`
- periodic domain `[1,1]^2`
- dynamic fitted grid with `schedule=1`
- interface monitor changed from `alpha=4` to `alpha=2`
- local interface thickness, pressure-jump surface tension
- water-air properties with `sigma=0.072`
- same IMEX-BDF2 convection, implicit-BDF2 viscous DC, FCCD PPE DC route
- same capillary CFL `cfl=0.2`, target `T=1.5`
- static circle `R=0.25`

## Validation

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_static_droplet_n64_alpha2_like_oscillating"
```

Result:

- runtime: `20m39.971s`
- initial fitted-grid minimum spacing: `h_min=1.2368e-02`
- first capillary step: `dt_cap=6.471e-04`
- completed target `T=1.5`
- stored time samples: `2320`
- final/max `kinetic_energy=1.686512978443789e-02`
- final/max `volume_conservation=8.741532383041076e-04`
- deformation `0.0 -> 0.0`
- max absolute deformation `3.96579064514723e-03`
- snapshots saved through `t=1.500`

## Interpretation

Alpha=2 converts the same N64 static-droplet route from FAIL to PASS for the
tested horizon. The alpha-4 static control failed at `t=1.1190` with kinetic
energy growing to `4.707e+06`; the alpha-2 control reaches `T=1.5` with kinetic
energy only `1.69e-02`.

This supports the physical/mathematical hypothesis that the late blowup is not
a static droplet equilibrium impossibility. It is strongly coupled to the
alpha-4 fitted-grid geometry: stronger monitor concentration lowers the local
spacing, tightens the capillary pressure-jump resolution budget, and amplifies
spurious capillary/pressure imbalance until advective CFL collapse. Weakening
to alpha=2 increases `h_min` (`1.0739e-02 -> 1.2368e-02`) and keeps the route
capillary-limited for most of the run, preventing the runaway observed in
CHK-RA-OSC-N64-004.

[SOLID-X] Config/run/artifact only; no solver/operator/builder boundary was
changed, and no tested implementation was deleted.
