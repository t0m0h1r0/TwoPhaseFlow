# CHK-RA-CH14-STATIC-N32-T5-001

## Scope

Run the ch14 static droplet production stack at `N=32`, `T=5.0`, using a
temporary YAML derived from canonical `ch14_static_droplet.yaml`.

Only these validation-only fields were changed:

- `grid.cells: [32, 32]`
- `run.time.final: 5.0`
- output directory and snapshot interval

The checked-in canonical static-droplet numerical stack was unchanged:
P2 ALE discrete-gradient curvature, Ridge--Eikonal every step, FCCD/TVD-RK3
interface transport, UCCD6/IMEX-BDF2 convection, CCD implicit-BDF2 viscosity
DC12, pressure-jump surface tension, and FCCD phase-separated affine-jump PPE
DC12 with FD direct base solve.

Temporary config:
`experiment/ch14/config/_tmp_ch14_static_droplet_base_n32_t5.yaml`

The temporary YAML was removed after the run; the checked-in ch14 config
directory is back to the canonical five YAML files.

## Remote Run

Command:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_static_droplet_base_n32_t5 --no-checkpoint-final"
```

Result:

- PASS: remote run completed and pulled results.
- Runtime: `4m18.528s`.
- GPU path was active during the run (`nvidia-smi` showed PID `1704203`
  using `278 MiB` while running).
- Result data:
  `experiment/ch14/results/_tmp_ch14_static_droplet_base_n32_t5/data.npz`

Progress log highlights:

| step | t | dt | KE | limiter |
|---:|---:|---:|---:|---|
| 1 | `0.0099` | `0.00988` | `2.305e-07` | capillary |
| 100 | `1.0429` | `0.01045` | `1.623e-04` | capillary |
| 200 | `2.0885` | `0.01047` | `3.646e-04` | capillary |
| 300 | `3.1372` | `0.01051` | `5.869e-04` | capillary |
| 400 | `4.1886` | `0.01051` | `8.250e-04` | capillary |

## NPZ Metrics

| Metric | Value |
|---|---:|
| final time | `5.000000000000e+00` |
| diagnostic samples | `478` |
| dt min | `2.413448169231e-03` |
| dt max | `1.051665265411e-02` |
| final volume drift | `1.522751967925e-15` |
| max volume drift | `2.791711941195e-15` |
| final kinetic energy | `1.030601680631e-03` |
| max kinetic energy | `1.030601680631e-03` at `t=5.0` |
| final deformation | `0.000000000000e+00` |
| max abs deformation | `0.000000000000e+00` |
| final velocity Linf | `1.608684791168e-02` |
| final velocity L2 | `2.539548073026e-03` |
| final psi min/max/mean | `1.329406783005e-02` / `9.620852500469e-01` / `2.538841996657e-01` |

Young--Laplace reference:

- Expected pressure jump: `sigma / R = 0.072 / 0.25 = 2.88e-01`.
- Final phase-mask estimate (`psi<0.10`, `psi>0.90`):
  `3.101743609738e-01`, relative error `7.699430893674e-02`.
- Final geometric bulk estimate (`r<0.20`, `r>0.30`):
  `2.824537447203e-01`, relative error `1.925783083217e-02`.

## Verdict

Execution/stability smoke: PASS. The production stack completed `N=32`, `T=5.0`
without blow-up, preserved volume to roundoff, kept circular deformation at
zero, and maintained the expected capillary time-step limiter.

Static-equilibrium quality: WARN. Kinetic energy increased monotonically to
`1.03e-03`, with final velocity Linf `1.61e-02`. At `N=32`, this is a coarse-grid
spurious-current signal, not an equilibrium pass. Pressure jump remains
qualitatively close, but the long-time static-droplet quality should be judged
by a resolution comparison rather than by this coarse smoke alone.

No main merge was performed.
