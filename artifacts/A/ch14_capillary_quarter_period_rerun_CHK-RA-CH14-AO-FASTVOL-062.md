# CHK-RA-CH14-AO-FASTVOL-062 - Ch14 capillary quarter-period rerun

## Question

User asked to rerun the Chapter 14 capillary-wave experiment for one quarter
period and regenerate the visualization.

## Configuration

- Config: `experiment/ch14/config/ch14_capillary.yaml`
- Final time: `0.008899695230 s`
- Physical window: first quarter cycle, upper crest to flat state
- Backend route: production ch14 active-geometry capillary decomposition with
  FCCD PPE, bundle Young--Laplace work, q geometric swept-volume transport, and
  UCCD6 momentum convection.
- Output directory: `experiment/ch14/results/ch14_capillary`

## Command

```text
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary --no-checkpoint-final"
```

The command pushed the worktree to the remote GPU host, ran the experiment, and
pulled the results back.

## Result

- Runtime: `real 3m21.423s`
- Steps: `483`
- Final time: `0.008899695230`
- Limiter: capillary CFL throughout the reported checkpoints
- Final volume drift: `0.0`
- Max volume drift: `2.7104946448049923e-16`
- Final kinetic energy: `1.637680684010133e-12`
- Signed interface amplitude:
  - first sample: `2.002862460105133e-04`
  - final sample: `2.0031783487681207e-04`
  - min/max: `2.002862460105133e-04` / `2.0031783487681207e-04`

## Visualization

Regenerated current-quarter outputs:

- `signed_interface_amplitude.pdf`
- `volume_drift.pdf`
- `kinetic_energy.pdf`
- `psi_t0.000.pdf`, `psi_t0.002.pdf`, `psi_t0.004.pdf`, `psi_t0.007.pdf`, `psi_t0.009.pdf`
- `velocity_t0.000.pdf`, `velocity_t0.002.pdf`, `velocity_t0.004.pdf`, `velocity_t0.007.pdf`, `velocity_t0.009.pdf`
- `pressure_t0.000.pdf`, `pressure_t0.002.pdf`, `pressure_t0.004.pdf`, `pressure_t0.007.pdf`, `pressure_t0.009.pdf`

Stale generated PDFs from an older longer run (`t0.018`, `t0.027`, `t0.035`)
were removed from the ignored local result directory so the folder now exposes
only this quarter-period visualization set.

## SOLID/A3

- [SOLID-X] Experiment execution, ignored result files, and bookkeeping only;
  no solver source, YAML, physical parameter, CFL, damping, smoothing,
  tolerance, iteration limit, nonuniform-grid contract, interface-tracking
  rebuild contract, hidden fallback, main merge, or branch deletion changed.
