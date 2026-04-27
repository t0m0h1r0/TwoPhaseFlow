# CHK-240 — §6 方程式項別空間離散化 査読官レビュー

**Date**: 2026-04-27
**Branch**: `worktree-ra-review-ch6-20260427`
**Trigger**: ユーザ依頼 — 「6章について、査読官になったつもりで厳正にレビュー」(ResearchArchitect 経由)
**入力**: `paper/sections/{06,06b,06c,06d}*.tex` 計 936 行
- §6.0 [06_scheme_per_variable.tex](../../paper/sections/06_scheme_per_variable.tex) — 98 行
- §6.1 [06b_advection.tex](../../paper/sections/06b_advection.tex) — 224 行
- §6.2 [06c_fccd_advection.tex](../../paper/sections/06c_fccd_advection.tex) — 289 行
- §6.3 + §6.4 [06d_viscous_3layer.tex](../../paper/sections/06d_viscous_3layer.tex) — 325 行

**出力**: 本 memo + §6 修正コミット (CHK-240)

---

## Section A: 査読官スタンスと総合判定

### A-1. §6 の理論的価値評価

§6 は「**差分演算子は場の特性に合わせて選択せよ**」という設計方針を、CLS $\psi$ (FCCD 面ジェット) / 運動量 (UCCD6) / 粘性 (Layer A/B/C + corner $\mu$) / 物性値 (代数更新) / 圧力 (GFM/IIM) の 5 変数別に分解して提示している。CHK-218 章再配置 → CHK-219 移流レビュー → CHK-222 design-purify → CHK-223 三章分離の 4 連改修により、構造的瑕疵 (DCCD legacy 言及・由来不明実数・実装識別子・narrative inconsistency) は概ね解消されている。Part 1 連続定式化との接続も各 subsection 冒頭の「Part 1 連続定式化との関係」段落で明示済。

### A-2. 主要問題の概観

最終確認として:
1. **表 (06_L45/L47) と本文 (06_L74-78) の priority 整合性** — 表セルが production default を明示せず、複数スキームを並列表示している箇所が 2 件残存
2. **ラベル意味的妥当性** — `sec:eikonal_reinit` (legacy alias) を経由したリンクが Ridge-Eikonal 節 (production stack) に飛ぶが、表セル記述が「Godunov / WENO-HJ」のみで production 主軸が読み取れない
3. **KL-12 違反** — 06d 内 subsubsection 見出し 2 箇所が `\texorpdfstring` 保護なしで数式を含む
4. **drafting artifact** — CHK-223 期 forward-ref コメント残存・§5b→§6 bridging sentence 欠如

### A-3. 総合判定

| 評価軸 | Pre-fix | Post-fix (想定) |
|---|:-:|:-:|
| 論理的一貫性 | △ | ◎ |
| 引用 (\\cite) 精度 | ◎ | ◎ |
| 式-テキスト整合 | ○ | ◎ |
| Algorithm Fidelity (PR-5) | △ | ◎ |
| Whole-Paper Consistency (P3) | △ | ◎ |
| Style (KL-12) | ✗ | ◎ |

**判定 (Pre-fix)**: **FAIL** (3 MAJOR + 3 MINOR / FATAL なし)
**判定 (Post-fix 期待)**: **PASS** (0 FATAL + 0 MAJOR — PaperReviewer AU2 gate 通過)

---

## Section B: FATAL 所見

**該当なし**. 全 \\ref ターゲット (36 件) の定義先存在 / 全 \\cite キー (3 件: `Fedkiw1999`, `JiangPeng2000`, `JiangShu1996`) の bib 存在を確認済み。`PPESolverCCDLU` `LGMRES` `FCCDLevelSetAdvection` `SplitReinitializer` 等の禁止トークン (PR-2/PR-6 / CHK-222 V-5) も §6 全 4 ファイルで 0 件。

---

## Section C: MAJOR 所見

### C-1: 表セル `sec:eikonal_reinit` ラベル意味的ミスマッチ + production 主軸欠如

- **File**: [paper/sections/06_scheme_per_variable.tex:47](../../paper/sections/06_scheme_per_variable.tex#L47)
- **Quote (現状)**:
  ```latex
  $\phi$（再初期化）& Eikonal & Godunov（等密度検証）/ WENO--HJ~\cite{JiangPeng2000}（変密度本番；\S\ref{sec:eikonal_reinit}）\\
  ```
- **問題**:
  1. リンク先 [paper/sections/05_reinitialization.tex:213-215](../../paper/sections/05_reinitialization.tex#L213) は subsubsection「**Ridge-Eikonal 再初期化：Eikonal 基盤と Ridge 補正の統合定式化**」であり、`\label{sec:xi_sdf_reinit}` が主ラベル、`sec:eikonal_reinit` は CHK-222 統合時の `\phantomsection` legacy alias (L215 コメント「旧 §6.3.4 ラベル統合; 外部参照保護」) — alias 経由は意味的に Ridge-Eikonal を指している
  2. しかし表セルの記述「Godunov（等密度検証）/ WENO-HJ（変密度本番）」だけでは ch13 production = **Ridge-Eikonal** であることが読者に伝わらない。実際 [06b_advection.tex:216](../../paper/sections/06b_advection.tex#L216) の box:scheme_roles では「Ridge-Eikonal (§\\ref{sec:ridge_eikonal})」と明示されており、§6.0 の表セルだけが旧表現で残存
  3. PR-5 Algorithm Fidelity 違反: ch13 production YAML (`interface.reinitialization.algorithm: ridge_eikonal`) と表セル narrative の不一致
  4. P3-C 相互参照整合違反: legacy alias を主参照に据えた表セル
- **YAML 根拠**: [experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml:28](../../experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L28) `algorithm: ridge_eikonal`
- **推奨修正**:
  ```latex
  $\phi$（再初期化）& Eikonal & \textbf{Ridge-Eikonal}（ch13 production；\S\ref{sec:xi_sdf_reinit}）／ Godunov・WENO--HJ~\cite{JiangPeng2000}（基底 Eikonal solver）\\
  ```
  ラベルを意味的に正確な `sec:xi_sdf_reinit` に切替、表記から production 主軸を明示、Godunov/WENO-HJ は基底 solver の補足記述に降格。

---

### C-2: 表 `u,v` bulk セル「CCD / UCCD6 / FCCD」三択並列の priority 不明確

- **File**: [paper/sections/06_scheme_per_variable.tex:45](../../paper/sections/06_scheme_per_variable.tex#L45)
- **Quote (現状)**:
  ```latex
  $u, v$ bulk & $C^\infty$ 滑 & CCD / UCCD6 / FCCD（\S\ref{sec:fccd_advection}）\\
  ```
- **問題**:
  1. 同ファイル [L77-78](../../paper/sections/06_scheme_per_variable.tex#L77) 本文では「**UCCD6 が ch13 production の実装デフォルト**」と単一明記
  2. [06b_advection.tex:215](../../paper/sections/06b_advection.tex#L215) box:scheme_roles でも「UCCD6 (§\\ref{sec:uccd6_def})」と単一明記
  3. しかし §6.0 の方針表は「CCD / UCCD6 / FCCD」と 3 者を並列、priority/role が判別不能
  4. P3-B 違反 (eq↔code: YAML default が表に反映されない) / PR-5 違反 (Algorithm Fidelity: production scheme 単一化)
- **YAML 根拠**: [experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml:68](../../experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml#L68) `momentum.terms.convection.spatial: uccd6` (両 ch13 production YAML 共通)
- **推奨修正**:
  ```latex
  $u, v$ bulk & $C^\infty$ 滑 & \textbf{UCCD6}（ch13 production；\S\ref{sec:fccd_advection}）／ CCD・FCCD（検証用代替）\\
  ```
  UCCD6 主軸 + 代替候補 (CCD/FCCD は §6.2 検証用) の役割分担を明示。

---

### C-3: KL-12 違反 — 06d subsubsection 見出し 2 箇所が `\texorpdfstring` 保護なし数式を含む

- **File 1**: [paper/sections/06d_viscous_3layer.tex:29](../../paper/sections/06d_viscous_3layer.tex#L29)
- **Quote (現状)**:
  ```latex
  \subsubsection{なぜ $\mu\nabla^2 u$ が誤りか}
  ```
- **File 2**: [paper/sections/06d_viscous_3layer.tex:109](../../paper/sections/06d_viscous_3layer.tex#L109)
- **Quote (現状)**:
  ```latex
  \subsubsection{コーナー粘性：$\tau_{xy}$ を第一級要素として扱う}
  ```
- **問題**:
  1. KL-12 ([docs/00_GLOBAL_RULES.md](../../docs/00_GLOBAL_RULES.md) §KL-12, L57-59): 「節タイトル・caption の数式は `\texorpdfstring` で保護せよ」が明文化された規則
  2. xelatex/PDF Outlines (TOC bookmarks) でこれら見出しが数式モードを表示しようとして fallback / corruption の可能性
  3. 同ファイル内 L222/L245/L277 の他 subsubsection は全て `\texorpdfstring` 保護済 — 本 2 件のみが取り残されている
  4. P1 LaTeX Authoring (Style) + KL-12 違反 — Style カテゴリだが規則明記により MAJOR
- **推奨修正**:
  ```latex
  % L29
  \subsubsection{\texorpdfstring{なぜ $\mu\nabla^2 u$ が誤りか}{なぜ μ∇²u が誤りか}}
  % L109
  \subsubsection{\texorpdfstring{コーナー粘性：$\tau_{xy}$ を第一級要素として扱う}{コーナー粘性：τ\_{xy} を第一級要素として扱う}}
  ```

---

## Section D: MINOR 所見

### D-1: CHK-223 期 forward-ref コメント残存 (drafting artifact)

- **File**: [paper/sections/06_scheme_per_variable.tex:85-86](../../paper/sections/06_scheme_per_variable.tex#L85)
- **Quote (現状)**:
  ```latex
  % CHK-223 Phase 4.5: 速度-PPE 整合性段落は時間積分順序設計のため §7 NEW へ移行．
  % 詳細は \S\ref{sec:cls_velocity_consistency_v7}（§7.3）に集約．
  ```
- **問題**: 読者には不可視だが、CHK-223 移行作業中の私的メモがソースに残存。clean 版提出前にクリーン化すべき drafting artifact。
- **推奨修正**: 2 行削除。

### D-2: §5b → §6 bridging sentence 欠如

- **File**: [paper/sections/05b_cls_stages.tex](../../paper/sections/05b_cls_stages.tex) (末尾)
- **Quote (現状)**: 末尾の `\subsubsection{失敗モードと回避}` (`sec:cls_failure_modes`) 内で §6.1 (`sec:advection_motivation`) への ref はあるが、§6 全体への章末橋渡し文が無い
- **問題**:
  1. [05_reinitialization.tex:18-19](../../paper/sections/05_reinitialization.tex#L18) では §5 章頭で §6 / §7 を予告済、しかし §5b 末尾からの handoff が欠如
  2. P3-D Whole-Paper Consistency: 章間の論理的流れが片寄せ (forward-ref のみ、backward 接続なし)
- **推奨修正**: §5b 末尾の `% ════` 直前に bridging 段落を 1 つ追加:
  ```latex
  \medskip
  \noindent\textbf{次章への接続：}
  以上で CLS 6 段階アルゴリズム (Stage A--F) の責務分離が確立した．
  続く §~\ref{ch:per_term_spatial}（§6）では，CLS $\psi$ 移流に加え運動量 $u,v$ 移流・
  粘性 $\bnabla\cdot(2\mu\bm{D})$・物性値 $\rho,\mu$・圧力 $p$ jump の各方程式項について
  「場の特性に合わせて差分演算子を選択せよ」の方針で個別離散化を論じる．
  ```

### D-3: §6→§8 forward-ref `(§N)` 括弧書き慣行 — **修正不要 (memo 記録のみ)**

- **File**: [paper/sections/06_scheme_per_variable.tex:48](../../paper/sections/06_scheme_per_variable.tex#L48), [L94](../../paper/sections/06_scheme_per_variable.tex#L94)
- **観察**: L48 (表セル内) は `(\S\ref{sec:balanced_force})` で章番号括弧書き省略、L94 (本文) は `\S~\ref{sec:balanced_force}（§8）に委ねる` で `(§8)` 明示
- **判断**: 表セル内は幅制約のため簡潔表現、本文は明示表現という設計選択であり、§6 内で一貫している (06b/06c/06d でも同慣行を確認)。**P3-C 違反ではなく許容範囲**。修正不要、本所見は将来の参照用に記録。

---

## Section E: 検証エビデンス

### E-1. PR-5 Algorithm Fidelity 対応表

ch13 production = `experiment/ch13/config/{ch13_rising_bubble_water_air_alpha2_n128x256, ch13_capillary_water_air_alpha2_n128}.yaml` 共通:

| YAML キー | 値 | §6 narrative | 整合性 (Pre-fix) | 修正対応 |
|---|---|---|:-:|---|
| `interface.reinitialization.algorithm` | `ridge_eikonal` | 06_L47 表「Eikonal/WENO-HJ」 | ✗ | C-1 |
| `interface.transport.spatial` | `fccd` | §6.1 / 06b L26-28 | ◎ | — |
| `momentum.algorithm` | `fractional_step` | §7 forward-ref | ◎ | — |
| `momentum.terms.convection.spatial` | `uccd6` | 06_L45 表「CCD/UCCD6/FCCD」並列 | ✗ | C-2 |
| `momentum.terms.viscosity.spatial` | `ccd` | §6.3 Layer A bulk | ◎ | — |
| `momentum.terms.pressure.formulation` | `pressure_jump` | §8 GFM/IIM (forward-ref) | ◎ | — |

### E-2. \\ref / \\cite / KL-12 / 禁止トークン scan 結果

- **\\ref ターゲット (36 件 / cross-chap)**: 全件 `\label` 定義先存在を確認 (`grep -c "\\label{<key>}" paper/sections/*.tex`)
- **\\cite キー (3 件: `Fedkiw1999`, `JiangPeng2000`, `JiangShu1996`)**: 全件 `paper/bibliography.bib` 存在確認
- **KL-12 unprotected math in heading**: 2 件検出 → C-3 (06d_L29, L109)
- **PR-1/PR-2/PR-6 forbidden tokens** (`PPESolverCCDLU` `LGMRES`): 0 件
- **CHK-222 V-5 forbidden identifiers** (`FCCDLevelSetAdvection` `SplitReinitializer`): 0 件

### E-3. A3 Traceability spot-check (§6 主要 eq label)

| eq label | docs/memo + src/ 言及 | 評価 |
|---|:-:|---|
| `eq:rho_update` | 1 件 | ◎ |
| `eq:mu_update` | 1 件 | ◎ |
| `eq:fccd_adv_face_value` | 0 件 | △ memo 不足 (実装関数名は `fccd_face_value` で対応) |
| `eq:fccd_adv_jet` | 0 件 | △ memo 不足 (実装関数名は `face_jet` で対応) |

A3 chain は eq→memo の文字列一致では一部欠落するが、実装関数名で対応取れているため **MINOR スコープ外** とし、本 memo の所見からは除外。後続 CHK で A3 chain explicit annotation を検討する余地あり。

---

## Section F: 修正コミット参照 + 関連 CHK

### 修正計画 (Step 4 で実施)
- C-1 → 06_scheme_per_variable.tex:47 編集
- C-2 → 06_scheme_per_variable.tex:45 編集
- C-3 → 06d_viscous_3layer.tex:29, L109 編集
- D-1 → 06_scheme_per_variable.tex:85-86 削除
- D-2 → 05b_cls_stages.tex 末尾に bridging 段落追加

### 検証 (Step 5)
- `cd paper && latexmk -xelatex main.tex` で再ビルド
- `grep -E "Undefined|Warning|Error" paper/main.log | head` で残警告ゼロ確認
- ページ数 ≤ 232pp (CHK-238 時点 231pp + bridging 1 段落 ≤ +1pp)

### 関連 CHK (時系列)
- [CHK-218](CHK-218-ch6-relocation-summary.md) — §6 章再配置
- [CHK-219](CHK-219-ch6-review-summary.md) — §6 移流レビュー
- [CHK-222](CHK-222-ch5-ch6-design-purify-summary.md) — §5/§6 design-purify
- [CHK-223](CHK-223-ch5-ch6-restructure-summary.md) — §5/§6/§7 三章分離
- **CHK-240 (本件)** — §6 厳正査読 + MAJOR/MINOR sweep 残骸最終解消

### 参考様式
- [CHK-228-ch11-algorithm-peer-review.md](CHK-228-ch11-algorithm-peer-review.md)
- [CHK-226-ch8-bf-ccd-peer-review.md](CHK-226-ch8-bf-ccd-peer-review.md)
