# PURPOSE
Generate a minimal, role-specific, environment-optimized agent prompt from meta-prompt.md.

# INPUTS
- prompts/meta/meta-prompt.md (axiom and protocol source)
- target role name
- target environment: Claude
- docs/ACTIVE_STATE.md (current phase context)

# CONSTRAINTS
- preserve all core axioms: A1–A7 (see meta-prompt.md)
- preserve all control protocols: P1–P7
- one role per prompt — no mixed responsibilities
- diff-only modifications to existing prompts
- explicit stop conditions required in every output
- escalation paths must be named explicitly
- layer isolation enforced: Structure / Content / Tags / Style
- solver / infra separation enforced (see A5)
- no implicit assumptions — use external memory only (see A2)

# PROCEDURE
1. Read prompts/meta/meta-prompt.md — extract axioms, protocols, state machine, template
2. Identify role scope, layer ownership, and solver/infra boundary for the target role
3. Draft prompt using STANDARD PROMPT TEMPLATE from meta-prompt.md
4. Verify: no cross-layer leakage, no solver/infra mixing, stop conditions present
5. Output final prompt + brief change rationale (diff style if updating existing)

# OUTPUT
1. Decision Summary — role scope, layer ownership, constraints applied
2. Final prompt text (complete, ready to deploy)
3. Risks / Missing constraints
4. Status: READY | NEEDS_REVIEW

# STOP
- role scope is ambiguous → escalate, do not guess
- axiom conflict detected → report conflict and stop
- layer isolation cannot be preserved for this role → stop
- meta-prompt.md is unreadable → stop
