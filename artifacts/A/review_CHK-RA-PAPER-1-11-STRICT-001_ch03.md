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

## Round 3: ユーザー指摘後の非語彙レビュー

判定: MAJOR なし。ただし MINOR 複数。

確認:
- 第3章の主張は「保存形で運ぶ主変数は $\psi$、幾何評価を支える補助距離場は $\phi$、曲率は標準経路では $\psi$ 微分から直接評価し、Ridge--Eikonal は品質劣化・トポロジー変化時の幾何修復段」という線で通っている。
- 章頭の節案内、保存形移流、$\psi$--$\phi$ 対応、直接曲率、Ridge--Eikonal の順序は、第2章の連続前提から第4章以降の離散化へ進む導線として成立している。
- Ridge--Eikonal は標準 CLS 手順の置換ではなく補助距離再構成である、と本文内で明示されている。

指摘:
- MINOR: `実装者`, `実装ガイド`, `ベンチマーク`, `SDF`, `diffuse-interface`, `隠れた正則化` など、論文本文としては内部運用寄りまたは英語寄りの語が残っていた。
- MINOR: 「既存接触根」は日本語として硬く、壁面上の相区間・接触点の保存という意味が伝わりにくかった。

対応:
- 「実装者への指針」を「数値設計上の含意」、「再初期化の実装・運用詳細」を「再初期化の離散化上の詳細」、「実装ガイド」を「設定指針」へ修正した。
- 「ベンチマーク」を「検証」、「SDF 幅/diffuse-interface 幅」を「符号付き距離関数の幅/拡散界面幅」、「隠れた正則化」を「暗黙の正則化」へ修正した。
- 「既存接触根」を「既存の接触点」へ修正し、壁面トポロジ制約の説明を読みやすくした。

## Round 4: 再レビュー

判定: MAJOR なし。

確認:
- 重点語彙スキャンで `pipeline`, `predictor`, `Stage`, `flagging`, `primitive`, `bootstrap`, `widening`, `pressure-jump`, `affine`, `sub-system`, `stack`, `検証ゲート`, `V番号`, `U番号`, `ベンチマーク`, `SDF`, `diffuse-interface`, `実装者`, `実装ガイド`, `ハイブリッド戦略` は検出されない。
- 残る `curvature_clamped` / `newton_inversion` は数式・節ラベルであり、本文表示語としての版管理語や値域制限語ではない。
- `git diff --check` は通過した。

残留リスク:
- `Ridge--Eikonal`, `FMM/FSM`, `HFE`, `FCCD`, `Newton` は手法名として残る。各節で用途が説明され、最新の研究内容を支える構成要素として必要なため、MAJOR ではない。
