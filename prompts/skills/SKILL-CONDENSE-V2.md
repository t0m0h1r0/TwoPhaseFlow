# SKILL-CONDENSE-V2

id: SKILL-CONDENSE-V2
purpose: Produce adaptive context checkpoints that preserve constraints, risks, and restart viability.
trigger:
- context utilization >= 60%
- turn count >= 30
- long handoff chain or unresolved STOP/AP flags
minimal_instruction: Emit V1 fields plus v8 objective, immutable constraints, state delta, risk flags, lost-context test, and any compression failure log.
full_ref: prompts/meta/kernel-ops.md §OP-CONDENSE
input_contract:
- current objective
- produced artifact paths and hashes
- open STOP/AP flags
- next action
forbidden_context:
- raw transcript as restart context
- chain-of-thought
- unresolved blocker omission
success_metric:
- restart agent can answer lost_context_test
- open issues preserved
- artifact hashes included
token_target: 170
