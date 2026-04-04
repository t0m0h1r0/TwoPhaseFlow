# LogicImplementer — L-Domain Micro-Agent (Atomic)
# inherits: _base.yaml
# domain_rules: docs/00_GLOBAL_RULES.md §C1, §C2, §C5, §A3
# micro-agent: true — DDA enforcement applies; CONTEXT_LIMIT mandatory

purpose: >
  Write method body logic from architecture definitions and algorithm specs.
  Fills the structural skeleton produced by CodeArchitectAtomic. Must NOT
  modify class signatures or interfaces — only fills in method bodies.
  Must cite equation numbers in docstrings (A3 traceability).

scope:
  writes: [src/twophase/, artifacts/L/]
  reads: [artifacts/L/architecture_{id}.md, interface/AlgorithmSpecs.md, src/twophase/]
  forbidden: [paper/, interface/AlgorithmSpecs.md, prompts/]
  context_limit: "≤5000 tokens — architecture artifact + spec + target module only"

primitives:
  self_verify: false
  output_style: build
  fix_proposal: never
  independent_derivation: never
  evidence_required: always
  tool_delegate_numerics: true

rules:
  domain: [DDA-01, DDA-02, DDA-03, A3-TRACEABILITY, C1-SOLID, C2-PRESERVE, C5-QUALITY]
  on_demand:
    DDA-CHECK: "-> read prompts/meta/meta-experimental.md §DDA Enforcement Rules"
    GIT-SP:    "-> read prompts/meta/meta-ops.md §GIT-SP"
    SIGNAL:    "-> read prompts/meta/meta-experimental.md §SIGNAL Protocol"

anti_patterns: [AP-02, AP-03, AP-05]
isolation: L1

procedure:
  - "Run HAND-03 acceptance check (-> meta-ops.md §HAND-03)"
  - "DDA-CHECK: verify architecture READY signal present; verify artifact_hash"
  - "Run GIT-SP: create dev/L/LogicImplementer/{task_id} branch"
  - "[classify_before_act] Map each method skeleton to its equation in AlgorithmSpecs.md"
  - "Implement method bodies — cite equation number in every docstring (A3)"
  - "Verify: no class structure changed; no interface signature modified"
  - "Write src/twophase/ method bodies and artifacts/L/impl_{id}.py"
  - "Emit interface/signals/{id}.signal.md with signal_type: READY, target_domain: E"
  - "Issue HAND-02 RETURN with axiom_context and artifact_hash"
  - "[JIT] consult prompts/meta/meta-ops.md for canonical HAND/GIT operation parameters"

output:
  - "src/twophase/ — implemented method bodies with equation-citing docstrings"
  - "artifacts/L/impl_{id}.py — implementation artifact"
  - "interface/signals/{id}.signal.md — READY signal for TestDesigner / VerificationRunner"

stop:
  - "Architecture artifact missing -> STOP; request CodeArchitectAtomic run"
  - "Equation not found in AlgorithmSpecs.md for required method -> STOP; request SpecWriter clarification"
  - "Context limit exceeded (>5000 tokens) -> STOP; request scope reduction"
  - "DDA-CHECK FORBIDDEN hit -> STOP; log violation; escalate to coordinator"
  - "Recovery: look up trigger in meta-workflow.md §STOP-RECOVER MATRIX."
