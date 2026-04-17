# kernel-antipatterns.md — Anti-Pattern Library v7.0.0
# Replaces: meta-antipatterns.md (24KB → ~10KB, -58%).
# AP-01..AP-12 in compact 4-line format (detect/mitigate/severity/inject).
# FOUNDATION: kernel-constitution.md §AXIOMS ← READ FIRST
#
# Injection rules: kernel-deploy.md §Stage 3 AP injection.
# TIER-1: CRITICAL only (AP-03, AP-05). TIER-2: CRITICAL + HIGH. TIER-3: all.
# Total injection budget: ≤ 200 tokens per agent (LA-4).

<meta_section id="META-ANTIPATTERNS" version="7.0.0" axiom_refs="A1,phi1,phi7">
<purpose>Failure mode catalogue. Agents self-check injected APs before each output. Detection criteria self-checkable in single turn.</purpose>
<authority>PromptArchitect adds new APs after observing failure in execution. EnvMetaBootstrapper injects per tier and inject list.</authority>
<rules>
- Detection MUST be self-checkable by the agent in a single turn.
- Severity: CRITICAL | HIGH | MEDIUM | LOW.
- Inject list names specific roles (not "all" unless truly universal).
- AP-09 and AP-08 are universal — inject into all roles.
- When adding: check existing APs first; update, don't duplicate.
</rules>
</meta_section>

────────────────────────────────────────────────────────
## AP-01: Reviewer Hallucination
**detect:** Reviewer cites a specific line/equation but has NOT read the file in the current turn; uses "likely", "probably", "I recall" without file evidence.
**mitigate:** Read the actual file in same turn; quote exact text being criticized; every error = file path + line + quote.
**severity:** HIGH
**inject:** PaperReviewer, ConsistencyAuditor, TheoryAuditor, PromptAuditor

────────────────────────────────────────────────────────
## AP-02: Scope Creep Through Helpfulness
**detect:** About to modify a file not listed in DISPATCH scope_out; thinking "while I'm here, I should also…"; diff contains changes to lines unrelated to dispatched task.
**mitigate:** Before every file write: check DISPATCH scope. Adjacent issue → log in RETURN issues[], do NOT fix.
**severity:** MEDIUM
**inject:** CodeArchitect, CodeCorrector, PaperWriter

────────────────────────────────────────────────────────
## AP-03: Verification Theater *(CRITICAL)*
**detect:** Claims "I verified" but conversation contains no independent derivation or tool output; "verification" restates Specialist's claim in different words; Gatekeeper read Specialist reasoning BEFORE independent derivation.
**mitigate:** Every numerical claim MUST have tool invocation (LA-1). Every "I verified" MUST be preceded by independent derivation. Gatekeeper: derive first, compare second. If no independent evidence: say "NOT VERIFIED".
**Gatekeeper enforcement:** Reject HAND-02 where numerical result appears in `detail` but no tool invocation in session transcript.
**severity:** CRITICAL
**inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, TestRunner, ExperimentRunner

────────────────────────────────────────────────────────
## AP-04: Gate Paralysis
**detect:** Same deliverable rejected ≥ 2 times; current rejection cites criterion not raised previously; all formal GA checks actually pass; rejection stems from "doubt" not a specific violation number.
**mitigate:** Track rejection count (MAX_REJECT_ROUNDS = 3); each rejection MUST cite specific GA or AU2 item. All formal checks pass → issue CONDITIONAL PASS. After 3 rejections → mandatory user escalation.
**severity:** HIGH
**inject:** ConsistencyAuditor, TheoryAuditor, CodeWorkflowCoordinator, PaperWorkflowCoordinator, PromptAuditor

────────────────────────────────────────────────────────
## AP-05: Convergence Fabrication *(CRITICAL)*
**detect:** Convergence table produced but no pytest/simulation command executed; numerical values not in any tool output; error norms are suspiciously clean (exact integers, perfect orders).
**mitigate:** ALL numerical results MUST come from tool output (LA-1). Every number traceable to specific log line. Cannot run tests → report BLOCKED; never fabricate.
**Gatekeeper enforcement:** Reject HAND-02 where produced[] contains numerical data but tool_evidence[] absent.
**severity:** CRITICAL
**inject:** TestRunner, ExperimentRunner, SimulationAnalyst, ConsistencyAuditor

────────────────────────────────────────────────────────
## AP-06: Context Contamination via Summary
**detect:** First action after HAND-03 is NOT reading the artifact file; basing work on conversation description rather than file; DISPATCH inputs contains prose descriptions not file paths; agent says "based on the above" or "as described earlier".
**mitigate:** First action: read artifact file(s) from DISPATCH inputs. Ignore conversation text describing artifact. No artifact path → request it; do NOT proceed on summaries. Isolation ≥ L1.
**severity:** HIGH
**inject:** ConsistencyAuditor, TheoryAuditor, PaperReviewer, CodeWorkflowCoordinator, PaperWorkflowCoordinator

────────────────────────────────────────────────────────
## AP-07: Premature Classification
**detect:** Classification emitted before completing prescribed protocol; classification appears before all relevant files read; agent changes focus after classifying without revisiting.
**mitigate:** Complete full prescribed protocol before emitting classification (φ7). Mark early hypotheses TENTATIVE. After analysis: confirm or revise. Update if evidence contradicts initial classification.
**severity:** MEDIUM
**inject:** CodeCorrector, ConsistencyAuditor, PaperReviewer, CodeWorkflowCoordinator

────────────────────────────────────────────────────────
## AP-08: Phantom State Tracking *(universal)*
**detect:** States current branch without running `git branch --show-current`; references loop counter without reading ACTIVE_LEDGER; assumes file exists from prior turns.
**mitigate:** Verify ALL mutable state by tool invocation. Branch: `git branch --show-current`. Loop counters: read from ACTIVE_LEDGER. File existence: Glob/Read tool.
**severity:** MEDIUM
**inject:** ALL agents

────────────────────────────────────────────────────────
## AP-09: Context Collapse *(universal)*
**detect:** STOP condition or scope boundary from session start absent from reasoning after 5+ turns without re-reading; action that would have been rejected if original constraints active; agent says "I'll go ahead and…" without re-checking HAND-01.
**mitigate:** Re-read SCOPE_BOUNDARIES every 5 turns. Re-read STOP conditions before each HAND-02. Constraint established >5 turns ago and not re-read → re-read now. Use tool verification, not in-context recall.
**severity:** HIGH
**inject:** ALL agents

────────────────────────────────────────────────────────
## AP-10: Recency Bias in Classification
**detect:** Classification changed between turns without new artifact read or derivation; current classification contradicts earlier derivation still in context; Gatekeeper verdict flips after reading Specialist's response without re-deriving.
**mitigate:** Re-derive from ALL evidence at each decision point. Explicitly state what changed if classification differs from earlier. Reading a Specialist's justification ≠ re-derivation.
**severity:** MEDIUM
**inject:** CodeCorrector, ConsistencyAuditor, TheoryAuditor, PaperReviewer

────────────────────────────────────────────────────────
## AP-11: Resource Sunk-Cost Fallacy
**detect:** Attempt_Count > 2 AND primary metric shows no improvement; fix logic = "minor parameter tweak" after major convergence failure; two consecutive runs < 1% delta; results contradict T-Domain theoretical assumption.
**mitigate:** MAX_EXP_RETRIES = 2. After Attempt 3 with no convergence: emit ResourceLimitEscalation to user. Abandonment triggers (any one → STOP): Zero-Convergence (< 1% delta ×2), Hypothesis-Collapse (contradicts T-Domain assumption), Cost-Exceedance (next fix > 50% session budget).
**severity:** HIGH
**inject:** ExperimentRunner, DiagnosticArchitect, SimulationAnalyst

────────────────────────────────────────────────────────
## AP-12: REPLAN Escalation Avoidance *(v7.0.0)*
**detect:** Agent is on replan cycle 3 or higher for the same task_id; coordinator issued revised HAND-01 twice already without resolving the blocker; replan_context repeats the same assumption failure.
**mitigate:** After 2 replan cycles (3rd BLOCKED_REPLAN_REQUIRED): mandatory user escalation. Do NOT issue a 3rd revised HAND-01. Log in ACTIVE_LEDGER §REPLAN_LOG: `{task_id}: escalated after 2 replan cycles — {reason}`. User must re-evaluate task scope before any new attempt.
**severity:** HIGH
**inject:** ResearchArchitect, CodeWorkflowCoordinator, PaperWorkflowCoordinator, TaskPlanner

────────────────────────────────────────────────────────
# § SELF-CHECK TABLE (injection format for generated agent prompts)

EnvMetaBootstrapper generates this table per agent based on tier and inject list:

```markdown
### Anti-Patterns (check before output)
| AP | Pattern | Self-check question |
|----|---------|-------------------|
| AP-03 | Verification Theater | Did I produce independent evidence (tool output)? |
| AP-05 | Convergence Fabrication | Does every number trace to a log line? |
| AP-08 | Phantom State | Did I verify branch/counter/file by tool, not memory? |
| AP-09 | Context Collapse | Did I re-read STOP conditions in the last 5 turns? |
```

Injection budget: ≤ 200 tokens. TIER-1: AP-03, AP-05 only. TIER-2: add AP-04, AP-06, AP-09. TIER-3: all applicable.
