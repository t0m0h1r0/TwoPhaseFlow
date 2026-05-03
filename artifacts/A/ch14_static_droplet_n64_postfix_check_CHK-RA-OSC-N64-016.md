# CHK-RA-OSC-N64-016 — Static Droplet Post-Fix Check

Date: 2026-05-03
Branch: `ra-oscillating-droplet-n64-20260503`

## Question

Does CHK-014 fully fix the N64 static droplet route, not merely the short
curvature-contract diagnostic?

## Run

```bash
make cycle EXP=experiment/run.py \
  ARGS='--config ch14_static_droplet_n64_alpha2_like_oscillating'
```

The first attempt fell back to local CPU because sandboxed `remote.sh check`
failed.  Per user correction, `./remote.sh check` was rerun outside the sandbox
and succeeded.  The same run was then launched through remote `make cycle`.

Remote produced `data.npz` at `T=1.5` and all requested snapshots
(`psi`, `velocity`, `pressure`, 31 each).  The remote process remained in
post-output CPU work after data/snapshot generation, so it was terminated after
the complete `T=1.5` data were confirmed and `./remote.sh pull` was run.

Result directory:

```text
experiment/ch14/results/ch14_static_droplet_n64_alpha2_like_oscillating/
```

## Metrics

From `data.npz`:

| metric | value |
|---|---:|
| final time | `1.5` |
| steps | `2320` |
| kinetic energy initial | `6.020933e-12` |
| kinetic energy final / max | `1.686513e-02` |
| first `KE >= 1e-3` | `t=0.551775` |
| first `KE >= 1e-2` | `t=1.199616` |
| volume drift final / max | `8.741532e-04` |
| deformation final / max | `0.0 / 3.965791e-03` |
| final speed `L_inf` | `2.393391e-01` |
| pressure contrast initial / final | `2.955149e-01 / 2.681811e+01` |

## Verdict

Not fully fixed.

CHK-014 removed the leading discrete transport/projection shortcut and makes
the short `T=0.40` curvature-contract diagnostic match the face-native control,
but the full `T=1.5` static droplet still accumulates parasitic kinetic energy
and pressure contrast.  The failure is slower and more localized than the
previous transport shortcut diagnosis, but static Young--Laplace equilibrium is
not yet a solved production contract.

The next root-cause search should therefore start after the face-native
transport boundary:

```text
projection-native psi transport is now enforced
  -> remaining error is in curvature/jump/projection history coupling,
     grid-motion feedback, or pressure-state representation
```

Do not treat this as a CFL/smoothing/cap tuning issue.

## SOLID-X

No code changed.  This is an experiment/diagnosis record only.
