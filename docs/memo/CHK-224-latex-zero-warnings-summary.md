# CHK-224 — LaTeX 警告ゼロ化 (hyperref + tabular p 列化 + 非対応書体回避)

**Date**: 2026-04-26
**Branch**: `worktree-ra-paper-zero-warnings`
**Trigger**: ユーザより 3 件指示 — (1) 新規作業ツリーで作業; (2) latex のエラー警告をゼロにするように校正; (3) フォント問題は対応していない書体を使わない方向で対応 (Mac compile env)
**Result**: main.log 全項目 0 件 (Warning / Overfull / Underfull / Token-not-allowed / font shapes not available / lmtt/bx ssub / Hiragino m/it ssub / undef refs / multiply defined); 256 pp 維持; xelatex 2-pass clean

---

## 背景: CHK-223 完了時点の残存 13 件 Warning

| 種別 | 件数 | 根本原因 |
|---|---|---|
| hyperref Warning (`Token not allowed in a PDF string (Unicode)`) | 9 | `\subsection` 中の裸数式 (`$\psi$` / `$\theta=1/2$` / `$\Ord{H^4}$`) を PDF ブックマーク文字列化する際に math-shift `$` および superscript `^` token がブックマーク文字列で禁止 |
| Overfull \\hbox (60..143 pt 超過) | 4 | tabular の `l`/`c` カラム指定で長文セル (Hiragino 日本語混じり) の自動折返しが効かず行幅超過 |

加えて副次的 Font Info (Warning ではないがユーザ指示「対応していない書体を使わない」と整合させるため対応):

| 種別 | 件数 | 根本原因 |
|---|---|---|
| `TU/lmtt/bx/n` 不在 (Latin Modern Typewriter Bold Extended) | 2 | `\textbf{\texttt{...}}` の入れ子: lmtt は `b/n` (太字) は持つが `bx/n` (太字拡張) を欠く |
| `TU/HiraginoMinchoProNW3(0)/m/it` 不在 (Hiragino Mincho ProN Italic) | 22 箇所 | Hiragino Mincho ProN は italic shape を一切持たない. preamble `\DeclareFontShape ssub` で silent fallback 既処理だが `\textit{Japanese}` / `\emph{Japanese}` / `\begin{proof}[Japanese]` 全箇所を Honest に置換 |

---

## Phase 1 — hyperref texorpdfstring (9 → 0)

**戦略**: `\subsection` 見出し中の数式を `\texorpdfstring{$math$}{plain}` で包み, PDF ブックマーク用 fallback 文字列を与える.

### 修正

- [paper/sections/07_advection.tex#L12](paper/sections/07_advection.tex#L12)
  ```diff
  -\subsection{移流項：CLS $\psi$ 用 FCCD と運動量用 UCCD6}
  +\subsection{移流項：CLS \texorpdfstring{$\psi$}{ψ} 用 FCCD と運動量用 UCCD6}
  ```

- [paper/sections/06c_fccd_nonuniform.tex#L7](paper/sections/06c_fccd_nonuniform.tex#L7)
  既存 `$\mathcal{O}(H^3)$` のみ texorpdfstring 化済 → 残る 2 数式を同様にラップ:
  ```diff
  -\subsection{...：\texorpdfstring{$\mathcal{O}(H^3)$}{O(H3)} 行列定式（$\theta=1/2$ 界面適合で $\Ord{H^4}$）}
  +\subsection{...：\texorpdfstring{$\mathcal{O}(H^3)$}{O(H3)} 行列定式（\texorpdfstring{$\theta=1/2$}{θ=1/2} 界面適合で \texorpdfstring{$\Ord{H^4}$}{O(H4)}）}
  ```

### トラップ (KL-19-(a))

PDF fallback 文字列に `^` を含めると hyperref が再度 superscript token として解釈し警告再発生.
- ❌ NG: `\texorpdfstring{$\Ord{H^4}$}{O(H^4)}` → `Token not allowed` 再発
- ✅ OK: `\texorpdfstring{$\Ord{H^4}$}{O(H4)}` (キャレット無し)

---

## Phase 2 — tabular p 列化 (Overfull 4 → 0)

**戦略**: 長文セルを含むカラムを `p{w\linewidth}` に変更し `\raggedright` で日本語自動折返しを許可. `\\` 手動改行は読みにくく折返し位置を硬直化させるため避ける.

### 修正

| File | カラム指定: 旧 → 新 |
|---|---|
| [09f_pressure_summary.tex#L25](paper/sections/09f_pressure_summary.tex#L25) | `lp{0.28\linewidth}cc` → `p{0.20\linewidth}p{0.28\linewidth}p{0.30\linewidth}p{0.10\linewidth}` (4 列全 p 化) |
| [10_full_algorithm.tex#L95](paper/sections/10_full_algorithm.tex#L95) | `clll` → `clp{0.50\linewidth}l` (手法列のみ p 化) |
| [10_3_level_selection.tex#L75](paper/sections/10_3_level_selection.tex#L75) | `@{}lll@{}` → `@{}p{0.30\linewidth}cp{0.50\linewidth}@{}` + `\small` |
| [10_5_pure_fccd_dns.tex#L188](paper/sections/10_5_pure_fccd_dns.tex#L188) | `@{}lll@{}` → `@{}p{0.18\linewidth}p{0.45\linewidth}p{0.30\linewidth}@{}` + `\small` |

### トラップ (KL-19-(b))

10_5 表は初版で第 1 列 `l` のまま 22.3 pt 残存. 「G-1 静水圧 spurious current」のような短いセルでも全角混在で `l` カラムに収まらない場合があり, **長文を含む可能性のあるカラムは全て p 列化** が安全. 反復計測 (`make` → main.log overfull 残量確認) で 1 度幅微調整した.

---

## Phase 3 — 非対応書体回避

### (a) lmtt/bx ssub Info → 0 (KL-19-(c))

`\textbf{\texttt{...}}` 入れ子は順序入れ替えで解決せず, **太字と等幅を分離** するしかない (Latin Modern Typewriter は `b/n` のみで `bx/n` を欠く).

- [appendix_ppe_pseudotime.tex#L182](paper/sections/appendix_ppe_pseudotime.tex#L182) + L224 計 2 箇所:
  ```diff
  -\textbf{...\texttt{PPESolverSweep}...}
  +\textbf{...}\texttt{PPESolverSweep}\textbf{...}
  ```

### (b) Hiragino italic 22 箇所一掃 (KL-19-(d))

Hiragino Mincho ProN は italic shape を一切持たない. preamble `\DeclareFontShape ssub` で silent fallback 可能だが, ユーザ指示「対応していない書体を使わない」に整合させるため明示的に `\textbf{}` または `[\upshape ...]` 起動へ置換.

| File | 件数 | パターン |
|---|---|---|
| [03d_ridge_eikonal.tex](paper/sections/03d_ridge_eikonal.tex) | 6 | 2× `\begin{proof}[Japanese]` → `[\upshape Japanese]` + 4× `\emph{Japanese}` → `\textbf{Japanese}` |
| [05_time_integration.tex#L679](paper/sections/05_time_integration.tex#L679) | 2 | `\textit{陰的化}` + `\emph{物理測定}` → `\textbf{...}` |
| [07b_reinitialization.tex](paper/sections/07b_reinitialization.tex) | 2 | `\textit{証明：}` → `\textbf{証明：}` (replace_all) |
| [07c_fccd_advection.tex#L185](paper/sections/07c_fccd_advection.tex#L185) | 1 | `\begin{proof}[証明（要旨）]` → `[\upshape 証明（要旨）]` |
| [08c_pressure_filter.tex](paper/sections/08c_pressure_filter.tex) | 2 | `\emph{許可}` + `\emph{禁止}` → `\textbf{...}` |
| [11_component_verification.tex#L49](paper/sections/11_component_verification.tex#L49) | 1 | `\textit{略語：}` → `\textbf{略語：}` |
| [11g_summary.tex#L108](paper/sections/11g_summary.tex#L108) | 1 | `\textit{追加検証（ギャップ充填）}` → `\textbf{...}` |
| [12g_nonuniform_grid.tex#L84-86](paper/sections/12g_nonuniform_grid.tex#L84-L86) | 1 | multi-line `\emph{注意：...}` → `\textbf{...}` |
| [12h_error_budget.tex#L35](paper/sections/12h_error_budget.tex#L35) | 1 | `\textit{追加検証}` → `\textbf{追加検証}` |
| [13_benchmarks.tex#L191-201](paper/sections/13_benchmarks.tex#L191-L201) | 5 | `\textit{補完}` / `\textit{継続}` → `\textbf{...}` (replace_all) |
| **合計** | **22** | — |

### amsthm `proof` env トラップ

`\begin{proof}[arg]` は arg を `\itshape` 起動で組版する. `\upshape` を arg 先頭に置くことで起動を打ち消し. 例:
```latex
\begin{proof}[\upshape 証明スケッチ (Ridge-based 距離関数の良定義性)]
```

---

## 検収

```bash
cd paper && make clean && make 2>&1 | tee build.log

# 検収項目 (全て期待値 0)
grep -cE "(LaTeX|Package).+Warning"            main.log   # 0
grep -cE "(Overfull|Underfull) \\\\hbox"        main.log   # 0
grep -cE "Token not allowed"                   main.log   # 0
grep -cE "Some font shapes were not available" main.log   # 0
grep -cE "lmtt/bx"                             main.log   # 0
grep -cE "HiraginoMinchoProNW3\\(0\\)/m/it"    main.log   # 0
grep -cE "undefined references|multiply defined" main.log # 0

pdfinfo main.pdf | grep Pages                  # Pages: 256 (CHK-223 baseline 一致)
```

全項目 0 を達成.

---

## Files changed

17 files (+33/-31 LOC):

```
paper/sections/03d_ridge_eikonal.tex
paper/sections/05_time_integration.tex
paper/sections/06c_fccd_nonuniform.tex
paper/sections/07_advection.tex
paper/sections/07b_reinitialization.tex
paper/sections/07c_fccd_advection.tex
paper/sections/08c_pressure_filter.tex
paper/sections/09f_pressure_summary.tex
paper/sections/10_3_level_selection.tex
paper/sections/10_5_pure_fccd_dns.tex
paper/sections/10_full_algorithm.tex
paper/sections/11_component_verification.tex
paper/sections/11g_summary.tex
paper/sections/12g_nonuniform_grid.tex
paper/sections/12h_error_budget.tex
paper/sections/13_benchmarks.tex
paper/sections/appendix_ppe_pseudotime.tex
```

---

## Commits

| Hash | Subject |
|---|---|
| `7243e3f` | `paper(warnings): CHK-224 — LaTeX 警告ゼロ化 (hyperref texorpdfstring + tabular p列化 + 非対応書体回避)` |
| `7dfac20` | `ledger: CHK-224 DONE — LaTeX 警告ゼロ化 (hyperref + tabular p 列化 + 非対応書体回避; 13→0 warnings; 256 pp 維持)` |
| (this) | `memo: CHK-224 — LaTeX 警告ゼロ化 summary + KL-19-(a..d)` |

---

## KL-19 (LaTeX zero-warnings) — 4 件

### KL-19-(a): hyperref `\texorpdfstring` PDF fallback はキャレット禁止

**症状**: `\texorpdfstring{$\Ord{H^4}$}{O(H^4)}` でも `Token not allowed in a PDF string (Unicode)` Warning が再発.

**根因**: PDF fallback 文字列 (第 2 引数) も hyperref が再度 tokenize し, `^` を superscript token として解釈する.

**対処**: PDF fallback 内で上付き表現を諦め, プレーンテキスト形式 `O(H3)` / `O(H4)` を使う. 視覚出力の本文側は `\Ord{H^4}` のまま正しく上付き表示される (`\texorpdfstring` の第 1 引数は本文用, 第 2 引数は PDF メタデータ用).

**一般化**: PDF メタデータ文字列内で禁止される TeX 記号 = `$ ^ _ \ { } #` 等. これらは Unicode 代用 (上付き → `³` などコードポイント直書き) または除去 (キャレット無し) で対応.

### KL-19-(b): tabular overfull は `p{w\linewidth}` 移行が確実

**症状**: `lll` / `clll` 等の固定幅指定で Overfull \hbox 60..143 pt 超過.

**根因**: `l` / `c` カラムは内容幅 = 自然幅で確定 (折返し不可). 全角混在文 (Hiragino + Times) は全角文字幅が大きく自然幅が容易に行幅を超える.

**対処**: 長文を含むカラムを `p{w\linewidth}` に変更. 幅は 0.05 単位の試行錯誤で 1 度調整 (合計幅 ≤ 1.0\linewidth, 列間 padding 考慮).

**避ける手法**: `\\` 手動改行は (i) 読みにくい (ii) 折返し位置が硬直化し将来の文言変更で破綻する (iii) 行高が不揃いになる. 自動折返しに任せるのが Honest.

### KL-19-(c): `\textbf{\texttt{...}}` 入れ子は分解しか手段がない

**症状**: `Font Info: Some font shapes were not available, defaults substituted (lmtt/bx → lmtt/m)` Info 出力.

**根因**: Latin Modern Typewriter は `b/n` (太字) を持つが `bx/n` (太字拡張) を欠く. NFSS は `\textbf{\texttt{}}` 順 (`bx/n`) と `\texttt{\textbf{}}` 順 (`bx/n`) のどちらも `bx/n` を要求する (順序入れ替えで解決しない).

**対処**: 太字と等幅を分離する `\textbf{...}\texttt{...}\textbf{...}` 形へ書き換え. 視覚出力上は太字テキスト+通常等幅+太字テキストになり, 元の「太字等幅」演出は失われるが, 元々 ssub で通常等幅 (`m/n`) に置換されていたため見た目は不変.

**代替**: lmodern + cm-super 系列の他フォントを使う (ただし全パッケージ整合の検証が必要; 本 CHK では非採用).

### KL-19-(d): Hiragino italic は `\upshape` または `\textbf` 置換が Honest

**症状**: `Font Info: Some font shapes were not available, defaults substituted (HiraginoMinchoProNW3(0)/m/it → m/n)` Info.

**根因**: Hiragino Mincho ProN は italic shape を一切持たない. preamble で `\DeclareFontShape{TU}{HiraginoMinchoProNW3(0)}{m}{it}{<->ssub*HiraginoMinchoProNW3(0)/m/n}{}` 等の silent ssub fallback 宣言が可能だが, ユーザ指示「対応していない書体を使わない」と整合しない.

**対処**: `\textit{Japanese}` / `\emph{Japanese}` を `\textbf{Japanese}` に置換 (強調を太字で表現); `\begin{proof}[Japanese]` を `\begin{proof}[\upshape Japanese]` に変更 (amsthm が proof arg に `\itshape` を起動するのを `\upshape` で打ち消す).

**注意**: `\emph{}` は upright 文脈では italic, italic 文脈では upright を出すトグルだが, 日本語フォントが italic を持たない場合 italic 文脈でも体感的差異が生まれない. 本 CHK では一律 `\textbf{}` へ置換し意味的強調を保存. 英語混じり ALL `\emph{English}` は本 CHK スコープ外 (実例なし; あれば italic OK).

---

## main マージ判断

ユーザ判断 (CHK-221/222/223 と同方針). worktree 上で完結.

---

## Out of scope (引き継ぎなし)

- `proof[Japanese]` 内の Hiragino italic は preamble の `\DeclareFontShape ssub` でも silent fallback 可能だが, 本 CHK では指示に従い明示的置換へ切替済 (preamble 変更なし)
- microtype の Helvetica Neue 文字欠損 Info (Info 大量; Warning ではないので不変)
- src/ コード変更なし
- ch11/ch13 検証実験の実行なし
