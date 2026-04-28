# RA 厳正レビュー — Abstract (`paper/sections/00_abstract.tex`)

**Reviewer**: ResearchArchitect (TIER-3 strict review mode)
**Date**: 2026-04-28
**Target**: [`paper/sections/00_abstract.tex`](../../paper/sections/00_abstract.tex) L1–60（titlepage L1–36 + abstract 環境 L39–60）
**Verification base**: paper本体 §1 / §4 / §8 / §9 / §12 / §13 / §14 / §15
**Verdict**: **REVISE REQUIRED** — FATAL 2 / MAJOR 4 / MINOR 6

---

## Post-Fix Status

N/A（初回レビュー）

---

## Routing

- **Scope**: Abstract（要旨）の対外主張・本体整合・引用適切性を厳正査読。
- **対象範囲**: titlepage `tcolorbox` 内の手法サマリ表（L14–31）と `\begin{abstract}...\end{abstract}` 環境（L39–60）の双方。両者は同一ファイル内で対外要約として機能するため、相互整合は必須。
- **Out of scope**: 本フェーズでは abstract 本体の修正は行わず findings のみ。fix は別 CHK でユーザー承認後。
- **Methodology**: 各主張について本体該当箇所の verbatim 引用と差分照合（file:line 単位）。

---

## Reviewer Skepticism Checklist

| # | 項目 | 結果 |
|---|---|---|
| 1 | 同一ファイル内自己矛盾 | ✗ 検出（F-1） |
| 2 | 本文との矛盾 | ✗ 検出（F-2） |
| 3 | 過大主張 / hedging 不足 | ✗ 検出（M-1） |
| 4 | 主要定量結果の欠落 | ✗ 検出（M-2） |
| 5 | 引用形式・出典の正確性 | △ 部分修正（N-3, N-6） |
| 6 | 用語の一貫性 | △ 軽微なゆらぎ（N-5） |
| 7 | アブストの self-contained 性 | △ 章節参照を含む（N-4） |

---

## FATAL

### F-1 — 同一ファイル内自己矛盾：低密度比 PPE 手法の記述不整合

**Location**: `paper/sections/00_abstract.tex` titlepage L22 vs. abstract L49–50

**事実**:

- **Titlepage 表（L22）**:
  > `低密度比 ($\rho_l/\rho_g \leq 5$): smoothed Heaviside 一括解法`
- **Abstract 本文（L49–50）**:
  > `変密度圧力 Poisson 方程式は低密度比（$\rho_l/\rho_g \leq 5$）では`
  > `欠陥補正法（FD 直接法 + CCD $\Ord{h^6}$ 勾配）で求解し`

**問題点**:

両者は同一の対外要約として読まれるが、「smoothed Heaviside 一括解法」と「欠陥補正法（FD 直接法 + CCD 勾配）」は**本体において別概念**である：

- 本体 [§9c L25](../../paper/sections/09c_hfe.tex)：「低密度比（$\rho_l/\rho_g \leq 5$）の **smoothed Heaviside 一括解法**では…HFE は不要」
- 本体 [§13i L66](../../paper/sections/13i_error_budget.tex)：「**二相流（$\rho_l/\rho_g \leq 5$，smoothed Heaviside）**」と低密度比＝smoothed Heaviside 一括を明示
- 本体 [§9d](../../paper/sections/09d_defect_correction.tex)：欠陥補正法（DC）は**別節として独立**し、低密度比・高密度比双方で用い得る精度向上手段
- 本体 [§15 L94–98](../../paper/sections/15_conclusion.tex)：「FD 直接法による PPE 求解と CCD 勾配の併用」は smoothed Heaviside パスでの実装詳細であり、defect correction とは別

**したがって**：低密度比パスの正しい記述は「smoothed Heaviside 一括 PPE（FD 直接法 + CCD 勾配；必要に応じ DC）」であって、Abstract L50 の「欠陥補正法（FD 直接法 + CCD $\Ord{h^6}$ 勾配）」は

1. 「一括解法」という分岐名の欠落
2. defect correction を低密度比パスのアイデンティティ的記述として誤って提示
3. その結果として titlepage 表との表記不一致

を生じている。**読者がアブストとタイトルページを順に読んだとき、低密度比で何を解いているのかが分からない**。

**Severity 根拠**: アブスト本文と同一ファイル内タイトルページとの自己矛盾は publication blocker。査読官が冒頭 1 ページ目で混乱すれば論文全体への信頼が損なわれる。

**Recommended fix（参考、適用は別 CHK）**:

```latex
% L49-51 案
変密度圧力 Poisson 方程式は低密度比（$\rho_l/\rho_g \leq 5$）では
smoothed Heaviside 一括解法（FD 直接法 + CCD $\Ord{h^6}$ 勾配；必要に応じ欠陥補正法）で求解し，
高密度比（$\rho_l/\rho_g > 5$）では分相 PPE 解法（HFE で各相の Poisson を独立化）により求解する．
```

---

### F-2 — 物理ベンチマーク実証ステータスの本体との矛盾

**Location**: `paper/sections/00_abstract.tex` L57–59

**事実**:

Abstract L57–59:
> `物理ベンチマーク（静止液滴・毛細管波・気泡上昇・Rayleigh--Taylor 不安定）の`
> `設計と期待される精度特性（理論収束次数・許容閾値）を定義する．`
> `物理ベンチマークの数値実験による実証は今後の課題として位置づける．`

**しかし本体には実行結果が存在する**：

| ベンチマーク | 本体該当 | ステータス |
|---|---|---|
| 毛細管波 | [§14 L99](../../paper/sections/14_benchmarks.tex)：「smoke 合格 / 動力学未確定」（体積誤差 $2.68\times10^{-5}$） | **実行済み（部分）** |
| 気泡上昇 | [§14 L158, L183](../../paper/sections/14_benchmarks.tex)：「closure PASS」（140 ステップ完走、$T=0.50$） | **実行済み（closure）** |
| RT 不安定 | [§13f L198–227](../../paper/sections/13f_coupling.tex)：成長率測定 $\omega_{\mathrm{meas}}=1.82$ vs 理論 $\sqrt{\pi}\approx1.77$、誤差 **2.8%** | **実行済み（component coupling）** |
| 静止液滴 | [§13b L141–151](../../paper/sections/13b_force_balance.tex)：FD/CCD = 69× 寄生流れ比較を測定 | **実行済み（force balance）** |

**問題点**:

Abstract は**4 件すべてを「今後の課題」として位置づけている**が、本体には 4 件すべての実行結果が存在し、定量的な数値が報告されている。査読官は abstract を信用して読み始め、§13/§14 で実行結果に出会うと「abstract と本文が一致しない」と判断する。

**Severity 根拠**: 査読論文の規約上、abstract は本文の正しい要約でなければならず、`未実施` と書かれた検証が `実施済み` で本体に存在することは **misrepresentation of scope**。論文の信頼性に関わる FATAL。

**Recommended fix（参考、適用は別 CHK）**:

スコープ階層を明示する：smoke/closure 合格は完了、Hysing-2009 級の terminal-velocity 定量比較・Prosperetti 1981 dispersion 比較・Hysing 円盤定量基準は今後課題、と区別。

```latex
% L56-59 案
コンポーネント単体検証（CCD 精度・Zalesak 円盤・PPE 収束等）と
界面結合検証（Force Balance：FD/CCD = $69\times$，RT 成長率誤差 $2.8\%$）に加え，
物理ベンチマーク（毛細管波 smoke 合格・気泡上昇 closure PASS）を実施する．
Hysing-2009 級の terminal-velocity・Prosperetti 1981 dispersion 等の
定量基準合致は今後の課題として位置づける．
```

---

## MAJOR

### M-1 — 「根本的に解決する」（L46）の過大表現

**Location**: `paper/sections/00_abstract.tex` L46

**事実**:

- Abstract L44–46:
  > `本稿は，この問題を結合コンパクト差分法（CCD，$\Ord{h^6}$），`
  > `Hermite 場延長法（HFE; Aslam 2004 の Extension PDE に基づく），および Dissipative CCD 散逸機構の組み合わせにより`
  > `根本的に解決する設計を提案する．`

**本体での実際の主張**:

- [§1 L23](../../paper/sections/01_introduction.tex)：「平滑領域の数値離散化誤差成分を **CSF モデル誤差 $\Ord{\varepsilon^2}$ が律速する水準まで低減する**」
- [§15 L12](../../paper/sections/15_conclusion.tex)：「本稿の技術的中核は**寄生流れの根本的抑制**にあり」（解決ではなく抑制）
- [§15 L124–126](../../paper/sections/15_conclusion.tex)：
  > `PPE は FD 直接法 $\Ord{h^2}$ + CCD 勾配 $\Ord{h^6}$ の併用で`
  > `Balanced-Force 条件を $\Ord{h^6}$ 精度で維持するが，`
  > `**CSF $O(\varepsilon^2)$ モデル誤差の根本的除去には分相 PPE + HFE（…）が必要**`
- [§15 L165–168](../../paper/sections/15_conclusion.tex)：「分相 PPE + HFE の **NS パイプラインへの統合実装は…最優先課題**」「残る課題は IPC 増分形式との結合および移動界面を含む時間発展への組み込み」

**問題点**:

本体は一貫して「**抑制**」「**律速まで低減**」と表現し、CSF モデル誤差そのものの根本除去には**分相 PPE + HFE のフル統合が必要**であり、それは未完了であると明言。Abstract の「根本的に解決する設計を提案する」は本体支持より一段強い主張。

特に動詞対比：

| 場所 | 動詞 |
|---|---|
| Abstract L46 | **解決する** |
| §1 L23 | **低減する** |
| §15 L12 | **抑制** |
| §15 L126 | （根本除去には）**必要** |

「解決」と「抑制」は学術文脈で意味が異なり、前者は問題の disappear、後者は magnitude reduction を含意。

**Severity 根拠**: 査読官は abstract を read & flag し、本文との整合を調べる。本論文の central claim の動詞選択が本体より一段過大なので、reviewer skepticism を招く。

**Recommended fix**: `根本的に解決する設計を提案する` → `寄生流れを CSF モデル誤差律速の水準まで根本的に抑制する設計を提案する`

---

### M-2 — 主要定量結果の欠落（FD/CCD = 69×、分相 PPE $\Ord{h^{7.0}}$）

**Location**: Abstract L40–60 全体

**事実**:

本体には次の **headline-level な測定値**が存在するが、abstract は一切触れない：

- [§13b L150](../../paper/sections/13b_force_balance.tex)：
  > `FD は CCD の**約 69 倍**の寄生流れを生じた．`
- [§13i L42](../../paper/sections/13i_error_budget.tex)：error budget 表で `FD/CCD $= 69\times$` と表頭に記載
- [§12h L98](../../paper/sections/12h_summary.tex) / [§13i L84, L127](../../paper/sections/13i_error_budget.tex)：
  > `分相 PPE + DC $k{=}3$: 全密度比で $\Ord{h^{7.0}}$`

**問題点**:

`69×` は「CCD で寄生流れを抑制する」という abstract の central claim を**唯一直接定量化する数値**。これが abstract に無いと、読者は理論主張と検証結果を頭の中で結びつけられない。同様に分相 PPE が ρl/ρg = 1–1000 で**設計次数 $\Ord{h^6}$ を上回る $\Ord{h^{7.0}}$** を達成した点は、論文の最強実証であり、査読官・引用者にとって最大の hook。

業界慣行：トップティア論文の abstract は最低 1 つ headline number を含む（例：「reduces spurious currents by 69× compared to FD」「achieves $\Ord{h^{7.0}}$ convergence at all density ratios up to 1000:1」）。

**Severity 根拠**: 業界慣行違反 + 論文の marketing 損失。論文 acceptance への影響は中程度〜大。

**Recommended fix**: abstract 後半（L55 と L56 の間あたり）に 1〜2 文挿入：

```latex
コンポーネント検証では CCD 勾配が標準 FD に対して
寄生流れ振幅を約 69 倍低減し，分相 PPE + 欠陥補正法は密度比 1:1--1000
の全範囲で $\Ord{h^{7.0}}$ 収束を達成する（§\ref{sec:force_balance}，§\ref{sec:verify_split_ppe_dc}）．
```

---

### M-3 — 「静止液滴」を future-work 側に列挙する誤分類

**Location**: `paper/sections/00_abstract.tex` L57–59

**事実**:

Abstract L57 は「物理ベンチマーク（**静止液滴**・毛細管波・気泡上昇・Rayleigh--Taylor 不安定）」とし、L59 で「実証は今後の課題」と blanket 宣言。

**しかし**：

- [§13b L141–155](../../paper/sections/13b_force_balance.tex)：静止液滴 (`exp13_03_force_balance_static_droplet`) を**Force Balance 検証の主軸**として実行し、Laplace ジャンプ・寄生流れ空間分布・$\|\bu\|_\infty$ 時間履歴・FD/CCD 比較を測定済み。
- [§12h](../../paper/sections/12h_summary.tex) U7：静止液滴を component verification U7 として実行済み。

**問題点**:

静止液滴は本論文の **Force Balance 主張の最重要証拠**であり、4 件のうちで唯一 FATAL/MAJOR レベルで完了している。これを「今後の課題」側に並列配置するのは **factually incorrect**。

**Severity 根拠**: F-2 の特殊ケース。F-2 が全 4 件の status mismatch をカバーするので二重カウントを避けて MAJOR に降格。ただし静止液滴は最も重要な「実行済み」項目なので独立記載に値する。

**Recommended fix**: 静止液滴を「実施済み Force Balance 検証」側に明示移動。M-2 の fix 例と統合可能。

---

### M-4 — 「外付け補正なしに内在的に抑制」（L54）の表現精度不足

**Location**: `paper/sections/00_abstract.tex` L52–54

**事実**:

Abstract L52–54:
> `HFE が CCD ステンシルの界面 Gibbs 振動を除去し，`
> `Balanced-Force 演算子整合と FCCD 面ジェット sub-system がコロケート格子でのチェッカーボード不安定を`
> `**外付け補正なしに内在的に抑制する**（§~\ref{sec:extension_pde}，§~\ref{sec:checkerboard_solution}）．`

**本体での記述**:

[§8 L107–122](../../paper/sections/08_collocate.tex)：
> （L109）`格子スケールデカップリング（FCCD 面ジェット sub-system で解消）`
> （L110）`**どちらか一方のみでは寄生流れまたはチェッカーボードが残存する．**`
> （L113）`歴史的には Rhie と Chow による [...]`
> （L119–121）`FCCD 面ジェット sub-system [...] $2\Delta x$ チェッカーボードモードの発散駆動を抑制`

[§8 L160](../../paper/sections/08_collocate.tex)：
> `特にコロケート格子では，変密度 PPE の離散演算子が $2h$ チェッカーボードモードに対してほぼ零固有値を持つ`

[§8e L122](../../paper/sections/08e_fccd_bf.tex)：FCCD + GFM の残差は $\Ord{\Delta x^2}$（**ゼロではない**）。

**問題点**:

「内在的に抑制する」という表現は **emergent / passive** な印象を与え、`BF + FCCD という二系統の意図的設計の協働` という事実を覆い隠す。本体は「片方では残存」と明示している。また、

- 「外付け補正なしに」は**Rhie–Chow を採用しない**という意味では正確
- だが FCCD 面ジェット sub-system は**それ自体が非自明な代替設計**であり、`外付け` の対義は `内在` ではなく `代替設計` のはず

学術精度上、`Balanced-Force 演算子整合と FCCD 面ジェット sub-system の協働により、Rhie–Chow 補間に頼らずチェッカーボード不安定を抑制する` の方が body-faithful。

**Severity 根拠**: 用語選択が本体より弱い精度を示唆。FATAL ほどではないが、査読時に refree が突くポイント。

**Recommended fix**: `外付け補正なしに内在的に抑制する` → `Rhie--Chow 補間に頼らず BF と FCCD の協働により抑制する` または `両者の協働で外部補正に依存せずに抑制する`

---

## MINOR

### N-1 — 「CCD $\Ord{h^6}$」のスコープ語不在

**Location**: `paper/sections/00_abstract.tex` L44, titlepage L18, L28

[§4 L155–160](../../paper/sections/04_ccd.tex) は明示的に：

> `内点が $\Ord{h^6}$ でも，Equation-II 境界閉包が局所 $\Ord{h^2}$ を持つ場合，`
> `重み付き $L^2$ ノルムは $\|e\|_{L^2}=\Ord{h^{5/2}}$ に律速される [...]`
> `本稿の精度主張「CCD $\Ord{h^6}$」は**内点点別誤差**を指し，`
> `大域 $L^2$ 漸近は $\Ord{h^{5/2}}$ である．`

**Recommended fix**: L44 を `結合コンパクト差分法（CCD，内点 $\Ord{h^6}$）` または最低でも footnote で global $L^2$ caveat を記載。Titlepage L18 / L28 にも同様の注釈を 1 行追加。

---

### N-2 — 「$\Ord{1}$ の誤差体積力」（L43）の framing

**Location**: `paper/sections/00_abstract.tex` L43

[§1 L14](../../paper/sections/01_introduction.tex) と [§8 L156–161](../../paper/sections/08_collocate.tex) によれば、寄生流れの grid-persistent 構造は：

- **Operator mismatch**：$\Ord{h^2}$ の残差 force（[§8 L156, L159](../../paper/sections/08_collocate.tex)）
- **2Δx 零モード増幅**：$O(1/\lambda_{\min})$ 増幅（[§8 L161](../../paper/sections/08_collocate.tex)）
- **CSF モデル誤差**：$\Ord{\varepsilon^2}=\Ord{h^2}$（[§1 L14](../../paper/sections/01_introduction.tex)）

の三者複合であり、純粋な「$\Ord{1}$ の誤差体積力」という性格付けは textbook-loose。"格子細分化で残留する" を本体的に書くなら `$\Ord{h^2}$ オーダーで残留しつつ, 零モード増幅で見かけ $\Ord{1}$ の影響を生む` が正確。

**Severity 判断**: 教科書的省略は許容範囲（abstract で詳細化すると煩雑）。ただし論文整合性として要意識。

**Recommended fix**: 軽い書き換えで本体整合可能。例：`格子を細分化しても下限が消えない誤差体積力を生む`（オーダー語を回避）。

---

### N-3 — HFE 出典「Aslam 2004」の引用形式

**Location**: `paper/sections/00_abstract.tex` L45

`Aslam 2004` は本体 [§9c L131](../../paper/sections/09c_hfe.tex) で `\cite{Aslam2004}` 形式で正規引用済み。Abstract では `\cite{}` を使わず素のテキストで `Aslam 2004` と記載。

学術慣例として：
- author-year 形式なら `Aslam (2004)`（括弧形）
- numeric 形式なら `\cite{Aslam2004}` または `[12]`

`Aslam 2004` の素表記は文献参照として弱い。ただし abstract 内 cite は journal style 依存（IEEE 系では abstract 内 cite 禁止、Springer 系では許容）。

**Recommended fix**: スタイル選択次第だが、本論文のスタイルが author-year であれば `Aslam (2004)` の括弧形に統一。Cite 可能スタイルなら `\citep{Aslam2004}` 化。

---

### N-4 — Abstract 内の章節 cross-reference（self-contained 慣例違反）

**Location**: `paper/sections/00_abstract.tex` L54

`§~\ref{sec:extension_pde}, §~\ref{sec:checkerboard_solution}` の章節参照あり。Titlepage 表（L23, L26, L27, L28）にも複数の `§~\ref{...}` が存在。

学術慣行：abstract / executive summary は **self-contained** が原則。読者が論文本文へアクセスせずに abstract のみで scope を判別できることが期待される。章節参照は self-contained 性を損なう。

**Severity 判断**: 既存スタイル選択の問題で本論文一貫性は保たれているため致命的ではない。査読官が style 観点で flag する可能性あり。

**Recommended fix**: スタイル選択。残すなら `\autoref{}` でなく `\S\ref{}` のように一貫化。除去するなら本文のみに留めて abstract から削除。

---

### N-5 — 用語ゆらぎ：「分相 PPE」「分相 PPE 解法」+ DC k=3 の有無

**Location**: `paper/sections/00_abstract.tex` L51, titlepage L23

本体での用語：

- [§9b](../../paper/sections/09b_split_ppe.tex)：`分相 PPE 解法`
- [§13i L84, L127](../../paper/sections/13i_error_budget.tex)：`分相 PPE + DC $k{=}3$`
- [§12h L98](../../paper/sections/12h_summary.tex)：`分相 PPE + DC $k = 3$ + HFE`

Abstract L51 は `分相 PPE 解法`、titlepage L23 は `分相 PPE + HFE`。Abstract 文中で DC や HFE の同伴有無が明示されない。

**Recommended fix**: 本体の主要構成 `分相 PPE + HFE + DC` に揃える。例 L51：`高密度比では分相 PPE + HFE 解法（必要に応じ欠陥補正 DC）により [...]`。

---

### N-6 — Titlepage L21「変密度 IPC（van Kan 1986）」の引用適切性

**Location**: `paper/sections/00_abstract.tex` titlepage L21

van Kan 1986（"A second-order accurate pressure-correction scheme for viscous incompressible flow"）は等密度 IPC の original reference。**変密度応用は別問題**で、[§13f L26–28](../../paper/sections/13f_coupling.tex) は IPC + 変密度の根本的限界（$\bnabla p^n$ が界面密度ジャンプを横断して発散）を明示。

Titlepage L21「変密度 IPC（van Kan 1986）」は、van Kan 1986 が変密度を扱ったかのような誤読を招く。本体 [§15 L94](../../paper/sections/15_conclusion.tex)：「変密度 IPC Projection 法から ... AB2 + IPC スプリッティング（van Kan 1986）」と記載しており、引用対象は IPC 一般、変密度応用は本論文独自。

**Recommended fix**: Titlepage L21 を `IPC 法（van Kan 1986）+ 変密度拡張 + CCD-PPE` のように IPC と「変密度拡張」を分離記述。

---

## 総括

| 区分 | 件数 | スコア影響 |
|---|---|---|
| FATAL | 2 | publication blocker。F-1 は同一ファイル内自己矛盾、F-2 は本文との scope 不整合。 |
| MAJOR | 4 | 過大主張・主要結果欠落・誤分類・表現精度不足。査読 acceptance リスク。 |
| MINOR | 6 | スタイル整備・用語整合・引用形式。査読官による flag 可能性中。 |

**勧告**: F-1 / F-2 を解消後に再レビューを推奨。M-1〜M-4 の同時修正で abstract の対外発信力が大幅向上し、論文の central claims（FD/CCD = 69×、分相 PPE $\Ord{h^{7.0}}$）が読者に到達する。

**Reviewer note**: 本論文は技術内容として（特に分相 PPE + HFE による収束性回復、Balanced-Force + FCCD 二重設計）強い貢献を含むが、abstract がそれを十分に表出できていない。Body-faithful な書き直しが本論文の評価を引き上げる。

---

**Verification base files (file:line references)**:

- [`paper/sections/00_abstract.tex`](../../paper/sections/00_abstract.tex)（L1–60；査読対象）
- [`paper/sections/01_introduction.tex`](../../paper/sections/01_introduction.tex)（L14, L23, L184, L213）
- [`paper/sections/01b_classification_roadmap.tex`](../../paper/sections/01b_classification_roadmap.tex)（L219, L227–229）
- [`paper/sections/04_ccd.tex`](../../paper/sections/04_ccd.tex)（L155–160）
- [`paper/sections/08_collocate.tex`](../../paper/sections/08_collocate.tex)（L107–122, L156, L159–161, L170, L217）
- [`paper/sections/08e_fccd_bf.tex`](../../paper/sections/08e_fccd_bf.tex)（L122）
- [`paper/sections/09c_hfe.tex`](../../paper/sections/09c_hfe.tex)（L25, L29–33, L131）
- [`paper/sections/09d_defect_correction.tex`](../../paper/sections/09d_defect_correction.tex)（独立節として確認）
- [`paper/sections/12h_summary.tex`](../../paper/sections/12h_summary.tex)（L67, L72, L98, L104）
- [`paper/sections/13b_force_balance.tex`](../../paper/sections/13b_force_balance.tex)（L141–151）
- [`paper/sections/13f_coupling.tex`](../../paper/sections/13f_coupling.tex)（L26–28, L198–227）
- [`paper/sections/13i_error_budget.tex`](../../paper/sections/13i_error_budget.tex)（L42, L66, L84, L127）
- [`paper/sections/14_benchmarks.tex`](../../paper/sections/14_benchmarks.tex)（L99, L158, L179, L183）
- [`paper/sections/15_conclusion.tex`](../../paper/sections/15_conclusion.tex)（L12, L94–98, L124–126, L165–168）
