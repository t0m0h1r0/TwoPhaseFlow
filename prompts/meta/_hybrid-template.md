# _hybrid-template.md — MetaEvolutionArchitect v1.1 Reference (NON-CONSUMED)

> **Status:** reference document. NOT parsed by `meta-deploy.md` bootstrapper.
> **Purpose:** define the XML Shell + JSON Core vocabulary for the Hybrid refactor of `prompts/meta/*.md` and show 3 worked examples.
> **Foundation:** `meta-core.md §φ` and `§A` — this file touches neither; it is purely presentational.
> **Introduced by:** CHK-NEW-0 (Phase P0 of MetaEvolutionArchitect v1.1).

---

## 1. Closed Tag Vocabulary

Only the following XML tags are permitted inside `prompts/meta/*.md`. The bootstrapper (upgraded in P5) enforces this as an allow-list; unknown tags trigger **STOP-02** (Immutable Zone modification).

| Tag | Required? | Contents | Notes |
|---|---|---|---|
| `<meta_section>` | yes | all other tags | outer wrapper; carries `id`, `version`, `axiom_refs`, optional `immutable` |
| `<purpose>` | yes | one-line intent | no nesting |
| `<authority>` | optional | who may invoke / caller constraints | free prose, ≤ 3 lines |
| `<rules>` | yes | RFC-2119 bullets | each bullet MUST begin with `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, or `MAY` |
| `<tool_use>` | optional | TypeScript function signature | SSoT reference only — never duplicate payload definitions |
| `<tool_declaration>` | optional | function name + input/output types + idempotency flag | siblings of `<tool_use>` for group declarations |
| `<parameters>` | optional | JSON object with `$ref` + required/enum constraints | `format="json"` attribute required |
| `<procedure>` | yes | ordered steps | reference rules/axioms by id; no inline free prose longer than 2 lines per step |
| `<thought_process>` | optional | CoVe (Chain-of-Verification) hints | ≤ 5 lines; `optional="true"` attribute permitted |
| `<stop_conditions>` | optional | STOP-xx ids only, comma-separated | NEVER redefine STOP bodies here; they live in `meta-ops.md §STOP CONDITIONS` |
| `<see_also>` | optional | `§anchor` pointers to sibling sections / `meta-*.md` files | JIT retrieval hooks |

**Attributes on `<meta_section>`:**
- `id="HAND-02"` — REQUIRED; must match a legacy anchor (`HAND-02`, `A8`, `phi4`, `AP-03`, …)
- `version="5.1.0"` — REQUIRED; matches `meta_version` in `_base.yaml`
- `axiom_refs="A8,A6,phi4,phi4.1"` — REQUIRED; comma-separated, no spaces, constitutional traceability
- `immutable="true"` — OPTIONAL; applied to wraps around φ1–φ7, A1–A11, HAND-03 logic, L0–L3. Bootstrapper rejects any body-diff between `immutable="true"` tags (STOP-02).

**Nesting rule:** single-level nesting only. `<rules><rule>…</rule></rules>` is FORBIDDEN. The bootstrapper's parser uses line-anchored regex, not full XML parsing.

---

## 2. Worked Example A — HAND-02 (operational section)

```xml
<meta_section id="HAND-02" version="5.1.0" axiom_refs="A8,A6,phi4,phi4.1">
  <purpose>RETURN token. Specialist → Coordinator handback after EXECUTE + CoVe.</purpose>
  <authority>Sender: any Specialist. Receiver: the Coordinator that issued the matching HAND-01.</authority>
  <rules>
    - MUST populate `produced[]` with concrete written paths on SUCCESS (empty list forbidden).
    - MUST leave `issues[]` empty on SUCCESS and non-empty on FAIL or REJECT.
    - MUST set `stop_code` (pattern `^STOP-[0-9]{2}$`) when `status != SUCCESS`.
    - MUST set `lock_released: true` on SUCCESS and `false` on FAIL when `concurrency_profile == "worktree"`.
    - SHOULD populate `detail` only when the matching HAND-01 requested self-evaluation.
    - MUST NOT emit both a text-format HAND-02 block AND a `emit_hand02()` tool call in the same session (STOP-12 reserved).
  </rules>
  <tool_use>
    <!-- SSoT: meta-roles.md #SCHEMA-IN-CODE::Hand02Payload (DO NOT duplicate payload body) -->
    function emit_hand02(payload: Hand02Payload): HandoffEnvelope
  </tool_use>
  <parameters format="json">
    {
      "$ref": "meta-roles.md#SCHEMA-IN-CODE::Hand02Payload",
      "required": ["status", "produced", "issues", "session_id", "branch_lock_acquired", "verification_hash", "timestamp"],
      "status_enum": ["SUCCESS", "FAIL", "REJECT"],
      "stop_code_when": "status != SUCCESS"
    }
  </parameters>
  <procedure>
    1. Complete CoVe (see_also: meta-roles.md §COVE MANDATE) — Q1 logical, Q2 axiom, Q3 scope.
    2. Canonicalize payload → sha256 → `verification_hash`.
    3. Emit envelope (`handoff_mode == "text"` in v5.1.0 → JSON block; `handoff_mode == "tool_use"` → function call, v1.2 only).
    4. If SUCCESS AND `concurrency_profile == "worktree"`: invoke LOCK-RELEASE (see_also: meta-ops.md §LOCK-RELEASE).
  </procedure>
  <thought_process optional="true">
    Before emitting: have you derived each `produced` path independently, or are you trusting the plan?
    Does any `issues[]` entry paraphrase a rule rather than name a concrete failure?
  </thought_process>
  <stop_conditions>STOP-02, STOP-10, STOP-11, STOP-12</stop_conditions>
  <see_also>§HAND-01, §HAND-03, §LOCK-RELEASE, meta-workflow.md §STOP-RECOVER MATRIX</see_also>
</meta_section>
```

**Net:** replaces ~50 prose lines with ~45 structured lines, eliminates the ASCII mockup block, and forces the rules into RFC-2119 form (drift-resistant).

---

## 3. Worked Example B — GIT-SP (primitive, JIT candidate)

```xml
<meta_section id="GIT-SP" version="5.1.0" axiom_refs="A8,phi4.1">
  <purpose>Single-path commit primitive. All file writes go through `scripts/git-sp.sh`.</purpose>
  <authority>All Specialist and Coordinator roles that write files. Gatekeepers invoke it for their own artifacts.</authority>
  <rules>
    - MUST invoke `scripts/git-sp.sh` for every file write inside the locked branch.
    - MUST NOT bypass GIT-SP even for "one-line" edits — STOP-05 triggers otherwise.
    - MUST verify branch name != "main" before the wrapper runs (wrapper enforces this too).
    - SHOULD batch writes inside a single GIT-SP invocation when they form one logical change.
  </rules>
  <procedure>
    1. Resolve target branch from `_base.yaml :: task.branch`.
    2. Invoke `scripts/git-sp.sh <branch> <commit-message>` with the staged paths.
    3. On wrapper failure: capture stderr → HAND-02 `issues[]`; do not retry blindly.
  </procedure>
  <stop_conditions>STOP-01, STOP-05</stop_conditions>
  <see_also>§GIT-00, §GIT-WORKTREE-ADD, §STOP CONDITIONS</see_also>
</meta_section>
```

**JIT hook:** agents load GIT-SP only when `on_demand_common.GIT-SP` is explicitly looked up (already the case in `_base.yaml`). No inline duplication in 33 agent prompts.

---

## 4. Worked Example C — Axiom wrap (constitutional; immutable)

```xml
<meta_section id="phi2" version="5.1.0" axiom_refs="phi2" immutable="true">
  <purpose>φ2 — Minimal Footprint. Constitutional principle; DO NOT paraphrase.</purpose>
## φ2: Minimal Footprint
  {{ body lines — BYTE-IDENTICAL to pre-refactor meta-core.md §φ2 }}
  <see_also>§A1 (Token Economy), §A6 (Diff-First Output)</see_also>
</meta_section>
```

**Rules specific to `immutable="true"` wraps:**
1. The legacy markdown heading (`## φ2: Minimal Footprint`) stays **inside** the `<meta_section>` so the bootstrapper's existing grep gate (`grep -c '^## φ'`) still counts 7.
2. Body text between the heading and `<see_also>` / `</meta_section>` is byte-identical. Trailing whitespace and blank lines preserved.
3. The bootstrapper's P5-upgraded parser runs `diff` against the pre-refactor HEAD for every `immutable="true"` wrap. Any non-empty diff → STOP-02 SYSTEM_PANIC.
4. No `<rules>` / `<procedure>` / `<tool_use>` inside constitutional wraps — axioms are declarative, not operational.

---

## 5. Red-Team Guards (recap)

| Vector | Guard (enforced by P5 bootstrapper) |
|---|---|
| Tag squatting | Closed-vocab allow-list; unknown tag → STOP-02 |
| Dangling `$ref` | Eager resolution at regen; `schema_resolution_report.json` artifact; any unresolved → abort |
| Prose drift in `<rules>` | RFC-2119 prefix grep on every bullet |
| Dual-emission HAND-02 | `procedure_post` assertion in `_base.yaml`; reserved STOP-12 |
| Immutable body drift | `immutable="true"` + body-diff gate |

---

## 6. What this template does NOT change

- Axiom bodies (φ1–φ7, A1–A11) — byte-identical in P5 wrap
- HAND envelope SSoT — stays in `meta-roles.md §SCHEMA-IN-CODE`, never externalized
- P-E-V-A loop definition — untouched in `meta-workflow.md`
- L0–L3 isolation levels — untouched in `meta-experimental.md`
- Anti-pattern injection model — `meta-deploy.md §INHERITANCE MODEL` still drives per-role AP injection
- `_base.yaml` inheritance chain — agents still inherit via the same mechanism; only the `handoff_mode` key is added

This file (`_hybrid-template.md`) is documentation only. Removing it does not affect any generated agent prompt.
