# CHK-RA-PAPER-1-11-STRICT-001 / Chapter 5 Review

対象:
- `paper/sections/05_reinitialization.tex`
- `paper/sections/05b_cls_stages.tex`

## Round 1: 厳正レビュー

判定: MAJOR あり。

指摘:
- MAJOR: 第5章は手順章なのに、`Stage`, `gate`, `ledger`, `contract`, `framework`, `sharp phase volume`, `surface-energy proxy`, `metric dissipation` などが混在し、アルゴリズム手順・受理条件・診断記録の区別が読み取りにくい。
- MAJOR: `Stage D` が標準手順なのか比較経路なのか、また DGR や幅拡大が標準閉包なのか比較感度なのかが、英語混じりの語彙で曖昧に見える。
- MAJOR: `seed`, `contact-line band`, `pinning band` など、壁面接触まわりの条件が実装語のまま残り、物理拘束と離散種点の区別が弱い。
- MAJOR: `pressure jump`, `jump`, `bulk`, `clamp` が第1--4章で整えた語彙と不一致。
- MINOR: `framework`, `redistancing`, `Gaussian`, `rescaling`, `ordering` は日本語本文の読みやすさを落としている。

対応:
- `Stage` を表示本文では「段階」に統一し、A--F は手順名として読めるようにした。
- `gate`, `ledger`, `contract`, `framework` を「判定条件」「診断記録」「受理前提」「枠組み」に置換した。
- `sharp phase volume`, `surface-energy proxy`, `metric dissipation`, `diffuse mass` を「閾値化相体積」「表面エネルギー代理量」「計量散逸」「拡散質量」に置換した。
- `seed`, `contact-line band`, `pinning band` を「種点」「接触線帯」「固定帯」または「壁面接触点」に整理した。
- DGR と幅拡大は「比較経路」「感度検証条件」として明示し、標準段階 D/F と混同しない表現へ修正した。

## Round 2: 再レビュー

判定: MAJOR なし。

確認:
- 第5章本文の重点語彙スキャンで `Stage`, `contract`, `framework`, `gate`, `ledger`, `sharp phase`, `surface-energy`, `seed`, `contact-line`, `pinning`, `rescaling`, `clamp`, `bulk`, `pressure-jump`, `jump` は表示本文として検出されない。
- 残検出は既存ラベル `sec:cls_stages`, `sec:cls_stage_sequence` のみで、読者に表示される語ではない。
- 章の構成は「Ridge--Eikonal 補助距離再構成 → 体積収支の切り分け → 実行条件と品質監視 → 物理移流と幾何射影の分離 → 標準段階 A--F」に整理された。

残留リスク:
- `Ridge--Eikonal`, `DGR`, `FMM/FSM`, `TVD-RK3`, `SSPRK3`, `ξ-SDF` は手法名として残した。各節で役割が定義されており、MAJOR ではない。

## Round 3: ユーザー指摘後の非語彙レビュー

判定: MAJOR なし。ただし MINOR 複数。

確認:
- 第5章の主張は「物理移流、Ridge--Eikonal 幾何射影、質量閉鎖を分ける」ことで一貫している。
- 段階 D は標準 CLS 手順そのものではなく補助距離再構成、段階 F は再初期化後の質量閉鎖として説明されている。
- DGR と幅拡大は比較・感度検証条件として明示され、標準経路の暗黙の安定化ではないと読める。

指摘:
- MINOR: `Part 1`, `Gaussian ridge`, `ベンチマーク`, `実装上`, `Hodge`, `identity`, `隠れた正則化`, `動的変更` が残り、章の手順説明が内部管理・英語寄りに見える箇所があった。

対応:
- `Part 1` を「前章までの定式化/連続定式化」、`Gaussian ridge` を「ガウス型リッジ」、`ベンチマーク` を「検証」、`実装上` を「計算上」に修正した。
- `毛管 Hodge 平衡判定` を「毛管平衡判定」、`離散 identity` を「離散同一性」へ修正した。
- `隠れた正則化` を「暗黙の正則化」、`$\varepsilon$ の動的変更` を「$\varepsilon$ を時間途中で変える」へ修正した。

## Round 4: 再レビュー

判定: MAJOR なし。

確認:
- 重点語彙スキャンで `Stage`, `contract`, `framework`, `gate`, `ledger`, `sharp phase`, `surface-energy`, `seed`, `contact-line`, `pinning`, `rescaling`, `clamp`, `bulk`, `pressure-jump`, `jump`, `ベンチマーク`, `Hodge`, `identity`, `Part 1`, `隠れた` は検出されない。
- `Direct Geometric Reinitialization` は DGR の正式名であり、比較経路として必要なため残す。
- `git diff --check` は通過した。

残留リスク:
- `Ridge--Eikonal`, `DGR`, `FMM/FSM`, `TVD-RK3`, `SSPRK3`, `ξ-SDF` は手法名として残る。標準経路との関係が明示されているため、MAJOR ではない。
