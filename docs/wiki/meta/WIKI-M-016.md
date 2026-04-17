# WIKI-M-016: Design Philosophy Synthesis — The 3 Pillars
**Category:** Meta | **Created:** 2026-04-18
**Sources:** `prompts/meta/meta-core.md` (§A–§C, §SYSTEM OPTIMIZATION TARGETS, §OPERATIONAL PHILOSOPHY, §LLM APTITUDE PRINCIPLES)

## Overview

The meta-prompt system is built on three interconnected design pillars. Every operational
rule, every constraint, and every protocol can be traced back to one or more of these pillars.
Understanding the pillars is prerequisite to understanding why the system is structured as it is.

---

## Pillar 1 — Corporate Autonomy (§A)

**Statement:** Each domain is a sovereign unit. Agents own their territory; they do not negotiate
access or receive unsolicited corrections from outside their domain.

**Key properties:**
- Domains have exclusive write territories (enforced by DOM-01/02 and LOCK-ACQUIRE)
- Cross-domain interactions happen only through signed Interface Contracts (GIT-00, IF-Agreement)
- An agent that writes outside its `write_territory` triggers CONTAMINATION_GUARD (DOM-02, STOP-03)
- No domain may "help" another by directly editing its files — it must DISPATCH via HAND-01

**Why it exists:** Without sovereignty, a well-intentioned fix in one domain silently invalidates
work in another. Corporate Autonomy makes boundary crossings explicit, auditable, and reversible.

---

## Pillar 2 — Broken Symmetry (§B)

**Statement:** The agent that creates an artifact must never be the same agent that validates it.
Context isolation is the practical gate (φ7, MH-3).

**Key properties:**
- Creator (Specialist) and Auditor (Gatekeeper/Reviewer) operate in separate contexts (L3 isolation for critical audits)
- HAND-03 check C6 (Phantom Reasoning Guard) enforces this: if Specialist CoT is in the DISPATCH inputs, the Auditor must REJECT
- CoVe (Chain-of-Verification) is a self-check by the Specialist BEFORE handoff — it does NOT replace independent verification
- "Verified by comparison only" is explicitly classified as broken symmetry (STOP-HARD)

**Isolation levels used:**
| Level | Description | When used |
|-------|-------------|-----------|
| L0 | Same context window | Same-agent iterative refinement |
| L1 | Prompt-boundary (no prior history) | Specialist → Gatekeeper within session |
| L2 | Tool-mediated (numerical computations delegated to tools) | All verification steps |
| L3 | Session-isolated (separate Claude Code invocation) | AU2 gate, TheoryAuditor re-derivation |

**Why it exists:** An agent that audits its own work rationalizes its own errors. Broken Symmetry
forces a second, independent reasoning path. If both paths converge, confidence is high; if they
diverge, a real problem has been found — not hidden.

---

## Pillar 3 — Falsification Loop (§C)

**Statement:** Agents must actively attempt to falsify their own artifacts before declaring them
correct. Affirmation is cheap; attempted refutation is the only meaningful quality signal.

**Key properties:**
- AUDIT-03 (Adversarial Edge-Case Gate) is the operational form: identify boundary conditions, predict failure, probe, classify (THEORY_ERR / IMPL_ERR / SCOPE_LIMIT)
- AP-03 (Verification Theater) is the failure mode: generating pro-forma "no issues found" answers without genuine adversarial reasoning
- CoVe Q1/Q2/Q3 are structured adversarial questions, not checklists to mark complete
- TheoryAuditor's first action after accepting a DISPATCH is independent derivation BEFORE opening the artifact (HAND-03 C6)

**Why it exists:** LLMs are optimized to produce fluent, confident output — including fluent, confident
wrong output. The Falsification Loop counteracts this by requiring agents to act as adversaries
to their own work, not advocates.

---

## How the Pillars Interlock

The three pillars are **mutually reinforcing**. Removing any one breaks the system:

| Remove | Consequence |
|--------|-------------|
| Corporate Autonomy | Domains become entangled; a change in one area silently invalidates another; contamination becomes undetectable |
| Broken Symmetry | Creators audit their own work; systematic errors survive undetected through P-E-V-A |
| Falsification Loop | Auditors become rubber-stampers; AP-03 Verification Theater proliferates; errors reach main |

The pillars together form a closed loop: sovereignty makes boundaries explicit (so contamination is detectable),
broken symmetry ensures independent eyes cross those boundaries, and falsification ensures
those eyes actually try to find problems.

---

## MH-1/2/3: Mechanical Harmonization Principles

Three operational principles that translate the pillars into agent behavior:

### MH-1: Stop is Progress
A STOP triggered by detecting a contradiction is more valuable than proceeding with flawed reasoning.
An agent that halts on a conflict and reports it produces a recoverable state.
An agent that guesses and continues produces untracked, unauditable state (φ1, φ5).

**Corollary:** A STOP returned with a clear trigger is a successful agent action.
A STOP concealed by a guess is a traceability violation.

### MH-2: The Ledger is the Truth
Any reasoning not recorded in `docs/02_ACTIVE_LEDGER.md` is non-existent to the system.
An agent's in-context conclusions that are not externalized are lost at session end (φ4).

**Practical implication:** Before relying on a prior decision, verify it exists in the Ledger.
If absent, re-derive or re-classify — do not rely on recall.

### MH-3: Broken Symmetry
The Executor (Specialist) and the Validator (Auditor) must never follow the same reasoning path.
If they share the same assumptions, the same bugs survive both checks.

**Practical implementation:** Use separate context windows (L3 for critical audits). Do not
expose Specialist chain-of-thought to the Auditor (HAND-03 C6 enforces this mechanically).

---

## System Optimization Targets

All agents share these optimization priorities (in priority order):

1. correctness
2. traceability
3. reproducibility
4. solver purity
5. structural integrity
6. token efficiency
7. external-memory efficiency
8. self-evolution
9. backward compatibility

Items 1–5 are correctness/integrity properties. Items 6–9 are operational efficiency properties.
Efficiency is never traded for correctness.

---

## LA-1..LA-5: LLM Aptitude Principles

LLMs have specific cognitive strengths and weaknesses. All agent designs account for these constraints.

### LA-1: Task Aptitude Matrix

| Aptitude | Description | Examples | Rule |
|----------|-------------|----------|------|
| **LLM-NATIVE** | LLM excels natively | Derivation, prose, code generation, reasoning, pattern recognition | Assign directly |
| **TOOL-DELEGATE** | Requires precision LLMs cannot guarantee | Numerical comparison, hash verification, file existence, git state, exact string matching, counting | Agent MUST delegate to tool — never in-context |
| **HUMAN-GATE** | Requires judgment beyond system authority | Ambiguous physical assumptions, competing design tradeoffs, publication decisions, scope changes | STOP and escalate — never approximate |

**Hard rule:** An agent performing a TOOL-DELEGATE task in-context commits a **Reliability Violation**.
The result is untrustworthy regardless of whether it appears correct.

### LA-2: Context Saturation Awareness

LLM performance degrades when the context window is saturated with rules rather than task content.

**Guideline:** Agent prompt + expected inputs ≤ 60% of effective context window.
The remaining 40% is reserved for reasoning and output generation.
Stage 4 of EnvMetaBootstrapper enforces this: prompts exceeding 60% are REJECTED.

### LA-3: State Tracking Limitation

LLMs cannot reliably track mutable state across long conversations. All persistent state must be externalized.

**This is a capability constraint, not a design preference** (extends φ4): git branch state, loop counters,
domain lock status, and review round counts must be verified by tool invocation at each step —
never assumed from prior context.

### LA-4: Rule Load Budgeting

More rules in context ≠ higher compliance. Beyond saturation threshold, compliance falls.

**Hard rule:** Each agent prompt declares a `RULE_BUDGET`. At dispatch time, only rules matching
the agent's domain and archetypal role are loaded. Cross-domain axioms (A1–A11) and φ-principles
are always included; other domains' specific rules are excluded unless the task explicitly crosses boundaries.

**Priority for inclusion when near budget:**
1. Stop conditions and CONTAMINATION rules (always — omitting them is worse than saturation)
2. Role-specific DELIVERABLES and CONSTRAINTS
3. Handoff protocol (HAND-01/02/03)
4. Cross-domain axioms (A1–A11)
5. φ-principles (summarized form acceptable)
6. Routing/dispatch details (coordinator/Gatekeeper roles only)

### LA-5: Dynamic Rule Injection via RULE_MANIFEST

Agent prompts declare a **RULE_MANIFEST** — rules are always/domain/on-demand, not all static:

```yaml
RULE_MANIFEST:
  always:     [STOP_CONDITIONS, DOM-02_CONTAMINATION_GUARD, SCOPE_BOUNDARIES, HAND-03_QUICK_CHECK]
  domain:
    code:     [C1-SOLID, C2-PRESERVE, A9-SOVEREIGNTY, MMS-STANDARD]
    paper:    [P1-LATEX, P4-SKEPTICISM, KL-12]
    theory:   [A3-TRACEABILITY, AU1-AUTHORITY]
    prompt:   [Q1-TEMPLATE, Q3-AUDIT, Q4-COMPRESSION]
    audit:    [AU2-GATE, PROCEDURES-A-E]
  on_demand:  # JIT pointer — retrieve only when operation is needed in current step
    HAND-01:  "→ read prompts/meta/meta-ops.md §HAND-01"
    AUDIT-01: "→ read prompts/meta/meta-ops.md §AUDIT-01"
    ...
```

**on_demand rule:** Agent must `Read` the specified file/section only when that operation is needed.
NOT preloaded at session start. If on_demand file unavailable → STOP; never improvise from memory.
Token savings: ~30–40% reduction vs. static embedding.

---

## Authority Tiers

| Tier | Who | Key Capabilities |
|------|-----|-----------------|
| Root Admin | ResearchArchitect (system-level decisions) | GIT-04 Phase B merge, PATCH-IF, system configuration changes |
| Gatekeeper | Domain coordinators, reviewers, auditors | GIT-02/03/04 Phase A, DOM-01 lock establishment, HAND-01 dispatch, AUDIT-01/02/03 |
| Specialist | Domain workers | File writes within write_territory, HAND-02 return, CoVe self-check, LOCK-ACQUIRE/RELEASE |

---

## Design Philosophy Summary

> **Every constraint exists to eliminate a failure mode.**

- STOP conditions exist because an undetected error is worse than a halt
- Domain sovereignty exists because silent cross-domain contamination is undetectable after the fact
- Broken symmetry exists because LLMs rationalize their own errors
- Falsification exists because affirmation is computationally cheap and epistemically worthless
- Statelessness exists because LLM in-context state tracking is unreliable (LA-3)
- JIT rule loading exists because context saturation degrades compliance (LA-2, LA-4)

The system is designed around **the specific failure modes of LLM agents**, not around abstract software
engineering principles. Each rule is a scar from a failure mode that was observed, classified, and encoded.

---

## Cross-References

- `→ WIKI-M-015`: Constitutional origins — when and why the pillars were formalized
- `→ WIKI-M-017`: Constitutional layer full text (φ1–φ7, A1–A11 verbatim)
- `→ WIKI-M-011`: Anti-pattern catalogue — the failure modes each pillar guards against
- `→ WIKI-M-019`: Workflow protocols — how the pillars manifest in P-E-V-A and pipeline rules
