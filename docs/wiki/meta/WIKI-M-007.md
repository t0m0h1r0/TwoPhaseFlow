---
id: WIKI-M-007
title: "Agent Meta System: K-Domain (Knowledge/Wiki) + meta-project Profile Swap Pattern"
status: ACTIVE
created: 2026-04-12
updated: 2026-04-12
depends_on: [WIKI-M-004]
---

# Agent Meta System: K-Domain + Project Profile Swap

## Motivation

Two distinct but temporally adjacent additions (2026-04-05 and 2026-04-07) both
addressed the same underlying problem: **the meta system mixed universal rules with
project-specific knowledge**, and knowledge that should have been reused across
sessions was re-derived every time.

The two additions:
1. **meta-project.md** (`4612223`, 2026-04-05) — extract project-specific rules into
   a swappable profile, leaving universal files untouched when changing projects
2. **K-Domain** (`9da3f9e`, 2026-04-07) — add a 5th horizontal governance domain for
   structured knowledge compilation and retrieval (`docs/wiki/`)

Together these form the **"LLM as Compiler, Wiki as OS"** architecture principle:
the agent (LLM) compiles requests into actions; the wiki (K-Domain) is the
persistent knowledge store that the agent reads and writes across sessions.

---

## Addition 1 — meta-project.md Profile Swap Pattern (2026-04-05)

**Problem:** `docs/00_GLOBAL_RULES.md` contained project-specific rules (CFD-specific
C4/C6/C7) mixed with universal rules (C1–C4 that apply to any project). To port
this system to a different project, a developer would have to edit multiple meta
files, each containing some project assumptions.

**Solution:** Layer P (project profile) — a single `meta-project.md` file carrying
ALL project-specific rules as PR-1 through PR-N:

```
Layer 1 (meta/):              Universal — same for any project
Layer P (meta-project.md):    Project-specific — swappable
Layer 2 (docs/00):            Derived from Layer 1 + Layer P
Layer 3 (docs/01–02):         Project state
```

**Current PR rules (CFD/CCD project):**

| PR-ID | Rule | Rationale |
|-------|------|-----------|
| PR-1 | CCD Primacy — 6th-order compact differences for all derivatives | Paper claim (§3) |
| PR-2 | Implicit Solver Policy — CCD+LU for CCD-PPE, FD-precond GMRES for 3D | §8c |
| PR-3 | MMS Verification Standard — order ≥ 5.5 for 6th-order methods | §11 |
| PR-4 | Experiment Infrastructure Toolkit — `src/twophase/experiment/` package | Infrastructure |
| PR-5 | Algorithm Fidelity — fixes MUST restore paper-exact behavior | Anti-drift |
| PR-6 | PPE Policy — No LGMRES for PPE (use DC k=3 + LU) | §8c empirical |

**Portability protocol:** to port to a new project:
1. Replace `meta-project.md` with project-appropriate PR-rules
2. Regenerate `docs/03_PROJECT_RULES.md` from the new `meta-project.md`
3. Update `_base.yaml` `project_rules` reference if PR-IDs change
4. Universal files (meta-core, meta-domains, meta-ops) require **NO changes**

**Why this matters now:** this is the reason the meta system can be treated as a
reusable infrastructure. Without Layer P separation, every new project would
require a full meta-system rewrite. With it, the project-specific content is a
single file with a documented swap procedure.

---

## Addition 2 — K-Domain (Knowledge/Wiki) (2026-04-07)

**Problem:** knowledge derived during one session (e.g., "why CCD-PPE requires
Kronecker assembly") was recomputed every subsequent session that needed it. Agents
had no persistent memory beyond `docs/02_ACTIVE_LEDGER.md` (which tracks state, not
knowledge). The cost of re-derivation was both token-expensive and error-prone —
each re-derivation had a small chance of producing a subtly different answer.

**Solution:** K-Domain as the 5th horizontal governance domain, with its own axioms,
agents, and storage territory.

**4×4 → 4×5 matrix extension:**

```
                     M        P        Q        K (NEW)
┌──────────┬────────┬────────┬────────┬──────────────┐
│ T Theory │        │        │        │ Theory wiki  │
│ L Library│        │        │        │ API/arch wiki│
│ E Experm.│        │        │        │ Result wiki  │
│ A Paper  │        │        │        │ Paper wiki   │
└──────────┴────────┴────────┴────────┴──────────────┘
```

**K-Domain axioms (K-A1 through K-A5):**

| Axiom | Name | Rule |
|-------|------|------|
| K-A1 | Knowledge-First Retrieval | Before deriving, check `docs/wiki/` for existing compilation |
| K-A2 | Pointer Integrity | `[[REF-ID]]` links MUST resolve to existing entries (enforced by WikiAuditor) |
| K-A3 | Single Source of Truth | Each concept has exactly one canonical wiki entry (lifecycle DEPRECATED/SUPERSEDED for replacements) |
| K-A4 | Derivation Must Cite Source | Wiki entries MUST cite their source (paper section, commit hash, experiment run) |
| K-A5 | RE-VERIFY on Upstream Change | When upstream code/paper changes, affected wiki entries get `RE-VERIFY` signal |

**A11 (Knowledge-First Retrieval)** was added to meta-core.md at the same time as
an axiom-level corollary: any agent that would derive a fact MUST first search the
wiki. The derivation happens only if no wiki entry exists.

---

## K-Domain Agents

Four new agents, all Specialists with strict read/write territorial scope:

| Agent | Role | Writes | Reads |
|-------|------|--------|-------|
| KnowledgeArchitect | Compile derived knowledge into wiki entries | `docs/wiki/**/WIKI-*.md` | All artifacts, all domains |
| WikiAuditor | Verify pointer integrity + K-A1..K-A5 compliance | (audit reports) | `docs/wiki/` |
| Librarian | Maintain wiki index + duplicate-to-pointer refactoring | `docs/wiki/INDEX.md` | `docs/wiki/` |
| TraceabilityManager | Map upstream changes → affected wiki entries | (signals) | `docs/wiki/`, git diff |

**Gatekeeper:** WikiAuditor is the K-Domain Gatekeeper — only it can approve new
wiki entries. K-LINT is the verdict it issues on proposed entries.

---

## K-OPERATIONS (meta-ops.md §K-*)

New operations specific to the K-Domain:

| Operation | Purpose | Invoked by |
|-----------|---------|-----------|
| K-COMPILE | Convert artifact → wiki entry | KnowledgeArchitect |
| K-LINT | Verify K-A1..K-A5 on proposed entry | WikiAuditor |
| K-DEPRECATE | Mark an entry as superseded; add SUPERSEDED_BY pointer | WikiAuditor |
| K-REFACTOR | Refactor duplicate entries into a canonical + pointers | Librarian |
| K-IMPACT-ANALYSIS | Find wiki entries affected by an upstream change | Librarian / TraceabilityManager |

---

## Wiki Directory Structure

```
docs/wiki/
├── INDEX.md                (maintained by Librarian)
├── theory/                 (T-Domain knowledge)
├── code/                   (L-Domain knowledge)
├── experiment/             (E-Domain knowledge)
├── paper/                  (A-Domain knowledge)
├── cross-domain/           (T-L-E-A spanning knowledge)
├── meta/                   (meta-system knowledge ← THIS FILE)
└── changelog/              (dated version notes)
```

**REF-ID convention:**

| Prefix | Domain | Example |
|--------|--------|---------|
| WIKI-T-NNN | Theory | WIKI-T-001 CCD Method Design Rationale |
| WIKI-L-NNN | Library (code) | WIKI-L-008 Library Architecture |
| WIKI-E-NNN | Experiment | WIKI-E-015 §13 Benchmark Suite |
| WIKI-P-NNN | Paper | WIKI-P-003 Problem Statement |
| WIKI-X-NNN | Cross-domain | WIKI-X-004 Pressure Instability |
| WIKI-M-NNN | Meta | WIKI-M-006 Micro-Agent Architecture |

---

## File Count Discipline (12 → 10)

The K-Domain initially added two new meta files (`meta-knowledge.md`,
`meta-knowledge-roles.md`), temporarily bringing `prompts/meta/` to 12 files.
On 2026-04-07 (`50cbf01`), these were consolidated into the existing
`meta-domains.md` (domain registry extended with K-Domain rows) and `meta-roles.md`
(4 new role contracts), bringing the count back to 10.

**Rationale:** file count is an LA-4 token budget concern — each meta file has a
baseline load cost. Consolidating K-Domain into existing files avoided inflating
the budget while adding a major new domain.

**Policy going forward:** `prompts/meta/` SHOULD remain at ≤ 10 files. New features
extend existing files; new files require explicit justification that they cannot
fit in any existing file.

---

## "LLM as Compiler, Wiki as OS" Principle

The architectural claim underlying K-Domain: an LLM-agent is analogous to a
**compiler** — it takes a request (source code) and produces actions (object code).
The **wiki** is the **operating system** — it provides persistent services
(knowledge retrieval, memoization, cross-session state) that the compiler depends
on but does not own.

**Implications:**
- A session starts with zero knowledge; it loads from the wiki as needed (K-A1)
- A session ends; new knowledge is compiled back into the wiki (K-COMPILE)
- The wiki is the cross-session memory; agents are ephemeral
- A consistent wiki is more valuable than a clever single session

**This is why the wiki is Layer 2 (execution layer), not Layer 3 (state layer).**
Layer 3 (`docs/02_ACTIVE_LEDGER.md`) is session-lifecycle state. Layer 2 is
persistent system infrastructure. The wiki is infrastructure, not state.

---

## Source

- `prompts/meta/meta-core.md §A11 Knowledge-First Retrieval`
- `prompts/meta/meta-domains.md §K-Domain` (registry + K-A1..K-A5 axioms)
- `prompts/meta/meta-ops.md §KNOWLEDGE OPERATIONS` (K-COMPILE/LINT/DEPRECATE/REFACTOR/IMPACT)
- `prompts/meta/meta-persona.md` (KnowledgeArchitect, WikiAuditor, Librarian, TraceabilityManager profiles)
- `prompts/meta/meta-roles.md` (K-Domain role contracts)
- `prompts/meta/meta-project.md` (PR-1..PR-6 CFD/CCD rules)
- Commits:
  - `4612223` (2026-04-05) meta-project architecture for universal/project-specific rule separation
  - `9da3f9e` (2026-04-07) add Domain K (Knowledge/Wiki) — 5th horizontal governance domain
  - `50cbf01` (2026-04-07) consolidate K-Domain files into meta-domains.md — 12→10 meta files

## Related entries

- [[WIKI-M-004]] Constitutional Foundations — 3-layer architecture that K-Domain extends
- [[WIKI-M-002]] v4.1 3-Pillar Protocol — Schema-in-Code discipline applies to K-Domain agents too
- [[WIKI-M-006]] Micro-Agent Architecture — SIGNAL protocol is the coordination mechanism for K-Domain TraceabilityManager
