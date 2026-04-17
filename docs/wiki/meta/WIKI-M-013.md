# WIKI-M-013: LEAN_METASTACK_2024 + v1.1 XML Hybrid Format
**Category:** Meta | **Created:** 2026-04-18
**Sources:** git log (2026-04-11 commits), `prompts/meta/meta-core.md`, `prompts/meta/meta-deploy.md`

## Context

By early April 2026, the meta-file system had grown to ~232KB across 10 files as protocols,
axioms, and agent contracts accumulated over 3 weeks. In production, every session that
loaded the full meta-stack paid a context window cost proportional to that size. Two
initiatives on 2026-04-11 addressed this: LEAN_METASTACK_2024 (compression) and the
v1.1 XML Hybrid refactor (structural immutability for the constitutional layer).

---

## LEAN_METASTACK_2024 Compression Campaign

**Goal:** Reduce total meta-file token cost without removing any rule, protocol, or axiom.

**Scope:** 5 sequential commits on 2026-04-11, targeting the 5 largest meta-files.

### What Was Cut

| File | Change | Rationale |
|------|--------|-----------|
| `meta-experimental.md` | −36.9% | L0–L3 isolation model promoted to canonical policy (meta-core.md §B.1); SIGNAL protocol trimmed; DDA rewritten as env-enforced interceptor rather than documented procedure |
| `meta-ops.md` | −7.5% | HAND-01 schema compressed: **14 fields → 4** (task / inputs / constraints / target); §HAND-01-ENV introduced for fields injected from environment (session_id, branch, lock status) rather than manually specified by coordinators |
| `meta-ops.md` | (continued) | HAND-02 status enum simplified: 9 codes → 3 (**SUCCESS / FAIL / REJECT**); 9 contextual rules → 4 essential rules |
| `meta-ops.md` | (continued) | §LEDGER UPDATE CADENCE added: ACTIVE_LEDGER writes batch-only intra-session (not after every step); reduces file I/O and context re-reads |
| `meta-roles.md` | −27.2% | Role-contract compression; removed per-agent boilerplate; retained only contract deltas from `_base.yaml` |
| `meta-workflow.md` | −29.7% | Pipeline compression; inserted §LEDGER UPDATE CADENCE (MH batch policy) |

**Result:** 232KB → 162KB (−30%) across the 5 targeted meta-files.

### Key Architectural Decision: HAND-01 Field Reduction

The original 14-field HAND-01 included explicit per-dispatch fields for session_id,
branch, lock status, parent_hash, and similar bookkeeping. The lean version separates
concerns:

- **§HAND-01-ENV** (environment-injected): session_id, branch, lock_acquired,
  verification_hash — injected by the runtime or agent infrastructure, not manually
  written by coordinators.
- **§HAND-01 payload** (manually specified): task, target, inputs, constraints — the
  minimal set a coordinator actually needs to specify.

This made HAND tokens easier to author while retaining full traceability via the
envelope wrapper (see `meta-roles.md §SCHEMA-IN-CODE`).

---

## v1.1 XML Hybrid Format (CHK-NEW-0..5)

**Goal:** Provide machine-verifiable protection for the constitutional layer — the axioms
(φ1–φ7, A1–A11) and handoff protocols that must not be modified by normal development
workflow. A subsequent refactoring commit that accidentally edits an axiom should be
catchable at CI/pre-commit level, not only by human review.

**Approach:** Wrap constitutional sections in XML `<meta_section>` elements with attributes
that express immutability and version binding.

### XML Schema

```xml
<meta_section
  id="AXIOMS"
  version="3.0.0"
  axiom_refs="phi1,phi2,phi3,phi4,phi5,phi6,phi7,A1..A11"
  immutable="true">
  <!-- constitutional content here -->
</meta_section>
```

**Attribute semantics:**
- `id`: unique section identifier within the file (used for `$ref` resolution)
- `version`: meta-stack version at which this section was authored
- `axiom_refs`: comma-separated list of axioms whose authority this section derives from
- `immutable="true"`: signals the parser that this section is in the STOP-02 Immutable Zone;
  any diff touching this body in a non-constitutional PR → parser blocks

### What Was Wrapped

| Content | Rationale |
|---------|-----------|
| φ1–φ7 Core Principles (meta-core.md) | Foundational philosophy; defines "why" for all other rules |
| A1–A11 Axioms (meta-core.md) | Constitutional layer; axiomatic — cannot be overridden by domain rules |
| HAND-03 Logic (meta-ops.md) | Acceptance check is the last line of defence; must not drift |
| SCHEMA-IN-CODE TypeScript interfaces (meta-roles.md) | HandoffEnvelope is the binding contract between all agents |

### `handoff_mode` Feature Flag

A `handoff_mode` field was added to `_base.yaml` to control how HAND tokens are emitted:

| Value | Behavior |
|-------|---------|
| `"text"` (default, current) | HAND tokens emitted as Markdown-formatted text blocks |
| `"tool_use"` (reserved) | HAND tokens emitted via `emit_hand01` / `emit_hand02` tool calls (v1.2+) |

The `"tool_use"` mode was deferred because it requires the runtime to support structured
tool declarations that match the TypeScript schema. When activated in v1.2, STOP-12
(Dual-emission guard) will also become active to prevent a session from emitting both
a text-format HAND and a tool-call HAND for the same token.

### Stage 1b Parser Spec

The v1.1 refactor added a new bootstrapper stage (Stage 1b) in `meta-deploy.md`:

1. **Tag balance check**: every `<meta_section>` must have a matching `</meta_section>`
2. **Closed-vocab allow-list**: only approved element names are valid inside meta files
3. **Eager `$ref` resolution**: `<see_also>` references are resolved and validated against
   the actual section IDs at generation time (not deferred to runtime)
4. **RFC-2119 rules check**: MUST/SHALL/SHOULD are validated for grammatical correctness
5. **Immutable body-diff gate**: if a commit diff touches the body of any `immutable="true"`
   section, Stage 1b rejects the generation and reports the section ID

Verification: 25/25 tag-balance gates passed across 9 meta files at v1.1 deployment.

### φ6 Fix: Absorbing `_hybrid-template.md`

The v1.1 deployment initially stored the XML hybrid format specification in a separate
`prompts/meta/_hybrid-template.md` file. This violated φ6 (Single Source of Truth):
the format spec was split across `meta-deploy.md §Stage 1b` and `_hybrid-template.md`.
A follow-up commit (`df65f85`) absorbed the template file into `meta-deploy.md`,
eliminating the violation. The fix was logged as EVO-001-fix in ACTIVE_LEDGER.

---

## Combined Impact

| Metric | Before | After |
|--------|--------|-------|
| Total meta file size | ~232KB | ~162KB |
| HAND-01 fields | 14 | 4 (+env-injected) |
| HAND-02 status codes | 9 | 3 |
| Constitutional layer | unprotected Markdown | XML immutable wrapper |
| Session loading cost | full file reads each session | JIT section-level reads (meta-core.md §LA-5) |

---

## Cross-References

- `→ WIKI-M-001`: v5.1 concurrency protocols deployed alongside this compression
- `→ WIKI-M-002`: v4.1 3-Pillar (JIT token economy directly enabled by compressed HAND schema)
- `→ WIKI-M-003`: v5.2 hardening that followed (AP-09/10, §STRUCTURAL ENFORCEMENT)
- `→ WIKI-M-014`: meta-deploy Stage 1b parser spec (bootstrapper lifecycle)
- `→ prompts/meta/meta-core.md`: φ6 Single Source principle that motivated the φ6 fix
