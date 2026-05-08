# CHK-RA-CH14-CAPILLARY-ONE-PERIOD-001

## Scope

User request: make the capillary-wave YAML official for the N=32 one-period
case, run the experiment, and update the paper with the same style of figures
used for the oscillating droplet.

## Configuration

Updated:

```text
experiment/ch14/config/ch14_capillary.yaml
```

Key settings:

```text
N = 32
boundary = {x: periodic, y: wall}
surface tension = pressure_jump
open-interface capillary force = curvature_jump
capillary_range_projection = component_hodge_augmented
pressure_force_contract = variational_adjoint
scalar_operator_pairing = variational_operator
initial interface = y = 0.5 + 0.01 cos(4πx)
```

The one-period time is set from the inviscid two-fluid capillary-wave
dispersion relation

```text
omega = sqrt(sigma k^3 / (rho_l + rho_g)),  k = 4π
omega = 0.377764048
T_sigma = 2π / omega = 16.632565583
```

Snapshots are requested at

```text
0, 1/4 T_sigma, 1/2 T_sigma, 3/4 T_sigma, T_sigma
```

with the same paper-facing velocity style as the oscillating droplet:
no scalar velocity background, larger colored arrows, shared speed scale, and
shared pressure scale.

## Experiment

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle \
  EXP=experiment/run.py ARGS='--config ch14_capillary'
```

Result:

```text
outdir = experiment/ch14/results/ch14_capillary
steps = 2145
t_final = 16.632565583
wall time = 16m03.824s
```

Diagnostics:

```text
interface_amplitude:
  first = 1.0469117056005617e-02
  min   = 8.793442029167431e-04
  max   = 1.1799880199031054e-02
  last  = 1.0288063183115093e-02

kinetic_energy:
  first = 1.7439312489722177e-09
  max   = 3.197241280953186e-04
  last  = 8.956696840330145e-05

volume_conservation:
  max   = 8.97275084780464e-15
  last  = 8.13807635033444e-15

snapshot speed:
  max over snapshots = 3.85594317896855e-03
  final Linf         = 2.7105809199611287e-03

final boundary checks:
  v(y=0) Linf              = 0
  v(y=1) Linf              = 0
  x-periodic u mismatch    = 0
  x-periodic v mismatch    = 0
```

## Paper Update

Updated:

```text
paper/sections/14_benchmarks.tex
```

Figures refreshed or added under `paper/figures/`:

```text
ch14_capillary_interface_amplitude.pdf
ch14_capillary_kinetic_energy.pdf
ch14_capillary_volume_drift.pdf
ch14_capillary_psi_t0.pdf
ch14_capillary_psi_tq1.pdf
ch14_capillary_psi_tq2.pdf
ch14_capillary_psi_tq3.pdf
ch14_capillary_psi_t1.pdf
ch14_capillary_velocity_t0.pdf
ch14_capillary_velocity_tq1.pdf
ch14_capillary_velocity_tq2.pdf
ch14_capillary_velocity_tq3.pdf
ch14_capillary_velocity_t1.pdf
ch14_capillary_pressure_t0.pdf
ch14_capillary_pressure_tq1.pdf
ch14_capillary_pressure_tq2.pdf
ch14_capillary_pressure_tq3.pdf
ch14_capillary_pressure_t1.pdf
```

The capillary-wave section now states the dispersion-derived one-period time,
the N=32 grid, the one-period diagnostics, and includes history, psi snapshot,
velocity snapshot, and pressure snapshot figures.

## Validation

```text
git diff --check
PASS

SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_config_io_fccd.py::test_ch14_capillary_yaml_loads_execution_stack twophase/tests/test_ns_pipeline_fccd.py::test_ch14_capillary_wave_yaml_builds_initial_field -q'
633 passed, 33 skipped in 41.94s

make -B -C paper
PASS, paper/main.pdf rebuilt (254 pages)
```

[SOLID-X] Configuration, experiment, paper text, and paper figures only.  No
solver implementation was changed, no tested code was deleted, and no FD/WENO/PPE
fallback, damping/CFL workaround, smoothing, curvature cap, benchmark-name branch,
blanket projection, or QP-as-physics route was introduced.
