# CHK-RA-CH14-OSC-ONEPERIOD-RERUN-001

## Request

User requested a one-period rerun of the Chapter 14 oscillating-droplet
experiment after the closed-droplet invariant and periodic-measure fixes.

## Command

```bash
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock \
make cycle EXP=experiment/run.py ARGS="--config ch14_oscillating_droplet"
```

Remote target:

- host: `python`
- GPU: NVIDIA GeForce RTX 3080 Ti
- config: `experiment/ch14/config/ch14_oscillating_droplet.yaml`
- final time: `T=0.105460663082`
- snapshots: `0, T/4, T/2, 3T/4, T`

## Result

The remote GPU run completed and results were pulled to:

```text
experiment/ch14/results/ch14_oscillating_droplet/
```

Runtime:

- `real 43m16.654s`
- samples: `3452`
- final time: `1.054606630820e-01`
- `pre_blowup_checkpoint_written=False`

Time-series diagnostics from `data.npz`:

| diagnostic | value |
|---|---:|
| final `volume_conservation` | `3.549517266127e-01` |
| max `volume_conservation` | `3.549517266127e-01` |
| final kinetic energy | `3.275793508021e-05` |
| max kinetic energy | `4.281261244890e-05` |
| initial signed deformation sample | `7.553485484232e-02` |
| final signed deformation | `2.180827416932e-02` |
| min signed deformation | `-3.457248445415e-02` |
| max signed deformation | `7.553485484232e-02` |
| Rayleigh-Lamb reference at final time | `1.000000000000e-01` |

P1 sharp area reconstructed from stored snapshot fields and per-snapshot grid
coordinates:

| snapshot | time | P1 sharp area | relative to first snapshot |
|---:|---:|---:|---:|
| 0 | `2.652412244614e-05` | `7.739538194696e-05` | `+0.000000e+00` |
| 1 | `2.638935673961e-02` | `8.266995278625e-05` | `+6.815098e-02` |
| 2 | `5.275687127774e-02` | `8.752467652010e-05` | `+1.308772e-01` |
| 3 | `7.911997126708e-02` | `9.235045015846e-05` | `+1.932295e-01` |
| 4 | `1.054606630820e-01` | `9.743452982326e-05` | `+2.589192e-01` |

## Interpretation

The rerun is a completed experiment, but it is not a physically acceptable
one-period validation result.  Over a full period the diffuse-mass diagnostic
increases to about `35.5%`, and an independent P1 sharp-area reconstruction
from the saved snapshots increases by about `25.9%`.

This means the short 20-step RCA probe was not sufficient to certify long-time
closed-droplet volume preservation.  The remaining defect is no longer the
periodic duplicate-node overcount itself: that was previously measured as
`rel_overcount=0`.  The one-period data instead points to a long-time mismatch
among transport, dynamic grid rebuild/remap, and sharp-volume retraction.

No solver/config parameter was changed for this rerun.
