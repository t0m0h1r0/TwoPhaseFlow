# CHK-RA-CH11-NARRATIVE-003 Review

Date: 2026-05-02
Branch: `ra-ch11-narrative-20260502`
Base: retained Chapter 11 worktree after CHK-RA-CH11-NARRATIVE-002 main merge
Scope:
- `paper/sections/11_full_algorithm.tex`
- `paper/sections/11c_dccd_bootstrap.tex`
- `paper/sections/11d_pure_fccd_dns.tex`

## Verdict

OPEN FATAL: 0
OPEN MAJOR: 0
OPEN MINOR: 0

## Strict Review Findings

| ID | Severity | Finding | Resolution |
|---|---:|---|---|
| RA-CH11-003-MAJOR-01 | MAJOR | Chapter 11 still carried a Crank--Nicolson/ADI-centered viscosity story, while Chapter 7 defines the adopted scheme as IMEX--BDF2 + implicit-BDF2 full-stress defect correction. | Rebuilt the operator map, overview table, timestep-control prose, and predictor equation around EXT2 advection + implicit-BDF2 viscous Helmholtz DC. |
| RA-CH11-003-MAJOR-02 | MAJOR | The one-field and split PPE paths were narrated as if they used different time-integration skeletons, obscuring the real fork: surface-tension/pressure-jump closure. | Recast the momentum predictor as a common vector equation and stated that the path difference is where the capillary term is closed. |
| RA-CH11-003-MAJOR-03 | MAJOR | Reader-facing prose still contained implementation/operation details (`sparse LU`, exact blow-up step counts, thresholds, `solver`-adjacent wording). | Removed low-level solve details and empirical thresholds; replaced them with mathematical low-order correction problems and operator-consistency conditions. |
| RA-CH11-003-MINOR-01 | MINOR | `アルゴリズム` / `7ステップ` / `Step`-adjacent wording conflicted with the chapter’s 第N段 narrative. | Standardized visible Chapter 11 wording to `統合更新手順`, `7段`, and `第N段`. |
| RA-CH11-003-MINOR-02 | MINOR | English fragments (`logit`, `no-slip`, `capillary energy`, `affine jump`, `lag`, `if`) made notation feel uneven. | Localized these terms to ロジット変換, 非すべり壁, 毛管エネルギー, アフィンジャンプ, 曲率の時間遅れ, and condition-only case notation. |
| RA-CH11-003-MINOR-03 | MINOR | Pure FCCD DNS still had minor operation-facing phrases around Thomas solve, execution, row structure, and expensive elliptic solve. | Rephrased as HFE boundary closure, high-order definition, discrete-equation structure, and elliptic conditioning/interface-condition complexity. |

## Reviewer Criteria

- Narrative coherence: PASS
- No old-version framing: PASS
- No implementation-centered paper prose: PASS
- Notation and term consistency: PASS
- A3 traceability through equation/operator/check references: PASS
- [SOLID-X]: paper/review documentation only; no production-code boundary changed.

## Validation

- `git diff --check`: PASS
- Chapter 11 visible obsolete-term guard: PASS; residual matches are source labels/styles or reference labels only.
- Chapter 11 prohibited-reader-framing grep: PASS; no visible old-version or implementation-centered prose.
- `rg '\\(section|subsection|caption)\\{[^}]*\\$' paper/sections/11*.tex`: PASS
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 240 pages)
- `main.log` undefined/multiply-defined/rerun grep: PASS; only package-name occurrence of `rerunfilecheck` remains.

## Merge Precondition

- Root `main` worktree was already in an unrelated CH10 conflict state before this review (`artifacts/A/review_CHK-RA-CH10-NARRATIVE-004.md`, `paper/sections/10*.tex`, `docs/02_ACTIVE_LEDGER.md`), so this CHK does not resolve or overwrite that unrelated merge state.
