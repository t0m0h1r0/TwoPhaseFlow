# CHK-RA-CODE-GPU-001 — paper/code/GPU strict review

Date: 2026-05-16
Branch: `codex/ra-code-paper-gpu-review-20260516`
Worktree: `.claude/worktrees/codex-ra-code-paper-gpu-review-20260516`
Mode: review/check/consideration only. No production source code edits.

## Review Verdict

P0 / blocker finding: none in the reviewed active-geometry, HFE, DC, and GPU-first implementation route.

P1 / major open front: wall-bounded `constrained_face` production route is still not a true restricted PPE solve `D_h P_w G_A`; the code currently routes constrained wall face state to a full-face PPE plus post-corrector/diagnostic boundary Hodge path. This is consistent with the wiki's known open front, but the paper must not imply that the full restricted operator is already the standard production solve.

P2 / paper-code wording mismatch: Chapter 14 common numerical configuration says `FCCD 保存形界面輸送 + TVD--RK3`, while the checked-in active-geometry Ch14 YAMLs use `interface.transport.spatial: geometric_swept_volume` for the q-owned interface transport. The code/YAML route appears aligned with the active-geometry contract; the paper wording is stale or ambiguous unless it explicitly distinguishes the standard CLS `psi` transport route from active-geometry q transport.

GPU-first verdict: the reviewed active-geometry and PPE/DC path is generally GPU-first: parser gates reject dense runtime fallback, active geometry uses backend arrays and explicit scalar packet boundaries, finite-stratum kernels are explicit, and sparse low-order solves have prepared CuPy SpSM flows. Remaining scalar host boundaries look bounded and report/fail-close oriented, not hidden production CPU fallbacks.

## Findings

### P1: `constrained_face` is not yet a true restricted PPE solve

Evidence:

| Source | Observation |
|---|---|
| `docs/wiki/cross-domain/WIKI-X-053.md` | Current wiki says the remaining open front is the full restricted PPE `D_h P_w G_A`; the latest boundary-state fix does not substitute for that missing operator. |
| `src/twophase/simulation/boundary_hodge.py:17-19` | `restricted_pressure_fluxes` is documented as a diagnostic/proof operator until the PPE solve itself changes to `D_h P_w G_A`. |
| `src/twophase/simulation/boundary_hodge.py:488-490` | Function docstring explicitly says it does not solve the restricted pressure equation. |
| `src/twophase/simulation/config_run_builder_sections.py:319-322` | `boundary_hodge.state_space == "impermeable_face"` maps to `boundary_face_space="impermeable_face"`; every other state, including `constrained_face`, maps to `full_face`. |
| `src/twophase/simulation/ns_runtime_config.py:305-310` | Runtime accepts only `full_face` and `impermeable_face`; `constrained_face` is not an executable PPE space. |
| `src/twophase/tests/test_config_io_fccd.py:574-578` | Tests currently encode the mapping: non-free-slip `constrained_face` expects `boundary_face_space == "full_face"`. |

Impact:

If the paper says the wall-bounded standard path already solves the constrained-wall pressure reaction in the restricted face space, that is a root-level paper/code mismatch. If the paper says this is a diagnostic or known open contract gap, then code and paper are consistent.

Recommended refactor direction, when code changes are authorized:

1. Add an executable restricted pressure operator `K_w = D_h P_w G_A` with the same metric retraction used by boundary Hodge.
2. Route `boundary_face_space="constrained_face"` through `NSRuntimeConfig`, `PPEBuilder`, affine jump coefficient assembly, DC low-order base, and diagnostics.
3. Make production wall-bounded `constrained_face` fail closed unless the restricted PPE operator, affine context, and wall trace projector are all present.
4. Add tests for Green identity, wall trace annihilation, high/low DC operator consistency, config routing, and at least one Ch14 wall-bounded production YAML.
5. Do not mask this with CFL, damping, smoother, solver-family substitution, or post-corrector projection-only workarounds.

### P2: Chapter 14 common transport wording does not match active-geometry YAML

Evidence:

| Source | Observation |
|---|---|
| `paper/sections/14_benchmarks.tex:39` | Common Ch14 stack says `FCCD 保存形界面輸送 + TVD--RK3`. |
| `experiment/ch14/config/ch14_oscillating_droplet.yaml:77` | Uses `spatial: geometric_swept_volume`. |
| `experiment/ch14/config/ch14_static_droplet.yaml:81` | Uses `spatial: geometric_swept_volume`. |
| `experiment/ch14/config/ch14_rayleigh_taylor.yaml:89` | Uses `spatial: geometric_swept_volume`. |
| `experiment/ch14/config/ch14_rising_bubble.yaml:94` | Uses `spatial: geometric_swept_volume`. |
| `experiment/ch14/config/ch14_capillary.yaml:100` | Uses `spatial: geometric_swept_volume`. |
| `docs/wiki/theory/WIKI-T-169.md` and `docs/wiki/cross-domain/WIKI-X-054.md` | Active geometry owns q transport by geometric swept volume and graph HFE jump; this is not the legacy/standard CLS `psi` FCCD transport statement. |

Impact:

The current YAML route appears correct for active geometry, but the paper phrasing can be read as saying Ch14 q transport is FCCD CLS transport. That risks a false A3 chain: Equation/object `q_C` -> Discretization `geometric_swept_volume` -> Code YAML, while the paper states `FCCD` at the same interface-transport slot.

Recommended paper correction, when paper edits are authorized:

Use wording like: active-geometry q transport uses geometric swept volume with TVD--RK3; FCCD remains the pressure/PPE and standard CLS transport family where the paper explicitly discusses the `psi` route.

### P2: Remaining GPU synchronization is performance debt, not a correctness mismatch

Evidence:

| Source | Observation |
|---|---|
| `docs/wiki/code/WIKI-L-043.md`, `WIKI-L-044.md`, `WIKI-L-045.md` | GPU-first policy is to remove hidden host/device boundaries first, then fuse finite-stratum operations and prepare sparse solve flows; known remaining scalar syncs are explicit debt. |
| `src/twophase/simulation/config_state_space.py:46-51` and `:338-340` | Active-geometry compatibility declares dense runtime fallback forbidden. |
| `src/twophase/simulation/geometric_phase_runtime_gpu.py:2801-2810` | Single scalar host transfer helper fails closed and directs callers to packetized scalar transfer at explicit boundaries. |
| `src/twophase/gpu_sparse_solve.py:7-41` and `:67-76` | Sparse solve path is explicitly prepared CuPy SpSM and fails when SpSM is unavailable. |
| `src/twophase/ppe/fd_direct.py:193-227` | FD direct base reuses prepared solve state and reports analysis counts. |

Impact:

No hidden CPU fallback or dense production substitute was found in the reviewed route. The remaining concern is performance architecture: scalar summaries for DC convergence, reprojector diagnostics, and time-step capacity are still boundary transfers and should remain visible as explicit packet/reporting boundaries.

## Contract Map For Future Work

| Object / contract | Current paper/wiki contract | Current implementation status |
|---|---|---|
| Active interface state | `interface.state_space: active_geometry_capillary` is scalar; parser owns q/theta/phi and compatibility knobs. | `config_state_space.py` rejects mapping forms, legacy names, and parser-owned YAML knobs; tests cover front-door failure. |
| q transport | Active geometry uses q-owned geometric swept volume; TVD--RK3 is the time integrator. | Ch14 active YAMLs use `geometric_swept_volume`; paper Ch14 common wording needs clarification. |
| Graph HFE jump | Column-height graph endpoint owns HFE pressure jump; jump is not smooth pressure history. | `geometric_phase_runtime_gpu.py` records `column_height_graph_hfe`; tests cover no pressure-coordinate history reuse for graph jump. |
| Capillary reaction | Pressure component Hodge / bundle virtual work route; no CSF predictor fallback for active geometry. | Parser and tests require `bundle_virtual_work` and `pressure_component_hodge` on the active path. |
| Projection face bridge | Geometric integrated face cochains must be converted exactly once to projection-native face velocities. | `ns_step_services.py` has a dedicated geometric-to-projection face pair path; tests cover projection-native complex use. |
| Defect correction | Converge by true residual against the high-order operator; no fixed iteration-count success. | `defect_correction.py` records true residuals, reports convergence, and can fail on nonconvergence. |
| Wall face state | Standard wall-bounded route should eventually solve `D_h P_w G_A`. | Open front: current executable spaces are `full_face` and `impermeable_face`; `constrained_face` remains diagnostic/post-corrector. |
| GPU execution | Backend-owned arrays; no dense runtime fallback; explicit packetized host transfers only at report/fail-close boundaries. | Reviewed route generally satisfies this. Remaining syncs are explicit and bounded. |
| Moving grid epoch | Moving-grid updates must transport projected face cochains across grid epochs. | Tests cover geometric grid rebuild remapping of projected face cochains. |

## Refactoring Policy

When implementation is authorized, the first refactor should be the restricted wall PPE, not a numerical tuning pass.

Order:

1. Define the restricted operator contract and acceptance tests before changing production code.
2. Thread `constrained_face` as a first-class executable `boundary_face_space`.
3. Connect the operator through high-order PPE, low-order DC base, affine jump context, corrector, YAML, diagnostics, and production gates.
4. Keep current `full_face` and `impermeable_face` behavior as tested routes; do not delete working legacy paths.
5. Update paper wording only after the executable/paper A3 chain is precise.

Explicit non-solutions:

- Do not reduce CFL, add damping, smooth curvature, loosen tolerances, change physical parameters, or substitute a solver family to hide the boundary-space gap.
- Do not call a post-corrector boundary Hodge projection equivalent to solving the restricted pressure equation.
- Do not disable nonuniform grids, moving-grid rebuilds, active geometry, HFE jumps, or fail-close gates to make GPU performance look better.

## Reviewed Inputs

Wiki / knowledge cards:

- `docs/wiki/INDEX.md`
- `docs/wiki/cross-domain/WIKI-X-040.md`
- `docs/wiki/cross-domain/WIKI-X-041.md`
- `docs/wiki/cross-domain/WIKI-X-049.md`
- `docs/wiki/cross-domain/WIKI-X-053.md`
- `docs/wiki/cross-domain/WIKI-X-054.md`
- `docs/wiki/theory/WIKI-T-169.md`
- `docs/wiki/theory/WIKI-T-171.md`
- `docs/wiki/theory/WIKI-T-172.md`
- `docs/wiki/experiment/WIKI-E-063.md`
- `docs/wiki/paper/WIKI-P-018.md`
- `docs/wiki/code/WIKI-L-043.md`
- `docs/wiki/code/WIKI-L-044.md`
- `docs/wiki/code/WIKI-L-045.md`
- `docs/wiki/code/WIKI-L-046.md`

Paper / configs / implementation:

- `paper/sections/11e_ao_fast_state_space.tex`
- `paper/sections/14_benchmarks.tex`
- `experiment/ch14/config/ch14_*.yaml`
- `src/twophase/simulation/config_state_space.py`
- `src/twophase/simulation/geometric_phase_runtime_gpu.py`
- `src/twophase/simulation/geometric_volume_hodge.py`
- `src/twophase/simulation/boundary_hodge.py`
- `src/twophase/simulation/config_run_builder_sections.py`
- `src/twophase/simulation/ns_runtime_config.py`
- `src/twophase/simulation/ns_step_services.py`
- `src/twophase/ppe/defect_correction.py`
- `src/twophase/ppe/fd_direct.py`
- `src/twophase/gpu_sparse_solve.py`
- Targeted tests in `src/twophase/tests/`

## Validation

Static/doc check:

- `git diff --check`: PASS after review-only documentation updates.

Test attempt:

- `make test PYTEST_ARGS='-q -k "config_state_space or ..."'`: remote pytest argument splitting rejected this form before useful collection.

Successful validation:

- `make test PYTEST_ARGS='-q twophase/tests/test_config_state_space.py twophase/tests/test_config_io_fccd.py twophase/tests/test_geometric_capillary_reaction_split.py twophase/tests/test_ns_pipeline_fccd.py::test_geometric_grid_rebuild_remaps_projected_face_cochains twophase/tests/test_ns_pipeline_fccd.py::test_affine_pressure_history_coordinate_strips_jump_offset twophase/tests/test_ns_pipeline_fccd.py::test_graph_hfe_pressure_jump_does_not_reuse_pressure_coordinate_history twophase/tests/test_ns_pipeline_fccd.py::test_face_hodge_reprojector_uses_projection_native_complex twophase/tests/test_ns_pipeline_fccd.py::test_face_hodge_reprojector_preserves_no_slip_face_space_when_requested'`
- Remote path/rootdir behavior collected the full suite.
- Result: `793 passed, 35 skipped in 44.37s`.

## SOLID / Scope

[SOLID-X] Review artifact, ledger, and lock/bookkeeping only. No `src/twophase/`, experiment YAML/result data, physical parameter, CFL, damping, smoothing, tolerance, production algorithm, hidden fallback, main merge, branch deletion, or worktree removal was introduced.
