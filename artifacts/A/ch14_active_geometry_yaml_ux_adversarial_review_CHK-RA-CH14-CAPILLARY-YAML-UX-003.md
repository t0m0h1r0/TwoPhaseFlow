# CHK-RA-CH14-CAPILLARY-YAML-UX-003 - adversarial YAML/UX design review

Date: 2026-05-12
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: review the design adversarially to minimize risk, then eliminate
the issues found.

Review target: the Chapter 14 active-geometry capillary YAML front door and
parser preset introduced by CHK-RA-CH14-CAPILLARY-YAML-UX-001/002.

## Adversarial Findings

### F1 - Hidden Detailed-Knob Back Door

Status: fixed.

The prior parser rejected legacy scheme names, but a YAML author could still
write:

```yaml
interface:
  state_space:
    scheme: active_geometry_capillary
    compatibility:
      projection:
        solver:
          fallback:
            policy: auto
```

The parser would then merge user details into the internal preset and rely on
deeper fail-close checks.  That was correct enough for safety but wrong for UX:
the front door still looked like a solver-control surface.

Fix: `interface.state_space.scheme='active_geometry_capillary'` now accepts
only the `scheme` key.  Any `kind`, `conserved_variable`, `normalized_view`,
`gauge`, or `compatibility` key fails immediately with a parser-owned-contract
message.

### F2 - Kind-Only Activation Ambiguity

Status: fixed.

`kind: geometric_cell_fraction` is an internal expanded classification, not a
user-facing route name.  Letting it activate the route would recreate the old
mental model with a new spelling.

Fix: kind-only activation fails closed.  The only user-facing activation is:

```yaml
interface:
  state_space:
    scheme: active_geometry_capillary
```

### F3 - Historical Alias Drift

Status: fixed.

The parser now rejects `ao_fast`, `ao-fast`, `active-geometry-capillary`, and
`geometric_cell_fraction` as scheme values.  This avoids silently normalizing
old documentation or local draft habits into the current paper route.

## Residual Risk

Internal runtime-contract modules and test helpers still contain historical
`ao_fast` names.  They are not user-facing YAML/UX names.  Renaming them is a
larger API migration and should be a separate mechanical slice if desired.

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  27 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 674 deselected

[SOLID-X] Parser front-door tightening plus tests/docs only.  No runtime
physics, solver equation, physical parameter, CFL, damping, smoothing,
curvature cap, FD/WENO/PPE fallback, dense runtime fallback, hidden CPU
fallback, experiment result, merge into main, or branch deletion was introduced.
