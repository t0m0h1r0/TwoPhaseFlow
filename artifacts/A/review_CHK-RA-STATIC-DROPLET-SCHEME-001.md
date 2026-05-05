# CHK-RA-STATIC-DROPLET-SCHEME-001 — Static Droplet Scheme Selection Review

Date: 2026-05-06

Scope: ch14 static-droplet configuration selection against the paper's Young--Laplace / balanced-force pressure-jump contract.

## Question

The short T=0.2 static-droplet smoke had been run with
`ch14_static_droplet_n64_alpha2_like_oscillating.yaml`. That file is named as a
static droplet, but it intentionally keeps the dynamic oscillating-droplet
IMEX-BDF2 / implicit-BDF2 stack. The question was whether this is the right
scheme selection for a paper static-equilibrium gate.

## Review

The paper contract for the pressure-jump static droplet is:

- surface tension is imposed as an oriented Young--Laplace jump, not as a CSF
  body force in the predictor;
- PPE and face velocity correction must share the same affine jump face data;
- the static-equilibrium check is a frozen-interface / BF reference route, not
  the moving-interface coupled-stack time-accuracy diagnostic.

`ch14_static_droplet.yaml` already matches the ch14 README static route:

- `tracking.enabled: false`
- `convection.time_integrator: ab2`
- `viscosity.time_integrator: forward_euler`
- `surface_tension.formulation: pressure_jump`
- `projection.poisson.operator: fccd / phase_separated / affine_jump`
- `projection.poisson.solver: defect_correction` with FD direct low-order base

The N64 `*_like_oscillating` static files are useful differential controls for
the oscillating route, but they are not the paper static Young--Laplace / BF
pass-fail gate.

## Fix

No numerical scheme was changed. Instead, the ambiguous checked-in N64 control
configs and the ch14 config README now state that `*_like_oscillating` files are
oscillating-route controls, not the paper static-equilibrium gate. Static
Young--Laplace / BF checks should use `ch14_static_droplet.yaml` or an untracked
short copy of it.

## Remote T=0.2 Check

Remote GPU run:

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_static_droplet_paper_t0p2 --no-checkpoint-final"
```

The temporary config was an untracked T=0.2 copy of `ch14_static_droplet.yaml`.
It was removed after the run. Result path:
`experiment/ch14/results/_tmp_ch14_static_droplet_paper_t0p2/data.npz`.

Metrics:

- final time: `0.2`
- samples: `162`
- kinetic energy: `3.944997685277e-11 -> 8.644733486102e-07`
- final/max volume drift: `9.824043804629e-16`
- final/max deformation: `0.0 / 0.0`
- final speed Linf: `6.475562401968e-04`
- Young--Laplace jump: expected `0.288`, measured `0.2882390238961`
- jump error at T=0.2: `2.390238961071e-04`
- phase-mean-removed bulk pressure RMS at T=0.2: `1.892430873108e-05`

Verdict: the paper-aligned static route passes the short T=0.2 equilibrium
smoke. This does not claim long-time static equilibrium is fully solved; the
existing long-time caveats still apply.

## SOLID

[SOLID-X] Documentation/config classification only; no production solver boundary
changed and no tested implementation was deleted.
