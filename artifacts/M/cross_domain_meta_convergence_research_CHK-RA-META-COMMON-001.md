# Cross-Domain Metaprompt Convergence Research - CHK-RA-META-COMMON-001

## Scope
- User request: research how the core design philosophy from the presentation-agent update can be generalized across other metaprompt domains.
- Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
- Branch: `codex/ra-presentation-agent-evolution-20260516`
- Main merge: not performed.

## Local Inputs Inspected
- `prompts/meta/kernel-constitution.md`: three pillars, especially Sovereign Domains, Broken Symmetry, and Falsification Loop.
- `prompts/meta/kernel-workflow.md`: P-E-V-A loop, workflow lesson handling, task classification, dynamic replanning.
- `prompts/meta/kernel-domains.md`: vertical/horizontal domains, artifact ownership, prompt/meta generation boundaries.
- `prompts/meta/kernel-ops.md`:
  - `SCHEME-CODE-01`
  - `PAPER-WRITE-01`
  - `PRESENTATION-GEN-01`
  - `AUDIT-*`, `K-*`, interface patch protocol.
- `prompts/meta/kernel-roles.md`: PaperWriter, PresentationWriter, PaperReviewer constraints.
- `prompts/meta/kernel-deploy.md`: Skill capsule specs for paper, scheme/code, presentation.
- `prompts/skills/SKILL-SCHEME-CODE.md`
- `prompts/skills/SKILL-PAPER-WRITING.md`

No external web source was newly used in this research pass. The user-provided notes and local kernel files were treated as the working evidence.

## Core Finding
The presentation update should not be generalized as "all domains need story maps and audiences." That would be too presentation-shaped.

The reusable core is more abstract:

```text
consumer / verifier / stakeholder definition
-> desired decision, action, acceptance, or belief change
-> intermediate intent/spec artifact before generation
-> evidence-backed deliverable construction
-> role/lens-specific review
-> issue register
-> focused repair
-> validation
-> convergence dashboard
-> freeze gates
-> final acceptance or human decision
```

For presentation decks, the consumer is an audience and the acceptance event is a decision/action. For code, the consumer is a verifier, downstream caller, or operator and the acceptance event is executable correctness. For papers, the consumer is a reviewer/reader and the acceptance event is scoped claim credibility. The same lifecycle fits all three only if the vocabulary is neutral.

## Existing Kernel Shape

### Presentation is currently the richest convergence implementation
`PRESENTATION-GEN-01` now has:
- `audience_profile.yaml`
- `story_map.md`
- `slide_spec.yaml`
- `review_plan.yaml`
- `issue_register.yaml`
- `convergence_dashboard.md`
- staged role reviews
- Must/Should/Could/Do-not-fix classification
- focused repair
- Story/Evidence/Visual/Final freeze gates
- final acceptance review.

This is strong, but domain-specific language is woven directly into the operation. It is valuable as a concrete adapter, not as the universal base.

### Code already has a domain-specific form of the same idea
`SCHEME-CODE-01` has:
- `SchemeCodePlan`
- problem decomposition
- equations/assumptions/invariants
- input/output contracts
- candidate loop
- evaluator metrics
- verification plan
- bounded diff policy
- TestRunner handoff.

What it lacks, compared with presentation, is a general issue/convergence layer:
- no explicit issue register for unresolved verification failures or risks,
- no phase/freeze vocabulary,
- no "after iteration N, do not restart from scratch" rule,
- no convergence dashboard tracking remaining delta.

The underlying behavior is already compatible with convergence. It should be lifted into a generic primitive instead of copy-pasting presentation rules into code.

### Paper writing already has a domain-specific form too
`PAPER-WRITE-01` has:
- `ManuscriptSectionPlan`
- author perspective
- source scope
- claim register
- section outline
- focused feedback
- bounded revision actions
- AI-use transparency record.

The paper loop maps naturally to the same lifecycle:
- consumer: venue reviewer, target reader, future author,
- acceptance: credible scoped claim, readable argument, no unsupported broadening,
- issue: overclaim, missing evidence, rhetorical gap, citation-function mismatch,
- freeze: claim freeze, evidence freeze, rhetoric freeze, submission lock.

As with code, the paper loop should reuse the convergence control layer without inheriting presentation-specific terms like slide 2, audience decision, or visual polish.

## Proposed Shared Primitive

Introduce a domain-neutral operation, tentatively:

```text
ARTIFACT-CONVERGENCE-01: Evidence-Grounded Deliverable Convergence Loop
```

Purpose:

```text
Drive any material deliverable from intent/spec to accepted artifact through
consumer-aware acceptance criteria, issue-shaped review, focused repair,
validation, shrinking remaining delta, freeze gates, and final acceptance.
```

Minimal generic artifact schema:

```yaml
deliverable_context:
  artifact_id:
  domain: T | L | E | A | M | P | Q | K | cross-domain
  consumer:
    primary:
    secondary: []
    acceptance_authority:
    knowledge_or_interface_assumptions:
  acceptance_target:
    decision_or_action:
    correctness_or_quality_contract:
    current_state:
    desired_state:
    objections_or_failure_modes: []
    evidence_needed: []

intent_map:
  core_claim_or_goal:
  source_scope: []
  constraints: []
  excluded_scope: []
  success_criteria: []

deliverable_spec:
  type:
  owned_paths: []
  forbidden_paths: []
  intermediate_artifacts: []
  validation_plan: []
  residual_risks: []

review_control:
  issue_register:
    path:
    fields:
      - issue_id
      - iteration_found
      - severity
      - category
      - consumer_or_verifier
      - target_artifact
      - problem
      - acceptance_impact
      - evidence_or_test_needed
      - proposed_minimal_fix
      - fix_policy
      - status
  convergence_dashboard:
    path:
    metrics:
      - phase
      - high_open
      - medium_open
      - new_high
      - reopened
      - remaining_delta
      - change_size
      - validation_status
      - stop_continue_human_review
  change_log:
    path:
  review_reports:
    path_pattern:

phase_control:
  phases: [Diverge, Structure, Stabilize, Polish, Lock]
  freeze_gates: []
  stop_criteria: []
  human_review_triggers: []
```

This schema should be optional/lightweight for trivial work and mandatory only for material deliverables or repeated review/repair loops. That preserves A1/A6 minimal footprint.

## Domain Adapters

### Presentation adapter
Keep current artifacts, but declare them as a specialization:

| Generic concept | Presentation artifact |
|---|---|
| consumer profile | `audience_profile.yaml` |
| intent map | `story_map.md` |
| deliverable spec | `slide_spec.yaml` |
| validation plan | `review_plan.yaml` |
| issue register | `issue_register.yaml` |
| convergence dashboard | `convergence_dashboard.md` |
| final acceptance | `review_report.md`, render/PPTX/PDF/previews |

Freeze gates:
- Story Freeze
- Evidence Freeze
- Visual Freeze
- Final Lock

### Code / scientific implementation adapter
Use:
- consumer: `TestRunner`, downstream API caller, production operator, paper-equation verifier,
- intent map: equation-to-interface-to-test map,
- deliverable spec: `SchemeCodePlan`,
- issue register: verification/contract issue register,
- dashboard: correctness/conservation/regression/performance remaining delta.

Possible freeze gates:
- Theory/Equation Freeze: governing equations, invariants, and allowed deviations are fixed.
- Interface Freeze: inputs/outputs/shapes/units/paths are fixed.
- Verification Freeze: unit/regression/scientific cases and tolerances are fixed.
- Release Lock: only typo, logging, docs, or clearly failing test fixes.

Do not import presentation concepts like "audience belief" into code. Translate to:

```text
current contract state -> desired verified contract state
objections -> failure modes / adversarial cases
decision impact -> acceptance impact / safety impact
```

### Paper/manuscript adapter
Use:
- consumer: reviewer, venue reader, future author,
- intent map: thesis/claim map,
- deliverable spec: `ManuscriptSectionPlan`,
- issue register: claim/rhetoric/evidence issue register,
- dashboard: unsupported-claim count, overbroad claim count, unresolved reviewer-critical issues.

Possible freeze gates:
- Claim Freeze: central contribution and allowed claim strength fixed.
- Evidence Freeze: source scope, citations, and limitations fixed.
- Rhetoric Freeze: paragraph ordering and rhetorical moves fixed.
- Submission Lock: only typos, citation formatting, build errors, and factual/source corrections.

### Evidence / experiment adapter
Use:
- consumer: claim owner, reviewer, downstream paper section,
- intent map: hypothesis and measurement map,
- deliverable spec: run/analysis plan,
- issue register: reproducibility, provenance, assumption, and interpretation issues,
- dashboard: failed runs, missing provenance, unresolved analysis deltas.

Possible freeze gates:
- Hypothesis Freeze
- Config/Data Freeze
- Analysis Freeze
- Report Lock

### Knowledge/wiki adapter
Use:
- consumer: future agent or human retrieving precedent,
- intent map: reusable lesson and source scope,
- deliverable spec: wiki entry format,
- issue register: stale, duplicate, unresolved reference, overgeneralized lesson,
- dashboard: lint status, cross-reference status, source validation status.

Possible freeze gates:
- Source Freeze
- Summary Freeze
- Index Freeze
- Knowledge Lock

### Prompt/meta adapter
Use:
- consumer: generated agents, skills, scripts, deploy runtime, receiving project maintainer,
- intent map: prompt behavior change map,
- deliverable spec: kernel/deploy/skill generation plan,
- issue register: Q3 audit failures, token bloat, stale generated artifact, project-local overwrite risk,
- dashboard: prompt audit status, generated artifact coverage, token budget, remaining high-risk prompt issues.

Possible freeze gates:
- Kernel Contract Freeze
- Generation Manifest Freeze
- Deploy/Audit Freeze
- Release Lock

This directly addresses recent lessons: generated skills, JSON, scripts, reports, and user-owned `kernel-project.md` safety should be governed by the same convergence primitive.

## Recommended Metaprompt Evolution

### Phase 1: Add a short generic primitive
Add `ARTIFACT-CONVERGENCE-01` to `kernel-ops.md` near the existing cross-domain operations, not inside `PRESENTATION-GEN-01`.

The section should be concise and define:
- consumer/acceptance model,
- issue-shaped review,
- Must/Should/Could/Do-not-fix triage,
- focused repair,
- remaining delta,
- convergence dashboard,
- freeze gates,
- final acceptance,
- human-review triggers.

This should be referenced by code, paper, presentation, evidence, knowledge, and prompt adapters.

### Phase 2: Refactor presentation to reference the primitive
Keep all current deck-specific rules, but shorten the convergence-heavy duplication by saying:

```text
Use ARTIFACT-CONVERGENCE-01 with the presentation adapter:
consumer=audience, intent_map=story_map.md, deliverable_spec=slide_spec.yaml,
acceptance=audience can understand/believe/decide, freeze gates=Story/Evidence/Visual/Final.
```

This prevents presentation from becoming a special-case island.

### Phase 3: Add lightweight references to code and paper loops
Do not add full dashboards to every small code or prose task. Instead:

```text
For material or iterative tasks, run ARTIFACT-CONVERGENCE-01 using the domain adapter.
For trivial or single-pass bounded edits, record why it is waived.
```

For `SCHEME-CODE-01`, add:
- verification issue register for repeated repair loops,
- convergence dashboard when multiple candidate/repair passes occur,
- freeze gates for equation/interface/verification/release.

For `PAPER-WRITE-01`, add:
- claim/rhetoric/evidence issue register for reviewer-like passes,
- convergence dashboard when multiple review/revision passes occur,
- claim/evidence/rhetoric/submission freeze gates.

### Phase 4: Update Skill Capsules and deploy specs
Because skills and JSON are generated from `kernel-deploy.md`, the generic primitive must propagate through:
- `SKILL-SCHEME-CODE`
- `SKILL-PAPER-WRITING`
- `SKILL-PRESENTATION-DECK`
- `SKILL-PROMPT-AUDIT`
- any future evidence/wiki skill.

The skill capsules should not duplicate the whole generic primitive. They should include a compact trigger:

```text
For material iterative work, apply ARTIFACT-CONVERGENCE-01 with this domain's adapter.
```

The generated reports should record whether the generic primitive was:
- applied,
- waived as trivial,
- or blocked pending human input.

### Phase 5: Add audit checks
Extend Q3/PromptAuditor only after Phase 1-4 are stable. Suggested checks:
- generated role prompts reference the generic primitive where expected,
- domain skills do not paste the full primitive body unless token ROI is justified,
- presentation-specific vocabulary does not leak into code/paper generated prompts,
- `kernel-project.md` can override domain adapter names or required artifacts without being overwritten.

## Why Not Make Everything a Presentation Pipeline?
Bad generalization would say:

```text
Every deliverable needs audience_profile.yaml, story_map.md, slide_spec.yaml.
```

That would violate domain sovereignty and create prompt bloat.

Good generalization says:

```text
Every material deliverable needs a consumer/acceptance model,
a pre-generation intent/spec artifact, issue-shaped review,
focused repair, validation, and convergence control.
```

Then each domain chooses its own artifact names and acceptance tests.

## Interaction With Existing Philosophy

This proposal strengthens existing kernel pillars:

- Sovereign Domains: shared lifecycle does not permit cross-domain mutation; adapters keep ownership local.
- Broken Symmetry: reviews remain role/lens-separated; acceptance should be independently checked when material.
- Falsification Loop: review is framed as finding decision-critical or acceptance-critical contradictions.
- Truth Before Action: no generation before intent/spec/evidence scope is explicit.
- Minimal Footprint: convergence machinery is mandatory only for material, iterative, or high-risk work.
- Stateless Agents, Persistent State: issue registers, dashboards, and change logs externalize loop state.

## Anti-Bloat Rules
To avoid turning the metaprompt into a heavy universal bureaucracy:

1. Do not require full convergence artifacts for trivial tasks.
2. Do not require presentation artifact names outside presentation.
3. Do not paste the generic primitive into every role prompt; expose it through SkillIDs and `kernel-ops.md`.
4. Keep domain adapters short.
5. Make waiver explicit: "ARTIFACT-CONVERGENCE waived because task is trivial/bounded/no iterative review."
6. Add dashboards only when there is an actual loop, multiple issues, or user asks for strict review.
7. Prefer existing artifacts (`SchemeCodePlan`, `ManuscriptSectionPlan`) over inventing duplicate specs.

## Proposed Implementation Order
Recommended next implementation sequence:

1. Research closure: keep this artifact as the design basis.
2. Add `ARTIFACT-CONVERGENCE-01` to `prompts/meta/kernel-ops.md`.
3. Update `PRESENTATION-GEN-01` to reference it while preserving deck-specific details.
4. Update `SCHEME-CODE-01` and `PAPER-WRITE-01` with lightweight convergence hooks and domain freeze gates.
5. Update `kernel-deploy.md` skill capsule specs so generated skills inherit the common primitive.
6. Run `scripts/deploy_codex_agents.py`.
7. Audit generated agents/skills/reports for:
   - no stale generated artifact,
   - no presentation vocabulary leakage into code/paper,
   - no excessive duplicated generic body,
   - Q3 audit PASS.

## Suggested Minimal Kernel Snippet
This is not yet applied; it is a candidate direction.

```md
<meta_section id="ARTIFACT-CONVERGENCE-01" version="0.1.0-candidate" axiom_refs="A1,A2,A3,A6,A8,phi1,phi2,phi4,phi5">
## ARTIFACT-CONVERGENCE-01: Evidence-Grounded Deliverable Convergence Loop

<purpose>For material or iterative deliverables, converge from intent/spec to accepted artifact by defining the consumer or verifier, acceptance target, evidence needed, issue register, focused repair loop, validation, remaining delta, freeze gates, and final acceptance.</purpose>

<rules>
- Before generation or repair, define who consumes or verifies the artifact and what acceptance means for that role.
- Use the domain's native intent/spec artifact; do not force presentation artifact names outside decks.
- Convert review findings into issues with severity, category, acceptance impact, proposed minimal fix, fix policy, and status.
- Classify findings as Must fix, Should fix, Could fix, or Do not fix; do not accept every comment.
- Repair only the smallest artifact surface needed to close Must and selected Should issues.
- Validate the repair against acceptance criteria and record remaining delta.
- After stabilization, re-review unresolved/reopened/new-critical issues and stop criteria, not the whole artifact from scratch.
- Apply domain-specific freeze gates; reopening a frozen layer requires a High/Must-fix reason.
- Stop when acceptance criteria pass and remaining delta is small; escalate to Human review when missing data, conflicting goals, or repeated non-shrinking delta block convergence.
- Waive this loop for trivial bounded work, but record the waiver when material claims or artifacts change.
</rules>
</meta_section>
```

## Strict Recommendation
Proceed with a common primitive, but keep it as a lifecycle/control abstraction rather than a universal artifact template.

Best next step:
- implement `ARTIFACT-CONVERGENCE-01`,
- connect presentation/code/paper to it through adapters,
- regenerate skills/agents through the existing deploy pipeline,
- audit for bloat and domain leakage.

Do not immediately impose `issue_register.yaml` and `convergence_dashboard.md` on every task. Instead, require them for material iterative tasks, strict review, repeated repair, or user-requested convergence.

## Verdict
PASS as a research direction. The presentation-agent upgrade reveals a reusable convergence-control architecture. The safe cross-domain evolution is to extract a neutral `ARTIFACT-CONVERGENCE-01` primitive and bind each domain through a short adapter, preserving existing domain-specific artifacts and authority boundaries.
