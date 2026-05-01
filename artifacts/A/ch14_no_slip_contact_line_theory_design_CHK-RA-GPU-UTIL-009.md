# CHK-RA-GPU-UTIL-009 — No-slip wall-contact theory and implementation design

Date: 2026-05-01
Status: theory established; implementation design ready
Scope: wall-attached capillary-wave interface, ridge-eikonal reinitialization,
dynamic interface-fitted grid rebuild, conservative-level-set geometry

## 1. Executive conclusion

The previous wall-closure implementation prevents a wall-attached interface
from becoming an open interior curve, but it does not yet enforce the stronger
no-slip contact-line invariant.  These are different mathematical contracts:

1. **Topological wall closure**: the reconstructed zero set must touch the
   wall.
2. **Material no-slip pinning**: the contact set on a stationary no-slip wall
   must stay at its original physical wall coordinates unless an explicit slip
   or contact-line law is introduced.

The N32/T25 result violates contract 2.  Therefore the correct implementation
unit is not a capillary-wave-specific clamp; it is a generic wall-contact
constraint service consumed by reinitialization, grid rebuild/remap, mass
correction, and grid-monitor construction.

## 2. Continuum theory

Let `Omega` be the flow domain, `Gamma_w = boundary(Omega)` a stationary solid
wall, and

```math
\Gamma(t)=\{x\in\Omega:\phi(x,t)=0\}.
```

The closed-domain interface is

```math
\overline{\Gamma}(t)=\Gamma(t)\cup C(t),
\qquad
C(t)=\overline{\Gamma}(t)\cap\Gamma_w .
```

For a material interface,

```math
{D\phi\over Dt}=\partial_t\phi+\mathbf{u}\cdot\nabla\phi=0.
```

On a no-slip stationary wall,

```math
\mathbf{u}|_{\Gamma_w}=0.
```

Therefore, on the wall trace,

```math
\partial_t\phi|_{\Gamma_w}=0.
```

Let a contact point be represented by a wall coordinate `s(t)`:

```math
\phi(X_w(s(t)),t)=0.
```

Differentiating along the wall gives

```math
0={d\over dt}\phi(X_w(s(t)),t)
  =\partial_t\phi+\dot{s}\,\partial_s\phi .
```

Since `partial_t phi = 0` on a no-slip wall, a transverse contact
(`partial_s phi != 0`) implies

```math
\dot{s}=0.
```

Thus, for this project’s current wall model, the contact-line set is a
geometric invariant:

```math
C(t)=C(0).
```

If this invariant is not desired, the physics must be changed explicitly:
Navier slip, a prescribed moving contact line, or a contact-angle/contact-line
law.  None of those appears in the current capillary-wave configuration, so
moving the contact point is not physically admissible.

## 3. Discrete invariant

Let `P_w` denote restriction to wall nodes and let `Z_w(psi)` denote the
wall half-contour positions where `psi=1/2`.  For the current no-slip wall:

```math
Z_w(\psi^{n+1}) = Z_w(\psi^n) = Z_w(\psi^0)
```

up to interpolation tolerance.  The stronger wall-trace property

```math
P_w \psi^{n+1}=P_w\psi^n
```

holds for pure physical advection.  Auxiliary geometry operators may restore
the interface profile, but they must at minimum preserve the pinned half
contour and phase sign on the wall.

This gives a precise distinction:

- **Allowed**: reinitialize the signed-distance profile in the interior.
- **Forbidden**: move the wall half-contour or detach it from its pinned
  physical wall coordinate.
- **Allowed only with explicit model**: change contact angle or contact-line
  speed.

## 4. Theory verification against current data

### 4.1 N32/T25 failure

The N32/T25 run stopped at `step=1970`, `t=16.3947`.  Saved snapshots show all
wall velocity components are zero, but the side-wall contact coordinate moves:

| time | side-wall contact `y` | wall velocity max |
|---:|---:|---:|
| 0.006 | 0.507129 | 0 |
| 5.001 | 0.447958 | 0 |
| 15.008 | 0.215440 | 0 |
| 16.001 | 0.515286 | 0 |

This falsifies “missing velocity wall BC” and confirms “missing contact-line
geometric constraint.”

### 4.2 Operator isolation probes

Short N32 probes (`T=0.15`) isolate the auxiliary operators:

| case | grid schedule | reinit every | max contact drift | wall `psi` L_inf change | max kappa |
|---|---:|---:|---:|---:|---:|
| production baseline | 1 | 20 | `1.99e-3` | `1.68e-1` | `5.0` |
| no reinit | 1 | 0 | `1.50e-3` | `8.53e-3` | `1.704` |
| static grid | 0 | 20 | `1.40e-5` | `1.76e-1` | `5.0` |
| static grid + no reinit | 0 | 0 | `5.46e-6` | `1.06e-4` | `1.704` |

Interpretation:

1. Pure advection with no-slip walls preserves the pinned contact coordinate.
2. Ridge-eikonal reinitialization changes the wall profile and quickly drives
   curvature to the cap.
3. Dynamic grid rebuild/remap moves the contact coordinate even without
   reinitialization.
4. The production route violates the no-slip contact invariant through the
   combination of geometry reinitialization and dynamic remapping.

## 5. Why the existing wall-closure theory is insufficient

The existing wall-ridge closure adds mirror Gaussian support, boundary ridge
admissibility, wall seeds, contact-pinned mass correction, and closure-seed
grid monitors.  That establishes a **closed-domain zero-set** contract.  It
does not store `C(0)` as an invariant physical constraint.

Current code uses the **current** wall trace as the contact source:

- `RidgeEikonalReinitializer._wall_contact_band(...)` detects whether a wall
  has a current crossing, then masks a near-interface band during mass
  correction.
- `RidgeExtractor.compute_xi_ridge(...)` mirrors current crossings.
- `Grid._closure_seed_indicator_1d(...)` builds a monitor from current
  crossings and current near-zero nodes.
- `rebuild_ns_grid(...)` applies global mass correction after remap without a
  pinned contact free-mask.

These operations can preserve wall attachment while still allowing the
attached point to slide.  That is exactly what the N32/T25 snapshots show.

## 6. Implementation design

### 6.1 New geometry contract

Add a wall-contact constraint layer, conceptually:

```python
@dataclass(frozen=True)
class WallContact:
    wall_axis: int          # normal axis of wall
    wall_side: Literal["lo", "hi"]
    tangent_axis: int       # wall coordinate axis in 2D
    coordinate: float       # physical coordinate fixed by no-slip
    mode: Literal["pinned_no_slip"]
    angle_mode: Literal["initial", "mirror_neutral", "unspecified"]

@dataclass(frozen=True)
class WallContactSet:
    contacts: tuple[WallContact, ...]
```

This is not capillary-wave-specific.  It is derived from wall BC + initial
interface geometry:

```math
boundary_condition.type = wall
\quad\land\quad
\Gamma(0)\cap\Gamma_w\ne\emptyset
\quad\Rightarrow\quad
C(t)=C(0).
```

### 6.2 Lifecycle ownership

Create the contact set once immediately after the initial `psi` field is
built, before any initial nonuniform grid rebuild:

1. `runner.run_simulation`: build `psi`.
2. Detect `WallContactSet` from `psi`, grid, and `boundary_condition`.
3. Attach it to the solver/geometry runtime.
4. Pass it to reinitializer and grid-rebuild services.

The contacts are stored in physical coordinates, so they remain valid after
dynamic grid rebuilds.

### 6.3 Reinitialization contract

`RidgeEikonalReinitializer` must accept `wall_contacts`.

Required behavior:

1. Convert each physical contact to current-grid interpolation coordinates.
2. Add exact Dirichlet zero seeds at the pinned contacts for FMM/redistance.
3. Build ridge mirror support around pinned contacts, not only current
   crossings.
4. Exclude a contact band around pinned contacts from mass correction.
5. After reinitialization, verify

```math
|\phi(c_k)| \le \varepsilon_{\rm pin}
```

for every pinned contact `c_k`.

For the current capillary-wave side-wall contacts, `angle_mode =
mirror_neutral` is consistent with the initial mode-2 graph because the
interface meets the side walls orthogonally.  For future wetting/contact-angle
physics, `angle_mode` must become an explicit physical input.

### 6.4 Grid rebuild/remap contract

`rebuild_ns_grid(...)` must accept `wall_contacts`.

Required behavior:

1. `Grid.update_from_levelset(...)` includes pinned contact coordinates in the
   monitor projection, independent of whether the current `psi` wall trace has
   drifted.
2. Remap `psi` from old to new grid.
3. Apply a constrained correction:

```math
\phi \leftarrow \phi + \lambda \chi_{\rm free},
\qquad
\chi_{\rm free}=0\quad\text{near pinned contacts}.
```

or equivalently use a masked `psi` mass correction whose free mask excludes
pinned contact neighborhoods.
4. Re-impose/interpolate the pinned half-contour locally on the wall if the
   remap interpolation leaves `|phi(c_k)|` above tolerance.
5. Reproject velocity as today; velocity wall BC is not the root cause.

This is a constrained projection onto the no-slip geometry manifold, not an
ad-hoc clamp.  The constraint comes directly from `C(t)=C(0)`.

### 6.5 API placement

Suggested files:

- `src/twophase/levelset/wall_contact.py`
  - `WallContact`, `WallContactSet`
  - `detect_wall_contacts_from_psi(...)`
  - `wall_contact_free_mask(...)`
  - `assert_wall_contacts_pinned(...)`
- `src/twophase/levelset/ridge_eikonal_reinitializer.py`
  - accept/update `wall_contacts`
  - use pinned contacts for FMM seeds and mass-correction mask
- `src/twophase/core/grid.py`
  - accept optional wall-contact projections in dynamic monitor
- `src/twophase/simulation/ns_grid_rebuild.py`
  - masked mass correction and post-remap pin verification
- `src/twophase/simulation/runner.py` or solver runtime bootstrap
  - detect/store contacts once from initial condition

### 6.6 Configuration

Default behavior should be safe and physical:

```yaml
boundary_condition:
  type: wall

interface:
  wall_contact:
    mode: pinned_no_slip
    detect: initial
    angle: mirror_neutral   # current capillary-wave-compatible default
```

If no wall contact is detected, this layer is inert.  If a user wants moving
contact lines, they must select an explicit non-default law.

## 7. Verification plan

### 7.1 Unit invariants

1. **Detection**: capillary-wave IC detects two side-wall contacts at the
   expected physical `y` coordinate.
2. **Pure reinit**: ridge-eikonal reinit preserves `psi=1/2` wall contact
   location to interpolation tolerance.
3. **Grid rebuild**: schedule-1 rebuild/remap preserves pinned contacts with
   no physical time advancement.
4. **Masked mass correction**: total free-region mass correction restores mass
   without changing `phi(c_k)=0`.
5. **No false positives**: closed droplet away from wall detects no contacts.

### 7.2 Pipeline probes

Repeat the four short probes from §4.2.  Acceptance:

- production baseline `T=0.15`: max contact drift `O(1e-5)` or lower.
- no-reinit schedule=1: drift comparable to static-grid/no-reinit baseline.
- reinit static grid: wall profile may change away from contact, but
  half-contour pin remains fixed and `kappa_max` should not hit cap immediately.

### 7.3 Long run

Run N32/T25 with `schedule=1`.  Required first-stage success:

- no contact drift before any later instability,
- no early `kappa_max=5` triggered by wall contact geometry,
- if blowup remains, classify it separately as capillary energy / affine-jump
  variational consistency rather than wall-contact physics.

## 8. Non-goals and rejected shortcuts

Rejected:

- Lowering CFL to hide the violation.
- Raising curvature cap.
- Clipping contact coordinates after the fact without storing the constraint.
- Adding capillary-wave-specific branches.
- Modifying the velocity wall hook as the primary fix.

Allowed:

- Projection onto the constrained geometry manifold because it is the discrete
  expression of the no-slip material-interface theorem.

## 9. SOLID audit

[SOLID-X] No violation in this design.  The new responsibility is a geometry
constraint service, not a PPE or capillary-wave runner feature.  Existing
operators should depend on a small `WallContactSet` interface rather than on
capillary-wave config details.
