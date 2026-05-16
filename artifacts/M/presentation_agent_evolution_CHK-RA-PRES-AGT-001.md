# Presentation Agent Evolution Audit — CHK-RA-PRES-AGT-001

## Scope

User memo target: evolve the presentation-generation agent so it treats deck work as a reproducible production pipeline, not a one-shot slide-writing request.

Worktree: `.claude/worktrees/codex-ra-presentation-agent-evolution-20260516`
Branch: `codex/ra-presentation-agent-evolution-20260516`
Prompt source commit in `prompts/meta`: `a375209`

## External Source Check

The user memo cited current Codex practices. I checked official OpenAI developer docs as data, not authority:

- Codex best-practice prompt structure: Goal, Context, Constraints, Done when.
  Source: https://developers.openai.com/codex/learn/best-practices
- Codex Skills: task-specific instructions/resources/scripts, progressive disclosure, implicit and explicit activation.
  Source: https://developers.openai.com/codex/skills

These support the memo's shape: stable workflow knowledge belongs in a Skill/JIT capsule, while task-specific deck intent belongs in `brief.md`/`slide_spec.yaml`.

## Design Decision

Do not paste the memo into generated role prompts. The high-ROI behavior is promoted into:

- `prompts/meta/kernel-ops.md §PRESENTATION-GEN-01`: canonical operation contract.
- `prompts/meta/kernel-roles.md §PresentationWriter` and `§PaperReviewer`: role-level obligations.
- `prompts/meta/kernel-deploy.md`: JIT trigger and Skill manifest wording.
- `prompts/skills/SKILL-PRESENTATION-DECK.md`: procedural deck-production workflow loaded only for deck work.
- `prompts/agents-codex/PresentationWriter.md`: regenerated Codex prompt now names `brief.md`/`slide_spec.yaml` and deck-generation project setup.

Claude generated prompts were not manually patched because generated artifacts should come from the metaprompt source. They already point to `SKILL-PRESENTATION-DECK`, so the updated Skill body is active through JIT loading.

## Memo Coverage Audit

| Memo requirement | Implemented location | Verdict |
|---|---|---|
| Prefer a slide-generation project over direct slide asking | `PRESENTATION-GEN-01` production plan/rules; Skill minimal instruction | PASS |
| Use `brief.md -> slide_spec.yaml -> assets -> PPTX/PDF/preview` pipeline | `PRESENTATION-GEN-01`; Skill best practices | PASS |
| Keep PPTX editability while using SVG/HTML/raster for complex visuals | `PRESENTATION-GEN-01`; PresentationWriter constraints; Skill best practices | PASS |
| Manage `brief.md`, `slide_spec.yaml`, `data/`, `assets/`, `src/`, `outputs/` | `PRESENTATION-GEN-01` `deck_project`; Skill contracts | PASS |
| One message per slide and claim-style titles | `PRESENTATION-GEN-01`; Skill best practices | PASS |
| Charts from source data; no invented numbers | `PRESENTATION-GEN-01`; PresentationWriter constraints; Skill best practices | PASS |
| Tables as decision/comparison tools | Skill best practices | PASS |
| Diagrams/charts/timelines over dense bullets | Skill best practices | PASS |
| Concept art only when claim-mapped and reviewed | Existing `SKILL-PRESENTATION-ILLUSTRATION`; retained in Skill/operation | PASS |
| Review actual previews/PDF/PPTX, not source text only | `PRESENTATION-GEN-01`; Skill success metric | PASS |
| Review editability, chart labels, text density, whitespace | `PRESENTATION-GEN-01`; PaperReviewer constraints; Skill review criteria | PASS |
| Parallelize by role/artifact boundary, not simultaneous deck-file edits | `PRESENTATION-GEN-01`; Skill best practices | PASS |
| Use Skillization for repeated deck workflow | Skill purpose/trigger expanded | PASS |

## Prompt-Bloat / JIT Audit

Verdict: PASS.

- The detailed workflow lives in `SKILL-PRESENTATION-DECK.md`, not in every generated role prompt.
- Generated Codex `PresentationWriter.md` static prompt is 318 whitespace tokens in `token_telemetry_report.json`.
- Q3 report passed Q3-01..Q3-15, AP-13, and AP-17.
- The generated prompt names the new behavior without embedding the full memo.

Residual risk: `SKILL-PRESENTATION-DECK` token target increased from 220 to 300. This is justified because the Skill is loaded only for deck work and replaces a much longer repeated user prompt.

## Propagation Audit

Verdict: PASS.

- Source metaprompt changed and committed in submodule: `a375209`.
- Parent repo tracks the new submodule pointer.
- `scripts/deploy_codex_agents.py` was run and produced 25 Codex agent prompts plus reports under `artifacts/P/codex_overwrite_deploy_CHK-RA-PRES-AGT-001/`.
- `prompts/agents-codex/PresentationWriter.md` includes `brief.md`/`slide_spec.yaml` and "deck-generation project".
- `PaperReviewer` generated prompt did not change textually because the compact generator truncates the role constraint before the newly added review tail. This is acceptable because it already loads `SKILL-PRESENTATION-DECK`, and the authoritative source plus Skill contain the new review checks.

## Validation Commands

- `git diff --check` at parent repo: PASS.
- `git diff --check` in `prompts/meta`: PASS.
- `python3 -m py_compile scripts/deploy_codex_agents.py`: PASS.
- `python3 scripts/deploy_codex_agents.py`: PASS; generated 25 Codex agents.
- `find prompts/agents-codex -maxdepth 1 -name '*.md' | wc -l`: 25.
- Targeted scan for `deck-generation project`, `brief.md`, `slide_spec.yaml`, `PPTX editability`, `chart_axis_legibility`, `whole-slide rasterization`, `claim-style titles`, `never invent numbers`, `parallelize by role`, `HTML/SVG`, and `preview`: PASS.

## Final Verdict

The update is effective for the intended behavior change. It changes the canonical operation, role contract, JIT Skill, and Codex generated prompt while preserving token economy and avoiding a static prompt dump. No FATAL or MAJOR prompt-audit findings remain.

[SOLID-X] Prompt/docs/tooling/artifact only; no `src/twophase/`, experiment YAML/result data, physical parameter, CFL, damping, smoothing, tolerance, fallback, production algorithm, main merge, branch deletion, or worktree removal changed.
