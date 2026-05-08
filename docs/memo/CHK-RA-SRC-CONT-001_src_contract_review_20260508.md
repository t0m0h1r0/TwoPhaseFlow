# CHK-RA-SRC-CONT-001 src contract review memo

Date: 2026-05-08

Branch/worktree: `ra-src-contract-review-20260508` at `.claude/worktrees/ra-src-contract-review-20260508`

## Scope

User instruction requested ResearchArchitect review of `src/` against paper, docs, and existing CHK memos, with special focus on A3 traceability, physical signs/jumps/boundary conditions/discretization contracts, GPU-first behavior, and NumPy/CuPy parity.

Follow-up instruction: stale/obsolete code is out of scope. This memo therefore treats retired reference implementations as audit context only and reviews active production routes/factories for whether retired code still leaks into runtime.

Primary contract sources checked:

- `paper/sections/09b_split_ppe.tex`: pressure jump convention `j_gl = p_g - p_l = -sigma kappa_lg`, affine pressure-jump PPE, and variational pressure-force contract.
- `docs/01_PROJECT_MAP.md` section 8: retired direct-import-only classes, including `PPESolverIIM` and `ConsistentIIMReprojector`.
- `docs/memo/CHK-RA-SRC-001_src_paper_audit_20260430.md`: prior src paper-audit findings and default/production preset policy.
- Recent CH14 Hodge/Riesz CHKs recorded in `docs/02_ACTIVE_LEDGER.md`: pressure-component Hodge and GPU sparse solve contracts.

## Finding And Fix

### Active runtime still constructed retired IIM corrector

`src/twophase/simulation/ns_runtime_bootstrap.py` still imported and constructed `IIMStencilCorrector(grid, mode="hermite")` unconditionally, then passed it into `build_ns_runtime_components`.

Because the user excluded stale code from this review, the retired IIM implementation itself was not changed. The active bug was the remaining runtime dependency: current docs mark `ConsistentIIMReprojector`/IIM-style paths as retired direct-import-only reference code, and active reprojector modes are expected to avoid constructing that host-oriented helper unless a registered route explicitly needs it.

Root fix:

- Removed the active bootstrap import/construction of `IIMStencilCorrector`.
- Set `NSRuntimeBootstrapArtifacts.reproj_iim` to `None`.
- Added regression coverage proving runtime bootstrap does not construct or pass a retired IIM corrector for active modes.

Code commit: `0afe13d7 fix(simulation): drop retired IIM bootstrap dependency`

## Non-Findings / Contract Checks

- Active affine jump sign remains paper-consistent: `pressure_jump_gas_minus_liquid = -sigma * kappa_lg`, matching `paper/sections/09b_split_ppe.tex`.
- Active closed-interface Riesz/Hodge path remains face-native and jump-aware: capillary pressure component cochains are passed into PPE and corrector evaluation through pressure-jump context rather than by post-hoc host-side dense fallback.
- Retired IIM source/tests contain old-sign/reference behavior, but they are outside this task by user instruction and by `docs/01_PROJECT_MAP.md` section 8. They were not modified.
- Library defaults still preserve legacy/raw compatibility in places, while CH14 production configs explicitly select `variational_adjoint`, `variational_operator`, and `pressure_component_hodge`. This matches the prior CHK policy that paper/production semantics are selected through explicit validated presets/configs rather than by silently changing broad defaults in this pass.

## GPU / NumPy-CuPy Audit

The implemented fix removes an unnecessary active dependency on retired host-oriented IIM construction. It does not add CPU/GPU transfers, dense conversions, host-side mask construction, NumPy calls on CuPy arrays, scalar synchronization, or Python-loop hot paths.

Targeted active GPU smoke passed for current CuPy routes:

- `src/twophase/tests/test_gpu_smoke.py`
- `src/twophase/tests/test_fccd_gpu_smoke.py`
- `src/twophase/tests/test_uccd6_gpu_smoke.py`

Result: `23 passed in 1.11s` on the remote workspace.

## Side-Effect Audit

Recent overlapping changes:

- CH14 pressure-component Hodge/Riesz and GPU sparse solve work.
- RA src review refactors around pressure-stage context and face-boundary helpers.
- Prior `CHK-RA-SRC-001` paper-audit note that production pressure-force contracts are explicit route/config contracts.

Why this change does not perturb recent experiments:

- No solver equation, capillary force, pressure jump, corrector, transport, reinit, CFL, or boundary-condition logic changed.
- Current registered active modes do not require the retired IIM corrector; existing tests already assert the retired `consistent_iim` route is not registered.
- The new regression asserts the runtime artifact remains `None` for the retired helper, preventing accidental reactivation.

Additional verification recommended only if an old direct-import experiment intentionally uses retired IIM reference code; such experiments are outside the current active-route scope and should be labeled as reference/stale before use.

## Paper Reflection

No paper text change is required.

Reason:

- The paper contract in `paper/sections/09b_split_ppe.tex` remains unchanged and already describes the active affine-jump/variational pressure framework.
- The implementation change removes a stale active dependency and aligns code with `docs/01_PROJECT_MAP.md` section 8 retirement status. This is an implementation hygiene/traceability correction, not a scientific or numerical contract change.

Implementation memo only: this memo records the route-hygiene correction and side-effect audit.

## Validation

Remote-first targeted attempt:

- `make test PYTEST_ARGS='twophase/tests/test_ns_pipeline_fccd.py::test_runtime_bootstrap_does_not_construct_retired_iim_corrector twophase/tests/test_ns_pipeline_fccd.py::test_retired_iim_reprojector_direct_import_does_not_register_route -q'`
- Initial wrapper could not reach remote and local fallback failed because bare `python` is absent.

Remote validation with SSH agent:

- `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='twophase/tests/test_ns_pipeline_fccd.py::test_runtime_bootstrap_does_not_construct_retired_iim_corrector twophase/tests/test_ns_pipeline_fccd.py::test_retired_iim_reprojector_direct_import_does_not_register_route -q'`
- Wrapper expanded to full test suite: `641 passed, 33 skipped in 82.60s`.

GPU targeted validation:

- `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ssh python 'cd /root/TwoPhaseFlow && .venv/bin/python -m pytest src/twophase/tests/test_gpu_smoke.py src/twophase/tests/test_fccd_gpu_smoke.py src/twophase/tests/test_uccd6_gpu_smoke.py --gpu -q'`
- Result: `23 passed in 1.11s`.

Diff hygiene:

- `git diff --check`: PASS.
