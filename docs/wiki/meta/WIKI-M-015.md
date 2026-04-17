# WIKI-M-015: Pre-Constitutional History + 3-Layer Architecture Birth
**Category:** Meta | **Created:** 2026-04-18
**Sources:** git log (2026-03-27 → 2026-03-29), `docs/00_GLOBAL_RULES.md`, `prompts/meta/meta-core.md`

## The Pre-Constitutional Era (before 2026-03-28)

The initial system (~12 agents, deployed 2026-03-27) had no meta-layer. Its characteristics:
- All agents lived in a single `prompts/agents/` directory as standalone Markdown files
- Documentation lived in `prompts/docs/` (co-located with prompts, not top-level)
- Rules were embedded directly in each agent file — axioms and constraints were duplicated verbatim across all agents
- No `prompts/meta/` directory; no φ-principles; no A1–A11 axiom system
- No domain sovereignty: any agent could reference any file without authorization
- No SSoT discipline: a rule change required editing all 12 files individually
- No handoff protocol: coordination between agents was informal

The absence of a governance layer meant the system was brittle under change: adding a new
rule required N edits (one per agent), and inconsistencies accumulated silently.

---

## The March 2026 Constitutional Refactoring

Four sequential commits on 2026-03-28 established the entire constitutional framework.

### Commit `92082d6` — 3-Layer Architecture + φ1–φ6

**What changed:**
- Created `docs/00_GLOBAL_RULES.md`, `docs/01_PROJECT_MAP.md`, `docs/02_ACTIVE_LEDGER.md`
  (migrating from the old `prompts/docs/` location to top-level `docs/`)
- Deleted 7 old docs files (ARCHITECTURE.md, CODING_POLICY.md, LATEX_RULES.md, etc.)
- Deleted `prompts/agents/GLOBAL_RULES.md` (rules now live in docs, not prompts)
- Established the 3-layer authority hierarchy
- Introduced φ1–φ6 design principles
- All 16 agents regenerated to cite the canonical docs files

**Why this was needed:** Scattered rules caused divergence between agents. The old structure
had no single authoritative source — the architecture document could contradict a coding
policy document, and neither had formal precedence.

### Commit `b9ce96e` — A9 Domain Sovereignty + Error Classification

**What changed:**
- Added **A9: Core/System Sovereignty** — "The solver core is the master; the infrastructure is the servant." `src/core/` never imports from `src/system/`. Violation = contamination.
- Added **THEORY_ERR / IMPL_ERR** error classification taxonomy: errors must be classified before routing (THEORY_ERR → theory domain; IMPL_ERR → code domain)
- English-First rule introduced (agent output must be in English regardless of user language)

**Why this was needed:** Without domain sovereignty, a code change in the infrastructure
layer could inadvertently affect numerical results in the solver core. The THEORY_ERR /
IMPL_ERR taxonomy prevents errors from being routed to the wrong correction domain.

### Commit `75033e9` — 7-File Meta-System + A10 + AUDIT-01/02 + DOM-01/02

**What changed:**
- Created `prompts/meta/` directory with 7 files: `meta-core.md`, `meta-domains.md`,
  `meta-persona.md`, `meta-roles.md`, `meta-ops.md`, `meta-workflow.md`, `meta-deploy.md`
- Resolved 11 structural violations (V1–V11) for φ6 Single Source
- Added **A10: Meta-Governance** — `prompts/meta/` is the SSoT; `docs/` are derived
- Added **AUDIT-01** (AU2 10-item release gate) and **AUDIT-02** (5-procedure mathematical verification)
- Added **DOM-01 / DOM-02** domain operations

**Why this was needed:** The 3-layer docs architecture (commit `92082d6`) established where
rules lived, but not how rules were generated or validated. The meta-system provided the
"compiler" layer: meta-files are the source; docs and agent prompts are the derived artifacts.
φ6 (Single Source) mandates that you change the source, never the derived artifact directly.

### Commit `ff01c6e` — HAND-03 Expansion + GIT-01 + DOM Specs

**What changed:**
- Expanded HAND-03 rejection protocol (Acceptance Check)
- Added GIT-01 auto-switch (branch alignment enforcement)
- DOM-01 and DOM-02 full specifications
- Sharpened per-agent STOP conditions
- Introduced CRITICAL_VIOLATION + THEORY_ERR/IMPL_ERR in ConsistencyAuditor

---

## The 3-Layer Authority Hierarchy

The core architectural insight of the March 2026 refactoring:

```
Layer 1 — Abstract Meta:    prompts/meta/          ← WHY (axioms, philosophy, SSoT)
Layer 2 — Universal Rules:  docs/00_GLOBAL_RULES   ← WHAT (project-universal rules, derived)
Layer 3 — Live Context:     docs/01_PROJECT_MAP    ← WHERE/WHICH (module map, interfaces)
                            docs/02_ACTIVE_LEDGER  ← WHEN/STATUS (phase, CHK/KL registers)
```

**Authority resolution rule:** When sources conflict: meta/ wins on axiom intent → docs/00 wins
on rule interpretation → docs/01–02 win on project state. No mixing across layers.

**Key property:** docs/ files are derived from prompts/meta/. Any rule change must happen
in meta/ first, then docs/ is regenerated via EnvMetaBootstrapper. Direct edits to docs/ are
a φ6 violation.

---

## The 3-Phase Domain Lifecycle

Introduced alongside the 3-layer architecture on 2026-03-28:

| Phase | Trigger | Commit message pattern |
|-------|---------|----------------------|
| DRAFT | Work begins on a domain branch | `{domain}({scope}): ...` |
| REVIEWED | Gatekeeper accepts the artifact | Merge commit with review tag |
| VALIDATED | Tests pass + AU2 gate clears | Merge to integration branch |

This replaced ad-hoc commits with a formal lifecycle enforced by the HAND-01/02/03 protocol.

---

## φ1–φ7 Core Principles

| ID | Name | TL;DR | Introduced |
|----|------|-------|------------|
| φ1 | Truth Before Action | Evidence before action — stop and read before you fix | `92082d6` |
| φ2 | Minimal Footprint | Do exactly what is authorized — scope creep is a traceability violation | `92082d6` |
| φ3 | Layered Authority | When sources conflict, the hierarchy resolves it — first principles win | `92082d6` |
| φ4 | Stateless Agents | If it's not in docs/ or git, it doesn't exist to the system | `92082d6` |
| φ5 | Bounded Autonomy | Every workflow has hard gates — human judgment at boundaries | `92082d6` |
| φ6 | Single Source, Derived Artifacts | Change the source in prompts/meta/; never patch a derived artifact | `92082d6` |
| φ7 | Classification Precedes Action | Reviewers classify; correctors act — merging roles destroys the audit trail | v3.0.0 era (2026-04-02) |

---

## A1–A11 Axiom System

The axioms are operational rules derived from the φ-principles:

| ID | Name | Parent φ | Introduced |
|----|------|----------|------------|
| A1 | Token Economy | φ2 | `92082d6` |
| A2 | External Memory First | φ4 | `92082d6` |
| A3 | 3-Layer Traceability | φ1 + φ3 | `92082d6` |
| A4 | Separation | φ7 | `92082d6` |
| A5 | Solver Purity | φ3 | `92082d6` |
| A6 | Diff-First Output | φ2 | `92082d6` |
| A7 | Backward Compatibility | φ2 + φ6 | `92082d6` |
| A8 | Git Governance | φ4 + φ5 | `92082d6` |
| A9 | Core/System Sovereignty | φ3 | `b9ce96e` (same day) |
| A10 | Meta-Governance | φ6 | `75033e9` (same day) |
| A11 | Knowledge-First Retrieval | φ4 + φ6 | `9da3f9e` (2026-04-07, with K-Domain) |

The progression A1–A8 (initial) → A9 (sovereignty) → A10 (meta-governance) → A11 (knowledge-first)
reflects the order in which failure modes were identified and formalized as axioms.

---

## What WIKI-M-004 Covers vs This Entry

WIKI-M-004 covers the constitutional foundations at the level of what the system looks like
after the refactoring (3-Layer architecture shape, A9 sovereignty principle, 3-phase lifecycle
rules). This entry covers the *origin*: what existed before, why the refactoring was
necessary, and the sequence of commits that established the system — providing the "from
where" context that WIKI-M-004 assumes as background.

---

## Cross-References

- `→ WIKI-M-004`: Constitutional Foundations — the resulting architecture in operational detail
- `→ WIKI-M-007`: K-Domain + A11 addition (the final axiom)
- `→ WIKI-M-012`: Agent roster evolution (the 16-agent roster that was regenerated in `92082d6`)
- `→ WIKI-M-014`: EnvMetaBootstrapper — the "compiler" that φ6 mandates as the generation path
- `→ docs/00_GLOBAL_RULES.md §A`: the current A1–A11 table derived from this constitutional work
