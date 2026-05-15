# CHK-RA-CH14-AO-FASTVOL-016 - AO-Fast runtime fail-close fixes

Date: 2026-05-13
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: eliminate the AO-Fast main-logic problems found by the
adversarial review.

## Theory Gate

SP-AO non-static capillary drive is the face-work residual

```text
r_sigma - Pi^{M_f}_{R_p(q_T)} r_sigma
```

The Young-Laplace pressure-Hodge residual is a geometry-layer identity
diagnostic.  It is not itself the admitted runtime pressure-reaction subspace.
Therefore the current code must not route non-static diagnostic pressure faces
into predictor/PPE/corrector as if they were the final pressure reaction.

## Fixes

1. AO-Fast runtime contract now verifies the parser-owned implementation
   contract: `active_cached`, `dense_reference: test_only`, `gpu_required:
   true`, and `fallback_policy: none`.
2. Solver construction from active-geometry YAML forces `use_gpu=True`, so the
   configured AO-Fast route cannot silently run on the dense CPU backend.
3. Direct solver construction with `advection_scheme='geometric_swept_volume'`
   now rejects CPU backend initialization.  This closes the non-YAML escape
   hatch.
4. Added a common runtime gate:
   `validate_geometric_runtime_capillary_application_admitted`.  Only
   pressure-exact static packets with zero pressure-balanced drive may proceed.
   Non-static packets fail closed until an admitted pressure-reaction projection
   `R_p(q_T)` is implemented.
5. The NS pipeline calls the common admission gate after GPU-specific checks and
   before publishing the downstream conservative/capillary certificate, so
   unadmitted AO packets cannot reach predictor, PPE, or corrector stages.

## Validation

- `git diff --check` PASS
- `make lint-ids` PASS
- `make test PYTEST_ARGS='-k config_state_space -q'` PASS:
  31 passed, 723 deselected
- `make test PYTEST_ARGS='-k config_io_fccd -q'` PASS:
  76 passed, 678 deselected
- `make test PYTEST_ARGS='twophase/tests/test_ns_pipeline_fccd.py -q'` PASS:
  721 passed, 33 skipped

[SOLID-X] Runtime contract/gate fixes only.  No physical parameter, CFL,
damping, smoothing, curvature cap, FD/WENO/PPE fallback, dense runtime fallback,
hidden CPU fallback, implicit PCG/DC fallback, experiment result, merge into
main, or branch deletion was introduced.
