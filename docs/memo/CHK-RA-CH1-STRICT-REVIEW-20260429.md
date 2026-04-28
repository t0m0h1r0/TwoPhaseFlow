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

---

## Overall Assessment

§1 は教材的構成の整理は丁寧で、読者誘導 (§1.2 困難の 4 分類 → §1.3 失敗例 4 つ → §1.4 ロードマップ) は読みやすい。引用 16 keys は全て bibliography.bib に存在 (確認済)、`\ref{}` 26+ は全て label に解決 (確認済)、内部数式 (チェッカーボード央差分 $=0$ など) も成立する。

問題は\textbf{導入の温度設定}に集中している。§7・§12-13 の strict review で既に retract されている主張群 (二相時間 $O(\Delta t^2)$ 未達, HFE 2D 条件付き精度, CCD 大域 $L^2$ caveat) を §1 が反映せず、さらに §15 結論が confess している future work (分相 PPE NS 統合, §14 物理ベンチマーク定量比較) を §1 が完了済み風に紹介する。導入は論文全体の expectations を設定する章であり、ここで hedge 不在のまま強い主張を並べると、読者は本文を読み進めるたびに「導入と乖離している」感を蓄積する。

修正優先順位 (Major → Minor 降格に必要な順):

1. \textbf{M-3} (§14 placeholder の表記訂正) — 一語修正で解決可、reject reason の最大ノードを直す
2. \textbf{M-1} (分相 PPE NS 統合の hedge) — §15 confess と §1 を整合させる、本文に他の波及なし
3. \textbf{M-5} (二相時間精度劣化の予告) — §1b L115-119 全体像段落に 2-3 行追加
4. \textbf{M-2} (HFE 2D 条件付き精度) — 1 sentence の hedge、§9c との粒度合わせ
5. \textbf{M-4} (CCD 大域 $L^2$ caveat) — 「内点で」修飾 1 語追加

m-1, m-2, m-3 は M-1..M-5 の対応中に併修できる軽微な修正である。これら 5 + 3 が対応されれば、§1 単体レビューとしては \textbf{Major revision → Minor revision (accept-with-minor)} まで進められる。

§7 (`CHK-249`)・§12-13 (`CHK-RA-CH12-001`) と同水準の strict-review pass を §1 でも達成するためには、上記 §15 confess と §13 V7 の reality を §1 に逆流させる作業が必須である。
