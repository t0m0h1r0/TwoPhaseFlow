# CHK-RA-OSC-N64-003 — Static-size N64 oscillating droplet

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Change

The N64 oscillating-droplet config was resized to match the static-droplet
benchmark scale.

- static droplet reference: `radius: 0.25`
- new oscillating semi-axes: `a=0.275`, `b=0.225`
- area-equivalent radius: `sqrt(ab)=0.24875`
- signed-deformation amplitude remains `D0=0.10`
- surface tension restored to the static-droplet water-air value `sigma=0.072`
- analytical reference updated to `omega0=0.167435`

The high-sigma period-one setting was not retained because scaling `R≈0.05` to
`R≈0.25` while keeping period one would require an artificial `sigma` increase
by about `5^3`, making the capillary pressure jump and timestep stiffness a
different benchmark.

## Validation

Command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet_n64"
```

Result:

- runtime: `17m41.296s`
- initial fitted-grid minimum spacing: `h_min=1.0153e-02`
- first capillary step: `dt_cap=4.813e-04`
- reached `step=1966`, `t=0.9495075425292716`
- BLOWUP before target `T=1.5`
- final/max `kinetic_energy=2.7309118136203587e+06`
- final/max `volume_conservation=5.697907042808521e-04`
- signed deformation `0.09232575 -> 0.09080559`
- field snapshots saved through `t=0.9002583791129763`

## Interpretation

The static-size change removes the immediate small-droplet failure mode:
the previous small ellipse failed at `t=0.01753`, while the resized case runs to
`t=0.94951`. This strongly supports the prior diagnosis that the original
ellipse was outside the geometry/capillary resolution contract.

The resized case still does not complete `T=1.5`, so droplet size alone is not
the entire stability contract. The remaining failure is a later-time nonlinear
growth problem under alpha-4 every-step fitted-grid pressure-jump dynamics.
The theory-consistent next levers remain those already isolated by
CHK-RA-OSC-N64-002: weaker alpha, stricter capillary timestep, smaller
perturbation amplitude, or a higher-resolution run. These are not interchangeable
patches; they correspond to the geometry/capillary resolution budget.

[SOLID-X] Config/run/artifact only; no solver/operator/builder boundary was
changed, and no tested implementation was deleted.
