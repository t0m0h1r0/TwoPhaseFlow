---
id: WIKI-M-004
title: "Agent Meta System: Constitutional Foundations (3-Layer Architecture + 3-Phase Lifecycle + A9 Sovereignty)"
status: ACTIVE
created: 2026-04-12
updated: 2026-04-12
depends_on: []
---

# Agent Meta System: Constitutional Foundations

## Motivation

Before the March 2026 constitutional refactoring, `prompts/meta/` was a flat collection
of role descriptions with duplicated rules scattered across files. The 2026-03-28
refactoring campaign (`92082d6`, `fd92d3a`, `b9ce96e`, `75033e9`) established the
three structural invariants that all later evolution (v4.1 / v5.1 / v5.2) builds on:

1. **3-Layer Architecture** — meta / docs/00 / docs/01-02 separation
2. **3-Phase Lifecycle** — DRAFT → REVIEWED → VALIDATED commit discipline
3. **A9 Domain Sovereignty** — Core vs. System vs. Interface territorial ownership

Without these, the v4.1 SSoT discipline and v5.1 worktree concurrency would have no
stable substrate to sit on.

---

## Foundation 1 — 3-Layer Architecture (2026-03-28, `92082d6`)

**Problem:** meta-*.md files contained both abstract rules (A1–A8 axioms, philosophical
principles) and concrete rule text (C1–C6 code rules, P1–P4 paper rules). Edits
produced drift between the abstract and concrete layers, and agents loading meta files
paid the token cost of both.

**Solution:** Three-layer separation with single-direction authority flow:

```
Layer 1 (meta/):            Abstract rules & axioms (A1–A11, φ1–φ7)
                            ↓ cited by
Layer 2 (docs/00):          Authoritative concrete rule source (C/P/Q/AU/GIT)
                            ↓ referenced by
Layer 3 (docs/01–02):       Project-specific state (docs/01 map, docs/02 active ledger)
```

**Key rules:**
- `docs/00_GLOBAL_RULES.md` is the **authoritative SSoT** for rule text, NOT a derived cache
- `prompts/meta/*.md` may cite `docs/00_GLOBAL_RULES.md §C1` but never inline the rule body
- `docs/01_PROJECT_MAP.md` holds project state (not rules)
- `docs/02_ACTIVE_LEDGER.md` holds phase/CHK state only (no rule content)

**Authority rule** (from meta-core.md): `meta-core.md` wins on axiom intent;
`docs/00_GLOBAL_RULES.md` wins on rule interpretation; `docs/01–02` wins on project state.
**No mixing allowed** (A10).

**Why this matters now:** Every v4.1/v5.1/v5.2 change that touches rule text must
decide whether it belongs in meta (abstract) or docs/00 (concrete). The decision is
no longer free — it is forced by the layer dependency rule.

---

## Foundation 2 — 3-Phase Lifecycle (2026-03-28, `fd92d3a`)

**Problem:** Before v3, branches had ad-hoc commit semantics. Some branches merged to
`main` via direct push, others via PR, and there was no uniform way to signal "this
work is ready for review" vs. "this work is merged and validated."

**Solution:** All domain branches (`code`, `paper`, `prompt`, `dev/*`) follow a
unified 3-phase lifecycle with per-phase commit triggers:

| Phase | Trigger | Gatekeeper action |
|-------|---------|-------------------|
| DRAFT | Specialist begins work on `dev/{agent_role}` | No action yet |
| REVIEWED | Specialist issues HAND-02 SUCCESS; Gatekeeper runs P-E-V-A | Domain PR reviewed, MERGE CRITERIA checked |
| VALIDATED | All GA-0 through GA-6 conditions met; ConsistencyAuditor AU2 PASS | Root Admin merges `{domain}` → `main` |

**Key discipline:**
- A commit on `dev/*` is DRAFT; a merge to `{domain}` is REVIEWED; a merge to `main` is VALIDATED
- Gatekeepers cannot skip phases; each phase produces evidence
- HAND-02 `status: SUCCESS` means REVIEWED, not VALIDATED

**Why this matters now:** The v5.1 worktree concurrency protocol (`LOCK-ACQUIRE`,
`GIT-ATOMIC-PUSH`) operates ON TOP OF the 3-phase lifecycle. A lock is held for a
DRAFT→REVIEWED transition; release happens after REVIEWED. Without the 3-phase
foundation, the worktree concurrency model would have no semantics for "when is the
lock released."

---

## Foundation 3 — A9 Domain Sovereignty (2026-03-28, `b9ce96e`)

**Problem:** `CodeArchitect` and other L-Domain specialists could write to any
`src/` path. This caused infrastructure code (`src/system/`) to leak into core code
(`src/core/`) and vice versa. Imports from Infrastructure→Core violated the
dependency rule but had no structural enforcement.

**Solution:** A9 Core/System Sovereignty axiom with explicit 4-domain territorial map:

```
Core      = src/twophase/{ccd, level_set, ns, two_phase, physics}/
System    = src/twophase/{infra, experiment, viz}/
Interface = src/twophase/interface/ (contracts only)
Tests     = tests/, experiment/ch*/
```

**Key rules:**
- Core MUST NOT import from System
- System MAY import from Core
- Interface is abstract — no concrete class imports
- CodeArchitect runs **import auditing** at every merge (detects leaks)
- ConsistencyAuditor scans for `CRITICAL_VIOLATION` — direct solver core access from infrastructure layer

**Why this matters now:** A9 became the axiom that meta-domains.md Domain Registry
and DOM-02 pre-write check enforce at the tool-wrapper level. Without A9, CodeArchitect
could not legitimately reject a patch — it would be subjective judgment. With A9,
the rejection cites a specific axiom violation.

---

## The Bootstrapping Sequence

The 2026-03-28 refactoring also introduced **§DOMAIN BOOTSTRAPPING SEQUENCE** —
the canonical 4-phase order for setting up a new project domain:

1. Define domain boundaries in `meta-domains.md §DOMAIN REGISTRY`
2. Assign Specialists + Gatekeeper in `meta-roles.md`
3. Register territory in `_base.yaml :: directory_conventions`
4. Generate initial agent prompts via EnvMetaBootstrapper

This sequence is the reason a new project can be onboarded by swapping
`meta-project.md` (→ [[WIKI-M-007]]) without touching universal files.

---

## Authority Hierarchy (Conflict Resolution)

From meta-core.md §Principle Hierarchy (introduced in the 2026-03-28 refactor):

```
1. First principles (independent derivation)
2. > Canonical specification (paper / docs/memo/)
3.     > Implementation (src/core/)
4.         > Infrastructure (src/system/)
```

When two sources conflict, the hierarchy resolves it — not agent judgment, not the
most recent edit. This is the operational form of φ3 (Layered Authority).

---

## THEORY_ERR / IMPL_ERR Classification (P9)

Introduced at the same time in meta-workflow.md:

| Error class | Origin | Responsible agent |
|-------------|--------|-------------------|
| THEORY_ERR | Equation / stencil is wrong | TheoryArchitect re-derives |
| IMPL_ERR | Equation correct but code wrong | CodeCorrector patches |
| PAPER_ERROR | Equation correct, code correct, paper text wrong | PaperWriter fixes |
| CODE_ERROR | Equation correct, paper correct, old code wrong | CodeCorrector fixes |

Before this classification, errors were routed to "whoever owns the file" — causing
CodeCorrector to fix a bug that was actually a THEORY_ERR, propagating the fix
downstream without catching the real issue. The classification is what allows
φ7 (Classification Precedes Action) to function.

---

## Why These Are the Invariants

Every later evolution builds on these three foundations:

| Later addition | Depends on foundation |
|----------------|----------------------|
| v4.1 Schema-in-Code ([[WIKI-M-002]]) | 3-layer (meta/docs/00 separation forces single home) |
| v4.1 CoVe Mandate | 3-phase (CoVe runs in REVIEWED→VALIDATED gap) |
| v4.1 JIT Load Policy | 3-layer (section references work because layers are distinct) |
| v5.1 Worktree Concurrency ([[WIKI-M-001]]) | 3-phase (lock scope = DRAFT→REVIEWED span) |
| v5.1 Branch Lock | A9 (territory boundaries are per-domain locks) |
| v5.2 Structural Enforcement ([[WIKI-M-003]]) | 3-layer (Gatekeeper layer is distinct from self-check layer) |
| v5.2 Two-Path Derivation | φ3 (first principles > implementation) |
| Micro-Agent Architecture ([[WIKI-M-006]]) | A9 (DDA territorial scoping) |
| K-Domain ([[WIKI-M-007]]) | 3-layer (wiki is a new horizontal domain at Layer 2) |

If these invariants were removed, all later additions would lose their substrate
and become ad-hoc rules again.

---

## Source

- `prompts/meta/meta-core.md §SYSTEM STRUCTURE` (3-layer definition)
- `prompts/meta/meta-core.md §A9 Core/System Sovereignty`
- `prompts/meta/meta-domains.md §DOMAIN REGISTRY §LIFECYCLE` (3-phase)
- `prompts/meta/meta-workflow.md §P9 THEORY_ERR/IMPL_ERR` + `§DOMAIN BOOTSTRAPPING SEQUENCE`
- `docs/00_GLOBAL_RULES.md` (authoritative concrete rule source)
- Commits:
  - `92082d6` (2026-03-28) 3-layer domain-oriented architecture
  - `fd92d3a` (2026-03-28) 3-phase lifecycle
  - `b9ce96e` (2026-03-28) Decoupled Architect Protocol v5 — A9
  - `75033e9` (2026-03-28) 7-file meta-system restructure — V1–V11 violations resolved

## Related entries

- [[WIKI-M-002]] v4.1 3-Pillar Protocol — builds on 3-layer for SSoT enforcement
- [[WIKI-M-005]] Dynamic Governance Patterns — builds on 3-phase for deadlock prevention
- [[WIKI-M-007]] K-Domain + Project Profile Swap — extends 3-layer with K and project profile
