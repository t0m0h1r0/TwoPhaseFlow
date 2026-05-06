# SKILL-PRESENTATION-DECK

id: SKILL-PRESENTATION-DECK
purpose: Create research-grounded decks through staged planning, editable generation, render review, and talk-track alignment.
trigger:
- PresentationWriter receives a slide deck, talk deck, or paper-to-presentation task
- Paper/RevisionBrief/EvidencePackage must become audience-facing slides
minimal_instruction: Derive the narrative spine, fit it to the slide/time budget, give each slide one sourced message, use editable slide source, render-review the output, and align notes with the talk track.
full_ref: prompts/meta/kernel-ops.md §PRESENTATION-GEN-01
input_contract:
- paper/sections, docs/memo, docs/wiki, or experiment/ch*/results paths
- signed RevisionBrief or EvidencePackage when claims go beyond source summary
- audience, venue/language, and slide/time budget when known
output_contract:
- deck outline/source under `paper/presentations/{deck_id}/`
- narrative spine: audience problem -> paper insight -> evidence -> implication
- slide source map, lead list, visual plan, message budget, rendered artifacts, and review notes
best_practices:
- start from audience knowledge; choose the shortest path to the contribution
- enforce slide/time budget; move derivations, caveats, and secondary details to notes/backup
- one claim per slide; lead is larger than labels/captions/notes
- visual hierarchy: lead -> visual -> labels -> source note
- use SKILL-PRESENTATION-ILLUSTRATION only for conceptual or reverse-readback visual tasks
- prefer diagrams/charts/timelines/mechanisms/comparisons over dense bullets
- preserve uncertainty, assumptions, limits, and cited quantitative/novelty/benchmark claims
- audience check: what remains after 30 seconds, 5 minutes, and the ending?
review_criteria:
- narrative clarity, compression quality, audience recall, cognitive load, source fidelity
forbidden_context:
- claims remembered from conversation but not present in artifacts
- unverified SOTA, novelty, benchmark, or numerical claims
success_metric:
- each slide has lead, visual, source refs, one message, and a role in the spine
token_target: 220
