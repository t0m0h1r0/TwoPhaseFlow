# CHK-RA-CH14-AO-FASTVOL-040 - AO-Fast pressure-reaction split implementation

Date: 2026-05-13
Branch/worktree: `codex/ra-ch14-capillary-ao-run-20260512` at `.claude/worktrees/codex-ra-ch14-capillary-ao-run-20260512`

## Scope

User request: implement the AO-Fast fix completely, based on the prior
SP-AO/active-geometry capillary analysis.

## Theory Gate

The fixed runtime equation is the face-work split

```text
r_sigma          = geometric bundle capillary source
corrected_source = r_sigma - B mu
pressure_range   = L_A(corrected_source)
balanced_drive   = corrected_source - pressure_range
```

Here `B` is the declared cell-volume reaction direction and `L_A` is the
active pressure-adjoint range induced by the same `div_op`/`ppe_solver` used by
the PPE.  The nodal Young-Laplace multiplier remains a diagnostic for the
bundle Riesz source; it is not the runtime pressure reaction.

## Fixes

1. Added `src/twophase/simulation/geometric_capillary_reaction_split.py`.
   It wraps the existing pressure-adjoint component saddle theorem and returns
   predictor, pressure-reaction, and balanced face accelerations with their
   weighted norms.
2. GPU capillary materialisation no longer sets
   `pressure_face = capillary_face`.  It now builds a raw AO capillary source,
   sets pressure reaction faces to zero, and marks non-static packets as
   `pressure_reaction_projection_pending`.
3. Replaced the diagonal Schur capillary source with a fixed-iteration
   device-resident PCG loop, avoiding residual-dependent host control in the
   source construction.
4. The common admission gate is now two-stage: the interface stage may pass a
   pending non-static packet only to the downstream splitter; predictor/PPE
   require the completed `pressure_component_hodge_split`.
5. `compute_ns_predictor_stage` now constructs the pressure-adjoint split
   before applying the AO predictor increment.  The predictor receives
   `corrected_source`, the PPE/corrector receive `pressure_range`, and the
   application packet records `balanced_drive`.
6. Split-static packets are reclassified before predictor use, suppressing
   legacy pressure-jump/CSF ownership while keeping the transported geometric
   q-state committable.
7. Added regression tests for the split algebra and the pending/completed AO
   admission boundary.

## Validation

- `python3 -m py_compile` PASS for touched runtime/test files.
- `git diff --check` PASS.
- Remote `make test PYTEST_ARGS='twophase/tests/test_geometric_capillary_reaction_split.py twophase/tests/test_config_state_space.py -q'` ran the repository suite and PASSed: `732 passed, 33 skipped`.
- Remote AO-Fast capillary-wave probe PASS:
  `make run EXP=experiment/ch14/diagnose_ao_gpu_theory_probe.py ARGS='--config experiment/ch14/config/ch14_capillary.yaml --steps 1'`.
  It advanced one step with nonzero AO capillary drive and no fail-close.

## SOLID / A3 Review

- [SOLID-S] The pressure-reaction split lives in its own simulation-layer
  service; geometry still owns only the bundle covector/source.
- [SOLID-D] The split depends on `div_op`, `ppe_solver`, and pressure-flux
  kwargs rather than concrete PPE classes.
- [PR-5] No FD/WENO, CFL, offset, damping, smoothing, curvature cap, dense CPU
  fallback, or hidden component-Hodge fallback was introduced.  The fix follows
  the SP-AO face-work projection equation.
