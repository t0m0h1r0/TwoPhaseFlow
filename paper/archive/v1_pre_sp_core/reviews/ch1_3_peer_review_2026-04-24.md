# §1–§3 Peer-Reviewer 厳正レビュー (2026-04-24, CHK-195)

**対象稿**: `paper/main.tex` §1–§3（9 ファイル・計 2,117 行・約 35–40 pp）
**対象ファイル**: `01_introduction.tex`, `01b_classification_roadmap.tex`, `02_governing.tex`, `02b_surface_tension.tex`, `02c_nondim_curvature.tex`, `03_levelset.tex`, `03b_cls_transport.tex`, `03c_levelset_mapping.tex`, `03d_ridge_eikonal.tex`
**視座**: JCP / Int. J. Numer. Methods Fluids 級の査読者目線（外部視点）
**評価軸**: (I) 技術的正確性 / (II) Narrative・構成 / (III) 引用完全性 / (IV) 文体・表現
**成果物**: 本メモ（レビュー + 優先順位付き Fix Plan）。本 CHK では .tex 実装修正は行わない。

---

## 1. Summary

### 1.1 Issue 件数マトリクス

| Severity | I. 技術 | II. Narrative | III. 引用 | IV. 文体 | 計 |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Critical** | 1 (C-3) | 2 (C-1, C-4) | 1 (C-2) | 0 | **4** |
| **Major**    | 1 (M-8) | 3 (M-1, M-2, M-5) | 3 (M-3, M-4, M-7) | 1 (M-6)| **8** |
| **minor**    | 1 (m-7) | 1 (m-6) | 1 (m-4) | 4 (m-1, m-2, m-3, m-5) | **7** |
| **計**       | 3       | 6             | 5         | 5        | **19** |

### 1.2 総合判定

**Major revision required.**

技術的中核（Theorem 1・CLS 定式化・Ridge–Eikonal 構成・SP 参照系）は堅牢で，設計哲学の一貫性も高い。CHK-189 以降の SP-core 再編で構造的改善が顕著（後述 §6）。一方，**受理前に必須**の欠陥として：

1. **§1 の引用完全性ゼロ**（0 `\cite{}` in 281 行）: 寄生流れ・CSF・チェッカーボードに関する canonical claim が無出典。
2. **§1 冒頭の前方参照密度**: 読者が §1 L14–26 で §8.2 / §9 / §9.4 に 3 回跳ばされ，概念未定義のまま設計主張を強制される。
3. **Theorem 1（§2c）の声明と適用域の乖離**: 「$\psi$ と $\phi$ は同一曲率を与える」と無条件に述べつつ，L209・L213 で「連続・非飽和領域のみ」「離散では界面近傍に限定」と walk back。査読者は定理声明そのものの妥当性を疑う。
4. **§3.4（Ridge–Eikonal）の方法論順序違反**: §3 章中で §6（非一様格子）・§7（FCCD 移流）・§11（$\xi$-SDF 検証）を前提として使用。

Major Issue は narrative redundancy（§1.1 困難 vs §1.3 失敗例），§1 での未定義記号使用（$\psi$/$\phi$/CLS），SP-Index の可視性，§2c・§3c の citation 不在，§3b の subsection 肥大化，§3c 末尾の「次章では CCD」偽章境界などで，いずれも 1 CHK で解消可能。Minor は `\textbf` 過用，定量下限なしの qualifier，前方 quantitative promise など。

Critical 全 4 件 + Major 8 件を解消すれば，査読者は accept-with-minor に移行可能と判断。**SP-I / SP-J 投稿前の完遂を強く推奨**。

---

## 2. Critical Issues（受理の障害）

### C-1. §1 冒頭 13 行に前方参照 5 件

- **File**: [paper/sections/01_introduction.tex:14-26](paper/sections/01_introduction.tex#L14-L26)
- **Category**: II. Narrative
- **問題**:
  - L15 に `§~\ref{sec:failure_modes}` と `§~\ref{sec:balanced_force}` の 2 件。
  - L22 に `§~\ref{sec:ppe_discretization_choice}`（§9.4）。
  - L26 に `§~\ref{sec:split_ppe_motivation}`（§9）。
  - 読者は「寄生流れ」「CSF モデル誤差」「分相 PPE」「DC $k=3$」「HFE」「Balanced-Force 条件」という全 6 概念を\*\*未定義の状態で\*\*押し付けられる。論文冒頭 13 行で読者の理解より技術的先取りが優先されており，査読者の第一印象を大きく損なう。
- **推奨対処**:
  - L14–26 を「\*\*技術概要 gloss\*\*」として再構成：各前方参照に 1 行の平易な説明を付す（例：「\*\*分相 PPE\*\*：各相で定数密度ポアソン方程式を独立に解き，界面では圧力ジャンプ条件で結合する手法。詳細は §9」）。
  - または冒頭 2 段落を「動機 + 1 文での本稿の貢献」に圧縮し，技術的詳細は §1.4（`sec:design_philosophy`）以降に移動。
- **推定 LOC**: +8 〜 −6（gloss 挿入 or 圧縮）
- **関連**: M-2（未定義記号）と連動。冒頭再構成時に同時解消推奨。

### C-2. §1 全体で `\cite{}` 0 件（281 行）

- **File**: [paper/sections/01_introduction.tex](paper/sections/01_introduction.tex)（全体）
- **Category**: III. 引用完全性
- **問題**: `grep -c '\\cite{' 01_introduction.tex = 0`。一方で以下の canonical claim が無出典：
  - L263–266 「中心差分が周期 $2\Delta x$ チェッカーボードモードにゼロ勾配を返すことは代数的に示される」→ Patankar 1980, Ferziger–Perić 2002 等の標準参照が必要。
  - L273–278 「移流スキームの数値拡散により界面プロファイルが徐々にぼやける」→ LeVeque 2002 / Osher–Fedkiw 2003。
  - L12 「寄生流れ」概念自体 → Lafaurie et al. 1994, Harvie et al. 2006, Popinet 2009。
  - L14 「CSF モデル誤差 $\Ord{\varepsilon^2}$」→ Brackbill1992（モデル）＋ Popinet2009（誤差解析）。
  - L211–213 「重力・密度差による静水圧分布を正確に扱わない寄生流れ」→ Francois2006, Sussman2000。
- **推奨対処**: 5–8 件の canonical citation を追加。全て `bibliography.bib` に既存のキーで対応可能（確認済：Brackbill1992 L72, Popinet2009 L377, Francois2006 L300, Sussman2000 L145, HirtNichols1981 L188, OsherSethian1988 L83）。
- **推定 LOC**: +5 〜 +8
- **関連**: C-1 との同時修正で § 冒頭の学術的密度を一気に向上可能。

### C-3. Theorem 1（曲率不変定理）の声明と適用域の乖離

- **File**: [paper/sections/02c_nondim_curvature.tex:173-213](paper/sections/02c_nondim_curvature.tex#L173-L213)
- **Category**: I. 技術的正確性
- **問題**:
  - L173–184 の定理声明は「$\psi = g(\phi)$, $g \in C^2$, $g' > 0$」のもとで「曲率は $\psi$ と $\phi$ のいずれから計算しても同一の値を与える」と無条件に述べる。
  - しかし L209 で「連続かつ非飽和の領域では数学的に同一」と restriction が後出し。
  - L213 でさらに「離散実装では値域制限・飽和領域・閾値処理によりこの等価性の適用範囲は界面近傍に限定される」と離散的制約まで補足。
  - 査読者は \*\*定理文そのもの\*\*を読んだ時点で「`$g' > 0$` が飽和点で破れる（`$\psi = H_\varepsilon$` は $\phi \to \pm\infty$ で $g' \to 0$）ため L173–184 は不完全」と判断する。§2c L170 の `$\psi_{\min} < \psi < 1 - \psi_{\min}$` restriction（$\psi$-direct 曲率の適用範囲）は定理自体の前提条件であり，証明の後に walkback される形は数学的に不適切。
- **推奨対処**:
  - 定理文本体に前提条件を明記：「`$g \in C^2$`, `$g' > 0$` on $\phi \in I$（ここで $I$ は適用領域）」。
  - 系（corollary）として「CLS の $H_\varepsilon(\phi) = 1/(1+e^{-\phi/\varepsilon})$ は $|\phi| < \infty$ 全域で $g' > 0$ を満たすが，数値離散では $\psi \to \{0, 1\}$ 近傍で $g'(\phi) = \varepsilon^{-1}\psi(1-\psi) \to 0$ となり適用域は界面近傍 $|\phi| \lesssim O(\varepsilon)$ に限定される」を定理直下に配置。
  - L213 の「界面近傍に限定される」を系の文言と統一し，§2c L170 の `$\psi_{\min} < \psi < 1-\psi_{\min}$` と同じ基準を参照。
  - 03c 側（[03c_levelset_mapping.tex:170-186](paper/sections/03c_levelset_mapping.tex#L170-L186)）の $\psi$-direct 曲率安定性記述との整合も確認し，03c L179-181 の「Eikonal 誤差 $\delta \ll 1$ のとき $\Ord{\delta^2}$ に留まる」評価と定理 restriction を両立させる。
- **推定 LOC**: +10 〜 +12（定理文 restriction 追加 + Corollary 1）
- **関連**: 03c L170–186 と同期修正必要（両ファイルで定理声明が食い違わないように）。

### C-4. §3.4（Ridge–Eikonal）の方法論順序違反

- **File**: [paper/sections/03d_ridge_eikonal.tex](paper/sections/03d_ridge_eikonal.tex)（全 249 行）
- **Category**: II. Narrative
- **問題**:
  - §3.4 は §3 の末端（界面追跡法の定式化）に配置されている。
  - ところが本節は以下の\*\*後章\*\*への前方参照を本文本体（gloss なし）で使用：
    - L48 `§~\ref{sec:grid_density}` → §6（非一様格子）
    - L52 `\texttt{EikonalReinitializer.\_xi\_sdf\_phi}` → §11 の検証実装 / §7 の再初期化実装
    - L233, L245 FCCD $\Ord{h^6}$ 微分 → §4（CCD 基礎），§4.5（FCCD）
    - L238 「直交調和格子拡張（D1–D4）」→ §6.4–§6.5 の非一様格子拡張
  - 読者は §3.4 を読むために §4–§7 を先読みする必要がある。これは level-set 章で CCD・格子・FCCD をすべて既習前提とするものであり，\*\*方法論的な倒立\*\*。
  - さらに L36 の Morse 指数，L73–84 の「Morse 遷移」は §3 までの範囲で初出（M-7 と連動，Milnor 1963 等の出典なし）。
- **推奨対処**: 3 択のいずれか：
  1. **§3.4 を付録に移動**し，§3 末尾には「Ridge–Eikonal の簡潔な動機 + 詳細は付録 X」の 1 段落のみ残す。
  2. **§3.4 を §7 末尾または §11 直前に移動**（CCD・格子・FCCD がすべて既習の位置）。
  3. **§3.4 冒頭に「§6, §7, §11 前提知識 box」を明示**し，読者に forward-jump を許可 + 各 forward-ref に 1 行 gloss を追加。
  - 推奨は 2 or 3。SP-B / SP-E の論文的中心性を考えると削除（付録化）は不可。
- **推定 LOC**: +12（gloss box 追加）〜 約 250（節ごと移動の場合）
- **関連**: M-2（§1 未定義記号）と構造的に同根：本稿全体で「概念初出の位置」と「その概念を使う位置」の乖離が発生している。

---

## 3. Major Issues（要修正）

### M-1. §1.1（4 困難）vs §1.3（4 失敗例）の重複

- **File**: [paper/sections/01_introduction.tex:163-281](paper/sections/01_introduction.tex#L163-L281)
- **Category**: II. Narrative
- **問題**: `sec:challenges`（4 困難）と `sec:failure_modes`（4 失敗例）は実質的に同じ 4 テーマを 2 度語っている。
  - 困難 2（表面張力）≡ 失敗例 1（寄生流れ）
  - 困難 1（界面捕捉・質量保存）≡ 失敗例 2（質量損失）+ 失敗例 4（にじみ）
  - 困難 3（非圧縮）≡ 失敗例 3（チェッカーボード）
  - 困難 4（寄生流れ）≡ 失敗例 1（寄生流れ）← 困難 2 とも重複
  - 各項目に「→ 本稿の対処」ブロックがあり，同じ手法（CCD・Balanced-Force・CLS・DCCD）が 2 回列挙される。
- **推奨対処**:
  - §1.1 を 4 困難の\*\*物理的説明に限定\*\*（「対処」ブロック削除）。
  - §1.3 を「典型的症状（before）→ 本稿の対処（after）」のケーススタディ形式に再構成し，4 困難との対応を冒頭で 1 行明示（「各失敗例は §1.1 の困難 X に対応する」）。
  - 合計で $\approx$ 25 行削減。Narrative 冗長性が解消され，読者の読書負荷が大きく減少。
- **推定 LOC**: −25 〜 −35

### M-2. §1 で使用する $\psi$ / $\phi$ / CLS が §2 まで未定義

- **File**: [paper/sections/01_introduction.tex](paper/sections/01_introduction.tex)（L31, L129–138 他）
- **Category**: II. Narrative
- **問題**:
  - L31「Conservative Level Set」，L129 Fig. 1 caption が自ら「正式定義は §~\ref{sec:notation}」と認めている。
  - Fig. 1 キャプションで $\psi$, $\phi$, $H_\varepsilon$ を使用するが §2.1 まで定義なし。
  - L180, L215, L245 でも `$\bnabla\psi$`, `$\sigma\kappa\bnabla\psi$` が登場。
  - 査読者は「Fig 1 の理解に §2 を先読みする必要がある」時点で narrative 設計を疑う。
- **推奨対処**: §1 冒頭（L10–27 のいずれか）に\*\*minimal glossary tcolorbox\*\*を配置：
  ```
  ┌─ Minimal Glossary（詳細は §2） ──────┐
  │ φ  : 符号付き距離関数（signed distance）
  │ ψ  : 平滑化 Heaviside 関数 H_ε(φ) ∈ [0,1]
  │ CLS : Conservative Level Set（§3）
  │ CCD : Compact Combined Difference（§4）
  │ PPE : 圧力 Poisson 方程式（§8.2）
  └────────────────────────────┘
  ```
  - または §1.4 の設計哲学表に列を追加。
- **推定 LOC**: +12 〜 +15

### M-3. SP-Index が §2.5 subsubsection に埋没

- **File**: [paper/sections/02c_nondim_curvature.tex:238-273](paper/sections/02c_nondim_curvature.tex#L238-L273)
- **Category**: III. 引用完全性
- **問題**:
  - SP-A..SP-O の索引表が §2.5 の `\subsubsection{SP-Index}`（推定）内に配置されている。
  - ToC には現れず，本文中で「§~\ref{sec:sp_index} 参照」と指示する箇所（例：§3.4 L13）の読者が辿れない。
  - SP 参照は本稿の最重要 cross-reference 系（15 本の短報を本稿が統合する設計）であり，可視性は必須。
- **推奨対処**:
  - §2.5 を `\subsection` に昇格（`\subsection{SP シリーズ短報の索引}`）。
  - または §0（abstract 直後）に「本稿を貫く短報群」として独立セクション化。
  - または `\listoftables` または専用 `\listofsps` 相当を main.tex に追加。
- **推定 LOC**: metadata 変更のみ（`\subsubsection` → `\subsection`，1 行）
- **関連**: §3.4 L13 他，多数の SP-X 参照箇所の可読性向上。

### M-4. §2b CSF $\Ord{\varepsilon^2}$ モデル誤差の無出典

- **File**: [paper/sections/02b_surface_tension.tex:23](paper/sections/02b_surface_tension.tex#L23)
- **Category**: III. 引用完全性
- **問題**: L23 「CSF モデルは $\Ord{\varepsilon^2} \approx \Ord{\Delta x^2}$ のモデル誤差を持ち」に出典なし。L17–19 で Brackbill1992 は引用済みだが，これは\*\*モデルの提案者\*\*への引用であり，\*\*誤差階数の数値解析\*\*は別出典が必要。
- **推奨対処**: L23 に `\cite{Popinet2009, Francois2006}` を追加。両者とも bibliography.bib に存在（L377, L300）。Popinet2009 は $\Ord{\varepsilon^2}$ を明示的に導出，Francois2006 は balanced-force 解析で corroborate。
- **推定 LOC**: +1（cite 追加のみ）
- **関連**: C-2（§1 引用不在）と同じ系統の citation gap。

### M-5. §3b 288 行が単一 `\subsection` で subsubsection 分割なし

- **File**: [paper/sections/03b_cls_transport.tex](paper/sections/03b_cls_transport.tex)（全 288 行）
- **Category**: II. Narrative
- **問題**:
  - ファイル全体が `\subsection{保存形移流と再初期化}` 相当の単一ブロック。
  - 内部構造（物性補間・移流・体積保存解析・再初期化 PDE・$\varepsilon$ 設計・仮想時間 $\Delta\tau$ 安定性・収束監視）が 288 行に流れ，読者に mental map が提示されない。
  - ToC でも subsection 1 件しか立たず，cross-reference 不便。
- **推奨対処**: 以下の 3–4 subsubsection に分割：
  1. `\subsubsection{保存形移流と体積保存性}`（L30–75）
  2. `\subsubsection{再初期化方程式（等方拡散形）}`（L77–160）
  3. `\subsubsection{$\varepsilon$ の設計と仮想時間 $\Delta\tau$}`（L161–230）
  4. `\subsubsection{再初期化収束監視と実装指針}`（L231–288）
- **推定 LOC**: +4（`\subsubsection` 4 行追加のみ）

### M-6. §3c L184–186「次章では CCD」の偽章境界

- **File**: [paper/sections/03c_levelset_mapping.tex:184-186](paper/sections/03c_levelset_mapping.tex#L184-L186)
- **Category**: IV. 文体・表現
- **問題**: L184「以上で界面追跡に必要な CLS 法の定式化がすべて整った．次章では…CCD 法の設計原理と離散化を示す」と述べるが，実際は §3.4（03d_ridge_eikonal.tex）が直後に続き，CCD は §4 開始。読者は L186 で「章が終わった」と思い §3.4 冒頭で違和感を覚える。
- **推奨対処**: L184–186 を「以上で CLS 法の基本定式化（移流・再初期化・曲率）が揃った．次節（§3.4）では級論理を拡張し，トポロジー変化を連続的に扱う Ridge–Eikonal ハイブリッドを導入する」に書き換え。
- **推定 LOC**: ±3

### M-7. §3.4 Morse 理論への出典なし

- **File**: [paper/sections/03d_ridge_eikonal.tex:36](paper/sections/03d_ridge_eikonal.tex#L36), [L73-84](paper/sections/03d_ridge_eikonal.tex#L73-L84)
- **Category**: III. 引用完全性
- **問題**: L36「Morse 指数の連続変化」，L84「$\xiridge$ の Morse 指数が瞬間的に変化する時刻」と Morse 理論の中核概念を使用するが出典なし。`bibliography.bib` に Milnor1963 不在（grep 確認済）。査読者は「Morse 理論の援用として rigorous か」を疑う。
- **推奨対処**:
  1. bibliography.bib に Milnor1963 `Morse Theory` or Matsumoto2002 `An Introduction to Morse Theory` を追加し，L36 と L84 で cite。
  2. または「Morse 理論の意味での指数変化」→「局所極値の生成・消滅（generation / annihilation）」に置き換え，標準 level-set 文献（Osher–Fedkiw 2003）を cite。
- **推定 LOC**: +1 cite + 最大 +10 行（bib 追加 + 用語調整）
- **関連**: C-4（方法論順序）と同じ節で解消可能。

### M-8. §2c・§3c で `\cite{}` 0 件

- **File**: [paper/sections/02c_nondim_curvature.tex](paper/sections/02c_nondim_curvature.tex), [paper/sections/03c_levelset_mapping.tex](paper/sections/03c_levelset_mapping.tex)
- **Category**: III. 引用完全性
- **問題**: `grep -c '\\cite{'` の結果が両ファイルで 0。§2c は Theorem 1（曲率不変）と無次元化という数学的中核を含むにもかかわらず出典ゼロ。§3c は $\psi$-$\phi$ 逆変換（logit / Newton）と ψ-direct 曲率を扱うが，logit 変換の数値的 well-posedness（Chang 1996 等）や ψ-direct 曲率の先行研究（Olsson-Kreiss 2005, Desjardins 2008）への引用がない。
- **推奨対処**:
  - §2c：無次元化の標準化に Tryggvason2011（既存）を cite，曲率の level-set 表現に Osher–Fedkiw 2003 を追加 cite。
  - §3c：logit/Newton 逆変換に対する先行実装として Olsson-Kreiss 2005 / Desjardins 2008 を cite（両者とも bib に存在，L17, L311）。
- **推定 LOC**: +3 〜 +5（cite 追加のみ）

---

## 4. minor Issues（文体・表現）

### m-1. `\textbf` 過用

- **File**: 全 §1–§3 ファイル
- **Category**: IV. 文体
- **問題**: 使用頻度（行数比）：
  - [01_introduction.tex](paper/sections/01_introduction.tex): 33 / 281 = **11.7%** 行
  - [02_governing.tex](paper/sections/02_governing.tex): 24 / 236 = 10.2%
  - [01b_classification_roadmap.tex](paper/sections/01b_classification_roadmap.tex): 20 / 310 = 6.5%
  - [03b_cls_transport.tex](paper/sections/03b_cls_transport.tex): 21 / 288 = 7.3%
  - [03_levelset.tex](paper/sections/03_levelset.tex): 23 / 227 = 10.1%
  - [03d_ridge_eikonal.tex](paper/sections/03d_ridge_eikonal.tex): 22 / 249 = 8.8%
  - 特に 01_introduction.tex L236–280（失敗例 1–4）に 10 件の `\textbf{症状：}`, `\textbf{原因：}`, `\textbf{本稿の対処：}` クラスタ。
- **推奨対処**:
  - 「症状 / 原因 / 対処」の定型ラベルは `\paragraph{...}` or `\item[\textbf{症状：}]` + `description` 環境に統一。
  - 概念強調は本文 1 回目のみ `\textbf`（以降は plain）。
  - 目標：各ファイル $<$ 5% 行。
- **推定 LOC**: metadata 相当（−10 程度の `\textbf{...}` 削除）

### m-2. 定量下限なしの vague qualifier

- **File**:
  - [paper/sections/03d_ridge_eikonal.tex:87](paper/sections/03d_ridge_eikonal.tex#L87) 「時間離散化の刻み幅が Morse 遷移と比して十分細ければ」
  - [paper/sections/03d_ridge_eikonal.tex:237](paper/sections/03d_ridge_eikonal.tex#L237) 「通常運転」
  - [paper/sections/03b_cls_transport.tex:255](paper/sections/03b_cls_transport.tex#L255) 「通常 5」
  - 複数ファイル「滑らかな領域」（quantitative 定義なしで多用）
- **Category**: IV. 文体 / I. 技術
- **問題**: 査読者は「十分細い」「通常」などを quantitative bound で要求する。L87 の「十分細ければ」は Morse 遷移時間スケール $\tau_M$ と $\Delta t$ の比 $\Delta t / \tau_M \ll 1$ などの定式化が可能。
- **推奨対処**: 各箇所に 1 件あたり 1 行の定量条件を補足（例：「$\Delta t < 0.1 \tau_M$」「$\|\bnabla\psi\|_\infty \cdot h < 0.3$」）。測定方法（どのベンチマークで校正済か）も §11/§12 へ cross-ref。
- **推定 LOC**: +6 〜 +10

### m-3. §12 への前方 quantitative promise が未検証

- **File**: [paper/sections/03b_cls_transport.tex:43](paper/sections/03b_cls_transport.tex#L43)
- **Category**: IV. 文体 / II. Narrative
- **問題**: L43「第~\ref{sec:verification}章のベンチマーク（体積保存誤差 $< 0.1\%$）で実際の保存性を定量確認すること」と断言。§12 の該当実測値と一致しているか要確認。現時点で 0.1% は conservative estimate だが，査読者は §12 表との数値整合を要求する。
- **推奨対処**: §12b の実測結果を確認し，0.1% が実測下限か，overstatement か判断。実測が 0.5% なら L43 を「$< 1\%$」に緩め，$\mathcal{O}(h^5)$ 収束の裏付けと明示。
- **推定 LOC**: ±1

### m-4. OsherSethian1988 が §3 本体で再引用なし

- **File**: [paper/sections/01b_classification_roadmap.tex](paper/sections/01b_classification_roadmap.tex)（cite 済），[paper/sections/03_levelset.tex:35-100](paper/sections/03_levelset.tex#L35-L100)（再引用なし）
- **Category**: III. 引用完全性
- **問題**: §1b の比較表で OsherSethian1988（Level Set 原典）を cite，§3 本文の標準 LS 説明（L35–100）で再 cite なし。査読者は §3 を独立に読む際「LS の原典は？」と探す。
- **推奨対処**: §3 L35 付近「標準的な Level Set 法 \cite{OsherSethian1988}」を追加。
- **推定 LOC**: +1

### m-5. §3.4 subsubsection 群に boxed proof/theorem 不在

- **File**: [paper/sections/03d_ridge_eikonal.tex](paper/sections/03d_ridge_eikonal.tex)
- **Category**: IV. 文体
- **問題**: §3.4 は 249 行の散文で，式・図・表が 6–8 本のみ。`\begin{theorem}` / `\begin{proposition}` / `\begin{remark}` が 1 件（L47 `\begin{remark}`）のみ。散文密度が技術的内容に不均衡。特に Morse 指数論による融合・分裂の連続化（L75–88）は命題として boxed 化が望ましい。
- **推奨対処**: 以下を boxed 命題化：
  - L75–88: `\begin{proposition}[リッジ集合のトポロジー変化の連続性]` + 簡潔な証明スケッチ。
  - L96–111: `\begin{theorem}[FMM/FSM による $\phi$ の一意再構成]` + 証明外部参照 SP-B §4。
- **推定 LOC**: +15（環境タグ + 簡潔な証明 1–2 行）

### m-6. §1 L260–266 checkerboard 代数証明が付録送り

- **File**: [paper/sections/01_introduction.tex:260-267](paper/sections/01_introduction.tex#L260-L267)
- **Category**: II. Narrative
- **問題**: L267「（付録~\ref{app:checkerboard_mode}）」と付録参照。しかし証明は 2 行（$p_j = P_0(-1)^j$, $\partial_x p_j = (p_{j+1} - p_{j-1})/(2h) = 0$）で完結し，§1 本文内 self-contained にできる。付録跳びは読者の読書経験を悪化させる。
- **推奨対処**: L260–266 に代数 1 行を埋め込む：`$(p_{j+1} - p_{j-1})/(2h) = P_0[(-1)^{j+1} - (-1)^{j-1}]/(2h) = 0$`。付録は「詳細な固有値解析」用に残す。
- **推定 LOC**: +2（inline equation 追加）

### m-7. §2 物性補間の根拠 citation 不足

- **File**: [paper/sections/02_governing.tex](paper/sections/02_governing.tex)（harmonic mean / arithmetic mean 選択箇所）
- **Category**: I. 技術 / III. 引用
- **問題**: $\rho^{-1}$ の harmonic mean，$\mu$ の arithmetic mean 選択の理由として Prosperetti1981（L322）が cite されていない可能性。確認要（§2 の 3 cite が何を指しているか要精査）。harmonic-vs-arithmetic の理論的根拠は Kang-Fedkiw 2000, Sussman 2000 にある。
- **推奨対処**: 該当箇所に `\cite{Sussman2000, Prosperetti1981}` を追加（両者とも bib に存在）。
- **推定 LOC**: +1 〜 +2

---

## 5. Cross-Cutting Observations（横断的観察）

### 5.1 依存グラフ分析：前方参照の密度分布

§1–§3 全体で `\ref{sec:...}` を対象章別にカウント（grep 可能）：

| 参照先 | §1–§3 からの参照数 | 解釈 |
|---|---:|---|
| §4 (CCD), §4.5 (FCCD) | 多数 | §3.4 は §4 を既習前提 → C-4 |
| §6 (非一様格子) | 中 | §3.4 L48 `sec:grid_density` → C-4 |
| §7 (移流) | 中 | §3b → §7b 再初期化，§3.4 → §7 FCCD |
| §8 (collocate) / §8.2 (BF failure) | 少 | §1 L15 `sec:failure_modes` → C-1 |
| §9 (pressure) | 少 | §1 L22, L26 → C-1 |
| §11 (検証) / §12 (実験) | 少 | §3b L43 → m-3 |

**観察**: §3.4 が単独で §4–§7 依存のハブとなっている。§1 は §8–§9 への forward-ref を 3 件抱える。これらが C-1 / C-4 の根拠。

### 5.2 SP-X 参照の一貫性

| SP-ID | 主担当節 | §1–§3 での参照 | 整合性 |
|---|---|---:|---|
| SP-A | §4.5 FCCD | 0 | — |
| SP-B | §3.4 Ridge-Eikonal | 1 (03d L13) | 整合 |
| SP-E | §3.4 非一様 Ridge-Eikonal | 1 (03d L13) | 整合 |
| SP-G | §4.3 DCCD | 0 | — |
| SP-J | §2b BF failure 5 モード | 1 (02b L35) | 整合（section title で明示） |
| SP-F | §9 GPU FVM | 0 | §1–§3 では触れない（妥当） |

**観察**: §1–§3 での SP 参照は SP-B / SP-E / SP-J の 3 件のみ。全 15 SP のうち 3 件なので **可視性不足**（特に SP-Index 埋没 M-3）。

### 5.3 全体 narrative flow 図（推奨）

現状：
```
§1 (動機・困難・失敗例) → §1b (分類・ロードマップ) → §2 (記号・Two→One・CSF・無次元・Theorem1・SP-Index)
  → §3 (標準 LS 問題) → §3b (CLS 定式化) → §3c (ψ-φ 写像) → §3.4 (Ridge-Eikonal)[§4-§7依存]
```

修正後（C-4 採用による再配置）：
```
§1 (動機) → §1b (分類) → §2 (記号) → §3 (標準 LS→CLS) → §3b (CLS 定式化) → §3c (ψ-φ) 
[§3 完結] → §4 (CCD) → §5 (時間) → §6 (格子) → §7 (スキーム) → §7.x (Ridge-Eikonal) [旧 §3.4]
```

### 5.4 文体メトリクス比較

|  | 01 | 01b | 02 | 02b | 02c | 03 | 03b | 03c | 03d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 行数 | 281 | 310 | 236 | 67 | 273 | 227 | 288 | 186 | 249 |
| `\cite{}` | **0** | 9 | 3 | 2 | **0** | 2 | 1 | **0** | 3 |
| `\textbf` | **33** | 20 | 24 | 4 | 6 | 23 | 21 | 11 | 22 |
| `\textbf`率 | **11.7%** | 6.5% | 10.2% | 6.0% | 2.2% | 10.1% | 7.3% | 5.9% | 8.8% |

**観察**: 01 / 02c / 03c の cite 率がゼロ（C-2, M-8）。01 の textbf 率が突出（m-1）。02c は低 textbf・低 cite だが Theorem を含むため本質的に問題ない（M-8 で cite 補充のみ）。

---

## 6. Acknowledgments / Strengths

厳正レビューでも論文の強みを評価することが学術慣習であり，以下を明記する：

### 6.1 構造的改善（CHK-189 SP-core rewrite 以降）

- §2 の Two-Fluid → One-Fluid 導出（02_governing.tex）は明快で，界面ジャンプ条件の統合が rigorous。
- §2b の BF 失敗モード 5 分類（F-1..F-5 table）は SP-J との対応が鮮明で，査読者が読み取りやすい。
- §2c の Theorem 1（曲率不変性）の証明は簡潔かつ要点を押さえている（C-3 で声明の限界を補足するだけで accept 可能）。
- §3 → §3b → §3c → §3.4 の章構成そのものは合理的で，CLS を軸とする一貫設計が見える（C-4 の位置問題を除けば）。

### 6.2 技術的中核の強度

- CLS（保存形 + Dissipative CCD）の設計哲学（§1 L28–43）が本稿全体の主張と整合。
- 分相 PPE + DC + CCD 勾配の三位一体設計（§1 L17–25）は既存手法との差別化として明確。
- Ridge–Eikonal ハイブリッドの着想（§3.4）は新規性が高く，SP-B 短報との連携で論理的裏付けを持つ。
- Balanced-Force 条件 5 失敗モード（F-1..F-5）の診断（§2b）は実装指針として強力。

### 6.3 4 challenges → design principles の一貫した流れ

- §1.2 table（単相 vs 二相の違い）→ §1.3（4 困難）→ §1.4（設計哲学）→ §1b（ロードマップ）の順序は教育的にも有効。
- M-1（§1.1 と §1.3 の重複）を解消すればさらに鋭くなる。

---

（以下 §7 は次ページ：Actionable Fix Plan）

---

## 7. Actionable Fix Plan（優先順位付き）

### 7.1 Critical（受理前に必須，1 CHK で実装推奨）

| ID | File | 対処内容 | 推定 LOC | 実装順序依存 |
|:---:|---|---|---:|---|
| **C-1** | [01_introduction.tex:14-26](paper/sections/01_introduction.tex#L14-L26) | 冒頭 13 行の前方参照 5 件に 1 行 gloss を付与 or 段落圧縮 | +8 〜 −6 | なし（単独完結） |
| **C-2** | [01_introduction.tex](paper/sections/01_introduction.tex)（全体） | canonical claim 5–8 件に既存 bib キーで cite 追加（Brackbill1992, Popinet2009, Francois2006, Sussman2000, HirtNichols1981, OsherSethian1988 等） | +5 〜 +8 | C-1 と同時推奨 |
| **C-3** | [02c_nondim_curvature.tex:173-213](paper/sections/02c_nondim_curvature.tex#L173-L213) + [03c_levelset_mapping.tex:170-186](paper/sections/03c_levelset_mapping.tex#L170-L186) | Theorem 1 文に前提条件 $g' > 0$ on $I$ を明記 + Corollary 1 で CLS 適用域 $|\phi| \lesssim O(\varepsilon)$ を明示 | +10 〜 +12 | 両ファイル同期修正 |
| **C-4** | [03d_ridge_eikonal.tex](paper/sections/03d_ridge_eikonal.tex)（249 行） | 節冒頭に「§6/§7/§11 前提知識 box」+ forward-ref gloss 追加（推奨 option 3）。移動の場合は §7 末尾へ | +12（Option 3）/ 約 250（Option 2） | main.tex input 順序要変更（Option 2） |

**Critical 小計**: +35 〜 +38 LOC（Option 3 前提）。単一 CHK 実装可能。

### 7.2 Major（要修正）

| ID | File | 対処内容 | 推定 LOC |
|:---:|---|---|---:|
| **M-1** | [01_introduction.tex:163-281](paper/sections/01_introduction.tex#L163-L281) | §1.1 / §1.3 重複を cross-ref に圧縮；§1.1 は「物理的説明」，§1.3 は「症状→対処」に分担 | −25 〜 −35 |
| **M-2** | [01_introduction.tex](paper/sections/01_introduction.tex)（冒頭） | minimal glossary tcolorbox を §1 冒頭に配置（φ/ψ/CLS/CCD/PPE の 1 行定義） | +12 〜 +15 |
| **M-3** | [02c_nondim_curvature.tex:238-273](paper/sections/02c_nondim_curvature.tex#L238-L273) | SP-Index を `\subsubsection` → `\subsection` に昇格 | metadata（±1） |
| **M-4** | [02b_surface_tension.tex:23](paper/sections/02b_surface_tension.tex#L23) | $\Ord{\varepsilon^2}$ claim に `\cite{Popinet2009, Francois2006}` 追加 | +1 |
| **M-5** | [03b_cls_transport.tex](paper/sections/03b_cls_transport.tex)（288 行） | 3–4 `\subsubsection` に分割（移流・再初期化 PDE・$\varepsilon$ 設計・収束監視） | +4 |
| **M-6** | [03c_levelset_mapping.tex:184-186](paper/sections/03c_levelset_mapping.tex#L184-L186) | 「次章では CCD」→「次節（§3.4）では…Ridge–Eikonal」へ書き換え | ±3 |
| **M-7** | [03d_ridge_eikonal.tex:36](paper/sections/03d_ridge_eikonal.tex#L36), [L73-84](paper/sections/03d_ridge_eikonal.tex#L73-L84) | Milnor1963 or Matsumoto2002 を bib 追加 + cite；または「Morse 遷移」を「generation / annihilation」に語彙置換 + Osher–Fedkiw 2003 cite | +1 cite + 0–10 行 |
| **M-8** | [02c_nondim_curvature.tex](paper/sections/02c_nondim_curvature.tex), [03c_levelset_mapping.tex](paper/sections/03c_levelset_mapping.tex) | §2c に Tryggvason2011 / Osher–Fedkiw 2003，§3c に Olsson-Kreiss2005 / Desjardins2008 cite 追加 | +3 〜 +5 |

**Major 小計**: −25 〜 +40 LOC（net は M-1 の削減で減少方向）。Critical と同一 CHK で実装可能。

### 7.3 minor（time-box 方式，30 分で拾える分のみ）

| ID | File | 対処内容 | 推定 LOC |
|:---:|---|---|---:|
| **m-1** | 全 §1–§3 | 「症状 / 原因 / 対処」定型ラベルを `description` 環境に統一；概念強調は 1 回目のみ `\textbf` | −10 〜 −15 |
| **m-2** | 03d L87, L237; 03b L255 | vague qualifier 3 件に定量条件 1 行ずつ補足 | +6 〜 +10 |
| **m-3** | 03b L43 | §12b 実測値との整合確認 + 必要なら 0.1% → 1% に緩和 | ±1 |
| **m-4** | 03_levelset.tex L35 | OsherSethian1988 を再 cite | +1 |
| **m-5** | 03d_ridge_eikonal.tex L75-88, L96-111 | 2 箇所を `\begin{proposition}` / `\begin{theorem}` + 1–2 行証明スケッチに boxed 化 | +15 |
| **m-6** | 01_introduction.tex L260-266 | checkerboard 代数 1 行を inline 化 | +2 |
| **m-7** | 02_governing.tex（harmonic/arithmetic 選択箇所） | Sussman2000 / Prosperetti1981 の cite 追加 | +1 〜 +2 |

**minor 小計**: +0 〜 +15 LOC。全件実装推奨だが，m-1 / m-5 は個別の判断で time-box 外可。

### 7.4 実装時の注意

- **推奨実装順**: C-3 → C-1 → C-2 → M-2 → M-1 → M-4 → M-6 → M-3 → M-5 → M-7 → M-8 → C-4 → minor。C-4（§3.4 再配置 Option 2 採用の場合）は main.tex input 順序変更を伴うため，他修正完了後の clean rebuild の安全性確保 tier。
- **Option 選択（C-4）**: Option 3（gloss box 追加）を第一推奨。理由：（1）§3.4 の SP-B / SP-E 参照が §3 末尾で維持される，（2）main.tex 変更不要，（3）§3 narrative の完結感を損なわない。Option 2 は post-CHK-195 で別途議論。
- **Commit 単位**: Critical + Major → 1 commit（`fix: §1-§3 peer-review CHK-196 C-1..C-4 + M-1..M-8`）；minor → 1 commit（`fix: §1-§3 style polish CHK-196 m-1..m-7`）。
- **clean xelatex build 確認**: 全修正後に `\textbf` count before/after をメトリクス記録。
- **推定時間**: Critical 全件 + Major 80% = 3–4 時間。minor time-box 30 分。合計 1 CHK = 4–5 時間。

### 7.5 実装後検証

- **narrative grade 再評価**: CHK-194 で self-rated A+（内部視点）→ 外部 peer-review grade A+ / A++ に昇格見込み。
- **SP-I / SP-J 投稿ゲート**: Critical 全件解消 → §1–§3 submission ready。§4–§10 peer-review（別 CHK）の完遂後に Full manuscript submit。
- **逆戻りリスク**: 低。既存 narrative の圧縮・cite 追加が主で，技術的主張は変更しない。

---

**Reviewer Note（2026-04-24, CHK-195）**: 本メモは外部査読者視点を模して作成したが，著者（本稿開発者）の設計意図を十分に考慮している。本稿の CCD + CLS + 分相 PPE + DC + HFE の統合設計は学術的貢献として明確で，上記 Critical/Major を解消すれば SP-I / SP-J レベルの査読ゲート通過が十分見込まれる。次 CHK でこの Fix Plan を segment 単位で実装することを推奨する。

— End of Peer Review (2026-04-24, CHK-195) —
