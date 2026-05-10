# CHK-RA-CH14-RISING-T003-001 — ch14 rising bubble T=0.03 checkpoint-0.01 run

## Request

User requested the Chapter 14 rising-bubble experiment with final time
`T=0.03` and checkpoints every `0.01`.

The canonical YAML was not rewritten for the final run.  The execution used
`experiment/ch14/config/ch14_rising_bubble.yaml` as the SSoT for grid,
physics, and numerical settings:

- grid: `cells: [32, 64]`
- domain: `[0.01, 0.02]`
- boundary: `x` periodic, `y` wall
- grid distribution schedule: `0`

Only launch-time overrides were applied:

```sh
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config ch14_rising_bubble --final-time 0.03 --checkpoint-interval 0.01"
```

`experiment/runner/main.py` now supports `--final-time` so short-run probes can
override `run.time.final` without editing the YAML.

## Outcome

The remote GPU run started from the YAML grid `[32,64]` and used capillary
limited timesteps of approximately `7.071088314e-06`.

The run did not reach `T=0.03`.  It stopped at:

- final sample time: `2.367834126506e-02`
- samples: `3372`
- final kinetic energy: `2.974161792852e+06`
- final volume_conservation: `7.381674992093e-06`
- final bubble centroid `yc`: `6.663999844135e-03`
- final mean rise velocity: `-1.542853040117e+03`
- final deformation: `3.370231525104e-01`
- `pre_blowup_checkpoint_written=True`

Generated checkpoints:

- `checkpoint_t0p01.npz`: pre-step checkpoint at
  `time=9.998518876307e-03`, `step=1414`, GPU
- `checkpoint_t0p02.npz`: pre-step checkpoint at
  `time=1.999703775261e-02`, `step=2828`, GPU
- `checkpoint_pre_blowup_input.npz`: pre-step checkpoint at
  `time=2.367827075068e-02`, `step=3371`, GPU
- `checkpoint_final.npz`: post-step final state at
  `time=2.367834126506e-02`, `step=3372`, GPU

No `checkpoint_t0p03.npz` was generated because the run did not reach
`T=0.03`.

Pulled results:

- `experiment/ch14/results/ch14_rising_bubble/data.npz`
- `experiment/ch14/results/ch14_rising_bubble/checkpoint_t0p01.npz`
- `experiment/ch14/results/ch14_rising_bubble/checkpoint_t0p02.npz`
- `experiment/ch14/results/ch14_rising_bubble/checkpoint_pre_blowup_input.npz`
- `experiment/ch14/results/ch14_rising_bubble/checkpoint_final.npz`
- time-series and snapshot PDF outputs through the available snapshot window

## Validation

- `python3 -m py_compile experiment/runner/main.py` PASS
- remote GPU execution used canonical YAML grid `[32,64]`
- results were pulled with `make pull`

## Interpretation

This is an executed but failed target run: the requested `T=0.03` was not
reached under the current YAML numerical settings.  The available evidence is
the successful `0.01` and `0.02` checkpoints and the pre-blowup/final states.
