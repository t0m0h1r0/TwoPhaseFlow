# CHK-RA-OSC-N64-004 — N64 static droplet control on oscillating route

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

Check whether a static droplet works under settings analogous to the resized
N64 oscillating-droplet experiment.

## Setup

Added `experiment/ch14/config/ch14_static_droplet_n64_like_oscillating.yaml`.
This is a direct control of `ch14_oscillating_droplet_n64.yaml`:

- `cells=[64,64]`
- periodic domain `[1,1]^2`
- dynamic fitted grid with `schedule=1`
- interface monitor `alpha=4`
- local interface thickness, pressure-jump surface tension
- water-air density and viscosity, `sigma=0.072`
- same IMEX-BDF2 convection, implicit-BDF2 viscous DC, FCCD PPE DC route
- same capillary CFL `cfl=0.2`, target `T=1.5`
- only the initial interface changes from ellipse `a=0.275,b=0.225` to circle
  `R=0.25`

## Validation

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_static_droplet_n64_like_oscillating"
```

Result:

- runtime: `19m44.155s`
- initial fitted-grid minimum spacing: `h_min=1.0739e-02`
- first capillary step: `dt_cap=5.236e-04`
- reached `step=2228`, `t=1.1190034721244824`
- BLOWUP before target `T=1.5`
- final/max `kinetic_energy=4.707075794508522e+06`
- final `volume_conservation=9.830958243295781e-04`
- max `volume_conservation=9.831277368260802e-04`
- deformation `0.0 -> 0.0`, max absolute deformation `3.575862641406817e-03`
- snapshots saved through about `t=1.100`

## Interpretation

The static circle does not complete under the alpha-4 N64 oscillating-route
settings. It runs longer than the resized oscillating ellipse
(`t=1.1190` vs `t=0.9495`), so the Rayleigh-Lamb elliptic perturbation is a
destabilizing accelerator. It is not the sole cause.

The late failure appears after a long phase of growing spurious kinetic energy:
the limiter changes from capillary-limited to advective-limited around
`t≈0.84`, then the advective timestep collapses before BLOWUP. Since the
interface remains nearly circular and the volume error stays below `1e-3`, the
evidence points to accumulated capillary/pressure-jump imbalance on the
alpha-4 fitted-grid route rather than gross volume loss or large physical
deformation.

Thus, under "same numerical route" conditions, static-droplet equilibrium is
not yet a successful control. The theory-consistent diagnosis from
CHK-RA-OSC-N64-002 remains active: the geometry/capillary resolution budget of
alpha-4 N64 pressure-jump dynamics is too tight. The ellipse excites the same
instability earlier, but the static circle can still enter it later.

[SOLID-X] Config/run/artifact only; no solver/operator/builder boundary was
changed, and no tested implementation was deleted.
