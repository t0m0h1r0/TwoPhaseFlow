# WIKI-M-012: Agent Roster Evolution (2026-03-27 → 2026-04-14)
**Category:** Meta | **Created:** 2026-04-18 | **Source:** git log, `prompts/meta/meta-roles.md`

## Overview

The agent roster grew from ~12 prototype agents to a 25×2-environment system over a period of
three weeks. The evolution was non-monotonic: two major consolidation events eliminated
redundancy, while two expansion events added architecture-driven roles.

---

## Roster Milestones

| Date | Count | Key event | Commit |
|------|-------|-----------|--------|
| 2026-03-27 | ~12 | Pre-meta era: initial deployment from `prompts/agents/` (CodeArchitect, CodeCorrector, CodeReviewer, ConsistencyAuditor, ExperimentRunner, PaperCompiler, PaperCorrector, PaperReviewer, PaperWriter, ResearchArchitect, TestRunner, WorkflowCoordinator) | `73cf371` |
| 2026-03-28 | 16 | PaperWorkflowCoordinator added; WorkflowCoordinator renamed → CodeWorkflowCoordinator; PromptArchitect + PromptAuditor added; docs moved from `prompts/docs/` to top-level `docs/` | `d8237fd` |
| 2026-04-02 | 29 | v3.0.0 full deployment: 9-file meta-architecture, AP-01..08, L0–L3 isolation model, BEHAVIORAL_PRIMITIVES | `8572454` |
| 2026-04-03 | 18 | **Consolidation**: 4 agents absorbed; YAML format adopted (`_base.yaml` inheritance); 71% size reduction | `9938b44` / `c598ab9` |
| 2026-04-03 | 19 | TaskPlanner added (M-Domain, between ResearchArchitect and domain coordinators); §PARALLEL EXECUTION protocols (PE/BS/RC) added | `64b5c7a` |
| 2026-04-04 | 20 | DiagnosticArchitect added (self-healing agent for blocked pipelines); STOP-RECOVER matrix extended with ERR-R1..R4 | `191d17c` |
| 2026-04-04 | 29 | **P3 micro-agents activated** (9 atomic agents): EquationDeriver, SpecWriter, CodeArchitectAtomic, LogicImplementer, ErrorAnalyzer, RefactorExpert, TestDesigner, VerificationRunner, ResultAuditor — now OPERATIONAL | `1326fa5` |
| 2026-04-07 | 33 | **K-Domain** (5th governance domain) introduced: +4 agents: KnowledgeArchitect, WikiAuditor, Librarian, TraceabilityManager; A11 axiom added | `9da3f9e` |
| 2026-04-08 | 33 | CHK-094 full Q3 9/9 PASS deployment; 24 composite + 9 micro agents confirmed | `efd93dd` |
| 2026-04-11 | 33 | v5.1 concurrency + v4.1 3-Pillar (CoVe + Schema-in-Code + JIT) + v5.2 AP-09/10; all 33 agents updated; no roster count change | multiple |
| 2026-04-14 | **25×2** | **Dual-environment split**: `prompts/agents/` deleted; `agents-claude/` (25 agents, ~2500 tokens) + `agents-codex/` (25 agents, ~1500 tokens) created via EnvMetaBootstrapper zero-base generation; TheoryArchitect + TheoryAuditor added | `c1fdbe3` |

---

## Consolidation Events (2026-04-03)

The 29→18 reduction eliminated agents whose roles could be handled by a dedicated step
inside an existing agent's procedure, rather than a separate DISPATCH cycle.

| Absorbed agent | Absorbed into | Mechanism |
|----------------|--------------|-----------|
| PaperCorrector | PaperWriter | Correction mode as Step 5a in PaperWriter procedure |
| ErrorAnalyzer | CodeCorrector | Diagnosis-only logic as Step 6a in CodeCorrector |
| PromptCompressor | PromptArchitect | Compression pass as Step 9 in PromptArchitect |
| ResultAuditor | ConsistencyAuditor | Convergence audit step in ConsistencyAuditor procedure |

Additionally, 7 micro-agents listed as "NOT-YET-OPERATIONAL" at v3.0.0 were moved to
`_experimental/` rather than shipped as broken agents.

---

## YAML Refactor Impact (2026-04-03, commit `c598ab9`)

Before: each agent was a standalone Markdown file with full axiom text, HAND protocols,
and boilerplate repeated verbatim.

After: `prompts/agents/_base.yaml` provides the universal foundation (shared axioms A1–A11,
φ1–φ7, behavioral primitives, rules_always). Individual agent files contain ONLY overrides.

Result: **71% total size reduction** (165KB → 48KB across 18 agent files).

---

## P3 Micro-Agent Architecture (2026-04-04, commit `1326fa5`)

9 atomic micro-agents activated with minimal context budgets for high-throughput tasks:

| Domain | Agents | Context budget |
|--------|--------|----------------|
| T (Theory) | EquationDeriver, SpecWriter | 4k, 3k tokens |
| L (Library) | CodeArchitectAtomic, LogicImplementer, ErrorAnalyzer, RefactorExpert | 5k, 5k, 3k, 4k tokens |
| E (Experiment) | TestDesigner, VerificationRunner | 4k, 2k tokens |
| Q (Quality) | ResultAuditor | 4k tokens |

Design principles: DDA-01/02/03 enforcement embedded; HAND-01-TE stateless handoff;
SIGNAL protocol (READY/BLOCKED/INVALIDATED/COMPLETE) for async coordination.

---

## Dual-Environment Split (2026-04-14, commit `c1fdbe3`)

The single `prompts/agents/` directory (33 agents) was replaced by two per-environment
directories generated from the same meta-source:

| Environment | Path | Token budget | Extra content |
|-------------|------|-------------|---------------|
| Claude | `prompts/agents-claude/` | ~2500 tokens/agent | THOUGHT_PROTOCOL (SLP-01 shorthand), AP self-check table, full procedure |
| Codex | `prompts/agents-codex/` | ~1500 tokens/agent | Diff-first compressed, no THOUGHT_PROTOCOL |

The split was driven by the observation that Claude and Codex respond differently to
instruction density: Claude benefits from the structured THOUGHT: key-value block and
AP self-check; Codex performs better with terse, diff-first instructions.

Additionally, TheoryArchitect and TheoryAuditor were added in this deployment,
bringing the per-environment count to 25 (vs. the prior 33-agent single-env roster
which included micro-agents that were now handled differently).

---

## Current Roster (agents-claude/, 25 agents)

| Domain | Agents |
|--------|--------|
| Root (M) | ResearchArchitect, TaskPlanner |
| Theory (T) | TheoryArchitect, TheoryAuditor |
| Library (L) | CodeArchitect, CodeCorrector, CodeReviewer, CodeWorkflowCoordinator, TestRunner, VerificationRunner |
| Experiment (E) | ExperimentRunner, SimulationAnalyst |
| Paper (A) | PaperWriter, PaperReviewer, PaperCompiler, PaperWorkflowCoordinator |
| Prompt (P) | PromptArchitect, PromptAuditor |
| Knowledge (K) | KnowledgeArchitect, WikiAuditor, Librarian, TraceabilityManager |
| Quality (Q) | ConsistencyAuditor |
| Infrastructure (M) | DevOpsArchitect, DiagnosticArchitect |

---

## Cross-References

- `→ WIKI-M-006`: Micro-agent architecture (P3 design, DDA, SIGNAL protocol)
- `→ WIKI-M-007`: K-Domain addition (KnowledgeArchitect et al., A11 axiom)
- `→ WIKI-M-008`: SLP/RAP/SDP protocols + per-environment generation rationale
- `→ WIKI-M-004`: Constitutional refactoring (March 2026) that preceded Phase 1 expansion
