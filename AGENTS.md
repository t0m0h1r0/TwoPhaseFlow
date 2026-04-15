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
**Remote-first policy: experiments MUST run on the remote GPU server. Local commands are fallback-only (remote explicitly unavailable).**

| Task | Command | Priority |
|---|---|---|
| Push + Run + Pull (code changed) | `make cycle EXP=<path>` | **preferred** |
| Run single experiment | `make run EXP=<path>` | default |
| Run all chapter experiments | `make run-all CH=ch11` | default |
| Tests | `make test` | default |
| Re-plot from cached npz | `make plot EXP=<path>` | default |
| SSH into remote | `make ssh` | — |
| Run locally (fallback) | `make run-local EXP=<path>` | fallback only |
| Tests locally (fallback) | `make test-local` | fallback only |

- Local Python environment: `.venv/` at project root — use `.venv/bin/python3` (or `source .venv/bin/activate`) for any local execution
- Do NOT use bare `python3 experiment/...` directly — bypasses remote and silently runs locally
- `make run` / `make test` auto-detect remote; fall back to local only when SSH is unreachable
- After standalone code changes: `make push` then `make run` (rsync uses `--checksum`)
- Use git worktrees for isolated feature/fix work; remote dir is shared across worktrees
- **Network required:** `make run` / `make push` / `make pull` all SSH to a remote GPU server.
  Codex must run with `sandbox = "network-enabled"` in `.codex/config.toml`.
