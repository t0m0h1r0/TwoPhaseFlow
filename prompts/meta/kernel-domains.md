# kernel-domains.md - Generic Research Domain Registry v1.0.0
# FOUNDATION: kernel-constitution.md §phi, §A
# Role contracts: kernel-roles.md | Operations: kernel-ops.md | Workflow: kernel-workflow.md

<meta_section id="META-DOMAINS" version="1.0.0" axiom_refs="A4,A9,phi3,phi5">
<purpose>Authoritative domain registry for generic research projects. Defines ownership, write territories, agent membership, and cross-domain interface contracts.</purpose>
<rules>
- MUST keep domains sovereign: each primary artifact has exactly one owning domain.
- MUST route cross-domain communication through signed Interface Contracts.
- MUST NOT let paper-writing agents silently modify source proofs, code, or evidence.
- MUST record every validated artifact in external memory.
</rules>
</meta_section>

--------------------------------------------------------
# § RESEARCH DOMAIN ARCHITECTURE

## Vertical Domains

| ID | Domain | Truth Type | Dir | Specialist | Gatekeeper |
|----|--------|------------|-----|------------|------------|
| T | Theory & Claims | Logical/mathematical | docs/memo/ | TheoryArchitect | TheoryAuditor |
| R | Research Implementation | Computational/functional | src/, analysis/, notebooks/ | CodeArchitect, CodeCorrector, TestRunner | CodeWorkflowCoordinator |
| E | Evidence & Evaluation | Empirical/bibliographic | docs/evidence/, data/ | ExperimentRunner, EvidenceAnalyst | CodeWorkflowCoordinator |
| A | Academic Writing | Manuscript/narrative/presentation | paper/ | PaperWriter, PresentationWriter, PaperCompiler, PaperReviewer | PaperWorkflowCoordinator |

## Horizontal Domains

| ID | Domain | Role | Key Agent(s) |
|----|--------|------|--------------|
| M | Meta-Logic | Research operating system | ResearchArchitect, TaskPlanner, DiagnosticArchitect, DevOpsArchitect |
| P | Prompt & Environment | Agent generation and audit | PromptArchitect, PromptAuditor |
| Q | QA & Audit | Cross-domain contradiction search | ConsistencyAuditor |
| K | Knowledge/Wiki | Compiled reusable memory | KnowledgeArchitect, WikiAuditor, Librarian, TraceabilityManager |

**Sovereignty rule:** All inter-domain communication uses an Interface Contract in `docs/interface/`.
**Broken Symmetry:** Gatekeeper and Specialist are different roles for any material review.
**Wiki-first rule:** Agents search K-domain memory before difficult or
precedent-likely work, and compile significant validated findings back into
K-domain memory before closing the task.

--------------------------------------------------------
# § INTER-DOMAIN INTERFACES

| Transfer | Contract Artifact | Precondition |
|----------|-------------------|--------------|
| Source -> T | `docs/interface/SourceClaimMap.md` | Source artifact registered |
| T -> R | `docs/interface/CheckSpec.md` | TheoryAuditor PASS |
| R -> E | `docs/interface/AnalysisPackage/` | TestRunner PASS |
| E -> A | `docs/interface/EvidencePackage/` | Evidence gate PASS |
| T/E -> A | `docs/interface/RevisionBrief.md` | Theory and evidence checks signed |
| Any -> K | `docs/wiki/{category}/{REF-ID}.md` | Owning Gatekeeper PASS; VALIDATED |
| K -> all | `docs/wiki/INDEX.md` | WikiAuditor PASS |

**Contract immutability:** Once a Specialist branch or task starts from a contract, that
contract is read-only. Change requires a new contract version.

--------------------------------------------------------
# § DOMAIN REGISTRY

```yaml
domain: Routing
branch: none
coordinator: ResearchArchitect
write: []
read: [docs/02_ACTIVE_LEDGER.md, docs/01_PROJECT_MAP.md, prompts/meta/kernel-project.md]
lifecycle: classify request -> route to owning domain -> exit

domain: T
branch: theory
coordinator: TheoryAuditor
specialists: [TheoryArchitect, PaperWriter(math exposition)]
write: [docs/memo/, docs/interface/SourceClaimMap.md, docs/02_ACTIVE_LEDGER.md]
read: [paper/source/, paper/sections/, docs/01_PROJECT_MAP.md]
forbidden: [src/, analysis/, notebooks/, data/, prompts/meta/]
produces: [docs/interface/CheckSpec.md, docs/interface/RevisionBrief.md]
rules: [A3, AU1-AU3, PR-3]
lifecycle: DRAFT -> REVIEWED(Independent derivation) -> VALIDATED(AU2 PASS)

domain: R
branch: research-impl
coordinator: CodeWorkflowCoordinator
specialists: [CodeArchitect, CodeCorrector, TestRunner]
write: [src/, analysis/, notebooks/, tests/, docs/02_ACTIVE_LEDGER.md]
read: [docs/interface/CheckSpec.md, paper/source/, docs/memo/]
forbidden: [paper/sections/, paper/presentations/, prompts/meta/, docs/interface/ without IF-COMMIT]
produces: docs/interface/AnalysisPackage/
rules: [C1-C6, PR-5]
lifecycle: DRAFT -> REVIEWED(TestRunner PASS) -> VALIDATED(AU2 PASS)

domain: E
branch: evidence
coordinator: CodeWorkflowCoordinator
specialists: [ExperimentRunner, EvidenceAnalyst]
write: [docs/evidence/, data/, artifacts/E/, docs/02_ACTIVE_LEDGER.md]
read: [paper/source/, docs/interface/AnalysisPackage/, docs/memo/]
forbidden: [src/ except invocation, paper/sections/, paper/presentations/, prompts/meta/]
produces: [docs/interface/EvidencePackage/, docs/interface/RevisionBrief.md]
rules: [PR-4, PR-5]
lifecycle: DRAFT -> REVIEWED(Evidence trace) -> VALIDATED(AU2 PASS)

domain: A
branch: paper
coordinator: PaperWorkflowCoordinator
specialists: [PaperWriter, PresentationWriter, PaperCompiler, PaperReviewer]
write: [paper/sections/, paper/figures/, paper/presentations/, paper/bibliography.bib, artifacts/A/, docs/02_ACTIVE_LEDGER.md]
read: [paper/source/, docs/interface/RevisionBrief.md, docs/interface/EvidencePackage/, docs/memo/]
forbidden: [src/, analysis/, notebooks/, data/, prompts/meta/, docs/interface/ without IF-COMMIT]
produces: [paper/sections/, paper/presentations/, artifacts/A/revision_notes.md]
rules: [P1-P4, PR-6]
lifecycle: DRAFT -> REVIEWED(PaperReviewer + build/format PASS) -> VALIDATED(AU2 PASS)

domain: M
branch: meta
coordinator: ResearchArchitect
specialists: [TaskPlanner, DiagnosticArchitect, DevOpsArchitect]
write: [artifacts/M/, docs/02_ACTIVE_LEDGER.md]
read: ALL
forbidden: [paper/source/ overwrite, prompts/meta/ without explicit prompt task]
rules: [A1-A11, PR-1]

domain: P
branch: prompt
coordinator: PromptArchitect
specialists: [PromptAuditor]
write: [prompts/agents-claude/, prompts/agents-codex/, prompts/skills/, artifacts/P/]
read: [prompts/meta/kernel-*.md, prompts/meta/kernel-project.md, docs/02_ACTIVE_LEDGER.md]
forbidden: [paper/source/, src/, analysis/, paper/sections/, paper/presentations/]
rules: [Q1-Q4, PR-1]
lifecycle: DRAFT -> REVIEWED(PromptAuditor Q3 PASS) -> VALIDATED

domain: Q
branch: audit
coordinator: ConsistencyAuditor
write: [artifacts/Q/, docs/02_ACTIVE_LEDGER.md]
read: [task-relevant artifacts, referenced sources, docs/02_ACTIVE_LEDGER.md]
forbidden: [paper/source/ overwrite, primary artifact edits]
rules: [AU1-AU3]
note: Finding contradiction is a useful result, not a failure.

domain: K
branch: wiki
coordinator: WikiAuditor
specialists: [KnowledgeArchitect, Librarian, TraceabilityManager]
write: [docs/wiki/, artifacts/K/, docs/02_ACTIVE_LEDGER.md]
read: [validated source artifacts cited by the task, docs/wiki/INDEX.md, related wiki entries, artifacts/K/]
forbidden: [primary artifact edits]
rules: [A2, A11, K-A1..K-A5]
lifecycle: DRAFT -> REVIEWED(K-LINT) -> VALIDATED
```

--------------------------------------------------------
# § ARTIFACT & DIRECTORY CONVENTIONS

```
paper/source/      Immutable source PDFs and extracted text
paper/sections/    Proposed manuscript sections or patches
paper/figures/     Curated figures for manuscript or presentation use
paper/presentations/  Paper-grounded slide decks, deck outlines, and presentation assets
docs/memo/         Mathematical and conceptual audits
docs/evidence/     Literature, citation, and empirical evidence notes
docs/interface/    Signed cross-domain contracts
docs/wiki/         Compiled reusable knowledge
artifacts/K/       Wiki candidates, K-domain audits, and compilation logs
analysis/          Reproducible scripts and outputs
notebooks/         Reproducible exploratory notebooks promoted to artifacts
src/               Reusable research code
data/              Local data inputs with provenance
artifacts/{M,T,R,E,A,Q,K,P}/  Agent intermediate artifacts
prompts/meta/      Local materialization of pulled metaprompt source plus kernel-project.md
prompts/agents-*/  Project-local generated executable agent prompts
prompts/skills/    Project-local generated JIT skill capsules
```

--------------------------------------------------------
# § MICRO-AGENT PRINCIPLES

| # | Principle |
|---|-----------|
| IF-01 | No direct cross-domain mutation; exchange artifacts through `docs/interface/` or `artifacts/` |
| IF-02 | HAND tokens reference artifact paths, not hidden conversation state |
| IF-03 | Critical audits use independent derivation before reading proposed fixes |
| IF-04 | Signed artifacts are read-only until superseded |
| IF-05 | Workflow lessons are first-class artifacts under `artifacts/M/` |

--------------------------------------------------------
# § WIKI ENTRY FORMAT

```yaml
WIKI-ENTRY:
  ref_id:         {e.g., WIKI-T-001}
  title:          {concise title}
  domain:         {T | R | E | A | M | cross-domain}
  status:         {ACTIVE | DEPRECATED | SUPERSEDED}
  superseded_by:  {[[REF-ID]] or null}
  sources:
    - path: {artifact path}
      git_hash: {short hash}
      description: {what was extracted}
  consumers:
    - domain: {domain ID}
      usage: {how used}
  depends_on: [[[REF-ID]], ...]
  compiled_by: KnowledgeArchitect
  verified_by: WikiAuditor
  compiled_at: {ISO date}
---
{structured Markdown body with [[REF-ID]] pointers}
```
