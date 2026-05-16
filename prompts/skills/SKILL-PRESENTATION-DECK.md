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
- paper/sections, docs/memo, docs/wiki, or experiment/ch*/results paths
- signed RevisionBrief or EvidencePackage when claims go beyond source summary
- audience, venue/language, and slide/time budget when known
- existing deck template, `brief.md`, `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml`, `review_plan.yaml`, `issue_register.yaml`, `convergence_dashboard.md`, `review_reports/`, `change_log.md`, `data/`, or `assets/` when available
output_contract:
- deck project/source under `paper/presentations/{deck_id}/`
- `brief.md`, `audience_profile.yaml`, `story_map.md`, `slide_spec.yaml`, `review_plan.yaml`, `issue_register.yaml`, `convergence_dashboard.md`, `review_reports/*.md`, `change_log.md`, and `review_report.md` when no equivalent artifacts exist
- narrative spine: audience current belief -> tension/problem -> take-home message -> evidence -> decision/action
- slide source map, role-in-story list, lead list, visual/data/export plan, issue-priority table, message budget, rendered artifacts, and review notes
best_practices:
- start from audience knowledge; choose the shortest path to the contribution
- prefer the pipeline shape `brief.md -> audience_profile.yaml -> story_map.md -> slide_spec.yaml -> review_plan.yaml -> deck exports -> role-specific review_reports -> issue_register.yaml -> focused repair -> validation -> convergence_dashboard.md -> diff/final acceptance -> change_log.md`
- define audience, decision/action, current belief, desired belief, constraints, and one take-home message before slide generation
- make primary audience concrete: role, decision authority, knowledge level, cares, likely objections, evidence needed, and language preference
- choose a story pattern intentionally: answer-first, current->problem->action->decision, question->finding->implication->action, future->gap->phased execution, or technical value->adoption
- enforce slide/time budget; move derivations, caveats, and secondary details to notes/backup
- one claim per slide; use claim-style titles, not topic labels; lead is larger than labels/captions/notes
- make the recommendation or decision ask visible by slide 2 for executive/decision decks unless the brief is exploratory
- record each slide's role_in_story, evidence_needed, and risk_if_removed; remove or merge slides with duplicate roles
- visual hierarchy: lead -> visual -> labels -> source note
- keep titles, body text, simple tables, and source notes editable; use SVG/HTML/raster assets only for complex diagrams, charts, or conceptual art where editability loss is justified
- generate charts from source data; never invent numbers; mark missing data as TODO/placeholders
- use tables for decisions/comparisons, charts for numeric trends/comparisons, diagrams for structures/processes/relationships, and illustrations sparingly for covers/section breaks/concepts
- constrain slide density: max three body bullets, compact decision tables, readable axes/legends, and no decorative visual noise
- use SKILL-PRESENTATION-ILLUSTRATION only for conceptual or reverse-readback visual tasks
- prefer diagrams/charts/timelines/mechanisms/comparisons over dense bullets
- preserve uncertainty, assumptions, limits, and cited quantitative/novelty/benchmark claims
- review in order: 1-minute story, slide structure, one-slide-one-message, visuals, evidence/data, accessibility/delivery
- execute role-specific reviews: primary audience, skeptic/objection, Q&A readiness, visual clarity, diff review, and final delivery rehearsal
- store each review as issue-shaped Markdown under `review_reports/`; each issue names issue_id, severity, target_audience, slide_id, problem, audience_impact, proposed_fix, and status
- classify all review findings as Must fix, Should fix, Could fix, or Do not fix using audience impact, decision impact, and confidence; do not accept every comment
- persist review findings in `issue_register.yaml`; use it as the SSoT for unresolved issues, status, fix policy, and remaining delta
- update `convergence_dashboard.md` each iteration with phase, High/Medium open counts, new High issues, reopened issues, change size, audience-readiness scores, remaining delta, and Stop/Continue/Human-review judgment
- treat repeated review as convergence: review, issue, triage, focused repair, validate, update remaining delta, then stop/continue/escalate
- after iteration 2, do not re-review from scratch unless a High issue reopens the story; check unresolved/reopened/new-critical issues and stop criteria
- reduce freedom by phase: Diverge finds issues, Structure fixes logic, Stabilize handles Must issues, Polish improves clarity, and Lock allows only fatal defects, factual/source-note fixes, layout bugs, typos, or speaker-note corrections
- apply Story Freeze before visual polish, Evidence Freeze before final polish, Visual Freeze before delivery rehearsal, and Final Lock before acceptance; reopening a frozen layer requires a High/Must-fix reason
- use focused repair: touch the smallest necessary slide/spec/code surface; prefer merge/delete/speaker-notes/backup over slide growth
- escalate to Human review when remaining delta does not shrink for two iterations, required data or politics are absent, audience interests conflict, the conclusion itself needs judgment, or comments become taste-only
- final acceptance review returns Pass / Conditional Pass / Fail; new improvement suggestions are forbidden unless they identify High severity or factual/export defects
- after every revision, update `change_log.md` with goal, changes, issues resolved, new issues, and residual risk
- compare previous/current versions before closing an iteration; reject revisions that fix one issue while harming audience clarity, slide count, or text density
- use Q&A review to decide whether missing evidence belongs in the main deck, speaker notes, or backup slides
- fix story gaps before visual polish; scores below 25/50 require story redesign before further deck generation
- parallelize by role/artifact boundary (story/spec, charts, diagrams, export pipeline, review), not by simultaneous edits to the same deck file
- audience check: what remains after 30 seconds, 5 minutes, and the ending?
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
