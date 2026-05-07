# CHK-RA-PAPER-1-11-STRICT-001 / Chapter 2 Review

対象:
- `paper/sections/02_governing.tex`
- `paper/sections/02b_surface_tension.tex`
- `paper/sections/02c_nondim_curvature.tex`

## Round 1: 厳正レビュー

判定: MAJOR あり。

指摘:
- MAJOR: 第2章は支配方程式の土台を定める章なのに、冒頭と結語で「連続レベルの契約」「係数契約」と書いており、読者にとって意味が硬すぎる。第1章で整理した「検証可能な離散条件」へ渡す前段としては「連続レベルの前提」と表現すべき。
- MAJOR: `face 係数`, `hydrostatic`, `Predictor`, `pressure-jump/Hodge`, `affine jump`, `プリミティブ` が残り、日本語章としての読みやすさと第1章の語彙方針に反する。
- MAJOR: CSF と分相 PPE の関係を「CSF が One-Fluid/BF の連続収縮と対照モデル」と述べており、何が縮約で何が主経路かが曖昧だった。CSF/BF は縮約経路、分相圧力ジャンプ PPE は高密度比主経路として明示する必要がある。
- MAJOR: 圧力方程式の面係数である $\rho^{-1}$ の平均表記が、密度値の平均なのか $1/\rho$ 値の平均なのか読み違えやすい。圧力閉包の章へ渡る重要点なので、表で明示すべき。
- MINOR: `Two-Fluid`, `One-Fluid` は標準語だが、章見出しと導入で日本語併記が不足していた。

対応:
- 「連続レベルの契約」「係数契約」を「連続レベルの前提」「係数前提」に置換した。
- `face 係数`, `hydrostatic`, `Predictor`, `pressure-jump/Hodge`, `affine jump`, `プリミティブ`, `CSF 収縮` を日本語主語彙へ修正した。
- `Two-Fluid` と `One-Fluid` は二流体・一流体を併記し、見出しと導入を日本語から読める形へ整えた。
- $\rho^{-1}$ 面係数は「$1/\rho$ 値の調和平均」と表内に明記し、$\mu$ 面係数との違いを読み違えにくくした。

## Round 2: 再レビュー

判定: MAJOR なし。

確認:
- 第2章本文の重点語彙スキャンで `契約`, `pressure-jump`, `affine jump`, `face closure`, `projection-native`, `primitive`, `hydrostatic`, `Predictor`, `連続収縮`, `sub-system`, `stack`, `検証ゲート`, `slope` は検出されない。
- Young--Laplace の符号規約，CSF 体積力，圧力ジャンプ条件，浮力の勾配・残差分解，曲率の単調変換不変性は維持されている。
- 第2章の章構成は「変数と符号規約 → 二流体から一流体へ → 物性・面係数 → 表面張力 → 無次元化 → 曲率」という流れになり，第3章へ渡す前提が明確になった。

残留リスク:
- `Continuum Surface Force`, `face-centred CCD` は定義時の括弧内英語として残した。本文の主語彙は「連続表面力」「面中心 CCD」であり，MAJOR ではない。
