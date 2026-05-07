# CHK-RA-PAPER-1-11-STRICT-001 Chapter 9 Review Log

## Scope

- 対象: `paper/sections/09_ccd_poisson.tex`, `09b_split_ppe.tex`, `09c_hfe.tex`, `09d_defect_correction.tex`, `09e_ppe_bc.tex`, `09f_pressure_summary.tex`
- 観点: 分相 PPE の章内ナラティブ、圧力ジャンプ・HFE・欠陥補正・変分毛管面共鎖の接続、最新の毛管 Hodge 閉包との整合、用語統一、LaTeX 健全性

## Round 1 Findings

### MAJOR: 章の中心語が `cochain / corrector / snapshot / gate` のまま残る

9章は「不連続な界面応力を同じ面演算子で保存したまま投影する」章だが、`cochain`, `PPE/corrector`, `snapshot`, `gate`, `solver`, `endpoint` が本文に残り、数式の責務が日本語として追いづらかった。

対応:

- `面共鎖`, `補正段`, `スナップショット`, `判定`, `解法`, `輸送終点` に統一。
- 章冒頭、分相 PPE の閉包条件、HFE の役割、章末まとめを同じ語彙に揃えた。

### MAJOR: 変分毛管閉包の最新版が実装メモ風に読める

`component-volume saddle`, `active pressure range`, `conservative face-\psi endpoint`, `trace-vertex Riesz` などが本文に残り、論文としての主張ではなく開発履歴の断片に見えた。

対応:

- 成分体積制約付き鞍点系、現在の圧力勾配値域、再初期化前の輸送終点、トレース頂点 Riesz 代表として説明を本文語に直した。
- 値域射影を本番力の置換ではなく診断代表として位置づけ、非平衡界面の毛管駆動を消してはならない論理を明確化した。

### MAJOR: 用語置換が TikZ コマンドを破壊している

`raw` の機械置換により `\draw` が `\d未補正` になり、HFE の概念図がコンパイル不能になっていた。

対応:

- TikZ の `\draw` を復旧。
- 本文中の `raw` は `未補正` に統一し、コマンド名には触れないようにした。

### MAJOR: 有限体積法/有限差分と純 FCCD 極限の関係が曖昧

`FVM 的`, `FD`, `face flux`, `PPE/projection` が混在し、有限体積法を捨てる話なのか、低次補正として限定利用する話なのかが読み分けにくかった。

対応:

- `有限体積法`, `有限差分`, `面フラックス`, `PPE/射影` に統一。
- 純 FCCD は参照極限であり、低次補正演算子や壁面閉包は面フラックス整合を破らない限り圧力ジャンプ型閉包に属する、と再整理した。

## Round 2 Findings

### MAJOR: なし

残存する `cochain`/`contract` 系ヒットは LaTeX ラベル、式ラベル、または互換参照名に限られる。本文上は、分相 PPE、HFE、変分毛管面共鎖、DC 残差受理条件、大域ゲージ・再投影分離へ自然につながる構成になった。

追加対応:

- `Laplacian`, `face value`, `face divergence`, `face kinetic mass`, `predictor`, `saddle` を本文日本語に修正。
- `有限体積法 基準離散化`, `切断面 代表`, `表面エネルギーの仮想仕事 と` などの不自然な空白を除去。

## Result

第9章は、MAJOR 以上の指摘が残らない状態と判断する。章のナラティブは、変密度一括 PPE の限界から分相 PPE へ進み、HFE で片側データを守り、圧力ジャンプ面共鎖と変分毛管 Hodge 閉包を同じ面複体上で結び、DC とゲージ・再投影分離で閉じる流れになった。
