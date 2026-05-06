# CHK-RA-CH14-STATIC-N32-T20-001

## Scope

Run the ch14 static droplet production stack at `N=32`, `T=20.0`, using a
temporary YAML derived from canonical `ch14_static_droplet.yaml`.

Only validation-only fields were changed:

- `grid.cells: [32, 32]`
- `run.time.final: 20.0`
- output directory, snapshot interval, and print cadence

The checked-in canonical numerical stack was unchanged:
P2 ALE discrete-gradient curvature, Ridge--Eikonal every step, FCCD/TVD-RK3
interface transport, UCCD6/IMEX-BDF2 convection, CCD implicit-BDF2 viscosity
DC12, pressure-jump surface tension, and FCCD phase-separated affine-jump PPE
DC12 with FD direct base solve.

Temporary config:
`experiment/ch14/config/_tmp_ch14_static_droplet_base_n32_t20.yaml`

The temporary YAML was removed after the run; the checked-in ch14 config
directory is back to the canonical five YAML files.

## Remote Run

Command:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_static_droplet_base_n32_t20 --no-checkpoint-final"
```

Result:

- PASS: remote run completed and pulled results.
- Runtime: `16m59.066s`.
- GPU path was active during the run (`nvidia-smi` showed PID `1706525`
  using `278 MiB` while running).
- Result data:
  `experiment/ch14/results/_tmp_ch14_static_droplet_base_n32_t20/data.npz`

Progress log highlights:

| step | t | dt | KE | limiter |
|---:|---:|---:|---:|---|
| 1 | `0.0099` | `0.00988` | `2.305e-07` | capillary |
| 500 | `5.2390` | `0.01049` | `1.094e-03` | capillary |
| 1000 | `10.4599` | `0.01042` | `2.153e-03` | capillary |
| 1500 | `15.6877` | `0.01047` | `2.515e-03` | capillary |

## NPZ Metrics

| Metric | Value |
|---|---:|
| final time | `2.000000000000e+01` |
| diagnostic samples | `1913` |
| dt min | `2.195861268888e-03` |
| dt max | `1.051665265411e-02` |
| final volume drift | `6.217903869026e-15` |
| max volume drift | `7.359967844969e-15` |
| final kinetic energy | `2.758994927608e-03` |
| max kinetic energy | `2.759626752836e-03` at `t=1.999780413873e+01` |
| final deformation | `0.000000000000e+00` |
| max abs deformation | `0.000000000000e+00` |
| final velocity Linf | `2.514469729957e-02` |
| final velocity L2 | `5.136702711493e-03` |
| final psi min/max/mean | `1.367448022170e-02` / `9.615645211538e-01` / `2.547147380146e-01` |

Kinetic-energy samples:

| target t | nearest t | KE | volume drift |
|---:|---:|---:|---:|
| `0.2` | `1.972173294378e-01` | `7.307386295181e-06` | `7.613759839623e-16` |
| `5.0` | `4.997586551831e+00` | `1.030191975485e-03` | `5.583423882390e-15` |
| `10.0` | `1.000126517563e+01` | `2.096693205293e-03` | `2.157231954560e-15` |
| `15.0` | `1.499659623766e+01` | `2.483832732883e-03` | `3.045503935849e-15` |
| `20.0` | `2.000000000000e+01` | `2.758994927608e-03` | `6.217903869026e-15` |

Young--Laplace reference:

- Expected pressure jump: `sigma / R = 0.072 / 0.25 = 2.88e-01`.
- Final phase-mask estimate (`psi<0.10`, `psi>0.90`):
  `3.299623568852e-01`, relative error `1.457026280737e-01`.
- Final geometric bulk estimate (`r<0.20`, `r>0.30`):
  `2.979239791006e-01`, relative error `3.445826076611e-02`.

## Verdict

Execution/stability smoke: PASS. The production stack completed `N=32`, `T=20`
without blow-up, preserved volume to roundoff, kept circular deformation at
zero, and remained capillary-limited.

Static-equilibrium quality: WARN/FAIL for this coarse long-time gate. Kinetic
energy grows from `7.31e-06` near `T=0.2` to `2.76e-03` at `T=20`, and final
velocity Linf reaches `2.51e-02`. This is a persistent coarse-grid
spurious-current signal, so `N=32` should not be used as an equilibrium-quality
pass criterion. It is useful only as a stability smoke and regression probe for
mass conservation.

No main merge was performed.
