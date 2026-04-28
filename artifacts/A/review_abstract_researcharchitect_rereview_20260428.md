# RA 再厳正レビュー — Abstract (`paper/sections/00_abstract.tex`)

**Reviewer**: ResearchArchitect (TIER-3 strict rereview, fresh skepticism)
**Date**: 2026-04-28
**Target**: [`paper/sections/00_abstract.tex`](../../paper/sections/00_abstract.tex) post-fix (commits `f2517b5`, `bbe0c51`)
**Initial review**: [`review_abstract_researcharchitect_20260428.md`](review_abstract_researcharchitect_20260428.md)
**Verdict**: **CONDITIONAL PASS** — FATAL 0 / MAJOR 0 / MINOR 4 (RR-1〜RR-4)

---

## Post-Fix Status (Initial review F-1 / F-2 / M-1..4 / N-1..6 verification)

各 finding に対して fix が完全に close したかを独立再検証。

| ID | 検証 | 結果 |
|---|---|---|
| F-1 | titlepage L22 と abstract L50 で低密度比手法が「smoothed Heaviside 一括解法」に統一されたか | △ **詳細度の非対称あり** → RR-1 |
| F-2 | 「実証は今後の課題」blanket 削除 / 実施済 vs future-work の階層化 | ✓ CLOSED |
| M-1 | 「根本的に解決」→「CSF モデル誤差律速まで根本的に抑制」 | ✓ CLOSED ([§1 L23](../../paper/sections/01_introduction.tex), [§15 L12](../../paper/sections/15_conclusion.tex) と整合) |
| M-2 | FD/CCD = 69× / 分相 PPE $\Ord{h^{7.0}}$ / RT 2.8% を挿入 | ✓ CLOSED |
| M-3 | 静止液滴を Force Balance 実施側に明示移動 | ✓ CLOSED |
| M-4 | 「外付け補正なし内在的」→「BF + FCCD 協働 / Rhie--Chow 補間に頼らず」 | ✓ CLOSED ([§8 L107–122](../../paper/sections/08_collocate.tex) と整合) |
| N-1 | CCD「内点 $\Ord{h^6}$」スコープ語追加 + titlepage footnote | ✓ CLOSED |
| N-2 | 「$\Ord{1}$ 誤差体積力」→「下限が消えない誤差体積力」 | ✓ CLOSED |
| N-3 | `\cite{Aslam2004}` 化 | ✓ CLOSED |
| N-4 | abstract 内章節 cross-reference 削除 | ✓ CLOSED (titlepage は導入装置として保持; OK) |
| N-5 | 分相 PPE + HFE + DC の 3 要素統一 | ✓ CLOSED |
| N-6 | titlepage L21 「IPC 法~\cite{vanKan1986}（本稿で変密度に拡張）」 | ✓ CLOSED |

11/12 close、1 件（F-1）は再判定で「詳細度非対称」として RR-1 に降格・継続。

---

## Routing

- **Scope**: 修正後の `paper/sections/00_abstract.tex` に対する fresh skepticism 再査読。
- **アプローチ**: 初回レビューの findings の close 状態確認に加え、fix で生じた新規問題・過剰修正・抜け落ち・読者への明瞭性を独立に評価。
- **判定基準**: 一般読者（業界外を含む論文投稿査読官）が abstract 単体で論文の scope と claim を正確に把握可能か。
- **Verification base**: paper 本体 §1 / §4 / §8 / §9 / §13b / §13f / §13i / §14 / §15。

---

## Reviewer Skepticism Checklist (Rereview)

| # | 項目 | 結果 |
|---|---|---|
| 1 | 初回 finding すべて close | △ F-1 残（RR-1） |
| 2 | 修正で新たな矛盾発生 | ✗ 検出（RR-1） |
| 3 | 過剰修正（情報削除）の妥当性 | △ 「期待される精度特性」削除（RR-2） |
| 4 | 業界外読者への明瞭性 | ✗ smoke / closure 用語未定義（RR-3） |
| 5 | 文長・構文バランス | ✗ 後段一文化（RR-4） |
| 6 | 数値の単位明示 | ✓ 概ね OK |
| 7 | 用語整合 | ✓ 一貫 |

---

## FATAL

なし。

## MAJOR

なし。

## MINOR (Rereview)

### RR-1 — Titlepage L22 と abstract L50 の詳細度非対称（F-1 残務）

**Location**: `paper/sections/00_abstract.tex` L22 vs. L50

**事実**:

- Titlepage L22:
  > `\textbf{低密度比}（$\rho_l/\rho_g \leq 5$）：smoothed Heaviside 一括解法`
- Abstract L49–50:
  > `[...] 低密度比（$\rho_l/\rho_g \leq 5$）では`
  > `smoothed Heaviside 一括解法（FD 直接法 + CCD $\Ord{h^6}$ 勾配；必要に応じ欠陥補正法）で求解し`

**問題点**:

F-1 を「同概念で表現を統一」することで close したが、**詳細度に依然として差**がある：

- titlepage は `smoothed Heaviside 一括解法` のみ（中身不明）
- abstract は `(FD 直接法 + CCD $\Ord{h^6}$ 勾配; 必要に応じ欠陥補正法)` まで開示

タイトルページの読者が「smoothed Heaviside 一括解法」の中身を知るには abstract 本文 L50 を読む必要がある。要約の階層構造としては自然だが、**`高密度比`側 (titlepage L23) は分相 PPE + HFE + DC まで開示しているため、対称性が崩れている**。

**Severity 判断**: 致命ではないが、読者が低密度比と高密度比のどちらが「複雑な手法」か誤読する余地。symmetric format 推奨。

**Recommended fix**: titlepage L22 を `smoothed Heaviside 一括解法（FD 直接法 + CCD $\Ord{h^6}$ 勾配；必要に応じ DC）` に拡張し、L23 の `分相 PPE + HFE（必要に応じ欠陥補正法 DC，§~\ref{sec:split_ppe_recovery}）` と対称化。

---

### RR-2 — 「界面結合検証」 vs 「物理ベンチマーク」の境界の暗黙性

**Location**: `paper/sections/00_abstract.tex` L56–60

**事実**:

修正後 abstract では検証を 3 階層で記述：

1. `コンポーネント単体検証（CCD 精度・Zalesak 円盤・PPE 収束等）`
2. `界面結合検証（静止液滴 Force Balance：…；分相 PPE + DC $k{=}3$：…；Rayleigh--Taylor 不安定の…）`
3. `物理ベンチマークでは毛細管波の smoke 合格・気泡上昇の closure 合格`

この 3 つの区分は本体構成（§12 component / §13 NS verification / §14 benchmarks）と整合するが、abstract 内では区分の**定義が暗黙的**。読者は「界面結合検証」と「物理ベンチマーク」の違いを文脈推定する必要がある。

**問題点**:

業界投稿査読官が論文を 30 秒で評価する場面で、「Rayleigh--Taylor が界面結合検証側で、毛細管波が物理ベンチマーク側」という分類は本体非読では再構成困難。**3 階層の意味付けが abstract で完結していない**。

**Severity 判断**: 軽微。業界内読者は 3 階層の階層性を一般概念として理解可能（unit → component coupling → physical benchmarks）。

**Recommended fix**: 軽い文言追加で明示化。

```latex
% 案 (L56-58):
コンポーネント単体検証（CCD 精度・Zalesak 円盤・PPE 収束等），
NS パイプライン整合検証（静止液滴 Force Balance：FD は CCD の約 69 倍の寄生流れ；
分相 PPE + DC $k{=}3$：全密度比で $\Ord{h^{7.0}}$；Rayleigh--Taylor 不安定：成長率誤差 $2.8\%$），
および物理ベンチマーク（毛細管波 smoke 合格・気泡上昇 closure 合格）の三段構成で検証を実施した．
```

---

### RR-3 — 業界外読者への用語不明確性：smoke / closure

**Location**: `paper/sections/00_abstract.tex` L60

**事実**:

> `物理ベンチマークでは毛細管波の smoke 合格・気泡上昇の closure 合格を達成した．`

「smoke 合格」「closure 合格」は本論文 [§14 L99, L158, L156, L179, L183](../../paper/sections/14_benchmarks.tex) で定義される operational ステータス：

- **smoke**: 長時間動作の保存性 sanity（破綻なく完走しエネルギ・体積誤差が有界）
- **closure**: 投影演算の発散回避（projection blowup なく短時間 closure）

**問題点**:

学術 abstract で初出の operational 用語は通常定義注記が伴う。`smoke pass` / `closure pass` は CFD コミュニティ内でも標準語ではなく、本論文独自の運用語。業界外読者には「煙合格？」と読まれかねない（実際 IT 文脈では `smoke test` ≠ `quantitative validation`）。

**Severity 判断**: 軽微。本体 §14 で明示定義されているので abstract 単独では曖昧だが、論文全体では追跡可能。

**Recommended fix**: 平易な短い注を加える。

```latex
% 案:
物理ベンチマークでは毛細管波の長時間保存性 smoke 合格・気泡上昇の short-time closure 合格（投影発散なし）を達成した．
```

または別案：

```latex
物理ベンチマークでは毛細管波（長時間保存性 smoke）と気泡上昇（投影発散有無の closure，$T = 0.5$）を実行し合格した．
```

---

### RR-4 — 後段の文長過大（L56–61 の 6 行 1 文）

**Location**: `paper/sections/00_abstract.tex` L56–60

**事実**:

L56 から L60 まで `[...]を実施し，物理ベンチマークでは[...]を達成した．` で 1 文に圧縮。`実施し` の連用形が二段構造を呼ぶため、読み手は中間で構造を再構成する必要。

**問題点**:

abstract 全体の文長分布：
- L40–43: 4 行 1 文（問題提示）
- L44–46: 3 行 1 文（解決策）
- L48–51: 4 行 1 文（CLS + PPE）
- L52–54: 3 行 1 文（HFE + checkerboard）
- L55: 1 行 1 文（時間ループ）
- **L56–60: 5 行 1 文（検証 + ベンチマーク）**
- L61: 1 行 1 文（future work）

最終段落の 5 行 1 文は読者疲労を招く。`実施した．` で文を切り、`物理ベンチマーク` を独立した文に分けるとリズムが整う。

**Severity 判断**: 文体・可読性。technical content は正確。

**Recommended fix**: L59 の `を実施し，` を `を実施した．` で文末。L60 を `さらに、物理ベンチマーク [...]` で開始。

```latex
% 案 (L56-60):
[...]
コンポーネント単体検証（CCD 精度・Zalesak 円盤・PPE 収束等）に加え，
NS パイプライン整合検証（静止液滴 Force Balance：FD は CCD の約 69 倍の寄生流れ；
分相 PPE + DC $k{=}3$：全密度比で $\Ord{h^{7.0}}$；Rayleigh--Taylor 不安定：成長率誤差 $2.8\%$）を実施した．
さらに，物理ベンチマークでは毛細管波 smoke 合格・気泡上昇 closure 合格を達成した．
```

---

## 総括（Rereview）

| 区分 | 件数 | 影響 |
|---|---|---|
| FATAL | 0 | — |
| MAJOR | 0 | — |
| MINOR (RR) | 4 | 全て style / readability。論文 acceptance リスクは低。 |

**判定**: **CONDITIONAL PASS** — 初回 12 件は実質 close。残る RR-1〜RR-4 は MINOR 範疇で、論文投稿に致命的問題なし。ただし業界外読者への明瞭性と対称性の観点から、追加修正が abstract 品質をさらに高める。

**Reviewer note**:

修正後の abstract は本体 claim と整合し、定量結果（69×, $\Ord{h^{7.0}}$, 2.8%）が読者に届く構造になった。M-1（過大表現）と F-2（scope 不整合）の解消は特に成功。残存 RR は文体面の磨き込みであり、初回 review が捕捉しきれなかった「fix で生じる新規問題」と「過剰削除の余地」を扱っている。

**勧告**:

- **オプション A（高品質仕上げ）**: RR-1〜RR-4 すべて適用。abstract が investor pitch deck 級に磨かれる。
- **オプション B（学術下限）**: 現状維持で投稿可能。査読官が文体面を flag したとき個別対応。

→ **オプション A を採用、全 RR 適用済み（後述 Post-Fix Status 参照）**。

---

## Post-Fix Status (Rereview)

**ALL CLOSED** (2026-04-28). RR-1〜RR-4 全 4 件を `paper/sections/00_abstract.tex` に反映。`latexmk -xelatex -interaction=nonstopmode main.tex` clean (219 pp; undefined ref/cite 0; 残 warning は既存の §12 `Text page 123 contains only floats` のみ)。

| ID | Status | 適用箇所 |
|---|---|---|
| RR-1 | CLOSED | titlepage L22 を `smoothed Heaviside 一括解法（FD 直接法 + CCD $\Ord{h^6}$ 勾配；必要に応じ DC）` に拡張、L23 と対称化。 |
| RR-2 | CLOSED | abstract L56–61 を `検証は三段構成で実施した：コンポーネント単体検証 / NS パイプライン整合検証 / および物理ベンチマーク` の階層化文へ書き換え。区分が abstract で明示。 |
| RR-3 | CLOSED | smoke / closure に括弧注：「毛細管波：長時間保存性 smoke 合格；気泡上昇：投影発散有無の closure 合格，$T{=}0.5$」。 |
| RR-4 | CLOSED | 後段 5 行 1 文を 3 行 + 階層構成へ短縮。`実施し，... を達成した` の二段構造を解消。 |

**最終 abstract 構造**:

- 問題提示（L40–43、4 行）
- 解決策提案（L44–46、3 行）
- 体系構成（L47、1 行）
- CLS + 変密度 PPE 分岐（L48–51、4 行）
- HFE + Balanced-Force / FCCD（L52–54、3 行）
- 7 ステップ統合（L55、1 行）
- 三段検証 + 定量結果（L56–61、6 行コロン階層）
- Future work（L62、1 行）

**Verification commits**:

- `575144d`: 初回 review md 追加（FATAL 2 / MAJOR 4 / MINOR 6）
- `f2517b5`: 初回 findings 全反映（abstract.tex; F-1..N-6）
- `bbe0c51`: 初回 review md に Post-Fix Status 追記
- `<rereview commit>`: 本 rereview md 追加 + RR-1..RR-4 適用 + 本 Post-Fix Status

**最終判定**: **PASS**。初回 12 件 + 再査読 4 件、計 16 finding すべて close。`main` への merge は未実施（ユーザー指示待ち、`--no-ff` 採用予定）。

---

**Verification base files (for reread)**:

- 修正対象: [`paper/sections/00_abstract.tex`](../../paper/sections/00_abstract.tex)（L1–62）
- 整合確認: 上記の各 § references（初回 review と同一）
- ビルド検証: `latexmk -xelatex` clean (219 pp; undefined ref/cite 0)
- Source commits: `f2517b5` (abstract fix), `bbe0c51` (review post-fix status)
