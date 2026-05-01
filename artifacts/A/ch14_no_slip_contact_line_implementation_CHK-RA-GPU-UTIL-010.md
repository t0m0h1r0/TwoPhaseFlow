# CHK-RA-GPU-UTIL-010 — No-slip wall-contact constraint implementation

Date: 2026-05-01
Scope: generic wall-contact constraints for CLS geometry, Ridge–Eikonal
reinitialization, dynamic grid rebuild/remap, and ch14 capillary-wave probes

## Summary

Implemented the CHK-RA-GPU-UTIL-009 design: a wall-attached interface under a
stationary no-slip wall now carries explicit pinned contact coordinates.  These
coordinates are detected from the initial `psi` wall trace and propagated as a
generic `WallContactSet`, not as capillary-wave-specific logic.

The implementation enforces the no-slip contact invariant:

```math
C(t)=C(0)
```

for the pinned contact branch, while leaving any later additional wall
crossings visible as diagnostics rather than hiding them.

## Code changes

- Added `src/twophase/levelset/wall_contact.py`
  - `WallContact`
  - `WallContactSet`
  - `detect_from_psi(...)`
  - pinned wall-trace imposition
  - pinned-contact FMM seeds
  - contact-excluded mass-correction masks
- Connected Ridge–Eikonal:
  - pinned contacts added to ridge Gaussian points,
  - nearest-node zero seeds passed to CPU/GPU FMM,
  - contact band excluded from mass correction,
  - wall half-contour re-imposed after reinit.
- Connected dynamic grid rebuild:
  - pinned contacts included in the grid monitor,
  - remapped `psi` receives pinned wall trace,
  - global mass correction uses a free mask excluding pinned contact nodes.
- Connected runtime:
  - `runner.run_simulation(...)` detects initial wall contacts after IC build,
  - `TwoPhaseNSSolver.set_wall_contacts(...)` propagates constraints to
    geometry services.

## Validation

Local:

```bash
/Users/tomohiro/Downloads/TwoPhaseFlow/.venv/bin/python3 \
  -m pytest src/twophase/tests/test_ridge_eikonal.py -q
```

Result: `22 passed, 2 skipped`.

Remote targeted:

```bash
make test PYTEST_ARGS="-k wall_contact -q"
make test PYTEST_ARGS="-k pinned_contact -q"
```

Results: `3 passed`, then `2 passed`.

Remote broad `make test PYTEST_ARGS="twophase/tests/test_ridge_eikonal.py -q"`
expanded to the full suite because `remote.sh test` always prepends
`twophase/tests`; the new wall-contact tests passed inside that run.  The
broad suite still failed in pre-existing unrelated groups: missing ch13 YAMLs,
small-grid CCD wall operator tests, local-eps+CSF validation tests, FCCD
preconditioner validation, IIM ridge precision, and split y-flip threshold.

## Experiment checks

### Short probe

`_probe_contact_baseline`, N=32, `T=0.15`, `schedule=1`, reinit every 20:

- pinned contact first/last: `0.5100895692511684 -> 0.5100895692511684`
- nearest pinned-contact drift: `0.0`
- steps: `25`

This confirms that the production geometry route now preserves the stored
no-slip contact coordinate over the reinit + dynamic-grid path.

### N32/T1

`ch14_capillary_n32_t1`:

- completed `t=1.0`, `steps=138`
- pinned contact first/last: `0.5100895692511684 -> 0.5100895692511684`
- nearest pinned-contact drift: `0.0`
- final amplitude: `0.014259382529662634`
- max divergence: `8.955660560831108e-05`
- `kappa_max` still reaches cap `5.0`

### N32/T25

`ch14_capillary_n32_t25`:

- completed `t=25.0`, `steps=3080`
- no BLOWUP
- wall-contact pinned branch first/last:
  `0.5100895692511684 -> 0.5100895692511684`
- nearest pinned-contact drift: `0.0`
- final amplitude: `0.15110207462990333`
- max amplitude: `0.1531095296438057`
- final kinetic energy: `0.009540524758845155`
- max kinetic energy: `0.009627343934316721`
- max volume drift: `0.00506190787376452`
- max divergence: `2.438614738661804e-04`
- `kappa_max` still reaches cap `5.0`

Additional wall crossings appear late in the run; e.g. at `t=25.0` the side
wall crossings include approximately `[0.33278, 0.48530, 0.51009]`.  The
original pinned contact is preserved exactly, but the extra crossings indicate
remaining high-mode / curvature-energy issues rather than contact-line drift.

## Interpretation

The former N32/T25 failure at `t=16.3947` was not reproduced after contact
pinning; the run reaches `T=25`.  The wall-contact invariant is therefore a
real stabilizing correction, not a cosmetic post-process.

The remaining concerns are separate:

1. `kappa_max` still saturates at the cap.
2. Additional wall crossings develop late.
3. Amplitude grows to `O(1e-1)`.

These should be treated as capillary geometry/energy consistency issues, not
as no-slip contact-line implementation failures.

## SOLID audit

[SOLID-X] No violation found.  The new responsibility is isolated in
`levelset.wall_contact`; solver/runtime code only detects and threads the
generic constraint object.  PPE/DC solver code is untouched.
