# CHK-RA-OSC-N64-020 — N64 oscillating droplet one-period config

## Question

Set the alpha-2 oscillating-droplet run length to one Rayleigh--Lamb period
rather than the short `T=1.5` smoke horizon.

## Period

The current analytical reference in the alpha-2 oscillating-droplet config is
`omega0 = 0.167435`, so

`T_period = 2*pi / omega0 = 37.52611644626026`.

## Change

Added:

`experiment/ch14/config/ch14_oscillating_droplet_n64_alpha2_one_period.yaml`

The config preserves the CHK-019 alpha-2 geometry/physics/numerics stack and
changes:

- `run.time.final: 37.52611644626026`
- output directory:
  `results/ch14_oscillating_droplet_n64_alpha2_one_period`
- snapshot interval: `1.0` to avoid hundreds of snapshot PDFs over one period

The short `T=1.5` smoke config is retained.

## Execution attempt

Remote was reachable and `make cycle` started:

`make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet_n64_alpha2_one_period'`

The run was stopped after `119m54.839s` wall time because it had only reached
about `t=7.5` (roughly 20% of the requested period).  Extrapolating from the
observed progress, the full N64 one-period run is approximately a 10-hour
single-core remote job.  No completed `data.npz` was produced.

## Verdict

The one-period physical horizon is now encoded in YAML.  Completing the N64
one-period simulation should be scheduled as a long remote/background job, not
as an interactive foreground `make cycle` run.

[SOLID-X] config/artifact only; no production code changed and no tested
implementation deleted.
