# META-KNOWLEDGE: Knowledge Domain — Wiki Architecture, Lifecycle & Operations
# VERSION: 1.0.0
# ABSTRACT LAYER — KNOWLEDGE: structured knowledge compilation, pointer integrity, SSoT enforcement.
# This domain acts as the "Standard Library" and "Global Memory" for all other domains.
# FOUNDATION (φ1–φ7, A1–A11): prompts/meta/meta-core.md  ← READ FIRST
# Role contracts per agent: prompts/meta/meta-knowledge-roles.md
# Domain registry: prompts/meta/meta-domains.md

────────────────────────────────────────────────────────
# § K-DOMAIN PHILOSOPHY — "Wiki as an OS"

Human-written notes and agent-generated memos are **source code** — unverified, unstructured,
potentially contradictory. The LLM (KnowledgeArchitect) acts as a **compiler**: it transforms
source artifacts into **compiled wiki entries** that are structured, referenced, and verified.

Only compiled entries in `docs/wiki/` are trusted system knowledge.
Raw artifacts in domain directories (`docs/memo/`, `experiment/`, `paper/`) remain authoritative
for their own domain but are NOT the canonical compiled form.

────────────────────────────────────────────────────────
# § K-DOMAIN AXIOMS (The Compiler Rules)

## K-A1: No Unstructured Raw Text
Direct writes to `docs/wiki/` are forbidden. All knowledge passes through a compilation
process: Source artifact (domain-verified, VALIDATED phase) → K-COMPILE → Compiled Entry.

## K-A2: Pointer Integrity (Link Validation)
Every `[[REF-ID]]` in the wiki MUST resolve to an existing, ACTIVE entry.
A broken reference is a **Segmentation Fault** — STOP-HARD; fix before proceeding.
This maps to φ1 (Truth Before Action): you cannot reference knowledge that does not exist.

## K-A3: Single Source of Truth (SSoT)
Duplicate knowledge is a refactoring target. Every concept, constant, or equation is
defined in exactly **one** wiki entry. All other references use `[[REF-ID]]` pointers.
Duplication is a φ6 violation (Single Source, Derived Artifacts).

## K-A4: Empirical Grounding & Lineage
Every wiki entry carries metadata: source artifact path, source git hash, domain of origin,
and dependent theory IDs. This enables traceability (A3) at the knowledge level.

## K-A5: Knowledge Mutability (Versioning)
Knowledge is not immutable stone. On error detection or strategy change:
- Do NOT delete entries — transition to `DEPRECATED` or `SUPERSEDED` status.
- `DEPRECATED` entries retain a pointer to the replacement (`superseded_by: [[REF-ID]]`).
- Status transitions trigger `RE-VERIFY` signals to all consuming domains.

────────────────────────────────────────────────────────
# § WIKI ENTRY FORMAT

Every entry in `docs/wiki/` follows this canonical structure:

```yaml
WIKI-ENTRY:
  ref_id:         {unique ID, e.g., WIKI-T-001}
  title:          {concise descriptive title}
  domain:         {T | L | E | A | cross-domain}
  status:         {ACTIVE | DEPRECATED | SUPERSEDED}
  superseded_by:  {[[REF-ID]] or null}
  sources:
    - path:       {source artifact path}
      git_hash:   {short hash at time of compilation}
      description: {what was extracted}
  consumers:
    - domain:     {consuming domain ID}
      usage:      {how this entry is used}
  depends_on:     [[[REF-ID]], ...]
  compiled_by:    KnowledgeArchitect
  verified_by:    WikiAuditor
  compiled_at:    {ISO date}
---
{structured content body — Markdown with [[REF-ID]] pointers}
```

────────────────────────────────────────────────────────
# § WIKI DIRECTORY STRUCTURE

```
docs/wiki/
├── theory/        # Compiled theory derivations, equations, mathematical definitions
├── code/          # Compiled API specifications, architecture decisions, solver contracts
├── experiment/    # Compiled experimental findings, benchmark results, validated data
├── paper/         # Compiled paper-level conclusions, narrative decisions
├── cross-domain/  # Compiled cross-domain knowledge (spans multiple verticals)
└── changelog/     # Knowledge modification and deprecation history (audit trail)
```

**Naming convention:** `{REF-ID}.md` — e.g., `docs/wiki/theory/WIKI-T-001.md`

────────────────────────────────────────────────────────
# § KNOWLEDGE LIFECYCLE

```
                    ┌─────────────┐
                    │   SOURCE    │  Domain artifact at VALIDATED phase
                    └──────┬──────┘
                           │  K-COMPILE (KnowledgeArchitect)
                           ▼
                    ┌─────────────┐
                    │   ACTIVE    │  Compiled, verified, referenceable
                    └──────┬──────┘
                           │  Error detected / superseded / strategy change
                           ▼
              ┌────────────┴────────────┐
              │                         │
       ┌──────┴──────┐          ┌──────┴──────┐
       │ DEPRECATED  │          │ SUPERSEDED  │
       │ (error/stale)│          │ (replaced)  │
       └──────┬──────┘          └──────┬──────┘
              │                         │
              └────────────┬────────────┘
                           │  RE-VERIFY signal → all consumers
                           ▼
                    ┌─────────────┐
                    │  CASCADE    │  Consuming domains re-validate
                    └─────────────┘
```

**State transitions require WikiAuditor approval.**
**RE-VERIFY signals are mandatory** — consuming domains must acknowledge and re-validate
any artifact that depends on a DEPRECATED or SUPERSEDED wiki entry.

────────────────────────────────────────────────────────
# § K-OPERATIONS INDEX

Operations are fully specified in meta-ops.md §KNOWLEDGE OPERATIONS.
Summary for quick reference:

| Operation | Auth Level | Trigger | Purpose |
|-----------|-----------|---------|---------|
| K-COMPILE | Specialist (KnowledgeArchitect) | Domain artifact reaches VALIDATED | Compile source into wiki entry |
| K-LINT | Gatekeeper (WikiAuditor) | Before wiki merge; periodic sweep | Verify all [[REF-ID]] pointers resolve; SSoT check |
| K-DEPRECATE | Gatekeeper (WikiAuditor) | Source invalidated or superseded | Set entry DEPRECATED; emit RE-VERIFY signals |
| K-REFACTOR | Specialist (TraceabilityManager) | K-LINT reports duplicate knowledge | Convert duplicates to [[REF-ID]] pointers |
| K-IMPACT-ANALYSIS | Specialist (Librarian) | Before K-DEPRECATE | Trace all consumers; estimate cascade depth |

────────────────────────────────────────────────────────
# § INTER-DOMAIN INTERACTION

**K reads from all domains (like Q-Domain):**
K-Domain has read access to all vertical domain artifacts for compilation purposes.
K-Domain does NOT modify source artifacts — it produces compiled entries in `docs/wiki/` only.

**All domains read from K:**
Per A11 (Knowledge-First Retrieval), agents in any domain may (and should) read `docs/wiki/`
entries before reasoning from scratch. Wiki entries are read-only for non-K agents.

**K ↔ Q relationship:**
- Q-Domain (ConsistencyAuditor) verifies **correctness** — issues PASS/FAIL verdicts.
- K-Domain (KnowledgeArchitect) compiles **knowledge** — produces wiki entries.
- Q may reference wiki entries during audits; K may not issue audit verdicts.
- No write-territory overlap: Q writes audit trails; K writes wiki entries.
