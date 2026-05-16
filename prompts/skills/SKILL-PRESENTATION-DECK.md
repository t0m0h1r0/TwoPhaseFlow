# SKILL-PRESENTATION-DECK

id: SKILL-PRESENTATION-DECK
purpose: Create research-grounded deck-generation projects and decks through staged planning, slide-spec management, editable/programmatic generation, render review, and talk-track alignment.
trigger:
- PresentationWriter receives a slide deck, talk deck, or paper-to-presentation task
- Paper/RevisionBrief/EvidencePackage must become audience-facing slides
- User asks to create, export, improve, or review a PPTX/PDF/HTML/SVG slide pipeline
minimal_instruction: Build or update the deck-generation project before polishing the deck: derive the narrative spine, maintain `brief.md`/`slide_spec.yaml` when useful, fit the slide/time budget, give each slide one sourced message, generate visuals/data artifacts reproducibly, render-review exports, and align notes with the talk track.
full_ref: prompts/meta/kernel-ops.md §PRESENTATION-GEN-01
input_contract:
- paper/sections, docs/memo, docs/wiki, or experiment/ch*/results paths
- signed RevisionBrief or EvidencePackage when claims go beyond source summary
- audience, venue/language, and slide/time budget when known
- existing deck template, `brief.md`, `slide_spec.yaml`, `data/`, or `assets/` when available
output_contract:
- deck project/source under `paper/presentations/{deck_id}/`
- `brief.md` and `slide_spec.yaml` when no equivalent spec exists
- narrative spine: audience problem -> paper insight -> evidence -> implication
- slide source map, lead list, visual/data/export plan, message budget, rendered artifacts, and review notes
best_practices:
- start from audience knowledge; choose the shortest path to the contribution
- prefer the pipeline shape `brief.md -> slide_spec.yaml -> HTML/SVG/chart/table assets -> PPTX/PDF/preview`
- enforce slide/time budget; move derivations, caveats, and secondary details to notes/backup
- one claim per slide; use claim-style titles, not topic labels; lead is larger than labels/captions/notes
- visual hierarchy: lead -> visual -> labels -> source note
- keep titles, body text, simple tables, and source notes editable; use SVG/HTML/raster assets only for complex diagrams, charts, or conceptual art where editability loss is justified
- generate charts from source data; never invent numbers; mark missing data as TODO/placeholders
- use tables for decisions/comparisons, charts for numeric trends/comparisons, diagrams for structures/processes/relationships, and illustrations sparingly for covers/section breaks/concepts
- constrain slide density: max three body bullets, compact decision tables, readable axes/legends, and no decorative visual noise
- use SKILL-PRESENTATION-ILLUSTRATION only for conceptual or reverse-readback visual tasks
- prefer diagrams/charts/timelines/mechanisms/comparisons over dense bullets
- preserve uncertainty, assumptions, limits, and cited quantitative/novelty/benchmark claims
- parallelize by role/artifact boundary (story/spec, charts, diagrams, export pipeline, review), not by simultaneous edits to the same deck file
- audience check: what remains after 30 seconds, 5 minutes, and the ending?
review_criteria:
- narrative clarity, compression quality, audience recall, cognitive load, source fidelity, design coherence, export reproducibility, PPTX editability
forbidden_context:
- claims remembered from conversation but not present in artifacts
- unverified SOTA, novelty, benchmark, or numerical claims
- whole-slide rasterization as the default route for an editable deck
- images with material slide text embedded unless explicitly required
success_metric:
- each slide has lead, visual, source refs, one message, and a role in the spine
- `deck.pptx`, `deck.pdf`, and preview images exist when deck generation is requested
- render review has no unresolved MAJOR+ findings or records explicit residual risk
token_target: 300
