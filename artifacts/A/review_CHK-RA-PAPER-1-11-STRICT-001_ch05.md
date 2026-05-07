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
