# CHK-RA-CH14-AO-FASTVOL-038 - AO-Fast YAML Solver Policy

## User Request

Chapter 14 YAML must be able to state whether the active geometry projection
uses DC only, PCG only, or DC with explicit fallback to PCG. Convergence
conditions must also be configurable.

## Design Decision

Keep `interface.state_space: active_geometry_capillary` as the simple state
carrier selection. Put numerical projection policy under:

```yaml
numerics:
  projection:
    active_geometry:
      solver:
```

This keeps the parser-owned active geometry contract separate from the solver
policy chosen by the experiment YAML.

## YAML Contract

Admitted solver schemes are exactly:

- `pcg`: active PCG/Newton only; no DC fallback.
- `dc`: residual-monotone DC only; no PCG fallback.
- `dc_then_pcg`: residual-monotone DC first, then explicit fallback to active
  PCG/Newton on listed triggers.

Convergence controls:

- `convergence.norm`
- `convergence.absolute_tolerance`
- `convergence.relative_tolerance`
- `convergence.max_iterations`
- `pcg.tolerance`
- `pcg.max_iterations`
- `pcg.roundoff_floor`
- `dc.tolerance`
- `dc.max_iterations`
- `dc.relaxation`

Fail-closed checks:

- `scheme: dc` rejects `pcg` and `fallback` blocks.
- `scheme: pcg` rejects `dc` and `fallback` blocks.
- `scheme` accepts no hidden aliases such as internal implementation names.
- `convergence.tolerance` is rejected as ambiguous; use
  `convergence.absolute_tolerance`.
- `pcg.roundoff_floor` must be no larger than `pcg.tolerance`.
- `dc.relaxation` must be in `(0, 1]`.
- Runtime contract preserves `convergence.norm`, solver tolerances, iteration
  limits, fallback target, and fallback triggers.

## Checked-In YAML

All checked-in Chapter 14 production YAMLs currently declare `scheme: pcg` with
explicit PCG and convergence tolerances. `dc` and `dc_then_pcg` remain admitted
research configurations but are never implicit.

## Validation

- `git diff --check` PASS.
- `make lint-ids` PASS.
- Remote `make test PYTEST_ARGS='-k config_state_space -q'` PASS
  (`38 passed, 723 deselected`).
- Remote `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS
  (`76 passed, 685 deselected`).
- Remote `make test PYTEST_ARGS='twophase/tests/test_ns_pipeline_fccd.py -q'`
  PASS (`728 passed, 33 skipped`).

## SOLID / Scope

[SOLID-S] Parser UX, runtime contract validation, checked-in YAML examples, and
tests remain separate responsibilities.

[SOLID-X] No physical parameter, CFL change, damping, smoothing, curvature cap,
FD/WENO/PPE fallback, dense runtime fallback, hidden CPU fallback, implicit
PCG/DC fallback, experiment result, merge into main, or branch deletion was
introduced.
