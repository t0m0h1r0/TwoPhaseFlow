# kernel-workflow.md - Generic Research Workflow v1.0.0
# P-E-V-A loop, research-domain pipeline, dynamic replanning, context management.

<meta_section id="META-WORKFLOW" version="1.0.0" axiom_refs="A1,A3,A4,A7,A9,phi5">
<purpose>Master workflow for generic research-agent execution. No material research output is accepted without plan, execute, verify, and audit phases.</purpose>
<rules>
- MUST classify the task before acting.
- MUST use independent verification for proof, evidence, numerical, or paper-review claims.
- MUST keep source artifacts immutable.
- MUST produce workflow-learning artifacts when the task improves the agent system.
- MUST search compiled wiki knowledge before difficult, investigative, or precedent-likely work.
- MUST compile important validated findings and reusable lessons into wiki memory.
</rules>
</meta_section>

--------------------------------------------------------
# § P-E-V-A LOOP

| Phase | Responsibility | Agent | Output |
|-------|----------------|-------|--------|
| PLAN | classify task, choose domain, define artifact contract | ResearchArchitect / TaskPlanner | HAND-01 + interface contract |
| EXECUTE | produce exactly one scoped artifact | domain Specialist | draft artifact on owned path |
| VERIFY | independently check artifact against contract | Gatekeeper or verifier | PASS/FAIL with evidence |
| AUDIT | cross-domain consistency and traceability | ConsistencyAuditor | VALIDATED or replan |

No phase may be skipped for material outputs. TRIVIAL tasks may use FAST-TRACK
only when no proof, evidence, code, or paper claim changes.

--------------------------------------------------------
# § WIKI-FIRST GATES

Compiled wiki knowledge is an active planning input, not an archival afterthought.

## WIKI-RETRIEVAL-GATE

Before substantial work, the acting agent MUST search `docs/wiki/` or dispatch
Librarian when any trigger applies:

| Trigger | Required action |
|---------|-----------------|
| Difficult or ambiguous problem | Search for prior approaches, failures, and assumptions |
| Literature, benchmark, derivation, debug, prompt, or design investigation | Search for reusable knowledge before deriving from scratch |
| Task resembles earlier work or previous project memory | Search by artifact names, concepts, methods, and failure modes |
| Cross-domain interface change | Run K-IMPACT-ANALYSIS or ask TraceabilityManager |
| No local wiki hit but prior-work risk is high | Record "wiki search: no hit" in HAND-02 |

Wiki output is evidence, not authority. Agents may use it to accelerate work,
but must still verify source artifacts when making material claims.

## WIKI-COMPILE-GATE

Before HAND-02 SUCCESS, the agent MUST classify whether the task produced
wiki-worthy knowledge:

| Trigger | Required action |
|---------|-----------------|
| Important finding, new reusable knowledge, or resolved hard failure | Invoke K-COMPILE or dispatch KnowledgeArchitect |
| Reusable workflow lesson or prompt limitation | Compile to wiki after PromptAuditor/owning gate validation, or record a K-candidate in `artifacts/K/` |
| Validated artifact that downstream agents are likely to reuse | Create or update a wiki entry and `docs/wiki/INDEX.md` |
| Significant negative result or blocked path likely to recur | Compile as a cautionary entry with source and scope |
| No wiki-worthy output | State "K-COMPILE: not triggered" with reason in HAND-02 |

Unvalidated artifacts MUST NOT be promoted as canonical wiki knowledge. They may
be recorded as K-candidates under `artifacts/K/` for later KnowledgeArchitect
review.

--------------------------------------------------------
# § RESEARCH PIPELINE

Primary ordering for paper-improvement work:

```
Source Artifact
  -> T: Theory & Claims
  -> L: Research Implementation
  -> E: Evidence & Evaluation
  -> A: Academic Writing
  -> Q: Cross-domain Audit
  -> K: Knowledge Compilation
```

| Domain | Branch | Gatekeeper | Execute | Verify | Entry contract |
|--------|--------|------------|---------|--------|----------------|
| T Theory | `theory` | TheoryAuditor | TheoryArchitect | independent derivation | SourceClaimMap signed |
| L Implementation | `research-impl` | CodeWorkflowCoordinator | CodeArchitect / CodeCorrector | TestRunner | CheckSpec signed |
| E Evidence | `evidence` | CodeWorkflowCoordinator | ExperimentRunner / EvidenceAnalyst | evidence trace | AnalysisPackage signed |
| A Writing | `paper` | PaperWorkflowCoordinator | PaperWriter / PresentationWriter / PaperCompiler | PaperReviewer | RevisionBrief signed |
| P Prompt | `prompt` | PromptArchitect | PromptArchitect | PromptAuditor | meta edit request |
| K Wiki | `wiki` | WikiAuditor | KnowledgeArchitect | K-LINT | VALIDATED source artifact |

--------------------------------------------------------
# § TASK CLASSIFICATION

| Class | Use when | Required agents |
|-------|----------|-----------------|
| TRIVIAL | formatting, file listing, no claim or artifact change | 1 executor |
| FAST-TRACK | bounded edit with existing contract | executor + verifier |
| FULL-PIPELINE | new theorem, evidence claim, reproducibility check, or paper section | coordinator + specialist + independent verifier + auditor |
| RESEARCH-BREADTH | literature scan, multiple proof paths, broad critique | orchestrator + artifact-separated subagents |
| PROMPT-EVOLUTION | agent/kernel change | PromptArchitect + PromptAuditor + ConsistencyAuditor |

Agent count scales with independence and artifact separability, not importance.

--------------------------------------------------------
# § PAPER-IMPROVEMENT MODES

| Mode | Output | Gate |
|------|--------|------|
| Proof audit | `docs/memo/{topic}.md` | TheoryAuditor re-derivation |
| Literature audit | `docs/evidence/{topic}.md` | citation/source verification |
| Numerical check | `analysis/{study}/` | TestRunner command log |
| Revision brief | `docs/interface/RevisionBrief.md` | T/E sign-off |
| Prose patch | `paper/sections/` or `artifacts/A/` | PaperReviewer |
| Presentation deck | `paper/presentations/` or `artifacts/A/`; conceptual visuals include VisualConceptBrief + reverse readback | PaperReviewer |
| Workflow lesson | `artifacts/M/{lesson}.md` | PromptAuditor if kernel-affecting |

--------------------------------------------------------
# § DYNAMIC REPLANNING

Trigger: any agent returns `status: BLOCKED_REPLAN_REQUIRED` in HAND-02.

1. Coordinator identifies blocker class: missing source, ambiguous claim, failed proof, failed evidence, failed reproducibility, scope mismatch.
2. If recoverable inside domain, issue revised HAND-01 with narrowed scope.
3. If cross-domain, create or update Interface Contract and restart from PLAN.
4. Max 2 replan cycles per task. On the 3rd, escalate to user with concrete choices.

--------------------------------------------------------
# § PROTO-DEBATE

When two independent agents reach conflicting verdicts on a falsifiable claim,
Coordinator invokes HAND-04.

| Round | Requirement |
|-------|-------------|
| 1 | each side provides one-paragraph claim + artifact evidence |
| 2 | at least one new artifact path not used in round 1 |
| Final | Gatekeeper issues SUSTAIN or OVERRULE with cited rule/evidence |

Empty evidence auto-loses the debate. Debate output becomes a workflow lesson if
the conflict reveals prompt or routing weakness.

--------------------------------------------------------
# § CONTEXT MANAGEMENT

At each HAND-02 emission, agent records:

| Field | Requirement |
|-------|-------------|
| produced | artifact paths only, not hidden reasoning |
| source_refs | source paths and section/equation/page references |
| verification | commands, logs, or independent derivation artifact |
| unresolved | blockers and exact next action |
| workflow_lesson | when PR-1 applies |

Condense when context exceeds 60% or task exceeds 30 turns. The condensed state
must let a resumed agent continue from external artifacts alone.

--------------------------------------------------------
# § STOP-RECOVER MATRIX

| STOP trigger | Severity | Recovery agent | Action | Resume |
|--------------|----------|----------------|--------|--------|
| Source artifact overwrite risk | HARD | ResearchArchitect | halt and preserve source | PLAN |
| Missing input file | SOFT | Coordinator | dispatch upstream artifact creation | PLAN |
| Proof gap or assumption mismatch | HARD | TheoryAuditor | re-derive or mark finding | EXECUTE |
| Citation unavailable | SOFT | Evidence gate | mark needs verification | VERIFY |
| Reproducibility failure | HARD | TestRunner -> CodeCorrector | fix script or mark inconclusive | EXECUTE |
| Paper build/format failure | SOFT | PaperWorkflowCoordinator | surgical fix | VERIFY |
| AU2 contradiction | HARD | ConsistencyAuditor | route to owning domain | PLAN |
| Replan cycle > 2 | HARD | User + ResearchArchitect | ask for decision | PLAN |

--------------------------------------------------------
# § BOOTSTRAP PIPELINE

For deploying a generic research-agent kernel after a git metaprompt pull:

| Step | Agent | Output | Gate |
|------|-------|--------|------|
| 1 Metaprompt intake | PromptArchitect | pulled `kernel-*.md` | upstream revision recorded |
| 2 Project profile | ResearchArchitect | local `kernel-project.md` + docs | PR count and traceability |
| 3 Local support + agent generation | PromptArchitect | local `prompts/skills/`, templates/scripts policy, `prompts/agents-*` | Q3-AUDIT validation |
| 4 Source registration | TaskPlanner | `docs/01_PROJECT_MAP.md` | source immutability |
| 5 First critique task | ResearchArchitect | HAND-01 for proof/lit audit | P-E-V-A |
