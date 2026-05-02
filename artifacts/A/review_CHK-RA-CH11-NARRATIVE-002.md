# CHK-RA-CH11-NARRATIVE-002 Review

Date: 2026-05-02
Branch: `ra-ch11-narrative-20260502`
Base: post-merge `main` (`8cb627ba`), retained source worktree
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
| RA-CH11-002-MAJOR-01 | MAJOR | 標準経路の一括 PPE / 分相 PPE の選択点が，章冒頭の物語としてまだ暗黙だった。 | 章冒頭に低・中密度比の一括 PPE と高密度比・高粘性比・低 We の分相 PPE の使い分けを明記し，後続の第5--7段へ接続した。 |
| RA-CH11-002-MAJOR-02 | MAJOR | 読者に見える `Step` / `Predictor` / `Corrector` / `Phase` が日本語本文の段・層ナラティブを分断していた。 | アルゴリズムを `第N段`，純 FCCD DNS を `第N層`へ統一し，予測段階・補正段階の語で全章を通した。 |
| RA-CH11-002-MAJOR-03 | MAJOR | `pressure-jump`，`BC`，`face-average`，`product-rule`，`full-tensor` などの英語混在により表記の基準が揺れていた。 | 圧力ジャンプ，境界条件，面平均，積の微分則，全テンソル評価などへ統一し，表示される説明語を数学的日本語へ寄せた。 |
| RA-CH11-002-MINOR-01 | MINOR | 純 FCCD DNS の寄生流れ抑制主張が検証範囲より強く読めた。 | `最小化` / `大幅削減` を，研究構成としての低減目標・期待される利点へ弱めた。 |
| RA-CH11-002-MINOR-02 | MINOR | 粘性 DC と PPE DC の右辺記法に `RHS` が残り，本文表記と数式記号が混在していた。 | 粘性右辺を `b_\nu^{n,n-1}`，PPE 右辺を `b_p` として導入し，欠陥式も同記号へ統一した。 |
| RA-CH11-002-MINOR-03 | MINOR | 純 FCCD DNS の対象外・検証済み範囲の言い方に英語調と過剰断定が残っていた。 | 対象外・検証範囲外・将来課題の語へ揃え，標準経路との補完関係を保った。 |

## Reviewer Criteria

- Narrative coherence: PASS
- No old-version framing: PASS
- No implementation-centered paper prose: PASS
- Notation and term consistency: PASS
- A3 traceability through equation/operator/check references: PASS
- [SOLID-X]: paper/review documentation only; no production-code boundary changed.

## Validation

- `git diff --check`: PASS
- Chapter 11 visible terminology guard: PASS; residual matches are source labels/styles or math symbols only (`sec:pure_fccd_gates`, `method/.default`, `\phi_{\mathrm{raw}}`, `sec:ppe_solve`).
- Chapter 11 prohibited-reader-framing grep: PASS; no visible old-version or implementation-centered prose.
- `rg '\\(section|subsection|caption)\\{[^}]*\\$' paper/sections/11*.tex`: PASS
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 241 pages)
- `main.log` undefined/multiply-defined/rerun grep: PASS; only package-name occurrence of `rerunfilecheck` remains.
