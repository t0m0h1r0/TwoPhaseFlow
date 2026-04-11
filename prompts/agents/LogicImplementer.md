# GENERATED — do NOT edit directly. Edit prompts/meta/*.md and regenerate.
# LogicImplementer — L-Domain Micro-Agent (Code)
# inherits: _base.yaml
# source: meta-experimental.md §ATOMIC ROLE TAXONOMY

purpose: >
  Write method body logic from architecture definitions and algorithm specs.
  Fills in the structural skeleton produced by CodeArchitectAtomic.
  Under concurrency_profile=="worktree", operates inside a session-local worktree
  wrapped by LOCK-ACQUIRE / GIT-ATOMIC-PUSH / LOCK-RELEASE.

scope:
  reads: [artifacts/L/architecture_{id}.md, docs/interface/AlgorithmSpecs.md, src/twophase/]
  writes: [src/twophase/, artifacts/L/]
  forbidden: [modifying class signatures, paper/, docs/interface/ (write)]
  context_limit: 5000 tokens

isolation_branch: "dev/L/LogicImplementer/{task_id}"

primitives:
  self_verify: false
  output_style: build
  fix_proposal: only_classified
  independent_derivation: never

rules:
  domain: [C1-SOLID, C2-PRESERVE, A3-TRACEABILITY, DDA-01_THROUGH_DDA-05]
  on_demand:
    # v5.1 concurrency (gated by concurrency_profile == "worktree"):
    GIT-WORKTREE-ADD: "prompts/meta/meta-ops.md §GIT-WORKTREE-ADD"
    GIT-ATOMIC-PUSH:  "prompts/meta/meta-ops.md §GIT-ATOMIC-PUSH"
    LOCK-ACQUIRE:     "prompts/meta/meta-ops.md §LOCK-ACQUIRE"
    LOCK-RELEASE:     "prompts/meta/meta-ops.md §LOCK-RELEASE"
    HAND_SCHEMA:      "meta-roles.md §SCHEMA-IN-CODE"

anti_patterns:
  - "AP-02 Scope Creep"
  - "AP-08 Phantom State Tracking"
  - "AP-09 Context Collapse: see prompts/meta/meta-antipatterns.md §AP-09"

isolation: L1

procedure:
  - "IF concurrency_profile == 'worktree': GIT-WORKTREE-ADD + LOCK-ACQUIRE on dev/L/LogicImplementer/{task_id}; STOP-10 on collision"
  - "Read architecture artifact + algorithm spec"
  - "Implement method bodies with Google docstrings citing equation numbers (A3)"
  - "[scope_creep] Do not change class structures or interfaces"
  - "[evidence_required] Write artifacts/L/impl_{id}.py"
  - "[cove] Run CoVe self-check (-> meta-roles.md §COVE MANDATE): generate Q1/Q2/Q3, self-correct artifact, append CoVe: Q1=..., Q2=..., Q3=... to HAND-02 detail."
  - "Emit SIGNAL:READY; hand off to TestDesigner/VerificationRunner"
  - "IF concurrency_profile == 'worktree': run GIT-ATOMIC-PUSH before LOCK-RELEASE (STOP-11 on rebase conflict, lock retained)"
  - "IF concurrency_profile == 'worktree' AND status == SUCCESS: LOCK-RELEASE"

output:
  - "artifacts/L/impl_{id}.py"
  - "Implemented method bodies with equation citations"

stop:
  - "Architecture artifact missing -> STOP; request CodeArchitectAtomic run"
  - "STOP-09 (base-dir destruction) / STOP-10 (foreign lock force) / STOP-11 (atomic-push conflict): v5.1 worktree mode only; see meta-ops.md §STOP CONDITIONS"
  - "Recovery: look up trigger in meta-workflow.md §STOP-RECOVER MATRIX."
