# CHK-RA-CH14-REALPARAM-003 - ch14 real-parameter GPU rerun

## Scope

Rerun the two real-parameter chapter-14 canonical experiments from their YAML
configs:

- `experiment/ch14/config/ch14_capillary.yaml`
- `experiment/ch14/config/ch14_oscillating_droplet.yaml`

No solver, YAML, test, or paper source was changed in this rerun slice.

## Remote Execution Setup

The default non-interactive shell did not expose an SSH agent, so
`./remote.sh check` initially reported `Remote 'python' is NOT reachable`.
The usable agent socket was:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock
```

With that socket, `ssh python true` passed and the remote GPU was available.
The target result directories were removed both locally and on the remote before
the accepted reruns, so the listed artifacts are not mixed with earlier
chapter-14 outputs:

```text
experiment/ch14/results/ch14_capillary
experiment/ch14/results/ch14_oscillating_droplet
```

An early oscillating-droplet `make cycle` attempt returned SSH error 255 after
starting a remote process. A subsequent direct run created a second process.
Both were killed, the droplet result directory was cleaned again, and only the
final single-process GPU run below is accepted.

## Commands

Capillary wave:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=experiment/run.py ARGS="--config ch14_capillary"
```

Oscillating droplet:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ./remote.sh run experiment/run.py --config ch14_oscillating_droplet
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ./remote.sh pull
```

Both accepted runs executed on the remote `python` host with
`TWOPHASE_USE_GPU=1`; live checks showed a single `python3 experiment/run.py`
process using the RTX 3080 Ti.

## Results

| Case | Status | Wall time | Samples | Final time | Final volume drift | Final KE | Final diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ch14_capillary` | PASS | `19m22.163s` | `2145` | `0.046742820855` | `3.74496285398e-04` | `2.29037124150e-05` | interface amplitude `9.46731244965e-05` |
| `ch14_oscillating_droplet` | PASS | `41m02.820s` | `3852` | `0.105460663082` | `8.57485730500e-05` | `5.59298866131e-05` | signed deformation `4.91504707629e-02` |

Both `data.npz` files report `pre_blowup_checkpoint_written=False`.

## Local Outputs

Capillary wave outputs:

- `experiment/ch14/results/ch14_capillary/data.npz`
- `experiment/ch14/results/ch14_capillary/interface_amplitude.pdf`
- `experiment/ch14/results/ch14_capillary/kinetic_energy.pdf`
- `experiment/ch14/results/ch14_capillary/volume_drift.pdf`
- five psi, velocity, and pressure snapshots at approximately
  `t=0, 0.012, 0.023, 0.035, 0.047`
- `checkpoint_continuation.npz`, `checkpoint_final.npz`, `snapshots.pkl`

Oscillating-droplet outputs:

- `experiment/ch14/results/ch14_oscillating_droplet/data.npz`
- `experiment/ch14/results/ch14_oscillating_droplet/signed_deformation.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/kinetic_energy.pdf`
- `experiment/ch14/results/ch14_oscillating_droplet/volume_drift.pdf`
- five psi, velocity, and pressure snapshots at approximately
  `t=0, 0.026, 0.053, 0.079, 0.105`
- `checkpoint_continuation.npz`, `checkpoint_final.npz`, `snapshots.pkl`

## SOLID

[SOLID-X] Remote experiment execution/artifact/ledger only. No solver source,
numerical operator, YAML parameter, tests, paper text, FD/WENO/PPE fallback,
damping/CFL workaround, smoothing, curvature cap, benchmark branch, blanket
projection, QP-as-physics path, hidden DCCD/UCCD damper, or tested
implementation deletion changed.
