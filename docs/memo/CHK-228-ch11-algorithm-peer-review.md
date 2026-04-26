# CHK-228 — §11 完全アルゴリズム章 査読官レビュー

**Date**: 2026-04-27
**Status**: REVIEW_ONLY (paper 編集なし; user 判断後 CHK-229 候補で paper 編集)
**Trigger**: ユーザより「11 章について査読官になったつもりで厳正にレビュー」+ 4 件事前懸念
**入力**: paper/sections/11_full_algorithm.tex (559 LOC) + 11b_level_selection.tex (284 LOC) + 11c_dccd_bootstrap.tex (60 LOC) + 11d_pure_fccd_dns.tex (250 LOC) = 計 1153 LOC
**出力**: 本 memo

> **読み替え注記**: 本 memo は paper 内の section 番号 (§11.1, §11.2, §11.3.x) を中心に議論する. file 名と章番号の対応は以下:
> - §11 (chapter) = `11_full_algorithm.tex` (chapter intro + §11.1 演算子マッピング + §11.2 完全アルゴリズム)
> - §11.3 = `11b_level_selection.tex` (Level 1/2/3 選択ロジック; 8 subsubsections)
> - §11.4 = `11c_dccd_bootstrap.tex` (bootstrap + timestep)
> - §11.5 = `11d_pure_fccd_dns.tex` (純 FCCD DNS アーキテクチャ; 8 subsubsections)

---

## ユーザ事前懸念 (4 件)

1. **Figure 8 がとにかく分かりづらい**
2. **§11.2 のような巨大なボックスを導入すべきでない**
3. **§11.3 Level のような分類定義はなくしました** (過去形 = 既に方針として deprecated)
4. **§11.3.8 実装の話は載せるつもりありません**

---

## Section A: 査読官のスタンスと総合判定

§11 章は paper 全体の **アルゴリズム集成章** として中核的役割を持つ — Step 1..7 の離散形式を一箇所に集約し, 各 Step が §3 (CLS), §6 (per-term), §7 (time integration), §9 (PPE) のどの式を呼び出すかを明示する. **理論的内容そのものは valid** であり削除対象ではない.

しかし **構成 (configuration) と framing に major revision を要する**:

- **§11.2 algbox** (`11_full_algorithm.tex:280-559`, **280 LOC**) は file 全体 559 LOC の **50% を占める単一 tcolorbox**. Step 1-7 + Optional step (Step 2b DGR / Step 5a HFE / Step 6a HFE) + Level 1/2/3 分岐 + DC 6 ステップ enumerate + Level 別 $L_H, L_L$ tabular を **1 つの box に collapse** した形. 「巨大ボックス」というユーザ懸念は LOC の絶対値で立証可能.
- **§11.3 (11b 全体)** は 284 LOC / 8 subsubsection で **Level 1/2/3 の独立節立て** の形をとる. ユーザの「分類定義はなくしました」(過去形) と整合させると, この構成自体が現在の方針と乖離している.
- **§11.3.8** (`sec:level_gpu_dual_path`, L261-285) は GPU 二路選択という **実装最適化** の話で, YAML キー (`time_integration.level`, `solver.architecture: split_fccd`), D2H/H2D 転送規律, PCR (Parallel Cyclic Reduction) アルゴリズム, 付録 GPU-FVM の 3 つの ref (app:gpu_fvm_ops/pcr/d2h) を含む. ユーザの「実装の話は載せない」方針と直接矛盾.
- **Figure 8** (`fig:algo_data_method_flow`, L118) は 28 nodes / 41 arrows の TikZ 図で, 4 種類の矢印スタイル (arr / auxarr / dep / 無名) を使うが caption は 3 色しか説明しない. `\resizebox{\textwidth}{!}` + `font=\scriptsize` → カラム幅組版で読めない可能性. さらに Figure 7 (`fig:ns_solvers` L33) と機能重複の疑いあり.

**総合判定: major revision**. 4 concerns はいずれも有効で, **互いに coupling している** — 懸念 3 (Level 分類削除) を adopt すれば 懸念 4 (§11.3.8 実装) は自動消滅し, さらに 懸念 2 (§11.2 algbox 内の Level 分岐) の圧縮も自動連動する. 故に 4 件を「個別パッチ」ではなく **構造的再編成として一括対処** すべき.

---

## Section B: 懸念 1 (Figure 8 が分かりづらい) の所見

### B-1: Figure 8 の所在と内容

- **所在**: [paper/sections/11_full_algorithm.tex:118](paper/sections/11_full_algorithm.tex#L118)
- **label**: `fig:algo_data_method_flow`
- **章配下**: §11.1 `sec:algo_operator_map` の末尾 (L24 で §11.1 開始, L271 で §11.2 開始, L118 はその間)
- **構造**: TikZ 図, 5 ノードスタイル (data / method / optmethod / term / aux), 4 矢印スタイル (arr 実線 / auxarr 紫破線 / dep ティール破線 / 無名), **計 28 ノード + 41 矢印**
- **caption** (L222-227): 3 種ノードの説明 (data 青角丸 / method 橙 / aux 紫破線), φ↔ψ 補助変換の言及, **dep ティール破線の凡例は欠落**

### B-2: 分かりづらさの 5 要因

| # | 要因 | 詳細 |
|---|------|------|
| B-2-1 | **ノード密度過多** | 28 ノード + 41 矢印 = 1 図に密集. data(8) + method(11) + optmethod(1) + term(4) + aux(4) の 5 種ノードが横 22 単位幅に並ぶ |
| B-2-2 | **scriptsize で読めない** | `\resizebox{\textwidth}{!}` + `font=\scriptsize` の組み合わせ. 紙面幅でノードラベルが拡大されるが scriptsize 起点なので最終サイズが小さくなる傾向 |
| B-2-3 | **caption 説明不足** | 4 種矢印のうち caption には 3 色しか記載なし. `dep` (ティール破線, 物性依存) の意味が読み取れない |
| B-2-4 | **データフロー + 依存性の重ね描き** | `auxarr` (ψ→φ 補助変換) と `dep` (物性依存) が同一キャンバスで色違いに描かれているため, 「方向性」と「依存性」のどちらの図かが unclear |
| B-2-5 | **Figure 7 と役割重複** | [paper/sections/11_full_algorithm.tex:33](paper/sections/11_full_algorithm.tex#L33) `fig:ns_solvers` (NS 各項とソルバー対応図) と Figure 8 (データ依存関係図) は **「7 ステップ概観表」(§11.2 algbox 直前の paragraph) と合わせて triple representation** になっている |

### B-3: 修正候補 4 件

| 候補 | 戦略 | LOC | リスク |
|-----|-----|-----|-------|
| B-3-α | **削除** (Figure 7 + Table 1 で代替可) | -110 LOC (L118-228) | 低; 図 7 で「何を使うか」, 7 step 概観表で「順序」が分かるなら図 8 は冗長 |
| B-3-β | **2 figure に分割** (界面系図 + NS/圧力系図) | ±0 LOC | 中; ノード半減で読みやすいが本数が増える |
| B-3-γ | **Figure 7 へ統合** (NS solver + データフロー一体化) | -50 LOC | 中; 統合後の図が大きくなる可能性 |
| B-3-δ | **§11.2 algbox 直前へ移動** (現在は §11.1 末尾) | ±0 LOC, 位置変更のみ | 低; 「7 ステップを構成するデータの流れ」として algbox の context 補強 |

**B 結論**: 候補 α (削除) または δ (移動) が穏当. β/γ は「分かりやすくする」ための積極的書き直しで CHK-228 範囲外 (paper 編集が必要).

---

## Section C: 懸念 2 (§11.2 巨大ボックス) の所見

### C-1: §11.2 algbox の現状

- **所在**: [paper/sections/11_full_algorithm.tex:280-559](paper/sections/11_full_algorithm.tex#L280-L559)
- **style**: `tcolorbox` with `algbox` style
- **title**: 「1 タイムステップ $t^n \to t^{n+1}$ の完全アルゴリズム」
- **LOC**: **280 行** (file 559 LOC の **50%**)

### C-2: 内部構造 (12 paragraph + 6 環境)

```
[Step 1: CLS 移流]      paragraph + align*(3行 TVD-RK3)
[Step 2: 再初期化]       paragraph + equation
[Step 2b: DGR 厚み補正] paragraph + 数式 3本   ← Optional step
[Step 3: 物性更新]       paragraph + align*
[Step 4: 曲率計算]       paragraph + align* + equation*
[Step 5: 運動量予測]     paragraph + align* + Level 2a/2b 分岐
                        + textbf "粘性 Helmholtz 系の呼び出し順" + enumerate(3項)
                        + textbf "注意 (移動界面 + 表面張力)"      ← ~45 LOC
[Step 5a: HFE 延長]    paragraph              ← Optional step
[Step 6: 圧力 Poisson]  paragraph + textbf "Level 別 PPE 主方程式"
                        + itemize(Level 1/2 + Level 2b/3 の 2 項; 内部 equation)
                        + equation aligned (PPE_CCD_fullalgo, 5 行)
                        + enumerate(Step 6.0..6.5 = DC 6 step)
                        + tabular (Level 別 L_H, L_L 定義)
                        + textbf "精度に関する補足"               ← ~80 LOC
[Step 6a: HFE 延長 (δp)] paragraph             ← Optional step
[Step 7: Corrector]    paragraph + align* + itemize(均一/非一様 2 項)
```

### C-3: 「巨大」と感じる構造的要因

| # | 要因 | 詳細 |
|---|------|------|
| C-3-1 | **絶対 LOC** | 280 LOC/single tcolorbox. CHK-227 の §9.7 mybox (42 LOC) や §11.1 defbox (39 LOC) と桁違い |
| C-3-2 | **Optional step 紛れ込み** | Step 2b (DGR) / Step 5a (HFE) / Step 6a (HFE δp) は **条件付きオプション**. 必須フロー Step 1-7 と同じ visual weight で扱われ, 読者は判別しながら読む必要 |
| C-3-3 | **Level 分岐 inline 展開** | Step 5 で Level 2a/2b 分岐を展開, Step 6 で Level 別 PPE 主方程式を展開. これは §11.3 (Level 選択ロジック) と内容重複 |
| C-3-4 | **DC 6 step enumerate** | Step 6 内に DC k 反復の Step 6.0..6.5 を 6 項 enumerate で展開. 本来 §9.5 (defect correction 章) に属する内容 |
| C-3-5 | **Level 別 $L_H, L_L$ tabular** | Step 6 内 Level 別演算子 tabular. これも §9 (PPE 章) または §11.3 に属する |
| C-3-6 | **環境ネスト 3 層** | tcolorbox > itemize > equation のネスト構造で組版負荷 + 視覚的密度高 |

### C-4: 修正候補 4 件

| 候補 | 戦略 | LOC | リスク |
|-----|-----|-----|-------|
| C-4-α | **Optional step を別 box に切り出し** | -30 LOC (Step 2b/5a/6a を separate optbox) | 低 |
| C-4-β | **Level 分岐を §11.3 ref に委譲** | -50 LOC (Step 5/6 inline Level 分岐削除 → ref のみ) | 低 (ただし §11.3 削除案 (D-3-α/β) と整合確認要) |
| C-4-γ | **DC 6 step + Level tabular を §9 ref に委譲** | -60 LOC (Step 6 内 DC 詳細削除 → ref) | 中 (§9 章末まとめとの整合確認要) |
| C-4-δ | **Step 1-7 必須フローのみ + ref 委譲 (α + β + γ 統合)** | **-150 LOC** (algbox を 130 LOC 程度に圧縮) | 中 |

**C 結論**: 候補 δ (Step 1-7 必須のみ + ref 委譲) が user の「巨大ボックスを導入すべきでない」方針と最も整合. ただし **DC 6 step や Level 別演算子 tabular の冗長な展開を §9/§11.3 で済ませている前提** が必要 — §9 と §11.3 で既に書かれているなら algbox は概略のみで済む.

---

## Section D: 懸念 3 (§11.3 Level 分類定義削除) の所見

### D-1: §11.3 (11b) の現状

- **file**: [paper/sections/11b_level_selection.tex](paper/sections/11b_level_selection.tex) (284 LOC)
- **構成**: 1 subsection + **8 subsubsection**

| § | 行 | label | タイトル |
|---|---|------|---------|
| §11.3 | L6 | `sec:level_selection` | Level 1/2/3 選択ロジックとコスト-精度トレードオフ |
| §11.3.1 | L18 | `sec:level_trigger` | Level 選択トリガー：剛性レジームの自動判定 |
| §11.3.2 | L69 | `sec:dc_pure_fccd_convergence` | 純 FCCD DNS での収束率 (Level 別 DC k 上界) |
| §11.3.3 | L108 | `sec:level_cost_accuracy` | Level 間コスト-精度トレードオフ |
| §11.3.4 | L155 | `sec:level1_validation` | バリデーション Level: Level 1 の役割 |
| §11.3.5 | L177 | `sec:level2_production` | プロダクション Level: Level 2 の既定 |
| §11.3.6 | L206 | `sec:level3_stiff_regime` | 極端剛性 Level: Level 3 の適用窓 |
| §11.3.7 | L229 | `sec:level_physics_matrix` | Level 選択マトリクス (物理 → 推奨) |
| §11.3.8 | L261 | `sec:level_gpu_dual_path` | Level 2 プロダクションでの GPU 二路選択 |

8 subsubsection 全てが Level 1/2/3 分類前提で書かれている.

### D-2: ユーザの「分類定義はなくしました」(過去形) の解釈

ユーザは過去形で「なくしました」と述べている. これは **既に paper 全体の方針として「Level 1/2/3 を独立節立てしない」が決定済** という意味と解釈する. CHK-227 で §9 章の 4 concerns を確認した時点では Level 言及はあったが, それ以降に user の方針が固まったか, あるいは別ファイル (例: §10 grid 章) では既に Level 言及を削除している可能性がある.

確認: §10 (`10_grid.tex` 等) や §1 (`01_introduction.tex`) で Level 1/2/3 が現状どう扱われているかを次 CHK で確認すべき.

### D-3: §11.3 削除影響 — outbound \ref cascade

§11 内部から `sec:level_*` への **\ref が 11 件**:

| from | line | to | context |
|------|------|------|---------|
| `11_full_algorithm.tex` | L16 | `sec:level_selection` | chapter intro enumerate |
| `11_full_algorithm.tex` | L442 | `sec:level_physics_matrix` | Step 6 Level 2a 説明中 |
| `11_full_algorithm.tex` | L444 | `sec:level_selection` | DC 残差 plateau 切替推奨 |
| `11_full_algorithm.tex` | L522 | `sec:level_selection` | Step 6 精度補足末尾 |
| `11c_dccd_bootstrap.tex` | L52 | `sec:level_selection` | timestep §11.x 関係説明 |
| `11c_dccd_bootstrap.tex` | L54 | `sec:level_selection` + `eq:level_cfl_min` | 3 項 min 言及 |
| `11d_pure_fccd_dns.tex` | L13 | `sec:level3_stiff_regime` | Level 3 完全構成冒頭 |
| `11d_pure_fccd_dns.tex` | L31 | `sec:level2_production` | Phase 1 軽量版参照 |
| `11d_pure_fccd_dns.tex` | L32 | `sec:level_selection` | Phase 1-4 同時採用前提 |
| `11d_pure_fccd_dns.tex` | L173 | `sec:level2_production` | 純 FCCD ⟷ Level 2 補完関係 |
| `11d_pure_fccd_dns.tex` | L242 | `sec:level2_production` | 移植経路 |

加えて **equation label** も消滅する: `eq:level_cfl_min` (CFL 3 項 min) と `eq:level2_dt` (Level 2 Δt 式).

**外部参照** (§11 以外からの ref): 別途 paper 全体で grep が必要だが, CHK-228 範囲外として deferred. 想定では §1 (chapter overview), §10 (grid), §13 (benchmarks) からの言及があり得る.

### D-4: 修正候補 4 件

| 候補 | 戦略 | LOC | リスク |
|-----|-----|-----|-------|
| D-4-α | **§11.3 全削除** + Level 言及を本文 inline 化 | -284 LOC | 高; 11 件 \ref 整理 + algbox 内 Level 分岐削除 + §11d Level 言及書換 cascade |
| D-4-β | **§11.3 を 1 page に圧縮** (Table 2 個 = §11.3.1 trigger + §11.3.7 matrix のみ keep, 他 6 subsubsection 削除) | -200 LOC | 中; 6 件 \ref redirect (§11.3.4/5/6 → §11.3.7 matrix へ) |
| D-4-γ | **§7 (時間積分) へ移管** + §11.3 削除 | -284 LOC, +50 LOC (§7) | 高; ref を §7 alias へ書換 + §11d 整合 |
| D-4-δ | **現状維持** + algbox 内の Level 分岐のみ §11.3 ref に集約 | ±0 LOC | 低 (ただし user 方針「なくしました」と矛盾) |

**D 結論**: ユーザ方針 (過去形「なくしました」) を厳格に解釈するなら **D-4-α (全削除)** が直接整合. ただし \ref cascade が大きく, paper 全体の Level 言及 (§1/§10/§13 等) 整理も同時に行う必要 → CHK-228 範囲外. **D-4-β (1 page 圧縮)** は妥協案で, 「分類定義の独立節立て」を解消しつつ Table 2 個で実用情報を保持.

---

## Section E: 懸念 4 (§11.3.8 実装の話) の所見

### E-1: §11.3.8 の現状

- **所在**: [paper/sections/11b_level_selection.tex:261-285](paper/sections/11b_level_selection.tex#L261-L285)
- **label**: `sec:level_gpu_dual_path`
- **タイトル**: 「Level 2 プロダクションでの GPU 二路選択」
- **LOC**: 25 行

### E-2: 実装言語の inventory

| # | 種別 | 内容 | 行 |
|---|------|-----|---|
| E-2-1 | YAML キー | `time_integration.level: 1\|2\|3` (\verb 形式) | `11b:255` (§11.3.7 末尾, §11.3.8 隣接) |
| E-2-2 | YAML キー | `solver.architecture: split_fccd` (\verb 形式) | `11d:177` (§11.5 内, 別ファイル) |
| E-2-3 | GPU API 分類 | D2H / H2D 転送規律 | `11b:273` |
| E-2-4 | アルゴリズム名 | 可変バッチ PCR (Parallel Cyclic Reduction) | `11b:272` |
| E-2-5 | 付録 ref | `app:gpu_fvm_ops` (演算子カリキュラス) | `11b:271` |
| E-2-6 | 付録 ref | `app:gpu_fvm_pcr` (可変バッチ PCR) | `11b:272` |
| E-2-7 | 付録 ref | `app:gpu_fvm_d2h` (転送規律) | `11b:273` |

### E-3: 実装の話の影響範囲

§11.3.8 単体だけでなく **隣接箇所にも実装言語が漏出** している:

- §11.3.7 末尾 (`11b:254-255`): YAML キー `time_integration.level` 言及
- §11.5 (§11d L177): YAML キー `solver.architecture: split_fccd`
- §11.5.8 (§11d L215-248): Phase 1-9 実装ロードマップ表 (移植経路)

ユーザ方針「実装の話は載せるつもりありません」を厳格適用するなら, §11.3.8 削除に加えて **隣接 4 箇所も同時整理** が必要.

### E-4: 修正候補 3 件

| 候補 | 戦略 | LOC | リスク |
|-----|-----|-----|-------|
| E-4-α | **§11.3.8 削除** + §11.3.7 末尾 YAML 削除 + §11d L177 YAML 削除 | -30 LOC | 低; 付録 GPU-FVM への ref が外れるが付録は self-contained |
| E-4-β | **付録へ移動** (§11.3.8 全文を `appendix_gpu_fvm.tex` 冒頭へ) | -25 LOC (本文), +25 LOC (付録) | 低 |
| E-4-γ | **1 行ノートに圧縮** (「実装上は Level 2 で 2 経路 (smoothed Heaviside / GPU-FVM); 詳細は付録 H 参照」のみ) | -20 LOC | 低 |

**E 結論**: 候補 α (削除) が user 方針と最も整合. β/γ は妥協案だが「実装の話を載せない」方針には完全には合致しない.

---

## Section F: 4 concerns の coupling

4 concerns は **互いに依存関係** がある:

```
懸念 3 (§11.3 削除/圧縮)
   ├── 懸念 4 (§11.3.8 実装) を自動消滅 (§11.3.8 は §11.3 の subsubsection)
   ├── 懸念 2 (§11.2 algbox の Level 分岐) を自動圧縮 (§11.3 ref 委譲先が消えるので inline 化 → 削除へ)
   └── §11d (§11.5) の Level 言及書き直しが必要 (5 件 \ref が §11.3 へ)

懸念 1 (Figure 8) は §11.1 内部問題で他と独立だが,
   §11.2 algbox 圧縮 (懸念 2) と合わせれば §11.1+§11.2 全体スリム化に貢献
```

**結果として 4 concerns は「§11.3 を削除/圧縮」を中心に集約可能** であり, 個別パッチではなく **構造再編成として一括対処** が効率的.

---

## Section G: §11 narrative arc 評価

### G-1: 現状 narrative

```
§11 chapter intro
   └── enumerate(7 項目): Level 1/2/3 概観 + 7 step 概観 + 演算子家族
        ↓
§11.1 演算子マッピング
   ├── Figure 7: NS 各項 ⟷ ソルバー対応
   ├── Figure 8: データ依存関係 + 計算方式分離
   └── defbox: 離散演算子記法
        ↓
§11.2 完全アルゴリズム (algbox 280 LOC)
   └── Step 1..7 + Optional + Level 分岐 + DC 6 step + Level tabular
        ↓
§11.3 Level 選択ロジック (8 subsubsection)
   └── trigger / 収束率 / コスト-精度 / Level 1 / Level 2 / Level 3 / matrix / GPU 二路
        ↓
§11.4 bootstrap + timestep
   └── 末尾 1 行のみ章末締め (\bigskip + 1 文)
        ↓
§11.5 純 FCCD DNS (8 subsubsection, 250 LOC)
   └── 設計命題 / Phase 1-4 / 位置付け / Acceptance Gate / 移植 roadmap
```

### G-2: 構造的問題

| # | 問題 | 詳細 |
|---|------|------|
| G-2-1 | **Level 三重出現** | chapter intro の Level 概観 → §11.2 algbox 内の Level 分岐 → §11.3 で再度詳述 = triple repetition |
| G-2-2 | **Optional step の埋没** | §11.2 algbox 内 Step 2b/5a/6a が必須 step と同じ visual weight |
| G-2-3 | **章末まとめ欠落** | `11c:58-61` の `\bigskip` + 1 文 ("以上の統合アルゴリズムの各構成要素が設計通りの精度を達成するか, 次章で系統的にコンポーネント単位の数学的検証を行う.") のみ. 専用 `\subsection{まとめ}` 不在 |
| G-2-4 | **§11.5 (§11d) の位置付け曖昧** | 「Level 3 完全構成」と銘打つが §11.3.6 (Level 3) と内容重複. Pure FCCD DNS が独立 subsection として十分か, §11.3.6 へ統合すべきか? |
| G-2-5 | **§11.3.8 の異質性** | §11.3.1..7 は Level 分類論で, §11.3.8 のみ GPU 実装最適化 → 性質の異なる subsubsection が同列扱い |

### G-3: narrative 改善方向

ユーザ方針 (4 concerns 全部 adopt) に従えば, 改善後の narrative は:

```
§11 chapter intro          ← Level 言及なし (本文 inline 化)
   ↓
§11.1 演算子マッピング     ← Figure 7 のみ (Figure 8 削除); defbox keep
   ↓
§11.2 完全アルゴリズム     ← algbox は Step 1-7 必須のみ (130 LOC)
   ↓
§11.3 → 削除 or 1 page 圧縮 (Level 分類のみ)
   ↓
§11.4 bootstrap + timestep + 章末まとめ追加
   ↓
§11.5 純 FCCD DNS         ← Level 言及書換 + Phase 移植 roadmap 整理
```

LOC 全体: 1153 → ~600 (≈ -550 LOC, 50% 削減).

---

## Section H: 再構成 options 3 案 (H-α/β/γ)

| Option | 戦略 | LOC 影響 | 外部 ref 影響 | リスク |
|---|---|---|---|---|
| **H-α (minimal)** | Figure 8 削除 + §11.3.8 削除 + algbox 内 Optional step を脚注化のみ. §11.3 (Level 分類) は keep. | -50 LOC | 0 件 (§11.3 label 不変) | **低**; ただし「分類定義はなくしました」(過去形) との整合は弱い |
| **H-β (moderate)** | H-α + §11.3 を 1 page subsection に圧縮 (Table 2 個 = §11.3.1 trigger + §11.3.7 matrix のみ keep, 他 6 subsubsection 削除) + §11.3.8 完全削除 + §11.3.7 末尾 YAML 削除 + algbox 内 Level 分岐を §11.3 ref に委譲 | **-200 LOC** | 中 (10 件 \ref のうち 6 件 redirect) | 中; user 方針との整合性高 |
| **H-γ (radical)** | H-β + §11.3 完全削除 + Level 分類を §7 (時間積分) または §1 chapter intro へ移管 + §11.2 algbox を Step 1-7 必須のみに圧縮 (DC 6 step + Level tabular を §9 ref に委譲) + Figure 8 削除 + §11d Phase 1-9 移植経路を簡素化 | **-550 LOC** | **高** (11 件 \ref alias 必須 + paper 全体の Level 言及整理) | 高; ただし user 方針 (Level 分類なし + 実装話なし) を完全実装 |

---

## Section I: User 判断要請 (Q1-Q4)

### Q1: Figure 8 (`fig:algo_data_method_flow` L118) の処理

- (a) **削除** — Figure 7 + 7 step 概観表で十分 (推奨)
- (b) **2 figure に分割** (界面系 + NS/圧力系)
- (c) **Figure 7 へ統合**
- (d) **§11.2 algbox 直前へ移動** (位置のみ変更; 内容は keep)
- (e) **現状維持** (分かりづらいが他で代替不能)

### Q2: §11.2 algbox (L280-559) の処理

- (a) **現状維持**
- (b) **Optional step を脚注化** (-30 LOC)
- (c) **Level 分岐を §11.3 ref に委譲** (-50 LOC)
- (d) **DC 6 step + Level tabular を §9 ref に委譲** (-60 LOC)
- (e) **Step 1-7 必須のみに圧縮** (b+c+d 統合; **-150 LOC**)

### Q3: §11.3 Level 分類 (11b 全体 284 LOC) の処理

- (a) **全削除** + 本文 inline 化 (D-4-α; **-284 LOC**, \ref 11 件 cascade)
- (b) **1 page 圧縮** (Table 2 個のみ keep, 他 6 subsubsection 削除; D-4-β; -200 LOC, \ref 6 件 redirect)
- (c) **§7 時間積分章へ移管** (D-4-γ; -284 LOC + §7 +50 LOC)
- (d) **現状維持** + algbox 内 Level 分岐のみ §11.3 ref 集約 (D-4-δ; ユーザ方針と矛盾)

### Q4: §11.3.8 + 隣接実装言語の処理

- (a) **§11.3.8 削除 + §11.3.7 末尾 YAML 削除 + §11d L177 YAML 削除** (E-4-α; -30 LOC)
- (b) **付録 GPU-FVM へ移動** (E-4-β)
- (c) **1 行ノートに圧縮** (E-4-γ; -20 LOC)

---

## Section J: ch13 production との fact-check

CHK-226 で確定した **ch13 production = `pressure_jump` formulation = 戦略 C** との整合性:

| # | §11 記述 | ch13 production 実態 | 整合性 |
|---|---------|---------------------|-------|
| J-1 | §11.3.5 「Level 2 = プロダクション既定」 | ch13 = Lv.2 で動作中 | ✅ 整合 |
| J-2 | §11.3.6 「Level 3 = 極端剛性レジーム」 | ch13 では Lv.3 不使用 (研究 DNS 用) | ✅ 整合 |
| J-3 | §11.3.5 内 PPE 形式 | ch13 = `pressure_jump` (= 戦略 C) | ⚠ §11.3.5 が CSF body force 前提なら不整合 (CHK-226 と同根) |
| J-4 | §11.3.8 GPU 二路選択 (Lv.2 内) | ch13 production = 経路 A (smoothed-Heaviside) | ✅ 整合 (§11.3.8 削除しても production には影響なし) |
| J-5 | §11.5 (§11d) 純 FCCD DNS = 「Level 3 完全構成」 | ch13 production = Lv.2 のため §11.5 は研究 DNS 用 | ✅ 整合 |

**ch13 production 観点では §11.3.5 の PPE 形式記述** (CSF vs phase-PPE) が CHK-226 の §8 BF 章と coupling し, 別途 §11.3.5 が CSF body force 前提で書かれているなら CHK-226 で user が選択した E-α (CSF primary 現状維持) との整合性確認が必要.

---

## Section K: Advisory

### K-1: 推奨 option

CHK-226 で user が **E-α (minimal; CSF primary 現状維持)** を選択した historical context から, **CHK-228 でも H-β (moderate) が自然な流れ**. ただし:

- ユーザの「**なくしました**」(過去形) は方針が既に固まっていることを示唆. これを厳格解釈するなら **H-γ (radical)** が user 意図と最直接.
- ただし H-γ は \ref cascade が大きく (11 件 + paper 全体の Level 言及整理), paper 全体の構造変更を伴う → **CHK-228 では H-β に留め, H-γ への移行は次々 CHK で別途検討** が安全.

### K-2: 4 concerns 個別の優先度

ユーザの言い方の強さで並べると:

1. **「載せるつもりありません」(§11.3.8)** — 最強 (絶対削除方針)
2. **「分類定義はなくしました」(§11.3)** — 強 (過去形 = 既定路線)
3. **「導入すべきでない」(§11.2 巨大ボックス)** — 中 (改善希望)
4. **「とにかくわかりづらい」(Figure 8)** — 中 (改善希望)

→ 個別パッチ路線を取るなら **§11.3.8 削除 + §11.3 圧縮** を最優先, **§11.2 algbox 圧縮 + Figure 8 削除/移動** は次優先.

### K-3: 査読官として最も注意すべき点

§11 章は **paper 全体の「アルゴリズム集成」役割** を持つため, 削除しすぎると **ch13 production の再現可能性** (Step 1-7 の具体的離散式が不明瞭になる) が損なわれるリスクがある. 特に §11.2 algbox の Step 5/6 の離散式は **paper 中で唯一の「全 Step を一望できる」記述** であり, 圧縮するなら **個別 Step は §6 (per-term)/§7 (time int)/§9 (PPE) に書かれている前提を verify** してからにすべき.

→ CHK-228 で memo 提出 → user の Q1-Q4 判断 → CHK-229 候補で paper 編集 (option H-α/β/γ いずれか) → CHK-230 で verification (xelatex clean + 256 pp 維持確認).

---

## 付録 A: §11 section/subsection 構造マップ

| ファイル | 行 | コマンド | タイトル | label |
|---------|---|---------|---------|------|
| `11_full_algorithm.tex` | 4 | `\section` | 完全アルゴリズムフロー：離散形式 | `sec:algorithm` |
| 〃 | 24 | `\subsection` | 演算子マッピングと全体概観 | `sec:algo_operator_map` |
| 〃 | 271 | `\subsection` | 完全アルゴリズム：離散形式 | `sec:algo_flow` |
| `11b_level_selection.tex` | 6 | `\subsection` | Level 1/2/3 選択ロジックとコスト-精度トレードオフ | `sec:level_selection` |
| 〃 | 18 | `\subsubsection` | Level 選択トリガー：剛性レジームの自動判定 | `sec:level_trigger` |
| 〃 | 69 | `\subsubsection` | 純 FCCD DNS での収束率 (Level 別 DC k 上界) | `sec:dc_pure_fccd_convergence` |
| 〃 | 108 | `\subsubsection` | Level 間コスト-精度トレードオフ | `sec:level_cost_accuracy` |
| 〃 | 155 | `\subsubsection` | バリデーション Level: Level 1 の役割 | `sec:level1_validation` |
| 〃 | 177 | `\subsubsection` | プロダクション Level: Level 2 の既定 | `sec:level2_production` |
| 〃 | 206 | `\subsubsection` | 極端剛性 Level: Level 3 の適用窓 | `sec:level3_stiff_regime` |
| 〃 | 229 | `\subsubsection` | Level 選択マトリクス (物理 → 推奨) | `sec:level_physics_matrix` |
| 〃 | 261 | `\subsubsection` | Level 2 プロダクションでの GPU 二路選択 | `sec:level_gpu_dual_path` |
| `11c_dccd_bootstrap.tex` | 16 | `\subsection` | ブートストラップ処理 | `sec:bootstrap` |
| 〃 | 27 | `\subsection` | タイムステップ制御 | `sec:algo_timestep` |
| `11d_pure_fccd_dns.tex` | 6 | `\subsection` | 純 FCCD DNS アーキテクチャ：Level 3 完全構成 | `sec:pure_fccd_dns` |
| 〃 | 35 | `\subsubsection` | 設計命題：高次演算子の共通基準面位置 | `sec:pure_fccd_thesis` |
| 〃 | 56 | `\subsubsection` | Phase 1: 界面追跡層 (Ridge-Eikonal + FCCD 輸送) | `sec:pure_fccd_phase1` |
| 〃 | 81 | `\subsubsection` | Phase 2: 運動量移流層 (FCCD + HFE) | `sec:pure_fccd_phase2` |
| 〃 | 103 | `\subsubsection` | Phase 3: 粘性項の応力発散 + DC 分離 | `sec:pure_fccd_phase3` |
| 〃 | 121 | `\subsubsection` | Phase 4: 分相 FCCD PPE + GFM の中核アーキテクチャ | `sec:pure_fccd_phase4` |
| 〃 | 153 | `\subsubsection` | CFD 位置付け：研究 DNS / シャープ界面極限 | `sec:pure_fccd_positioning` |
| 〃 | 180 | `\subsubsection` | Acceptance Gate と検証計画 | `sec:pure_fccd_gates` |
| 〃 | 215 | `\subsubsection` | 実装ロードマップと Level 2 への移植経路 | `sec:pure_fccd_roadmap` |

---

## 付録 B: Figure 8 詳細 inventory

- **行**: `11_full_algorithm.tex:118-228` (caption 含む)
- **環境**: `figure[htbp]` + `\resizebox{\textwidth}{!}{...}` + `tikzpicture`
- **font**: `font=\scriptsize`
- **ノードスタイル**: 5 種 (`data` 青角丸 / `method` 橙 / `optmethod` 橙細線 / `term` 灰 / `aux` 紫破線)
- **ノード総数**: **28** (data 8 + method 11 + optmethod 1 + term 4 + aux 4)
- **矢印スタイル**: 4 種 (`arr` 実線 / `auxarr` 紫破線 / `dep` ティール破線 / 無名)
- **矢印総数**: **41**
- **caption**: 3 色しか説明なし (data 青 / method 橙 / aux 紫破線). **`dep` ティール破線の凡例欠落**

---

## 付録 C: §11.2 algbox 内部構造詳細

| Step | LOC 推定 | 環境内訳 |
|------|---------|---------|
| Step 1: CLS 移流 | ~10 | paragraph + `align*` (3 行 TVD-RK3) |
| Step 2: 再初期化 | ~10 | paragraph + `equation` |
| Step 2b: DGR 厚み補正 (Optional) | ~15 | paragraph + 3 数式 |
| Step 3: 物性更新 | ~10 | paragraph + `align*` |
| Step 4: 曲率計算 | ~15 | paragraph + `align*` + `equation*` |
| **Step 5: 運動量予測** | **~45** | paragraph + `align*` + Level 2a/2b 分岐 + `enumerate`(3 項) + 注意 textbf |
| Step 5a: HFE 延長 (Optional) | ~5 | paragraph |
| **Step 6: 圧力 Poisson** | **~80** | paragraph + textbf + `itemize`(2 項 + 内部 `equation`) + `equation aligned`(5 行) + `enumerate`(6 項 = DC) + `tabular`(Level 別 $L_H, L_L$) + textbf |
| Step 6a: HFE 延長 (δp) (Optional) | ~5 | paragraph |
| Step 7: Corrector | ~25 | paragraph + `align*` + `itemize`(2 項) |
| (paragraph 間スペース) | ~60 | (空行 + コメント) |
| **合計** | **~280** | 12 paragraph + 6 内部環境 |

---

## 付録 D: §11.3 削除影響 — outbound \ref cascade

| from | line | to label | redirect 候補 |
|------|------|---------|--------------|
| `11_full_algorithm.tex` | L16 | `sec:level_selection` | 削除 (chapter intro inline 化) |
| 〃 | L442 | `sec:level_physics_matrix` | §11.3.7 圧縮版 (D-4-β) or 削除 (D-4-α) |
| 〃 | L444 | `sec:level_selection` | 同上 |
| 〃 | L522 | `sec:level_selection` | 同上 |
| `11c_dccd_bootstrap.tex` | L52 | `sec:level_selection` | §7 (時間積分) ref へ |
| 〃 | L54 | `sec:level_selection` + `eq:level_cfl_min` | §7 + eq alias |
| `11d_pure_fccd_dns.tex` | L13 | `sec:level3_stiff_regime` | §11.5 chapter intro inline 化 |
| 〃 | L31 | `sec:level2_production` | 削除 |
| 〃 | L32 | `sec:level_selection` | 削除 |
| 〃 | L173 | `sec:level2_production` | 削除 |
| 〃 | L242 | `sec:level2_production` | §11.3.7 圧縮版 (D-4-β) or 削除 |
| **計** | **11 件** | | |

加えて **equation label** 消滅: `eq:level_cfl_min`, `eq:level2_dt`.

---

**memo 終わり**

後続: user の Q1-Q4 判断 → CHK-229 候補で §11 paper 編集 (option H-α/β/γ いずれか + Q1-Q4 個別選択) → CHK-230 で verification (xelatex clean + page count 維持確認).

main マージ: ユーザ判断 (CHK-226/227 のパターン: review-only memo は --no-ff merge してから worktree 継続使用).
