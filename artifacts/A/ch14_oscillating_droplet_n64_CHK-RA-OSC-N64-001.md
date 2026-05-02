# CHK-RA-OSC-N64-001 — ch14 oscillating droplet N=64 run

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`
Worktree: `.claude/worktrees/ra-oscillating-droplet-n64-20260503`

## Scope

Run the existing Rayleigh-Lamb `n=2` oscillating droplet route at `N=64`
without changing the production `ch14_oscillating_droplet.yaml`.

Config:

- `experiment/ch14/config/ch14_oscillating_droplet_n64.yaml`
- `grid.cells: [64, 64]`
- `grid.distribution.schedule: 1`
- `alpha: 4.0` on both fitted axes
- `run.time.final: 1.5`
- `viscosity.time_integrator: implicit_bdf2`
- `viscosity.solver.kind: defect_correction`
- `projection.poisson.solver.kind: defect_correction`

## Command

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet_n64"
```

Remote-first cycle completed push, run, and pull.

## Result

The run did not reach `T=1.5`. It tripped the runner BLOWUP guard:

- runtime: `2m23.583s`
- initial fitted-grid minimum spacing: `h_min=5.9351e-03`
- limiter: capillary
- first-step capillary time step: `dt_cap=6.409e-05`
- BLOWUP: `step=275`, `t=0.0175309134281993`
- samples saved: `275`
- field snapshots saved: `1`
- `max(kinetic_energy)=5.4783028622477e+08`
- final `kinetic_energy=5.4783028622477e+08`
- final `volume_conservation=1.180102300864e-06`
- max `volume_conservation=1.214267243164e-06`
- `signed_deformation: 0.04433361 -> 0.04425019`

Pulled local artifacts are under:

- `experiment/ch14/results/ch14_oscillating_droplet_n64/data.npz`
- `experiment/ch14/results/ch14_oscillating_droplet_n64/*.pdf`

These result files are intentionally ignored by git.

## Interpretation

Verdict: numerical FAIL for the `N=64`, period-one, alpha-4, every-step
fitted-grid DC route.

The early failure is kinetic-energy dominated. Volume drift remains around
`1.2e-06` up to the blowup point, so this run does not point to volume loss as
the immediate trigger. The trajectory is too short to evaluate the intended
Rayleigh-Lamb period-scale oscillation.

[SOLID-X] No SOLID violation found. This checkpoint adds a reproducible YAML
variant and records run evidence only; no solver, operator, or builder boundary
was changed, and no tested implementation was deleted.
