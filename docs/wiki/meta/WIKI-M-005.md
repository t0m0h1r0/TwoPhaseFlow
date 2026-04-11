---
id: WIKI-M-005
title: "Agent Meta System: Dynamic Governance Patterns (MAX_REJECT_ROUNDS + CONDITIONAL_PASS + INTEGRITY_MANIFEST + Phantom Guard)"
status: ACTIVE
created: 2026-04-12
updated: 2026-04-12
depends_on: [WIKI-M-004]
---

# Agent Meta System: Dynamic Governance Patterns

## Motivation

The 2026-03-31 governance addendum (`ba2095c`, `d79588b`) resolved four distinct
failure modes observed in early multi-agent runs: infinite rejection loops, contract
drift propagation, auditor chain-of-thought contamination, and silent token waste
on duplicated spec text. These four patterns are invisible in normal operation but
load-bearing — remove any of them and the system develops the corresponding failure.

They are grouped here because they share a common theme: **the governance layer
adapts to observed failure modes rather than being statically fixed**.

---

## Pattern 1 — MAX_REJECT_ROUNDS + CONDITIONAL_PASS (Deadlock Prevention)

**Failure mode observed:** A Gatekeeper repeatedly rejected deliverables, citing
vague skepticism ("this needs more work") without pointing to a specific GA
condition. Specialist addressed each rejection; Gatekeeper moved the goalposts.
Loop ran indefinitely until user manually intervened.

**Response — Audit Exit Criteria:**

```
MAX_REJECT_ROUNDS = 3

Rules:
1. Each rejection MUST cite a specific GA-1..GA-6 or AU2 item number
2. A rejection that cites a new criterion not raised previously = Deadlock Violation
3. After 3 rejections without resolution → mandatory Root Admin escalation
4. If all formal checks pass but doubt remains → issue CONDITIONAL_PASS with Warning Note
```

**CONDITIONAL_PASS:** the Gatekeeper-side breaker that allows forward progress
despite residual (but un-citable) concerns. The Warning Note becomes part of the
merged artifact's provenance — future sessions can read it and decide whether to
address it separately.

**Why this matters now:** AP-04 (Gate Paralysis) in meta-antipatterns.md is the
anti-pattern form of this failure. The detection criteria and mitigation in AP-04
are literally the rules above. Without MAX_REJECT_ROUNDS, the P-E-V-A loop has no
termination guarantee — it would loop until the user killed it.

---

## Pattern 2 — INTEGRITY_MANIFEST Hash Continuity

**Failure mode observed:** Downstream domains started work on an upstream interface
contract that had been silently updated by a concurrent session. The downstream work
completed and merged, but was built against a stale contract. The CI/CP propagation
mechanism existed but had no way to detect "I'm looking at a stale version of the
thing you think I'm looking at."

**Response — INTEGRITY_MANIFEST:**

```
docs/02_ACTIVE_LEDGER.md §5 INTEGRITY_MANIFEST
  T_hash: <sha256 of docs/interface/AlgorithmSpecs.md at signing>
  L_hash: <sha256 of docs/interface/SolverAPI_vX.py at signing>
  E_hash: <sha256 of docs/interface/ResultPackage/ manifest at signing>
  A_hash: <sha256 of final paper/sections/ commit at VALIDATED>
```

**Rules:**
- Each hash is recorded ONLY after upstream is locked (T→L→E→A order)
- Gatekeeper MUST verify hash continuity before issuing PASS
- Mismatch = CONTAMINATION → trigger CI/CP re-propagation
- Fresh deployment: all hashes `{pending}` — treat as missing contract; block downstream

**Why this matters now:** The hash chain is how v5.1's concurrent sessions detect
when another session silently updated an upstream contract while they were running.
Without INTEGRITY_MANIFEST, worktree concurrency would silently produce stale-contract
merges. It is a prerequisite for v5.1, not an optional addition.

---

## Pattern 3 — Phantom Reasoning Guard (HAND-03 Check 6)

**Failure mode observed:** An Auditor (e.g., ConsistencyAuditor) received a DISPATCH
envelope whose `inputs` field contained the Specialist's reasoning chain — not just
the artifact path. The Auditor read the reasoning, pattern-matched it, and issued
PASS based on "the Specialist's argument is plausible" rather than independent
derivation. Broken Symmetry (φ2) was silently violated.

**Response — Phantom Reasoning Guard (HAND-03 check 6):**

```
Auditor's FIRST action after acceptance: perform independent derivation
BEFORE opening the artifact under review.

Rule: DISPATCH `inputs` MUST contain ONLY:
  - final artifact paths (no intermediate derivation notes)
  - signed Interface Contract paths
  - test/build log paths

If `inputs` includes Specialist session history, intermediate derivation notes,
or chain-of-thought → REJECT immediately (STOP-HARD).
```

**"Verified by comparison only" = broken symmetry → STOP-HARD.**

**Why this matters now:** This is the structural enforcement that makes Broken
Symmetry (meta-core.md §B) operationally verifiable rather than aspirational.
AP-06 (Context Contamination via Summary) and AP-03 (Verification Theater) both
depend on the Phantom Reasoning Guard. v5.2's §STRUCTURAL ENFORCEMENT note on
AP-03/AP-05 composes with this — the Gatekeeper rejects phantom inputs at HAND-03,
and then rejects phantom outputs at HAND-02.

---

## Pattern 4 — JIT Command Reference Pattern

**Failure mode observed:** Agent prompts inlined full syntax for every operation they
might call (GIT-SP, HAND-01, BUILD-02, etc.). A 16-agent roster inlining all ops
consumed roughly 40% of each agent's token budget on operation text that was
identical across agents.

**Response — JIT Command Reference:**

```
Agent prompts cite operation IDs only: "run GIT-SP" or "emit HAND-01"
Full syntax lives in meta-ops.md §GIT-SP, §HAND-01, etc.
Agents load the specific section just before executing the command.
```

**Enforcement:** `meta-deploy.md Stage 3` injects JIT citation pattern into all
generated agent prompts. Full-file load is restricted to EnvMetaBootstrapper and
PromptArchitect only.

**Why this matters now:** This is the first formal statement of the JIT pattern
that later became [[WIKI-M-002]] Pillar 3. The 2026-03-31 version introduced the
rule; the 2026-04-11 v4.1 version codified it as a pillar with the 60–80% token
reduction measurement.

---

## Integration: How These Four Compose

| Pattern | Defends against | Composes with |
|---------|----------------|---------------|
| MAX_REJECT_ROUNDS | Infinite P-E-V-A loops | AP-04 (Gate Paralysis), STOP-07 |
| INTEGRITY_MANIFEST | Stale upstream contract | v5.1 worktree concurrency, CI/CP protocol |
| Phantom Reasoning Guard | Auditor contamination via summary | AP-03/06, COVE Mandate, v5.2 structural enforcement |
| JIT Command Reference | Token bloat from inlined ops | WIKI-M-002 Pillar 3, v5.1 HAND-01 compression |

These four patterns share a common property: **they convert aspirational rules
("don't be lazy", "don't be wasteful") into structurally verifiable checks.** The
philosophical content of each pattern existed before 2026-03-31; the governance
addendum turned each into a rule with specific trigger conditions and a specific
enforcement mechanism.

---

## PATCH-IF Protocol (Agile Synchronization)

Added in the same 2026-03-31 governance addendum. Allows ResearchArchitect to patch
a minor upstream Interface Contract error without running full CI/CP re-propagation:

| Scope | Definition | Action |
|-------|-----------|--------|
| MINOR | Typo, unit label, clarification — no API or math change | ResearchArchitect patches + re-signs; downstream resumes |
| FUNCTIONAL | API signature, equation form, operator structure | PATCH-IF DENIED → run full CI/CP |

**Why this matters:** without PATCH-IF, every typo in `AlgorithmSpecs.md` would
trigger re-propagation through all four domains. PATCH-IF keeps the contract sacred
for FUNCTIONAL changes while allowing cheap updates for MINOR edits.

---

## Source

- `prompts/meta/meta-ops.md §AUDIT EXIT CRITERIA` (MAX_REJECT_ROUNDS + CONDITIONAL_PASS)
- `prompts/meta/meta-workflow.md §CI/CP PIPELINE §INTEGRITY_MANIFEST`
- `prompts/meta/meta-core.md §B Broken Symmetry` (Phantom Reasoning Guard foundation)
- `prompts/meta/meta-ops.md §HAND-03 check 6` (Phantom Reasoning Guard enforcement)
- `prompts/meta/meta-ops.md §PATCH-IF`
- `prompts/meta/meta-antipatterns.md §AP-04 Gate Paralysis`, `§AP-06 Context Contamination`
- Commits:
  - `ba2095c` (2026-03-31) Dynamic Governance & Deadlock Prevention addendum
  - `d79588b` (2026-03-31) v2 update — Phantom Guard + INTEGRITY_MANIFEST + JIT + CONDITIONAL_PASS
  - `1bf75ff` (2026-03-31) Improvement Framework audit — 4 structural gaps

## Related entries

- [[WIKI-M-004]] Constitutional Foundations — the substrate these governance patterns run on
- [[WIKI-M-002]] v4.1 3-Pillar Protocol — Pillar 3 (JIT) extends Pattern 4 above
- [[WIKI-M-003]] v5.2 LLM-Specific Hardening — Structural Enforcement composes with Pattern 3
