# CHK-RA-CH14-TRACE-RIESZ-N32T1-001 — Trace-Riesz Runtime N32/T1 Gate

Date: 2026-05-07

User request: implement the selected closed-interface trace-Riesz capillary
source and run N=32, T=1 static/oscillating droplet experiments.

## Implementation

The production path now exposes a force-source selector:

```yaml
surface_tension:
  formulation: pressure_jump
  source: closed_interface_riesz
projection:
  poisson:
    operator:
      capillary_reaction_projection: pressure_component_hodge
```

For this source, the pressure stage builds the capillary cochain from the
pre-reinit transport endpoint:

```text
s_K = -M_f^{-1} C_K^T d_z(sigma S_h)
B_K =  M_f^{-1} C_K^T d_zV_m
c_K = s_K - B_K mu
```

It then adds `D_f c_K` to the PPE RHS and passes the same `c_K` through
`div_op.pressure_fluxes(..., capillary_jump_components=c_K)`.  The scalar
Young-Laplace jump is set to zero for this source so scalar curvature and
trace-Riesz cochains cannot double count.  Existing affine-jump face pressure
history is retained.

The weighted Hodge solve remains the same theorem object, but the implementation
now builds the FCCD divergence matrix analytically as a sparse CSR matrix and
solves the singular normal equations with sparse LSMR.  This keeps the same
`M_f,D_f` projection while making the N=32 gate practical on the remote GPU
machine.

## Validation Commands

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='twophase/tests/test_config_io_fccd.py::test_closed_interface_riesz_source_requires_reaction_projection twophase/tests/test_closed_interface_trace_riesz.py -q'
```

The wrapper expanded to the full CPU suite:

```text
608 passed, 32 skipped in 42.77s
```

Temporary N=32/T=1 YAMLs were generated under `experiment/ch14/config/`, pushed
for the remote runs, and removed after results were pulled.

## Static Droplet N=32/T=1

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_static_trace_riesz_n32_t1'
```

Result directory:

```text
experiment/ch14/results/_tmp_ch14_static_trace_riesz_n32_t1/
```

Metrics:

```text
final time                         1.0
kinetic_energy first -> last        1.270102870656e-10 -> 8.881600364608e-07
deformation first -> last           0 -> 0
max volume drift                    2.030335957233e-15
final speed Linf                    1.347149112711e-03
corrected capillary weighted L2     5.363597e-02 -> 5.343402e-02
Hodge residual weighted L2          6.397429e-03 -> 4.694422e-03
div_u max final                     4.730460e-07
```

Visualization PDFs:

```text
experiment/ch14/results/_tmp_ch14_static_trace_riesz_n32_t1/psi_t1.000.pdf
experiment/ch14/results/_tmp_ch14_static_trace_riesz_n32_t1/velocity_t1.000.pdf
experiment/ch14/results/_tmp_ch14_static_trace_riesz_n32_t1/pressure_t1.000.pdf
```

Interpretation: the static run is stable, volume-preserving, and geometrically
stationary by the reported deformation metric.  It is not a roundoff-static
proof: the finite trace polygon retains a nonzero Hodge residual and produces a
small spurious current.  This is consistent with the earlier theoretical caveat
that a sampled continuum circle is a convergence gate, not an exact discrete
critical polygon.

## Oscillating Droplet N=32/T=1

Command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS='--config _tmp_ch14_oscillating_trace_riesz_n32_t1'
```

Result directory:

```text
experiment/ch14/results/_tmp_ch14_oscillating_trace_riesz_n32_t1/
```

Metrics:

```text
final time                         1.0
kinetic_energy first -> last        2.302005850263e-09 -> 9.657244011558e-05
deformation first -> last           8.034730291014e-02 -> 6.838554894764e-02
signed deformation first -> last    7.617534118366e-02 -> 4.349287543057e-02
max volume drift                    1.917070154649e-15
final speed Linf                    5.405474140833e-03
corrected capillary weighted L2     5.607454e-02 -> 7.344034e-02
Hodge residual weighted L2          1.063894e-02 -> 1.824185e-02
div_u max final                     2.257667e-07
```

Visualization PDFs:

```text
experiment/ch14/results/_tmp_ch14_oscillating_trace_riesz_n32_t1/psi_t1.000.pdf
experiment/ch14/results/_tmp_ch14_oscillating_trace_riesz_n32_t1/velocity_t1.000.pdf
experiment/ch14/results/_tmp_ch14_oscillating_trace_riesz_n32_t1/pressure_t1.000.pdf
```

Interpretation: the old zero-drive failure is removed.  The previous
`range_projected` N=32/T=1 run had `KE ~1e-37` and velocity Linf
`3.57e-19`; the trace-Riesz source reaches KE `9.66e-05` and speed Linf
`5.41e-03`.  This proves capillary drive now enters the production corrector.

## Verdict

Pass for implementation plumbing, finite execution, volume conservation, visual
output generation, and elimination of the zero-drive symptom.  Not yet a final
physics proof: static-current convergence and Rayleigh-Lamb phase/amplitude
must still be checked across N and with the reinit endpoint ledger separated.

[SOLID-X] Code changes preserve the pressure-jump/FCCD/UCCD6 production
contract, add no FD/WENO/PPE fallback, damping, CFL workaround, curvature cap,
smoothing, benchmark-name branch, blanket `c -> Pi_R c`, or QP-as-physics
route.  Tested implementation was not deleted.
