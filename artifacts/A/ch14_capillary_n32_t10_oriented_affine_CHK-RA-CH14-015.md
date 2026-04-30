# CHK-RA-CH14-015 — N=32, T=10 capillary-wave run with oriented affine jump

- Worktree: `ra-ch14-capillary-rootcause-20260430`
- Branch HEAD at run start: `0681f4a4` (`main` no-ff merge retained in this worktree)
- Config: `experiment/ch14/config/ch14_capillary_n32_t10_oriented_affine.yaml`
- Base config: `experiment/ch14/config/ch14_capillary.yaml`
- Result: `experiment/ch14/results/ch14_capillary_n32_t10_oriented_affine/data.npz`
- Command:

```text
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary_n32_t10_oriented_affine"
```

## Configuration delta

Only the benchmark size/time/output identity was changed from the existing
capillary-wave YAML:

```text
grid.cells = [32, 32]
run.time.final = 10.0
output.dir = results/ch14_capillary_n32_t10_oriented_affine
```

The production route remains:

```text
surface_tension.formulation = pressure_jump
projection.poisson.operator.interface_coupling = affine_jump
```

## Run outcome

The run completed to the requested final time.

```text
final t = 10.0
steps   = 1792
wall    = 45m35.784s
status  = completed, no BLOWUP guard
```

Affine coupling diagnostics:

```text
ppe_interface_coupling_affine_jump = 1 for all steps
ppe_interface_coupling_jump        = 0 for all steps
```

## Primary diagnostics

| Quantity | First | Last | Max |
|---|---:|---:|---:|
| `kinetic_energy` | `1.3827e-09` | `2.6867e-03` | `2.6903e-03` |
| `interface_amplitude` | `1.1970e-02` | `7.8471e-02` | `7.9242e-02` |
| `volume_conservation` | `0.0000e+00` | `6.3666e-04` | `6.7475e-04` |
| `kappa_max` | `1.7068e+00` | `5.0000e+00` | `5.0000e+00` |
| `ppe_rhs_max` | `0.0000e+00` | `1.3670e+00` | `1.3071e+01` |
| `bf_residual_max` | `3.0495e+00` | `1.6656e+01` | `3.1796e+01` |
| `div_u_max` | `2.6856e-03` | `2.6695e-04` | `4.8288e-02` |

## Early signed-mode acceleration

The signed `m=2` interface coefficient was reconstructed from saved `psi`
snapshots by locating the `psi=0.5` interface and projecting
`eta(x)=y_interface(x)-0.5` onto `cos(4πx)`.

Quadratic fits over early snapshots give:

| Fit snapshots | `A''_obs` | `A''_obs / A''_theory` |
|---:|---:|---:|
| 5 | `-1.2578e-03` | `0.8814` |
| 6 | `-1.4813e-03` | `1.0380` |
| 8 | `-1.4507e-03` | `1.0166` |

Reference theory from CHK-RA-CH14-011:

```text
A''_theory = -1.427056761315e-03.
```

The decisive sign has flipped from the previous wrong-sign run
(`A''_obs=+1.5025e-03`) to the restoring Young--Laplace sign.  The 6--8
snapshot fits also recover the expected magnitude to within roughly 4%.

## Interpretation

The oriented affine-jump contract fixes the primary sign failure: the run no
longer blows up near `t≈4.88`, reaches `T=10`, and the early capillary
acceleration is restoring with the expected scale.

This is not yet a perfect physical validation.  The interface amplitude still
grows substantially by `T=10`, and `kappa_max` remains pinned at the configured
cap `5.0`.  Therefore the remaining issue is not the Young--Laplace jump sign;
it is a later-time geometry/curvature/energy-stability problem to be treated
separately from this N=32/T=10 execution request.

## SOLID audit

[SOLID-X] no production code change in this CHK.  New config and artifact only.

