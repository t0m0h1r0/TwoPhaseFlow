# CHK-RA-PAPER-1-11-STRICT-001 Chapter 7 Review Log

## Scope

- 対象: `paper/sections/07_time_integration.tex`
- 観点: 時間積分の因果順序、項別剛性分離、毛管力/PPE/浮力の論理接続、用語の日本語化、試行錯誤・版差分の排除

## Round 1 Findings

### MAJOR: 表面張力の節が英語の部品名で読者を置いていく

`affine jump face slot`, `pressure-jump face cochain`, `raw jump`, `surface-energy Riesz cochain`, `active range`, `divergence-free Hodge`, `gate`, `stack` が本文の主要説明に残り、時間積分章としての因果順序が見えにくくなっていた。

対応:

- `アフィンジャンプ面補正枠`, `圧力ジャンプ面共鎖`, `未補正ジャンプ`, `表面エネルギーの Riesz 面共鎖`, `有効範囲`, `発散零 Hodge 成分`, `静的平衡判定量`, `結合系` に統一。
- 表面張力節を「再初期化前の移流後状態 → 表面エネルギー面共鎖 → 成分体積制約付き鞍点系 → PPE 補正段」の順で読めるように修正。

### MAJOR: 第7章の時間順序と説明順の違いが用語で曖昧になる

章冒頭では `CLS -> NS 予測子 -> IPC PPE` の因果順序を述べているが、毛管力節の `pre-reinit endpoint` や `face slot` が、どの時刻・どの状態を参照するのかを曖昧にしていた。

対応:

- `pre-reinit endpoint` を `再初期化前の移流後状態` と明示。
- `q_c` は英語添字ではなく、本文で「再初期化前の移流後場」と説明する形に変更。
- PPE 右辺・圧力増分・速度補正が同じ `\psi^{n+1}` を参照する、という章の主張に揃えた。

### MAJOR: 欠陥補正の説明に “contract” 系の語が残る

`精度契約` という見出しと本文が、査読者には契約 API 的に読める。ここは論文としては停止条件・受理条件の説明で十分である。

対応:

- 見出しを `精度受理条件` に変更。
- 本文も `契約` から `受理条件` に修正。
- ラベル名は参照互換性のため維持。

## Round 2 Findings

### MAJOR: なし

残存ヒットは LaTeX ラベル、引用略語、または `FCCD/PPE/CSF/IMEX-BDF2/TVD-RK3` など本稿の記号体系として保持すべきものに限られる。

追加対応:

- `クランプ`, `バルク`, `slope`, `projection 値域`, `capillary coupled-stack`, `parasitic currents`, 小文字 `balanced-force` を本文から除去。
- `値域制限`, `領域内部`, `傾き`, `射影値域`, `毛管結合系`, `寄生流速`, `Balanced--Force` に統一。

## Result

第7章は、MAJOR 以上の指摘が残らない状態と判断する。章のナラティブは、項別剛性分離を導入し、CLS 先行更新から物性値・毛管力・PPE・浮力残差へ同時刻情報を渡す構造として読める。
