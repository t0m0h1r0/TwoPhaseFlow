# CHK-RA-CH14-VARIATIONAL-PRESSURE-IMPL-N32T1-001

## Scope

Implemented the variational pressure-reaction contract selected by the
finite-dimensional pressure-complex theory, then validated the N=32, T=1
static and oscillating droplet runs with field visualization.

## Implemented Contract

The production pressure face force now has an explicit contract:

```text
pressure_force_contract: variational_adjoint
scalar_operator_pairing: variational_operator
```

For the subtractive projection convention, the returned pressure reaction
faces satisfy the signed Green identity

```text
<G p, w>_M + <p, D w>_W = 0
```

on the same face divergence, coefficient, boundary quotient, and scalar
operator used by the projection. The scalar PPE path can therefore use
`L_var = D G_var` instead of reusing a divergence-equivalent compact-gradient
representative as a physical reaction.

The legacy compact pressure gradient remains available under the explicit
`raw_compact_gradient` contract. It is not silently substituted into the
variational production path.

## Validation

Code gates:

- `git diff --check`: PASS
- local `py_compile` over touched modules: PASS
- remote targeted FCCD pressure tests: `2 passed`
- remote full CPU/GPU suite via `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test`: `834 passed, 3 skipped`

N=32, T=1 experiments were run remote-first. The canonical YAML files were
temporarily changed only for `cells`, `run.time.final`, `print_every`, and
validation output naming, then restored and pushed back to the remote.

Static droplet:

- result data: `experiment/ch14/results/ch14_static_droplet/data.npz`
- final time: `1.0`
- deformation: `0.0 -> 0.0`
- kinetic energy final/max: `2.352740522948937e-07` / `2.625304623629482e-07`
- volume drift final/max: `5.075839893082154e-16` / `1.3958559705975922e-15`
- snapshot velocity Linf max: `2.2409995841729332e-04`

Oscillating droplet:

- result data: `experiment/ch14/results/ch14_oscillating_droplet/data.npz`
- final time: `1.0`
- signed deformation: `7.617534118365688e-02 -> 6.978270737321528e-02`
- kinetic energy final/max: `4.302657418093863e-05` / `4.302657418093863e-05`
- volume drift final/max: `1.5285397216419708e-06` / `1.5285397216419708e-06`
- snapshot velocity Linf max: `3.6373145456232406e-03`

Visualization:

- summary PDF: `artifacts/A/ch14_variational_pressure_n32_t1_visualization.pdf`
- per-snapshot PDFs:
  - `experiment/ch14/results/ch14_static_droplet/psi_t*.pdf`
  - `experiment/ch14/results/ch14_static_droplet/velocity_t*.pdf`
  - `experiment/ch14/results/ch14_static_droplet/pressure_t*.pdf`
  - `experiment/ch14/results/ch14_oscillating_droplet/psi_t*.pdf`
  - `experiment/ch14/results/ch14_oscillating_droplet/velocity_t*.pdf`
  - `experiment/ch14/results/ch14_oscillating_droplet/pressure_t*.pdf`

## Interpretation

The previous zero-drive pathology is removed: the oscillating droplet develops
nonzero kinetic energy and nonzero velocity from the capillary pressure
reaction. The static droplet is still not a roundoff-zero state; it shows a
small residual velocity/energy while preserving volume and deformation at
N=32/T=1. This is consistent with the theory distinction between a
variationally paired pressure reaction and a fully constrained finite-N static
critical interface. It is not a damping/CFL/smoothing issue and was not treated
as one.

[SOLID-X] Production pressure/corrector behavior now has an explicit
variational-adjoint contract and matching scalar operator path. No tested code
was deleted. No FD/WENO/PPE fallback, damping, CFL workaround, curvature cap,
smoothing, benchmark-name branch, blanket projection, or QP-as-physics route
was introduced.
