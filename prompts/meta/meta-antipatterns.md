# META-ANTIPATTERNS: Known Failure Modes & Mitigation Library
# VERSION: 1.0.0
# ABSTRACT LAYER — WHAT TO AVOID: catalogues recurring agent failure patterns with
# detection criteria, root cause, and mitigation. Injected into agent prompts at
# generation time based on the agent's archetypal role and domain.
# FOUNDATION (φ1–φ7, A1–A11): prompts/meta/meta-core.md  ← READ FIRST

────────────────────────────────────────────────────────
# § PURPOSE

Agents learn effectively from negative examples. This file defines anti-patterns —
recurring failure modes observed across agent executions — with machine-verifiable
detection criteria and concrete mitigation actions.

**Usage by EnvMetaBootstrapper:**
Each anti-pattern declares an `inject` list of agent roles. At Stage 3, the bootstrapper
includes the anti-pattern's DETECTION + MITIGATION block in the generated prompt for
each listed agent. Only anti-patterns relevant to the agent's role are injected (LA-4
Rule Load Budgeting).

**Usage by agents at runtime:**
Before producing output, agents SHOULD scan the anti-pattern list injected into their
prompt and verify they are not exhibiting a listed pattern. Detection criteria are
designed to be self-checkable within a single turn.

────────────────────────────────────────────────────────
# § ANTI-PATTERN CATALOGUE

────────────────────────────────────────────────────────
## AP-01: Reviewer Hallucination

**Summary:** Reviewer reports an error that does not exist in the actual artifact.

**Root cause:** Reviewer operates from memory or summary of the artifact rather than
reading the actual file. LLMs can confabulate plausible-sounding errors when working
from cached or partial context.

**Detection criteria (self-checkable):**
- Reviewer cites a specific line/equation but has NOT read the file in the current turn
- Reviewer's claimed error does not match the actual text at the cited location
- Reviewer uses phrases like "likely", "probably", "I recall" without file evidence

**Mitigation:**
1. Read the actual file (full section) in the same turn as producing the review
2. Quote the exact text being criticized — if you cannot quote it, you have not read it
3. For every reported error: cite file path + line number + quoted text

**Severity if unmitigated:** HIGH — false error reports waste pipeline cycles and erode
trust in the review process.

**Inject:** PaperReviewer, ConsistencyAuditor, TheoryAuditor, PromptAuditor, ResultAuditor

────────────────────────────────────────────────────────
## AP-02: Scope Creep Through Helpfulness

**Summary:** Agent modifies files or adds improvements beyond what was dispatched.

**Root cause:** LLMs have a strong "helpfulness" prior that pushes them to fix adjacent
issues, add documentation, or refactor nearby code. In a multi-agent system, this
bypasses the audit trail and introduces untracked state (φ2 violation).

**Detection criteria (self-checkable):**
- Agent is about to modify a file not listed in DISPATCH `scope_out`
- Agent is about to add a feature, docstring, or comment not requested
- Agent thinks "while I'm here, I should also..."
- Diff contains changes to lines not related to the dispatched task

**Mitigation:**
1. Before every file write: check DISPATCH scope — is this file in scope?
2. If you notice an adjacent issue: log it in RETURN `issues` field — do NOT fix it
3. Rule of thumb: if you cannot trace the change back to a DISPATCH instruction, don't make it

**Severity if unmitigated:** MEDIUM — untracked changes break reproducibility and may
introduce bugs that no test covers (because the test was designed for the dispatched scope).

**Inject:** CodeArchitect, CodeCorrector, CodeReviewer, PaperWriter, PaperCorrector,
RefactorExpert, LogicImplementer

────────────────────────────────────────────────────────
## AP-03: Verification Theater

**Summary:** Agent claims to have verified something without actually performing
independent verification. The verification step produces no new evidence.

**Root cause:** LLMs can generate confident "I verified that X is correct" statements
based on pattern matching rather than actual computation or file reading. The statement
looks like verification but adds zero epistemic value.

**Detection criteria (self-checkable):**
- Agent claims a numerical result without a corresponding tool invocation in the same turn
- Agent says "I verified" but the conversation contains no independent derivation or tool output
- Agent's "verification" is restating the Specialist's claim in different words
- Gatekeeper read the Specialist's reasoning BEFORE performing independent derivation

**Mitigation:**
1. Every numerical claim MUST have a tool invocation (LA-1 TOOL-DELEGATE, LA-2 in §B.1)
2. Every "I verified" MUST be preceded by an independent derivation or tool output
3. Gatekeeper MUST derive first, compare second — sequence is mandatory (MH-3)
4. If you cannot show independent evidence, say "NOT VERIFIED" — do not claim verification

**Severity if unmitigated:** CRITICAL — false verification passes bugs through the gate.
This is the single most dangerous anti-pattern because it silently disables the audit system.

**Inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, TestRunner,
ExperimentRunner, ResultAuditor, CodeWorkflowCoordinator

────────────────────────────────────────────────────────
## AP-04: Gate Paralysis

**Summary:** Gatekeeper repeatedly rejects deliverables without enabling progress,
creating an infinite rejection loop.

**Root cause:** Gatekeeper's skepticism prior is too strong relative to its obligation
to issue CONDITIONAL PASS when all formal checks pass. Moving goalposts — introducing
new criteria after the Specialist addressed previous ones — is a common manifestation.

**Detection criteria (self-checkable):**
- Same deliverable rejected ≥ 2 times
- Current rejection cites a criterion not raised in previous rejection
- All formally citable checks (GA-1 through GA-6, AU2 items) actually pass
- Gatekeeper feels "doubt" but cannot cite a specific violation number

**Mitigation:**
1. Track rejection count per deliverable (MAX_REJECT_ROUNDS = 3)
2. Each rejection MUST cite a specific GA condition or AU2 item number
3. If all formal checks pass but doubt remains: issue CONDITIONAL PASS with Warning Note
4. After 3 rejections: mandatory escalation to user (do not continue the loop)
5. A rejection that cites a new criterion not raised previously = potential Deadlock Violation

**Severity if unmitigated:** HIGH — blocks pipeline progress; demoralizes the system;
wastes tokens on repeated cycles that produce no new information.

**Inject:** ConsistencyAuditor, TheoryAuditor, CodeWorkflowCoordinator,
PaperWorkflowCoordinator, PaperReviewer, PromptAuditor

────────────────────────────────────────────────────────
## AP-05: Convergence Fabrication

**Summary:** Agent reports numerical results (convergence rates, error norms, slopes)
without actually running the computation.

**Root cause:** LLMs can generate plausible-looking numerical tables from training data
patterns. A convergence table showing "order 4.02" for a 4th-order method is exactly
what the LLM expects to see — and it can generate it without running any code.

**Detection criteria (self-checkable):**
- Agent produces a convergence table but no `pytest` or simulation command was executed
- Numerical values in the table do not appear in any tool output in the current session
- Agent says "the convergence rate is approximately X" without citing a log file
- Error norms are suspiciously clean (exact integers, perfect orders)

**Mitigation:**
1. ALL numerical results MUST come from tool output (LA-1 TOOL-DELEGATE — non-negotiable)
2. Every number in a convergence table must be traceable to a specific line in a log file
3. If tests cannot be run (missing dependencies, environment issues): report BLOCKED — do NOT
   fabricate expected results
4. Attach `tests/last_run.log` or equivalent — the log IS the evidence

**Severity if unmitigated:** CRITICAL — fabricated results that look correct propagate
through the entire T-L-E-A pipeline and may end up in the published paper.

**Inject:** TestRunner, ExperimentRunner, ResultAuditor, VerificationRunner,
ConsistencyAuditor, SimulationAnalyst

────────────────────────────────────────────────────────
## AP-06: Context Contamination via Summary

**Summary:** Downstream agent receives a natural-language summary of an upstream agent's
work instead of reading the actual artifact file.

**Root cause:** In single-session LLM environments, conversation history accumulates.
A coordinator may summarize a Specialist's work when dispatching to the Gatekeeper.
This summary carries the Specialist's framing and biases — breaking context isolation.

**Detection criteria (self-checkable):**
- Agent's first action is NOT reading the artifact file directly
- Agent bases its work on a description in the conversation rather than a file read
- DISPATCH `inputs` field contains prose descriptions rather than file paths
- Agent says "based on the above" or "as described earlier" instead of citing a file

**Mitigation:**
1. First action after HAND-03: read the artifact file(s) listed in DISPATCH `inputs`
2. Ignore all conversation text that describes the artifact — read the file yourself
3. If no artifact file path is provided in DISPATCH: request it — do NOT proceed on summaries
4. Isolation level ≥ L1 (→ meta-core.md §B.1): artifact file is the ONLY valid input

**Severity if unmitigated:** HIGH — breaks Broken Symmetry (§B) by smuggling Specialist
framing into the Auditor's context. The Auditor no longer derives independently.

**Inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, ResultAuditor,
CodeWorkflowCoordinator, PaperWorkflowCoordinator

────────────────────────────────────────────────────────
## AP-07: Premature Classification

**Summary:** Agent classifies an error or issue without sufficient evidence, then
treats the classification as settled fact for subsequent decisions.

**Root cause:** LLMs can generate confident classifications (THEORY_ERR / IMPL_ERR,
FATAL / MAJOR / MINOR) early in analysis. Once emitted, the classification anchors
all subsequent reasoning — even if later evidence contradicts it.

**Detection criteria (self-checkable):**
- Agent classifies before completing the prescribed protocol (e.g., A→B→C→D for CodeCorrector)
- Classification appears before the agent has read all relevant files
- Agent changes topic/focus after classifying, without revisiting the classification
- Classification confidence is high but only one evidence source was consulted

**Mitigation:**
1. Complete the full prescribed protocol before emitting any classification (φ7)
2. Explicitly mark early hypotheses as TENTATIVE — do not treat them as settled
3. After completing analysis: revisit and confirm or revise the classification
4. If evidence contradicts initial classification: update it — anchoring bias is a bug

**Severity if unmitigated:** MEDIUM — misclassification routes fixes to the wrong
agent/domain, wasting a full pipeline cycle before the error is discovered.

**Inject:** CodeCorrector, ErrorAnalyzer, ConsistencyAuditor, PaperReviewer,
CodeWorkflowCoordinator

────────────────────────────────────────────────────────
## AP-08: Phantom State Tracking

**Summary:** Agent relies on in-context memory of mutable state (branch name, loop
counter, phase) instead of verifying via tool invocation.

**Root cause:** LLMs track state poorly across long conversations (LA-3). An agent
that "remembers" it is on the `code` branch may actually be on `main` if a checkout
failed silently. An agent that "knows" this is review round 3 may be wrong if the
counter was not externalized.

**Detection criteria (self-checkable):**
- Agent states the current branch without running `git branch --show-current`
- Agent references a loop counter without reading it from docs/02_ACTIVE_LEDGER.md
- Agent assumes a file exists without checking (e.g., "the test file I created earlier")
- Agent says "as I noted earlier" about mutable state

**Mitigation:**
1. Verify ALL mutable state by tool invocation at each step (LA-3)
2. Branch state: `git branch --show-current` — never assume
3. Loop counters: read from docs/02_ACTIVE_LEDGER.md — never count in-context
4. File existence: use Glob or Read tool — never assume from prior turns

**Severity if unmitigated:** MEDIUM — wrong branch = contamination; wrong counter =
exceeded MAX_REVIEW_ROUNDS without escalation; wrong file assumption = missing artifact.

**Inject:** ALL agents (universal anti-pattern)

────────────────────────────────────────────────────────
# § INJECTION RULES FOR EnvMetaBootstrapper

When generating agent prompts (meta-deploy.md Stage 3):

1. Collect all anti-patterns where the agent appears in the `inject` list
2. For TIER-1 (MINIMAL) prompts: inject only AP severity=CRITICAL (AP-03, AP-05)
3. For TIER-2 (STANDARD) prompts: inject AP severity=CRITICAL + HIGH
4. For TIER-3 (FULL) prompts: inject all applicable APs
5. Injection format in generated prompt:

```markdown
### Known Anti-Patterns (self-check before output)
| AP | Pattern | Self-Check |
|----|---------|------------|
| AP-03 | Verification Theater | Did I produce independent evidence? |
| AP-05 | Convergence Fabrication | Does every number trace to a tool output? |
...
```

6. The self-check column is a one-line question the agent asks itself before finalizing output
7. Total AP injection must not exceed 200 tokens (respect LA-4 Rule Load Budgeting)

────────────────────────────────────────────────────────
# § EVOLUTION: ADDING NEW ANTI-PATTERNS

When a new failure mode is observed in execution:

1. Check if an existing AP already covers it (update rather than duplicate)
2. Create a new AP-NN entry with: Summary, Root cause, Detection criteria, Mitigation, Severity, Inject
3. Detection criteria MUST be self-checkable by the agent in a single turn
4. Severity must be one of: CRITICAL / HIGH / MEDIUM / LOW
5. Inject list must name specific agent roles (not "all" unless truly universal like AP-08)
6. Add the AP to this file; EnvMetaBootstrapper will pick it up on next regeneration
