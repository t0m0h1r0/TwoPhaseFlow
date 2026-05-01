# CHK-RA-GPU-UTIL-011 — Wall-trace invariant RCA after pinned-contact fix

Date: 2026-05-01
Scope: `experiment/ch14/config/ch14_capillary_n32_t25.yaml`, no-slip wall,
wall-attached capillary wave, post CHK-RA-GPU-UTIL-010 implementation

## Conclusion

The observed "moving wall contact point" in the post-fix N=32, T=25 run is
not the original no-slip contact branch moving.  The original branch remains
exactly fixed at

```text
y = 0.5100895692511684
```

with measured nearest-branch drift `0.0` over all saved snapshots.

The actual failure is stricter and more geometric: the wall trace of `psi`
changes even though the wall velocity is zero, and this creates an additional
pair of wall intersections at both side walls.  The first saved snapshot with
multiple side-wall crossings is

```text
t = 10.505674768265004
left  = [0.4631928987578815, 0.4821112336647799, 0.5100895692511684]
right = [0.4631928987578629, 0.4821112336647857, 0.5100895692511684]
```

Therefore the current implementation enforces only

```math
C_{\mathrm{pinned}}(t)=C_{\mathrm{pinned}}(0),
```

but the no-slip theory requires the stronger wall-trace invariant

```math
\psi|_{\partial\Omega}(s,t)=\psi|_{\partial\Omega}(s,0)
```

for the material phase variable on a stationary no-slip wall, unless an explicit
slip/contact-line/contact-angle law is introduced.  The current code preserves
the original crossing but still allows auxiliary geometry operations to alter
the rest of the wall trace, so new contacts can be born.

## Theory

For the material level-set/phase variable,

```math
\partial_t \psi + u\cdot\nabla\psi = 0.
```

On a stationary no-slip wall,

```math
u|_{\partial\Omega}=0.
```

Thus the boundary trace satisfies

```math
\partial_t \psi_w(s,t)=0,\qquad \psi_w=\psi|_{\partial\Omega}.
```

If a transverse wall contact is defined by

```math
\psi_w(c(t),t)=1/2,\qquad \partial_s\psi_w(c(t),t)\ne0,
```

then

```math
\dot c(t)=-{\partial_t\psi_w\over \partial_s\psi_w}=0.
```

This also fixes the wall phase intervals between contacts.  The number of
wall intersections and their physical coordinates cannot change under the
no-slip material model.  Reinitialization, FMM seeding, grid rebuild/remap, and
mass correction are auxiliary numerical operations; they must be projected back
onto this admissible wall-trace manifold.

## Re-analysis notes

Use `snapshots.pkl` for this check, not the static `data.npz` grid coordinate
arrays.  The dynamic-grid snapshots carry their own `grid_coords`; using the
final `data.npz` coordinates for every time can manufacture an apparent drift.

Post-fix N32/T25 observations from `snapshots.pkl`:

| t | left wall crossings of `psi=0.5` | wall-trace L∞ vs initial left trace |
|---:|---|---:|
| 0.006047776846959745 | `[0.5100895692511684]` | 0.0 |
| 5.004971791796142 | `[0.5100895692511684]` | 0.1601351561188333 |
| 10.007154469057369 | `[0.5100895692511684]` | 0.16972934256222338 |
| 10.505674768265004 | `[0.4631928987578815, 0.4821112336647799, 0.5100895692511684]` | 0.23560031229049877 |
| 12.50585166271933 | `[0.42078913672779344, 0.47101716788304093, 0.5100895692511684]` | 0.37261219491077163 |
| 15.003196610404455 | `[0.3907647053744174, 0.46610791771411314, 0.5100895692511684]` | 0.45481836236526096 |
| 20.008187959163383 | `[0.3357369572031939, 0.49345925795061535, 0.5100895692511684]` | 0.5318691540399831 |
| 25.0 | `[0.33278007147088356, 0.4853028975305518, 0.5100895692511684]` | 0.5990140028417634 |

Other diagnostics:

- wall velocity max over saved snapshots: `max |u_wall| = 0.0`,
  `max |v_wall| = 0.0`;
- original pinned branch drift: `0.0`;
- `max div_u_max = 2.438614738661804e-4`;
- final volume drift: `0.00506190787376452`;
- `kappa_max` is saturated at the cap `5.0` from the first output.

## Hypothesis audit

| ID | Hypothesis | Verdict | Evidence |
|---|---|---|---|
| H1 | The original pinned contact branch is still moving. | Rejected | Nearest branch to `y=0.5100895692511684` has drift `0.0`. |
| H2 | The movement is a post-processing artifact from using static `data.npz` grid coordinates. | Partly confirmed | Dynamic-grid analysis must use per-snapshot `grid_coords`; otherwise an apparent drift can be introduced. |
| H3 | New side-wall crossings are being created after the fix. | Confirmed | First multi-crossing snapshot at `t=10.505674768265004` has three crossings on both side walls. |
| H4 | The no-slip invariant is stronger than pinning one crossing. | Confirmed | Theory gives `\partial_t\psi_w=0`; wall-trace L∞ grows to `0.5990140028417634`. |
| H5 | Velocity wall BC is missing. | Rejected | Saved snapshots have `max |u_wall| = max |v_wall| = 0.0`. |
| H6 | Pure divergence/PPE error creates the observed contact issue. | Rejected as primary | `div_u_max` remains below `2.44e-4`; the failure is visible in `psi_w` topology. |
| H7 | Volume correction alone explains the extra contacts. | Rejected as primary | Volume drift is small compared with wall-trace deformation; current correction also excludes only a local pinned band. |
| H8 | The current wall-contact implementation intentionally hides all wall topology changes. | Rejected | It preserves the original pinned branch but leaves later extra crossings visible. |
| H9 | Ridge-eikonal reinitialization can alter wall trace if only local pins are imposed. | Supported | The reinitializer imposes pins after FMM and mass correction, but only at stored crossings. |
| H10 | Dynamic grid rebuild/remap can alter wall trace outside pinned bands. | Supported | Rebuild imposes pins and masks mass correction only near contacts, not over the full wall trace. |
| H11 | Capillary curvature/energy inconsistency excites wall wrinkles. | Supported as driver | `kappa_max` is capped from the first output, and the extra crossings appear symmetrically as the wall trace is distorted. |
| H12 | Missing contact-angle law justifies the new crossings. | Rejected | Without an explicit slip/contact-line law, no-slip material theory forbids wall-trace evolution. |
| H13 | The wall crossing count is a diagnostic ambiguity. | Rejected | Direct `psi=0.5` interpolation on per-snapshot wall coordinates shows the new crossing pair. |
| H14 | FD direct vs CG/DC solver choice is the primary issue. | Rejected for this symptom | Wall velocity and divergence are controlled; the topology error is in geometry boundary invariants. |
| H15 | The current code enforces `C(t)=C(0)` but not `\psi_w(t)=\psi_w(0)`. | Confirmed | `impose_on_wall_trace` writes only two wall nodes around each stored contact; wall L∞ still grows. |
| H16 | A full-wall trace constraint is a theoretically valid fix, not a clamp. | Confirmed design direction | It is exactly the discrete projection of `\partial_t\psi_w=0` for a stationary no-slip wall. |

## Code-path mismatch

The current implementation is correctly scoped for a pinned crossing, but it is
not the full no-slip wall-trace boundary condition:

- `src/twophase/levelset/wall_contact.py:139` builds a local mask near each
  contact coordinate only.
- `src/twophase/levelset/wall_contact.py:168` imposes an exact half-level
  crossing only around each pinned contact.
- `src/twophase/levelset/wall_contact.py:190` writes only the two neighboring
  wall nodes that straddle the stored coordinate.
- `src/twophase/levelset/ridge_eikonal_reinitializer.py:126` re-imposes those
  local pins after FMM reinitialization.
- `src/twophase/levelset/ridge_eikonal_reinitializer.py:131` excludes a local
  pinned band from mass correction, not the full wall trace.
- `src/twophase/simulation/ns_grid_rebuild.py:70` applies the same local pin
  and local mass-correction mask after dynamic-grid remap.

This is why the original branch is fixed but additional branches can appear.

## Root cause

The root cause is an incomplete discrete expression of the wall material
invariant.  The implementation currently constrains a finite set of contact
coordinates, while the continuous no-slip model constrains the whole boundary
trace of the material phase variable.  Auxiliary geometry steps then have
enough freedom to distort `psi_w` away from its initial trace; once the
distortion changes the sign/phase ordering on the wall, a new pair of
`psi=0.5` crossings appears.

The capillary curvature/energy stack is likely the forcing source that drives
the wall-trace wrinkle growth, as indicated by persistent curvature-cap
saturation.  However, even a flawed capillary force should not be allowed to
change `\psi_w` at a no-slip wall.  The invariant violation is therefore the
first boundary-condition bug to fix.

## Implementation policy

Do not apply an ad hoc capillary-wave clamp.  The theoretically consistent
design is to promote the current `WallContactSet` into a wall-trace constraint:

1. Store the initial physical wall trace `\psi_w^0(s)` for every stationary
   no-slip wall, including sign/phase intervals and initial contact roots.
2. On dynamic grids, interpolate `\psi_w^0` onto the current physical wall
   coordinates.
3. After reinitialization, dynamic remap, and global mass correction, project
   only boundary nodes back to `\psi_w^0`; leave the interior evolution free.
4. Exclude the boundary trace, or a rigorously defined boundary-adjacent trace
   band, from global mass correction so conservation repair cannot move wall
   topology.
5. Use the stored trace to seed contact roots and to reject creation of new
   wall crossings in invariant tests.
6. Add tests for: original contact drift, wall-trace L∞ preservation, no new
   wall crossings, CPU/GPU parity, and dynamic-grid remap with `schedule=1`.

This follows the A3 chain:

```text
Equation:        Dpsi/Dt=0 and u|wall=0
Boundary result: partial_t psi_w=0
Discretization: stored physical wall trace + projection after auxiliary ops
Code:           WallTraceInvariant used by reinit/remap/mass-correction paths
```

## SOLID audit

[SOLID-X] No production code changed in this CHK.  The identified design keeps
wall-boundary responsibility isolated in the level-set geometry layer and does
not move PPE/DC/capillary responsibilities into unrelated modules.
