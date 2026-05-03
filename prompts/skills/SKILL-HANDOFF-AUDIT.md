# SKILL-HANDOFF-AUDIT

id: SKILL-HANDOFF-AUDIT
purpose: Validate handoff envelope shape and artifact-only review boundary.
trigger:
- receiving HAND-01
- auditing HAND-02
- before accepting Specialist artifacts
minimal_instruction: Check schema, scope, artifact paths, signed contracts, and forbidden context before work.
full_ref: prompts/meta/kernel-ops.md §HAND-03
input_contract:
- HandoffEnvelope
- artifact paths from DISPATCH.inputs
- signed Interface Contract when cross-domain
forbidden_context:
- chain-of-thought
- producing agent transcript
- intermediate files not listed in DISPATCH.inputs
success_metric:
- schema-valid envelope
- no forbidden input
- HAND-03 C1-C7 verdict emitted
token_target: 140
