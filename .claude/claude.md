# 🚨 STRICT CONTEXT CONTROL

## NEVER DO
- Do NOT read entire files unless explicitly requested
- Do NOT scan the whole repository
- Do NOT include full logs or outputs
- Do NOT include previous conversation history unless required

## ALWAYS DO
- Only use explicitly mentioned files (e.g., @file.py)
- If logs are long → summarize to max 20 lines
- Focus ONLY on the error or question
- Prefer minimal context over completeness

## OUTPUT RULES
- Be concise
- No repetition
- No full code unless requested

## HARD LIMIT
If input is too long:
→ IGNORE most of it
→ Extract only the final error message

## FIRST TASK
- prompts/agents/ResearchArchitect.md
- docs/02_ACTIVE_LEDGER.md (phase, branch, last decision, open CHKs)
- docs/01_PROJECT_MAP.md (module map, interface contracts, numerical reference)
- docs/00_GLOBAL_RULES.md (universal axioms A1–A10, universal code rules C1–C4)
- docs/03_PROJECT_RULES.md (project-specific rules PR-1–PR-6: CCD primacy, solver policy, MMS, toolkit, fidelity, PPE)

## CODING RULES (enforced every session)
- **Universal rules** → docs/00_GLOBAL_RULES.md §C (C1–C4: SOLID, preserve-tested, builder, quality)
- **Project rules** → docs/03_PROJECT_RULES.md §PR (PR-1–PR-6: CCD primacy, solver policy, MMS, toolkit, fidelity, PPE)
- **SOLID audit** — report violations in `[SOLID-X]` format and fix before proceeding (C1)
- **Never delete tested code** — retain as legacy class; register in docs/01_PROJECT_MAP.md §8 (C2)
- **Algorithm Fidelity** — fixes MUST restore paper-exact behavior; deviation = bug (PR-5)
- **A3 Traceability** — Equation → Discretization → Code chain is mandatory

## DIRECTORY CONVENTIONS (enforced every session)
- **Library code** → `src/` (`src/twophase/`). `lib/` is NOT used.
- **Simulation configs** → `src/configs/` (YAML format)
- **Experiment scripts** → `experiment/ch{N}/` (chapter-based: ch10, ch11, ch12)
- **Experiment results & graphs** → `experiment/ch{N}/results/{experiment_name}/` (colocated)
- **Graphs** → **PDF format ONLY** (publication-quality vector; `savefig('*.pdf')`)
- **Experiment scripts MUST** save result data (NPZ/CSV/JSON) and support `--plot-only` re-plotting
- **Experiment scripts MUST** use `twophase.experiment` toolkit (`src/twophase/experiment/`):
  - `apply_style()` for unified rcParams (call once at top)
  - `experiment_dir(__file__)` for output directory
  - `experiment_argparser()` for `--plot-only` argparse
  - `save_results()` / `load_results()` for NPZ I/O
  - `save_figure()` for PDF output
  - `field_panel()`, `convergence_loglog()`, `time_history()`, `summary_text()` for plotting
  - Direct matplotlib calls are OK for custom layouts, but style/IO/save must go through the toolkit
- **`results/` (top-level)** → DEPRECATED. Migrate to `experiment/ch{N}/results/`.
- **Meta-prompts** → `prompts/meta/`. Top-level `meta/` is NOT used.
- **Agent prompts** → `prompts/agents/`
- **Short papers / memos / theory derivations** → `docs/memo/`, Markdown/TeX, Japanese

## AGENT PROMPT SYSTEM
- Agent prompts are YAML-format files in `prompts/agents/*.md`.
- All agents inherit `prompts/agents/_base.yaml` (shared axioms, primitives, rules, procedure pre/post).
- Agent files contain ONLY overrides and domain-specific content.
- To understand an agent: read `_base.yaml` FIRST, then the agent file.