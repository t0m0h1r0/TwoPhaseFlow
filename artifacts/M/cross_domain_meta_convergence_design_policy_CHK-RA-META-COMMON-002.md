# Cross-Domain Artifact-Convergence Design Policy - CHK-RA-META-COMMON-002

## Scope
- User request: define the design policy for evolving the metaprompt so the presentation-agent design philosophy becomes reusable across domains.
- Basis: `artifacts/M/cross_domain_meta_convergence_research_CHK-RA-META-COMMON-001.md`.
- Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
- Branch: `codex/ra-presentation-agent-evolution-20260516`
- Main merge: not performed.

## Design Goal
Extract the reusable core from the presentation workflow into a cross-domain metaprompt primitive while preserving domain sovereignty.

The common layer should govern the lifecycle:

```text
intent/spec -> evidence-grounded construction -> issue-shaped review
-> focused repair -> validation -> shrinking remaining delta
-> freeze/lock -> final acceptance or human decision
```

The common layer must not make code, papers, experiments, wiki entries, or prompt deployment pretend to be slide decks.

## Central Design Decision
Introduce one shared operation:

```text
ARTIFACT-CONVERGENCE-01
```

Working title:

```text
Evidence-Grounded Deliverable Convergence Loop
```

This operation is a control primitive, not a new artifact type. It defines how a material deliverable converges, while each domain keeps its native artifacts:

| Domain | Native spec remains primary |
|---|---|
| Presentation | `PresentationDeckPlan`, `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml` |
| Code | `SchemeCodePlan`, CheckSpec, tests, verifier reports |
| Paper | `ManuscriptSectionPlan`, claim register, source scope, revision actions |
| Evidence | EvidencePackage, run/analysis plan, provenance record |
| Wiki | canonical wiki entry, source/ref map, K-LINT result |
| Prompt/meta | kernel/deploy plan, generated skill/agent reports, Q3 audit |

## Non-Goals
Do not:

1. Rename all domain artifacts to generic names.
2. Require `audience_profile.yaml` or `story_map.md` outside presentation work.
3. Add full issue dashboards to trivial edits.
4. Paste a long convergence checklist into every role prompt.
5. Let the common primitive override domain-specific authority, paths, validation, or STOP conditions.
6. Reopen already stable presentation behavior merely to make naming symmetrical.
7. Treat "review" as preference collection; it must remain acceptance-critical.

## Core Vocabulary
Use neutral terms in the common primitive:

| Common term | Meaning |
|---|---|
| consumer | The person, role, verifier, runtime, or downstream artifact that must accept/use the deliverable |
| acceptance target | The decision, action, correctness contract, credibility target, or operational pass condition |
| native intent/spec artifact | The domain's own pre-generation artifact |
| issue register | External SSoT for review findings and their status |
| remaining delta | What still blocks or weakens acceptance |
| focused repair | Minimal change that closes selected issues without broad redesign |
| freeze gate | Point after which a layer can be reopened only by High/Must-fix evidence |
| final acceptance | Pass / Conditional Pass / Fail, not open-ended improvement |

Domain adapters translate these terms into local language.

## ARTIFACT-CONVERGENCE-01 Contract
The operation should contain five sections.

### 1. Applicability
Mandatory when:
- the user asks for repeated review, strict review, convergence, repair loops, final acceptance, or role/lens review,
- a material deliverable changes claims, behavior, evidence, generated agents, deployment, or presentation output,
- two or more repair iterations are expected,
- a prior review produced unresolved High/Must-fix issues,
- a deliverable must satisfy a verifier, reviewer, audience, or generated-runtime contract.

Waivable when:
- the task is trivial,
- the change is a narrow formatting or bookkeeping edit,
- no claim/behavior/contract changes,
- no iterative review requested.

Waiver must be explicit for material-looking tasks:

```text
ARTIFACT-CONVERGENCE waived: bounded non-material edit; no iterative review or acceptance-critical issue.
```

### 2. Required Generic Steps
```text
1. Define consumer/verifier/stakeholder.
2. Define acceptance target and evidence needed.
3. Use the domain's native intent/spec artifact before generation/repair.
4. Produce or update the deliverable inside owned paths only.
5. Review through the relevant role/lens.
6. Convert findings to issue-shaped records.
7. Triage Must / Should / Could / Do-not-fix.
8. Apply focused repair.
9. Validate against acceptance target.
10. Update remaining delta, change log, and stop/continue/human-review judgment.
```

### 3. Required Issue Fields
Common issue fields:

```yaml
issue_id:
iteration_found:
severity: High | Medium | Low
category:
consumer_or_verifier:
target_artifact:
problem:
acceptance_impact:
evidence_or_test_needed:
proposed_minimal_fix:
fix_policy: Must fix | Should fix | Could fix | Do not fix
status: Open | Resolved | Deferred | Rejected | Reopened
```

Domain adapters may add fields. They must not remove acceptance impact, fix policy, or status.

### 4. Convergence Metrics
Common dashboard metrics:

```yaml
phase:
high_open:
medium_open:
new_high:
reopened:
remaining_delta:
change_size:
validation_status:
stop_continue_human_review:
```

Adapters may add:
- presentation: primary audience score, slide count, text-heavy slides,
- code: failing tests, conservation/regression/performance deltas,
- paper: unsupported claims, overbroad claims, unresolved reviewer-critical issues,
- prompt/meta: Q3 audit failures, token budget, stale generated artifacts, deploy coverage.

### 5. Stop/Human Review
Stop when:
- no High/Must-fix issue remains,
- acceptance target is satisfied,
- validation passes or residual risk is explicitly accepted,
- latest change set is small enough not to reopen earlier layers,
- remaining issues are preference, minor polish, or human-context decisions.

Escalate to human review when:
- remaining delta does not shrink for two iterations,
- necessary data or internal context is absent,
- the conclusion itself requires human judgment,
- stakeholders conflict,
- review comments become taste-only,
- fixing the issue would violate scope, domain authority, or project rules.

## Domain Adapter Policy

### Presentation Adapter
Keep current concrete artifacts:
- `brief.md`
- `audience_profile.yaml`
- `story_map.md`
- `slide_spec.yaml`
- `review_plan.yaml`
- `issue_register.yaml`
- `convergence_dashboard.md`
- `review_reports/*.md`
- `change_log.md`
- deck exports and previews.

Adapter mapping:

```yaml
consumer: audience / decision maker / presenter
acceptance_target: understands, believes, decides, and can act
native_spec: PresentationDeckPlan + slide_spec.yaml
issue_register_path: issue_register.yaml
freeze_gates: [Story Freeze, Evidence Freeze, Visual Freeze, Final Lock]
```

Keep deck-specific rules such as "decision ask by slide 2" inside this adapter only.

### Code Adapter
Use for numerical scheme/code tasks when work is material or iterative.

```yaml
consumer: TestRunner / downstream API caller / production operator / paper-equation verifier
acceptance_target: executable correctness, contract fidelity, scientific verification, regression safety
native_spec: SchemeCodePlan / CheckSpec
issue_register_path: artifacts/L or task-local verification issue register
freeze_gates: [Equation Freeze, Interface Freeze, Verification Freeze, Release Lock]
```

Rules:
- Do not introduce presentation language like belief change.
- Treat likely objections as failure modes or adversarial cases.
- Treat decision impact as acceptance, safety, reproducibility, or scientific-validity impact.
- Do not add dashboards to one-shot trivial code edits.

### Paper Adapter
Use for drafting, revision, related work, abstract, and review-response loops.

```yaml
consumer: reviewer / venue reader / future author / PaperReviewer
acceptance_target: scoped claim credibility, source fidelity, rhetorical fit, limitation preservation
native_spec: ManuscriptSectionPlan + claim_register
issue_register_path: artifacts/A or section-local review issue register
freeze_gates: [Claim Freeze, Evidence Freeze, Rhetoric Freeze, Submission Lock]
```

Rules:
- Keep `claim_register` as the central evidence object.
- Convert reviewer feedback to issues only when it affects claim credibility, argument flow, evidence, venue fit, or acceptance.
- Style-only comments are Could-fix unless the task is explicitly style editing.

### Evidence / Experiment Adapter
```yaml
consumer: claim owner / paper section / reviewer / downstream analysis
acceptance_target: reproducible evidence with provenance and valid interpretation
native_spec: EvidencePackage / analysis plan / run plan
freeze_gates: [Hypothesis Freeze, Config/Data Freeze, Analysis Freeze, Report Lock]
```

Rules:
- Never let convergence pressure change data, tolerances, or interpretation strength.
- If evidence is missing, mark TODO or inconclusive rather than inventing support.

### Wiki Adapter
```yaml
consumer: future agent / human maintainer / traceability auditor
acceptance_target: reusable validated knowledge with resolvable source refs
native_spec: wiki entry format + K-LINT
freeze_gates: [Source Freeze, Summary Freeze, Index Freeze, Knowledge Lock]
```

Rules:
- The issue register can be lightweight unless a wiki refactor or stale/conflict audit is underway.
- Source validation status is more important than prose polish.

### Prompt/Meta Adapter
```yaml
consumer: generated agents / skills / deploy scripts / receiving-project maintainer
acceptance_target: generated artifacts match kernel intent, no stale copies, no project-local overwrite, token ROI acceptable
native_spec: kernel-deploy.md manifest + Q3 audit reports
freeze_gates: [Kernel Contract Freeze, Generation Manifest Freeze, Deploy/Audit Freeze, Release Lock]
```

Rules:
- All skill/agent/JSON/script support artifacts must remain generated from metaprompt/deploy sources where the current architecture requires it.
- `kernel-project.md` remains user-owned receiving-project overlay; convergence changes must not weaken preservation.
- PromptAuditor should reject presentation vocabulary leakage into code/paper prompts.

## File-Level Implementation Plan
Do this in separate commits.

### Commit 1: Kernel primitive
Files:
- `prompts/meta/kernel-ops.md`

Actions:
- Add `ARTIFACT-CONVERGENCE-01` near the high-level operations before domain-specific loops.
- Add it to the operation index.
- Keep it concise.

Acceptance:
- `PRESENTATION-GEN-01` still remains valid and behaviorally unchanged.
- No generated artifacts yet.

### Commit 2: Domain adapters in operations
Files:
- `prompts/meta/kernel-ops.md`

Actions:
- Add a short "uses ARTIFACT-CONVERGENCE-01 adapter" paragraph to:
  - `SCHEME-CODE-01`
  - `PAPER-WRITE-01`
  - `PRESENTATION-GEN-01`
- Reduce only obvious duplicated convergence prose in presentation if safe; do not remove concrete deck requirements.

Acceptance:
- Code and paper loops gain convergence hooks without mandatory deck artifacts.
- Presentation still names all deck artifacts explicitly.

### Commit 3: Role and skill propagation
Files:
- `prompts/meta/kernel-roles.md`
- `prompts/meta/kernel-deploy.md`

Actions:
- Add lightweight references to the common primitive in relevant roles.
- Update skill capsule specs so generated `SKILL-SCHEME-CODE`, `SKILL-PAPER-WRITING`, `SKILL-PRESENTATION-DECK`, and `SKILL-PROMPT-AUDIT` inherit the common policy.
- Do not duplicate the full primitive body in every skill.

Acceptance:
- Skill capsules mention common convergence only where material/iterative tasks require it.
- Token growth remains controlled.

### Commit 4: Regenerate and audit
Files:
- generated `prompts/agents-codex/*.md`
- generated `prompts/skills/*.md`
- `artifacts/P/...`
- ledger/audit artifact.

Commands:
```text
python3 scripts/deploy_codex_agents.py --report-id CHK-RA-META-COMMON-003
git diff --check
```

Additional scans:
```text
rg -n "ARTIFACT-CONVERGENCE|consumer|remaining delta|freeze" prompts/agents-codex prompts/skills
rg -n "audience_profile|story_map|slide 2" prompts/agents-codex/CodeArchitect.md prompts/agents-codex/PaperWriter.md prompts/skills/SKILL-SCHEME-CODE.md prompts/skills/SKILL-PAPER-WRITING.md
```

Acceptance:
- New primitive appears where expected.
- Presentation-specific terms do not leak into code/paper generated prompts except as references to presentation work.
- Q3 audit passes.

## Validation Policy
Because this is prompt/meta work:

Required:
- `git diff --check`
- `git -C prompts/meta diff --check` if submodule files changed
- `python3 scripts/deploy_codex_agents.py` after deploy-source changes
- Q3 deploy/audit report review
- targeted generated-prompt scans.

Not required:
- `make test`
- experiments
- paper build

Reason:
No `src/twophase/`, experiment YAML, or paper output is changed by this design/implementation path.

## Risk Controls

| Risk | Control |
|---|---|
| Prompt bloat | Primitive is short; domain adapters reference it instead of duplicating |
| Over-generalization | Native artifacts remain primary |
| Presentation vocabulary leaks into code/paper | Add targeted scans and PromptAuditor check |
| Trivial work becomes bureaucratic | Explicit waiver rule |
| Existing deck quality regresses | Preserve deck-specific artifacts and rules |
| `kernel-project.md` safety regresses | Prompt/meta adapter includes project-overlay preservation as acceptance concern |
| Generated skills become stale | Continue metaprompt-driven deployment via `kernel-deploy.md` specs |

## Acceptance Criteria For The Design
This design is acceptable when:

1. It names a single common primitive.
2. It preserves existing domain artifacts.
3. It defines when the primitive is mandatory and when it is waived.
4. It gives concrete adapters for presentation, code, paper, evidence, wiki, and prompt/meta.
5. It provides a staged implementation plan with validation.
6. It explicitly rejects prompt bloat and presentation vocabulary leakage.
7. It keeps main merge out of scope.

## Verdict
Adopt the design. Implement `ARTIFACT-CONVERGENCE-01` as a common lifecycle primitive, then bind each domain through a short adapter. Presentation remains the richest concrete implementation, but the kernel's reusable idea becomes "artifact convergence under acceptance-critical review," not "deck/story workflow everywhere."
