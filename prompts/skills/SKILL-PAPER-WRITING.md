# SKILL-PAPER-WRITING

id: SKILL-PAPER-WRITING
purpose: Write or revise manuscript sections from author intent, sourced claims, scoped evidence, focused feedback, bounded revision actions, and reviewer-oriented convergence when the work is material or iterative.
trigger:
- PaperWriter drafts, expands, revises, abstracts, related-work text, or review responses
- PaperReviewer audits manuscript claims, scope, or content feedback
minimal_instruction: Record author key points, build a claim register with source refs and scope limits, draft from a section outline, then revise only dispatched paragraphs with content-focused feedback; for material or iterative revisions apply ARTIFACT-CONVERGENCE-01 with the paper adapter.
full_ref: prompts/meta/kernel-ops.md §PAPER-WRITE-01
input_contract:
- target section and writing task type
- source paths with section/line claim scope
- author perspective, intended contribution, exclusions, and length/terminology constraints
forbidden_context:
- unsupported claim broadening
- citation as summary without rhetorical function
- silent rewrite outside dispatched scope
- deck-specific artifacts or audience rules required for manuscript work
success_metric:
- each material claim has source refs, scope limit, and allowed strength
- revision actions are recorded and bounded to the task
- AI-use transparency record names source materials and verification actions
- iterative reviews track acceptance-critical claim/evidence/rhetoric issues or explicitly waive ARTIFACT-CONVERGENCE
token_target: 220
