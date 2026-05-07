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

## Round 3: ユーザー指摘後の非語彙レビュー

判定: MAJOR あり。

前回 Round 2 の扱い:
- Round 2 は語彙置換後のスキャンに依存しすぎており、章の役割である「連続レベルの前提を置く」ことへのレビューが不足していた。したがって、Round 2 の「MAJOR なし」は最終通過判定として採用しない。

指摘:
- MAJOR: 変数定義直後の Eikonal 説明が、FMM/FSM/Godunov や Ridge--Eikonal の設計論まで踏み込み、第2章の役割である符号規約・連続方程式の土台作りを妨げていた。再初期化の詳細は第5章へ送るべき。
- MAJOR: 表面張力節に F-1--F-5 の表と V番号つき検証説明が入り、第8章の Balanced--Force 本体と第13章の検証章の内容を先取りしすぎていた。第2章では、CSF と Young--Laplace ジャンプが同じ界面応力条件に由来する、という前提だけを固定すべき。
- MAJOR: `Hodge`, `アフィンジャンプ`, `bulk`, `wall-normal capillary closure layer`, `ベンチマーク` などが残り、日本語の支配方程式章として読みにくかった。
- MAJOR: 冒頭で「HFE と面共鎖投影」と書いており、第2章の読者に未導入の離散概念を要求していた。高密度比主経路の説明は必要だが、連続章では「片側データ」と「面上の補正量」までに抑えるべき。

対応:
- Eikonal の箱を、$\phi$ は幾何評価を支える補助場、$\psi$ は保存形移流の主変数、という役割分担の説明へ置き換えた。
- 表面張力節の F-1--F-5 表を第2章から外し、連続平衡が離散平衡として残るために何が後続章で揃えられるべきかだけを短く説明した。
- V番号、`Hodge`, `アフィンジャンプ`, `bulk`, `wetting/contact-angle`, `wall-normal capillary closure layer`, `曲率 cap`, `ベンチマーク`, `実装チェックリスト` を第2章本文から除去または日本語化した。
- 冒頭の高密度比主経路の説明を「HFE で片側データを構成し，速度補正で使う面上の補正量まで同じ離散構造に閉じる」とし、未導入の面共鎖投影を持ち込まない形にした。

## Round 4: 再レビュー

判定: MAJOR なし。

確認:
- 章構成は「変数と符号規約 → 二流体から一流体への弱形式等価性 → 物性補間と面係数 → 表面張力と圧力ジャンプ → 無次元化 → 曲率」となり、第3章へ渡す連続前提として読める。
- 第2章本文の重点語彙スキャンで `Hodge`, `V番号`, `P-1..P-7`, `アフィン`, `bulk`, `wetting/contact-angle`, `wall-normal`, `ベンチマーク`, `pressure-jump`, `projection-native`, `face-space`, `contract`, `primitive`, `stack`, `Stage`, `Step`, `サブシステム`, `検証ゲート`, `面共鎖投影`, `F-1--F-5` は検出されない。
- `git diff --check` は通過した。

残留リスク:
- `Two-Fluid`, `One-Fluid`, `CSF`, `PPE`, `HFE`, `Riesz` は標準的な定義名または後続章の正式略語として残る。第2章では日本語併記と近接説明があるため、MAJOR ではない。
