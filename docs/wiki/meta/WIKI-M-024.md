ref_id:        WIKI-M-024
title:         Derived-Artifact Documentation Pattern: Generating Visual Maps from Kernel Data
domain:        M
status:        ACTIVE
superseded_by: null
sources:
  - path: prompts/meta/kernel-deploy.md
    git_hash: 9a7311b
    description: Stage 2c spec — §5b generation rules added to EnvMetaBootstrapper
  - path: prompts/meta/kernel-domains.md
    git_hash: 9a7311b
    description: §AGENT INTERACTION MAP static copy removed (A1/φ6 violation corrected)
  - path: prompts/README.md
    git_hash: 9a7311b
    description: §5b Agent Interaction Map — generated output, source note updated
consumers:
  - domain: P
    usage: PromptArchitect runs EnvMetaBootstrapper; Stage 2c generates §5b automatically
  - domain: M
    usage: ResearchArchitect references this pattern when adding new documentation sections
depends_on: [WIKI-M-014, WIKI-M-017, WIKI-M-018]
compiled_by: KnowledgeArchitect
verified_by: WikiAuditor
compiled_at: 2026-04-18

---

# Derived-Artifact Documentation Pattern: Generating Visual Maps from Kernel Data

## Problem

When adding visual documentation (Mermaid diagrams, relationship maps) to a meta-prompt
system, the naive approach is to embed the diagram as static content directly in a kernel
or meta file. This creates a **φ6 violation** (Single Source → Derived Artifacts) and an
**A1 violation** (Token Economy — no redundancy).

### Concrete instance (2026-04-18, this session)

A Mermaid agent interaction map was added to `prompts/README.md §5b`. A static copy of
the diagram was placed in `kernel-domains.md §AGENT INTERACTION MAP` as the "SSoT."

**Why this was wrong:**
All data in the diagram already existed in the kernel files:

| Diagram element | Actual SSoT |
|---|---|
| Agent nodes + Tier | `kernel-roles.md §Agent Profile Table` |
| Domain subgraphs | `kernel-domains.md §4×4 MATRIX + §DOMAIN REGISTRY` |
| Handoff edges (`-->`) | Role contracts: AUTHORITY / DELIVERABLES per agent |
| Interface contracts (`==>`) | `kernel-domains.md §INTER-DOMAIN INTERFACES` |
| Error intercept edges (`-.->`) | DiagnosticArchitect role contract |

Embedding the diagram in `kernel-domains.md` duplicated ~150 lines already fully
derivable from existing sources.

---

## Principle

> **Visual documentation is a derived artifact.** Define generation rules in the
> bootstrapper; never store the rendered output in the kernel source.

This is a direct corollary of:
- **A1 Token Economy** — no redundancy; reference > duplication
- **φ6 Single Source, Derived Artifacts** — change the source; never patch a derived artifact

---

## Solution: Stage 2c in EnvMetaBootstrapper

`kernel-deploy.md` Stage 2c specifies §5b generation rules. The bootstrapper derives
the Mermaid `flowchart TD` block at generation time from existing kernel data — no static
copy is stored anywhere.

### Element → Source mapping

| Mermaid element | Kernel source | Field |
|---|---|---|
| Node `ID["Name\n[role·TIER]"]` | `kernel-roles.md §Agent Profile Table` | `tier`, archetype |
| Subgraph per domain | `kernel-domains.md §DOMAIN REGISTRY` | `domain`, `specialists`, `coordinator` |
| `-->` HAND-01/02 edges | Role contracts | `AUTHORITY`, `DELIVERABLES` |
| `==>` contract edges | `kernel-domains.md §INTER-DOMAIN INTERFACES` | `Transfer`, `Contract Artifact` |
| `-.->` intercept edges | DiagnosticArchitect role contract | `AUTHORITY` |
| `classDef` styles | Fixed in Stage 2c spec (not data-driven) | — |

### Why styles are hardcoded in the spec

Color assignments (`rootAdmin`, `gatekeeper`, `specialist`, `auditNode`) map to authority
tiers, which are structural constants of the system. They do not change unless the tier
model changes, and that change would be tracked via a CHK session anyway.

---

## Anti-Pattern: "Convenience SSoT"

Placing a static rendered diagram in a kernel file and labeling it as the SSoT is an
anti-pattern. The diagram becomes stale the moment any agent, domain, or handoff changes,
and maintainers will edit the rendered copy instead of the authoritative source — a
classic φ6 violation.

Detection signal: a file contains both structured data (tables, YAML) **and** a
Mermaid diagram that visualizes the same data.

Correct action: remove the diagram; add generation rules to the bootstrapper.

---

## Applicability

This pattern applies whenever a meta-system needs persistent visual documentation of
relationships that are already encoded as structured data elsewhere. Examples:

- Agent interaction maps (this case)
- Domain ownership diagrams (derivable from `§DOMAIN REGISTRY`)
- Interface contract chains (derivable from `§INTER-DOMAIN INTERFACES`)
- HAND token flow diagrams (derivable from `kernel-ops.md §HAND-01..04`)

It does NOT apply to one-off sketches or exploratory diagrams, which belong in
`docs/memo/` and are not part of the generated documentation.
