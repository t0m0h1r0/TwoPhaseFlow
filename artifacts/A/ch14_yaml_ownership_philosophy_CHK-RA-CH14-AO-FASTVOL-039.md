# CHK-RA-CH14-AO-FASTVOL-039 - Chapter 14 YAML Ownership Philosophy

## User Request

Clarify, across the whole YAML surface, which parameters should be directed by
the user and incorporate the philosophy into YAML where useful.

The attempted broad `numerical_stack: ch14_active_geometry_capillary` direction
was rejected because it hides too much in code. Final decision: do not add a
stack preset. Keep scheme selection, parameter selection, and initial-state
definition explicit in YAML.

## Final Design

The YAML is the experiment contract.

User-owned choices:

- Scheme selection: `interface.state_space`, interface transport,
  reinitialization, momentum term schemes, gravity formulation, PPE
  operator/solver, and `projection.active_geometry.solver.scheme`.
- Parameter selection: grid resolution/distribution, physics constants,
  CFL/final-time controls, tolerances, iteration limits, relaxation factors,
  and fallback triggers.
- Initial/boundary state: `initial_condition`, `initial_velocity`, and
  `boundary_condition`.
- Output and diagnostics.

Code-owned duties:

- Validate combinations against the paper contract.
- Normalize local aliases where already admitted.
- Derive internal runtime-only contracts such as q/theta/phi handoff metadata,
  active-cache implementation markers, GPU fail-close guards, dense-reference
  test boundaries, and geometry ledgers.

Code must not choose a broad production stack for the user.

## Changes

- Updated `experiment/ch14/config/README.md` with the ownership philosophy and
  an explicit warning against a broad `numerical_stack` key.
- Added a short ownership comment to all five checked-in Chapter 14 YAMLs.
- Left the actual scheme and parameter surface explicit in YAML, including
  active-geometry solver policy, PPE settings, transport/tracking settings,
  capillary source/reaction settings, and initial-condition definitions.

## Validation

- `git diff --check` PASS.
- `make lint-ids` PASS.
- Remote `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS
  (`76 passed, 685 deselected`).

## SOLID / Scope

[SOLID-X] Documentation/YAML-comment clarification only; no parser preset,
production source path activation, physical parameter, CFL change, damping,
smoothing, curvature cap, FD/WENO/PPE fallback, dense runtime fallback, hidden
CPU fallback, implicit PCG/DC fallback, experiment result, merge into main, or
branch deletion introduced.
