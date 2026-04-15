# TwoPhaseFlow — Codex Instructions

## Context Rules
- No full file reads unless asked — use `head`/`tail`/`grep` with line ranges
- No whole-repo scans — `grep`/`find` targeted
- Logs → max 5 lines (`tail` only)
- Focus ONLY on error/question
- Long input → extract final error message only

## Output Rules
- No repetition; no full code unless asked
- File edits → targeted patch over full rewrites
- Plain relative file paths for references

## Session Start
1. `head -60 docs/02_ACTIVE_LEDGER.md` → Phase / Branch / open CHKs
2. Load ONLY if task demands:
   - Code changes → `docs/00_GLOBAL_RULES.md §C` + `docs/03_PROJECT_RULES.md`
   - Deps/interfaces → `docs/01_PROJECT_MAP.md`
   - Domain knowledge → `prompts/agents-claude/*.md` (reference)
3. No pre-loading unrequired files

## Coding Rules
- Full rules: `docs/00_GLOBAL_RULES.md §C` (C1-C4) + `docs/03_PROJECT_RULES.md §PR` (PR-1-PR-6)
- **SOLID audit** — report `[SOLID-X]`, fix before proceeding (C1)
- **Never delete tested code** — retain as legacy; register `docs/01_PROJECT_MAP.md §8` (C2)
- **Algorithm Fidelity (PR-5)** — paper-exact behavior mandatory; deviation = bug
- **A3 Traceability** — Equation → Discretization → Code chain mandatory
- **GPU/CuPy** — `backend.xp` for array ops; CPU bit-exact (PR-5). ch11 GPU-opted. ASM-122-A: split-reinit drift = Lyapunov chaos, not bug

## Directory Conventions
- Library: `src/twophase/` (`lib/` NOT used)
- Experiments: `experiment/ch{N}/`; results: `experiment/ch{N}/results/{name}/`
- Graphs: **PDF only** (`savefig('*.pdf')`)
- Experiments: `twophase.experiment` toolkit + `--plot-only`
- `results/` (top-level) → DEPRECATED
- Wiki: `docs/wiki/{theory,experiment,cross-domain,paper,code}/` (96+ entries, `docs/wiki/INDEX.md`)
- Memos: `docs/memo/`
- Agent prompts: `prompts/agents-claude/` (domain reference, not routing)

## Execution Workflow
**Remote-first. Local fallback only when remote unavailable.**

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

- Local env: `.venv/bin/python3` (or `source .venv/bin/activate`)
- No bare `python3 experiment/...` — bypasses remote
- `make run`/`make test` auto-detect remote; local fallback when SSH unreachable
- Code-only changes: `make push` then `make run` (rsync `--checksum`)
- Git worktrees for isolated work; remote dir shared
- **Network required** for `make run`/`make push`/`make pull`; `sandbox = "network-enabled"` in `.codex/config.toml`
