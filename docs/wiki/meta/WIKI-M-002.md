---
id: WIKI-M-002
title: "Agent Meta System: v4.1 3-Pillar Protocol (Schema-in-Code + CoVe + JIT)"
status: ACTIVE
created: 2026-04-11
updated: 2026-04-11
depends_on: []
---

# Agent Meta System: v4.1 3-Pillar Protocol

Three orthogonal optimizations merged in `9fc1c19`, each addressing a distinct failure
mode in the agent handoff/verification cycle.

---

## Pillar 1 — Schema-in-Code

**Problem**: `HandoffEnvelope` was defined in `prompts/meta/schemas/hand_schema.json`
(external JSON Schema). Agents could only reference it by path, making the schema
invisible to LLM context without a file-load step. The JSON file also drifted from
the prose descriptions in meta-roles.md.

**Solution**: TypeScript interfaces embedded directly in `meta-roles.md §SCHEMA-IN-CODE`
(Single Source of Truth). External `schemas/` directory deleted.

```typescript
interface HandoffEnvelope {
  schema_version: "2.0";
  session_id:     string;      // UUID v4 — identifies the session across all envelopes
  envelope_type:  "HAND-01" | "HAND-02" | "HAND-03";
  from_role:      string;
  to_role:        string;
  task_id:        string;
  payload:        Hand01Payload | Hand02Payload | Hand03Payload;
}

interface Hand02Payload {
  status:                "SUCCESS" | "FAIL" | "REJECT";
  artifact_ref:          string;
  verification_hash:     string;  // SHA-256 of the artifact diff
  branch_lock_acquired:  boolean; // true while writes are in progress (v5.1)
  detail:                string;  // MUST contain "CoVe: Q1=..., Q2=..., Q3=..." (Pillar 2)
}
```

All agents reference `meta-roles.md §SCHEMA-IN-CODE` via the `HAND_SCHEMA` on-demand
pointer in `_base.yaml`. The `schemas/` directory is **FORBIDDEN** from being recreated
(enforced in `meta-deploy.md §FORBIDDEN`).

---

## Pillar 2 — CoVe (Chain-of-Verification)

**Problem**: Specialist agents self-reported success without adversarial checking
(AP-03 Verification Theater). The VERIFY phase is a *separate agent* check, but
the Specialist's own output needed self-correction before hand-off.

**Solution**: Mandatory 3-step adversarial self-check (`meta-roles.md §COVE MANDATE`)
after artifact production and before HAND-02 emission.

```
CoVe PROCESS (non-negotiable):
  Step 1. Generate 3 verification questions challenging the artifact's correctness,
          completeness, and traceability.
  Step 2. Self-correct the artifact by answering each question independently.
  Step 3. Finalize — append to HAND-02 detail:
            "CoVe: Q1={pass|corrected}, Q2={pass|corrected}, Q3={pass|corrected}"
```

- CoVe runs inside the **EXECUTE** phase, immediately before HAND-02.
- It does NOT replace the VERIFY phase (VERIFY = independent agent; CoVe = self-check).
- Gatekeeper MUST reject HAND-02 where the CoVe summary contains generic language.
- Generic pass-through without genuine adversarial reasoning = CoVe violation.

**Integration in P-E-V-A**: added as a mandatory sub-step of E (Execute) in
`meta-workflow.md §P-E-V-A EXECUTION LOOP`.

---

## Pillar 3 — JIT Load Policy (Token Economy)

**Problem**: Agents loading full meta-*.md files at session start consumed excessive
context tokens on operations that used only a small section of the file.

**Solution**: JIT (Just-in-Time) load policy in `meta-ops.md §JIT Load Policy`:

- Agents load **only the specific section** they need immediately before execution.
- Example: if an agent needs LOCK-ACQUIRE, it reads only `meta-ops.md §LOCK-ACQUIRE`,
  not the entire meta-ops.md.
- Full-file load is **restricted** to:
  1. EnvMetaBootstrapper (regeneration run)
  2. PromptArchitect (audit run)

This cuts per-operation context by ~60–80% for large meta files.

---

## Propagation

v4.1 changes were propagated to all 33 agent `.md` files via EnvMetaBootstrapper:
- `HAND_SCHEMA` pointer updated: `prompts/meta/schemas/hand_schema.json` → `meta-roles.md §SCHEMA-IN-CODE`
- CoVe PROCEDURE step inserted before HAND-02 / SIGNAL:READY in 9 Specialist agents
- 4 priority agents (TheoryArchitect, CodeArchitect, ExperimentRunner, PaperWriter) +
  5 micro-agents (EquationDeriver, LogicImplementer, CodeArchitectAtomic, SpecWriter, RefactorExpert)

Commits: `9fc1c19` (core), `26e539a` + `678cf40` (EnvMetaBootstrapper propagation)

---

## Source

- `prompts/meta/meta-roles.md §SCHEMA-IN-CODE`
- `prompts/meta/meta-roles.md §COVE MANDATE`
- `prompts/meta/meta-ops.md §JIT Load Policy`
- `prompts/meta/meta-workflow.md §P-E-V-A EXECUTION LOOP`
- `prompts/meta/meta-deploy.md §Q3 checklist #10` (Schema-in-Code compliance)

## Related entries

- [[WIKI-M-001]] v5.1 Concurrency model — companion architectural change
