# CHK-222 — §5/§6 設計章 design-purify 完了サマリ

**Date**: 2026-04-26
**Phase**: PAPER_CH5_CH6_DESIGN_PURIFY
**Branch**: worktree-ra-paper-ch4-rewrite
**Predecessor**: CHK-221 (§5 Option A radical cleanup)

---

## 1. Trigger

CHK-221 完了後の追加査読でユーザより 6 件の懸念が提示された．いずれも「設計章 (§5/§6) に**実装詳細・ベンチマーク結果・由来不明数値**が混入し，読者を混乱させる」という共通根を持つ．

| # | 懸念 | §5 件数 | §6 件数 |
|---|---|---|---|
| 1 | DCCD legacy 言及不要 | 1 | 26 (5 ファイル) |
| 2 | 由来不明実数の濫用 (eps=1.4 / cfl=0.10 / θ_reinit=1.10 / ε_d^adv=0.05 等) | 7 | 13 |
| 3 | §6.3.4 Eikonal 推し ↔ §6.3.5 Eikonal 否定 (narrative inconsistency) | — | 1 (構造) |
| 4 | 毛管波 (BKZ / Brackbill / Δt_cap) 設計章混入 | 22 | 17 |
| 5 | 実装識別子 (FCCDLevelSetAdvection 等) | 4 | 16 |
| 6 | 測定結果 (体積保存 347%→0.02% / D=0.245 等) | 4 | 6 |

ユーザ判断 (確定):
- **Q1**: §4.4 DCCD 章 = **残置** (歴史的経緯保持; §5/§6 から ref のみ; §1 introduction にも 1 文補強)
- **Q2**: §6.3.4 + §6.3.5 = **統合** (Ridge-Eikonal 主軸; Eikonal 理論保証は前段 motivation)
- **Q3**: 本 CHK は §5/§6 削除のみ (ch13 検証章への measurements 実書込みは別 CHK = CHK-223 候補)

---

## 2. Phase 別作業内訳

| Phase | 主要作業 | §5 LOC delta | §6 LOC delta | commit |
|---|---|---|---|---|
| 1 | §5 DCCD 1 + 実装識別子 4 + YAML/dir 4 + mystery floats 7 + measurements 4 削除 | -25 | 0 | Phase 1 commit |
| 2 | §5.5 capillary subsection 50 LOC 削除 + remark block + per-term 17 箇所一般化 + §5.9 律速合成式 Δt_cap 削除 + Brackbill \cite 削除 | -75 | 0 | Phase 2 commit |
| 3 | §6 DCCD legacy 5 ファイル 26 箇所完全除去 (07b SplitReinitializer paragraph 80 LOC 削除 + Ridge-Eikonal 主軸再構成) | 0 | -150 | Phase 3 commit |
| 4 | §6.3.4 + §6.3.5 統合 (Eikonal 基盤 + Ridge 補正の単一節再構成; 比較表整理; phantomsection sec:eikonal_reinit alias) | 0 | -50 | Phase 4 commit |
| 5 | §6 mystery floats 13 + 実装識別子 16 + dir paths 5 削除 | 0 | -25 | Phase 5 commit |
| 6 | §6 毛管波 17 + measurements 6 完全除去 (flagship 「347%→0.02%」削除 / D=0.245 削除 / Prosperetti ref → §13 / 「適用制限 (2)」一行参照圧縮) | 0 | -100 | Phase 6 commit |
| 7 | V-grep verification (V-1..V-10) + 残 DCCD 修飾 3 箇所最終クリーンアップ + LEDGER + memo | 0 | -6 | Phase 7 commit + ledger/memo commit |

**§5 終状 LOC**: ~870 (CHK-221 終状 970 から -100; 主に §5.5 capillary subsection 削除分)
**§6 (07b) 終状 LOC**: 591 (~700 から -109; legacy + measurements + capillary 削除分)
**xelatex**: 256 pp (CHK-221 baseline 260 から -4 pp; 純削除)

---

## 3. 採択判断 (Q1/Q2/Q3)

### Q1: §4.4 DCCD 章をどうするか

| 選択肢 | 影響 | 採択 |
|---|---|---|
| 削除 (radical) | §1/§5/§6 から ref 一律削除; ch13 production stack purity 最大 | × |
| **残置 (歴史的経緯)** | §4.4 を「導出章」として保持; §5/§6 からは ref のみで参照; §1 intro に 1 文補強 | **○ (採択)** |

**理由**: DCCD 導出 (§4.4) は Lele 1992 / Sengupta-Sengupta 系統の理論的価値を持ち，paper 体系の連続性確保に必要．設計章 (§5/§6) からの言及を「歴史的経緯」と明示すれば，読者の混乱を回避しつつ研究系譜を保てる．

### Q2: §6.3.4 + §6.3.5 統合

| 選択肢 | 影響 | 採択 |
|---|---|---|
| 別節維持 + narrative 修正 | 「§6.3.4 Eikonal 法 → §6.3.5 Ridge-Eikonal はその修正版」と明示 | × |
| **統合 (1 節 / 3 段構成)** | 新 §6.3.4「Ridge-Eikonal: Eikonal 基盤と Ridge 補正の統合定式化」: 前段 (Eikonal motivation 30 LOC) + 中段 (limitation analysis) + 後段 (Ridge-Eikonal 定式) | **○ (採択)** |

**理由**: 別節維持は「Eikonal を推す → 否定」の対立構造が残り読者混乱が継続．統合により「Eikonal は理論保証を持つが Godunov 離散化由来のゼロセット drift; Ridge 補正で克服」という単一 narrative に整理できる．phantomsection sec:eikonal_reinit alias で外部参照を保持し外部影響を 0 化．

### Q3: ch13 検証章への measurements 実書込み

| 選択肢 | 影響 | 採択 |
|---|---|---|
| 本 CHK で ch13 (12_*.tex) 同時書込み | scope 拡大; ch13 narrative の独立性が損なわれる | × |
| **本 CHK は §5/§6 削除のみ + 「§13 参照」cross-ref のみ** | 別 CHK (CHK-223 候補) で ch13 verification 章に flagship 測定結果を構造化収納 | **○ (採択)** |

**理由**: ch13 検証章は physics-driven な独自 narrative (capillary wave dynamics / mass-loss diagnostics / convergence study) を持ち，paper §6 の Ridge-Eikonal 設計章から流用すべきではない．分離 CHK で ch13 integrity 確保．

---

## 4. KL-17 系 lessons learned

### KL-17-1: 「設計章 vs 検証章」境界 — 由来不明実数 / 測定結果 / 実装識別子の所属判定基準

**Issue**: §5/§6 設計章に `eps_scale=1.4`, `θ_reinit=1.10`, `ε_d^adv=0.05`, 「体積保存誤差 347% → 0.02%」, `\texttt{FCCDLevelSetAdvection}` が混在し，「設計の根拠」と「検証の数値」と「実装のディテール」が**章境界を跨いで散発**していた．

**判定基準** (CHK-222 で確立):

| 内容 | 設計章 (§5/§6) | 検証章 (§13) | 実装章 (付録 / コード) |
|---|---|---|---|
| 数式 / 演算子定義 | ○ (中心) | ref のみ | ref のみ |
| **由来不明実数** (経験的安全係数 etc) | ×; 「保守的安全余裕」等の概念表現 | ○ (測定値 + 由来) | ○ (YAML / config) |
| **測定結果** (誤差 / 収束率) | ×; 「§13 参照」cross-ref のみ | ○ (中心) | × |
| **実装識別子** (class/method/YAML key) | ×; 「FCCD 面ジェット移流」等の概念名 | △ (再現性のため class 名は許容) | ○ (中心) |
| 物理 CFL 数値 (Δt_cap = 1/√C_wave 等) | ×; 「界面張力 CFL 制約」一般表現 + ref | ○ (実測値 + ベンチマーク) | △ |
| 安定性条件 (eq:dt_sigma 定義式) | ○ (canonical 定義) | ref + 測定値 | ref |

**採択原則**: 設計章は「**why** (物理 / 数値解析の必然性)」を扱い，検証章は「**how much** (定量的検証)」を扱い，実装章は「**how** (具体的なコード実体)」を扱う．境界を跨いだ場合は読者は混乱する．

### KL-17-2: legacy 比較段落 (DCCD vs FCCD, Eikonal vs Ridge-Eikonal) の narrative tradeoff

**Issue**: 設計章で「**A** (旧手法) → 課題 → **B** (新手法) で克服」narrative は教育的価値が高いが，研究 paper としては「混乱源」になる．特に：

- **DCCD vs FCCD**: §6 で 26 箇所「DCCD legacy」言及が散発し，読者は「結局 ch13 production はどっち？」と迷う．
- **Eikonal vs Ridge-Eikonal**: §6.3.4 で Eikonal を「統一解」と推した直後に §6.3.5 で「Eikonal の根本欠陥を排除」と宣言する narrative inconsistency．

**判定基準**:

| 比較スタイル | 適用条件 | リスク |
|---|---|---|
| **散発比較** (per-term DCCD vs FCCD 言及) | 各演算子で legacy が広く認知されている場合 | × 読者の認知負荷; 「結局どっち」混乱 |
| **章末注記** (§4.4 への ref 1 行) | 旧手法に独立価値があり残置する場合 | ○ 採択 (CHK-222 Q1) |
| **統合 narrative** (前段 motivation + 後段 solution) | 旧手法が新手法の理論基盤を提供する場合 | ○ 採択 (CHK-222 Q2) |
| **完全削除** | 旧手法に独立価値なし | △ 研究系譜が失われるリスク |

**採択原則**: 設計章では「単一 narrative」を優先する．legacy は (1) 別章に隔離 + ref のみ，(2) 前段 motivation として統合，のいずれかに集約する．

### KL-17-3: 物理 CFL 制約 (capillary wave) の章間配分 — 設計の根拠 vs 検証の数値

**Issue**: 毛管波 CFL 制約 `Δt_cap = √(ρh³/2πσ)` (BKZ 1992) は (a) 設計章で「界面張力時間刻みの本質的下限」として根拠を述べる必要があるが，(b) 検証章で「具体ベンチマーク (Prosperetti 1981) での実測値」として定量検証する必要もある．**両方を設計章に置くと読者混乱**．

**判定基準** (CHK-222 で確立):

| 要素 | 配置先 | 例 |
|---|---|---|
| **CFL 制約定義式** (eq:dt_sigma) | 設計章 (§5 canonical) | eq:dt_sigma; §5 で 1 回 + §02b/§08/§10b/付録から ref |
| **物理的根拠** (毛管波分散関係 / 表面張力エネルギー均衡) | 設計章 (背景) | §5 適切な per-term 節で 1 段落程度 |
| **保守的安全係数の数値** (C_wave = 0.1-0.3 等) | 検証章 + 実装章 (YAML) | §5 では「保守的安全余裕」一般表現; 数値は §13/YAML |
| **ベンチマーク測定結果** (Prosperetti 振幅減衰率) | 検証章 (§13 中心) | §6 から削除 (CHK-222 Phase 6) |
| **specific YAML 数値** (cfl=0.10 等) | 実装章 (付録 / config) | 設計章から削除 (CHK-222 Phase 1/5) |

**採択原則**: 「数式 + 物理 (why) は設計章 / 数値 + 検証 (how much) は検証章 / config (how) は実装章」を厳守．`eq:dt_sigma` のような canonical 定義式は設計章に 1 回置き，他章は ref で参照する．

---

## 5. V-grep verification (V-1..V-10 全 pass)

| V-id | 検証項目 | 期待 | 結果 |
|---|---|---|---|
| V-1 | `grep -rc "DCCD\|Dissipative CCD\|SplitReinitializer" §5/§6` | 0 | 0 ✓ |
| V-2 | `grep -rc "ε_eff\|eps_scale=1.4\|f=1.4\|cfl=0.10\|restart 80\|θ_reinit=1.10" §5/§6` | 0 | 0 ✓ |
| V-3 | §6.3.4 narrative consistency (Eikonal motivation → Ridge-Eikonal solution が連続接続) | 一貫 | ✓ |
| V-4 | `grep -rc "毛管波\|BKZ\|capillary\|Prosperetti\|Brackbill" §5/§6` | 0 (Brackbill 1992 CSF 4 件は §5 で legitimate citation 残置 ≠ capillary-wave-CFL) | ✓ |
| V-5 | `grep -rc "FCCDLevelSetAdvection\|RidgeEikonalReinitializer\|UCCD6ConvectionTerm\|SplitReinitializer\|EikonalReinitializer" §5/§6` | 0 | 0 ✓ |
| V-6 | `grep -rc "experiment/ch13\|ns_pipeline\.py\|src/twophase" §5/§6` | 0 | 0 ✓ |
| V-7 | `grep -rc "347\\%\|0.245\|0.021\|3.5\\%\|0.15\\%" §5/§6` | 0 | 0 ✓ |
| V-8 | §5.5 「毛管波時間刻み制約」subsection 削除確認 | 削除済 | ✓ |
| V-9 | §6.3 SplitReinitializer paragraph 削除確認 | 削除済 | ✓ |
| V-10 | xelatex 2-pass clean | 256 pp / 0 undef / 0 multiply | ✓ |

---

## 6. 結果

- **§5 終状**: ~870 LOC (CHK-221 終状 970 から -100)
- **§6 (07b) 終状**: 591 LOC (~700 から -109)
- **xelatex**: 256 pp (CHK-221 baseline 260 から -4 pp; 純削除)
- **§4.4 (04c_dccd_derivation.tex)**: 歴史的経緯として残置 (§5/§6 から ref のみ; §1 introduction にも 1 文補強)
- **commit 7 件** (Phase 1-7) + **ledger/memo commit 1 件**
- **未完**: ch13 検証章への measurements 実書込みは CHK-223 候補; main マージ判断待ち

---

## 7. 次タスク候補

- **CHK-223** (推奨): ch13 検証章 (12_*.tex) への measurements 実書込み — flagship `347%→0.02%` / D=0.245/0.021 / Prosperetti 1981 ベンチマーク等を ch13 に構造化収納．
- **CHK-224** (推奨): main マージ判断 — CHK-219/220/221/222 (4 件) を順次 main へマージ．paper 主流の design-purify 完了を反映．
