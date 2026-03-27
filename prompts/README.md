# Research-to-Paper-to-Code Workflow System

A deterministic, self-evolving prompt architecture for transforming ideas into validated scientific papers, correct numerical solvers, and robust infrastructure.

Designed NOT to maximize LLM creativity — designed to maximize **Correctness, Traceability, Reproducibility, and Structural Integrity**.

---

## 1. Core Axioms

Defined in `meta/meta-tasks.md`. All agents obey these unconditionally.

| Axiom | Rule |
|-------|------|
| A1 Token Economy | diff > rewrite; reference > duplication; no redundancy |
| A2 External Memory First | all state in `docs/`; never rely on implicit context |
| A3 3-Layer Traceability | Equation → Discretization → Code chain must be preserved |
| A4 Separation | never mix logic/content/tags/style; never mix solver/infra |
| A5 Solver Purity | infrastructure must not affect numerical results |
| A6 Diff-First Output | no full file rewrites unless explicitly required |
| A7 Backward Compatibility | preserve semantics; upgrade by mapping, never by discarding |
| A8 Git Governance | 3-phase lifecycle per domain: DRAFT → REVIEWED → VALIDATED → auto-merge `{branch} → main`; each domain independent |

---

## 2. Directory Structure

```
project-root/
├── prompts/
│   ├── meta/                          # Meta system (canonical source — edit here only)
│   │   ├── meta-deploy.md             # Bootstrap workflow; environment profiles; 6-stage deployment
│   │   ├── meta-tasks.md              # Agent roles, axioms (A1–A8), per-agent task specs
│   │   ├── meta-persona.md            # Agent personality, skills, decision styles
│   │   └── meta-workflow.md           # State machine, handoff map, protocols P1–P7
│   │
│   └── agents/                        # Generated agent prompt files (DO NOT edit directly)
│       ├── GLOBAL_RULES.md            # Shared axiom inheritance (A1–A8, P1, P5, P6)
│       ├── ResearchArchitect.md       # Session start, intent routing (cross-domain)
│       ├── CodeWorkflowCoordinator.md # Code domain pipeline orchestrator
│       ├── CodeArchitect.md           # Equation → Python implementation + MMS tests
│       ├── CodeCorrector.md           # Staged numerical debugging (protocols A–D)
│       ├── CodeReviewer.md            # Refactoring without numerical change
│       ├── TestRunner.md              # Convergence analysis, PASS/FAIL verdict
│       ├── ExperimentRunner.md        # Reproducible benchmark execution
│       ├── PaperWorkflowCoordinator.md# Paper domain pipeline orchestrator + review loop
│       ├── PaperWriter.md             # LaTeX manuscript authoring (skeptical verifier)
│       ├── PaperReviewer.md           # Rigorous peer review — output in Japanese
│       ├── PaperCompiler.md           # LaTeX compilation and repair (KL-12 guard)
│       ├── PaperCorrector.md          # Minimal targeted fixes from verified findings only
│       ├── ConsistencyAuditor.md      # Cross-validates equations ↔ code ↔ paper
│       ├── PromptArchitect.md         # Generates role-specific agent prompts
│       ├── PromptCompressor.md        # Reduces token usage without semantic loss
│       └── PromptAuditor.md           # Validates prompt correctness (read-only)
│
├── docs/                         # External Memory (mandatory)
│   ├── ACTIVE_STATE.md           # Current phase, branch, last decision, next action
│   ├── CHECKLIST.md              # CHK-ID task tracking
│   ├── ASSUMPTION_LEDGER.md      # ASM-ID assumption registry
│   ├── LESSONS.md                # LES-ID failure patterns and fix recipes
│   ├── ARCHITECTURE.md           # High-level design (authority source)
│   ├── CODING_POLICY.md          # SOLID rules and code governance
│   └── LATEX_RULES.md            # LaTeX authoring rules (tcolorbox, labels, refs)
│
├── paper/                        # LaTeX workspace
└── src/
    └── twophase/                 # Solver + infrastructure (domain boundary enforced in code)
```

**Note on `GLOBAL_RULES.md`:** All 16 agent prompts inherit A1–A8, P1, P5, P6 and universal stop triggers from this file by reference. Per A1, axioms are not restated per-agent.

---

## 3. Meta System Overview

The `meta/` directory is the **canonical source** for the entire agent system.
From these 4 files alone, all 16 agents can be reconstructed from scratch.

| File | Purpose |
|------|---------|
| `meta-deploy.md` | Bootstrap workflow; environment profiles (Claude/Codex/Ollama/Mixed); 6-stage deployment; validation checklist |
| `meta-tasks.md` | Global axioms (A1–A8); per-agent task specifications (PURPOSE, INPUTS, PROCEDURE, OUTPUT, STOP) |
| `meta-persona.md` | Per-agent personality, skills, decision styles, and critical behaviors |
| `meta-workflow.md` | Workflow state machine; agent handoff map; control protocols P1–P7; meta-evolution policy |

**Important:** `prompts/agents/*.md` files are **generated outputs — never edit them directly**. All changes must be made in `prompts/meta/*.md` and then regenerated via `Execute EnvMetaBootstrapper`. The meta files are the single source of truth for the entire agent system.

---

## 4. Initial Deployment (Bootstrapping)

### From Scratch

Place the 4 meta files in `prompts/meta/`. Then run:

```
Execute EnvMetaBootstrapper
Using meta-deploy.md
Input meta-tasks.md, meta-persona.md, meta-workflow.md
Target Claude
```

The bootstrapper will:
1. Initialize external memory files under `docs/`
2. Generate `agents/GLOBAL_RULES.md` (shared axiom inheritance)
3. Generate all 16 agent prompts (environment-optimized)
4. Run PromptAuditor on all generated prompts
5. Output an audit report and deployment notes

### First Agent to Run

```
Execute ResearchArchitect
```

ResearchArchitect loads `docs/ACTIVE_STATE.md`, maps your intent, and routes to the appropriate agent.

### File-Generation Mode (recommended for Claude Code)

Instruct the LLM to write files directly — no copy-paste:

> *"You are a file-generating agent. Read meta-tasks.md, meta-persona.md, and meta-workflow.md. Generate all agent prompt files directly into prompts/agents/. DO NOT print prompts inline."*

---

## 5. The Execution Loop

1. **Load state:** ResearchArchitect reads `docs/ACTIVE_STATE.md`
2. **Single-action discipline:** one agent, one objective per step (P5)
3. **Agent executes:** outputs a diff/patch; never rewrites full files
4. **Record decisions:** findings → `docs/ACTIVE_STATE.md`; new constraints → `docs/ASSUMPTION_LEDGER.md` (ASM-ID); violations → `docs/CHECKLIST.md` (CHK-ID)
5. **Hand off:** agent routes result to next agent per the handoff map in `meta-workflow.md`
6. **3-phase lifecycle:** each domain auto-commits at DRAFT, REVIEWED, and VALIDATED boundaries; auto-merges `{branch} → main` on ConsistencyAuditor / PromptAuditor GATE_PASS — independently per domain

---

## 6. Agent Roster

| Domain | Agent | Role |
|--------|-------|------|
| Session | ResearchArchitect | Session start, intent routing (cross-domain) |
| Code | CodeWorkflowCoordinator | Code domain orchestrator; drives DRAFT→REVIEWED→VALIDATED lifecycle |
| Code | CodeArchitect | Equation → Python implementation + MMS tests |
| Code | CodeCorrector | Staged numerical debugging (protocols A–D) |
| Code | CodeReviewer | Refactoring without numerical change |
| Code | TestRunner | Convergence analysis, PASS/FAIL verdict |
| Code | ExperimentRunner | Reproducible benchmark execution |
| Paper | PaperWorkflowCoordinator | Paper domain orchestrator; drives DRAFT→REVIEWED→VALIDATED lifecycle; auto-merges on gate PASS |
| Paper | PaperWriter | LaTeX manuscript authoring (skeptical verifier); returns to coordinator on completion |
| Paper | PaperReviewer | Rigorous peer review — output in Japanese |
| Paper | PaperCompiler | LaTeX compilation and repair (KL-12 guard) |
| Paper | PaperCorrector | Minimal targeted fixes from verified findings only |
| Verification | ConsistencyAuditor | Re-derives equations from first principles; VALIDATED gate for paper and code domains |
| Prompt | PromptArchitect | Generates role-specific agent prompts |
| Prompt | PromptCompressor | Reduces token usage without semantic loss |
| Prompt | PromptAuditor | Validates prompt correctness (read-only) |

---

## 7. Agent Collaboration Diagram

```mermaid
flowchart TD
    User([User]) --> RA

    subgraph session[Session Start — cross-domain]
        RA[ResearchArchitect]
    end

    subgraph code[Code Domain — branch: code]
        CWC[CodeWorkflowCoordinator]
        CArc[CodeArchitect]
        CRev[CodeReviewer]
        CCor[CodeCorrector]
        TR[TestRunner]
        ER[ExperimentRunner]
    end

    subgraph paper[Paper Domain — branch: paper]
        PWC[PaperWorkflowCoordinator]
        PW[PaperWriter]
        PR[PaperReviewer]
        PCor[PaperCorrector]
        PC[PaperCompiler]
    end

    subgraph verify[Verification — Domain Gate]
        CA[ConsistencyAuditor]
    end

    subgraph prompts[Prompt System — branch: prompt]
        PArc[PromptArchitect]
        PCmp[PromptCompressor]
        PAud[PromptAuditor]
    end

    MERGE_PAPER([merge paper → main])
    MERGE_CODE([merge code → main])
    MERGE_PROMPT([merge prompt → main])

    %% Session routing
    RA -->|code pipeline| CWC
    RA -->|paper pipeline| PWC
    RA -->|paper write only| PW
    RA -->|experiment| ER
    RA -->|cross-validate| CA
    RA -->|prompt task| PArc

    %% Code domain flow
    CWC --> CArc
    CWC --> CRev
    CRev -->|migration plan| CArc
    CArc -->|impl done| TR
    TR -->|PASS — draft commit| CWC
    TR -->|FAIL — STOP| CCor
    CCor -->|fix applied| TR
    ER -->|verified data| PWC
    CWC -->|all PASS — reviewed commit| CA
    CA -->|CODE_ERROR| CArc
    CA -->|GATE_PASS — validated commit + merge| MERGE_CODE

    %% Paper domain flow — loop until no FATAL/MAJOR, then auto-merge
    PWC -->|dispatch write| PW
    PW -->|writing complete — auto-commit draft| PWC
    PWC -->|dispatch compile| PC
    PWC -->|dispatch review| PR
    PWC -->|dispatch fix| PCor
    PR -->|findings| PWC
    PCor -->|fix result| PWC
    PC -->|unresolvable error| PW
    PWC -->|no FATAL/MAJOR — reviewed commit| CA
    CA -->|PAPER_ERROR| PW
    CA -->|GATE_PASS — validated commit + merge| MERGE_PAPER

    %% Prompt system flow
    PArc -->|generated| PAud
    PCmp -->|compressed| PAud
    PAud -->|FAIL| PArc
    PAud -->|PASS — auto-commit + auto-merge| MERGE_PROMPT
```

**Reading the diagram:**
- Every domain follows the same 3-phase lifecycle: **DRAFT commit → REVIEWED commit → VALIDATED commit + merge**
- `FAIL — STOP` means the agent halts and waits for user direction before CCor is invoked
- **PaperWriter always returns to PaperWorkflowCoordinator** — it does not stop autonomously; coordinator issues the DRAFT commit
- **Code domain:** DRAFT commit per component (TestRunner PASS); REVIEWED commit when all components pass; VALIDATED commit + merge after ConsistencyAuditor GATE_PASS
- **Paper domain:** DRAFT commit after PaperWriter returns; REVIEWED commit when review loop clears; VALIDATED commit + merge after ConsistencyAuditor GATE_PASS
- **Prompt domain:** DRAFT commit after PromptArchitect/Compressor; VALIDATED commit + merge after PromptAuditor PASS (no separate REVIEWED phase)
- Each domain merges to `main` **independently** — no cross-domain wait

---

## 8. Control Protocols

Defined in `meta-workflow.md`. Key protocols:

| Protocol | Purpose |
|----------|---------|
| P1 LAYER_STASIS | When editing one layer, all others are READ-ONLY |
| P2 NON_INTERFERENCE_AUDIT | Infrastructure changes must not alter numerical results |
| P3 ASSUMPTION_TO_CONSTRAINT | Stable assumptions promoted to constraints with ASM-ID |
| P4 CONTEXT_COMPRESSION_GATE | Token efficiency before DONE / schema migration / prompt regeneration |
| P5 SINGLE-ACTION DISCIPLINE | One agent, one objective per step — no multi-goal execution |
| P6 BOUNDED LOOP CONTROL | Retry counter per phase; escalate on threshold breach; never loop silently |
| P7 LEGACY MIGRATION | Old prompts/schemas mapped, compressed, and upgraded; semantics preserved |

---

## 9. Meta Rules

- **diff > rewrite** — minimal changes only
- **stop early > guess** — STOP and escalate when information is missing; never hallucinate
- **explicit > implicit** — all decisions in `docs/` with IDs; never rely on LLM context window
- **one agent per step** — no multi-goal execution inside a single action
- **test failure = halt** — TestRunner and WorkflowCoordinator never auto-fix; they STOP and ask
- **authority chain** — MMS-passing code > ARCHITECTURE.md > paper (ConsistencyAuditor enforces)
