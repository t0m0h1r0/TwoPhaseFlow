# Metaprompt Audit and Repair - CHK-RA-META-AUDIT-001

## Scope
- User request: review metaprompts for redundancy/token waste, contradictions/policy conflicts, role-scope violations, and project-specific content outside `kernel-project.md`; fix root causes and repeat until no findings remain.
- Target: `prompts/meta/*.md` as source of truth, plus generated `prompts/agents-codex/*.md` and `prompts/skills/*.md` after redeploy.
- Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
- Branch: `codex/ra-presentation-agent-evolution-20260516`
- Main merge: not performed.

## Issue Register

| ID | Severity | Category | Finding | Risk | Fix |
|---|---|---|---|---|---|
| MP-AUD-001 | High | Project leakage | Generic kernel files use fixed implementation paths such as `src/core`, `src/system`, and `src/research`. | Conflicts with receiving projects whose code paths differ; violates project-specific profile boundary. | Replace with project-configured implementation/infrastructure paths and kernel-project references. |
| MP-AUD-002 | High | Project leakage / conflict | Generic files assign fixed semantics to `PR-1`, `PR-3`, `PR-4`, `PR-5`, and `PR-6`. | A new project can define PR numbers differently; generated prompts may enforce wrong rules. | Replace fixed PR semantics outside `kernel-project.md` with "project profile rule" wording. |
| MP-AUD-003 | Medium | Project leakage | ID prefix examples include `ch9`, `ch11`, `ch14`, and project-like branches. | Generic metaprompt appears tied to one project and leaks legacy examples. | Replace examples with domain-neutral branch slugs. |
| MP-AUD-004 | High | Role/scope conflict | `AUDIT-01`, `EXP-01`, and `EXP-02` encode project-specific output/tooling/path rules as universal audit checks. | Auditors may fail valid projects or pass invalid ones because checks do not come from the project profile. | Make audit and experiment operations defer project-specific output/tooling/path requirements to `kernel-project.md` / generated project rules. |
| MP-AUD-005 | Medium | Token bloat | `SKILL-PRESENTATION-DECK` spec duplicates much of `PRESENTATION-GEN-01` despite full JIT reference. | Skill capsule consumes unnecessary tokens and increases maintenance surface. | Compress generated skill best-practices to adapter-level guidance and rely on full_ref for details. |
| MP-AUD-006 | High | Role/scope conflict | Codex deploy script assigned broad PAPER-domain rules to every paper-domain role, causing `PaperWriter` to receive `PRESENTATION-GEN-01` and `PresentationWriter` to receive manuscript-writing rules. | Generated agents can over-activate the wrong workflow and waste context on out-of-role operations. | Move PAPER/PRESENTATION operation IDs from domain-wide assignment to role-specific `ROLE_RULES_BY_AGENT`. |
| MP-AUD-007 | High | Project leakage | Codex deploy script hard-coded generated `_base.yaml` paths such as implementation/experiment/result directories. | A receiving project with different paths would receive wrong local base config unless the script is edited. | Derive project directory hints from `prompts/meta/kernel-project.md` and fall back to project-profile references. |

## Repair Plan

1. Patch `kernel-constitution.md`, `kernel-roles.md`, `kernel-ops.md`, `kernel-domains.md`, and `kernel-workflow.md` to remove hard-coded project path and PR semantics.
2. Patch `kernel-deploy.md` skill spec to reduce presentation skill duplication while preserving behavior through `full_ref`.
3. Commit the `prompts/meta` submodule changes.
4. Run `scripts/deploy_codex_agents.py --report-id CHK-RA-META-AUDIT-001`.
5. Audit generated outputs for:
   - no `src/research`, `src/core`, `src/system` in generated role prompts where project paths should be used,
   - no `ch9/ch11/ch14` examples outside `kernel-project.md`,
   - no fixed PR-number semantics outside `kernel-project.md`,
   - presentation terms do not leak into code/paper skills.
6. Repeat until targeted scans show no remaining findings.

## Repairs Applied

### Shared metaprompt source
- `prompts/meta/kernel-constitution.md`: replaced fixed implementation/infrastructure path examples with project-configured wording.
- `prompts/meta/kernel-ops.md`: replaced chapter-like branch examples, fixed PR-rule semantics, project-specific audit checks, and project-specific output/path rules with project-profile references.
- `prompts/meta/kernel-domains.md`: changed project-rule references from fixed PR meanings to receiving-project profile rules.
- `prompts/meta/kernel-roles.md`: removed fixed implementation/source path assumptions from code/devops role authority and constraints.
- `prompts/meta/kernel-workflow.md`: changed fixed PR-lesson wording to project-profile/reusable-prompt lesson wording.
- `prompts/meta/kernel-deploy.md`: compressed `SKILL-PRESENTATION-DECK.best_practices` from a long duplicated manifest into compact adapter guidance with `full_ref` to `PRESENTATION-GEN-01`; replaced project-specific presentation input paths with project evidence/result/source wording.

### Deployment script and generated artifacts
- `scripts/deploy_codex_agents.py`: changed `DOMAIN_RULES["PAPER"]` from broad workflow assignment to role-specific `ROLE_RULES_BY_AGENT`, so manuscript, presentation, review, workflow, and compiler roles receive only the operation IDs they actually need.
- `scripts/deploy_codex_agents.py`: changed generated `_base.yaml` directory hints to derive from `prompts/meta/kernel-project.md`; script no longer embeds TwoPhaseFlow-specific implementation or experiment paths.
- Regenerated 25 Codex agents and 9 skill capsules with `python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-AUDIT-001`.

## Final Validation

| Check | Result |
|---|---|
| Shared-kernel project leakage scan for fixed implementation paths, chapter examples, fixed PR meanings, old figure/output rules | PASS |
| Shared-kernel TwoPhaseFlow-specific term scan outside `kernel-project.md` | PASS |
| Generated code/paper skill scan for presentation artifacts such as `audience_profile`, `story_map`, `slide_spec`, and `convergence_dashboard` | PASS |
| Generated role manifest review for PaperWriter / PresentationWriter / PaperReviewer / PaperCompiler role boundaries | PASS |
| Deploy script project-specific path scan | PASS |
| `git -C prompts/meta diff --check` before submodule commit | PASS |
| `python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-AUDIT-001` | PASS |
| `python3 -m py_compile scripts/deploy_codex_agents.py` | PASS |
| `git diff --check` | PASS |
| Q3 audit report | PASS Q3-01..Q3-15, AP-13, AP-17, agent count, skill capsules, reports |
| Token telemetry | PASS, total static prompt tokens 5977 |
| Skill capsule generation report | PASS, 9 generated, 0 missing, 0 extra |

## Final Issue Status

| ID | Status |
|---|---|
| MP-AUD-001 | Resolved |
| MP-AUD-002 | Resolved |
| MP-AUD-003 | Resolved |
| MP-AUD-004 | Resolved |
| MP-AUD-005 | Resolved |
| MP-AUD-006 | Resolved |
| MP-AUD-007 | Resolved |

## Residual Risk

- Generated `_base.yaml` now derives implementation and experiment path hints from the current `kernel-project.md`, but result-path extraction falls back to a project-profile reference unless the project profile states a result-path convention explicitly. This is acceptable because the script no longer invents a universal result path; a future receiving project can make the result path explicit in `kernel-project.md` if agents need it in `_base.yaml`.

## Status
DONE. No open findings remain after the final targeted scans and deploy audit.
