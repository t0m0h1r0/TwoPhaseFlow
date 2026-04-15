---
id: WIKI-M-010
title: "Caveman-Compress: Token Reduction for AI Instruction Files"
status: ACTIVE
created: 2026-04-16
depends_on: []
---

# Caveman-Compress: Token Reduction for AI Instruction Files

Source: [github.com/JuliusBrussee/caveman](https://github.com/JuliusBrussee/caveman)

---

## Section 1 — Technique Overview

**Caveman-Compress** rewrites memory/instruction files into terse prose,
stripping filler while preserving all technical content. Targets: articles
(the/a/an), hedge phrases, redundant sentences that restate tables.

### Intensity Levels

| Level | Description | Typical Savings |
|-------|-------------|-----------------|
| Lite | Remove filler, maintain grammar | ~30% |
| Full | Drop articles, use fragments | ~46% |
| Ultra | Telegraphic, abbreviations | ~60%+ |

### Preservation Rules (mandatory)

- Code blocks, commands, file paths — verbatim
- IDs (CHK/ASM/KL/PR/A#) — verbatim
- Table structure — intact
- Dates, URLs — verbatim
- `**bold**` emphasis on constraints — keep

---

## Section 2 — Application to This Project

Applied 2026-04-16 at "Lite-to-Full" level to 4 AI instruction files.

### Results

| File | Before (words) | After | Reduction |
|------|----------------|-------|-----------|
| `.claude/CLAUDE.md` | 534 | 406 | -24% |
| `AGENTS.md` | 548 | 412 | -25% |
| `docs/00_GLOBAL_RULES.md` | 566 | 550 | -3% |
| `docs/03_PROJECT_RULES.md` | 547 | 422 | -23% |
| **Total** | **2195** | **1790** | **-18%** |

### Skipped (and why)

- `docs/02_ACTIVE_LEDGER.md` — live/append-only state; structure matters more than prose
- `docs/01_PROJECT_MAP.md` — 327 lines, data-heavy; compress separately if needed
- `prompts/agents-claude/*.md` — domain reference, not loaded every session

---

## Section 3 — Reuse Guidelines

### When to Apply

- New instruction files added to `.claude/` or `docs/`
- Existing instruction file grows beyond ~100 lines
- Session start latency noticeably increases

### How to Apply

1. Identify prose bullets/paragraphs (not tables, not code)
2. Strip: articles, "Do NOT ... unless explicitly requested" -> "No ... unless asked"
3. Merge: multi-sentence explanations -> terse imperative fragments
4. Verify: diff every ID, command, table row, file path present after compression

### Anti-Patterns

- Do NOT compress live-state documents (ACTIVE_LEDGER) — append-only contract
- Do NOT compress code blocks or command strings
- Do NOT remove `**bold**` constraint markers
- Do NOT apply Ultra level to instruction files — too terse loses nuance for LLMs
