# 🚨 STRICT CONTEXT CONTROL

## NEVER DO
- Do NOT read entire files unless explicitly requested
- Do NOT scan the whole repository
- Do NOT include full logs or outputs
- Do NOT include previous conversation history unless required

## ALWAYS DO
- Only use explicitly mentioned files (e.g., @file.py)
- If logs are long → summarize to max 5 lines (tail only)
- Focus ONLY on the error or question
- Prefer minimal context over completeness

## OUTPUT RULES
- Be concise
- No repetition
- No full code unless requested
- **File updates: `diff` format preferred — never re-output entire files**
- Reasoning: max 3 bullet points

## HARD LIMIT
If input is too long:
→ IGNORE most of it
→ Extract only the final error message

## EXECUTION STEP 0 (session start)
1. Read `docs/02_ACTIVE_LEDGER.md` → identify current Phase / Branch / open CHKs
2. Load additional files ONLY if the current task demands it:
   - Code changes → `docs/00_GLOBAL_RULES.md §C` + `docs/03_PROJECT_RULES.md`
   - Dependency/interface resolution → `docs/01_PROJECT_MAP.md`
   - Agent routing / full initialization → `prompts/agents/ResearchArchitect.md` + all above
3. Do NOT pre-load any file not required by the current task

## CODING RULES (enforced every session)
- Full rules in `docs/00_GLOBAL_RULES.md §C` (C1–C4) and `docs/03_PROJECT_RULES.md §PR` (PR-1–PR-6)
- **SOLID audit** — report violations as `[SOLID-X]` and fix before proceeding (C1)
- **Never delete tested code** — retain as legacy class; register in `docs/01_PROJECT_MAP.md §8` (C2)
- **Algorithm Fidelity** — fixes MUST restore paper-exact behavior; deviation = bug (PR-5)
- **A3 Traceability** — Equation → Discretization → Code chain is mandatory

## DIRECTORY CONVENTIONS (enforced every session)
- Full conventions in `prompts/agents/_base.yaml §directory_conventions`
- Key rules:
  - Library code → `src/twophase/` (`lib/` is NOT used)
  - Experiment scripts → `experiment/ch{N}/`; results colocated in `experiment/ch{N}/results/{name}/`
  - Graphs → **PDF only** (`savefig('*.pdf')`)
  - Experiment scripts MUST use `twophase.experiment` toolkit and support `--plot-only`
  - `results/` (top-level) → DEPRECATED
  - Meta-prompts → `prompts/meta/`; Agent prompts → `prompts/agents/`
  - **Experiment execution default = remote server `python`**: use `make run EXP=<path>` (remote) or `make run-local EXP=<path>` (local fallback). Direct `python3 experiment/…` invocation is discouraged — it silently runs locally.

## AGENT PROMPT SYSTEM
- Agent prompts are YAML-format files in `prompts/agents/*.md`.
- All agents inherit `prompts/agents/_base.yaml` (shared axioms, primitives, rules, procedure pre/post).
- Agent files contain ONLY overrides and domain-specific content.
- To understand an agent: read `_base.yaml` FIRST, then the agent file.
