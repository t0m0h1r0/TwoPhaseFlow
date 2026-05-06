# CHK-RA-CH14-OSC-N32-T1-001 — ch14 Oscillating Droplet N=32, T=1

Date: 2026-05-06
Branch: `codex/ra-ch14-osc-n32-t1-20260506`
Worktree: `.claude/worktrees/codex-ra-ch14-osc-n32-t1-20260506`

## Scope

Run the ch14 oscillating-droplet benchmark first at `N=32`, `T=1`.
The checked-in production YAML set remains one file per experiment type.
This run used a temporary derived YAML named
`_tmp_ch14_oscillating_droplet_n32_t1`, removed locally after execution.

Derived settings:

- Base: `experiment/ch14/config/ch14_oscillating_droplet.yaml`
- Grid: `32 x 32`
- Final time: `1.0`
- Stack: unchanged pressure-jump/FCCD/UCCD6/implicit-BDF2/DC route
- Extra diagnostic: `pressure_contrast`

## Execution

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py \
  ARGS="--config _tmp_ch14_oscillating_droplet_n32_t1 --no-checkpoint-final"
```

Result: PASS.

- Remote: `python`
- Runtime: `0m52.049s`
- Steps: `100`
- Final time: `1.0`
- Result: `experiment/ch14/results/_tmp_ch14_oscillating_droplet_n32_t1/data.npz`

## Metrics

| Quantity | Value |
|---|---:|
| initial signed deformation | `7.617534e-02` |
| final signed deformation | `4.446894e-02` |
| Rayleigh--Lamb reference at `t=1` | `9.860155e-02` |
| final signed-deformation error | `-5.413260e-02` |
| final volume drift | `7.668281e-16` |
| max volume drift | `2.044875e-15` |
| initial KE | `1.847565e-38` |
| final KE | `2.877473e-37` |
| max KE | `3.179823e-37` |
| initial pressure contrast | `2.822989e-01` |
| final pressure contrast | `2.896270e-01` |
| max pressure contrast | `3.269438e-01` |
| velocity Linf over stored snapshots | `3.571025e-19` |
| pressure Linf over stored snapshots | `4.419391e-01` |
| affine pressure-acceleration face Linf | `4.163336e-17` |

All stored velocity, pressure, pressure-face, and diagnostic arrays are finite.

## Verdict

Numerical short gate: PASS for completion, stability, finite outputs, and volume
conservation.

Physical oscillation: NOT demonstrated at `N=32`, `T=1`.  The velocity remains
machine-zero and the signed-deformation signal deviates strongly from the
Rayleigh--Lamb reference.  This result is useful as a short stability gate, but
not as evidence that the oscillating-droplet physical benchmark is active.

[SOLID-X] experiment record/bookkeeping only; no solver or checked-in ch14
production YAML change; no tested implementation deleted; no FD/WENO/PPE
fallback or alternate numerical scheme introduced.
