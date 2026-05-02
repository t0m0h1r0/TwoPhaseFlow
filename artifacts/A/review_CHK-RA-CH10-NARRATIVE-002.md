# Review CHK-RA-CH10-NARRATIVE-002

- Date: 2026-05-02
- Branch: `ra-ch10-narrative-20260502`
- Context: `main` への no-ff merge（`e6bb3324`）後，同一ワークツリーを継続して 10 章を再査読。
- Scope: `paper/sections/10_grid.tex`, `paper/sections/10b_ccd_extensions.tex`, `paper/sections/10c_fccd_nonuniform.tex`, `paper/sections/10d_ridge_eikonal_nonuniform.tex`

## Reviewer Findings and Fixes

### MAJOR-1: 固定格子標準経路のナラティブが二重化して見える

章の主線は「共有界面幾何を固定非一様格子へ写し，その面幾何上で CCD/FCCD と Ridge--Eikonal を整合させる」ことである。
しかし読者に見える `Mode 1/Mode 2` 的な語りは，章の標準経路が固定格子なのか追従格子なのかを曖昧にしていた。

Fix:
- 標準経路を「固定非一様格子 + 固定 $\varepsilon$ + 固定 HFE/jump 面幾何」として前面化。
- 追従再生成は標準経路ではなく，ALE，保存的リマップ，HFE/jump 面幾何再構成，壁面境界条件の面演算子整合が揃う場合の拡張条件として整理。
- 「過剰細分化モード」などの語を「過剰細分化の兆候」に置換し，分類名ではなく診断として読ませる構成に変更。

Status: Closed.

### MAJOR-2: 実装・運用に寄った英語語彙が論文の説明密度を下げる

`step`, `caveat`, `corrector`, `RHS`, `face-locus`, `wall BC`, `pressure-jump`, `seed`, `upwind`, `narrow band` などの語が，数学的対象と手順名を混在させていた。
この混在は，章 10 の対象が実装ではなく「非一様格子上の面幾何・差分演算子・再距離化条件」であることを弱めていた。

Fix:
- 読者に見える語彙を，`段階`, `注意`, `速度補正`, `PPE 右辺`, `同一面位置`, `壁面境界条件`, `圧力ジャンプ`, `種点`, `風上`, `狭帯域` に統一。
- `グリッド` は章 10 の読者向け本文では `格子` に統一。
- `Gaussian support` などの英語句を `ガウス型支持帯` などの数学的な日本語句へ寄せた。

Status: Closed.

### MAJOR-3: 格子座標生成の説明がアルゴリズム列に見える

座標生成節が「アルゴリズム」「ステップ」として読めるため，格子写像の仮定・精度律速・メトリクス評価という理論的接続が弱く見えていた。

Fix:
- 節名と本文を「構成」「段階」に統一。
- 採用するメトリクス評価を，代替案の列挙ではなく「座標生成後の離散写像に対する CCD メトリクス評価」として再定義。
- 低次差分は採用外の比較対象として位置づけ，章の主線から外した。

Status: Closed.

### MAJOR-4: FCCD の精度主張が局所面演算子と座標生成精度を混同する

FCCD 面演算子の局所精度と，台形則で生成した物理座標写像を合成した全体精度が同じ主張として読める箇所があった。
これは過大主張に見えるため，査読上は厳しく分離すべきである。

Fix:
- 局所 FCCD 面演算子は生成済み格子上で $\Ord{H^4}$ と記述。
- 物理微分として合成した全体精度は，座標写像生成の求積精度に律速されると明記。
- 格子生成の注意節への参照を `sec:grid_metric_order_note` として，内容も「精度律速の注意」に統一。

Status: Closed.

### MINOR-1: Ridge--Eikonal 節の壁面・FMM 語彙がデータ構造に寄る

`Accepted`, `trial queue`, `freezing`, `signed-distance`, `wall trace` などの表現が，論文本文では幾何条件より手続きに見えた。

Fix:
- `確定集合`, `候補列`, `凍結集合`, `符号付き距離`, `壁面トレース` に統一。
- `禁止定理` は強すぎるため，「避ける理由」に変更。
- 壁面接触界面の式ラベルを source-only でも `wall_contact_zero_set` に改名し，本文語彙と揃えた。

Status: Closed.

## Verification

- `git diff --check`: PASS
- Chapter 10 prohibited visible-term grep: PASS; residual `sec:fvm_ccd_corrector` is a cross-chapter source label only.
- `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex`: PASS (`paper/main.pdf`, 239 pp)
- `main.log` undefined/multiply-defined/rerun grep: clean

## Open Items

- FATAL: 0
- MAJOR: 0
- MINOR: 0

## SOLID Audit

- [SOLID-X] Paper/review documentation only; no production code boundary changed.
