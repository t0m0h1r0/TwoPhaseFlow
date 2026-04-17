# WIKI-M-011: Anti-Pattern Catalogue — AP-01..AP-11
**Category:** Meta | **Created:** 2026-04-18 | **Source:** `prompts/meta/meta-antipatterns.md`

## Motivation

LLM-based agents exhibit recurring failure modes that differ from classical software bugs.
These failures are probabilistic, context-dependent, and often self-invisible — the agent
is unaware it is exhibiting the pattern. Explicit cataloguing with machine-verifiable
detection criteria enables both (a) pre-injection into agent prompts at generation time
and (b) self-auditing at runtime before output is finalized.

The catalogue is maintained in `prompts/meta/meta-antipatterns.md` and injected selectively
by EnvMetaBootstrapper (Stage 3) based on LA-4 Rule Load Budgeting:
- TIER-1 (minimal prompts): CRITICAL only (AP-03, AP-05)
- TIER-2 (standard): CRITICAL + HIGH
- TIER-3 (full, e.g. agents-claude/): all applicable APs for the role

---

## Summary Table

| AP | Name | Severity | Meta version | Axioms |
|----|------|----------|--------------|--------|
| AP-01 | Reviewer Hallucination | HIGH | 5.1.0 | φ1, A3 |
| AP-02 | Scope Creep Through Helpfulness | MEDIUM | 5.1.0 | φ5, A4 |
| AP-03 | Verification Theater | **CRITICAL** | 5.1.0 | φ1, A3, A6 |
| AP-04 | Gate Paralysis | HIGH | 5.1.0 | φ5, A8, A6 |
| AP-05 | Convergence Fabrication | **CRITICAL** | 5.1.0 | φ1, A5, A3 |
| AP-06 | Context Contamination via Summary | HIGH | 5.1.0 | φ4, A2, A4 |
| AP-07 | Premature Classification | MEDIUM | 5.1.0 | φ7, A4 |
| AP-08 | Phantom State Tracking | MEDIUM | 5.1.0 | φ4, A2 |
| AP-09 | Context Collapse | HIGH | 5.2.0 | φ4, A2, A1 |
| AP-10 | Recency Bias in Classification | MEDIUM | 5.2.0 | φ1, φ7, A3 |
| AP-11 | Resource Sunk-Cost Fallacy | HIGH | 5.3.0 | A5, φ4 |

---

## AP Entries

### AP-01: Reviewer Hallucination
**Pattern:** Reviewer reports an error that does not exist in the actual artifact — operating
from memory or summary rather than reading the file.
**Detection:** Reviewer cites line/equation without having read the file in the current turn;
uses "likely", "probably", "I recall" without evidence.
**Mitigation:** Read the actual file in the same turn; quote the exact text being criticized;
cite file path + line number for every reported error.
**Inject:** PaperReviewer, ConsistencyAuditor, TheoryAuditor, PromptAuditor, ResultAuditor

---

### AP-02: Scope Creep Through Helpfulness
**Pattern:** Agent modifies files or adds improvements beyond what was dispatched — the
LLM "helpfulness" prior overrides scope constraints (φ2 violation).
**Detection:** About to modify a file not in DISPATCH `scope_out`; thinking "while I'm here...".
**Mitigation:** Check DISPATCH scope before every write; log adjacent issues in RETURN
`issues` field — do NOT fix them.
**Inject:** CodeArchitect, CodeCorrector, PaperWriter, RefactorExpert, LogicImplementer

---

### AP-03: Verification Theater ← CRITICAL
**Pattern:** Agent claims to verify something without performing independent verification.
The step produces no new evidence — it is pattern-matched confidence, not computation.
**Detection:** Numerical result with no tool invocation in the same turn; "I verified" without
independent derivation; Gatekeeper reads Specialist's reasoning before deriving independently.
**Mitigation:** Every numerical claim requires a tool invocation (LA-1); every "verified"
requires prior independent derivation; Gatekeeper must derive first, compare second (MH-3).
**Structural Enforcement (Gatekeeper):** Reject any HAND-02 where numerical results appear
in `detail` but no tool invocation appears in the session transcript.
**Inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, TestRunner, ExperimentRunner

---

### AP-04: Gate Paralysis
**Pattern:** Gatekeeper repeatedly rejects deliverables with moving goalposts, creating
an infinite rejection loop. New criteria appear after previous ones were addressed.
**Detection:** Same deliverable rejected ≥ 2 times; current rejection introduces a criterion
not raised previously; all formal GA/AU2 checks actually pass.
**Mitigation:** Track rejection count per deliverable; MAX_REJECT_ROUNDS = 3; each rejection
must cite a specific GA condition or AU2 item; issue CONDITIONAL_PASS when formal checks
pass even if informal doubt remains; escalate to user after 3 rejections.
**Inject:** ConsistencyAuditor, TheoryAuditor, CodeWorkflowCoordinator, PaperReviewer

---

### AP-05: Convergence Fabrication ← CRITICAL
**Pattern:** Agent reports numerical results (convergence rates, error norms, slopes) without
running the computation. LLMs generate plausible-looking tables from training patterns.
**Detection:** Convergence table produced but no pytest or simulation command executed;
values do not appear in tool output; numbers are suspiciously clean (exact integer orders).
**Mitigation:** ALL numerical results must come from tool output (LA-1, non-negotiable);
every number must trace to a specific line in a log file; report BLOCKED if tests cannot run.
**Structural Enforcement (Gatekeeper):** Reject any HAND-02 where `produced[]` contains
numerical data but `tool_evidence[]` is absent.
**Inject:** TestRunner, ExperimentRunner, ResultAuditor, VerificationRunner, SimulationAnalyst

---

### AP-06: Context Contamination via Summary
**Pattern:** Downstream agent receives a natural-language summary of upstream work instead
of reading the artifact file — importing the Specialist's framing and biases.
**Detection:** First action is NOT reading the artifact file; bases work on conversation
description rather than file read; DISPATCH `inputs` contains prose not file paths.
**Mitigation:** First action after HAND-03 must be reading the artifact file listed in
DISPATCH `inputs`; ignore all conversation text describing the artifact.
**Inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, ResultAuditor, CodeWorkflowCoordinator

---

### AP-07: Premature Classification
**Pattern:** Agent classifies an error before completing analysis, then treats the
classification as settled — even when later evidence contradicts it.
**Detection:** Classification appears before all relevant files were read; agent changes
topic after classifying without revisiting; high confidence from only one evidence source.
**Mitigation:** Complete the full prescribed protocol before emitting any classification (φ7);
mark early hypotheses as TENTATIVE; revisit and confirm or revise after completing analysis.
**Inject:** CodeCorrector, ErrorAnalyzer, ConsistencyAuditor, CodeWorkflowCoordinator

---

### AP-08: Phantom State Tracking
**Pattern:** Agent relies on in-context memory of mutable state (branch name, loop counter,
phase) instead of verifying via tool invocation. State tracking degrades over long sessions (LA-3).
**Detection:** Agent states current branch without running `git branch --show-current`;
references loop counter without reading from ACTIVE_LEDGER; assumes file exists from prior turns.
**Mitigation:** Verify ALL mutable state by tool invocation at each step; never track branch
or counters in-context; use Glob/Read to verify file existence.
**Inject:** ALL agents (universal)

---

### AP-09: Context Collapse ← added v5.2.0
**Pattern:** In long sessions, constraints established early (scope boundaries, STOP conditions,
domain restrictions) are gradually forgotten. The agent does not "decide" to ignore them —
it simply fails to retrieve them as attention degrades for early tokens.
**Detection:** A STOP condition stated at session start is absent from reasoning after 5+ turns
without re-reading; agent takes an action that would have been rejected if original constraints
were active.
**Mitigation:** Re-read `SCOPE_BOUNDARIES` from HAND-01 every 5 turns; re-read STOP
conditions before each HAND-02; use tool verification rather than in-context recall.
**Inject:** ALL agents (universal — affects every role in long sessions)

---

### AP-10: Recency Bias in Classification ← added v5.2.0
**Pattern:** Most recently seen evidence disproportionately influences classification.
Gatekeeper silently revises verdict toward Specialist's framing after reading their
justification — without re-deriving from primary sources.
**Detection:** Classification changed between turns without new artifact read; current
classification contradicts earlier derivation still visible in context; Gatekeeper's verdict
flips after reading Specialist response.
**Mitigation:** Re-derive classification from ALL evidence at each decision point;
explicitly state what changed and why if classification differs from earlier derivation;
reading a Specialist's justification does NOT constitute re-derivation.
**Inject:** CodeCorrector, ConsistencyAuditor, TheoryAuditor, PaperReviewer

---

### AP-11: Resource Sunk-Cost Fallacy ← added v5.3.0
**Pattern:** Agent repeatedly applies minor fixes to a fundamentally broken experiment
rather than stopping. Resistance to marking a task STOPPED increases with investment made.
**Detection:** Attempt_Count > 2 with no improvement; fix logic is "minor parameter tweak"
after major convergence failure; two consecutive runs with < 1% delta in primary metric;
result contradicts a T-Domain theoretical assumption.
**Mitigation (RAP-01):** MAX_EXP_RETRIES = 2 (3 total attempts); after attempt 3 with no
convergence, emit ResourceLimitEscalation — do NOT improvise a 4th fix. Abandonment triggers:
(a) Zero-Convergence (two runs < 1% improvement), (b) Hypothesis-Collapse (contradicts
T-Domain assumption), (c) Cost-Exceedance (next fix > 50% of session budget).
**Inject:** ExperimentRunner, DiagnosticArchitect, VerificationRunner, SimulationAnalyst

---

## Evolution Narrative

| Period | Event |
|--------|-------|
| 2026-04-02 | AP-01..AP-08 introduced in commit `2fb2ceb` alongside 9-file meta-architecture and L0–L3 isolation model (v3.0.0 era). Initial names differed slightly from current formulation (e.g. AP-04 was "Coordinator Overreach", AP-05 was "Fabricated Numeric Results"). |
| 2026-04-02 | AP-03 and AP-05 designated CRITICAL — the two patterns most likely to produce silently wrong outputs that pass through the gate. |
| 2026-04-11 | v5.1.0 XML Hybrid format applied: all APs wrapped in `<meta_section id="AP-NN" version="5.1.0">` with `immutable="true"` on the constitutional sections. AP names and content refined from initial introduction. |
| 2026-04-12 | **AP-09** (Context Collapse, HIGH) and **AP-10** (Recency Bias, MEDIUM) added in commit `5091d55` as part of v5.2.0 LLM-specific hardening. Both are universal injections — they affect every role in long sessions. §STRUCTURAL ENFORCEMENT blocks added to AP-03 and AP-05 to enforce Gatekeeper-side rejection independent of agent self-report. |
| v5.3.0 | **AP-11** (Resource Sunk-Cost Fallacy, HIGH) added; ties directly to RAP-01 (Retry Abort Protocol) introduced in `72e1cb8`. |

## Cross-References

- `→ WIKI-M-003`: v5.2 hardening — AP-09/10 introduction + Structural Enforcement on AP-03/AP-05
- `→ WIKI-M-002`: CoVe Mandate — the structural protocol that AP-03 violations would break
- `→ WIKI-M-008`: RAP-01 — the retry protocol that AP-11 mitigation is based on
- `→ WIKI-M-006`: Micro-agent architecture — DDA and SIGNAL supplement AP-08 mitigation (state via filesystem, not memory)
- `→ prompts/meta/meta-antipatterns.md §INJECTION RULES`: bootstrapper AP injection logic
