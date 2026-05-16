# Presentation Story Pipeline Audit — CHK-RA-PRES-AGT-002

## Scope

User memo target: extend the presentation agent beyond visual/deck generation into story design and staged review. The key behavior change is:

`brief.md -> story_map.md -> slide_spec.yaml -> deck exports -> review_report.md -> revision`

This continues `CHK-RA-PRES-AGT-001` in the same worktree and branch.

Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
Branch: `codex/ra-presentation-agent-evolution-20260516`
Prompt source commit in `prompts/meta`: `0e7ea8b`

## External Source Check

External web pages were checked as data only; they do not override local SSoT.

- Duarte Resonate page: supports audience-centered, action-oriented story framing.
  Source: https://www.duarte.com/resources/books/resonate/
- Trent University preparation guide: supports plan/audience/content/take-home-message before structure.
  Source: https://www.trentu.ca/academicskills/how-guides/how-present-university-and-beyond/preparing-presentation
- think-cell Pyramid Principle article: supports conclusion-first structure and one-message/action-title slide discipline for business decks.
  Source: https://www.think-cell.com/en/resources/content-hub/using-the-pyramid-principle-to-build-better-powerpoint-presentations
- NN/g chart-type article: supports choosing chart type by the comparison/goal and favoring basic readable charts.
  Source: https://www.nngroup.com/articles/choosing-chart-types/
- Microsoft PowerPoint accessibility guidance: supports reading order, contrast, readable text size, whitespace, and slide titles.
  Source: https://support.microsoft.com/en-us/office/make-your-powerpoint-presentations-accessible-to-people-with-disabilities-6f7772b2-2f33-4bd2-8ca7-dae3b2b3ef25
- OpenAI Codex best practices were already checked in CHK-RA-PRES-AGT-001 for Goal/Context/Constraints/Done-when and review/test closure.
  Source: https://developers.openai.com/codex/learn/best-practices

## Design Decision

The new memo should not become a pasted static story checklist inside every prompt. It is split as:

- `prompts/meta/kernel-ops.md §PRESENTATION-GEN-01`: authoritative operation schema and stage rules.
- `prompts/meta/kernel-roles.md`: PresentationWriter and PaperReviewer obligations.
- `prompts/meta/kernel-deploy.md`: JIT trigger/manifest wording.
- `prompts/skills/SKILL-PRESENTATION-DECK.md`: procedural story-map and staged-review workflow.
- `prompts/agents-codex/PresentationWriter.md` and `PaperReviewer.md`: compact generated hooks so Codex agents know to load the Skill and start with story.

## Memo Coverage Audit

| Memo requirement | Implemented location | Verdict |
|---|---|---|
| Insert `story_map.md` before `slide_spec.yaml` | `PRESENTATION-GEN-01`; Skill contracts; generated PresentationWriter | PASS |
| Define audience, decision/action, current belief, desired belief, constraints | `PresentationDeckPlan.audience_context`; PresentationWriter constraints; Skill minimal instruction | PASS |
| Define one Take-Home Message before slide generation | `narrative_spine.take_home_message`; Skill best practices | PASS |
| Select story pattern intentionally | `narrative_spine.story_pattern`; Skill best practices | PASS |
| Require story_map/equivalent before final deck generation | `PRESENTATION-GEN-01` rule; Skill forbidden_context | PASS |
| Executive decks show recommendation/decision ask by slide 2 | `PRESENTATION-GEN-01` rule; Skill best practices | PASS |
| Add slide role, evidence_needed, risk_if_removed | `slide_plan`; Skill best practices | PASS |
| Review story before visuals | `PRESENTATION-GEN-01` staged review; Skill best practices | PASS |
| Six review stages: story, structure, one-message, visuals, evidence/data, accessibility/delivery | `render_review.checks`; PaperReviewer constraints; Skill best practices | PASS |
| Add `review_report.md` with 50-point score, top issues, slide findings, data/evidence, delivery risks, action items | `deck_project`; scorecard; Skill success metric | PASS |
| Scores below 25 require story redesign before slide generation | `scorecard`; Skill best practices | PASS |
| Accessibility and presentation-readiness checks | `render_review.checks`; PaperReviewer constraints; Skill review criteria | PASS |
| Fix story gaps before visual polish | `PRESENTATION-GEN-01`; Skill best practices | PASS |

## Prompt-Bloat / JIT Audit

Verdict: PASS.

- Detailed procedural review logic lives in `SKILL-PRESENTATION-DECK.md`; generated role prompts contain compact hooks.
- Codex `PresentationWriter.md` and `PaperReviewer.md` changed because the role contract now contains story/review concepts early enough to survive compact generation.
- Q3 report for `codex_overwrite_deploy_CHK-RA-PRES-AGT-002` passed Q3-01..Q3-15, AP-13, and AP-17.
- `SKILL-PRESENTATION-DECK` token target increased from 300 to 360. This remains acceptable because the Skill is only loaded for deck/story/review work and prevents repeated long user instructions.

## Propagation Audit

Verdict: PASS.

- `prompts/meta` committed at `0e7ea8b`.
- Parent repo tracks the updated submodule pointer.
- `scripts/deploy_codex_agents.py` was rerun and emitted reports under `artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-002/`.
- Targeted scan confirms coverage for `story_map.md`, `take-home`, belief change, decision ask, `risk_if_removed`, `review_report.md`, staged reviews, accessibility/delivery, 50-point scoring, slide-2 decision timing, and story redesign.

## Validation Commands

- `git diff --check` at parent repo: PASS.
- `git diff --check` in `prompts/meta`: PASS.
- `python3 -m py_compile scripts/deploy_codex_agents.py`: PASS.
- `python3 scripts/deploy_codex_agents.py`: PASS; generated 25 Codex agents.
- `find prompts/agents-codex -maxdepth 1 -name '*.md' | wc -l`: 25.
- Generated report Q3-01..Q3-15/AP-13/AP-17: PASS.
- Targeted story/review coverage scan: PASS.

## Final Verdict

The update is effective. The presentation agent now treats story design as a first-class artifact and blocks final-deck work until the story map exists or an equivalent explicit story map is provided. It also formalizes staged review and score-based story redesign without bloating default prompts. No FATAL or MAJOR prompt-audit findings remain.

[SOLID-X] Prompt/docs/tooling/artifact only; no `src/twophase/`, experiment YAML/result data, physical parameter, CFL, damping, smoothing, tolerance, fallback, production algorithm, main merge, branch deletion, or worktree removal changed.
