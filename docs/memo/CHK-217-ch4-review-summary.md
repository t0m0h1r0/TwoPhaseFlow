# CHK-217: §4 (CCD 章) 査読官視点レビュー + narrative 精緻化 — 完了サマリ

**Date**: 2026-04-26
**Branch**: `worktree-ra-paper-ch4-rewrite` (CHK-216 main マージ済 e243777; CHK-217 8 commit 未マージ)
**Status**: DONE (Critical 0 / Major 0 / Minor 0 / Nit 0 残)

---

## 経緯

CHK-216 (§4 抜本改稿 + 純化) main 取込後，ユーザから 4 件の追加 narrative
違和感が指摘された．

| # | ユーザ指摘 | 解決 phase |
|---|---|---|
| Concern 1 | §4.7.1 DCCD なのに 1 次風上スキームの修正方程式を展開 | Phase 2 |
| Concern 2 | §4.10 FCCD と §4.9 UCCD6 順序; UCCD6 は DCCD の特殊か? | Phase 1 |
| Concern 3 | §4.10.3 で CN を §5 より先に展開 | Phase 3 |
| Concern 4 | §4.11 face-jet と UCCD6 の関係 framing | Phase 4 |

2 並列 Explore agent で User concerns 検証 + 独立 reviewer pass を実施し，
計 **15 defect** (Major 7 + Minor 5 + Nit 3) を抽出．全件解消．

---

## 9 phase commit 一覧

| # | Commit | Phase | 内容 |
|---|---|---|---|
| 1 | `bb913a6` | Phase 1 | Concern 2 — input 順序 swap (04f ↔ 04e) + 04_ccd ロードマップ 2 family taxonomy 書換 + 04f framing 「節点中心 family」化 |
| 2 | `97e4874` | Phase 2 | Concern 1 — 04c から 1 次風上 subsubsection 削除; 動機を中心系の対称性で再構築; 旧内容を 04f「散逸動機の階層」に k=1→k=4 スケール論として移植 |
| 3 | `48fa5ff` | Phase 3 | Concern 3 — 04f §CN 安定性 proof 圧縮 (1 文 + §sec:time_int forward ref); remark[陽解法 CFL] 維持 |
| 4 | `2f6c388` | Phase 4 | Concern 4 — 04g face-jet タイトル「基底 CCD 出力の面 API（FCCD と等価）」 + 章番号正規化 (m-1) |
| 5 | `6e53fb7` | Phase 5 | Major M-1..M-3 — Level-2/AB2/IRK 詳細削除 + sec:dccd_decoupling → sec:collocate + FCCD 散逸欄統一 |
| 6 | `714ce79` | Phase 6 | Minor m-1..m-5 — phantom self-ref 解消 + cross-ref 修復 + §4 純化逸脱削除 |
| 7 | `b28e8f8` | Phase 7 | Nit n-1..n-3 — 表記揺れ統一 |
| 8 | `cc464a4` | Phase 8 | V-1 fixup — 残存 1 次風上 narrative 言及 (L3 + L81) を除去 |

---

## V-grep V-1..V-9 結果

| # | 検証項目 | 期待 | 実測 | 結果 |
|---|---|---|---|---|
| V-1 | `1 次風上` in 04c | 0 | 0 | PASS |
| V-2 | `FCCD/UCCD6 出力` in 04g | 0 | 0 | PASS |
| V-3 | CN proof 行数 in 04f | ≤ 5 | 3 | PASS |
| V-4 | `sec:dccd_decoupling/sec:future_gks/sec:dccd_bc` body refs in 04*.tex | 0 | 0 | PASS |
| V-5a | 04c CA-3 `sec:fccd_bc_options` | 0 | 0 | PASS |
| V-5b | 04b L245-250 `app:ccd_ghost` | 0 | 0 | PASS |
| V-6 | 散逸機構 in 04*.tex | 0 | 0 | PASS |
| V-7 | input 順序 | 04→04b→04c→04f→04e→04g | 確認 | PASS |
| V-8 | undef refs / multiply defined | 0 / 0 | 0 / 0 | PASS |
| V-9 | ページ数 | 256 ± 5 | 257 | PASS |

`xelatex` clean: 257 pp, 0 LaTeX warnings, 0 undefined references.

---

## §4 narrative の完成度 (CHK-217 後)

### Before (CHK-216 後)

```
§4.1 動機
§4.2-§4.3 CCD 基底 + ω_1, ω_2
§4.4 BC + ブロック Thomas
§4.5 DCCD (1 次風上 → 修正方程式 → spectral filter)
§4.6 FCCD (面中心)
§4.7 UCCD6 (節点 hyperviscosity; 「第 3 の経路」 framing)
§4.8 face-jet (FCCD/UCCD6 出力の 3 成分 API)
§4.9 章末まとめ
```

### After (CHK-217 後; 2 family taxonomy)

```
§4.1 動機
§4.2-§4.3 CCD 基底 + ω_1, ω_2
§4.4 BC + ブロック Thomas
§4.5 DCCD       ┐
§4.6 UCCD6      ├─ 節点中心 dissipation family
§4.7 FCCD       ─── 面中心 family
§4.8 face-jet   ─── FCCD と等価な面 API; 全節点中心 family の統一手段
§4.9 章末まとめ
```

### narrative axis の明示

- **DCCD**: 中心 CCD 散逸ゼロ → 偶数次 -D_2^CCD 正定値 → 散逸チャンネル
  (1 次風上参照を完全排除; 自閉的導出)
- **UCCD6**: 1 次風上 (k=1; 修正方程式 ε|a|h ∂_x²) → ハイパー粘性 (k=4;
  ε|a|h^7 (-D_2^CCD)^4) のスケール論で風上派生として位置付け
- **FCCD**: 面中心 family の代表; Fourier シンボルは純虚数で散逸ゼロ
- **face-jet ≡ FCCD**: 数式上等価; FCCD は本 API の面中心実装形態;
  全節点中心 CCD 派生も本 API 経由で面値を得る

---

## 解消 defect 一覧 (15 件)

### Major (7 件)

| # | Phase | 修正内容 |
|---|---|---|
| C-1 | 2 | 04c から 1 次風上修正方程式 subsubsection 全削除 + UCCD6 へ移植 |
| C-2 | 1 | input 順序 swap (04f → 04e); 2 family taxonomy 明示 |
| C-3 | 3 | 04f CN proof 圧縮 (§sec:time_int 重複回避) |
| C-4 | 4 | 04g face-jet を「FCCD 等価」 framing に修正 |
| M-1 | 5 | 04c から Level-2/AB2/IRK 用途章実装詳細削除 |
| M-2 | 5 | 04c sec:dccd_decoupling → sec:collocate (§4 単独で未定義 label 修正) |
| M-3 | 5 | 04g/04f 比較表 FCCD 散逸欄「風上構造」 → 「なし（散逸ゼロ）」 |

### Minor (5 件)

| # | Phase | 修正内容 |
|---|---|---|
| m-1 | 4 | 04g L3 コメント §4.6 → §4.7 (新順序対応) |
| m-2 | 6 | 04c L302 \ref{sec:dccd_bc} → \ref{sec:ccd_bc} |
| m-3 | 6 | 04c CA-3 反論 sec:fccd_bc_options → §sec:grid 章境界処理 |
| m-4 | 6 | 04f \label{sec:future_gks} 削除 (同一 subsection 自己参照解消) |
| m-5 | 6 | 04b L248 並列化注記末尾「実装詳細：付録 app:ccd_ghost 参照」削除 |

### Nit (3 件)

| # | Phase | 修正内容 |
|---|---|---|
| n-1 | 7 | 「散逸機構」 → 「散逸チャンネル」 統一 |
| n-2 | 7 | 04b L204 「行列の左右は非対称」 → 「左右境界は異なる片側スキームで閉じる」 |
| n-3 | 7 | 04 L8 章概要を「DCCD」 → 「CCD 派生スキーム族（DCCD・UCCD6・FCCD・面ジェット）」 |

---

## Lessons (KL-12)

### KL-12-1: 抜本改稿直後の追加レビュー pass の有効性

CHK-216 で「自己査読」を Phase 7 に組込み Critical 0/Major 0 を達成したが，
**書き手 bias** で structural 違和感は完全には除去できなかった．
ユーザの読み手視点による独立 review で 4 件の Major level structural 違和感が
新規抽出された．self-review の限界として明示的に記録．

### KL-12-2: 章順序 = narrative axis の宣言

`input` file 順序の決定は「章 axis の宣言」と等価．
**節点中心 dissipation family → 面中心 family** のような分類軸を input 順序で
表現すると，後の章本文 (taxonomy 表 / family 比較段落) と自動整合する．
逆に「第 3 の経路」のような ordinal framing は順序入替で破綻する．

### KL-12-3: forward ref の severity hierarchy

最悪なのは「同一 subsection 内の自己参照」 (m-4 sec:future_gks 例;
\label{sec:future_gks} と \ref{sec:future_gks} が同一 subsubsection 内).
forward ref として機能しない上に label が duplicate を引き起こす可能性がある．
label と参照は最低でも別 subsection 跨ぎが必要．

### KL-12-4: 派生スキーム間の数学的同一性の framing 重要性

face-jet 公式と FCCD 公式は数式上等価だが，CHK-216 までは「FCCD/UCCD6 出力の
3 成分 API」 という framing で「複数の独立 API が並立」と誤認される構造だった．
**等価性の明示** (「面ジェット ≡ FCCD 公式; FCCD は本 API を面中心スキームとして
直接実装した形態」) が narrative 簡潔化の核心．派生スキーム間の数学的同一性は
framing 上で明示しないと読者は構造を誤解する．

---

## CHK-216 → CHK-217 の差分

| 観点 | CHK-216 (抜本改稿) | CHK-217 (review pass) |
|---|---|---|
| 焦点 | §4 純化原則 (HFE/PPE/BF/GFM consume-side 機構の §4 排除) | §4 内部 narrative 精緻化 (taxonomy axis / framing / cross-ref) |
| 改稿規模 | 8 paper commit + 1 review memo | 8 paper commit + 1 ledger/memo commit |
| LOC 影響 | 全章 narrative 全面改稿 | 局所修正主体 (Net ~-50 paper LOC) |
| ページ | 256 pp | 257 pp |
| 検証指標 | V-1..V-8 (純化 grep + phantom 残置確認) | V-1..V-9 (新 narrative 整合 + 章順序確認) |
| 自己査読 | Phase 7 に組込み | 独立 reviewer pass + ユーザ違和感統合 |

**§4 純化原則 (CHK-216 成果) は維持**: §4 を読むだけで CCD/DCCD/UCCD6/FCCD/
面ジェット の数値特性が完結理解可能; HFE/PPE/BF/GFM consume-side 機構への
依存ゼロ．

---

## 次タスク候補

- **CHK-218**: §4 main マージ + §5-§13 への back-ref 整合確認 (§4 順序入替に伴う
  §5 以降の forward ref 適合性確認)
- **CHK-219**: §11+ 検証実装 (CHK-216 持越 mn-3..mn-5; UCCD6/FCCD 数値検証)
- 数値検証実行 (`make run-all CH=ch11`; level 1/2/3 ベンチマーク)
