# WIKI-M-019: Workflow & Concurrency Protocols
**Category:** Meta | **Created:** 2026-04-18
**Sources:** `prompts/meta/meta-workflow.md` (full), `prompts/meta/meta-core.md §B.1`

## P-E-V-A Execution Loop

Master execution frame for ALL domain work. No phase may be skipped.

| Phase | Responsibility | Agent | Output | Git Phase |
|-------|---------------|-------|--------|-----------|
| PLAN | Define scope, success criteria, stop conditions | Coordinator or ResearchArchitect | task scope (temp_work_log) | — |
| EXECUTE | Produce artifact; run CoVe self-check before HAND-02 | Specialist (CodeArchitect, PaperWriter, PromptArchitect, …) | code / patch / paper / prompt | DRAFT commit |
| VERIFY | Confirm artifact meets spec (independent agent) | TestRunner / PaperCompiler+Reviewer / PromptAuditor | PASS or FAIL verdict | REVIEWED commit on PASS |
| AUDIT | Gate check; cross-system consistency | ConsistencyAuditor / PromptAuditor | AU2 gate verdict (10 items) | VALIDATED commit + merge on PASS |

**Loop rules:**
- FAIL at VERIFY → return to EXECUTE (not PLAN unless scope changes)
- FAIL at AUDIT → return to EXECUTE
- Loop counter tracked per phase (P6); MAX_REVIEW_ROUNDS = 5
- AUDIT agent must be independent of EXECUTE agent (φ7)
- PLAN always starts with ResearchArchitect loading `docs/02_ACTIVE_LEDGER.md`

**CoVe (Chain-of-Verification) — mandatory inside EXECUTE, before HAND-02:**
1. Generate 3 adversarial questions (Q1 logical, Q2 axiom compliance, Q3 scope/IF-Agreement fidelity)
2. Derive answers independently; correct the artifact for any flaw found
3. Place ONLY the corrected artifact in HAND-02 payload; append `"CoVe: Q1=..., Q2=..., Q3=..."` to `detail`

CoVe does NOT replace VERIFY. VERIFY = independent agent check (Broken Symmetry).
Missing CoVe summary in `detail` → Gatekeeper MUST reject HAND-02; return to EXECUTE.

---

## Pipeline Mode Selection

ResearchArchitect classifies every incoming task before routing.

| Mode | When to use | Required gates |
|------|-------------|----------------|
| **TRIVIAL** | No interface contract required; single file change; no solver-core changes; 1 domain agent | Informal review; no AU2 required |
| **FAST-TRACK** | Interface contract present; tests required; ≤2 domain agents; limited cross-domain scope | IF-Agreement + TestRunner or PromptAuditor; AU2 recommended but STOP-SOFT on omission |
| **FULL-PIPELINE** | Cross-domain (T→L→E→A); solver-core change; any paper submission; new Interface Contract | Full P-E-V-A; IF-Agreement; AU2 mandatory (STOP-HARD if omitted) |

---

## Parallel Execution Rules (PE / BS / RC)

### Parallel Eligibility (PE)

| Rule | Description |
|------|-------------|
| PE-1 | Tasks with no `depends_on` edges MAY run in parallel |
| PE-2 | Tasks writing to the SAME file/directory MUST NOT run in parallel |
| PE-3 | Same-domain tasks sharing same Gatekeeper MAY run in parallel on separate `dev/` branches |
| PE-4 | Under `concurrency_profile == "worktree"`: each parallel task needs its own worktree + LOCK-ACQUIRE |
| PE-5 | ResearchArchitect MUST verify BRANCH_LOCK_REGISTRY before dispatching parallel tasks |

### Barrier Sync (BS)

- **BS-1:** Stage N+1 does NOT begin until ALL tasks in Stage N issue HAND-02 RETURN
- **BS-2:** Any STOPPED/FAIL in a parallel stage → barrier PARTIAL; next stage BLOCKED
- **BS-3:** User chooses: (a) fix + retry, (b) re-plan, (c) proceed with partial results
- **BS-4:** Task exceeds 3× estimated duration → STATUS_CHECK. Under `concurrency_profile == "worktree"`: any task holding branch lock >24h past `acquired_at` → STATUS_CHECK; if stale → STOP-10 (stale locks NEVER silently reclaimed)

### Resource Conflict (RC)

- **RC-1/2/3:** Collect `writes_to` per task; non-empty intersection → make SEQUENTIAL
- **RC-4:** DOM-02 rules still apply per-agent; RC is an additional pre-dispatch check
- **RC-5 (v5.1):** Under `concurrency_profile == "worktree"`, `writes_to` conflict additionally checked against BRANCH_LOCK_REGISTRY (`docs/02_ACTIVE_LEDGER.md §4`): a task whose branch already appears in §4 under another session MUST NOT be dispatched

---

## CI/CP Pipeline (Continuous Integration / Continuous Paper)

**Trigger:** Any change that affects the T→L→E→A chain (solver core change, new derivation, etc.)

### Propagation Steps

1. **T-Domain** signs `docs/interface/AlgorithmSpecs.md` → triggers L-Domain
2. **L-Domain** signs `docs/interface/SolverAPI_vX.py` → triggers E-Domain
3. **E-Domain** signs `docs/interface/ResultPackage/` → triggers A-Domain
4. **A-Domain** AUDIT → ConsistencyAuditor AU2 gate → merge to `main`

**Rolling validation:** ResearchArchitect may sequence propagation one domain at a time.

### INTEGRITY_MANIFEST Hash Chain

`docs/02_ACTIVE_LEDGER.md` maintains an `[INTEGRITY_MANIFEST]` section:

```
[INTEGRITY_MANIFEST]
  T_hash: {sha256 of docs/interface/AlgorithmSpecs.md at signing}
  L_hash: {sha256 of docs/interface/SolverAPI_vX.py at signing}
  E_hash: {sha256 of docs/interface/ResultPackage/ at signing}
  A_hash: {sha256 of paper/main.pdf at last validated build}
```

Hash mismatch → STOP-08 (CONTAMINATION) → CI/CP re-propagation from the mismatched domain.

---

## v5.1 Concurrency Node Structure

Under `concurrency_profile == "worktree"`, each domain pipeline node has this structure:

```
┌─── LOCK-ACQUIRE (docs/locks/{branch_slug}.lock.json via O_EXCL) ───┐
│                                                                       │
│   Normal node body (GIT-SP + IF-AGREE + P-E-V-A loop)               │
│                                                                       │
│   GIT-ATOMIC-PUSH: fetch + rebase + push                             │
│     → STOP-11 if rebase conflict (STOP-SOFT; lock retained)          │
│                                                                       │
└─── LOCK-RELEASE (after successful GIT-ATOMIC-PUSH) ────────────────┘
```

**Ordering rule:** GIT-ATOMIC-PUSH completes BEFORE LOCK-RELEASE.
A lock held during push guarantees no other session races the push on the same branch.

---

## Domain Pipeline Agent Assignments

| Domain | Branch | Gatekeeper | EXECUTE agents | VERIFY agent(s) | Precondition |
|--------|--------|------------|----------------|-----------------|--------------|
| **T** Theory | `theory` | TheoryAuditor | TheoryArchitect | TheoryAuditor (independent re-derivation) | none |
| **L** Code | `code` | CodeWorkflowCoordinator | CodeArchitect, CodeCorrector | TestRunner (TEST-01/02) | `AlgorithmSpecs.md` signed |
| **E** Experiment | `experiment` | CodeWorkflowCoordinator | ExperimentRunner (EXP-01/02) | CodeWorkflowCoordinator (Validation Guard) | `SolverAPI_vX.py` signed |
| **A** Paper | `paper` | PaperWorkflowCoordinator | PaperWriter | PaperCompiler + PaperReviewer | `ResultPackage/` signed |
| **P** Prompt | `prompt` | PromptArchitect | PromptArchitect | PromptAuditor (Q3 checklist) | none |
| **K** Knowledge | `wiki` | WikiAuditor | KnowledgeArchitect (K-COMPILE) | WikiAuditor (K-LINT) | Any domain artifact at VALIDATED |

**Domain-specific rules:**
- **T:** TheoryAuditor re-derives WITHOUT reading Specialist's work (Broken Symmetry). DISAGREE → STOP; escalate.
- **L:** VERIFY FAIL routing: THEORY_ERR → CodeArchitect; IMPL_ERR → CodeCorrector
- **E:** Absent `SolverAPI_vX.py` → STOP (hard precondition). SC-1..SC-4 must all PASS.
- **A:** 0 FATAL + 0 MAJOR → PASS. AUDIT FAIL: PAPER_ERROR → PaperWriter; CODE_ERROR → CodeArchitect
- **K:** K-COMPILE runs parallel / not blocking main pipeline. K-LINT mandatory pre-merge.

---

## Ledger Update Cadence

Within EXECUTE phase, specialists append to `artifacts/temp_work_log.json` (unstructured, append-only, session-local).
The Gatekeeper performs **batch-update** to `docs/02_ACTIVE_LEDGER.md` at exactly **two moments**:

1. On `HAND-02` receipt (regardless of status)
2. On AU2 `VALIDATED` verdict at AUDIT phase

Between these moments the ledger is **read-only**.
Any write to `02_ACTIVE_LEDGER.md` mid-EXECUTE = **Ledger-Thrash violation** (STOP-SOFT).

---

## Common Pipeline Structure

```
PRE-CHECK  Gatekeeper → GIT-01 (branch preflight) + DOM-01 (domain lock)
IF-AGREE   Gatekeeper → GIT-00 (interface contract) → Specialist creates dev/ branch
PLAN       Gatekeeper → identify gaps, dispatch Specialist
EXECUTE    Specialist → produce artifact on dev/ branch → open PR: dev/ → {domain} (LOG-ATTACHED)
VERIFY     Verifier   → run checks
             → PASS: Gatekeeper merges (GIT-03) + opens PR → main (GIT-04-A)
             → FAIL: loop back to EXECUTE (P6 bounded)
AUDIT      ConsistencyAuditor → AU2 gate
             → PASS: Root Admin merges → main (GIT-04-B)
             → FAIL: route error to responsible agent
```

---

## STOP-RECOVER MATRIX

Every STOP is recoverable — the matrix defines WHO resolves it and WHERE the pipeline resumes.

| STOP Trigger | Severity | Recovery Agent | Recovery Action | Resume Point |
|-------------|----------|---------------|-----------------|-------------|
| Paper/equation ambiguity | STOP-HARD | User → PaperWriter or CodeArchitect | User clarifies; Specialist re-derives | EXECUTE |
| TestRunner FAIL | STOP-HARD | Coordinator → CodeCorrector | Classify THEORY_ERR/IMPL_ERR; dispatch targeted fix | EXECUTE |
| AU2 FAIL — PAPER_ERROR | STOP-HARD | ConsistencyAuditor → PaperWriter | Cite specific AU2 item; fix | EXECUTE |
| AU2 FAIL — CODE_ERROR | STOP-HARD | ConsistencyAuditor → CodeArchitect | Cite specific AU2 item; re-implement | EXECUTE |
| AU2 FAIL — THEORY_ERROR | STOP-HARD | ConsistencyAuditor → TheoryArchitect | Re-derive; TheoryAuditor re-verifies | EXECUTE (T) |
| Authority conflict (paper vs code vs theory) | STOP-HARD | User | Ruling + rationale in LEDGER; φ3 hierarchy | PLAN |
| Merge conflict (GIT) | STOP-HARD | User | Manual conflict resolution; re-run GIT-01 | PRE-CHECK |
| MAX_REJECT_ROUNDS exceeded | STOP-HARD | User → Root Admin | Review both artifacts; binding ruling | VERIFY |
| Loop > MAX_REVIEW_ROUNDS | STOP-HARD | User | Review full loop history; scope decision | PLAN |
| Branch contamination (DOM-02 violation) | STOP-HARD | User | Revert contaminated commit; re-run GIT-SP | PRE-CHECK |
| Upstream contract invalidated (CI/CP) | STOP-HARD | CI/CP propagation | Re-sign upstream; cascade INVALIDATED signals | PLAN |
| Broken Symmetry detected (Auditor saw CoT) | STOP-HARD | Coordinator | Re-dispatch Auditor in fresh L3 session with sanitized inputs | VERIFY |
| Token budget exceeded | STOP-SOFT | Coordinator | Compress context or split task; re-dispatch | EXECUTE |
| Missing input file | STOP-SOFT | Coordinator | Identify which upstream agent produces it; dispatch | PLAN |
| PaperCompiler BUILD-FAIL | STOP-SOFT | PaperWorkflowCoordinator → PaperCompiler | Parse log; surgical fix; re-compile | VERIFY |
| K-LINT broken pointer (K-A2) | STOP-HARD | WikiAuditor → TraceabilityManager | Fix/remove broken pointer; re-run K-LINT | VERIFY |
| SSoT violation (duplicate wiki entry) | STOP-SOFT | WikiAuditor → TraceabilityManager | K-REFACTOR to consolidate duplicates | EXECUTE |
| Source artifact invalidated after wiki compilation | STOP-HARD | WikiAuditor | K-DEPRECATE entry; RE-VERIFY to consumers | PLAN |
| GPU/environment error | STOP-SOFT | User → DevOpsArchitect | Fix environment; re-run experiment | EXECUTE |
| HAND token malformed | STOP-SOFT | DiagnosticArchitect | Re-emit corrected HAND (ERR-R3); Gatekeeper approves | PLAN |
| BUILD-FAIL (dependency/config) | STOP-SOFT | DiagnosticArchitect | Propose install/config fix (ERR-R2); retry | EXECUTE |
| Wrong write path (pre-DOM-02) | STOP-SOFT | DiagnosticArchitect | Propose corrected path (ERR-R1); Specialist retries | EXECUTE |
| GIT conflict on non-logic file | STOP-SOFT | DiagnosticArchitect | Propose merge resolution (ERR-R4) | PRE-CHECK |
| STOP-09: base-directory destruction (v5.1) | STOP-HARD | User | Do NOT auto-delete; verify worktree path violation; manual removal with rationale in LEDGER §4 | PRE-CHECK |
| STOP-10: foreign branch-lock force (v5.1) | STOP-HARD | User | Confirm lock ownership via LEDGER §4 + lock file; `--force` only after verifying holder session crashed; never overwrite live lock | PRE-CHECK |
| STOP-11: atomic-push rebase conflict (v5.1) | STOP-SOFT | User (conflict resolve) + Specialist (resumes) | `git rebase --abort` already run; human resolves rebase; Specialist retains lock (`lock_released: false`); after `git rebase --continue` + tests → re-run GIT-ATOMIC-PUSH | EXECUTE |

**Recovery protocol (5 steps):**
1. Agent triggers STOP → issue RETURN token with `status: STOPPED` + `issues` citing specific trigger
2. Coordinator looks up trigger in matrix → identify Recovery Agent and Resume Point
3. Coordinator dispatches recovery → HAND-01 to Recovery Agent with original task scope + STOP trigger + Resume Point
4. Recovery Agent fixes → HAND-02 RETURN → pipeline resumes at Resume Point
5. If Recovery Agent = "User" → Coordinator issues RETURN STOPPED with full context; awaits input

**Hard rule:** Coordinator that encounters a STOP trigger NOT listed in this matrix → escalate to User. Do not improvise.

---

## DiagnosticArchitect Self-Healing Flow

When Recovery Agent = DiagnosticArchitect:

```
Coordinator
  │── HAND-01 → DiagnosticArchitect (STOP trigger + error class ERR-R?)
  │
  DiagnosticArchitect
  │── Classify: RECOVERABLE or NON-RECOVERABLE
  │   If NON-RECOVERABLE → HAND-02 STOPPED → escalate to User
  │── Write artifacts/M/diagnosis_{id}.md
  │── HAND-01 → Gatekeeper (fix proposal)
  │
  Gatekeeper (DOM-02 + scope check only — NOT scientific correctness)
  │── PASS → DiagnosticArchitect     OR    FAIL → DiagnosticArchitect (increment round counter)
  │
  DiagnosticArchitect
  │── On PASS: HAND-01 → originally blocked agent; resume at Resume Point
  │── On FAIL (round < 3): propose revised fix → back to Gatekeeper
  │── On FAIL (round = 3): HAND-02 STOPPED → coordinator → User
```

**Max 3 repair rounds.** Gatekeeper checks DOM-02 compliance + safety only — not scientific correctness (GA-4/GA-6 do NOT apply to diagnostic proposals).

---

## POST_EXECUTION_REPORT Format

Every agent issuing HAND-02 SHOULD append:

```yaml
POST_EXECUTION_REPORT:
  friction_points:    # steps that caused unnecessary overhead
    - "{rule/protocol ID}: {description}"
  missing_inputs:     # inputs that should have been in the DISPATCH
    - "{artifact_path}: {why needed}"
  protocol_improvement:
    - "{proposed change to meta-ops/workflow/roles}"
  token_efficiency:   # estimate only
    context_used_pct: {N}%
    compressed_steps: {list of steps where A1 token economy helped}
```

---

## META-EVOLUTION POLICY

**Cycle:** Observe → Evaluate → Generalize → Promote → Validate → Compress

**3 Immutable Zones** (require CHK-tracked MetaEvolutionArchitect session):
1. φ1–φ7 and A1–A11 text (STOP-02 if modified outside constitutional session)
2. HAND-03 7-check logic body (semantic integrity of the acceptance gate)
3. SCHEMA-IN-CODE TypeScript interfaces (HandoffEnvelope binding contract)

Non-immutable meta content (can be changed via standard EnvMetaBootstrapper run):
- Domain registry (meta-domains.md) — requires CHK + non-overlapping territory
- Agent profiles (meta-persona.md) — TIER and role changes allowed
- Pipeline modes (meta-workflow.md) — criteria adjustable
- Anti-patterns (meta-antipatterns.md) — new APs can be added

---

## Audit Exit Criteria (Deadlock Prevention)

A Gatekeeper / Auditor may REJECT ONLY when tied to a specific violation of:

| Category | Examples |
|----------|---------|
| 1. Formal Checklist | Q1–Q3 item failed; AUDIT-01 item N failed |
| 2. Interface Contract | Output ≠ contract outputs; contract unsigned |
| 3. Core Axiom | A1–A11 violated (cite axiom + exact violation) |

"Gut feeling" rejection is forbidden. When all formal checks pass → CONDITIONAL PASS:

```
CONDITIONAL PASS:
  verdict:      CONDITIONAL_PASS
  warning_note: {specific concern — must reference a named risk}
  escalate_to:  user
  pipeline:     CONTINUES
```

Auditor withholding PASS without citable violation = **Deadlock Violation**.

---

## Interface Drafting (Speculative Parallel Execution)

TheoryArchitect MAY publish `docs/interface/{id}.draft` once core algorithm structure is known.
CodeArchitect MAY read `.draft` files to build scaffolding in `artifacts/L/scaffold_{id}.py.draft` — never in `src/`.

Rules:
1. No `.draft` artifact may be merged into `src/`, `paper/`, or any domain branch
2. Every draft-derived function carries: `# DRAFT — pending TheoryAuditor signature on docs/interface/{id}.draft`
3. Promotion gate: TheoryAuditor HAND-02 with `interface_contracts_checked: [{id}.draft → SIGNED]` → Gatekeeper removes `.draft` suffix → standard flow
4. TheoryAuditor FAIL on draft → ALL scaffold files MUST be deleted (coordinator dispatches cleanup)

---

## Cross-References

- `→ WIKI-M-001`: v5.1 concurrency protocols (LOCK-ACQUIRE/RELEASE, GIT-ATOMIC-PUSH, STOP-09/10/11)
- `→ WIKI-M-020`: Canonical operations reference (all operation syntax for the protocols above)
- `→ WIKI-M-016`: Design philosophy synthesis (pillars behind P-E-V-A and Broken Symmetry)
- `→ WIKI-M-018`: Domain architecture (the domains that P-E-V-A operates over)
