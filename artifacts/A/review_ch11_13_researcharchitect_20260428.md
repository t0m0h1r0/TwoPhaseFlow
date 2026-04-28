# §11--§13 ResearchArchitect Strict Review — 2026-04-28

Initial verdict: MAJOR REVISION.
Verdict after fixes: PASS (0 FATAL, 0 MAJOR).

## Scope
- Reviewed `paper/sections/11_full_algorithm.tex`.
- Reviewed `paper/sections/11c_dccd_bootstrap.tex`.
- Reviewed `paper/sections/11d_pure_fccd_dns.tex`.
- Reviewed `paper/sections/12_component_verification.tex` and `paper/sections/12u*.tex`.
- Reviewed `paper/sections/13_verification.tex` and `paper/sections/13[a-f]_*.tex`.
- Review focus: technical consistency after §11 restoration, U/V experiment separation, reviewer-facing evidence strength, terminology unification, and chapter-format consistency with §1--§3.

## Findings
- R11-13-1 MAJOR: §11 was restored as an old algorithm chapter but still contains the retired Level taxonomy as the visible routing layer. `paper/sections/11_full_algorithm.tex:75`, `paper/sections/11_full_algorithm.tex:248`, and `paper/sections/11_full_algorithm.tex:321` define Level 1/2/3 behavior, while §12--§13 now organize evidence by U-series component tests and V-series integration tests. A reviewer sees two incompatible classification systems.
- R11-13-2 MAJOR: §11 Step 5/6 algorithm description is internally inconsistent. The overview table says Step 5 uses UCCD6 + EXT2 / IMEX--BDF2 and Step 6 uses split FCCD PPE, but the detailed Step 5 formula is the old Level 2a AB2 + CN/ADI form, and Step 6 later presents a Level 1/2 lumped PPE equation before split PPE. This makes the “one complete timestep” underspecified rather than executable.
- R11-13-3 MAJOR: §11 Figure/caption claims Level 3 removes CSF and replaces it with HFE pressure-jump evaluation at Step 5a, but Step 5a actually constructs an HFE extension of the old pressure `p^n`; the jump condition is discussed in the PPE branch. This misplaces the pressure-jump mechanism and invites an algorithm-fidelity objection.
- R11-13-4 MAJOR: §11 Pure FCCD DNS subsection mixes final-paper content with implementation roadmap / acceptance-plan language. `paper/sections/11d_pure_fccd_dns.tex:178`--`230` includes “検証予定”, “実装ロードマップ”, “付録予定”, and “ジャンプ YAML 仕様”. A reviewer will treat these as unverified engineering plans, not paper results.
- R11-13-5 MAJOR: §12 U6 and §13 V6 use similar labels for different pressure strategies without enough separation. §12 reports lumped--PPE high-density deterioration, while §13 claims split PPE + DC + HFE density-ratio robustness. The text references U6 from V6, but U6 is titled and evidenced as lumped--PPE. The negative result and the replacement strategy must be separated explicitly.
- R11-13-6 MAJOR: §11 presents IMEX--BDF2 / implicit-BDF2 as the main two-phase timestep path, but §13 V7 shows two-phase slope 0.56 and states that BDF2 design order is not maintained. This is a correct and valuable negative result, but §11 does not pre-announce the limitation; the paper currently over-promises before later retracting.
- R11-13-7 MAJOR: §13 claims to evaluate whether the integrated solver preserves physical consistency and design convergence order, but multiple V results are failures or conditional: V4 RT error 40--55%, V7 time order 0.56, V9 local epsilon unstable, V10 non-uniform CLS drift +12%. These are useful findings, but the parent chapter needs an explicit “success / limitation / out-of-scope” framing before the table.
- R11-13-8 MAJOR: §13 has visible implementation/history residue. `paper/sections/13_verification.tex:44` exposes figure basenames as “新図 (ch13_v*)”; `paper/sections/13d_density_ratio.tex:20` mentions “旧 §13g”; `paper/sections/13d_density_ratio.tex:75` uses `blew_up = False`. This violates the paper-facing style already enforced for §12--§13.
- R11-13-9 MAJOR: Cross-chapter references in §13e are semantically stale. `paper/sections/13e_nonuniform_ns.tex:185` says “§3 (非一様格子), §9 (CLS 移流), §11 (制約整理)”, but current non-uniform grid is §10 and CLS transport is §3b/§3; §9 is pressure/PPE. The recommendation is sound, but the chapter mapping is wrong.
- R11-13-10 MINOR: §12 summary accepts U4-a and U4-b with absolute errors but does not state a threshold in the table itself. The criterion says slope or known deterioration; U4’s `9e-3` and `3e-6` need a local acceptance threshold or a reference to the theoretical tolerance.
- R11-13-11 MINOR: §13 V6 repeats the “検証対応” sentence pair. This is a simple prose duplicate in `paper/sections/13d_density_ratio.tex:83`--`85`.
- R11-13-12 MINOR: Terminology is visibly mixed: `NS` and `Navier--Stokes`, `spurious current` and `寄生流れ`, `reinit` and `再初期化`, `Lumped--PPE` and `lumped--PPE`, `smoothed Heaviside` and `Smoothed Heaviside`, `production` and `プロダクション`. Most are harmless individually; together they make §11--§13 look assembled from different drafts.
- R11-13-13 MINOR: Chapter format is not unified. §11 begins with an enumerated roadmap, §12 uses `目的 / 構成 / 検証成績一覧`, §13 uses `位置付け / 設計指針 / 概観 / 構成`, and subtests differ between `単体テスト` and `設定`. §1--§3 generally open with a chapter-positioning paragraph and then proceed with coherent subsections; §11--§13 should adopt a similar rhythm.

## Treatment Policy
- Do not delete the restored §11 wholesale. Preserve its useful role: a single algorithm map linking §4--§10 methods to §12--§13 evidence.
- Replace the visible Level taxonomy with physical/evidence-based regimes unless the paper defines Level terms once and carries them consistently. Recommended visible regimes: “単相/等密度検証”, “一括 smoothed-Heaviside PPE”, “分相 PPE + HFE”, and “純 FCCD DNS（研究構成）”.
- Demote unverified roadmap material from §11d. Either move it to appendix/memo or compress it to a short “研究構成の位置付け” paragraph with no YAML, no planned appendix, and no unvalidated acceptance gates.
- Make §11 honest about §13 limitations: IMEX--BDF2 is second-order for single-phase tests, but two-phase integration is currently limited by reinitialization frequency and curvature lag.
- Split U6/V6 vocabulary: U6 should be “一括 PPE の限界 + HFE/DC component behavior”; V6 should be “分相 PPE + DC + HFE integrated density-ratio robustness”. The replacement relation must be explicit.
- Put negative results up front in §13. A strict reviewer accepts limitations when they are framed as findings, not when they appear after a success-sounding overview.

## Terminology Unification Plan
- Use `Navier--Stokes` at first mention in each chapter; use `NS` only after local introduction.
- Use `Ridge--Eikonal`, `Balanced--Force`, `Level Set`, `Conservative Level Set (CLS)` consistently.
- Use Japanese paper-facing terms for visible results: `寄生流れ` instead of raw `spurious current` except parenthetical first mention; `再初期化` instead of `reinit` except code comments; `ブローアップなし` instead of `blew_up = False`.
- Normalize PPE terminology:
  - `一括 PPE` / `一括 smoothed-Heaviside PPE` for lumped one-field pressure tests.
  - `分相 PPE` for split phase pressure solves.
  - Avoid mixing `Lumped--PPE`, `lumped--PPE`, and `phase-density lumped` in visible prose.
- Remove paper-visible implementation tokens: `ch13_v*`, `YAML`, `実装ロードマップ`, `付録予定`, `production`, old-section history markers.

## Format Unification Plan
- §11:
  - Add `本章の位置付け` and `本章の構成` style opening.
  - Keep one compact 7-step algorithm table.
  - Follow with `制約条件と §13 検証への接続` so limitations are not hidden.
- §12:
  - Keep the U-series but align the parent opening to §1--§3: position first, then structure.
  - Standardize each U subsection as `検証対象 / 設定 / 結果 / 判定 / 次章への接続`.
  - Add explicit acceptance threshold for tests that are not slope-based.
- §13:
  - Add an opening “判定の読み方”: checkmark = verified, triangle = conditionally supported, cross = limitation.
  - Standardize each V subsection as `検証対象 / 設定 / 結果 / 判定 / 制約条件`.
  - Move the master failure/limitation summary near the front or duplicate it in compact form before individual V sections.

## Recommended Fix Order
1. Fix paper-visible residue and duplicated prose in §13 (low risk, high polish).
2. Align terminology across §11--§13 and remove old Level wording where not essential.
3. Rewrite §11 opening and Step 5/6 routing to match the current validated solver regimes.
4. Reframe §11d pure FCCD DNS as a research-limit architecture, not an implementation plan.
5. Reframe §13 parent summary to foreground V7/V9/V10 limitations and make the chapter’s verdict honest.
6. Normalize §12/§13 experiment subsection format after the technical routing is stable.

## Fix Summary
- R11-13-1 fixed: §11 no longer exposes retired Level 1/2/3 routing; visible routing now uses “一括 PPE”, “分相 PPE”, and “純 FCCD DNS（研究構成）”.
- R11-13-2/R11-13-3 fixed: §11 Step 5/6 now separates one-field PPE and split PPE paths, clarifies Step 5a as HFE extension of known pressure, and places pressure-jump handling in the split PPE branch.
- R11-13-4 fixed: §11d roadmap/YAML/planned-appendix/acceptance-plan material was replaced by a paper-facing “検証章との接続” table and a scoped research-architecture positioning paragraph.
- R11-13-5 fixed: §12 U6 is now “一括 PPE の限界 + DC/HFE 単体挙動”; §13 V6 remains split PPE + DC + HFE integrated robustness.
- R11-13-6/R11-13-7 fixed: §11 and §13 now state upfront that two-phase IMEX--BDF2 is limited by reinitialization frequency and curvature lag; §13 adds a verdict policy distinguishing pass, conditional pass, and limitation.
- R11-13-8/R11-13-9 fixed: visible `ch13_v*`, `旧 §13g`, `blew_up = False`, and stale §13e chapter references were removed or corrected.
- R11-13-10 fixed: U4 acceptance thresholds were made explicit (`≤1.5h`, ratio error `≤10^{-4}`).
- R11-13-11 fixed: duplicate V6 verification prose was removed.
- R11-13-12/R11-13-13 fixed: terminology and subsection headings were normalized across §11--§13 (`寄生流れ`, `再初期化`, `一括 PPE`, `分相 PPE`; `検証対象 / 設定 / 結果 / 判定...`).

## Verification After Fixes
- `git diff --check` passed.
- `cd paper && latexmk -xelatex -interaction=nonstopmode main.tex` passed.
- Output: 221 pages.
- Log scan: 0 undefined references, 0 undefined citations, 0 multiply-defined labels.

## SOLID Audit
- [SOLID-X] Not applicable to this review artifact. No `src/` code or production class/module structure was modified.
