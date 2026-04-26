# CHK-226 査読メモ: §8 BF-CCD 章 (Balanced-Force / 圧力・速度連成) 厳正レビュー

> **renumber 注記 (2026-04-26)**: 本メモは当初 CHK-225 として作成したが, 同日 main 側で別作業 (`worktree-ra-paper-prefix-realign`) が CHK-225 を取得済 (paper section file prefix b-style 統一 + 40 file renames; commits `ea1635d`/`56bb0ba`/`3654aef`/`4f34580`) のため, 本査読作業を CHK-226 へ renumber して main 取り込み後に worktree で継続. 後続 §8 restructuring は CHK-227 候補.
>
> **file rename 反映 (post-merge)**: main 側 CHK-225 で §8 ファイル 4 件が改名 — `08c_bf_failure.tex → 08c_bf_failure.tex`, `08d_bf_seven_principles.tex → 08d_bf_seven_principles.tex`, `08e_fccd_bf.tex → 08e_fccd_bf.tex`, `08f_pressure_filter.tex → 08f_pressure_filter.tex`. 本メモ内の markdown link path は更新済. 本文中の filter-prohibition shorthand (旧 c-prefix) は新ファイル名 `08f_*` に合わせて `§8f` 表記に更新済. ただし `§8.1` `§8.2` (旧 _1/_2 prefix 由来 shorthand; それぞれ §8d / §8e に対応) は本文 narrative 連続性のため旧表記を維持; 読み替えは `§8.1 ≡ §8d (BF 7 原則)`, `§8.2 ≡ §8e (FCCD-BF + 戦略表)` を推奨. `08_collocate.tex` `08b_pressure.tex` は rename 対象外.

**status**: REVIEW_ONLY (paper 編集は CHK-227 候補として後続)
**date**: 2026-04-26
**reviewer**: ResearchArchitect agent (査読官スタンス)
**scope**: `paper/sections/08_collocate.tex`, `08c_bf_failure.tex`, `08d_bf_seven_principles.tex`, `08e_fccd_bf.tex`, `08b_pressure.tex`, `08f_pressure_filter.tex` (計 6 ファイル / ~1,213 LOC)
**ユーザ事前懸念**:
1. C/RC・DCCD・Rhie-Chow が UCCD/FCCD 移行後も §8 に残置されている — 陳腐化していないか
2. CSF 前提で書かれた §8 BF が分相 PPE (`pressure_jump` formulation) でそのまま機能するのか

---

## Section A: 査読官のスタンスと総合判定

### A-1. 章の理論的価値 — 高い

§8 は `(F-1..F-5) → (P-1..P-7)` の **失敗モード→設計原則** という二段構成を持ち，
Balanced-Force (BF) を「微分階数の問題ではなく**離散演算子の整合性**の問題」として
正しく抽象化している ([08c_bf_failure.tex:23-25](paper/sections/08c_bf_failure.tex#L23-L25),
[08d_bf_seven_principles.tex:14-22](paper/sections/08d_bf_seven_principles.tex#L14-L22))．
P-1..P-7 のうち主解消 4 原則 (P-1/P-2/P-4/P-6) と副次寄与 3 原則 (P-3/P-5/P-7) の
役割分離は明示的で，F×P 対応マップ ([08d_bf_seven_principles.tex:235-251](paper/sections/08d_bf_seven_principles.tex#L235-L251)) も整合的．
査読官として **理論部分そのものは保持価値が高い**．

### A-2. 章の framing 上の重大問題 — production stack との乖離

`ch13_rising_bubble_water_air_alpha2_n128x256.yaml` (production benchmark) は
([config L74-84](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L74-L84))：

```yaml
surface_tension:
  formulation: pressure_jump        # ← CSF 体積力ではなく PPE 圧力ジャンプ
poisson:
  operator:
    discretization: fccd
    coefficient: phase_separated    # ← 分相 PPE
    interface_coupling: jump_decomposition
```

すなわち **production = 戦略 C (分相 PPE + FCCD face-jet + GFM jump)**．
ところが §8 全体は **戦略 A/B (CSF 体積力 + 節点 CCD or 低次面フラックス + Rhie-Chow + DCCD filter)** を
"本稿の手法"として現在形で記述している．§8.2 戦略表 ([08e_fccd_bf.tex:135-163](paper/sections/08e_fccd_bf.tex#L135-L163)) のみ
戦略 C を「Level 3 = 純 FCCD DNS 目標」と位置付けるが，これは
production 実態 (Level 2/3 を区別せず Level 3 で動いている) と逆転している．

### A-3. 総合判定 — Major Revision

| 評価軸 | 判定 |
|---|---|
| 理論的厳密性 | ◎ (P-1..P-7 framework は valid) |
| 内部整合性 | ○ (F×P 対応・eq label 連携は整合) |
| Production stack との整合 | × (戦略 A/B 前提で書かれ，戦略 C は "研究レベル" と marked) |
| 移行ナラティブ | × (DCCD-NS → CCD-NS → FCCD/UCCD6 → 分相 PPE の歴史軸が皆無) |
| 読者の判断容易性 | △ (どの記述が現 production で，どれが legacy か不明) |

**判定**: 内容そのものは保持価値が高いが，**framing と production との整合**に
本質的問題があり **major revision** を要する．rejection ではなく構造的書き直し．

---

## Section B: 懸念 1 (legacy operator 残置) の所見

### B-1. C/RC を "本稿の手法"として現在形で記述している誤誘導

[08_collocate.tex:276-285](paper/sections/08_collocate.tex#L276-L285) は
「**追加計算コストゼロで空間精度を $\Ord{h^4}$ に改善する手法を導出する**」とし，
C/RC (CCD-enhanced Rhie-Chow) を「本稿の手法」として位置付けている．

**査読官の指摘**:
- ch13 production YAML には Rhie-Chow 関連設定は存在しない (`pressure_jump` + `fccd` 直接出力)．
- WIKI-X-029 §6 ([Strategy A](docs/wiki/cross-domain/WIKI-X-029.md#L194-L204)) は明示的に
  「FCCD or low-order face-flux で $G_h^{bf}$ を構築」とし，C/RC は §8 (Anti-Patterns) で
  「Rhie-Chow in BF pressure path → BF violated by construction」と排除している．
- すなわち **C/RC は本稿の現 production 経路では使われていない**．残すなら "legacy / 教育的説明" として明示すべき．

### B-2. C/RC-DCCD (eq:crc_dccd) も同様 — production 不使用

[08_collocate.tex:388-417](paper/sections/08_collocate.tex#L388-L417) の C/RC-DCCD は
「DCCD 散逸の高次精度化」として現在形で記述．しかし：
- ch13 YAML の PPE は `defect_correction + GMRES` 構成で
  ([config L86-97](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L86-L97))，
  DCCD filter は PPE RHS には適用されていない (戦略 C では cross-interface coupling が
  `jump_decomposition` で断たれているため，そもそも RHS に界面 driven の checkerboard 駆動項が乗らない)．
- WIKI-T-076 ([Projection-Closure Theorem](docs/wiki/theory/WIKI-T-076.md#L14-L22)) は
  「PPE rows と velocity corrector が同一面演算子 $L_h = D_f A_f G_f$ を共有」を要求；
  DCCD filter を片側にのみ作用させると closure が崩れる．これは §8f で正しく禁止規則として
  ([08f_pressure_filter.tex:38-47](paper/sections/08f_pressure_filter.tex#L38-L47)) 述べられているが，
  C/RC-DCCD は「両辺対称」を満たさないため，**§8f 禁止規則と §8.collocate C/RC-DCCD は内部矛盾している可能性**．

### B-3. DCCD filter 自体の必要性 — operator dependence の明示が不足

§8f ([08f_pressure_filter.tex:6-15](paper/sections/08f_pressure_filter.tex#L6-L15)) は
「DCCD 散逸機構 $\varepsilon_d=1/4$ は移流経路に限定して適用」と正しく規定．
しかし §8.collocate ([08_collocate.tex:340-381](paper/sections/08_collocate.tex#L340-L381)) は
「PPE 右辺は DCCD フィルタ済み CCD 発散」を `本稿の手法`として記述．

**査読官の指摘**: PPE RHS への DCCD filter の必要性は **operator が何か** に依存する：

| operator | DCCD filter 必要性 |
|---|---|
| 節点 CCD (中心系) | 必要 (Nyquist モード散逸ゼロ; [04c L26-29](paper/sections/04c_dccd_derivation.tex#L26-L29)) |
| FCCD face-jet | **不要** (face 出力は natively `2Δx` モードを持たない; WIKI-T-076 の closure theorem) |
| 分相 PPE + jump_decomposition | **不要** (cross-interface coupling 断ち切りで checkerboard 駆動源が消える) |

§8 で **どの operator で DCCD filter が必要 / 不要か**を明示せず，
全 operator で必要な印象を与えている．現 production (FCCD + 分相 PPE) では不要．

### B-4. Rhie-Chow 自体の必要性 — 同様に operator dependence

[08_collocate.tex:110-119](paper/sections/08_collocate.tex#L110-L119) は
「コロケート格子における $2\Delta x$ checkerboard 解消には Rhie-Chow が標準」と現在形で書く．
[08_1 bf_rhie_chow_restriction L210-228](paper/sections/08d_bf_seven_principles.tex#L210-L228) は
「RC 単独 = 不可，RC + CSF 整合拡張 = 既定」とし，**Level 2 既定経路**として
RC + CSF の独立成立を主張．しかし ch13 production は Level 2/3 区別なく `pressure_jump` で動作．
WIKI-X-029 §5 ([Rhie-Chow critique](docs/wiki/cross-domain/WIKI-X-029.md#L171-L186)) は
「RC ≠ force balance；RC は debugging or coarse-grid 用途のみ」と明確に位置付け．
**§8.1 の "RC + CSF 整合拡張 = 既定" 言明と WIKI-X-029 の "RC ≠ production BF mechanism" 言明が矛盾**．

### B-5. 移行ナラティブの欠落 — "なぜ FCCD に移ったか"が読み取れない

§8 は「DCCD-NS 時代 (DCCD-advection が主) → CCD-NS 時代 (節点 CCD + Rhie-Chow + DCCD filter) →
FCCD/UCCD6 時代 (face-native operator + 分相 PPE)」という研究室史を narrate していない．
- §4.4 ([04c_dccd_derivation.tex:16-50](paper/sections/04c_dccd_derivation.tex#L16-L50)) は DCCD-as-filter を
  「節点中心 CCD への外殻 post-filter」として導出し，「移流の安定化専用」と限定．
- §4.7 (FCCD; sec:face_jet_def) は face-native operator として確立．
- しかし §8 はこの 2 つを橋渡しせず，DCCD filter を pressure 経路に持ち込み続ける記述が残る．

**査読官の指摘**: 読者は「§4.4 DCCD は移流専用と書いてあるのに，§8.collocate では PPE RHS に
DCCD filter を適用するのか」「§4.7 FCCD は face-native と書いてあるのに，§8 では
Rhie-Chow + DCCD filter で checkerboard 抑制するのか」を混乱して読むはず．
**§4 (operator definition) と §8 (BF application) の narrative bridge が必要**．

### B 総括

§8 は「BF 概念 → 各演算子で実装」という章立てだが，現実は
**演算子ごとに BF 整合の達成方法が大きく異なる**．現状の章立ては：
- 節点 CCD には RC + DCCD filter が必須 (§8.collocate `本稿の手法`)
- FCCD face-jet には RC も DCCD filter も不要 (§8.2 の `Level 2/3`)

の **2 stack を混在記述**しており，どちらが現 production か明示されない．
査読官として **「演算子家族 → BF 適用例」の順で書き直すべき**と判断．

---

## Section C: 懸念 2 (CSF 前提) の所見

### C-1. P-1..P-7 のうち CSF 専用は P-3 と P-4 item 3 のみ

| 原則 | CSF 専用？ | 根拠 |
|---|---|---|
| P-1 (位置一致) | × (formulation-agnostic) | $G_h p$ と $f_{\sigma,h}$ の位置一致は両 formulation で必要 |
| P-2 (随伴 $D_h = -G_h^*$) | × (formulation-agnostic) | PPE SPD と同 $G_h$ 共有は分相 PPE でも必須 (WIKI-T-076) |
| P-3 ($f_\sigma = G_h p_\sigma$) | **○ (CSF 専用)** | [08_1 L83-91](paper/sections/08d_bf_seven_principles.tex#L83-L91); 分相 PPE では $f_\sigma=0$ |
| P-4 ($\beta_f$ 統一) | △ (item 1,2 は universal; item 3 = $f_\sigma$ normalization は CSF 専用) | [08_1 L99-107](paper/sections/08d_bf_seven_principles.tex#L99-L107) |
| P-5 (曲率非 CCD) | × (formulation-agnostic) | $\kappa$ 計算は分相 PPE の jump $[p]_\Gamma=\sigma\kappa$ にも必要 |
| P-6 (jump 補正) | × (formulation-agnostic) | GFM/IIM は両 formulation で必要 |
| P-7 (sub-system 分離) | × (formulation-agnostic) | 設計原則 |

**結論**: 7 原則中 5 原則 (P-1, P-2, P-5, P-6, P-7) は formulation-agnostic．
P-3 と P-4 item 3 のみが CSF 体積力に依存．
**§8 が P-3 を universal 原則として presentation しているのは誤り** — 分相 PPE では
P-3 は意味を失う (RHS の $G_h p_\sigma$ が存在しないため)．

### C-2. §8b PPE 導出 と §8f filter 禁止式が CSF を含み，分相 PPE では破綻する記述

- [08b_pressure.tex:64-66](paper/sections/08b_pressure.tex#L64-L66): 「外力 $F_\text{ext}^{n+1}$ には
  重力項と CSF 体積力 $(\kappa^{n+1}\nabla\psi^{n+1})/We$ の両方が含まれる」と明記．
  しかし分相 PPE (`pressure_jump`) では CSF 体積力は **方程式から消滅**
  (運動量方程式の表面張力項 = 0; [09b L386-394](paper/sections/09b_split_ppe.tex#L386-L394))．
- [08f_pressure_filter.tex:30-31](paper/sections/08f_pressure_filter.tex#L30-L31): BF 平衡式 $-G_h^\text{bf} p + f_{\sigma,h}$
  は CSF $f_{\sigma,h}$ を含む．分相 PPE では $f_{\sigma,h} \equiv 0$ となり，平衡式そのものが
  $-G_h^\text{bf} p \approx 0$ という単側式に退化．**§8f の片側フィルタ非対称論は意味を失う**．

### C-3. §8.2 戦略表は production と逆転

[08e_fccd_bf.tex:158-163](paper/sections/08e_fccd_bf.tex#L158-L163):
> Level 1 (SSPRK3 検証) = 戦略 B；
> Level 2 (プロダクション) = 戦略 A (FCCD 面ジェット + GFM)；
> Level 3 (純 FCCD DNS) = 戦略 C を**目標**とする分相 PPE．

ch13 YAML (production) は `formulation: pressure_jump` + `coefficient: phase_separated` +
`interface_coupling: jump_decomposition` で **戦略 C で動作**．
したがって "Level 2 = 戦略 A" "Level 3 = 戦略 C **目標**" の framing と
ch13 production が乖離．**戦略 C は既に production 既定**であり "目標" ではない．

### C-4. 分相 PPE 下での BF 中核条件の再解釈

§8 BF 中核条件 ([08_collocate.tex:124-131](paper/sections/08_collocate.tex#L124-L131)):
> 圧力勾配 $\nabla p$ と表面張力 $(\kappa/We)\nabla\psi$ に**同一の離散演算子**を使用する

これは CSF 前提の表現．分相 PPE での再解釈は次の通り：

**分相 PPE 下の BF (新定式)**: WIKI-T-076 (Projection-Closure Theorem) より，
PPE と velocity corrector が **同一面演算子** $L_h = D_f A_f G_f$ を共有することが要件．
具体的には：
- $G_f$: nodal pressure → normal-face gradient
- $A_f$: phase-separated 係数 ($f \subset \Omega_q$ で $\rho_q^{-1}$, cross-phase で 0)
- $D_f$: face flux → nodal divergence
- $A_f^{PPE} = A_f^{corr}$ が必須 (式 [09b eq:same_face_projection_closure L231-247](paper/sections/09b_split_ppe.tex#L231-L247))

**operator-consistency という骨格は不変**だが，consistency relation の **対象が異なる**：
- CSF 下: $G_h p$ vs $f_\sigma = G_h p_\sigma$ の整合
- 分相 PPE 下: PPE side $A_f^{PPE} G_f p$ vs corrector side $A_f^{corr} G_f p$ の整合

§8 はこの **分相 PPE 下の BF formulation** を §9b に丸投げしており，§8 内で完結していない．

### C-5. §9b との関係整理が不足

§9b ([sec:split_ppe_pressure_jump_formulation L382-409](paper/sections/09b_split_ppe.tex#L382-L409)) は
分相 PPE の formal derivation を持つが，
**「分相 PPE 下では P-1..P-7 のどれが survive し，どれが reformulate されるか」の audit がない**．
査読官として：
- §8 の BF 7 原則 と §9b の Projection Closure Theorem (WIKI-T-076) の橋渡しが必要．
- 「分相 PPE 下では P-3 は不要 (CSF $f_\sigma$ がないため)，代わりに `A_f` 統一が新 P-3 になる」
  といった原則 reaudit を §8 か §9b で行うべき．

### C 総括

§8 BF は本質的に CSF 前提で書かれているが，現 production は分相 PPE．
書き直しの方向性は 2 通り：
1. **Dual-formulation**: CSF / 分相 PPE 両対応で 7 原則を再分類 (universal 5 + CSF-only 2 + phase-PPE-specific N)．
2. **Phase-PPE primary**: 分相 PPE を primary とし，CSF を「historical / 教育的説明」として §8 末尾に置く．

どちらが望ましいかは Section E (再構成 options) で論じる．

---

## Section D: 懸念 1 と 2 の coupling

### D-1. 分相 PPE の採用は legacy operator deprecation を自動正当化する

分相 PPE では $f_\sigma$ が消えるため：
- 「$f_\sigma \leftrightarrow G_h p$ 整合性」を保証する Rhie-Chow は **役割消失**．
- DCCD filter は「checkerboard 駆動項を PPE RHS に入れない正則化」だが，
  分相 PPE + jump_decomposition では cross-interface coupling が断たれており，
  そもそも RHS に界面 driven の checkerboard 駆動源が乗らない → **不要**．
- C/RC, C/RC-DCCD は両方とも CSF/節点 CCD 前提の高次化機構 → **両方とも不要**．

つまり **分相 PPE 採用 → C/RC, RC, DCCD filter 全て deprecated** となる．
懸念 1 (legacy operator) と 懸念 2 (CSF) は **同根**．

### D-2. Dual-formulation を維持する場合の負担

逆に CSF + 分相 PPE 両対応を §8 で維持するなら：
- CSF mode: P-1..P-7 + RC + DCCD filter の現行記述を retain．
- 分相 PPE mode: WIKI-T-076 closure theorem ベースの BF formulation を追加．
- **§8 LOC は ~+200 増える方向**．外部 ref (60+ 件) は label 不変なら影響軽微．

### D-3. 推奨方向性 (advisory; user judgment 必須)

ch13 production が `pressure_jump` で動作している事実を所与とすると，
査読官の advisory は以下：
- 戦略 C を production primary に格上げ．
- C/RC, RC, DCCD filter は **§8 内 historical section** として retain (削除でなく) — paper の教育的価値は残す．
- BF 7 原則は **universal 5 (P-1, P-2, P-5, P-6, P-7) + CSF-only (P-3, P-4 item 3)** に再分類．
- 分相 PPE 下の operator-consistency は WIKI-T-076 を §8 内で本文化．

ただし上記は assistant の判断であり，user の paper 設計方針に従う．

---

## Section E: 推奨される再構成 options (3 案)

| Option | 戦略 | LOC 影響 | 外部 ref 影響 | リスク | production 整合 |
|---|---|---|---|---|---|
| **E-α (minimal)** | §8 現状維持; chapter intro + §8.2 戦略表に「production = 戦略 C」と注記．§8.2 戦略 C 表記を「Level 3 目標」→「production default」に格上げ．Section A の framing 矛盾を最小注記で解消． | +20 LOC | 0 件 (label 不変) | 低 (ただし production と paper の本質的乖離は完全には解消されない) | △ |
| **E-β (dual-formulation)** | §8 を CSF / 分相 PPE 並立構造に refactor．BF 7 原則を `universal 5 + CSF-only 2 + phase-PPE-only 1` に再分類．C/RC/RC/DCCD filter は CSF mode 限定として retain．§8.2 戦略表を 2 column に拡張． | +200 LOC, -50 LOC (整理) | 中 (P-3/P-4 番号変更; sec:rc_balanced_force などの内部 ref 更新; 外部 ref は label 保持で minimal) | 中 (§8 は paper 中で最大の hub なので慎重) | ◎ |
| **E-γ (phase-PPE single + historical)** | §8 を 分相 PPE + FCCD face-jet single stack に統一．C/RC, RC, DCCD filter は §8 末尾の `historical / Strategy A/B 教育的説明` section にまとめ，production = phase-PPE と冒頭明示．BF 7 原則を分相 PPE 視点で再構成．§9b の Projection Closure Theorem を §8 本文に格上げ． | -150 LOC (legacy 削減), +80 LOC (phase-PPE 拡充) | 高 (P-3/P-4 大幅 reformulate; sec:rc_balanced_force / sec:rc_high_order の内部位置変更; 外部 ref は label 保持で alias 化必須) | 高 (ただし production stack と paper の整合は完全) | ◎ |

### E-α 詳細
- §8 chapter intro に 1 段落追加：「本章 §8.collocate--§8f は `戦略 A/B (CSF + RC + DCCD filter)` 経路の理論的厳密性を扱う．現 production stack (ch13 benchmarks) は §8.2 戦略 C (分相 PPE + FCCD face-jet + GFM) で動作；分相 PPE 下での BF formulation は §9b sec:split_ppe_framework に集約」
- §8.2 戦略表 ([08e_fccd_bf.tex:158-163](paper/sections/08e_fccd_bf.tex#L158-L163)): 「Level 3 = 戦略 C を**目標**とする」→「Level 3 = 戦略 C (現 production default; ch13 benchmarks 適用)」に修正．
- §8b ([08b_pressure.tex:64-66](paper/sections/08b_pressure.tex#L64-L66)) の「CSF 体積力を Predictor に保持」記述に「分相 PPE 経路では $f_\sigma=0$ (§9b 参照)」のクロスリファレンス追加．

### E-β 詳細
- §8.0 (新設): formulation 選択フロー (CSF vs 分相 PPE) と本稿の dual-stack 設計方針．
- §8.1 (現 §8.collocate Helmholtz): 等密度 → 変密度の 共通基礎．
- §8.2 (新): CSF stack の BF (現 §8.collocate `sec:balanced_force` + §8.1 P-3 + §8.collocate RC/DCCD filter)．
- §8.3 (新): 分相 PPE stack の BF (WIKI-T-076 Projection Closure Theorem + §9b の core 部分を §8 に格上げ)．
- §8.4 (現 §8.1 の universal 5 原則 + §8.2 FCCD-BF + §8f DCCD filter rule)．

### E-γ 詳細
- §8.collocate (大幅縮小): Helmholtz 分解 + 変密度 PPE 導出 + checkerboard 問題定義のみ．
- §8.1 BF 7 原則 → 5 原則 (universal) に縮約．P-3/P-4 item 3 は「附属：CSF 体積力との互換」として §8 末尾へ．
- §8.2 FCCD face-jet + 分相 PPE BF (WIKI-T-076 を本文化)．
- §8f DCCD filter prohibition: 削除 or 「§4.4 DCCD-as-filter から論理的に派生する追加禁止規則」として §4.4 に移管．
- §8 末尾 (新): 「Historical: 戦略 A/B (CSF + RC + DCCD filter) 教育的説明」 ~ §8.collocate の `sec:rc_balanced_force`, `sec:rc_high_order`, `sec:dccd_decoupling` を historical として retain．

---

## Section F: User 判断要請事項 (Q1, Q2)

### Q1: §8 の primary framework

§8 は CSF / 分相 PPE どちらを primary framework とすべきか:

- **(a) CSF primary (現状維持)** — option E-α
  - メリット: 既存記述温存; LOC 増加 minimal; 外部 ref 影響 0．
  - デメリット: production との framing 乖離が解消されない (注記止まり)．

- **(b) Dual-formulation 並立** — option E-β
  - メリット: CSF + 分相 PPE 両 stack を maintainable な形で記述; 教育的価値最大．
  - デメリット: §8 LOC ~+200; refactor 中の整合性管理コスト中．

- **(c) phase-PPE primary, CSF を historical 化** — option E-γ
  - メリット: production stack と完全整合; legacy clarity 最高; §8 LOC は -70 程度．
  - デメリット: refactor 範囲最大; 外部 ref alias 管理必須; 現行記述の論理構造を大幅に解体．

### Q2: legacy operator (C/RC, RC, DCCD filter) の処理

production 不使用と判断した場合の処理：

- **(i) §8 内で `historical / 教育的説明` として retain**
  - メリット: 現行 LOC 温存; 教育的価値; 外部 ref 不変．
  - デメリット: 章 LOC 大; production との混同リスクは framing で抑制．

- **(ii) §8 から削除し，§4 (operator 章) に historical 移管**
  - メリット: §8 がシャープ; production stack に集中．
  - デメリット: §4 LOC 増; cross-chapter ref 多数発生; refactor coast 高．

- **(iii) §8 残置 + 「現在は使用していない」明記**
  - メリット: 最小変更．
  - デメリット: 読者は「なぜ残してあるのか」と困惑; "本稿の手法" 表現と矛盾．

### Q1 × Q2 の組み合わせ推奨

| Q1 | Q2 推奨 | 整合性 |
|---|---|---|
| (a) E-α | (iii) | ○ (注記+表現修正だけで完結) |
| (b) E-β | (i) | ◎ (CSF stack 内に retain; 章構造で 2 stack 並列) |
| (c) E-γ | (i) | ◎ (§8 末尾 historical として明示的に retain) |

---

## Section G: ch13 production との実装ギャップ check (fact-check)

ch13 production YAML (`ch13_rising_bubble_water_air_alpha2_n128x256.yaml`) の構成と
§8 記述の対応：

| YAML 設定 | §8 記述 | 一致/不一致 |
|---|---|---|
| `surface_tension.formulation: pressure_jump` ([L75](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L75)) | §8 全体は CSF 前提; §8.2 戦略 C のみ分相 PPE 言及 | **不一致** (production は分相 PPE) |
| `poisson.operator.coefficient: phase_separated` ([L83](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L83)) | §8b PPE 導出は smoothed Heaviside 一括解法前提 ([L68-71](paper/sections/08b_pressure.tex#L68-L71)) | **不一致** (production は phase_separated) |
| `poisson.operator.interface_coupling: jump_decomposition` ([L84](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L84)) | §8 にこの言葉は登場しない (§9b には登場) | **§8 未言及** |
| `momentum.terms.pressure.gradient: fccd` ([L70](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L70)) | §8.2 FCCD face-jet は production 経路として記述 ([L27-37](paper/sections/08e_fccd_bf.tex#L27-L37)) | **一致** |
| `momentum.terms.convection.spatial: uccd6` ([L67](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L67)) | §8 P-7 表 ([L184](paper/sections/08d_bf_seven_principles.tex#L184)) で「節点 CCD / UCCD6 / FCCD」と並列列挙のみ; 選択基準なし | **§8 で UCCD6 採用根拠不明** |
| `momentum.terms.viscosity.spatial: ccd` ([L72](experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L72)) | §8 では viscosity は §8.2 P-7 表のみ | **§8 で粘性 operator 設計言及なし** (§7e に集約; out of §8 scope) |
| Rhie-Chow 設定なし | §8.collocate `sec:rc_balanced_force`, `sec:rc_high_order` ([L210-336](paper/sections/08_collocate.tex#L210-L336)) で現在形 | **不一致** (production は RC 不使用) |
| DCCD filter on PPE RHS 設定なし | §8.collocate `sec:dccd_decoupling` ([L340-457](paper/sections/08_collocate.tex#L340-L457)) で「PPE 右辺は DCCD フィルタ済み」と記述 | **不一致** (production は分相 PPE で不要) |

### G 結論

**production 8 軸中 5 軸が §8 記述と不一致**．これは
「§8 が `戦略 A/B` を `本稿の手法` として記述しているが，
ch13 production は `戦略 C` で動作している」という事実の reflection．

---

## Section H: assistant 推奨 (advisory note)

(注：本セクションは判断材料の advisory であり，user の判断に従う)

ch13 production が分相 PPE で動作しており，かつ short paper (SP-M) も
"Pure FCCD Phase-Separated PPE Architecture" を主軸とする方針が確立している
([SP-M L1-21](docs/memo/short_paper/SP-M_pure_fccd_phase_separated_ppe_hfe.md#L1-L21)) ことを
踏まえると，本長 paper の §8 も **option E-γ (phase-PPE primary + historical)** が
production と paper の整合を最も達成する．

ただし E-γ は refactor 範囲が最大で，外部 ref 60+ 件への影響を慎重に
管理する必要がある．LOC 影響は -70 程度だが，章構造の解体・再構築コストは高い．
中間妥協として **option E-β (dual-formulation)** も選択肢．これは LOC 増加を
許容する代わりに，CSF / 分相 PPE 両 stack を明示的に並列記述し，
読者がどの formulation で動いているかを表で区別できる．

E-α は `現状維持 + 注記` で minimum effort 路線だが，**production と paper の
framing 乖離は本質的には残る**．次の peer review (外部) で同じ指摘が再発する
可能性が高い．

assistant の推奨優先順位: **E-γ ≥ E-β > E-α** (ch13 production の単一 stack
化が確定している場合) ／ **E-β > E-γ > E-α** (CSF stack も legacy benchmark で
維持したい場合)．

---

## 付録 A: 査読官として記録した B-3 矛盾の詳細

[08_collocate.tex:438-440](paper/sections/08_collocate.tex#L438-L440):
> 変密度 (Level 2 smoothed-Heaviside / Level 3 分相 PPE) では
> $\bu^* - \Delta t\,\rho^{-1}G_h p$ — 以下 $G_h p$ は適切な係数を含む projection gradient と読む．

これは Level 2 と Level 3 を並列扱いしているが，§8.2 戦略表は Level 3 = 戦略 C "目標"
と marked．**§8.collocate の `Level 3 分相 PPE` 記述と §8.2 の `Level 3 = 目標` 記述は
内部で矛盾している**．現 production が Level 3 で動作していることを反映するなら，
§8.2 戦略表の修正 (E-α) が最低限必要．

## 付録 B: 査読官として記録した P-5 statement の再検討必要性

[08d_bf_seven_principles.tex:140-148](paper/sections/08d_bf_seven_principles.tex#L140-L148):
> 圧力フィルタリングは BF 経路に適用する場合，
> $-G_h p + f_\sigma$ の**両辺に対称に**適用せねばならない．

分相 PPE では $f_\sigma=0$ となるため，「両辺対称」は単に
「$G_h p$ にもフィルタを適用しない」と退化する．**P-5 の現行記述は CSF 前提でしか
意味を持たない**．分相 PPE 下では P-5 は「$G_h p$ にフィルタ禁止」だけが残り，
これは §8f [`sec:dccd_pressure_filter_prohibition`] の禁止規則と同値．

---

## 付録 C: 外部 ref 影響範囲 summary

§8 章構造変更時の外部 ref 影響 (Phase 1 探索で取得済):

| label | 外部参照数 | 主要参照元 | refactor 影響 |
|---|---|---|---|
| `sec:balanced_force` | ~17 | §1, §2, §7c, §10, §12, §14, appendix_*, 09c_hfe | label 保持で影響軽微 |
| `sec:dccd_decoupling` | ~6 | §10, §11a, §12h, §14, appendix_numerics_solver_s4 | E-γ で章末 historical に移しても label 保持で OK |
| `sec:fvm_ccd_corrector` | ~5 | §9f, §10 (×2) | label 保持必須 |
| `sec:bf_seven_principles` | ~3 | §1, §1b, §2 | E-γ では `7 原則`→`5 原則` に変わるが label 保持で alias 可 |
| `sec:rc_balanced_force` | ~3 | §1b, §9f, appendix_numerics_solver_s4 | E-γ で historical 化しても label 保持で OK |
| `sec:rc_high_order` | ~3 | §14, appendix_numerics_solver_s4, appendix_pressure | 同上 |
| `sec:bf_p1_location` ~ `sec:bf_p7_separation` | 各 1-2 | §10_5, §7c, §11 | E-γ で再番号化する場合は alias 必須 |
| `sec:fccd_bf_sub_system` | ~2 | §10_5, §7c | label 保持で OK |
| `sec:dccd_pressure_filter_prohibition` | 0 (内部 §8 のみ) | — | E-γ で削除 or 移管自由 |

**結論**: 外部 ref 60+ 件のうち本質的に再番号化が必要なのは
P-1..P-7 (E-γ で 5 原則化する場合) のみ．alias (`\phantomsection\label{...}`) で
backward-compat を維持すれば全 option で外部 ref 影響は管理可能．

---

## まとめ (1 段落)

§8 BF-CCD 章は理論的には valid だが，**production stack (ch13 = 戦略 C 分相 PPE) と章 framing (戦略 A/B CSF + RC + DCCD filter) が乖離**しており **major revision** を要する．懸念 1 (legacy operator 残置) と 懸念 2 (CSF 前提) は同根であり，分相 PPE 採用は C/RC, RC, DCCD filter の役割消失を自動正当化する．再構成 option は E-α (minimal 注記)，E-β (dual-formulation)，E-γ (phase-PPE primary + historical) の 3 案．user の Q1 (formulation 方針) と Q2 (legacy operator 処理) の判断後，CHK-226 候補として §8 restructuring を実施する．
