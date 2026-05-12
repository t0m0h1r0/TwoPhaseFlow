# CHK-RA-CH14-CAPILLARY-YAML-UX-002 - strict active-geometry YAML front door

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: do not preserve legacy compatibility; usability matters more.

## Decision

The active-geometry capillary state space has one user-facing YAML entry:

```yaml
interface:
  state_space:
    scheme: active_geometry_capillary
```

The parser rejects old route names such as `ao_fast`, hyphenated AO variants,
and `scheme: geometric_cell_fraction`.  It also rejects `kind:
geometric_cell_fraction` as a user front door.  That `kind` value remains only
the internal expanded classification after the canonical scheme is accepted.

This keeps the visible YAML small and removes the mental burden of deciding
which historical spelling means the current paper route.

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  25 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 672 deselected

[SOLID-X] This is a parser front-door and documentation cleanup only.  No
runtime physics, solver equation, physical parameter, fallback, experiment
result, merge into main, or branch deletion is introduced.
