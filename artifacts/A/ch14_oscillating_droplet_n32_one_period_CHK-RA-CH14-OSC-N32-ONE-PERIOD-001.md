# CHK-RA-CH14-OSC-N32-ONE-PERIOD-001

## Scope

User request: run the Chapter 14 oscillating droplet for one Rayleigh--Lamb
period at N=32, update the YAML so the experiment is reproducible, and reflect
the result in the paper if the run finishes without blow-up.

## Reproducible Input

Checked-in YAML:

- `experiment/ch14/config/ch14_oscillating_droplet.yaml`

Key settings:

- Grid: `cells: [32, 32]`
- Final time: `37.526116446 = 2*pi/0.167435`
- Snapshots: `0`, `T/4`, `T/2`, `3T/4`, `T`
- Runner command:
  `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config ch14_oscillating_droplet'`

## Run Outcome

The run completed on the remote machine and pulled results back to:

- `experiment/ch14/results/ch14_oscillating_droplet/data.npz`
- `experiment/ch14/results/ch14_oscillating_droplet/signed_deformation.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/volume_drift.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/kinetic_energy.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/psi_t*.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/velocity_t*.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/pressure_t*.pdf`

Solver log summary:

- Steps: `3866`
- Final time: `37.526116446`
- Time-step range: `9.149424769e-03` to `9.962167266e-03`
- Limiter: capillary throughout the sampled progress log

Numerical checks from `data.npz`:

- All stored time histories and snapshot fields were finite.
- `signed_deformation`: `7.617534e-02 -> 5.017776e-02`
- Minimum `signed_deformation`: `-6.366763e-02`
- Signed-deformation sign changes: `2`
- `volume_conservation` final / max: `4.330808e-05` / `6.365672e-05`
- `kinetic_energy` start / final / max:
  `2.355046e-09` / `7.977569e-04` / `1.975622e-03`
- Snapshot velocity Linf: `8.813019e-03`
- Snapshot pressure representative min / max:
  `-1.477029` / `6.659652e-01`

## Interpretation

This is a successful one-period bounded-motion gate, not a fine-grid amplitude
convergence result.  At N=32 with nonuniform mesh rebuild and Ridge--Eikonal
reinitialization every step, the Rayleigh--Lamb curve is used as a phase and
restoring-direction reference.  The important checks for this gate are:

- the droplet does not freeze into the old zero-drive failure mode,
- the signed deformation crosses sign twice and returns to the positive side
  at one period,
- kinetic energy is generated and remains bounded,
- volume drift stays small, and
- pressure and velocity snapshot fields remain finite.

The amplitude damping/phase error should not be overinterpreted as a theorem of
the continuous Rayleigh--Lamb problem; it contains coarse-grid interface
representation, reinitialization work, and physical viscosity.

## Paper Figures

The paper version imports the run PDFs into `paper/figures/` under stable names:

- `ch14_osc_droplet_signed_deformation.pdf`
- `ch14_osc_droplet_kinetic_energy.pdf`
- `ch14_osc_droplet_volume_drift.pdf`
- `ch14_osc_droplet_psi_t0.pdf`
- `ch14_osc_droplet_psi_tq1.pdf`
- `ch14_osc_droplet_psi_tq2.pdf`
- `ch14_osc_droplet_psi_tq3.pdf`
- `ch14_osc_droplet_psi_t1.pdf`
- `ch14_osc_droplet_velocity_tq1.pdf`
- `ch14_osc_droplet_velocity_tq2.pdf`
- `ch14_osc_droplet_velocity_t1.pdf`
- `ch14_osc_droplet_pressure_tq1.pdf`
- `ch14_osc_droplet_pressure_tq2.pdf`
- `ch14_osc_droplet_pressure_t1.pdf`

`paper/sections/14_benchmarks.tex` now includes these as a time-history figure,
a five-time $\psi$ snapshot figure, and a velocity/pressure two-dimensional
field figure.  The snapshot-series regeneration uses shared numerical axes:
the $\psi$ color axis is fixed to `[0, 1]`, the velocity panels share one speed
color axis and one raw-arrow quiver scale, and the pressure-Hodge panels share
one symmetric pressure color axis.
