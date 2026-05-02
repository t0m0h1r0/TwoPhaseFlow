# Review CHK-RA-CH10-NARRATIVE-004

- Date: 2026-05-02
- Branch: `ra-ch10-narrative-20260502`
- Context: `main` への no-ff merge（`74c12199`）後，同一ワークツリーを継続して 10 章を再査読。
- Scope: `paper/sections/10_grid.tex`, `paper/sections/10c_fccd_nonuniform.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`

## Reviewer Findings and Fixes

### MAJOR-1: 固定 ε 標準経路と空間可変幅の関係がまだ曖昧

章冒頭では固定 $\varepsilon$ を標準範囲としている一方，後段の空間可変 Heaviside 幅節は同じ強さの採用候補に見えた。
このままだと読者は「固定 $\varepsilon$ が標準なのか，空間可変幅も標準なのか」を判断しにくい。

Fix:
- 適用範囲の箱で，固定 $\varepsilon$ が CLS/CSF 界面厚みを指すことを明示。
- 空間可変幅節を「固定 $\varepsilon$ 標準経路と空間可変 Heaviside 幅の制約」へ再題名化。
- 空間可変幅は GFM/圧力ジャンプ型閉包に限る補足的幾何検討であり，標準経路ではないと明記。

Status: Closed.

### MAJOR-2: D1--D4 の基本条件と詳細節が同じ階層に見える

D1--D4 節では，基本条件と後続の格子場・離散化詳細が並列に見え，補正の役割と読書順が曖昧だった。

Fix:
- `D1--D4 の数学的定義` を `D1--D4 と壁閉包の基本条件` に変更。
- 後続節を `D1 の格子場`, `D2 の離散ヘッセ行列`, `D3 の Eikonal 幾何`, `D4 の再構成幅場` として，基本条件から離散幾何への接続であることを明確化。
- D4 の体積保存記述から固定しきい値・切替語彙を除去し，保存許容範囲に基づく別較正問題として整理。

Status: Closed.

### MINOR-1: FCCD 節題と BF 表記が読み手に少し不親切

FCCD 節題が「行列定式」を前面に出しており，章全体の面幾何ナラティブより手段が目立っていた。
また `Balanced--Force` と `BF` の導入がやや不均一だった。

Fix:
- 節題を「非一様格子上の FCCD 面演算子：一般面 $\Ord{H^3}$ と中央面 $\Ord{H^4}$」へ変更。
- BF 節で `Balanced--Force（BF）` を明示し，以後の BF 表記を読みやすくした。

Status: Closed.

## Verification

- `git diff --check`: PASS
- Chapter 10 prohibited/implementation-term grep: PASS; residual `grid[step=0.5]` and `sec:fvm_ccd_corrector` are source/TikZ labels only.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 241 pp)
- `main.log` undefined/multiply-defined/rerun grep: clean

## Open Items

- FATAL: 0
- MAJOR: 0
- MINOR: 0

## SOLID Audit

- [SOLID-X] Paper/review documentation only; no production code boundary changed.
