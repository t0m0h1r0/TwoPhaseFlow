# WIKI-L-021: matplotlib Figure Titles — Use English Only (Remote CJK Font Absence)

## Problem

Japanese (or any CJK) text in YAML figure spec fields (`title:`, `xlabel:`, `ylabel:`, `labels:`) renders as **white tofu boxes** (□□□) in generated PDFs on the remote Linux server.

Example (broken):
```yaml
- type: time_series
  title: "毛細管波 D(t) — 水-空気"   # <- renders as □□□ on remote
  ylabel: "変形量"
```

## Root Cause

matplotlib's default font stack on a headless Linux server does not include CJK (Chinese/Japanese/Korean) fonts. When a glyph is missing, matplotlib substitutes a white rectangle. The remote server (`python` host) has no `fonts-noto-cjk` or equivalent package installed.

**Exception**: LaTeX math mode strings (`$...$`) work correctly because matplotlib's `mathtext` engine renders them using its own internal font, bypassing the system font stack entirely.

## Fix

Commit `2ad0bb1` — all three ch13 production configs updated:
- `ch13_01_capwave_waterair.yaml`
- `ch13_02_rising_bubble.yaml`
- `ch13_03_taylor_deformation.yaml`

Rule applied:
```yaml
# BEFORE (broken on remote):
title: "§13.1 毛細管波 D(t) — 水-空気 (ρ=833:1)"
ylabel: "Kinetic energy $E_k$"   # OK — E_k is math mode

# AFTER (correct):
title: "Capillary wave D(t) — water/air (rho=833:1), GFM, alpha=1.5"
ylabel: "Kinetic energy $E_k$"   # still OK
```

## Rules

| Field | Rule |
|---|---|
| `title:` | ASCII/English only |
| `xlabel:`, `ylabel:` | ASCII/English or LaTeX math (`$...$`) |
| `labels:` list | ASCII/English or LaTeX math |
| YAML comments (`#`) | Any language — not rendered |
| LaTeX paper source (`.tex`) | Any language — compiled by XeLaTeX with CJK support |

## Detection

Open generated PDF and search for contiguous □□□ blocks in axis labels or titles. If the title appears as white space with fixed width, it's CJK tofu.

## sources

- `experiment/ch13/config/ch13_01_capwave_waterair.yaml`
- `experiment/ch13/config/ch13_02_rising_bubble.yaml`
- `experiment/ch13/config/ch13_03_taylor_deformation.yaml`
- `src/twophase/tools/plot_factory.py`

## depends_on

- `[[WIKI-X-017]]` (ch13 production config pattern)
