# CHK-RA-GPU-UTIL-008 — N32/T25 capillary-wave wall-contact RCA

Date: 2026-05-01
Scope: `experiment/ch14/config/ch14_capillary_n32_t25.yaml`, wall-attached capillary wave, no-slip contact-line invariant

## Conclusion

The N=32, T=25 capillary-wave run does not fail because the wall velocity
condition itself is absent.  The saved fields show all velocity components are
zero on the walls, but the interface contact points and the wall trace of
`psi` still move.

The root cause is therefore in the geometry pipeline, not in the velocity wall
hook: ridge-eikonal reinitialization and dynamic interface-fitted grid rebuilds
do not enforce the closed-domain contact-line invariant required by a no-slip
wall.  A wall-attached interface is not just an interior zero contour; its
closure includes constrained contact points on `boundary(Omega)`.

## Physical invariant

For a material level set,

```math
\partial_t \psi + u \cdot \nabla \psi = 0.
```

At a no-slip wall, `u = 0`.  Therefore the wall trace must satisfy

```math
\partial_t \psi|_{\partial\Omega}=0,
```

and the contact-line set

```math
C(t)=\overline{\Gamma}(t)\cap\partial\Omega
```

must remain fixed unless an explicit slip/contact-angle/contact-line law is
introduced.  Reinitialization and ALE/grid remapping are auxiliary numerical
operations; they are not allowed to move this constrained zero set.

## N32/T25 observation

Baseline command:

```bash
make cycle EXP=experiment/run.py ARGS="--config ch14_capillary_n32_t25"
```

Result:

- BLOWUP at `step=1970`, `t=16.3947`.
- `kappa_max` reaches the cap at `t≈0.125`.
- Interface amplitude exceeds `0.1` at `t≈6.775`.
- `div_u_max > 1e-3` at `t≈15.248`.
- Final saved values: `A=0.4501`, `KE=1.11e10`, `div_u_max=1.95e5`.

Wall-contact check from saved snapshots:

| time | left contact y | right contact y | wall speed max |
|---:|---:|---:|---:|
| 0.006 | 0.507129 | 0.507129 | 0 |
| 5.001 | 0.447958 | 0.447958 | 0 |
| 10.004 | 0.512443 | 0.512443 | 0 |
| 15.008 | 0.215440 | 0.215440 | 0 |
| 16.001 | 0.515286 | 0.515286 | 0 |

The contact point moves by `O(10^-1)` while the wall velocity remains exactly
zero.  This violates the no-slip material-interface invariant.

## Controlled probes

All probes are N=32, `final=0.15`, same pressure-jump/FCCD stack, with dense
snapshots.  They isolate the numerical geometry operators:

| case | grid schedule | reinit every | max contact drift | wall `psi` L_inf change | max kappa |
|---|---:|---:|---:|---:|---:|
| baseline | 1 | 20 | `1.99e-3` | `1.68e-1` | `5.0` |
| no reinit | 1 | 0 | `1.50e-3` | `8.53e-3` | `1.704` |
| static grid | 0 | 20 | `1.40e-5` | `1.76e-1` | `5.0` |
| static grid + no reinit | 0 | 0 | `5.46e-6` | `1.06e-4` | `1.704` |

Interpretation:

1. Pure advection with no-slip walls nearly preserves the contact point.
2. Ridge-eikonal reinitialization changes the wall `psi` trace strongly and
   drives curvature to the cap, even when static grid keeps the crossing
   nearly fixed.
3. Dynamic grid rebuild with global remap/mass correction moves the contact
   point even without reinitialization.
4. The production combination (`schedule=1`, reinit every 20) combines both
   effects: wall-trace distortion plus contact-coordinate drift.

## Hypothesis audit

| ID | hypothesis | judgement |
|---|---|---|
| H1 | Velocity wall BC is missing. | Rejected: wall velocity is zero on saved snapshots. |
| H2 | No-slip contact-line invariant is missing from geometry operations. | Confirmed: `psi` wall trace and contact y move despite zero wall velocity. |
| H3 | Reinitialization alone moves the contact coordinate. | Partly rejected: static-grid reinit keeps contact nearly fixed short-term, but distorts wall trace and curvature. |
| H4 | Dynamic grid remap/mass correction moves pinned contacts. | Confirmed: `schedule=1`, no-reinit probe still moves contact by `1.5e-3` in `t=0.15`. |
| H5 | Curvature cap is the primary physical cause. | Rejected as root, confirmed amplifier: it is reached immediately after wall-geometry distortion. |
| H6 | CFL is the primary cause. | Rejected as root: an invariant violation occurs under capillary-limited small steps. |
| H7 | FD direct / DC `L_L` solver causes the blowup. | Rejected: factor reuse is active and divergence remains small until much later. |
| H8 | Young--Laplace sign is simply reversed. | Rejected by prior signed-mode checks; current failure is wall/high-mode geometry. |
| H9 | Volume drift drives the failure. | Rejected as primary; wall-contact motion and curvature cap occur first. |
| H10 | Output/diagnostics artifact. | Rejected: direct snapshot geometry shows moving wall contacts. |
| H11 | Missing contact-angle physics matters. | Confirmed at design level: current config has no explicit contact-angle/contact-line law, so no-slip implies pinned contacts. |
| H12 | Nonuniform affine-jump energy inconsistency is irrelevant. | Rejected: prior N32/T8 RCA shows it is a downstream amplifier, but it does not explain zero-wall-velocity contact motion alone. |

## Implementation implication

The correct fix is not a CFL reduction, curvature-cap tuning, or artificial
clamping.  The paper-faithful correction is to promote wall contacts to
constrained geometry data:

1. Detect/store contact-line seeds on solid walls for wall-attached interfaces.
2. Reinitialize with those seeds as Dirichlet zero-set data.
3. Exclude pinned contact DOFs from all mass corrections, including
   `ns_grid_rebuild` remap correction.
4. Build dynamic grid monitors from the closed interface
   `Gamma_bar = Gamma union C`, not from the already-shifted wall trace.
5. Add invariant tests: pure advection, reinit, grid rebuild, and full
   capillary short probe must preserve `C(t)=C(0)` under no-slip walls.

[SOLID-X] Investigation artifact only; no production code/module boundary
change.  The identified design change belongs in geometry/regrid services, not
in the PPE solver or capillary-wave-only configuration.
