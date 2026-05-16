# SKILL-PRESENTATION-DECK

id: SKILL-PRESENTATION-DECK
purpose: Create research-grounded deck-generation projects and decks through the ARTIFACT-CONVERGENCE presentation adapter: audience-profile definition, story-map design, slide-spec management, editable/programmatic generation, role-specific iterative review, issue-register convergence control, diff review, and talk-track alignment.
trigger:
- PresentationWriter receives a slide deck, talk deck, or paper-to-presentation task
- Paper/RevisionBrief/EvidencePackage must become audience-facing slides
- User asks to create, export, improve, or review a PPTX/PDF/HTML/SVG slide pipeline
- User asks for story structure, slide outline, executive deck logic, or review_report.md
- User asks for audience-role review, skeptic review, Q&A review, diff review, or iterative deck revision
- User asks for repeated review, convergence, stop criteria, issue register, final acceptance, or avoiding endless deck revision
minimal_instruction: Build or update the story and deck-generation project before polishing the deck, using ARTIFACT-CONVERGENCE-01 through the presentation adapter: define `audience_profile.yaml`, audience decision/current belief/desired belief/action, create `story_map.md` and a take-home message, maintain `slide_spec.yaml`, execute `review_plan.yaml`, record role-specific `review_reports/*.md`, maintain `issue_register.yaml` and `convergence_dashboard.md`, prioritize issues, apply focused repair, update `change_log.md`, regenerate deck artifacts as needed, run diff/final-acceptance review, and align notes with the talk track.
full_ref: prompts/meta/kernel-ops.md §PRESENTATION-GEN-01
input_contract:
- paper sections, docs/memo, docs/wiki, project evidence/result paths, or other source paths
- signed RevisionBrief or EvidencePackage when claims go beyond source summary
- audience, venue/language, and slide/time budget when known
- existing deck template, `brief.md`, `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml`, `review_plan.yaml`, `issue_register.yaml`, `convergence_dashboard.md`, `review_reports/`, `change_log.md`, `data/`, or `assets/` when available
output_contract:
- deck project/source under `paper/presentations/{deck_id}/`
- `brief.md`, `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml`, `review_plan.yaml`, `issue_register.yaml`, `convergence_dashboard.md`, `review_reports/*.md`, `change_log.md`, and `review_report.md` when no equivalent artifacts exist
- narrative spine: audience current belief -> tension/problem -> take-home message -> evidence -> decision/action
- slide source map, role-in-story list, lead list, visual/data/export plan, issue-priority table, message budget, rendered artifacts, and review notes
best_practices:
- Treat the deck workflow as the presentation adapter of ARTIFACT-CONVERGENCE-01 while keeping deck artifacts explicit.
- Prefer the pipeline brief.md -> audience_profile.yaml -> story_map.md -> slide_spec.yaml -> review_plan.yaml -> deck exports -> review_reports -> issue_register.yaml -> focused repair -> validation -> convergence_dashboard.md -> diff/final acceptance -> change_log.md.
- Define audience, decision/action, current belief, desired belief, constraints, and one take-home message before slide generation.
- Use one supported claim per slide with claim-style titles; for executive decision decks, make the recommendation or decision ask visible by slide 2 unless exploratory.
- Keep claims source-grounded; generate charts from source data; mark unknown numbers as TODO/placeholders rather than inventing values.
- Choose visuals by message: tables for decisions/comparisons, charts for numeric evidence, diagrams for structures/processes, illustrations sparingly for covers or concepts.
- Keep titles, body text, simple tables, and source notes editable; use SVG/HTML/raster assets only where they materially improve quality.
- Review in order: story, slide structure, one-slide-one-message, visual clarity, evidence/data integrity, accessibility/delivery.
- Run role-specific reviews and store issue-shaped findings under review_reports/ with severity, audience impact, proposed fix, and status.
- Classify findings as Must/Should/Could/Do-not-fix; update issue_register.yaml, convergence_dashboard.md, and change_log.md after each revision.
- After iteration 2, use delta review and stop criteria instead of zero-base review; apply Story/Evidence/Visual/Final freezes.
- Use focused repair; avoid slide growth unless required by a Must-fix decision issue; escalate to Human review when remaining delta does not shrink or missing context/politics decides the answer.
- Parallelize by role or artifact boundary, not by simultaneous edits to the same deck file.
review_criteria:
- audience/decision clarity, belief-change plausibility, objection coverage, take-home message strength, story tension and logic, slide-role uniqueness, issue prioritization, compression quality, audience recall, cognitive load, source fidelity, design coherence, export reproducibility, PPTX editability, accessibility/delivery readiness
forbidden_context:
- claims remembered from conversation but not present in artifacts
- unverified SOTA, novelty, benchmark, or numerical claims
- whole-slide rasterization as the default route for an editable deck
- images with material slide text embedded unless explicitly required
- final-deck generation before story_map.md or equivalent story map exists
- review that skips story and evidence checks because visuals look polished
- unprioritized review dumping where all comments are treated as equally actionable
- slide growth that is not justified by audience decision need
- zero-base re-review after the stabilization point without a High/Must-fix reason
- endless improvement loops without stop criteria, remaining-delta tracking, or Human-review escalation
- adding new slides during Polish/Lock unless required to close a Must-fix decision issue
success_metric:
- each slide has lead, visual, source refs, one message, and a role in the spine
- `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml`, `review_plan.yaml`, `issue_register.yaml`, `convergence_dashboard.md`, `review_reports/*.md`, `change_log.md`, and `review_report.md` exist when a full deck workflow is requested
- `deck.pptx`, `deck.pdf`, and preview images exist when deck generation is requested
- render review has no unresolved MAJOR+ findings or records explicit residual risk
- review_report.md includes total score out of 50, top issues, slide-level findings, data/evidence findings, delivery risks, and action items
- no High/Must-fix issue remains unaddressed or explicitly justified as Do-not-fix
- convergence_dashboard.md shows zero High issues, no new High issues across required stable iterations, small latest change set, and Stop/Conditional Pass/Human-review rationale
token_target: 460
