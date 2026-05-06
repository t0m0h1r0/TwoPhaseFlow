# CHK-RA-PAPER-TEX-ZERO-001 — Paper TeX Warning Zeroization

## Scope

- Worktree: `.claude/worktrees/codex-ra-paper-tex-zero-20260506`
- Branch: `codex/ra-paper-tex-zero-20260506`
- Lock: `docs/locks/ra-paper-tex-zero-20260506.lock.json`
- Route: ResearchArchitect → PaperCompiler + KnowledgeArchitect

## Findings

Initial `make -B -C paper` succeeded, but the final log retained one layout
warning:

```text
LaTeX Warning: Text page 148 contains only floats.
```

The source was a local U7 float cluster in
`paper/sections/12u7_bf_static_droplet.tex`: two tables and two figures all
used `[!ht]`, leaving LaTeX no page-float option.

The KL-12 pre-scan also found caption math without `\texorpdfstring` fallbacks.
Those were build-hygiene violations even though they were not emitted as final
LaTeX warnings.

## Fixes

- Changed U7 float specifiers from `[!ht]` to `[!htbp]`.
- Wrapped caption math in `\texorpdfstring{...}{...}` across affected captions.
- Added `docs/wiki/paper/WIKI-P-017.md` as a reusable build-hygiene card and
  registered it in `docs/wiki/INDEX.md`.

## Validation

- `rg -n '\\section|\\subsection|\\caption' paper/sections/*.tex | rg '\\$' | rg -v 'texorpdfstring'`: PASS, zero matches.
- `make -B -C paper`: PASS, `paper/main.pdf`, 247 pages.
- Build-log scan for LaTeX/package/class warnings, overfull/underfull boxes,
  float-only pages, fatal errors, undefined controls, undefined refs/cites,
  multiply-defined labels, and rerun warnings: PASS, zero matches.
- `git diff --check`: PASS.

## Commits

- `54cc87df` start paper tex zero ResearchArchitect task
- `f276b977` zero paper tex warnings

## SOLID-X

Paper/wiki/bookkeeping only. No `src/twophase/`, experiment scripts, configs,
or cached result artifacts were changed. No tested implementation was deleted.
No FD/WENO/PPE fallback or alternate pressure scheme was introduced.
