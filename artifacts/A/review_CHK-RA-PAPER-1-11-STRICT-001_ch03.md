# CHK-RA-PAPER-1-11-STRICT-001 / Chapter 3 Review

対象:
- `paper/sections/03_levelset.tex`
- `paper/sections/03b_cls_transport.tex`
- `paper/sections/03c_levelset_mapping.tex`
- `paper/sections/03d_ridge_eikonal.tex`

## Round 1: 厳正レビュー

判定: MAJOR あり。

指摘:
- MAJOR: CLS 章の読者導線は「$\psi$ を保存形で運ぶ」「必要時だけ $\phi$ を作る」「曲率は標準経路では $\psi$ から直接評価する」であるべきだが、`pipeline`, `predictor`, `clamp`, `flagging`, `primitive`, `bootstrap` などの実装語が混ざり、数理上の役割が読みにくい。
- MAJOR: `MAC スタガード格子 = 0（厳密保存）` という表現は過剰で、保存形スカラー移流・境界処理・値域制限の誤差を隠す。比較対象としては、離散発散フリー速度と保存形フラックスを組み合わせやすい、という範囲に留めるべき。
- MAJOR: `既存の xi_sdf 再初期化モード` と具体的な実装名が本文に出ており、論文本文としては内部実装履歴に見える。研究の構成要素として一般化して記述すべき。
- MAJOR: Ridge--Eikonal の位置づけは「標準 CLS 手順の置換ではなく幾何修復段」と書かれている一方、表では再初期化そのものが Ridge--Eikonal 距離再構成であるように読めた。標準手順と補助経路の階層を揃える必要がある。
- MINOR: `Gaussian`, `Stage`, `widening`, `branch` などの英語語彙が残り、日本語としての可読性を落としている。

対応:
- `pipeline`, `predictor`, `clamp`, `Stage`, `flagging`, `primitive`, `bootstrap`, `widening`, `branch` をそれぞれ「標準 CLS 手順」「予測段」「値域制限/分母下限制限」「段階」「検出」「解析形状」「初期補助構成」「局所界面幅拡張」「連続枝」に置換した。
- MAC スタガード格子の比較表を、厳密保存の過剰主張から「保存形フラックスと離散発散フリー速度を組み合わせやすい」へ修正した。
- 内部実装名 `xi_sdf` とクラス名を削り、「単純な符号付き距離再構成」として一般化した。
- 再初期化表では Ridge--Eikonal を標準再初期化そのものとして見せず、「圧縮--拡散平衡を基準にした距離再構成と質量閉鎖」へ整えた。

## Round 2: 再レビュー

判定: MAJOR なし。

確認:
- 第3章本文の重点語彙スキャンで `pipeline`, `predictor`, `clamp`, `Stage`, `flagging`, `primitive`, `bootstrap`, `widening`, `契約`, `pressure-jump`, `affine jump`, `sub-system`, `stack`, `検証ゲート` は表示本文として検出されない。
- 残検出は既存の数式ラベル `eq:curvature_clamped` のみで、読者に表示される語ではない。
- ナラティブは「CLS を使う理由 → 保存形移流 → 再初期化 → $\psi$--$\phi$ 対応 → $\psi$ 直接曲率 → Ridge--Eikonal 補助再構成」に整理された。

残留リスク:
- `Ridge--Eikonal`, `FMM/FSM`, `HFE`, `FCCD` は手法名として残した。各節で役割説明があり、MAJOR ではない。
