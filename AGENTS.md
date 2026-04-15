# TwoPhaseFlow — Codex Instructions

## Context Rules
- Do NOT read entire files unless explicitly requested — use `head`/`tail`/`grep` with line ranges
- Do NOT scan the whole repository — use `grep`/`find` for targeted search
- Logs → summarize to max 5 lines (`tail` only)
- Focus ONLY on the error or question; prefer minimal context over completeness
- If input is too long → extract only the final error message

## Output Rules
- Be concise — no repetition, no full code unless requested
- File edits → prefer targeted patch over full rewrites
- Use plain relative file paths for references

## Session Start
1. `head -60 docs/02_ACTIVE_LEDGER.md` → current Phase / Branch / open CHKs
2. Load additional files ONLY if the task demands it:
   - Code changes → `docs/00_GLOBAL_RULES.md §C` + `docs/03_PROJECT_RULES.md`
   - Dependency/interface resolution → `docs/01_PROJECT_MAP.md`
   - Domain knowledge → relevant `prompts/agents-claude/*.md` as reference
3. Do NOT pre-load files not required by the current task

## Coding Rules
- Full rules: `docs/00_GLOBAL_RULES.md §C` (C1-C4) + `docs/03_PROJECT_RULES.md §PR` (PR-1-PR-6)
- **SOLID audit** — report violations as `[SOLID-X]` and fix before proceeding (C1)
- **Never delete tested code** — retain as legacy; register in `docs/01_PROJECT_MAP.md §8` (C2)
- **Algorithm Fidelity (PR-5)** — fixes MUST restore paper-exact behavior; deviation = bug
- **A3 Traceability** — Equation → Discretization → Code chain is mandatory
- **GPU/CuPy backend** — library code uses `backend.xp` for array ops; CPU path must remain bit-exact (PR-5). All ch11 experiments are GPU-opted. ASM-122-A: split-reinit pointwise drift on GPU is FUNDAMENTAL (Lyapunov chaos), not a bug

## Directory Conventions
- Library code → `src/twophase/` (`lib/` is NOT used)
- Experiment scripts → `experiment/ch{N}/`; results → `experiment/ch{N}/results/{name}/`
- Graphs → **PDF only** (`savefig('*.pdf')`)
- Experiments MUST use `twophase.experiment` toolkit and support `--plot-only`
- `results/` (top-level) → DEPRECATED
- Wiki → `docs/wiki/{theory,experiment,cross-domain,paper,code}/` (96+ entries, INDEX at `docs/wiki/INDEX.md`)
- Memos/derivations → `docs/memo/`
- Agent prompts → `prompts/agents-claude/` (read as domain reference, not routing)

## Execution Workflow
| Task | Command |
|---|---|
| Run experiment (remote GPU) | `make run EXP=<path>` |
| Run experiment (local CPU) | `make run-local EXP=<path>` |
| Push + Run + Pull | `make cycle EXP=<path>` |
| Run all chapter experiments | `make run-all CH=ch11` |
| Re-plot from cached npz | `make plot EXP=<path>` |
| Tests (remote GPU) | `make test` |
| Tests (local CPU) | `make test-local` |
| SSH into remote | `make ssh` |

- Direct `python3 experiment/...` is discouraged — it silently runs locally
- After code changes, `make push` before `make run` (remote uses rsync with `--checksum`)
- Use git worktrees for isolated feature/fix work; remote dir is shared across worktrees
- **Network required:** `make run` / `make push` / `make pull` all SSH to a remote GPU server.
  Codex must run with `sandbox = "network-enabled"` in `.codex/config.toml`.
