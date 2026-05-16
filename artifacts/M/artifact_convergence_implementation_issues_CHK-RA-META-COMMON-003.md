# Artifact Convergence Implementation Issues - CHK-RA-META-COMMON-003

## Scope
- User request: clarify implementation issues for metaprompt adoption and resolve them.
- Basis:
  - `artifacts/M/cross_domain_meta_convergence_research_CHK-RA-META-COMMON-001.md`
  - `artifacts/M/cross_domain_meta_convergence_design_policy_CHK-RA-META-COMMON-002.md`
- Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
- Branch: `codex/ra-presentation-agent-evolution-20260516`
- Main merge: not performed.

## Implementation Issues

| ID | Issue | Risk if unresolved | Resolution target | Status |
|---|---|---|---|---|
| AC-001 | Common primitive has no canonical operation ID | Presentation convergence remains isolated and duplicated | Add `ARTIFACT-CONVERGENCE-01` to `kernel-ops.md` and shorthand index | Resolved |
| AC-002 | Code/paper could inherit presentation vocabulary | Code/paper prompts may require `audience_profile.yaml`, `story_map.md`, or slide-specific rules | Use neutral common terms and domain adapters; add leakage scans | Resolved |
| AC-003 | Existing presentation behavior could regress | Deck workflow loses concrete artifacts and stop criteria | Keep all deck artifacts/rules explicit; reference common primitive as adapter | Resolved |
| AC-004 | Prompt bloat from copying the full primitive into every role/skill | Generated agents become too long and harder to audit | Roles/skills get compact references to `ARTIFACT-CONVERGENCE-01`; full body stays JIT in `kernel-ops.md` | Resolved |
| AC-005 | Trivial tasks could become over-bureaucratic | Agents create dashboards for tiny edits | Add applicability/waiver rule; require full loop only for material/iterative/strict-review work | Resolved |
| AC-006 | Generated skills/agents may become stale | Metaprompt source differs from project-local deploy outputs | Update `kernel-deploy.md`, rerun deploy script, review reports | Resolved |
| AC-007 | `kernel-project.md` preservation could be weakened | User-owned project overlay could be overwritten in future sync/deploy flows | Prompt/meta adapter must include project-overlay preservation as acceptance concern | Resolved |
| AC-008 | No concrete audit evidence after implementation | Hard to tell whether cross-domain commonization actually propagated | Produce deploy reports, targeted scans, and final artifact summary | Resolved |

## Resolution Strategy

1. Implement the common primitive in `prompts/meta/kernel-ops.md`.
2. Bind domain loops as adapters:
   - `SCHEME-CODE-01`: verifier/operator, `SchemeCodePlan`, equation/interface/verification/release freezes.
   - `PAPER-WRITE-01`: reviewer/reader, `ManuscriptSectionPlan`, claim/evidence/rhetoric/submission freezes.
   - `PRESENTATION-GEN-01`: audience, deck artifacts, Story/Evidence/Visual/Final freezes.
3. Propagate compact references through `kernel-roles.md`.
4. Update generated skill specs in `kernel-deploy.md`.
5. Regenerate project-local agents/skills/reports through `scripts/deploy_codex_agents.py`.
6. Run diff checks and targeted scans for propagation and vocabulary leakage.
7. Update this artifact with resolved status and residual risks.

## Expected Non-Code Validation

```text
git -C prompts/meta diff --check
python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-COMMON-003
git diff --check
rg -n "ARTIFACT-CONVERGENCE|remaining delta|focused repair|freeze" prompts/agents-codex prompts/skills
rg -n "audience_profile|story_map|slide 2" prompts/agents-codex/CodeArchitect.md prompts/agents-codex/PaperWriter.md prompts/skills/SKILL-SCHEME-CODE.md prompts/skills/SKILL-PAPER-WRITING.md
```

## Resolved Changes

- `prompts/meta/kernel-ops.md`
  - Added shorthand and role-operation index entry for `ARTIFACT-CONVERGENCE-01`.
  - Added `ARTIFACT-CONVERGENCE-01` as a JIT-loaded common operation.
  - Bound `SCHEME-CODE-01`, `PAPER-WRITE-01`, and `PRESENTATION-GEN-01` through domain-specific `convergence_control` adapters.
  - Added explicit waiver, issue-register, convergence-dashboard, freeze-gate, final-acceptance, and Human-review rules.
  - Preserved presentation-specific artifacts and rules.

- `prompts/meta/kernel-roles.md`
  - Added compact role-level references for code, evidence, paper, presentation, prompt generation, and prompt audit.
  - Kept code/paper phrasing domain-native: verifier/operator and reviewer/reader, not audience/story-map.
  - Added PromptAuditor rejection criterion for presentation vocabulary leakage into code/paper prompts.

- `prompts/meta/kernel-deploy.md`
  - Updated generated skill specs for prompt audit, paper writing, scheme/code, and presentation deck skills.
  - Kept skills generated from metaprompt source rather than manual edits.

- Generated project-local artifacts:
  - `prompts/agents-codex/*.md`
  - `prompts/skills/*.md`
  - `artifacts/P/codex_overwrite_deploy_CHK-RA-META-COMMON-003/*`

## Validation Evidence

Executed:

```text
git -C prompts/meta diff --check
python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-COMMON-003
git diff --check
```

Deployment output:

```text
Generated 25 Codex agents into prompts/agents-codex
Generated 9 skill capsules into prompts/skills
Reports written to artifacts/P/codex_overwrite_deploy_CHK-RA-META-COMMON-003
```

Audit:

```text
artifacts/P/codex_overwrite_deploy_CHK-RA-META-COMMON-003/q3_audit_report.md
Q3-01..Q3-15 PASS
AP-13 Rule Bloat PASS
AP-17 Wiki Over-Injection PASS
Skill capsules PASS: 9 regenerated from kernel-deploy skill_capsule_specs
```

Targeted propagation scan:

```text
rg -n "ARTIFACT-CONVERGENCE|remaining delta|focused repair" prompts/skills prompts/agents-codex artifacts/P/codex_overwrite_deploy_CHK-RA-META-COMMON-003
```

Result: expected hits in `SKILL-PROMPT-AUDIT`, `SKILL-PAPER-WRITING`, `SKILL-SCHEME-CODE`, `SKILL-PRESENTATION-DECK`, and the relevant generated Codex agents.

Targeted leakage scan:

```text
rg -n "audience_profile|story_map|slide 2" prompts/agents-codex/CodeArchitect.md prompts/agents-codex/PaperWriter.md prompts/skills/SKILL-SCHEME-CODE.md prompts/skills/SKILL-PAPER-WRITING.md
```

Result: no matches.

## Residual Risks

- Generated Codex agent constraints are intentionally compact and may truncate long role text; the full `ARTIFACT-CONVERGENCE-01` body remains available through JIT `kernel-ops.md`.
- Full dashboards are policy-required only for material/iterative work; agents must still use the waiver path for trivial edits to avoid bureaucracy.
- This pass implements the prompt behavior and generated artifacts; it does not create sample code/paper/deck projects exercising every adapter.

## Status
Resolved. The implementation issues were clarified, addressed in the metaprompt source, propagated through generated skills/agents, and validated with deploy/audit evidence.
