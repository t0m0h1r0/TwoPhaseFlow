# SKILL-SCHEME-CODE

id: SKILL-SCHEME-CODE
purpose: Decompose scientific scheme/code tasks into equation-grounded subproblems, bounded candidates, executable evaluators, and verifier-gated handoff.
trigger:
- CodeWorkflowCoordinator receives a numerical scheme, research-code, solver-design, or implementation task
- CodeArchitect, CodeCorrector, or TestRunner changes or verifies numerical behavior
minimal_instruction: Start from equations, invariants, interface/boundary conditions, and expected consistency/stability behavior; define implementation paths, evaluator metrics, tests, and verifier role before patching.
full_ref: prompts/meta/kernel-ops.md §SCHEME-CODE-01
input_contract:
- governing equation or paper/memo/spec references
- declared implementation paths and forbidden paths
- verification cases, tolerances, and resource budget
forbidden_context:
- benchmark-score-only acceptance
- unrelated infrastructure optimization
- generated code accepted without local execution
success_metric:
- SchemeCodePlan exists or is explicitly waived for trivial non-numerical edits
- bounded diff passes unit/regression plus scientific verification where behavior changes
- TestRunner reports commands, tolerances, pass/fail, and residual risks
token_target: 220
