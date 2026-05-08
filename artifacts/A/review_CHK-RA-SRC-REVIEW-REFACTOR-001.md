# CHK-RA-SRC-REVIEW-REFACTOR-001 - Source Refactor Review Loop

Date: 2026-05-08

Scope: `src/twophase/` architecture/code-quality review under ResearchArchitect, with root-cause refactors for all MAJOR-or-higher findings.

## User Trigger

User requested a new worktree, coherent commits while progressing, no merge to `main` without explicit instruction, and repeated review/fix rounds over `src/` until no MAJOR-or-higher finding remains or the loop exceeds 10 rounds.

## Verdict

MAJOR fixed. Stop condition reached at Round 4: no active MAJOR-or-higher refactor finding remains in the audited `src/twophase/` hotspots.

## Rounds

- Round 1 MAJOR fixed: `simulation/ns_step_services.py` embedded face-native predictor assembly inside `compute_ns_predictor_stage`, mixing stage integration with face-boundary policy, interface-band masking, full-band state transforms, and residual buoyancy force construction. The responsibilities are now separated into `simulation/face_boundary.py` and `simulation/ns_predictor_face_state.py`; predictor orchestration calls the extracted helpers. Commit: `041a13cc`.
- Round 2 MAJOR fixed: `solve_ns_pressure_stage` mixed predictor RHS construction, closed-interface pressure-jump context setup, affine face-pressure history plumbing, capillary flux evaluation options, and diagnostics. The pressure-stage subcontracts are now represented by `PressureJumpStageContext` plus targeted helper functions in `simulation/ns_step_services.py`. Commit: `89464aa6`.
- Round 3 MAJOR fixed: `parse_run_operator_settings` handled PPE, surface-tension, closed-interface, viscous, predictor-assembly, and coupled time-scheme validation in one parser, making config contract drift too easy. Operator setting parsing is now split into cohesive section helpers while preserving the external YAML contract. Commit: `fa2468ac`.
- Round 4 rescan: no MAJOR-or-higher issue found. Remaining large functions are either high-level orchestration (`run_simulation`), already-decomposed numerical stage drivers (`compute_ns_predictor_stage`, `solve_ns_pressure_stage`, `correct_ns_velocity_stage`), configuration aggregation, diagnostics, or math kernels where further splitting would need a separate algorithm/API design task rather than a safe refactor in this loop.

## Validation

- `git diff --check`: passed.
- Remote-first `make test`: attempted in the sandbox; remote was unavailable and Makefile local fallback failed because `python` is absent. Escalation for remote execution was rejected because the target would sync the workspace to an unverified remote with `--delete`, so validation continued with the safer local workspace venv.
- Targeted predictor/face-boundary tests: `67 passed`.
- Targeted config parser tests: `87 passed, 3 skipped`.
- Full local CPU suite with workspace venv: `640 passed, 33 skipped`.

## SOLID

[SOLID-X] [SOLID-S] No C1 violation found. Refactors reduce responsibility overload and duplicate boundary/config plumbing without changing solver equations, capillary force, pressure/DCCD/FCCD/UCCD scheme behavior, transport, reinit physics, damping/CFL workaround, smoothing, curvature cap, benchmark branch, blanket projection, or fallback path. No tested implementation was deleted.
