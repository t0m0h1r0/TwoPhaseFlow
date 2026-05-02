# Review CHK-RA-CH10-NARRATIVE-003

- Date: 2026-05-02
- Branch: `ra-ch10-narrative-20260502`
- Context: `main` への no-ff merge（`f032ee3f`）後，同一ワークツリーを継続して 10 章を再査読。
- Scope: `paper/sections/10_grid.tex`, `paper/sections/10b_ccd_extensions.tex`, `paper/sections/10c_fccd_nonuniform.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`

## Reviewer Findings and Fixes

### MAJOR-1: 未採用の追従格子が細部に入りすぎ，固定格子標準経路を曇らせる

固定非一様格子を標準経路とする章なのに，追従格子節が場の転写方法や数値的目安に踏み込みすぎていた。
これは読者に「追従格子も標準経路の一部」と誤読させ，章全体の fixed-grid geometry story を弱める。

Fix:
- 追従格子の記述を，ALE 項，保存的全変数リマップ，圧力ジャンプ面幾何の再構築という数学的必要条件へ整理。
- 未採用経路の補間方法・経験的閾値・百分率誤差を本文から除去。
- 固定格子では格子運動由来の一次時間誤差を持ち込まない，という主張に限定。

Status: Closed.

### MAJOR-2: D1--D4 の導入が重複し，補正の役割が読みにくい

Ridge--Eikonal 節の冒頭と D1--D4 定義節で同じ不変量破れを繰り返していた。
また `Hessian` と「実用的困難性」という表現が混在し，数学的な不整合の所在が曖昧だった。

Fix:
- 冒頭で不変量破れを一度だけ列挙し，D1--D4 節は各補正の定義へ直行する構成に変更。
- 読者向け表記を `ヘッセ行列` に統一。
- `実用的困難性` と `フロア誤差` を，`数値的不整合` と `下限誤差` に置換。

Status: Closed.

### MAJOR-3: 実装寄り語彙がまだ本文に残っていた

`アルゴリズム`, `Level Set`, `入力/出力`, `実行`, `メモリ`, `計算量`, `並列化`, `高速化`, `シード` などが残り，論文本文の対象が理論・離散化ではなく実装説明に見える箇所があった。

Fix:
- `構成`, `水準集合`, `与える量/得られる量`, `作用`, `評価`, `格子幾何量`, `種点` などへ統一。
- FCCD の `計算量` 節を `演算子構造` として再構成。
- Ridge--Eikonal の `並列化時の等価性要件` を `離散解の等価性要件` として再定義。

Status: Closed.

### MINOR-1: 空間可変 ε の注意が二重の「ただし」で弱く見える

空間可変 $\varepsilon(\bm{x})$ の位置づけが，候補なのか採用なのか曖昧に読める表現だった。

Fix:
- 固定 $\varepsilon$ が既定であることを維持し，空間可変幅は短時間・静止界面の幾何検討に限ると明記。
- 座標変換メトリクスがジャンプ補正項を自動生成しないことを，注意ではなく閉包条件として記述。

Status: Closed.

## Verification

- `git diff --check`: PASS
- Chapter 10 implementation/prohibited-term grep: PASS; residual `grid[step=0.5]` and `sec:fvm_ccd_corrector` are source/TikZ labels only.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 239 pp)
- `main.log` undefined/multiply-defined/rerun grep: clean

## Open Items

- FATAL: 0
- MAJOR: 0
- MINOR: 0

## SOLID Audit

- [SOLID-X] Paper/review documentation only; no production code boundary changed.
