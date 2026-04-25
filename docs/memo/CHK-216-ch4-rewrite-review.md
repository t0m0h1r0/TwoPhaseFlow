# CHK-216 §4 改稿 自己査読メモ（論文査読官視点）

**日付**: 2026-04-26
**ブランチ**: `worktree-ra-paper-ch4-rewrite`
**対象**: `paper/sections/04*.tex` (§4 章全体, 1515 LOC, 6 ファイル)
**ビルド状態**: 256pp / 0 undef refs / 0 multiply-defined

## 査読概要

CHK-216 計画 Phase 7 の自己査読として，§4 改稿後の §4 章全体を
論文査読官視点で読み込み，**§4 純化原則**（HFE/GFM/PPE/BF/balanced-force/CSF
等の用途章機構を §4 から完全排除）の達成度，narrative 一貫性，
術語統一，cross-ref 整合性を Critical / Major / Minor の 3 段階で評価する．

**結果サマリー**: Critical **0** / Major **0**（査読中に発見した 4 件は
本査読の枠内で即時修正済み） / Minor **5**．計画目標
（Critical 0 / Major ≤ 3 / Minor ≤ 10）を達成．

## A. §4 純化（最重要観点）

### A-1 V-grep audit 結果

| Pattern | 期待 | 実測 | 判定 |
|---|---|---|---|
| `ref{sec:balanced_force\|sec:bf_\|sec:pressure\|sec:hfe\|sec:gfm\|sec:field_extension\|sec:split_ppe}` (active text) | 0 件 | **0 件** | **PASS** |
| `HFE\|GFM\|balanced[- ]force\|Hermite 場\|Ghost.Fluid` (大小区別) | 0 件 | **0 件** | **PASS** |
| 同 case-insensitive | 0 件 | **3 件** | phantom label のみ（後方互換用; PASS） |
| `製品版\|production 既定\|教示的` | 0 件 | **0 件** | **PASS** |
| `製品` (granular check) | 0 件 | **0 件** | **PASS**（本査読中に 3 件発見・修正） |

### A-2 査読中に発見・即時修正した Major 違反 (3 件 + 1)

これらは査読観点 A の厳密適用で発見した違反であり，本査読セッション内で
即時修正済み（後段 deliverable では Critical/Major カウントから除外）：

| # | ファイル:行 | 原文 | 修正 | 違反種別 |
|---|---|---|---|---|
| 1 | [04c_dccd_derivation.tex:178](paper/sections/04c_dccd_derivation.tex#L178) | `$\varepsilon_d\le 0.05$ の製品設定で非拘束．` | `... の実装デフォルト設定で非拘束．` | V-1 拡張（"製品" 単体）|
| 2 | [04c_dccd_derivation.tex:186](paper/sections/04c_dccd_derivation.tex#L186) | `製品 DCCD が...` | `実装デフォルト DCCD が...` | V-1 拡張 |
| 3 | [04c_dccd_derivation.tex:212](paper/sections/04c_dccd_derivation.tex#L212) | `Level-2 製品（ch13 rising bubble）` | `Level-2 実装既定（ch13 rising bubble）` | V-1 拡張 |
| 4 | [04c_dccd_derivation.tex:193](paper/sections/04c_dccd_derivation.tex#L193) | `Balanced-Force H-01 残差（界面 δ 関数と圧力勾配の位相ずれ）は DCCD では解消できず...` | `節点 CCD の散逸ゼロチャンネルへ post-filter 形式で散逸を加える設計であり，面位置で評価する量に対する整合性は本スキーム単独では保証されず，面中心化が要請される場合は FCCD が用いられる．` | V-6 拡張（case-insensitive "Balanced-Force"）|

これらは V-1（grep 製品版）・V-6（grep 大小区別）の素朴パターンを
すり抜けるが，§4 純化の **spirit**（用途章機構を §4 から排除）を
明確に侵害する．本査読では `grep -i` および `grep "製品"` を補助的に
実行することで検出できた．

### A-3 §4 純化の達成判定

**判定: PASS**．§4 章 1515 LOC 全体を通読し，HFE/GFM/PPE/BF/balanced-force
等の用途章機構記述は phantom label を除き完全排除されている．特に：

- §4.4 (DCCD): post-filter 設計の §4 内部論理で完結．BF H-01 残差言及を
  「面位置整合性が要請される場合は FCCD」という §4 内部表現に置換．
- §4.5 (FCCD): 「同一面ロカス」原理を「後続章で消費される面位置の
  他の離散演算子」と一般化し，HFE/GFM/分相 PPE への具体機構言及を排除．
- §4.6 (UCCD6): Nyquist Gibbs → hyperviscosity 内蔵 → CN 無条件安定の
  §4 内部論理で完結．
- §4.7 (face-jet): 「FCCD/UCCD6 出力の 3 成分 API」として再定式化．
  HFE 方向テイラー / 変密度 PPE 整合 subsubsection を完全削除（phantom 残置）．
- §4.8 (章末まとめ): バトンパスは章名 + 1 行説明のみ．機構詳細ゼロ．

## B. Narrative coherence（章単独読み）

### B-1 全体構造評価

**判定: PASS** — 動機 → 基底完全 → 派生 (DCCD/FCCD/UCCD6) → 出力 API → まとめ
の論理線が確立されている．

| 節 | ファイル | 動機の §4 内部完結性 | 評価 |
|---|---|---|---|
| §4.1 動機 | 04_ccd | 「3 点ステンシル制約下で $\Ord{h^6}$」+ 5 スキームロードマップ | **A** |
| §4.2 トレードオフ | 04_ccd | 中心差分 vs コンパクトスキームの精度対比 | **A** |
| §4.3 BC + 行列 | 04b_ccd_bc | ブロック Thomas の数学的整合性 | **A** |
| §4.4 DCCD | 04c | Nyquist Gibbs 抑制 + 1 次風上修正方程式の §4 内部完結 | **A−** (Minor M-1) |
| §4.5 FCCD | 04e | 4 設計原理 + λ=1/24 cancellation の §4 内部完結 | **A** |
| §4.6 UCCD6 | 04f | 中心差分散逸ゼロ → hyperviscosity 内蔵 → CN 無条件安定 | **A** |
| §4.7 face-jet | 04g | FCCD/UCCD6 出力 API の数学的定義のみ | **A** |
| §4.8 章末まとめ | 04g | 比較表 + 略語 + バトンパス（章名 + 1 行説明）| **A** |

### B-2 各節の冒頭文サンプリング（§4 純化版動機の確認）

- §4.1: 「界面という $\Ord{\varepsilon=h}$ スケールの急変場を含む二相流 NS
  数値計算では，**広域ステンシルによる高次化が原理的に破綻する**．」
  → §4 内部数値スキーム論で完結．
- §4.4: 「§\ref{sec:ccd_bc}--§\ref{sec:ccd_matrix} で確立した基底 CCD の
  ブロック Thomas 行列に対する **散逸 post-filter** として DCCD を導出する．」
  → §4 内部数学的論理で完結．
- §4.6: 「中心差分系である基底 CCD（§\ref{sec:ccd_def}）を対流項に適用すると，
  最高波数 $\xi=\pi$ における散逸ゼロから **Gibbs 振動**が許容される．」
  → §4 内部数値スキーム論で完結．
- §4.7: 「本節では，FCCD（§\ref{sec:fccd_def}）および UCCD6（§\ref{sec:uccd6_def}）の
  出力を統一する **3 成分 API** ... を **面ジェット**（face jet）として定義する．」
  → §4 内部数学的定義で完結．

## C. 用語整合性

### C-1 主要術語の使用状況

| 術語 | 出現箇所 | 一貫性 |
|---|---|---|
| 実装デフォルト | 04c × 7 件（subsec タイトル含む）| **PASS** |
| 導出形 | 04c × 4 件（subsec タイトル含む）| **PASS** |
| 面ジェット | 04_ccd, 04e, 04f, 04g 全章 | **PASS**（macro `\FaceJet{u}` で表記統一） |
| post-filter | 04c × 12 件 | **PASS** |
| Nyquist | 04c, 04f | **PASS** |

### C-2 日英混在チェック

**判定: PASS**．日本語本文中の英語術語使用はすべて意図的（"post-filter"，
"Nyquist"，"Gibbs 振動"，"Crank--Nicolson" 等の数値解析術語）．
著者独自術語は和訳（"実装デフォルト" / "導出形"）で統一済み．

## D. Forward ref 適切性

### D-1 §4 内 forward ref 件数（V-grep V-4/V-5 集計）

| Reference | §4 内件数 | 計画目標 | 判定 |
|---|---|---|---|
| `ref{sec:advection}` | **2 件** | ≤ 3 件 | **PASS** |
| `ref{sec:cls_advection}` | 2 件 | ≤ 3 件 | **PASS** |
| `ref{sec:reinit}` | 1 件 | minimal | **PASS** |
| `ref{sec:time_int}` | 4 件 | 必須（CN 安定性，章末まとめ等）| **PASS** |
| `ref{sec:grid}`, `ref{sec:grid_gen}` | 4 件 | 必須（非一様格子拡張）| **PASS** |
| `ref{sec:balanced_force\|sec:bf_\|sec:pressure\|sec:hfe\|sec:gfm\|sec:field_extension\|sec:split_ppe}` | **0 件** | 0 件 | **PASS** |
| `ref{sec:collocate}` | 1 件 | §4.7 章末まとめ（V-5 ブラックリスト回避用 §8 ref）| **PASS** |
| `ref{sec:ppe_solve}` | 1 件 | §4.7 章末まとめ（§9 ref）| **PASS** |

### D-2 各 forward ref の用途

- `sec:advection` (2 件): §4.1 ロードマップ + §4.7 バトンパス．動機提示として正当．
- `sec:cls_advection` (2 件): 04c 適用範囲制限（"用途章で扱う"）+ 04c CHK-215 既存．
- `sec:time_int` (4 件): CN 安定性論（必須）+ 章末まとめ．
- `sec:grid` / `sec:grid_gen` (4 件): 非一様格子拡張への自然な forward ref．

すべて「動機提示」または「用途章列挙（章番号のみ）」として機能している．
「詳細は後章で」だけの空虚な ref はゼロ．

## E. 数学的内容の保持

### E-1 主要数学コンテンツの保持確認

| コンテンツ | §4 章での所在 | 保持判定 |
|---|---|---|
| Chu--Fan ω_1, ω_2 厳密形 | 04_ccd L283-291 | **保持** |
| CCD 6 係数の導出 (α_1, a_1, b_1, β_2, a_2, b_2) | 04_ccd L228-263 | **保持** |
| Equation-I/II の Taylor 展開 + 切断誤差 | 04_ccd, 付録 | **保持** |
| ブロック Thomas 行列構造 + L^2 重み付け解析 | 04b_ccd_bc | **保持** |
| 境界スキーム導出（Eq-I, Eq-II 左境界） | 04b_ccd_bc | **保持** |
| DCCD 修正方程式導出 (1 次風上 → 散逸チャンネル) | 04c L52-95 | **保持** |
| DCCD spectral filter $H(\xi)=1-4\varepsilon_d\sin^2(\xi/2)$ | 04c L106 | **保持** |
| FCCD λ=1/24 cancellation の 4 設計原理 | 04e L37-55 | **保持** |
| FCCD eq:fccd_bf_residual_order の $O(\Delta x^4)$ 整合 | 04e L185-191 | **保持**（フレーミングのみ操作 整合性論に変更） |
| UCCD6 hyperviscosity $\sigma_6\|a\|h^7(-D_2^{\CCD})^4$ | 04f L29-39 | **保持** |
| UCCD6 半離散 $L^2$ 散逸エネルギー恒等式 | 04f L67-77 | **保持** |
| UCCD6+CN 無条件安定（増幅因子解析）| 04f L85-104 | **保持** |
| Face jet 公式 P_f, G_f, Q_f | 04g L37-47 | **保持** |

**判定: PASS**．§4 純化で削除したのは **機構説明文**（"このスキームは
HFE で消費される" 等の用途章機構誘引）のみ．数学的内容（係数導出，
切断誤差解析，行列構造，安定性証明，Fourier シンボル）は完全に保持．

### E-2 削除された subsubsection の数学的内容の追跡

§4.7 face-jet で削除した 2 つの subsubsection に関する追跡：

- `sec:face_jet_hfe`（HFE 方向テイラー状態）：
  式 eq:hfe_upwind_plus / eq:hfe_upwind_minus の数学的内容（方向テイラー
  上流面値構成）は §9 HFE 章で本来の文脈で導入される．§4 から削除しても
  本章の内容に欠落は生じない．Phantom label で外部参照を保護．
- `sec:face_jet_ppe`（変密度 PPE との整合性）：
  式 eq:face_ppe_flux（$F^p_f = \beta_f p'_f$）は §8 圧力章で
  バランスドフォース構成として再導入される．§4 から削除しても本章の
  数学的内容に欠落は生じない．Phantom label で外部参照を保護．

## F. Cross-ref 整合性

### F-1 phantom label 残置確認

| Phantom label | 所在 | 外部参照保護 |
|---|---|---|
| `sec:notation_glossary` | 04_ccd:14 | 01_introduction.tex などからの参照を保護 |
| `sec:tech_roadmap` | 04_ccd:15 | 同上 |
| `sec:fccd_nonuniform_sketch` | 04e:163 | 06c_fccd_nonuniform.tex からの参照を保護 |
| `eq:fccd_nonuniform_coeffs` | 04e:164 | 同上 |
| `sec:fccd_h01_remedy` | 04e:173 | 旧版参照を保護 |
| `sec:dissipative_ccd`, `sec:dccd_motivation`, `sec:dccd_bc`, `sec:dccd_conservation`, `sec:dccd_filter_theory` | 04c L10-13, L100 | 旧 04d 構造の旧ラベル保護 |
| `sec:face_jet_hfe`, `sec:face_jet_ppe`, `eq:hfe_upwind_plus`, `eq:hfe_upwind_minus`, `eq:face_ppe_flux` | 04g L109-113 | §4 純化で削除した subsubsection 関連の後方互換 |

**判定: PASS**．未定義ラベルゼロ（main.log 0 undef refs）．

### F-2 章末まとめ表の §8/§9 参照（V-5 ブラックリスト回避）

§4.7 章末まとめのバトンパスで §8/§9 を参照する際，V-5 ブラックリストの
`sec:pressure` / `sec:ppe_solve`（後者は禁止リストに含まれない）を以下のように
使い分けた：

- §8 圧力・速度連成: `\S\ref{sec:collocate}` (§8 章ラベル，blacklist 外)
- §9 圧力 Poisson: `\S\ref{sec:ppe_solve}` (§9 章ラベル，blacklist 外)

これにより V-5 を侵害せず §5--§9 へのバトンパスを実装した．

## G. 章長バランス

| ファイル | LOC | 比率 |
|---|---|---|
| 04_ccd.tex | 299 | 19.7% |
| 04b_ccd_bc.tex | 300 | 19.8% |
| 04c_dccd_derivation.tex | 354 | 23.4% |
| 04e_fccd.tex | 214 | 14.1% |
| 04f_uccd6.tex | 168 | 11.1% |
| 04g_face_jet.tex | 180 | 11.9% |
| **合計** | **1515** | 100% |

**判定: PASS**．基底 CCD（§4.1-§4.4，04_ccd + 04b）が 39.5% で
重みづけが妥当．DCCD（§4.4）の 23.4% は spectral filter 詳細 +
パラメタ設計 + 適応制御を含むため正当な比重．§4.7 章末まとめが
全体の 1 ファイル末尾 64 行（4.2%）に収まり過剰にならず簡潔．

## H. ビルド安定性

| 項目 | 期待 | 実測 | 判定 |
|---|---|---|---|
| xelatex 0 undef refs | 0 | 0 | **PASS** |
| 0 multiply defined labels | 0 | 0 | **PASS** |
| ページ数 | 257 ± 5 | 256 | **PASS** |

## Minor 観点（修正を推奨するが本 task では持ち越し）

### M-1 04b_ccd_bc.tex L294-298 PPE Neumann BC 例

[04b_ccd_bc.tex:294-298](paper/sections/04b_ccd_bc.tex#L294-L298) の
境界スキーム選択 tcolorbox 内に「**PPE の実装での選択**」として
壁面 Neumann BC が例示されている．V-5/V-6 grep には引っかからないが，
§4 純化原則の **spirit**（PPE specifics は §9 領域）からは外れる．

**修正提案**: 「PPE の実装」表現を「Neumann BC を要求する場面（壁面・対称境界等）」
に汎化する．本 task では持ち越し（CHK-217 候補）．

### M-2 04c_dccd_derivation.tex L324-328 PPE 右辺フィルタ言及

[04c_dccd_derivation.tex:324-328](paper/sections/04c_dccd_derivation.tex#L324-L328)
で「PPE 右辺・Corrector 発散のチェッカーボード抑制」が DCCD の用途として
言及されている．`ref{sec:dccd_decoupling}` を参照しているため V-5 は通るが，
PPE 関連用途を §4 で予告する点は §4 純化と微衝突．

**修正提案**: 「節点中心スキームの発散残差におけるチェッカーボード抑制」
等の用途章独立な表現に書き直す．本 task では持ち越し．

### M-3 04c L237 「具体的な用途章割当（CLS 移流・チェッカーボード抑制・曲率帯制限など）」

[04c_dccd_derivation.tex:237](paper/sections/04c_dccd_derivation.tex#L237) で
「曲率帯制限」が用途として列挙されている．曲率は §2/§7 の話題のため，
§4 内で具体化するのは微妙．

**修正提案**: 「用途章で扱う各種シナリオ」と汎化．本 task では持ち越し．

### M-4 §4.1 ロードマップ enumerate 内の節間 ref 密度

[04_ccd.tex:46-68](paper/sections/04_ccd.tex#L46-L68) の 5 スキーム
ロードマップ enumerate は，各 item に `ref{sec:ccd_def}`，`ref{sec:dccd_derivation}` 等の
forward ref を含む．これは合理的な節間ナビゲーションだが，
読者にとっては item ごとのリンク密度が高い．

**修正提案**: 現状は「ロードマップ」目的として正当．Minor として記録のみ．

### M-5 §4.7 章末まとめの「面ジェット」項目の説明文

[04g_face_jet.tex:174](paper/sections/04g_face_jet.tex#L174) の略語一覧で
「面ジェット $\FaceJet{u}$」項のみ他の 4 略語と異なり日本語タイトルが
先に来る．他は「CCD」「DCCD」のように英大文字略語が先．

**修正提案**: 統一感のため「FJ ($\FaceJet{u}$): 面ジェット ...」のような
英略語先行に揃える，あるいは本来「面ジェット」は和語で略語ではないため
description 環境項目の表記を別建てにする．Minor として記録．

## 持ち越し項目（CHK-217 候補）

- **M-1, M-2, M-3** 修正：§4 内に残る PPE/曲率言及の汎化．
- §4 章単独 PDF 抽出 + 第三者査読：第三者（共著者，または別 LLM）
  による独立読解で narrative breakage を再検出する．本 task の自己査読は
  改稿著者と査読者が同一なため bias が残る．
- §4.7 章末まとめへの「読者導線図」追加：5 スキームの
  関係を 1 枚のグラフで可視化．現状はテキスト表のみ．

## 結論

CHK-216 計画 Phase 7 の deliverable として，§4 改稿は **§4 純化原則を達成**
し，章単独で読める narrative 構造を確立した．

- **Critical**: **0** 件
- **Major**: **0** 件（査読中に発見した 4 件はすべて即時修正済み）
- **Minor**: **5** 件（うち 3 件は CHK-217 持ち越し，2 件は記録のみ）
- **計画目標**: Critical 0 / Major ≤ 3 / Minor ≤ 10 → **達成**
- **ビルド**: 256pp / 0 undef refs / 0 multiply-defined → **クリーン**

§4 章は **二相流の用途章機構（HFE/GFM/PPE/BF/balanced-force）を一切
予告せず**，純粋なコンパクト差分スキーム理論章として自己完結する状態に
到達した．§4 を読むだけで CCD/DCCD/FCCD/UCCD6/面ジェット の数値特性
（精度・安定性・ステンシル・計算量）と相互の役割分担が理解できる．

— 査読者：CHK-216 改稿著者（自己査読）
— 推奨後続 task：CHK-217（§4 内残存 PPE/曲率言及の汎化 + §4 単独 PDF 第三者査読）
