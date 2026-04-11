---
id: WIKI-M-003
title: "Agent Meta System: v5.2 LLM-Specific Hardening (AP-09/10 + Two-Path Gate + Structural Enforcement)"
status: ACTIVE
created: 2026-04-11
updated: 2026-04-11
depends_on: [WIKI-M-001, WIKI-M-002]
---

# Agent Meta System: v5.2 LLM-Specific Hardening

## Motivation

v5.0/v5.1 built correct multi-agent governance (φ1–φ7, T-L-E-A pipeline, worktree
concurrency), but the anti-pattern catalogue only covered *structural* failure modes
(verification theater, convergence fabrication, phantom state). v5.2 adds the class of
failures that are **intrinsic to LLM attention mechanics** — context collapse and
recency bias — and tightens two self-check pathways that were previously
honor-system-only.

Three orthogonal additions, merged in `93e1c7a` (2026-04-11):

1. **AP-09 / AP-10** — LLM-attention failure modes in the anti-pattern catalogue
2. **Two-Path Derivation Gate** — self-consistency sampling in AUDIT-02 Procedure A
3. **Structural Enforcement Layer** — Gatekeeper-side rejection rules complementing AP-03/AP-05 self-checks

---

## Addition 1 — AP-09 Context Collapse (HIGH)

**Failure mode:** In long sessions, constraints established early in the conversation
are silently dropped. The agent applies rules correctly for the first 3–5 turns, then
gradually forgets them — scope boundaries, STOP conditions, and domain restrictions
disappear from reasoning without any explicit decision to abandon them.

**Root cause:** LLM attention over long contexts is recency-weighted. Instructions set
at session start are effectively lower-weighted by turn 10+. The agent does not decide
to ignore constraints — it simply fails to retrieve them.

**Detection (self-checkable):**
- A STOP condition stated at session start is absent from reasoning after 5+ turns without re-reading
- Agent takes an action that would have been rejected if the original constraints were active
- Agent says "I'll go ahead and..." without re-checking the HAND-01 mandate

**Mitigation:**
1. Re-read `SCOPE_BOUNDARIES` every 5 turns
2. Re-read STOP conditions before each HAND-02 emission
3. Tool-verify mutable state (branch, files) rather than relying on in-context recall
4. If a constraint was established >5 turns ago and you have not re-read it: re-read now

**Inject:** ALL agents (universal — context collapse affects every role in long sessions)

---

## Addition 2 — AP-10 Recency Bias in Classification (MEDIUM)

**Failure mode:** The most recently seen evidence disproportionately shapes classification
decisions. A Gatekeeper that performs independent re-derivation at turn 1 and then
reads the Specialist's "plausible explanation" at turn 4 may silently revise its
verdict without explicitly re-deriving.

**Root cause:** LLM attention is recency-weighted at the token level, not just at the
session level. Reading a Specialist's justification effectively overwrites the
earlier derivation unless the agent explicitly re-derives.

**Detection (self-checkable):**
- Classification changed between turns without new artifact read or derivation
- Current classification contradicts earlier evidence still in context
- Gatekeeper's AGREE/DISAGREE verdict flips after reading Specialist's response, without re-deriving

**Mitigation:**
1. Re-derive classification from ALL evidence at each decision point
2. If classification differs from earlier derivation: explicitly state what changed and why
3. Reading a Specialist's justification does NOT constitute re-derivation — derive again from primary sources

**Inject:** CodeCorrector, ErrorAnalyzer, ConsistencyAuditor, TheoryAuditor, PaperReviewer

---

## Addition 3 — Two-Path Derivation Gate (AUDIT-02 Procedure A)

**Context:** AUDIT-02 Procedure A is ConsistencyAuditor / TheoryAuditor's "independent
derivation from first principles" step — the core mechanism enforcing Broken Symmetry.
Previously it required only a single derivation path.

**Upgrade:** When a derivation yields ≥2 plausible interpretations of the governing
equation or stencil (ambiguous PDE form, conflicting index conventions, sign ambiguity),
the auditor MUST derive via **two independent paths** before concluding:

- **Path 1:** direct Taylor expansion from the governing PDE
- **Path 2:** operator algebra (matrix form or spectral analysis)

```
BOTH PATHS AGREE → PASS
PATHS DISAGREE   → STOP-HARD (authority conflict); HAND-02 status: REJECT
                    with specific disagreement cited. Do NOT average or pick one.
```

**Why this is self-consistency sampling, not over-engineering:**
The standard self-consistency technique (Wang et al. 2023) samples multiple reasoning
paths on the same question and takes the majority vote. Applied to mathematical
derivation, "majority of 2" degenerates to "agreement required" — if the two paths
disagree, there is no stable answer and the auditor MUST escalate rather than pick one.

**Conditional, not universal:** Single-path derivation is sufficient when the equation
interpretation is unambiguous (no competing readings in the context). The two-path
requirement fires only when ambiguity is detected — this keeps the token cost bounded
while catching the dangerous class of false-PASS outcomes.

**Applied to this project:** the CCD-PPE defect correction operator has historically
produced ambiguous interpretations (Kronecker ordering, ghost cell sign, filter
coefficient placement). All future AUDIT-02 runs on CCD operator issues should apply
the two-path requirement.

---

## Addition 4 — Structural Enforcement Layer (AP-03 / AP-05)

**Previous state:** AP-03 (Verification Theater) and AP-05 (Convergence Fabrication)
relied entirely on self-checkable detection criteria — the agent had to honestly
report whether it ran tools. A dishonest (or attention-collapsed) agent could pass
the self-check and propagate false verification downstream.

**Upgrade:** Both anti-patterns now carry a **§STRUCTURAL ENFORCEMENT** note that
shifts partial enforcement to the Gatekeeper layer:

| AP | Structural rule (Gatekeeper side) |
|----|----------------------------------|
| AP-03 | Reject any HAND-02 where a numerical result appears in `detail` but no tool invocation appears in the session transcript. CoVe Q1 answers containing numbers not traceable to tool output are rejected regardless of agent self-report. |
| AP-05 | Reject any HAND-02 where `produced[]` contains numerical data but `tool_evidence[]` is absent or empty. A convergence table in `detail` without a corresponding log file path in `tool_evidence` is rejected regardless of agent confidence claim. |

**Architectural pattern:** self-check + Gatekeeper structural check = **composite
verification**. Self-checks are fast but fakeable; structural checks are slow but
adversarial. Composing them gives the cheap-then-adversarial layering that v5.2
now codifies as the standard pattern for anti-pattern enforcement.

**Design implication:** Any future anti-pattern added to meta-antipatterns.md SHOULD
be evaluated for whether a structural enforcement rule can back the self-check. If
yes, the structural rule goes in the corresponding Gatekeeper role contract.

---

## Why These Were Missing Before

The v5.0/v5.1 anti-pattern catalogue targeted *agent-produced* failures: the agent
does something wrong. The v5.2 additions target *LLM-intrinsic* failures: the LLM's
own attention mechanics cause silent drift even when the agent is "trying" to comply.

This distinction matters because:
- Agent-produced failures are caught by better prompts and clearer rules
- LLM-intrinsic failures require **architectural countermeasures** (re-reading cadence,
  structural gatekeeper rejection, self-consistency sampling) because no amount of
  "please pay attention" will override attention weighting

The v5.2 hardening is therefore **not** better prompting — it is *workflow architecture*
designed around known LLM limitations.

---

## Integration with Existing Pillars

| v5.2 Addition | Composes with |
|--------------|---------------|
| AP-09 Context Collapse | LA-3 (external state verification) — extends it from "verify git state" to "re-read constraints periodically" |
| AP-10 Recency Bias | φ7 Classification Precedes Action — strengthens it from "classify before acting" to "re-classify without deference to latest evidence" |
| Two-Path Gate | COVE MANDATE (WIKI-M-002 Pillar 2) — Chain-of-Verification self-checks the *output*; two-path checks the *derivation process* |
| Structural Enforcement | HAND-03 check 6 (Phantom Reasoning Guard) — HAND-03 blocks phantom inputs; structural enforcement blocks phantom outputs |

---

## Evolution Protocol Notes

v5.2 was implemented as Track A (SSoT/clarity fixes — safe) + Track B (compression
& modernization — additive). **Zero existing rules were deleted.** The universal
regression guard (φ count = 7, A count = 11, SCHEMA-IN-CODE unchanged, file count = 10)
passed after every phase.

**Deferred to v5.3 or later:**
- DSPy-style programmatic signature optimization (tooling not yet in place)
- Process Reward Models (would dissolve the explicit GA-0–GA-6 gate conditions)
- Track C structural merge (meta-experimental.md → meta-domains.md) — only if
  glossary slot becomes urgent

**Explicitly rejected:**
- Tree-of-Thoughts multi-branch reasoning (violates P5 Single-Action + Broken Symmetry)
- Full-file preload (violates LA-2/LA-4 + JIT policy)

---

## Source

- `prompts/meta/meta-antipatterns.md §AP-09, §AP-10`
- `prompts/meta/meta-antipatterns.md §AP-03 / §AP-05 STRUCTURAL ENFORCEMENT`
- `prompts/meta/meta-ops.md §AUDIT-02 Procedure A — Two-Path Requirement`
- Plan file: `.claude/plans/curried-launching-liskov.md`
- Merged: `93e1c7a` (2026-04-11) meta(v5.2): Track A+B evolution

## Related entries

- [[WIKI-M-001]] v5.1 Concurrency-Aware Worktree Model — companion architectural layer
- [[WIKI-M-002]] v4.1 3-Pillar Protocol — CoVe/Schema/JIT foundation that AP-03 STRUCTURAL ENFORCEMENT composes with
