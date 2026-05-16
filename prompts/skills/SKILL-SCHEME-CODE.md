# SKILL-SCHEME-CODE

id: SKILL-SCHEME-CODE
purpose: Decompose scientific scheme/code tasks into equation-grounded subproblems, bounded candidates, executable evaluators, verifier-gated handoff, and acceptance-critical convergence when the work is material or iterative.
trigger:
- CodeWorkflowCoordinator receives a numerical scheme, research-code, solver-design, or implementation task
- CodeArchitect, CodeCorrector, or TestRunner changes or verifies numerical behavior
minimal_instruction: Start from equations, invariants, interface/boundary conditions, and expected consistency/stability behavior; define implementation paths, evaluator metrics, tests, and verifier role before patching; for material or iterative repairs apply ARTIFACT-CONVERGENCE-01 with the code adapter.
full_ref: prompts/meta/kernel-ops.md §SCHEME-CODE-01
input_contract:
- governing equation or paper/memo/spec references
- declared implementation paths and forbidden paths
- verification cases, tolerances, and resource budget
forbidden_context:
- benchmark-score-only acceptance
- unrelated infrastructure optimization
- generated code accepted without local execution
- deck-specific artifacts or audience-belief language required for code work
success_metric:
- SchemeCodePlan exists or is explicitly waived for trivial non-numerical edits
- bounded diff passes unit/regression plus scientific verification where behavior changes
- TestRunner reports commands, tolerances, pass/fail, residual risks, and acceptance-critical remaining delta when iterative
token_target: 220
