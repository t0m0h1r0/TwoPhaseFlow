# CHK-227 査読メモ: §9 圧力 Poisson / 分相 PPE / HFE / DC / BC / 精度まとめ

**status**: REVIEW_ONLY (paper 編集は CHK-228 候補として後続)
**date**: 2026-04-27
**reviewer**: ResearchArchitect agent (査読官スタンス)
**scope**: `paper/sections/09_ccd_poisson.tex`, `09b_split_ppe.tex`, `09c_hfe.tex`, `09d_defect_correction.tex`, `09e_ppe_bc.tex`, `09f_pressure_summary.tex` (計 6 ファイル / 1,455 LOC)

**ユーザ事前懸念**:
1. YAML 記法 / 実装の話混入 — 論文趣旨外
2. §9.6.1 が実験結果を理論章に記載 — 違和感 (理論的厳密理屈があるなら別)
3. §9.7 「精度バランス + 設計上のトレードオフ」 — 章末配置が違和感
4. FVM 言及 — UCCD/FCCD 移行で陳腐化したのではないか

---

## Section A: 査読官スタンスと総合判定

### A-1. 章の理論的価値 — 高い

§9 前半 ([09_ccd_poisson.tex](paper/sections/09_ccd_poisson.tex), [09b_split_ppe.tex](paper/sections/09b_split_ppe.tex), [09c_hfe.tex](paper/sections/09c_hfe.tex), [09d_defect_correction.tex](paper/sections/09d_defect_correction.tex)) は「変密度 PPE 演算子の行列構造 → 分相 PPE 定式化 → HFE 場延長 → DC 高次反復」という教科書的体系を踏んでおり, 理論的厳密性は高い. 特に [09b_split_ppe.tex:131-150](paper/sections/09b_split_ppe.tex#L131-L150) の「純 FCCD 分相 PPE アーキテクチャ」設計選択論と [09b_split_ppe.tex:382-403](paper/sections/09b_split_ppe.tex#L382-L403) の「圧力ジャンプ形式によるクリーン分離」は本稿の中核理論貢献.

### A-2. 章 narrative arc 評価

| ファイル | 推定 §番号 | 役割 | 査読判定 |
|---|---|---|---|
| `09_ccd_poisson.tex` | §9.1-9.2 | 行列構造 + Balanced-Force + FVM 比較 | borderline OK |
| `09b_split_ppe.tex` | §9.3 | 分相 PPE 導出 + 純 FCCD アーキ | NG (YAML 漏出 1 箇所) |
| `09c_hfe.tex` | §9.4 | HFE 定式化 | OK |
| `09d_defect_correction.tex` | §9.5 | DC 法 + 収束保証 | OK |
| `09e_ppe_bc.tex` | §9.6 | BC + 安定化 + Option III/IV | borderline NG |
| `09f_pressure_summary.tex` | §9.7 | 精度まとめ + 設計トレードオフ | NG |

§9.1-9.5 は理論として概ね妥当. **§9.6-9.7 が理論章を逸脱**しており, ユーザの 4 件懸念はすべてこの後半 2 ファイル + §9b 1 箇所に集中している.

### A-3. 総合判定 — **major revision** 推奨

理論内容の保持価値は高いが, (1) YAML/実装漏出, (2) 観察ベース主張の理論章混入, (3) 章末への design rationale 配置, (4) FVM の framing 不整合 — の 4 軸で構造的修正が必要. **rejection ではなく revise** だが, 単純な wording 修正では収束しない (章 boundary 整理が必要).

---

## Section B: 懸念 1 (YAML 記法 / 実装の話) の所見

### B-1. YAML セマンティクス節 — 削除候補 (確証あり)

[09b_split_ppe.tex:405-414](paper/sections/09b_split_ppe.tex#L405-L414) に **YAML セマンティクス** という見出しで以下 4 件の YAML キーが直接記述されている:

```text
operator.coefficient = phase_separated
operator.interface_coupling = jump_decomposition
surface_tension.formulation = pressure_jump
surface_tension.gradient = none
```

これは config file の key=value 形式そのものであり, **論文ではなく実装ドキュメント**の記述形式. 直前 L382-403 の「圧力ジャンプ形式：CSF 体積力を回避するクリーン分離」(`sec:split_ppe_pressure_jump_formulation`) は理論記述として valid だが, その直後 L405 から実装セマンティクスに突如 drift する.

### B-2. ランタイム診断テーブル — 削除候補

[09b_split_ppe.tex:416-432](paper/sections/09b_split_ppe.tex#L416-L432) に「ランタイム診断」というタイトルで 6 件の診断キー (`ppe_phase_count`, `ppe_pin_count`, `ppe_mean_gauge`, `ppe_rhs_phase_mean_before_max`, `ppe_rhs_phase_mean_after_max`, `ppe_interface_coupling_jump`) を tabular で列挙し, 末尾に「これにより P-2 / P-3 / P-4 の実装上の破綻を step 単位で検出できる」(L431-432). これも実装/運用ガイドであり論文に置く理由がない.

### B-3. 配置論

両者とも 1 つの subsubsection (`sec:split_ppe_pressure_jump_formulation`) の末尾 28 LOC を占めており, **削除しても理論導出 (圧力ジャンプ形式) の論理構造には影響しない**. むしろ削除することで理論章の clean termination が回復する.

### B-4. 同種漏出の他章スキャン (negative finding)

§9 全 6 ファイルで `formulation:`, `coefficient:`, `interface_coupling:` 等の YAML キーを grep した結果, **`09b:405-414` 1 箇所のみ**. Python class 名 (`SplitPPE`, `PressureProjector` 等), `experiment/ch13` パス, `.yaml` ファイル名は §9 全体で検出ゼロ. つまり懸念 1 は **isolated 1 箇所の局所修正で完全解消**できる (CHK-222 の §5/§6 大規模 deprecation とは規模が違う).

### B-5. B 結論

- **B-削除候補 1**: [09b_split_ppe.tex:405-432](paper/sections/09b_split_ppe.tex#L405-L432) (28 LOC) — YAML セマンティクス + ランタイム診断
- **影響範囲**: 当該節への外部 ref ゼロ (sec:split_ppe_pressure_jump_formulation 自体は維持; 内部 28 LOC 削除のみ)
- **代替**: 必要なら付録 (`app:impl_yaml`) または `docs/wiki/code/WIKI-L-*` へ移管

---

## Section C: 懸念 2 (§9.6.1 実験結果が理論章に記載) の所見

### C-1. §9.6.1 の正体

[09e_ppe_bc.tex:21-69](paper/sections/09e_ppe_bc.tex#L21-L69) `\subsubsection{高密度比における条件数と数値安定性}` (label `sec:ppe_condition_number`). 49 LOC.

内容は 3 ブロックに分解できる:

| ブロック | 行範囲 | 内容 | 性格 |
|---|---|---|---|
| C-1a | L24-25 | ρ_l/ρ_g ≈ 10^3 (水/空気相当) — 物性値 | 理論 (前提条件) |
| C-1b | L26-32 | 「DC 反復が発散」「精度 plateau」 | **観察的** (証明なし; `sec:varrho_ppe_limitation` 参照のみ) |
| C-1c | L36-44 | 条件数式 κ(L_h) = O(ρ_l/ρ_g · 1/h²) ≈ O(10³/h²) — `eq:ppe_cond_number` | 理論 (純粋な漸近解析) |
| C-1d | L46-69 | 安定化戦略 3 件 (フェイス係数 / 分相 PPE / ピン対称性) | design rationale |

### C-2. 査読官観点 — 「実験結果」の正体

ユーザが感じた「実験結果」は実体としては **C-1b の観察的主張**:

> 「変密度 PPE 自体が ρ_l/ρ_g ≥ 10 で **DC 反復が発散** (divergent residual) するか, 反復が形式収束する場合でも **精度が O(1) 付近で plateau** する本質的問題が存在する」 ([09e_ppe_bc.tex:27-29](paper/sections/09e_ppe_bc.tex#L27-L29))

これは **数値実験で観察される現象**であり, §9.6.1 内で定理 / 証明 / 漸近解析として導出されていない. 唯一の根拠は別節 `sec:varrho_ppe_limitation` への forward reference. つまり「現象を主張するが根拠は別所」という構造.

純粋な theory 章としては:
- (i) この観察を **lemma + proof** として §9.6.1 内で完結させる, または
- (ii) この観察を **§11 (verification 章)** へ移し, §9 では「§11 で示されるように」と一行参照する

のいずれかが期待される. 現状はどちらでもない.

### C-3. 数値実験データ (table, %, error metric) は §9.6.1 内に存在しない

`agent A` および本査読の精読により, §9.6.1 (49 LOC) 内に具体的数値結果 (収束率 table, 体積保存誤差 %, L2 ノルム値, benchmark 結果) は **検出ゼロ**. ユーザの「実験結果」直観は厳密には数値データではなく, 上述 C-2 の **観察ベース主張** に向けられたもの.

### C-4. 本当の「実験結果記載」は §9.6.1 ではなく §9.7

実は数値実験への依存をより強く self-document している箇所は §9.7 = `09f_pressure_summary.tex` であり (Section D で詳述), 特に:

> 「Lv.2 の理論証明は §`sec:dc_accuracy` の理想化条件 (等密度・均一格子・周期 BC) 外なので, **DC convergence は本稿では実測値として扱う**」 ([09f_pressure_summary.tex:48](paper/sections/09f_pressure_summary.tex#L48))

ここに「実測値として扱う」と明記されており, **理論章内に実験的主張が存在することを著者自身が認めている**. これは査読上の重大な指摘点.

### C-5. §9.6.1 内の Option III/IV menu (L105-168) との結合

§9.6.1 (L21-69) は条件数 + 安定化戦略, §9.6.4 = `sec:fccd_bc_options` (L105-168) は Option I/II/III/IV menu + 採用根拠 + 実装手順. 後者は明確に **設計判断 menu + 実装ガイド** であり, 理論章としては逸脱. ただしユーザは特に §9.6.1 を指摘したため §9.6.4 は「同種の構造的問題」として併記する程度に留める.

### C-6. C 結論

- **C-修正候補 1**: [09e_ppe_bc.tex:26-32](paper/sections/09e_ppe_bc.tex#L26-L32) の「DC 反復が発散」「精度 plateau」観察 → (a) §9.6.1 内で proof 補強 / (b) §11 verification へ pointer 化 / (c) 削除
- **C-修正候補 2**: [09e_ppe_bc.tex:46-69](paper/sections/09e_ppe_bc.tex#L46-L69) 「安定化戦略」3 件 → design rationale なので §10 (algorithm 章) または §11 (verification) へ移管検討
- **C-修正候補 3**: [09e_ppe_bc.tex:105-168](paper/sections/09e_ppe_bc.tex#L105-L168) Option III/IV menu → 付録 (`app:bc_options`) 化または §10 (algorithm) へ移管検討

---

## Section D: 懸念 3 (§9.7 精度バランス + 設計上のトレードオフ) の所見

### D-1. §9.7 の正体 — `09f_pressure_summary.tex` 単一ファイル (123 LOC)

[09f_pressure_summary.tex:7-9](paper/sections/09f_pressure_summary.tex#L7-L9):

```latex
\subsection{本章のまとめ：精度バランスと設計上のトレードオフ}
\label{sec:pressure_accuracy_summary}
```

タイトル自体に「設計上のトレードオフ」と明記されており, **self-describe で design rationale を宣言している**. 理論章末尾としては異質.

### D-2. ファイル冒頭コメントが配置混乱を物語る

[09f_pressure_summary.tex:1-5](paper/sections/09f_pressure_summary.tex#L1-L5):

```text
% paper/sections/09f_pressure_summary.tex
%
% §8 章末まとめ：精度バランスと設計上のトレードオフ
% ※ 旧所在: 09_ccd_poisson.tex 内 → §8 章末に移動
%   理由：HFE（§8.4）・BC（§8.6）を全て読んだ後に精度全体像を示す構成に変更
```

このファイルは **「§8 章末まとめ」として設計**されたが, 現在は §9 ファイル群に配置されている. CHK-225 (file prefix b-style 統一) の章番号 ripple で §9 配下に slot されたものの, 本来の意図 (§8 まとめ) と現実配置 (§9 まとめ) のずれがコメントに残置. これは **章境界 redesign の証拠**.

### D-3. tab:accuracy_summary — self-documenting NG 注 2 件

[09f_pressure_summary.tex:19-58](paper/sections/09f_pressure_summary.tex#L19-L58) `tab:accuracy_summary` は CLS 移流 / PPE Lv.1/Lv.2/Lv.3 / NS 粘性 / 対流 / Projection / HFE の 8 行 × 空間精度 + 時間精度 の 10 行精度比較表. これ自体は理論章の summary として OK だが, 注釈 2 件が問題:

- **L48 注 ‡‡**: 「Lv.2 の理論証明は §`sec:dc_accuracy` の理想化条件 (等密度・均一格子・周期 BC) 外なので, **DC convergence は本稿では実測値として扱う**」 — 著者自身が「理論章内に実測値依拠の主張」を認めている
- **L49 注 ‡‡‡**: 「Lv.3 分相 PPE + DC k≥3 では各相内 O(h⁷) (Dirichlet 超収束) / O(h⁵) (Neumann BC 律速) を密度比に直接依存しない形で達成 (§`sec:verify_split_ppe_dc`)」 — verification 章への forward reference に依存

→ これらは ユーザ懸念 2 (実験結果の理論章混入) の最も明確な evidence.

### D-4. tcolorbox 2 件 = design rationale

- [09f_pressure_summary.tex:60-74](paper/sections/09f_pressure_summary.tex#L60-L74) `warnbox{精度ミスマッチと設計上のトレードオフ}` (15 LOC) — 空間/時間精度のトレードオフ警告
- [09f_pressure_summary.tex:76-117](paper/sections/09f_pressure_summary.tex#L76-L117) `mybox{設計選択の根拠：分相 PPE + DC + CCD 勾配の統合設計}` (42 LOC; `box:ppe_design_rationale`) — 「2 経路切替」「BF 整合性」「疎行列直接法」3 原則の説明

両者ともタイトルから明らかに **design rationale / 設計判断書** であり, 理論導出ではない. 章末尾に置くのは読者に「この章は設計判断書である」と再印象付けることになり, 理論章としては逆効果.

### D-5. GPU-native FVM 注記と main.tex L77 コメントの矛盾

[09f_pressure_summary.tex:119-123](paper/sections/09f_pressure_summary.tex#L119-L123):

> 「Level 2 プロダクションでの 2 経路選択 (変密度一括 smoothed-Heaviside PPE vs **GPU-native FVM 経路**; 同精度・性能差のみ) は §`sec:level_gpu_dual_path` に集約. 付録 `app:gpu_fvm` に実装詳細を記す」

しかし `paper/main.tex:77` のコメントは:

```text
\input{sections/09f_pressure_summary}  %% §9 のまとめ（GPU-native FVM 詳細は付録 H へ移動）
```

「FVM 詳細は付録 H に移動済」と認識されているが, 09f L119-123 は **本文中で「経路名」として FVM を依然 production option として presented**. これは section E (FVM 言及) で詳述する.

### D-6. 章末尾構造異常

純粋な理論章であれば章末尾は (a) 結論 / (b) 次章への bridge / (c) 章内で導出した primary theorem の要約, のいずれかであるべき. §9.7 (09f) は (a) 部分的にあるが (本文 L11-17 で各節 recap), (b) 不在, (c) 表で代用; 代わりに **設計判断 menu + 実装注記** が大半を占める.

### D-7. D 結論

- **D-修正候補 1**: [09f_pressure_summary.tex:48-49](paper/sections/09f_pressure_summary.tex#L48-L49) 注 ‡‡ ‡‡‡ の wording を「§11 verification で実測される」に置換
- **D-修正候補 2**: [09f_pressure_summary.tex:60-117](paper/sections/09f_pressure_summary.tex#L60-L117) tcolorbox 2 件 → §10 algorithm 章 (sec:design_rationale) または §11 verification (実測ベース trade-off) へ移管
- **D-修正候補 3**: [09f_pressure_summary.tex:119-123](paper/sections/09f_pressure_summary.tex#L119-L123) GPU-native FVM 注記 → §10 (production stack 説明) または §15 (conclusion) へ移管
- **D-修正候補 4 (radical)**: 09f 全体を §9 から削除し, 必要部分を §10/§11/§15 へ分散. §9 末尾は §9d (DC 法) または §9e (BC) で自然に終結.

---

## Section E: 懸念 4 (FVM 言及残置と陳腐化整合性) の所見

### E-1. §9 内 FVM 言及 7 箇所の用途分類

| ファイル:行 | 文脈 | 用途分類 | 査読判定 |
|---|---|---|---|
| [09_ccd_poisson.tex:158](paper/sections/09_ccd_poisson.tex#L158) | tcolorbox title「FVM + CSF との比較」 | 比較 baseline | OK (CCD 採用根拠) |
| [09_ccd_poisson.tex:166](paper/sections/09_ccd_poisson.tex#L166) | 表内行「FVM + CSF + Rhie-Chow」 | 比較 baseline | OK |
| [09_ccd_poisson.tex:187-212](paper/sections/09_ccd_poisson.tex#L187-L212) | `sec:ccd_vs_fvm` 「空間離散化スキームの定量的比較」(`tab:ccd_vs_fvm`) | 比較 baseline (定量) | OK (理論的選択根拠) |
| [09b_split_ppe.tex:135-148](paper/sections/09b_split_ppe.tex#L135-L148) | 「FVM の制御体積保存を放棄」(純 FCCD アーキ) | 陳腐化 note 付き 比較 | OK (FCCD 採用の明示的対比) |
| [09e_ppe_bc.tex:13](paper/sections/09e_ppe_bc.tex#L13) | 「周期境界: FVM 行列に折り返しフェイス…組み込む」(`sec:fvm_periodic` 参照) | 現役 method 言及 | **borderline NG** (本文中で FVM 行列を BC 実装 path として retain) |
| [09e_ppe_bc.tex:18](paper/sections/09e_ppe_bc.tex#L18) | コメント「FVM PPE 周期 BC 対応は付録 fvm_periodic に移動」 | 移動記録 (コメント) | OK |
| [09e_ppe_bc.tex:49,57](paper/sections/09e_ppe_bc.tex#L49) | 「FVM フラックス連続性から自然に導かれるフェイス係数 a = 2/(ρ_L+ρ_R)」 | 物理的根拠 説明 | OK (係数の由来説明) |
| [09f_pressure_summary.tex:119-123](paper/sections/09f_pressure_summary.tex#L119-L123) | 「Level 2 プロダクション: 2 経路 (一括 PPE vs GPU-native FVM 経路)」 | 現役 production option 言及 | **NG** (CHK-226 で確認した production primary は分相 PPE = Level 3 = FVM 不在) |

### E-2. ユーザ「陳腐化」直観の検証 (CHK-226 production framing との整合)

CHK-226 (§8 BF-CCD 査読) で確認:
- ch13 production YAML (`ch13_capillary_water_air_*`, `ch13_rising_bubble_*`) は **`formulation: pressure_jump` + `coefficient: phase_separated`**
- これは §8.2 戦略 C = §9b 分相 PPE = §9.7 で言う **Lv.3** に相当
- Level 3 の path には FVM 不在 (FCCD face-jet のみ)

つまり **production primary では FVM は陳腐化済み**. ユーザの直観は正しい.

しかし §9 では:
- §9.7 (09f L78-80) で「Level 2 = 中程度密度比の主戦略」「Level 3 = 高密度比 + 低 We 同時成立」と書かれている
- Level 2 は default フォールバックとして提示されており, その内部で「変密度一括 PPE vs GPU-native FVM」の **2 経路 option** が提示される
- → **Level 2 fallback の 2 経路の 1 つとして FVM が retain されている** が, paper 全体の primary stack は Level 3 = 分相 PPE

### E-3. Framing 整理の必要性

§9 内で FVM が:
1. **比較 baseline** (CCD vs FVM の理論的優位性 demonstrate) — 4 箇所 (`09_ccd_poisson.tex:158, 166, 187-212`, `09b:135-148`) — **適切で削除非推奨**
2. **物理的根拠 anchor** (FVM フラックス連続性が a_f = 2/(ρ_L+ρ_R) の由来) — 2 箇所 (`09e:49, 57`) — **適切**
3. **現役 production fallback path** (`09f:119-123` Level 2 GPU-native FVM 経路) — **要 framing 整理** (production primary は分相 PPE; FVM は Level 2 fallback の 1 option)
4. **BC 実装 path** (`09e:13` 周期 BC で FVM 行列参照) — **borderline; 付録 fvm_periodic に移動済み実装の本文 ref**

### E-4. E 結論

- **E-修正候補 1**: [09f_pressure_summary.tex:119-123](paper/sections/09f_pressure_summary.tex#L119-L123) GPU-native FVM 経路言及 → 「Level 2 fallback の 1 option」と明記し, 「production primary (Level 3) は分相 PPE + FCCD face-jet」と framing
- **E-修正候補 2**: [09e_ppe_bc.tex:13](paper/sections/09e_ppe_bc.tex#L13) 周期 BC FVM 行列 ref → 付録誘導のみに圧縮 ("詳細は付録 fvm_periodic")
- **E-修正候補 3**: 比較 baseline (3 箇所) と物理的根拠 (2 箇所) の FVM 言及は **保持** (理論的選択根拠として valid)

---

## Section F: 懸念間 coupling

### F-1. §9.6.1 + §9.7 の coupling

両者とも「実測値依拠の主張」を含む:
- §9.6.1 (`09e:27-32`) 「DC 反復が発散」「精度 plateau」 — 観察ベース
- §9.7 (`09f:48`) 「DC convergence は本稿では実測値として扱う」 — self-documenting

→ 両者を同時に修正することで「実測値依拠の主張は §11 verification 章へ集約」という統一的解決が可能.

### F-2. §9.7 + 懸念 1 (YAML) の coupling

両者とも「実装メモ性格」:
- §9.7 (`09f:60-117`) tcolorbox 2 件 = design rationale
- 懸念 1 (`09b:405-432`) YAML/diagnostic = implementation memo

→ 両者を「§10 algorithm 章への移管 + §9 は理論導出に専念」という方針で統一的に解決可能.

### F-3. §9.7 + 懸念 4 (FVM) の coupling

§9.7 (`09f:119-123`) の GPU-native FVM 経路言及は **§9.7 の design rationale 性格**と **FVM の framing 不整合**を同時に体現. §9.7 を §10 へ移管すれば自動的に解決.

### F-4. 懸念 1+2+3 統合 — 「§9 後半は理論章ではなく algorithm 章 / verification 章である」

3 件の懸念は同根: **§9.6 後半 + §9.7 全体は実装/設計/検証の混合章**であり, §9 (理論章) 末尾に置く構造的妥当性が薄い. ユーザの 4 懸念は表層的には独立だが, 章境界の再設計で **同時に解決可能**.

---

## Section G: §9 全体 narrative arc 評価

### G-1. 6 ファイルの役割マップ (再掲)

| ファイル | LOC | 内容性格 | 理論章としての適格性 |
|---|---|---|---|
| `09_ccd_poisson.tex` | 215 | 行列構造 + BF + FVM 比較 | OK (比較表は理論的根拠として正当) |
| `09b_split_ppe.tex` | 445 | 分相 PPE 導出 + 純 FCCD アーキ | OK 但し L405-432 (28 LOC) 削除推奨 |
| `09c_hfe.tex` | 296 | HFE 定式化 | OK |
| `09d_defect_correction.tex` | 208 | DC 法 + 収束保証 | OK |
| `09e_ppe_bc.tex` | 168 | BC + 安定化 + Option III/IV | borderline NG (L46-69, L105-168 = 100 LOC が design rationale) |
| `09f_pressure_summary.tex` | 123 | 精度まとめ + 設計トレードオフ + FVM 経路 | NG (全 123 LOC が summary + design rationale; 48% が design content) |

### G-2. 章 boundary の整理仮説

§9 を「**変密度 PPE 演算子の数学的定式化**」に純化するなら, §9 = §9.1 ([09_ccd_poisson](paper/sections/09_ccd_poisson.tex)) + §9.2 ([09b_split_ppe](paper/sections/09b_split_ppe.tex)) + §9.3 ([09c_hfe](paper/sections/09c_hfe.tex)) + §9.4 ([09d_defect_correction](paper/sections/09d_defect_correction.tex)) + §9.5 ([09e_ppe_bc.tex:5-19](paper/sections/09e_ppe_bc.tex#L5-L19) BC 概観 + L71-103 零モード + ピン点) で完結. その他は:
- `09b:405-432` (YAML/diagnostic) → 付録 / wiki
- `09e:46-69` (安定化戦略 3 件) → §10 algorithm
- `09e:105-168` (Option III/IV menu) → 付録 (`app:bc_options`) または §10
- `09f` (123 LOC 全体) → §10 (design rationale + production stack) または §11 (verification 章) または §15 (conclusion)

### G-3. CHK-226 (§8 査読) との比較

| 観点 | §8 (CHK-226) | §9 (本 CHK-227) |
|---|---|---|
| 主問題 | production stack との framing 乖離 (CSF vs phase-PPE) | YAML/実装漏出 + 後半 2 ファイルの理論章逸脱 |
| 主体的な構造再設計の必要性 | 高 (E-α/β/γ で全章再構成検討) | 中 (§9.1-9.5 は維持; §9.6-9.7 のみ整理) |
| user 確定方針 (CHK-226) | E-α minimal (CSF primary 維持) | — (本 CHK で判断) |
| 推奨 option の方向性 | minimal | moderate (§9 後半の 章境界整理) |

§8 と異なり §9 は **理論導出本体は健全** (§9.1-9.5 = ~1,200 LOC は OK) であり, 周辺 ~250 LOC の整理で大部分の懸念が解消する点が違い.

---

## Section H: 推奨される再構成 options (3 案)

| Option | 戦略 | 削除/移管対象 LOC | 外部 ref 影響 | リスク |
|---|---|---|---|---|
| **H-α** (minimal) | YAML 漏出のみ削除 (`09b:405-432`, 28 LOC) + `09e:26-32` の「発散/plateau」観察を `sec:varrho_ppe_limitation` への単純 pointer に圧縮 + `09f:48-49` 注記 wording を「§11 verification で実測される」に置換 | -28 LOC (YAML), -7 LOC (観察 → pointer), 0 (注記改良のみ) | 0 件 (label 不変) | 低; 構造的乖離は残る (Option menu, design rationale, FVM framing は維持) |
| **H-β** (moderate) | H-α + (a) `09e:46-69` 安定化戦略 → §10 algorithm 章へ移管; (b) `09e:105-168` Option III/IV menu → 付録 `app:bc_options` 化; (c) `09f` tcolorbox 2 件 (60-117) → §10 design rationale section へ移管; (d) `09f:119-123` FVM 経路注記 → §10 production stack section へ移管. `tab:accuracy_summary` は §9 末尾に summary table として残置 (注記改良のみ). | -100 LOC (§9), +100 LOC (§10/付録) | 中 (`sec:fccd_bc_options`, `box:ppe_design_rationale`, `sec:level_gpu_dual_path` の参照側調整 ~5-7 件; alias で backward-compat 可) | 中; §9 が clean な理論章になる |
| **H-γ** (radical) | H-β + 09f を完全廃止, `tab:accuracy_summary` も §10 (algorithm 完全像) または §11 (verification) へ移管. §9 は §9d (DC 法) または §9e (BC; Neumann/ピン点のみ) で自然終結. §9 LOC 1,455 → ~1,150 LOC. 章タイトルも「圧力 Poisson 方程式の解法と分相 PPE」のような純理論名へ整理. | -300 LOC (§9), +250 LOC (§10/§11) | 高 (`sec:pressure_accuracy_summary` 外部 ref ~7 件, `sec:ppe_bc_stability` 外部 ref ~3 件 alias 必須; chapter intro [09_ccd_poisson.tex:7](paper/sections/09_ccd_poisson.tex#L7) `sec:ppe_solve` の章 boundary 再宣言) | 高; ただし §9 は paper 中の数学的中核として完全 clean |

---

## Section I: User 判断要請

memo 末尾で 3 つの question を user に提示:

### Q1: 懸念 1 (YAML 記法 `09b:405-432`) の処理
- **(a)** 即削除 (28 LOC; 影響なし) — H-α/β/γ 共通
- **(b)** 付録 `app:impl_yaml` へ移管 (理論章から切り離すが論文内に残置)
- **(c)** 残置 (現状維持)

### Q2: 懸念 2 (§9.6.1 観察ベース主張 `09e:26-32`) の処理
- **(a)** §9.6.1 内で proof 補強 (例: 条件数下限 → DC 不動点存在不能の lemma 追加)
- **(b)** §11 verification 章へ pointer 化 (「§11 で示されるように」と一行参照)
- **(c)** 削除 (条件数式 `eq:ppe_cond_number` のみ残し, plateau 主張は除去)

### Q3: 懸念 3 (§9.7 = 09f 全体配置)
- **(a)** 章末維持 (現状; 注記改良のみ) — H-α
- **(b)** tcolorbox 2 件 + FVM 注記を §10 algorithm 章へ移管, summary table のみ §9 末尾に残置 — H-β
- **(c)** 09f 全体を §10/§11/§15 に分散, §9 は §9e で自然終結 — H-γ
- **(d)** 09f 全体を §11 verification 章 1 章として独立 (実測値依拠の主張をすべて §11 に集約)

### Q4 (sub-question): 懸念 4 (FVM framing)
- **(i)** 比較 baseline + 物理的根拠 retain (5 箇所); production option 言及 (`09f:119-123`) は H-β/γ で §10 に移管
- **(ii)** 同上 + `09e:13` 周期 BC FVM 行列 ref を付録誘導のみに圧縮
- **(iii)** すべての FVM 言及を historical/comparative note として明示 ("legacy method; 本稿では FCCD 採用")

---

## Section J: ch13 production との実装ギャップ check

| §9 の記述 | ch13 production 実態 | 整合性 |
|---|---|---|
| §9.7 (09f L121-122) Level 2 = 「変密度一括 smoothed-Heaviside PPE vs GPU-native FVM」 | ch13 YAML は `pressure_jump` (= Lv.3 = 分相 PPE) | **不整合** (Lv.2 が production と書かれているが実態は Lv.3) |
| §9.7 (09f L78-80) Level 3 = 「高密度比 + 高粘性比 + 低 We 同時成立時」 | ch13 = 水/空気 (ρ ratio 10³, μ ratio 10²) | **整合** (条件成立) |
| §9b YAML セマンティクス (L405-414) `phase_separated` + `jump_decomposition` + `pressure_jump` | ch13 production と一致 | (記述自体は実態整合だが 論文に置く形式が問題) |
| §9.6.1 (09e L24) 「水/空気相当 ρ_l/ρ_g ≈ 10³」 | ch13 = 水/空気 | 整合 |
| §9 内の FVM 経路言及 (`09f:119-123`) | ch13 production stack に FVM 不在 | **不整合** (production primary は FCCD face-jet) |

→ §9 は「Level 2 が default; Level 3 は研究/特殊用途」という framing で書かれているが, **実 production は Level 3 が default**. CHK-226 §8 査読でも同じ framing 乖離を確認しており, §9 も同じパターン. ただし CHK-226 で user 確定方針 = E-α (CSF primary 現状維持) を選んだため, §9 でも同 framing を保持する選択肢 (H-α) は valid.

---

## Section K: assistant の advisory

(user の judgment 自由度を保障するため最後に置く. 最終決定は user に委ねる)

CHK-226 で user は §8 を E-α (minimal) に確定した. 一貫性のため **§9 でも H-α/H-β** 寄りが自然 (H-γ は radical で paper 全体構造に波及する). 個人的推奨は **H-β**:

理由:
1. **H-α の制約**: YAML 削除と注記改良で 35 LOC 程度の局所修正だが, §9.6 後半 + §9.7 の構造的問題 (Option menu, design rationale, FVM framing) は手付かずで残る. ユーザが「違和感」と表現した直観の半分しか解消しない.
2. **H-β の利点**: §9 が clean な理論章になり, design rationale + production stack 説明は §10 algorithm 章という適所に集約される. ユーザの 4 件懸念がすべて構造的に解消する. 外部 ref 影響は alias で吸収可能 (~5-7 件).
3. **H-γ のリスク**: §9 タイトル変更 + tab:accuracy_summary 移管は paper 全体の章番号 ripple を引き起こし, CHK-225 (file prefix 統一) に類する大規模再構成になる. 効果対コストが見合わない.

ただし user が CHK-226 で E-α を選んだ理由 (production framing 維持) と一貫させるなら H-α も valid. H-β は paper 改稿コストが中程度発生する (CHK-228 候補で 2-4 commits 想定).

---

## 付録 A: §9 各 section/subsection 構造マップ

| ファイル | section/subsection | label | 行 |
|---|---|---|---|
| `09_ccd_poisson.tex` | `\section{圧力 Poisson 方程式の解法}` | `sec:ppe_solve` | L7 |
| | `\subsection{CCD 法の楕円型ソルバーとしての双対的役割}` | `sec:ccd_elliptic` | L45 |
| | `\subsection{CCD-Poisson 演算子の行列構造と変密度拡張}` | `sec:ccd_poisson_matrix` | L63 |
| | `\subsubsection{2 次元変密度 CCD-Poisson 演算子の完全定式化}` | `sec:ccd_2d_full` | L90 |
| | `\subsubsection{CSF + Balanced-Force + CCD 勾配による寄生流れの抑制}` | `sec:ccd_balanced_force` | L127 |
| | `\subsubsection{空間離散化スキームの定量的比較（FVM vs CCD）}` | `sec:ccd_vs_fvm` | L187 |
| `09b_split_ppe.tex` | `\subsection{分相 PPE 解法}` | `sec:split_ppe_framework` | L5 |
| | `\subsubsection{変密度一括解法の本質的制約}` | `sec:monolithic_ppe_limitation` | L20 |
| | `\subsubsection{分相 PPE 解法の定式化}` | `sec:split_ppe_formulation` | L52 |
| | `\subsubsection{純 FCCD 分相 PPE アーキテクチャ}` | `sec:pure_fccd_split_ppe` | L131 |
| | `\subsubsection{位相分離 FCCD PPE：面ジェット随伴ペア}` | `sec:phase_separated_fccd_adjoint` | L166 |
| | `\subsubsection{同一面係数による投影閉包と浮力残差}` | `sec:phase_separated_projection_closure` | L214 |
| | `\subsubsection{GFM ゴーストジェットによる位相ステッチ}` | `sec:gfm_ghost_jet_stitch` | L250 |
| | `\subsubsection{PPE 整合性条件と相別平均ゲージ}` | `sec:ppe_phase_gauge_pin` | L339 |
| | `\subsubsection{圧力ジャンプ形式：CSF 体積力を回避するクリーン分離}` | `sec:split_ppe_pressure_jump_formulation` | L382 |
| | `\subsubsection{再メッシュ再投影と PPE コンテキスト防護}` | `sec:split_ppe_regrid_guard` | L435 |
| `09c_hfe.tex` | `\subsection{Hermite 場延長法（HFE）：O(h⁶) 界面越し場延長}` | `sec:field_extension`/`sec:hfe` | L10 |
| | (4 subsubsections; OK) | | L58, L72, L125, L226 |
| `09d_defect_correction.tex` | `\subsection{欠陥補正法による効率的 PPE 求解}` | `sec:defect_correction_main` | L8 |
| | (5 subsubsections; OK) | | L43, L79, L105, L149, L200 |
| `09e_ppe_bc.tex` | `\subsection{境界条件と数値安定性}` | `sec:ppe_bc_stability` | L5 |
| | `\subsubsection{高密度比における条件数と数値安定性}` | `sec:ppe_condition_number` | L21 |
| | `\subsubsection{全周 Neumann 境界における零モード対策}` | `sec:ppe_zero_mode` | L71 |
| | `\subsubsection{圧力固定点（ピン点）の選択原則}` | `sec:pinpoint` | L90 |
| | `\subsubsection{FCCD 境界条件オプション III / IV}` | `sec:fccd_bc_options` | L105 |
| `09f_pressure_summary.tex` | `\subsection{本章のまとめ：精度バランスと設計上のトレードオフ}` | `sec:pressure_accuracy_summary` | L7 |

---

## 付録 B: §9 内 FVM 言及 7 箇所詳細 (file:line + 用途)

(Section E-1 の表を参照. 重複のため省略)

---

## 付録 C: 外部 ref 影響範囲 (restructuring impact)

| label | 外部参照数 (推定) | 主要参照元 | refactor 影響 |
|---|---|---|---|
| `sec:pressure_accuracy_summary` | ~7 | §9 各章, §10, §11, §13, appendix | H-β/γ で位置変更; label 保持で alias 可 |
| `sec:ppe_bc_stability` | ~3 | §9 内, §10, §11 | H-α 不変; H-β/γ で要 alias |
| `sec:fccd_bc_options` | ~2 | §10, §11 | H-β で 付録移管; alias 必須 |
| `sec:ppe_condition_number` | ~1 (内部) | §9.6 | H-α/β 不変 |
| `box:ppe_design_rationale` | ~3 | §10, §11 | H-β/γ で 移管; label 保持 |
| `sec:level_gpu_dual_path` | ~2 | §10, §11 | H-β/γ で §10 へ集約 |

**結論**: 外部 ref ~18 件のうち本質的に再番号化が必要なのは H-γ のみ. H-α なら 0 件, H-β なら ~5-7 件 (alias で backward-compat 可). 全 option で外部 ref 影響は管理可能.

---

## まとめ (1 段落)

§9 は理論的本体 (§9.1-9.5 = `09_ccd_poisson` + `09b` + `09c` + `09d` の ~1,200 LOC) は健全だが, **後半 2 ファイル (`09e` + `09f` = ~290 LOC) が理論章を逸脱**しており, ユーザの 4 件懸念 (YAML 漏出 / §9.6.1 観察ベース / §9.7 設計トレードオフ / FVM framing) はすべてこの後半に集中. CHK-226 §8 査読と異なり §9 は **章境界の整理 (28-300 LOC の削除/移管)** で大部分が解決可能で, 構造的再設計の必要性は §8 より低い. 再構成 option は H-α (minimal 35 LOC), H-β (moderate 100 LOC + §10 移管), H-γ (radical 300 LOC + 章 boundary 再設計) の 3 案. user の Q1-Q4 判断後, CHK-228 候補として §9 restructuring を実施する.
