# CHK-RA-CH14-STATE-SPACE-IMPL-001: Constrained Face-State Space Implementation Slice

## Question

Can the SP-AN state-space reformulation be implemented without promoting an
unverified production solver, while preserving GPU-first design and providing
cheap gates for the next proof step?

## Implemented Scope

This slice implements the matrix-free building blocks for the constrained
face-state route:

```text
P_w f     = metric wall retraction into F_w=ker C_w
G_w p     = P_w G_A p
operator  = D_h P_w G_A
```

The production PPE solve is not replaced yet.  That is intentional: SP-AN
requires S1--S6 gates before long simulations.

## Code Changes

- `src/twophase/simulation/boundary_hodge.py`
  - added `face_mass_inner_product` for the current transported face-density
    metric used by `P_w`;
  - added `restricted_pressure_fluxes`, which composes the active production
    `div_op.pressure_fluxes(...)` with the wall metric retraction
    `project_wall_trace`;
  - kept the implementation backend-native: no dense matrices or host fallback
    in the runtime helper.

- YAML/UX:
  - added boundary-Hodge state-space fields:

```yaml
numerics:
  projection:
    boundary_hodge:
      mode: off
      state_space: constrained_face
      wall_trace: reconstruct_nodes
      wall_retraction: metric_projection
      metric: transported_face_mass
      pressure_pairing: restricted_variational_adjoint
      gate: diagnostic
```

  - `state_space: constrained_face` requires
    `pressure_pairing: restricted_variational_adjoint`;
  - `mode: wall_trace_projection` is rejected when combined with
    `state_space: constrained_face`, because it is the old post-pressure repair.

- `experiment/ch14/config/ch14_rising_bubble.yaml`
  - now records the SP-AN state-space contract while leaving the production
    solver `mode: off` until the restricted PPE solve is validated.

## Efficient Verification

The verification intentionally avoids long rising-bubble runs.

### Unit / Manufactured Gates

Added tests in `src/twophase/tests/test_boundary_hodge.py`:

```text
P_w idempotence
P_w M_f-self-adjointness
C_w P_w G_A p = 0
rank(D_h P_w G_A) = rank(D_h | F_w) on full-wall topology
```

The rank gate is assembled densely only inside the small unit test.  The
runtime helper remains matrix-free and backend-native.

### YAML / Builder Gates

Updated config and solver-construction tests assert that
`ch14_rising_bubble.yaml` carries:

```text
state_space = constrained_face
wall_retraction = metric_projection
pressure_pairing = restricted_variational_adjoint
```

## Validation Result

Remote-first validation command:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test \
  PYTEST_ARGS='twophase/tests/test_boundary_hodge.py \
  twophase/tests/test_config_io_fccd.py::test_ch14_rising_bubble_yaml_loads_execution_stack \
  twophase/tests/test_ns_pipeline_fccd.py::test_ch14_rising_bubble_yaml_builds_solver -q'
```

The Makefile wrapper expanded to the full CPU suite:

```text
646 passed, 33 skipped in 42.91s
```

`git diff --check` also passed.

## Production Decision

Do not enable a production restricted PPE solve yet.  The implemented helpers
establish S1--S5 for full-wall topology and provide the GPU-first operator
composition needed for the next step.  Remaining work:

```text
1. add matrix-free solve for D_h P_w G_A p = D_h P_w f_dag,
2. fail-close mixed periodic-wall until quotient rank gate passes,
3. integrate state publication gates C_w f, D_h f, u=R_h f, m=rho u,
4. run one-step rising-bubble S6 before short N32x64 runs.
```

## Negative Knowledge Preserved

This slice does not revive the rejected routes:

```text
post-pressure wall-only projection,
nodal wall clamp,
boundary-face zeroing,
generic D_h^T pressure bypass,
dense CPU KKT production,
penalty slip,
damping/CFL/smoothing/DCCD/UCCD suppression.
```
