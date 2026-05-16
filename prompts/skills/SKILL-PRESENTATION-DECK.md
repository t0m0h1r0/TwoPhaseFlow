# SKILL-PRESENTATION-DECK

id: SKILL-PRESENTATION-DECK
purpose: Create source-grounded deck projects/decks via PRESENTATION-GEN-01: audience/story/spec, editable generation, role review, convergence, and final acceptance.
trigger:
- PresentationWriter receives a deck/talk/paper-to-slides task
- paper/evidence must become audience-facing slides
- user asks to create/export/review PPTX/PDF/HTML/SVG slides
- user asks for story, audience/skeptic/Q&A/diff review, convergence, or final acceptance
minimal_instruction: Use PRESENTATION-GEN-01. Before polishing, define audience decision/beliefs/action, story_map, and slide_spec; maintain review_plan, review_reports, issue_register, convergence_dashboard, and change_log; regenerate artifacts; run delta/final review.
full_ref: prompts/meta/kernel-ops.md §PRESENTATION-GEN-01
input_contract:
- source/evidence paths plus signed brief/evidence when claims exceed summary
- audience, venue/language, slide/time budget, template when known
- existing deck project artifacts or data/assets when available
output_contract:
- deck source plus PPTX/PDF/previews when generation is requested
- brief/audience/story/spec/review/issue/dashboard/changelog artifacts when full workflow is requested
- source map, role-in-story, visual/export plan, prioritized issues, and review notes
best_practices:
- Keep the skill as the presentation adapter; load full_ref for detailed rules.
- Pipeline: brief -> audience_profile -> story_map -> slide_spec -> review_plan -> exports -> reviews -> issue register -> focused repair -> dashboard -> final acceptance.
- One supported claim per slide; executive decks show recommendation/decision ask by slide 2 unless exploratory.
- Use editable text/tables/notes; use SVG/HTML/raster only where quality justifies editability loss.
- Choose visuals by message; never invent numbers; mark unknown data TODO.
- After iteration 2, use delta review, freeze gates, and stop criteria instead of zero-base review.
- Avoid slide growth unless needed for a Must-fix decision issue; escalate when remaining delta stops shrinking.
review_criteria:
- audience/decision clarity, objection coverage, story logic, slide-role uniqueness, source fidelity, visual clarity, export reproducibility, editability, delivery readiness
forbidden_context:
- unsupported remembered or unverified claims
- whole-slide rasterization as default editable-deck route
- material text embedded in images unless required
- final deck before story_map or equivalent exists
- visual-only review that skips story/evidence
- unprioritized review dumping or accepting every comment
- slide growth without audience decision need
- zero-base re-review after stabilization without High/Must-fix reason
- endless improvement without stop criteria or Human-review escalation
success_metric:
- one supported message and story role per slide
- full workflow artifacts exist when requested; deck exports/previews exist when generation is requested
- no unresolved High/Must-fix issue or explicit Do-not-fix rationale
- dashboard shows stable convergence or Stop/Conditional/Human-review rationale
token_target: 460
