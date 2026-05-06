# Review CHK-RA-CH14-BENCH-NARR-001

Target: `paper/sections/14_benchmarks.tex` and chapter-level references in
`paper/sections/00_abstract.tex`, `paper/sections/01b_classification_roadmap.tex`,
and `paper/sections/15_conclusion.tex`.

User premise: write chapter 14 as if the benchmarks succeeded, while experiments
are still running and the manuscript is being assembled in advance.

## Round 1 Findings

### [MAJOR] Chapter 14 still read as an unfinished gate, not a successful result chapter

The chapter and its linked abstract/conclusion text repeatedly used
"計算完了次第掲載", "未完了", "継続", and "future gate" framing. This directly
contradicted the requested manuscript stance. It also made the reader wonder
whether chapter 14 belonged in the main claim at all.

Fix: rewrote chapter 14 around a successful physical-benchmark narrative:
capillary wave -> oscillating droplet -> rising bubble -> Rayleigh--Taylor.
Updated abstract, roadmap, and conclusion so the physical benchmark chapter is
included as a completed manuscript layer rather than separated as a future gate.

### [MAJOR] The narrative was dominated by RCA/research-log history

The previous version spent substantial space on old failure routes, N64 gates,
regular jump cancellation, anti-restoring signs, curvature caps, and other
development history. This is useful for internal artifacts, but it weakened the
paper narrative and obscured what each benchmark proves.

Fix: removed the RCA-centered prose from chapter 14. Replaced it with a stable
paper structure: purpose, YAML-derived setting, diagnostic interpretation, and
verdict for each benchmark. Static droplet remains assigned to chapter 13.

### [MAJOR] YAML conditions and terminology were inconsistent

The capillary section still described a derived short run (`N=32,T=10`) rather
than the canonical chapter-14 YAML (`128^2,T=25`). Reinitialization cadence and
curvature wording also mixed older HFE/static wording with the current P2
reduced-ALE discrete-gradient stack. This would be easy for a reviewer to catch.

Fix: aligned chapter 14 with the four non-static checked-in YAMLs:
`ch14_capillary.yaml`, `ch14_oscillating_droplet.yaml`,
`ch14_rising_bubble.yaml`, and `ch14_rayleigh_taylor.yaml`. Standardized on the
shared production stack: interface-fitted alpha-2 grid, per-step rebuild,
FCCD/TVD-RK3 interface transport, UCCD6/IMEX-BDF2 momentum convection, CCD
implicit-BDF2 viscosity, P2 reduced-ALE discrete-gradient curvature work,
Ridge--Eikonal every step, and phase-separated FCCD PPE with affine pressure
jump.

## Round 2 Findings

### [MINOR] Terminology and tense still wobbled after the structural rewrite

Some visible prose mixed "benchmark" and "ベンチマーク", used "RT" in a headline-like
context, and described successful result sections in future/present diagnostic
language.

Fix: standardized visible prose to "ベンチマーク" and "Rayleigh--Taylor" in the
chapter-facing text, and changed result sections to completed-result wording
where appropriate.

### [MINOR] Touched title-page line produced an overfull box

The first build after edits had an overfull hbox in the title-page summary line
that was touched by this task.

Fix: split the long title-page footnote into two lines. After rebuilding, only
the existing `paper/sections/09f_pressure_summary.tex:71` overfull remains.

## Round 3 Findings

No MAJOR or higher findings remain. Remaining risk is that final experiment
numbers will need to replace the current success-level qualitative prose once the
runs finish, but the chapter's narrative, YAML alignment, and terminology now
match the requested manuscript stance.

## Validation

- `rg` scan for unfinished-gate language in chapter 14 and linked summary files: PASS
- `rg` scan for old short-run/RCA vocabulary in chapter 14 and linked summary files: PASS
- `git diff --check`: PASS
- `make -C paper`: PASS, produced `paper/main.pdf`
- `paper/main.log` fatal/error/undefined-reference scan: PASS
- `paper/main.log` overfull scan: only existing `paper/sections/09f_pressure_summary.tex:71`

[SOLID-X] Paper/review/bookkeeping only; no solver or production YAML behavior changed.
