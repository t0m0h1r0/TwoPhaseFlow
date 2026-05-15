# CHK-RA-CH14-CAPILLARY-YAML-UX-005 - active-geometry parser logic fixes

Date: 2026-05-13
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: fix the issues found by the adversarial review of YAML/UX and
main parser logic.

## Theoretical contract

The active-geometry capillary route has one user-facing choice:

```yaml
interface:
  state_space: active_geometry_capillary
```

The expanded geometric cell-fraction state is a parser-owned contract.  It is
not a second YAML surface for q/theta/phi, gauge, active projection, GPU storage,
solver, or fallback knobs.  This matches the SP-AO/AO-Fast split: experiments
select the admitted state-space scheme, while the implementation owns the
mathematical bundle/projection invariants required for that scheme.

## Fixes

1. Active geometry now accepts only scalar
   `interface.state_space: active_geometry_capillary`.  The mapping form
   `state_space: {scheme: active_geometry_capillary}` is rejected even when it
   has no extra keys.  This prevents users from reading the mapping as an
   extensible solver-control surface.
2. Parser-owned keys under active geometry are rejected with a scalar-form
   message and explicit key names.
3. Contradictory mappings such as
   `state_space: {scheme: diffuse_cls, kind: geometric_cell_fraction}` now fail
   closed instead of being silently rewritten to diffuse CLS.

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  29 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 676 deselected

[SOLID-X] Parser front-door logic and tests only.  No runtime physics, solver
equation, physical parameter, CFL, damping, smoothing, curvature cap,
FD/WENO/PPE fallback, dense runtime fallback, hidden CPU fallback, experiment
result, merge into main, or branch deletion was introduced.
