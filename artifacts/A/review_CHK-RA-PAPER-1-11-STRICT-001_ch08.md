# CHK-RA-PAPER-1-11-STRICT-001 Chapter 8 Review Log

## Scope

- 対象: `paper/sections/08_collocate.tex`, `08b_pressure.tex`, `08c_bf_failure.tex`, `08d_bf_seven_principles.tex`, `08e_fccd_bf.tex`
- 観点: Balanced--Force のナラティブ、面評価位置と面共鎖の用語統一、コロケート格子の問題設定、P-1--P-7 と F-1--F-5 の対応、標準圧力ジャンプ経路の論理一貫性

## Round 1 Findings

### MAJOR: 章の中心概念が `face cochain / pressure-jump / face complex` のまま残る

第8章は「どの量を同じ面空間で釣り合わせるか」が主題だが、`face cochain`, `pressure-jump`, `face complex`, `face slot`, `surface-energy cochain`, `component-corrected cochain` がそのまま残り、読者が概念を掴みにくい。

対応:

- `面共鎖`, `圧力ジャンプ`, `面複体`, `面補正枠`, `表面エネルギー面共鎖`, `成分補正済み面共鎖` に統一。
- 章冒頭、構成リスト、Balanced--Force 条件、FCCD 面フラックス部分系の説明を同じ語彙に揃えた。

### MAJOR: コロケート格子の2つの破綻原因が英語のまま曖昧

`decoupling`, `face complex`, `PPE/corrector`, `RHS` の混在により、演算子不整合と格子スケールの圧力・速度分離が別問題であることが見えにくかった。

対応:

- `格子スケールの圧力・速度分離`, `同じ面複体による PPE/補正段共有`, `右辺発散` として整理。
- Rhie--Chow の説明も `面速度補間` に修正。

### MAJOR: P-1--P-7 が API 契約のように読める

`残差契約`, `標準契約`, `精度契約`, `gate`, `range projection`, `raw` が混在し、査読者には実験・実装メモの名残として見える。

対応:

- `残差受理条件`, `標準受理条件`, `精度受理条件`, `判定量`, `値域射影`, `未補正` に修正。
- 固定回数 `k=3` は実用上限であり、標準 BF 閉包の受理条件ではないことを明確化。

## Round 2 Findings

### MAJOR: なし

残存する英語系ヒットは LaTeX ラベル、`FaceJet` の演算子名、または既存参照キーに限られる。

追加対応:

- `spurious currents`, `FVM`, `face-average`, `face-adjoint`, `face-balance`, `PASS/FAIL`, `フェイス速度`, `静止液滴 gate` を本文から除去。
- `寄生流れ`, `有限体積法`, `面平均`, `面随伴`, `面釣合`, `合格/不合格`, `面速度`, `静止液滴判定量` に統一。

## Result

第8章は、MAJOR 以上の指摘が残らない状態と判断する。章のナラティブは、コロケート格子の圧力・速度分離問題から始まり、面共鎖の釣合、P-1--P-7、FCCD 面フラックス部分系へ自然につながる。
