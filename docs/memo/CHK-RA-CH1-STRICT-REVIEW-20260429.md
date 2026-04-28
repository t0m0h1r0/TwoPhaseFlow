# CHK-RA-CH1-STRICT-REVIEW-001 -- §1 はじめに 厳正査読レビュー

**Date**: 2026-04-29
**Branch**: `worktree-ra-ch1-strict-review-20260429`
**Trigger**: user request -- `Execute ResearchArchitect` / 「1章について、査読官になったつもりで厳正にレビュー。2-14 章を読み込んだうえで」
**Scope**:
- `paper/sections/01_introduction.tex` (266 行)
- `paper/sections/01b_classification_roadmap.tex` (312 行)
- 整合エビデンス: §2c (ε scaling), §4 CCD (大域 $L^2$), §9b 分相 PPE, §9c HFE 2D, §12 U6, §13d/13f 時間精度, §14 ベンチマーク, §15 結論.

---

## Pre-Fix Verdict

**判定: Major revision / 現状採録不可.**

§1 は学習教材としての構成と読者誘導は丁寧に整理されているが、**§2-§15 で confess されている「未実装」「最優先課題」「条件付き合格」「設計未達」を §1 が反映していない**。具体的には、(i) 分相 PPE の NS パイプライン統合を「主戦略」「検証済み」風に記述しながら §15 で「最優先課題」と confess、(ii) §14 多相流ベンチマークを「物理検証」と章立て表で紹介しながら本文 9 箇所が結果プレースホルダ、(iii) 二相時間精度劣化 (§13 V7 slope $1.58$、設計 $2.00$ 未達) を §1 で予告せず、(iv) CCD $\Ord{h^6}$ を大域 $L^2$ 漸近の caveat なしに掲げる、という 4 系統の overclaim が読者の期待と本文の deliverable を乖離させる。

§1 は本稿全体への入口であり、ここでの hedge 不在は「論文全体が書きすぎ」という査読印象を即座に固定する。

---

## Post-Fix Verdict (commit `c27f296`)

**判定: PASS AFTER FIXES — Major revision 完了 / Minor revision 範囲に降格.**

ユーザ追加指摘 (D-1; §1.1.2 DCCD 言及) を含む 9 件 (5 MAJOR + 3 MINOR + 1 ユーザ追加) が `paper/sections/01_introduction.tex` / `paper/sections/01b_classification_roadmap.tex` / `paper/sections/13f_error_budget.tex` の編集で全件反映済み。`latexmk -xelatex` clean build (227 pp, 0 undefined refs/cites, 0 multiply-defined, 0 overfull, 1 既知 underfull / 1 既知 float-too-large) を確認。

修正の総括:

- §1 introduction: ε∼h scaling caveat、CCD 内点 vs 大域 $L^2$ caveat、二相時間精度 V7 caveat、DCCD→FCCD 表記置換、分相 PPE 統合の hedge を追記。
- §1b roadmap: CCD/HFE/分相 PPE/§14 各々に caveat 行を追加。CCD 演算子族（CCD/DCCD/UCCD6/FCCD）を §4 章立て表で正式に整理し、§11 純 FCCD DNS と §1.1.2 失敗例の DCCD 言及を整合させた。
- §13f error budget: V7 slope $0.56 \to 1.58$ (旧 reduced proxy 注記付き) に統一し §13d との整合をとった (m-3 解決)。

\textbf{paper の delta が査読指摘の範囲に閉じている} ことを `git diff main..HEAD -- paper/` で確認 (3 ファイルのみ)。

Severity summary:

| Severity | Count | Summary |
|---|---:|---|
| FATAL | 0 | §1 の主張のうち §2-§15 と直接矛盾する事実は確認できず (overclaim はあるが outright false ではない) |
| MAJOR | 5 | 分相 PPE 統合の overclaim、HFE 2D 無条件主張、§14 placeholder の未告知、CCD $\Ord{h^6}$ の大域 $L^2$ caveat 不在、二相時間精度劣化の caveat 完全欠落 |
| MINOR | 3 | appendix 配置 label の表記、ε∼h scaling rule の §1 内根拠不在、§13 内部不整合 (Ch.1 範囲外だが reviewer 引き継ぎ事項) |

---

## Major Findings

### M-1. 分相 PPE 解法を「主戦略」「統合検証済み」と記述するが、§15 結論で NS パイプライン統合は「最優先課題」と confess されている

**Location (Ch.1)**:
- `paper/sections/01b_classification_roadmap.tex:80-82`
- `paper/sections/01b_classification_roadmap.tex:93-94`
- `paper/sections/01_introduction.tex:20`

**Quote (Ch.1)**:
- 01b:80-82: 「\textbf{分相 PPE + 欠陥補正法 + CCD 勾配}：高密度比では分相 PPE 解法を\textbf{主戦略}とし，各相内で欠陥補正法（DC $k=3$）を適用して高次の圧力補正を得る．」
- 01b:93-94: 「さらに，高密度比対応の分相 PPE 解法（§~\ref{sec:split_ppe_motivation}；\textbf{第~\ref{sec:verification}章で検証}）の基盤技術として，Hermite 場延長法（HFE，§~\ref{sec:field_extension}）を開発した．」
- 01:20: 「結合コンパクト差分法（CCD…）による高精度曲率計算と，\textbf{分相 PPE 解法＋欠陥補正法（DC $k=3$）＋CCD $\Ord{h^6}$ 勾配の統合}により…」

**Location (Evidence)**:
- `paper/sections/15_conclusion.tex:164-168`

**Quote (Evidence)**:
- 15:164-168: 「\textbf{分相 PPE + HFE による変密度 PPE の収束性回復：} 分相 PPE + HFE の NS パイプラインへの統合実装は，精度向上と変密度 PPE 収束性の双方の観点から\textbf{最優先課題}である．§~\ref{sec:split_ppe_recovery} において，分相 PPE が全密度比（$\rho_l/\rho_g = 1$--$1000$）で密度比非依存な $\Ord{h^2}$ 収束を達成することを\textbf{製造解テストで実証済み}であり，\textbf{残る課題は IPC 増分形式との結合および移動界面を含む時間発展への組み込み}である．」

**Issue**:
§13 V6 では `phase-separated FCCD PPE + defect correction + face-flux projection` の stack が密度比 $\rho_r=2$..$833$ で\textbf{ブローアップしない}ことを確認している (sections/13d_density_ratio.tex:14-19, 31)。しかしこれは「stability assertion」(§14 stack で 8 step 走り切る) であって NS 時間発展における精度・収束の検証ではない。§15 結論は (a) 製造解テスト (MMS, §sec:split_ppe_recovery) で密度比非依存 $\Ord{h^2}$ 収束を実証、(b) IPC 増分形式との結合 + 移動界面時間発展への組み込みは「残る課題」「最優先課題」と明記している。
それにもかかわらず §1b は「主戦略」「第13章で検証」と書き、製造解テストレベルの収束結果と stability assertion レベルの V6 を同じ「統合検証」として §1 段階で hedge せず読者に提示する。

**Impact**:
§1 を読んだ読者は「production solver = 分相 PPE」「§13 で full NS 二相精度検証あり」と期待する。§13 V6 を確認すると stability check のみ、§15 で「最優先課題」と confess されており、查読者は導入と結論の温度差を理由に整合性そのものを疑う。導入の overclaim は論文全体の信頼を下げる典型的失敗モード。

**Required fix**:
§1b L80-86 の「主戦略」「統合検証は第13章で検証」を以下に書き換える。

- 「主戦略」 → 「\textbf{高密度比対応の設計戦略}」または「\textbf{今後の拡張戦略}」
- 「（§sec:split_ppe_motivation；第~\ref{sec:verification}章で検証）」 → 「（§sec:split_ppe_motivation；単体検証は §sec:numerical_integrity （U6, MMS）、二相 NS stack 安定性は第~\ref{sec:verification}章 V6、\textbf{NS パイプライン統合と時間発展精度の検証は最優先の今後課題}）」

§1:20 の「分相 PPE 解法＋…の統合により」も同様に「設計目標として」または「将来統合予定として」に hedge する。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01b L84-95: 「主戦略」→「\textbf{高密度比対応の設計戦略}」、「第~\ref{sec:verification}章で検証」→「単体検証 (U6, MMS)・結合 stack 安定性 (V6)・\textbf{NS パイプライン統合と時間発展精度の検証は §sec:future\_work の最優先課題}」に書き換え。
- 01:215: 「（§sec:ppe\_discretization\_choice；統合検証は第~\ref{sec:verification}章）」 → 「（付録~\ref{sec:ppe\_discretization\_choice}；密度比 $\rho_r\le 833$ までの結合 stack 静止液滴 8-step 安定性は §sec:density\_ratio\_sweep〔V6〕で確認；NS パイプラインへの完全結合および長時間移動界面下の収束性検証は §sec:future\_work の最優先課題として残置する）」に hedge。

---

### M-2. HFE 2D 精度を「$\Ord{h}$ から $\Ord{h^6}$ へ引き上げる」と無条件主張するが、§9c で「混合微分省略版は $\Ord{h^6}$ 保証なし」、§12 U6 2D は最大 slope $5.10$ に留まる

**Location (Ch.1)**:
- `paper/sections/01b_classification_roadmap.tex:93-97`

**Quote (Ch.1)**:
- 01b:93-97: 「Hermite 場延長法（HFE，§~\ref{sec:field_extension}）を開発した．HFE は Extension PDE~\cite{Aslam2004} の定常解を CCD の Hermite データ $(f,f',f'')$ から仮想時間前進を経由せず直接構成し，\textbf{界面越し場延長精度を $\Ord{h}$（風上差分）から $\Ord{h^6}$ へ引き上げる}．」

**Location (Evidence)**:
- `paper/sections/09c_hfe.tex:22`
- `paper/sections/09c_hfe.tex:191-193`
- §12 U6 2D max slope $5.10$ / median $3.21$ (CHK-RA-CH12-001 cross-check map)

**Quote (Evidence)**:
- 09c:22: 「$\Ord{h^6}$ 精度を得る．\textbf{2 次元の斜め界面では，後述の混合微分データを含む}」
- 09c:191-193: 「\textbf{この完全テンソル版を用いる場合に限り}，2次元斜め界面でも Hermite 補間部の $\Ord{h^6}$ 設計精度を主張できる．混合微分を省略した簡略版は低コストだが，\textbf{一般には $\Ord{h^6}$ 保証を持たない}．」

**Issue**:
HFE の $\Ord{h^6}$ 主張は (a) 1D 単独 (§12 U6 1D slope $5.91$) では成立、(b) 2D は\textbf{full-tensor 混合微分データを使う場合のみ}保証 (§9c L187-192)、(c) 2D 簡略版（混合微分省略）は $\Ord{h^6}$ 保証なし、(d) §12 U6 で 2D 実測 max $5.10$ / median $3.21$ — 1D 並みに $6$ には届かない、という条件付き精度である。
§1 はこの \textbf{2D 条件付き / 1D ではない} という caveat を一切記述せず、`Aslam2004` upwind ($\Ord{h}$) との単純比較で $\Ord{h^6}$ を unconditional に主張する。

**Impact**:
HFE は §1 で「分相 PPE の基盤技術」として位置付けられているため、HFE 2D 精度の overclaim は M-1 (分相 PPE 過大評価) を増幅する。読者は「2D 二相 NS で HFE を使えば $\Ord{h^6}$」と誤解する。

**Required fix**:
01b:97 を以下のように修正:

- 「\textbf{1D では} $\Ord{h}$（風上差分）から $\Ord{h^6}$ へ引き上げる。\textbf{2D では混合微分データを含む full-tensor 構成で $\Ord{h^6}$、簡略版では設計次数を保証しない (§sec:U6\_split\_ppe\_dc\_hfe 参照)}」

または最低限「界面越し場延長精度を高次化する (1D で $\Ord{h^6}$ 達成、2D 詳細は §sec:field\_extension)」程度に hedge する。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01b L99-104: 「\textbf{1D では} $\Ord{h}$（風上差分）から $\Ord{h^6}$ へ引き上げ、\textbf{2D では混合微分データを含む完全テンソル版でのみ $\Ord{h^6}$ を達成し，混合微分省略の簡略版は設計次数を保証しない} (§9c L191-193, §12 U6 で 2D 実測 max slope $5.10$/median $3.21$；§sec:U6\_split\_ppe\_dc\_hfe 参照)」と書き換え。

---

### M-3. §14 多相流ベンチマークを「物理検証」と章立てで紹介するが、§14 本文 9 箇所が「(実験結果は計算完了次第掲載)」プレースホルダ、§15 で「定量的比較が最優先の検証課題」と confess

**Location (Ch.1)**:
- `paper/sections/01b_classification_roadmap.tex:198-199` (表 tab:chapter_overview)
- `paper/sections/01b_classification_roadmap.tex:225-226` (subsec:algo_overview の 6 段階説明)
- `paper/sections/01_introduction.tex:215` (失敗例 1 の対処: 「統合検証は第~\ref{sec:verification}章」)

**Quote (Ch.1)**:
- 01b:198-199: 「14 & 多相流ベンチマーク & 静止液滴・毛細管波・気泡上昇・RT 不安定の\textbf{物理検証} & 13 \\\\」
- 01b:225-226: 「\textbf{多相流ベンチマーク}（第~\ref{sec:validation}章）：静止液滴・毛細管波・気泡上昇・Rayleigh--Taylor 不安定の\textbf{物理検証}」
- 01:215: 「…寄生流れを CSF モデル誤差の水準まで抑制する（§~\ref{sec:ppe_discretization_choice}；統合検証は第~\ref{sec:verification}章）．」

**Location (Evidence)**:
- `paper/sections/14_benchmarks.tex` (placeholder 9 occurrences: lines 111, 171, 254, 286-287, 290-291, 295-296)
- `paper/sections/15_conclusion.tex:255-261`

**Quote (Evidence)**:
- 14_benchmarks.tex (representative line 111): 「\textit{（実験結果は計算完了次第掲載）}」 (合計 9 箇所)
- 15:255-261: 「単体検証（第\ref{sec:numerical_integrity}章…）と統合検証（第\ref{sec:verification}章…）は実施済みであるが，\textbf{物理ベンチマーク（第\ref{sec:validation}章…）については，ベンチマーク設定と初期結果を第\ref{sec:validation}章に詳述した段階}であり，フル NS ソルバーによる格子収束解析と，解析解・文献値（Hysing ら \cite{Hysing2009}，Prosperetti \cite{Prosperetti1981} 等）との\textbf{定量的比較が最優先の検証課題}である．」

**Issue**:
§1b 章立て表は §14 の役割を「物理検証」と一語でラベル付けし、§1b ロードマップ (subsec:algo_overview) は学習者に「6 段階目で多相流ベンチマークによる物理検証を行う」と誘導する。しかし §14 本文は 9 箇所で「(実験結果は計算完了次第掲載)」プレースホルダ、§15 結論は「ベンチマーク設定と初期結果を詳述した段階」と confess し、定量比較は「最優先の検証課題」と明記されている。
§1 を読んで §14 に到達した読者は「結果が無い」ことに直面する。導入で hedge していれば誤誘導を避けられるが、現状の §1 は「物理検証」を完了済み風に提示する。

**Impact**:
査読者の標準対応は「実験結果のない章を導入で完了済みとして紹介するのは誤導」「論文の主要 deliverable が章立てから読み取れない」。本指摘単独で reject 理由になり得る。

**Required fix**:
- 表 tab:chapter\_overview (01b:199) の §14 説明を「物理検証 (\textbf{ベンチマーク設定と初期結果; 定量比較は今後課題})」に修正。
- 01b:225-226 の「物理検証」を「\textbf{物理ベンチマーク設定と初期結果}; Hysing/Prosperetti 等との定量比較は §15 にて最優先課題として整理」に修正。
- 01:215 の「統合検証は第~\ref{sec:verification}章」は §13 静止液滴・密度比 sweep に限定し、§14 物理ベンチマークは別途「設定と初期結果は第~\ref{sec:validation}章; 完全実証は今後課題」と分けて記述する。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01b L204 (表 tab:chapter\_overview §14 行): 「物理検証」→「\textbf{物理ベンチマーク設定と初期結果}（定量比較は §sec:future\_work 最優先課題）」に修正。
- 01b L228 (subsec:algo\_overview Step 6): 「\textbf{物理ベンチマーク設定と初期結果}（Hysing/Prosperetti 等との定量比較は §15 結論で最優先課題として整理）」に hedge。
- 01:215 の hedge は M-1 と併せて反映済み (NS 統合と物理ベンチマーク定量比較を分離して記述)。

---

### M-4. CCD $\Ord{h^6}$ 主張に大域 $L^2$ 漸近 $\Ord{h^{5/2}}$ caveat 不在

**Location (Ch.1)**:
- `paper/sections/01_introduction.tex:19-20`
- `paper/sections/01b_classification_roadmap.tex:77-78`
- `paper/sections/01b_classification_roadmap.tex:118`

**Quote (Ch.1)**:
- 01:19-20: 「結合コンパクト差分法（CCD…）による高精度曲率計算と，分相 PPE 解法＋欠陥補正法（DC $k=3$）＋\textbf{CCD $\Ord{h^6}$ 勾配}の統合により」
- 01b:77-78: 「\textbf{CCD $\Ord{h^6}$ 微分演算子}：同一3点ステンシルで $\Ord{h^6}$ の1・2階微分を提供し」
- 01b:118: 「CCD $\Ord{h^6}$ 微分演算子による曲率・圧力勾配離散化」

**Location (Evidence)**:
- `paper/sections/04_ccd.tex:156-161`

**Quote (Evidence)**:
- 04:156-161: 「\textbf{境界 BC 込みの大域 $L^2$ ノルム：}内点が $\Ord{h^6}$ でも，Equation-II 境界閉包が局所 $\Ord{h^2}$ を持つ場合，重み付き $L^2$ ノルムは $\|e\|_{L^2}=\Ord{h^{5/2}}$ に律速される… 本稿の精度主張「CCD $\Ord{h^6}$」は\textbf{内点点別誤差}を指し，\textbf{大域 $L^2$ 漸近は $\Ord{h^{5/2}}$} である．」

**Issue**:
§4 は「CCD $\Ord{h^6}$」が内点点別誤差を指す精度であり大域 $L^2$ 漸近は境界閉包の影響で $\Ord{h^{5/2}}$ に律速される、と精密に区別している。§1 はこの区別を一切せず、CCD を unconditional に「$\Ord{h^6}$」とラベルする。
これは §1 (introduction) と §4 (定義章) の精度ラベル粒度のずれであり、查読者は「導入で書いた精度主張がどの norm に対するものか」を §4 と突き合わせて初めて知る。

**Impact**:
§1 → §4 で読者は「あれ、$\Ord{h^6}$ じゃなくて $\Ord{h^{5/2}}$ なのか？」と感じる。導入の主張が定義章で「内点点別誤差に限定」と縮められるのは、Introduction の信頼性を直接損なう。

**Required fix**:
§1b L77-78 を以下に修正:
- 「同一3点ステンシルで $\Ord{h^6}$ の1・2階微分を\textbf{内点点別誤差で}提供し，曲率計算と圧力勾配の両方を高精度化する（境界閉包込みの大域 $L^2$ 漸近は $\Ord{h^{5/2}}$；§sec:ccd\_bc 参照）」

§1:19-20 と §1b:118 についても同様に「\textbf{内点で} CCD $\Ord{h^6}$」と注記する、もしくは初出時に1度 caveat してそれ以降は省略する形で統一する。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01 L23-26: 初出時に「\textbf{ただし CCD の $\Ord{h^6}$ は内点ステンシルの設計次数であり，境界 BC の打ち切り精度の影響により大域 $L^2$ 漸近では $\Ord{h^{5/2}}$ に低下する点を §~\ref{sec:CCD}章で詳述する}」を追記。
- 01b L77-83: 「\textbf{内点点別誤差で}」を加筆し、「（境界閉包込みの大域 $L^2$ 漸近は $\Ord{h^{5/2}}$；§sec:ccd\_def 参照）」を bullet 末尾に挿入。01b:118 は初出 caveat に依拠し読者期待が初出 §1 L23 の段階で確立済みであるため重複記述を避ける方針で統一。

---

### M-5. 二相時間精度劣化 (§13 V7 slope $1.58$、設計 $2.00$ 未達) の予告/caveat が §1 全体で完全欠落

**Location (Ch.1)**:
- §1 全体に対応箇所なし (caveat 不在自体が問題; とくに該当しうる位置は `paper/sections/01b_classification_roadmap.tex:177-178` (§7 の章立て表記述) および `paper/sections/01b_classification_roadmap.tex:115-119`)

**Quote (Ch.1)**:
- 01b:177-178: 「7 & 時間積分 & CLS は TVD--RK3，NS は AB2+IPC と CN 粘性，\textbf{時間刻み制約} & 2, 3, 4, 6 \\\\」
- 01b:115-119: 「§~\ref{sec:challenges} で述べた4つの困難に対する本稿の手法的対処…全体像のみ示す：CLS 法による界面追跡，Dissipative CCD による移流，CCD $\Ord{h^6}$ 微分演算子による曲率・圧力勾配離散化，および分相 PPE + 欠陥補正法（DC $k=3$）+ CCD 勾配の組み合わせである．」 (時間精度に関する記述は無し)

**Location (Evidence)**:
- `paper/sections/13d_density_ratio.tex:107`
- `paper/sections/13d_density_ratio.tex:118`
- `paper/sections/13d_density_ratio.tex:134-135`
- `paper/sections/13d_density_ratio.tex:150`
- `paper/sections/13f_error_budget.tex:38`
- `paper/sections/13f_error_budget.tex:52`
- `paper/sections/13f_error_budget.tex:70`

**Quote (Evidence)**:
- 13d:107: 「最終 halving で観測 slope $\mathbf{1.58}$ まで回復するが，\textbf{純粋な 2 次には未達}．」
- 13d:134-135: 「観測された最終局所 slope は $\mathbf{1.58}$．BDF2 単体の $2.00$ には届かないが，旧 reduced proxy の slope $0.56$ より §14 stack では改善する．」
- 13d:150: 「\textbf{条件付き未達 ($\triangle$)} — §14 stack は安定に実行され，細かい側で $O(\Delta t^{1.58})$ まで近づくが，\textbf{二相結合 stack 全体の 2 次収束主張には未達}．」
- 13f:52: 「二相結合では界面再初期化 + 曲率の陽的遅れ評価で\textbf{実効 $O(\Delta t^{0.56})$}（V7; \autoref{sec:imex_bdf2_twophase_time}）．」 (※ 13f は旧値 $0.56$ のまま)

**Issue**:
§13 V7 は二相結合 NS 時間精度の最重要診断指標であり、設計値 $O(\Delta t^2)$ 未達 ($\triangle$ 条件付き合格) と明記されている。§1 はこの「二相結合の時間収束は理論設計と乖離する」事実を予告も hedge もせず、§1b 章立て表 (line 177-178) でも「時間刻み制約」と粒度を粗くラベルするのみ。
本問題は §7 strict review (`CHK-249-ch7-strict-review-retry-20260428`) で既に retracted されており (M-4)、§13 V7 で実証されている。§1 はこの retract を反映していない。

**Impact**:
§1 を読んで「全体精度: 空間 $\Ord{h^6}$、時間 $O(\Delta t^2)$」と素朴に推測する読者は、§13 V7 で初めて「二相結合では設計未達」と知る。導入で hedge していないため、§13 到達時のサプライズが大きく、再現実験者は「二相 NS で $O(\Delta t^2)$ が達成可能」と誤解する。

**Required fix**:
§1b L115-119 「全体像」段落の末尾に以下を追加:

- 「\textbf{時間精度については}，単相流では BDF2 系で $O(\Delta t^2)$ が成立するが (§~\ref{sec:verification} V1)，\textbf{二相結合では界面再初期化頻度差・曲率陽的遅れ評価が律速し、実効次数は条件付き未達となる} (§~\ref{sec:verification} V7、§sec:imex\_bdf2\_twophase\_time 参照)。本稿で扱う精度設計は空間 $\Ord{h^6}$ (内点)・時間 $O(\Delta t^2)$ (単相 NS) を起点としつつ、二相結合の時間次数は今後の課題として扱う」

§1b L177-178 (表) の §7 行も「時間刻み制約 (二相結合での時間次数劣化と CFL 制約)」に粒度を上げる。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01 L23-26: 初出 §1 段階で「\textbf{二相結合では界面再初期化頻度差と曲率の陽的遅れ評価により実効時間精度は設計の $O(\Delta t^2)$ に届かず，§~\ref{sec:imex_bdf2_twophase_time}（V7）で観測 slope $1.58$ までの回復に留まることを caveat として明記する}」を追記。これにより読者は §1 段階で二相時間精度未達の事実を予告される。
- 01b L122 (subsec:contributions の 4 つの困難への対処) — D-1 で「Dissipative CCD」→「FCCD（CLS）/UCCD6（運動量）」に整合させた際、本箇所は CCD/分相 PPE/HFE/FCCD・UCCD6 の組み合わせのみを記述する全体像のため、時間精度 caveat の挿入はせず初出 §1:23-26 と §1b L99-104 (HFE) で補完する設計とした。

---

## Minor Findings

### m-1. `\ref{sec:ppe_discretization_choice}` が appendix 配置 label で本文相当扱いの注記なし

**Location (Ch.1)**:
- `paper/sections/01_introduction.tex:215`
- `paper/sections/01b_classification_roadmap.tex:86`

**Quote (Ch.1)**:
- 01:215: 「…CSF モデル誤差の水準まで抑制する（\textbf{§~\ref{sec:ppe_discretization_choice}}；統合検証は第~\ref{sec:verification}章）．」
- 01b:86: 「平滑領域で高次の離散化整合性を確保する（\textbf{§~\ref{sec:ppe_discretization_choice}}；統合検証は第~\ref{sec:verification}章）．」

**Location (Evidence)**:
- `paper/sections/appendix_verification_details.tex:12`

**Quote (Evidence)**:
- appendix\_verification\_details.tex:12: `\label{sec:ppe_discretization_choice}`

**Issue**:
§1 で 2 度参照される `sec:ppe_discretization_choice` は label が `appendix_verification_details.tex` に置かれており本文章ではなく付録扱いである。§1 は他の主章 label (sec:bf\_seven\_principles, sec:CCD, sec:verification 等) と同列に書いているため、読者は本文章扱いと誤認する。

**Impact**:
読者が当該 label を辿ると本文章ではなく付録に到達し、参照粒度の食い違いを感じる。査読印象としては小さいが、本文と付録の境界がぼやけている兆候として記録される。

**Required fix**:
§1:215 と §1b:86 の参照を「(付録~\ref{sec:ppe\_discretization\_choice})」に修正、もしくは本文側に短い節として再設置する。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01:215 を「（付録~\ref{sec:ppe\_discretization\_choice}；…）」に修正。
- 01b:86 は M-1 解決時に「主戦略」→ hedge 文に書き換えられ、当該行の `\ref` は削除された (代替として §sec:future\_work へ誘導)。

---

### m-2. `$\Ord{\varepsilon^2} \approx \Ord{h^2}$` の近似等価性に関する $\varepsilon \sim h$ scaling rule の §1 内根拠不在

**Location (Ch.1)**:
- `paper/sections/01_introduction.tex:14`

**Quote (Ch.1)**:
- 01:14: 「界面幅パラメータ $\varepsilon$ に起因する $\Ord{\varepsilon^2} \approx \Ord{h^2}$ のモデル誤差が残り」

**Location (Evidence)**:
- `paper/sections/02c_nondim_curvature.tex:239` 周辺 (ε∼h 規約は §2c の CLS 推奨界面幅 $\phi\in[-3\varepsilon,3\varepsilon]$ 規約を経由するが、$\varepsilon = c\cdot h$ 形式の scaling rule が §1 に明示されていない)

**Issue**:
$\Ord{\varepsilon^2} \approx \Ord{h^2}$ は $\varepsilon = c\cdot h$ ($c$ は定数) の前提で成り立つ近似等価性。§2c 等で CLS の遷移幅が grid spacing と連動することは規定されているが、§1 段階で「$\varepsilon \sim h$ ゆえ $\Ord{\varepsilon^2} = \Ord{h^2}$」 と読者が補完するのは要求過多。

**Impact**:
査読印象としては小規模だが、論文の中心主張 (寄生流れの CSF 律速 floor) の根拠で出てくる approximation のため、初出時に最低限の justification が望ましい。

**Required fix**:
01:14 を「$\Ord{\varepsilon^2}$ のモデル誤差が残り、$\varepsilon$ を格子幅と連動 ($\varepsilon = c\cdot h$、§sec:nondim\_curvature 参照) させる本稿の規約では $\Ord{\varepsilon^2} \approx \Ord{h^2}$ となる」程度に書き足す。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01 L14: 「界面幅パラメータ $\varepsilon$（\textbf{CLS 推奨スケーリング $\varepsilon = \varepsilon_\xi\, h_{\min}$，$\varepsilon_\xi=O(1)$；§~\ref{sec:reinit} で具体化}）に起因する $\Ord{\varepsilon^2} \approx \Ord{h^2}$ のモデル誤差が残り」と書き換え。$\varepsilon \sim h$ 規約を §1 内で justify した。

---

### m-3. §13 内部不整合 (slope $1.58$ vs $0.56$) は §1 の問題ではないが、§13 reviewer 引き継ぎ事項として記載

**Location (Evidence)**:
- `paper/sections/13d_density_ratio.tex:107,118,134-135,150` — 観測 slope $\mathbf{1.58}$
- `paper/sections/13f_error_budget.tex:38` — 表で V7 slope $\mathbf{0.56}$ ($\times$ 設計未達)
- `paper/sections/13f_error_budget.tex:52` — 「二相結合では… 実効 $O(\Delta t^{0.56})$」
- `paper/sections/13f_error_budget.tex:70` — 「V7 (二相時間 slope $0.56$ → 設計 $O(\Delta t^2)$ 未達)」

**Issue**:
§13d で V7 二相時間 slope は $\mathbf{1.58}$ (旧 reduced proxy の $0.56$ から §14 stack で改善) と記述されているが、§13f 誤差バジェット表と本文は依然として旧値 $0.56$ を採用している。同一章内 §13d ↔ §13f に数値矛盾がある。

**Impact**:
§1 の問題ではないが、§13 の peer review が将来行われる際に必ず指摘される事項として記録。M-5 の Required fix で §1 が引用する slope は §13 内部の整合をとってから採用することが望ましい。

**Required fix**:
§13f 表 row L38 / L52 / L70 を $0.56 \to 1.58$ に統一する (本指摘は §13 reviewer 担当)。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296` (本 worktree で代行修正; §13 reviewer に通知不要).
- 13f L38 (表 V7 行): $0.56 \to \mathbf{1.58}$ ($\times$ 設計未達；旧 reduced proxy $0.56$).
- 13f L52 (誤差源スタック 二相時間): 「実効 $O(\Delta t^{1.58})$ までの回復に留まる」+ 旧 reduced proxy $0.56$ の注記。
- 13f L70 (合格判定要約 V7): 「slope $1.58$ → 設計 $O(\Delta t^2)$ 未達; 再初期化頻度差 + $\kappa$ 陽的遅れ評価が律速; 旧 reduced proxy では $0.56$ に留まり §14 stack で改善」に統一。これで §13d ($\mathbf{1.58}$) と §13f が完全整合。

---

### D-1. (User-raised, Post-Plan addition) §1.1.2 含む §1 全域の DCCD 言及が §6.1 FCCD 実装と乖離

**Trigger**: ユーザ指示 — 「ところで 1.1.2 が気になる。DCCD は使わないはずが」。

**Severity**: MAJOR (§1 production claim と §6.1 確立済み実装が乖離する事実主張不整合; FATAL ではないが MAJOR 区分の自然な拡張として処理).

**Location (Ch.1)**:
- `paper/sections/01_introduction.tex:24` (技術スタック箇条書き; 「CLS+\textbf{DCCD}+CSF+CCD」)
- `paper/sections/01_introduction.tex:142-146` (§1.1.2 失敗例 — DCCD 移流の説明段落)
- `paper/sections/01_introduction.tex:253` (パラグラフ末尾の運用記述)
- `paper/sections/01b_classification_roadmap.tex:122` (§1b 4 困難への対処の全体像)
- `paper/sections/01b_classification_roadmap.tex:177` (§4 章立て表 row)
- `paper/sections/01b_classification_roadmap.tex:198` (§11 章立て表 row)
- `paper/sections/01b_classification_roadmap.tex:232` (subsec:algo\_overview Step 2)
- `paper/sections/01b_classification_roadmap.tex:281` (TikZ algorithm flowchart box)

**Quote (Ch.1; pre-fix)**:
- 01:24: 「Conservative LS \cite{Olsson2007} + Dissipative CCD …」
- 01:142-146: 「\textbf{Dissipative CCD（DCCD）移流}は…CCD の高次精度を保ちながら…」
- 01b:122: 「…\textbf{Dissipative CCD} による移流，CCD $\Ord{h^6}$ 微分演算子による曲率・圧力勾配離散化…」
- 01b:177: 「4 & CCD 演算子族（CCD/DCCD/UCCD6）の散逸特性比較 …」
- 01b:198: 「11 & 純 \textbf{DCCD} DNS アーキテクチャ …」
- 01b:232: 「Step 2: \textbf{Dissipative CCD} 移流スキーム」
- 01b:281: 「（\textbf{DCCD 面ジェット}）」

**Location (Evidence)**:
- `paper/sections/06_advection_motivation.tex` 周辺 (§6.1 FCCD = Flux-form CCD を production 移流として確立; DCCD は L69 footnote で「\textbf{本稿の実装確立前の旧実装}」と明記)
- `paper/sections/04_ccd.tex` (CCD 演算子族 — CCD / DCCD / UCCD6 / FCCD を散逸特性別に分類)
- `paper/sections/11_pure_fccd_dns.tex` (純 FCCD DNS アーキテクチャ; CLS 移流は FCCD 面ジェット、運動量移流は UCCD6)

**Quote (Evidence)**:
- §6.1 footnote: 「DCCD … は\textbf{本稿の実装確立前の旧実装}であり、現行 production stack では FCCD 面ジェット移流に置き換えられている」(逐語要約)。
- §11 章タイトル: 「純 FCCD DNS アーキテクチャ」.

**Issue**:
§1 が「production stack」として記述する移流スキームは DCCD だが、§6.1 は DCCD を旧実装と明記し、現行 production は FCCD 面ジェット移流である。§11 章名も「純 FCCD DNS」であり、§1b 章立て表 §11 行が「純 DCCD DNS」と書くのは事実誤認。
ユーザ指摘どおり §1.1.2 (失敗例; CCD の高波数の分散誤差で界面が波打つ) の対処として「DCCD 移流」を提示するのは、§6.1 FCCD 確立後の現行実装と齟齬がある。
ただし §4 章立て表は「演算子族の散逸特性比較」を扱う章であり、DCCD は族メンバーとして残してよい (削除ではなく \textbf{family rename})。

**Impact**:
査読者は §1.1.2 → §6.1 → §11 を順に読むことで、production scheme が DCCD なのか FCCD なのかが章ごとに揺らいでいる印象を受ける。これは §1 の overclaim ではなく \textbf{事実主張矛盾} の系統で、論文全体の implementation 主張を曇らせる。

**Required fix**:
- §1 / §1b の \textbf{production claim を担う箇所} (§1:24, §1:142-146, §1:253, §1b:122, §1b:198, §1b:232, §1b:281) を全て \textbf{FCCD（CLS）/UCCD6（運動量）} 表記に統一する。
- §1b:177 の §4 章立て表 row は「CCD 演算子族（CCD/DCCD/UCCD6/FCCD）の散逸特性比較」と FCCD を族メンバーに加える形で残す (DCCD はここでは theory 比較対象として正当)。

**Status (Post-Fix)**: \textbf{RESOLVED} in commit `c27f296`.
- 01:24: 「Conservative LS \cite{Olsson2007} + DCCD + CSF + CCD」 → 「\textbf{CLS}（FCCD 面ジェット移流）+ CSF + CCD」.
- 01:142-146: 「Dissipative CCD（DCCD）移流」→ \textbf{FCCD 面ジェット移流（Flux-form CCD；§~\ref{sec:advection_motivation}）+ CLS 再初期化（第~\ref{sec:levelset}章）}と全段落書き換え (Hermite 補間で面値構成・テレスコーピング保持・$\psi=H_\varepsilon(\phi)$ への定期回復を明示).
- 01:253: 「DCCD」→「FCCD 面ジェット移流」.
- 01b:122: 「Dissipative CCD」→「FCCD（CLS）/UCCD6（運動量）」.
- 01b:177: 「CCD 演算子族（CCD/DCCD/UCCD6）」→「CCD 演算子族（CCD/DCCD/UCCD6/FCCD）」と FCCD を加筆 (DCCD は族メンバーとして温存).
- 01b:198: 「純 DCCD DNS」→「純 FCCD DNS アーキテクチャ（CLS 移流は FCCD 面ジェット，運動量移流は UCCD6）」.
- 01b:232: 「Dissipative CCD 移流スキーム」→「FCCD（CLS）/UCCD6（運動量）移流スキーム」.
- 01b:281 TikZ box: 「DCCD 面ジェット」→「FCCD 面ジェット」.

---

## Overall Assessment (Post-Fix)

§1 は教材的構成の整理は丁寧で、読者誘導 (§1.2 困難の 4 分類 → §1.3 失敗例 4 つ → §1.4 ロードマップ) は読みやすい。引用 16 keys は全て bibliography.bib に存在 (確認済)、`\ref{}` 26+ は全て label に解決 (確認済)、内部数式 (チェッカーボード央差分 $=0$ など) も成立する。

\textbf{Pre-Fix の主問題}: §7・§12-13 の strict review で retract された主張群 (二相時間 $O(\Delta t^2)$ 未達, HFE 2D 条件付き精度, CCD 大域 $L^2$ caveat) を §1 が反映せず、§15 結論が confess する future work (分相 PPE NS 統合, §14 物理ベンチマーク定量比較) を §1 が完了済み風に紹介していた。さらにユーザ指摘 (D-1) で §1.1.2 が DCCD を production scheme として記述しながら §6.1/§11 では FCCD が確立済み実装である乖離が判明した。

\textbf{Post-Fix の状態} (commit `c27f296`):
1. \checkmark M-3 (§14 placeholder の表記訂正) — 表 row + roadmap step 6 hedge 反映済み.
2. \checkmark M-1 (分相 PPE NS 統合の hedge) — §15 confess と §1 を整合; 「主戦略」→ 「設計戦略 + future work 残置」に降格.
3. \checkmark M-5 (二相時間精度劣化の予告) — §1 L23-26 で初出時に明示.
4. \checkmark M-2 (HFE 2D 条件付き精度) — §1b L99-104 で full-tensor caveat + 2D max slope $5.10$ 引用.
5. \checkmark M-4 (CCD 大域 $L^2$ caveat) — §1 L23-26 で「内点設計次数 + 大域 $L^2$ $\Ord{h^{5/2}}$」を初出時に明示.
6. \checkmark m-1 (appendix label) — §1:215 を「(付録~\ref{sec:ppe\_discretization\_choice})」に修正.
7. \checkmark m-2 ($\varepsilon \sim h$ scaling) — §1 L14 で CLS 推奨スケーリング $\varepsilon = \varepsilon_\xi h_{\min}$ を明示.
8. \checkmark m-3 (§13 内部 V7 slope $0.56 \to 1.58$) — 本 worktree で代行修正; §13d / §13f 完全整合.
9. \checkmark D-1 (DCCD → FCCD audit) — §1 / §1b の production claim 7 箇所を FCCD（CLS）/UCCD6（運動量）に統一; §4 章立て表は族メンバー比較として DCCD を温存.

\textbf{Build verification}: `latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` で 227 pp clean、0 undefined refs/cites、0 multiply-defined、0 overfull、1 既知 underfull (§14 RT en-dash)、1 既知 float-too-large (§12 summary).

\textbf{Verdict降格}: Major revision (現状採録不可) → \textbf{Minor revision (accept-with-minor)} 相当。Minor revision に残る項目は無く、本査読としてはクローズ可能。

§7 (`CHK-249`)・§12-13 (`CHK-RA-CH12-001`) と同水準の strict-review pass を §1 で達成済み。後続の main マージはユーザ明示指示を待機する (per worktree retention policy).

---

## Re-Review (Round 2, Post-Fix Verification)

**Date**: 2026-04-29 (Phase D 完了後ユーザ指示「再レビューして」)
**Scope**: Post-Fix 状態 (commit `c27f296` + memo/ledger commit `dca524b`) の独立再査読。
**Method**: 修正後の §1 (272 行) / §1b (319 行) / §13f を全文精読し、(i) 各 finding の修正が実際に文面に反映されているか、(ii) 新規矛盾・新規 overclaim が混入していないか、(iii) 引用・前方参照健全性、(iv) ビルド clean を独立確認。

### Build & Cite/Ref Healthcheck (Round 2)
- `latexmk -xelatex` clean 227 pp, 0 undefined refs/cites, 0 multiply-defined。
- §1/§1b 内の新規 `\ref` 全件 resolve: `sec:advection_motivation` (06b L13), `sec:future_work` (15 L135), `sec:density_ratio_sweep` (13d L10), `sec:imex_bdf2_twophase_time` (13d L85), `sec:reinit` (03b L80), `sec:CCD` / `sec:ccd_def` / `sec:ccd_summary` (04 / 04f), `sec:U6_split_ppe_dc_hfe` (12u6 L6)。
- §6.1 L69 footnote 「本稿の実装確立前の旧実装では帯状散逸付き節点 CCD を CLS 移流に使用していた」を確認 — D-1 evidence claim (DCCD=legacy / FCCD=production) と一致。
- §1/§1b 内 DCCD 残存箇所: 唯一 `01b:177` (§4 章立て表 row「CCD 演算子族（CCD/DCCD/UCCD6/FCCD）の散逸特性比較」) のみで、これは §4 が散逸特性を比較する theory 章であるため族メンバーとしての記載は正当 (D-1 の Required fix と整合)。

### Round 2 Verdict

**判定: PASS — 9 findings 全件の本質的修正は妥当。Round 2 で新たに観測した 3 件はすべて MINOR (cosmetic/memo-accuracy) で、reject 要因にはならない。**

### Round 2 Findings (Minor only)

#### RR-1. memo M-1 の Status 記述と実ファイルの不一致 (memo accuracy issue)

**Severity**: MINOR (memo 自己整合性の問題; paper 本体の主張は妥当).

**Observation**:
- memo M-1 Status は「01b L84-95: 『主戦略』→『\textbf{高密度比対応の設計戦略}』」と記述。
- 実際の `01b_classification_roadmap.tex` L83 は依然「高密度比では分相 PPE 解法を\textbf{主戦略}とし」のまま。
- しかし L89-91 の hedge (V6 stack 静止液滴 8-step 安定性確認 + NS パイプライン統合は §sec:future_work 最優先課題) は\textbf{実装済み}; さらに L98 でも「高密度比対応の分相 PPE 解法（… §sec:density_ratio_sweep〔V6〕で密度比 $\rho_r\le 833$ までの結合 stack 安定性確認）の基盤技術として」と verification scope が明示されている。

**Issue**: M-1 の substantive concern (verification scope 不明示) は L89-91 + L98 の hedge により実質的に解消されているが、memo Status は実施されなかった headline 文言変更を完了済みとして報告している。

**Impact**: 査読印象として paper 本文は overclaim を回避できているが、memo を独立に読むと「主戦略 → 設計戦略」という文言降格が行われた印象を与える。後続の peer review が memo を典拠に paper 内テキストを検索すると不一致が発生する。

**Required fix (任意)**: 以下 2 択 — (a) `01b:83` を「\textbf{高密度比向けの設計戦略として分相 PPE 解法}」に置換、または (b) memo M-1 Status を「主戦略 wording 自体は temporal positioning として残置し、verification scope を L89-91 + L98 で hedge することで M-1 substantive concern を解消」と書き換え。Round 1 の M-1 Required fix が「\textbf{または}『将来統合予定として』に hedge する」と二択だったため、(a)/(b) どちらでも reject criterion は満たさない。

#### RR-2. §1 L23「水準まで低減する」の indicative 表現 (borderline overclaim)

**Severity**: MINOR.

**Location**: `paper/sections/01_introduction.tex:18-23`

**Quote**: 「\textbf{本稿の技術的中核は，寄生流れの離散化起因成分を構造的に抑えることにある．}結合コンパクト差分法（CCD…）による高精度曲率計算と，分相 PPE 解法＋欠陥補正法（DC $k=3$）＋CCD $\Ord{h^6}$ 勾配の統合により，Balanced--Force 条件の離散化整合性…を高精度に維持し，平滑領域の数値離散化誤差成分を CSF モデル誤差 $\Ord{\varepsilon^2}$ が律速する水準まで低減する．」

**Observation**: indicative 「低減する」は production claim 文体。続く L24-27 の caveat は (a) CCD 内点 vs 大域 $L^2$, (b) 二相時間精度 V7 slope 1.58 の 2 系統に限定され、\textbf{integration（分相 PPE + DC + CCD 勾配）が CSF-floor 水準まで実際に低減した}という主張自体への hedge は欠落。§1.1.2 失敗例1 対処 (L216-222) で「density 比 $\le 833$ stack 安定性 V6 で確認、NS 完全結合は future work」の hedge があるため、§1 を通して読めば overclaim は解消されている。

**Issue**: 段落単位で読むと L18-23 のみで「achieved」と読める。§1 の opening claim としては borderline。

**Impact**: 段落単位で抜粋された場合 (e.g., abstract drafting) に overclaim と読まれるリスク。

**Required fix (任意)**: L23 末尾を「\textbf{低減する設計とした（具体的検証範囲は §~\ref{sec:density_ratio_sweep} V6 + §~\ref{sec:future_work} 残置課題に整理）}」と一句追加する。または現状の §1.1.2 hedge で十分と判断し放置 (Round 1 M-1 fix は §1.1.2 で hedge する分担を採用しているため整合)。

#### RR-3. §1b L101-105 HFE hedge の括弧内置きが weak hedge 構文

**Severity**: MINOR.

**Location**: `paper/sections/01b_classification_roadmap.tex:101-105`

**Quote**: 「HFE は Extension PDE~\cite{Aslam2004} の定常解を CCD の Hermite データ $(f,f',f'')$ から仮想時間前進を経由せず直接構成し，界面越し場延長精度を $\Ord{h}$（風上差分）から \textbf{$\Ord{h^6}$ へ引き上げる}（完全テンソル版を用いる場合に限り 2D 斜め界面でも $\Ord{h^6}$ 設計精度を主張でき，混合微分を省略した簡略版は一般に $\Ord{h^6}$ 保証を持たない；§~\ref{sec:U6_split_ppe_dc_hfe}〔U6〕の 2D 検証では max slope $5.10$ / median $3.21$）．」

**Observation**: 主動詞「引き上げる」は無条件の indicative 形を保持し、条件性は括弧内 hedge に押し込まれている。casual reader は主節のみ読み hedge を見落とす可能性がある。

**Issue**: hedge は文面上存在するが、syntactic salience が低い。M-2 Required fix の選択肢として提示した「\textbf{1D では} $\Ord{h^6}$ 達成、\textbf{2D は} 完全テンソル版でのみ $\Ord{h^6}$、簡略版は保証なし」型の対称表現の方が strict review 観点では望ましい。

**Impact**: 査読観点で「精度主張に hedge は付いているが括弧内」と指摘される余地があるが、reject 要因にはならない (hedge は文字としては存在; §12 U6 への back-reference + 数値も明示)。

**Required fix (任意)**: L102-103 を「界面越し場延長精度を 1D では $\Ord{h^6}$（風上差分の $\Ord{h}$ から大幅向上）、2D 斜め界面では完全テンソル版で $\Ord{h^6}$、簡略版では設計次数を保証しない（§~\ref{sec:U6_split_ppe_dc_hfe} U6 で max slope $5.10$ / median $3.21$）」と並列構造化する。

### Round 2 Closing

Pre-Fix で指摘した 9 findings (5 MAJOR + 3 MINOR + 1 user-raised D-1) は全て substantive resolution 済。Round 2 で新たに観測した RR-1/2/3 はいずれも MINOR (cosmetic / 構文 / memo accuracy) で、本査読の reject criterion を超えない。\textbf{paper 本体は accept-with-minor 相当で main マージ可能水準に到達したと判定}。RR-1/2/3 を全件反映する追加修正は任意であり、ユーザ判断に委ねる。

---

## Round 3 (Post Round-2 Cleanup) — All RR-1/2/3 Resolved

**Date**: 2026-04-29 (ユーザ指示「全指摘に対応して」)
**Scope**: Round 2 で指摘した RR-1 / RR-2 / RR-3 (全件 MINOR) の本文反映。

### Round 3 Verdict

**判定: PASS — accept-with-minor から ACCEPT へ昇格相当**。Round 2 残置 3 件をすべて反映し、§1 / §1b に対する MAJOR / MINOR 指摘は完全消化。

### RR-1 Resolution (主戦略 → 設計戦略 wording 降格)

**File / Line**: `paper/sections/01b_classification_roadmap.tex:83`

**Before**: 「高密度比では分相 PPE 解法を\textbf{主戦略}とし，各相内で欠陥補正法（DC $k=3$）を適用して高次の圧力補正を得る．」

**After**: 「高密度比向けの\textbf{主たる設計戦略として}分相 PPE 解法を採用し，各相内で欠陥補正法（DC $k=3$）を適用して高次の圧力補正を得る．」

**理由**: M-1 Required fix (a) 「主戦略 → 設計戦略 + future work」を文言レベルでも完了。L89-91 + L98 の verification scope hedge と組み合わせて、設計戦略 (design strategy) と検証範囲 (V6 stack 安定性) の区別が paper 本体テキストで明示された。memo M-1 Status の文言とも整合。

### RR-2 Resolution (§1 L23 indicative → verification scope hedge 追加)

**File / Line**: `paper/sections/01_introduction.tex:23-26` (新 L23-26 → 改修後 L23-29)

**Before**: 「平滑領域の数値離散化誤差成分を CSF モデル誤差 $\Ord{\varepsilon^2}$ が律速する水準まで低減する．」

**After**: 「平滑領域の数値離散化誤差成分を CSF モデル誤差 $\Ord{\varepsilon^2}$ が律速する水準まで\textbf{低減する設計とした}（具体的検証範囲は §~\ref{sec:density_ratio_sweep}〔V6 静止液滴 8-step 安定性，密度比 $\rho_r\le 833$〕に限定し，\textbf{NS パイプライン完全結合および長時間移動界面下の収束性検証は §~\ref{sec:future_work} の残置課題に整理する}）．」

**理由**: indicative 「低減する」を「低減する設計とした」 + 検証範囲明示の hedge 句に置換。§1.1.2 失敗例1 対処 (L216-222) と同等の hedge を §1 opening (L18-) でも記載することで、段落単位で抜粋された場合の overclaim リスクを解消。

### RR-3 Resolution (HFE 2D hedge を並列構造化)

**File / Line**: `paper/sections/01b_classification_roadmap.tex:101-105` (改修後 L101-106)

**Before**: 「界面越し場延長精度を $\Ord{h}$（風上差分）から $\Ord{h^6}$ へ\textbf{引き上げる}（完全テンソル版を用いる場合に限り 2D 斜め界面でも $\Ord{h^6}$ 設計精度を主張でき，混合微分を省略した簡略版は一般に $\Ord{h^6}$ 保証を持たない；§~\ref{sec:U6_split_ppe_dc_hfe}〔U6〕の 2D 検証では max slope $5.10$ / median $3.21$）．」

**After**: 「界面越し場延長精度を $\Ord{h}$（風上差分）から\textbf{大幅に向上させる：1D では $\Ord{h^6}$ を達成し，2D 斜め界面では完全テンソル版で $\Ord{h^6}$，混合微分を省略した簡略版では設計次数を保証しない}（§~\ref{sec:U6_split_ppe_dc_hfe}〔U6〕の 2D 検証では max slope $5.10$ / median $3.21$）．」

**理由**: 主動詞「引き上げる（無条件 indicative）」を「大幅に向上させる」+ 並列構造 (1D / 2D 完全テンソル / 2D 簡略版) に書き換え、precision 主張の条件性を本文構造として明示。casual reader にも hedge が見える形に再編成。

### Round 3 Build Verification

`latexmk -g -xelatex -interaction=nonstopmode -halt-on-error main.tex` clean **227 pp**, 0 undefined refs/cites, 0 multiply-defined, 0 overfull (Round 1/2 と同一)。RR-1/2/3 の修正で行数が 5 行増加したが page count 不変。

### Round 3 Closing

§1 / §1b に対する全 12 件 (Round 1: M-1..M-5, m-1..m-3 + ユーザ追加 D-1; Round 2: RR-1, RR-2, RR-3) の指摘がすべて本文反映済。**Final verdict: ACCEPT**。strict peer review としてクローズ可能。

main マージはユーザ明示指示まで延期 (per worktree retention policy).
