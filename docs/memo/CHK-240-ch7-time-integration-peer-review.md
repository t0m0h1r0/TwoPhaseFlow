# CHK-240 査読メモ: §7 時間積分 (TVD-RK3 / IMEX-BDF2 / CN / IPC / CFL)

> Reviewer: Claude Code (Opus 4.7) — strict peer review stance
> Scope: [paper/sections/07_time_integration.tex](../../paper/sections/07_time_integration.tex) 976 行 + Appendix D ([appendix_advection.tex](../../paper/sections/appendix_advection.tex), [appendix_stability_analysis.tex](../../paper/sections/appendix_stability_analysis.tex), [appendix_numerics_solver_s1.tex](../../paper/sections/appendix_numerics_solver_s1.tex))
> Style: CHK-227 / CHK-228 と同型。**Reviewer 独自識別の懸念群** が出発点 (user 事前懸念は無し)
> Method: PaperReviewer prompt §AP-01 準拠 — **全 finding に file:line + verbatim quote + severity**

---

## Section A: 査読官スタンスと総合判定

### A-1. 章の理論的価値 — **高い**

§7 は CHK-223 で旧 §5/§6 から 5 項目を migrate して新規作成された章で、項別時間処理 (移流 / 粘性 / 表面張力 / 圧力投影 / 浮力) の **設計判断と根拠** を一次資料として整理した。特に:

- §7.1-§7.2 で CFL 数定義 → von Neumann 安定性分類 → 時間精度 (Lax) を **積み上げ式に提示**
- §7.3-§7.7 が **項別 5 節構成** で、各節が「production の選択 + 安定性 + 精度」の triple を持つ
- §7.8 表 (`tab:time_accuracy_prod`) で全項の時間精度を集約、**界面粘性クロス項 O(Δt) 律速** を脚注付きで誠実に開示
- §7.9 で **項別律速合成式** `Δt_ch13 = min(Δt_adv, Δt_σ, Δt_buoy, Δt_operator)` を確定

**理論的核**: jump-decomposed CSF が IPC と同時刻結合することで standard Chorin の O(Δt) splitting 誤差を O(Δt²) に低減する [paper/sections/07_time_integration.tex:866-872](../../paper/sections/07_time_integration.tex#L866-L872) — この proof sketch (§7.6 L705-723) は self-contained で、章の中核的な理論的貢献である。

### A-2. 章 narrative arc 評価

**全体 arc は強固**: 章頭 tcolorbox table → 形式分類 → 剛性 map → 項別 5 節 → 全体精度表 → Δt 合成式 という流れは読者にとって辿りやすい。CHK-227/228 で指摘された §9/§11 章のような「巨大 algbox」「Level 分類削除残存」 type の問題は **無い**。

ただし、**3 つの構造上の弱点**が指摘される:
- (i) §7.4 内 "ch13 production = implicit-BDF2" と "比較・検証用 = CN" の境界が L574-575 の 1 文のみで明示され、subsection title "Crank--Nicolson 粘性 Helmholtz とデフェクト補正（**CN 採用時**）" の括弧内補足にしか反映されていない (B-3 詳述)
- (ii) §7.8 表内で "CN 採用時の defect-correction" 行が無いため、production 表と比較研究が混在している
- (iii) CHK-NNN migration markers が本文に 6 件残置 (L2, L262, L331, L571, L673, L937) — 公開前に削除すべき技術的負債

### A-3. 総合判定 — **major revision 推奨**

| 重大度 | 件数 | 概要 |
|---|---|---|
| **FATAL** (factual error / paper eq 矛盾) | **0** | proof sketch / 安定性解析の致命的誤りは検出されず |
| **MAJOR** (missing citation / wrong eq / A3 gap / load-bearing 主張の論拠欠落) | **12** | 理論的飛躍 4 + citation 欠落 2 + A3/PR-5 4 + structural 2 |
| **MINOR** (style / label inconsistency / 古いコメント残置) | **10** | §番号 hardcode 誤り + CHK marker + magic number + backward-compat label |

**Verdict: major revision** — FATAL は無いが MAJOR が 12 件あり、特に **A3/PR-5 群 (D-1〜D-4) は code 側 docstring の §番号が現 paper と完全に乖離** しているため、reviewer として「公開前に修正すべき」と判定する。citation 群 (C-2, C-3) は **load-bearing claim の論拠が \cite{} key 無しで人名のみ** という査読基準上の致命点を含み、最低限ここは修正必須。

---

## Section B: 懸念 1 (数学・derivation 疑義 4 件)

### B-1 [MAJOR / C1-1] Helmholtz 演算子 A の対称正定値主張は変密度・変粘性で一般に成立しない

[paper/sections/07_time_integration.tex:435](../../paper/sections/07_time_integration.tex#L435):
> 左辺演算子 $A = I - \gamma\Delta t\,\mathcal{L}_{\nu}$ は対称正定値であり，ch13 既定では Krylov 部分空間法 (GMRES) で解く．

ここで $\mathcal{L}_{\nu} = \rho^{-1}\bnabla\cdot\bigl[\mu(\bnabla + \bnabla^T)\bigr]$ ([07_time_integration.tex:429](../../paper/sections/07_time_integration.tex#L429))。

**疑義**: 変密度 $\rho(\bm x)$ ・変粘性 $\mu(\bm x)$ では:
1. $\rho^{-1}$ が空間変化するため、$\rho^{-1}\nabla\cdot[\mu(\nabla+\nabla^T)]$ は **左から行列積で書くと一般に非対称** ($\rho^{-1}$ が右からの乗算であれば対称でも、ここでは $L_2$ 内積に対して非対称)
2. 仮に **重み付き内積** $\langle u,v\rangle_\rho = \int \rho \, u\cdot v\,dx$ を採用すれば対称性は回復するが、本文はこの内積選択を明示していない
3. GMRES が選ばれている事実 (L436) 自体、**演算子が対称正定値でないこと**を示唆する (対称正定値なら CG が標準選択)

**論理的帰結**: 「対称正定値」の主張と「GMRES を選ぶ」事実は内部矛盾している。reviewer 判断としては:
- (a) 「対称正定値」を **「(適切な重み付き内積で)対称正定値」** に修正、または
- (b) 「GMRES を採用する理由は変密度に伴う非対称性」と明示するのが正しい

**補足**: paper §7.4 直後の L438-444 では Jacobi 前処理付き GMRES の収束性議論があり、論理は GMRES 前提で書かれている。L435 の対称正定値主張は **章内で残された旧記述** である可能性が高い。

### B-2 [MAJOR / C1-2] Lie splitting で全体 O(Δt²) 主張に citation 無し / justification 不十分

[paper/sections/07_time_integration.tex:146-148](../../paper/sections/07_time_integration.tex#L146-L148):
> \textbf{Splitting 整合性}：本実装は Lie splitting（IMEX-BDF2 を主軸とする fractional step）を採用し，splitting 誤差は $\Ord{\Delta t^2}$ である．各段の時間精度（NS 対流 2 次・粘性 2 次・圧力投影 2 次）と整合する．

**標準的事実**: Lie splitting (Trotter formula) は **operator splitting で O(Δt¹)**, Strang (symmetric) splitting で O(Δt²) というのが教科書的事実 (Marchuk 1990, Glowinski 2003 等)。本文は逆を主張している。

**疑義の解像**: §7.6 の IPC proof sketch [paper/sections/07_time_integration.tex:705-723](../../paper/sections/07_time_integration.tex#L705-L723) で「IPC により $\delta p$ を介し Predictor + PPE が同時刻結合され、splitting 誤差が O(Δt²) になる」という議論が展開されている。これが L146-148 の「Lie splitting で O(Δt²)」の根拠と思われるが:
- §7.1 (L146) では **citation も §7.6 への forward-ref も無く**、いきなり「O(Δt²)」と断定
- 「projection idempotency」「BDF2 self-consistency」という根拠語が用いられていないため、**読者は Lie splitting の標準理論との矛盾を解消できない**

**修正提案** (C1-2): L146-148 に「IPC 補正 (§7.6) により splitting 誤差は $\Ord{\Delta t^2}$ に緩和される」という forward-ref を追加し、Marchuk 等 Lie splitting の標準引用も付記。

### B-3 [MAJOR / C1-3] σ_max ≈ 0.91 「数値計算による」が支持 figure / table 無し

[paper/sections/appendix_stability_analysis.tex:35-38](../../paper/sections/appendix_stability_analysis.tex#L35-L38):
> $\varepsilon_d^{\mathrm{adv}} = 0.05$ のとき $\max_\xi\{H(\xi)\,\hat{k}^*(\xi)\} \approx 1.9$（$\xi \approx 0.8\pi$ 付近，**数値計算による**）であるから：
> \[ \sigma_{\max} = \frac{\sqrt{3}}{1.9} \approx 0.91 \]

**疑義**:
1. 「数値計算による」と明記しているが、**dispersion curve の図、表、補助計算スクリプトへの ref が無い**
2. $\varepsilon_d^{\mathrm{adv}} = 0.05$ という数値が **どこから来るか paper 全体で定義されていない** (DCCD filter parameter? §4.4 sec:dissipative_ccd の指定?)
3. 結果 $\sigma_{\max} \approx 0.91$ は §6 advection 章の Result 6.X (`result:dccd_stability` [06b_advection.tex:176](../../paper/sections/06b_advection.tex#L176)) で引用されているが、その引用箇所と App. D.1 の符号・数値の往復整合性が読者には見えにくい

**修正提案**: App. D.1 に dispersion curve の small figure (≤ 1 page) を追加するか、補助スクリプト (numerical evidence) を artifacts/ 以下に置いて参照。

### B-4 [MAJOR / C1-4] C_cross = O(1) は値・出典・derivation が無い

[paper/sections/07_time_integration.tex:497-501](../../paper/sections/07_time_integration.tex#L497-L501):
> \begin{equation}
>   \Delta t \le C_{\mathrm{cross}} \cdot \frac{h^2}{\Delta\mu / \rho}
>   \label{eq:cross_cfl}
> \end{equation}
> ここで $C_{\mathrm{cross}} = O(1)$，$\Delta\mu = \mu_l - \mu_g$．$\mu_l/\mu_g = 100$ の系では等粘性系の陽的粘性 CFL より約 $1/100$ 倍厳しくなる可能性がある．

**疑義**:
1. $C_{\mathrm{cross}} = O(1)$ は **具体的数値 (例: 1/4 や 1/2) も上界も与えられない**
2. 「界面上での von Neumann 解析から」と L496 で述べているが、解析自体は paper 内に **存在しない**
3. eq:cross_cfl は warnbox 内 (`warn:cross_cfl`) として提示されているため、「主結果」ではなく「注意喚起」のラベル付け。だが §7.8 表 (`tab:time_accuracy_prod`) の「界面クロス項 O(Δt)」を実質的に支える鍵式である

**修正提案**: $C_{\mathrm{cross}}$ の数値見積もりを App. D.1 に追加 derivation として置く、または既存文献 (例: Sussman & Smereka 系列) への citation を付記。

---

## Section C: 懸念 2 (citation / 参考文献疑義 4 件)

### C-1 [MINOR] HairerWanner Sec. V vs Sec. V.1 の表記不一致

[paper/sections/07_time_integration.tex:256](../../paper/sections/07_time_integration.tex#L256):
> 証明と $\rho$--$\sigma$ 多項式の根分布は Hairer--Wanner~\cite{HairerWanner1996} **Sec.~V** を参照．

[paper/sections/07_time_integration.tex:397](../../paper/sections/07_time_integration.tex#L397):
> 粘性ブロックは BDF2 で陰的に扱うため，BDF2 が A-stable（Hairer--Wanner~\cite{HairerWanner1996} **Sec.~V.1**）

[paper/sections/07_time_integration.tex:449](../../paper/sections/07_time_integration.tex#L449):
> BDF2 は A-stable (Hairer--Wanner~\cite{HairerWanner1996} **Sec.~V.1**; 詳細分類は §\ref{sec:von_neumann} 参照)

**疑義**: 同一 reference の同一主張に対し Sec. V (chapter) と Sec. V.1 (subsection) の混在。Hairer-Wanner Vol. I 第 V 章「BDF methods」の中で A-stability は V.1 に詳述される構成のため、**Sec. V.1 が正しく、L256 の "Sec. V" は脱字**と推定。

**修正**: 三箇所を Sec. V.1 に統一。

### C-2 [MAJOR / C2-1] Pyo--Shen / Guermond--Quartapelle 系列に \cite{} key 無し (load-bearing)

[paper/sections/07_time_integration.tex:729](../../paper/sections/07_time_integration.tex#L729):
> 本節の精度評価は変密度下でも保たれる（**直接的な variable-density IPC $\Ord{\Delta t^2}$ 誤差解析は Pyo--Shen / Guermond--Quartapelle 系列を参照**）．

**疑義**:
1. これは §7.6 IPC proof sketch の **load-bearing 主張** (variable-density で IPC が O(Δt²) を保つことの直接的根拠)
2. 人名のみで `\cite{}` key 無し → **bibliography に出力されない** → 読者は文献を辿れない
3. Bibliography ([paper/bibliography.bib](../../paper/bibliography.bib)) に Pyo / Quartapelle で始まる entry の有無も確認すべき

**修正必須** (publication blocker): \cite{PyoShen2007} (or 該当年), \cite{GuermondQuartapelle1998} (or 該当年) を bibliography に登録し、key で引用。

### C-3 [MAJOR / C2-2] standard IPC で variable-density O(Δt²) を主張するが Guermond2006 §6.2 は rotational IPC の節

[paper/sections/07_time_integration.tex:727-729](../../paper/sections/07_time_integration.tex#L727-L729):
> 変密度下でこの正則性が破綻しないことは Guermond--Minev--Shen~\cite{Guermond2006} **§6.2 (rotational pressure correction)** およびそこで参照される変密度系列で確立されており，本節の精度評価は変密度下でも保たれる

**疑義**:
- §7.6 本文 (eq:ppe_jump_decomposed, L641-646) で実装されているのは **standard IPC** ($\nabla\cdot(\rho^{-1}\nabla\delta p) = \nabla\cdot u^*/\Delta t$)
- 一方 citation source は Guermond2006 §6.2 = **rotational IPC** (圧力更新が $p^{n+1} = p^n + \delta p - \nu\nabla\cdot u^*$)
- standard IPC と rotational IPC の variable-density 精度結果は **同一とは限らない** (rotational IPC は L²-norm で O(Δt^{5/2}), L∞ で O(Δt²) という別結果が知られる; cf. [docs/memo/2026-04-18_third_order_time_integration.md](../2026-04-18_third_order_time_integration.md) Q2)
- つまり L727-729 は「standard IPC の variable-density O(Δt²)」を「rotational IPC が立証されている」で支える論理飛躍を含んでいる可能性

**修正提案**: (a) Guermond2006 で standard IPC の variable-density 結果が確立されている節 (§5 か §4) を citation source に変更、または (b) "rotational pressure correction で確立された結果が standard IPC に拡張可能であることを示すための補助 lemma" として明示的に整理。

### C-4 [MINOR / Q5] C_σ < 1 が定義されないまま「補正」と書かれる

[paper/sections/appendix_numerics_solver_s1.tex:29-32](../../paper/sections/appendix_numerics_solver_s1.tex#L29-L32):
> 厳密な係数は $2/(3\sqrt{\pi}) \approx 0.376$ であるが，文献で広く用いられる簡略形 $1/\sqrt{2\pi} \approx 0.399$ を採用すると式 \eqref{eq:dt_sigma} を得る（$6\%$ 大きい $\Delta t$ を許すが，**CFL 安全係数 $C_\sigma < 1$ で補正するため実用上問題ない**）

**疑義**:
- $C_\sigma$ という記号は §7 + App. D を通じて **どこにも定義されていない** (`grep -n "C_.\\sigma\\|C_sigma\\|安全係数" paper/sections/`)
- "補正するため" と書きながら、補正の具体的な手順 (例: 「$\Delta t_\sigma$ に最終的に乗じる係数」) も明記が無い

**修正**: $C_\sigma$ の定義を App. D.2 内で明示するか、§14 ベンチマーク章での具体値 (例: $C_\sigma = 0.5$) への ref を付記。

---

## Section D: 懸念 3 (A3 / PR-5 algorithm fidelity 4 件)

### D-1 [MAJOR / C3-1] TVD-RK3 — code docstring の §番号と paper §番号が完全乖離

[src/twophase/time_integration/tvd_rk3.py:4](../../src/twophase/time_integration/tvd_rk3.py#L4):
> Implements **§8 (Eq. 79–81)** of the paper.

[paper/sections/07_time_integration.tex:280](../../paper/sections/07_time_integration.tex#L280) — **paper の正しい位置**:
> ... \notag\\ q^{n+1} &= ... \label{eq:tvd_rk3}

paper §7.3 (sec:time_level1) の eq:tvd_rk3 が現在の正しい location。code 側は **§8 Eq. 79-81** を参照しているが、現 paper §8 は [08_collocate.tex](../../paper/sections/08_collocate.tex) (collocate / pressure 章)。完全な A3 chain 切断。

**根本原因 (推定)**: CHK-225 で `05_time_integration.tex → 07_time_integration.tex` rename が行われた際、code 側の docstring 更新が伴わなかった。tvd_rk3.py の `§8` は **paper の更に古い構成** (おそらく当初 §8 にあった時期) の名残と推測される。

**A3 違反のさらなる証拠**: tvd_rk3.py が呼ばれる先で **3 種の異なる §番号**が用いられている (Phase 1 Explore agent 2 の指摘):
- [src/twophase/tests/test_time_integration.py:8](../../src/twophase/tests/test_time_integration.py#L8) — `(§4 eq:tvd_rk3)`
- [src/twophase/tests/test_time_integration.py:275](../../src/twophase/tests/test_time_integration.py#L275) — `§9 eq:tvd_rk3`
- tvd_rk3.py:4 — `§8 (Eq. 79–81)`

**正しい現位置**: paper §7.3 eq:tvd_rk3 (L280)。**3 種すべて誤り**。

**修正提案**: tvd_rk3.py docstring + 関連 test docstring 計 4 箇所を `§7.3 eq:tvd_rk3` に統一。本件は **PR-5 Algorithm Fidelity の最低限の前提である「paper-code 同一参照」**を破っており、A3 traceability マニフェストの中核違反。

### D-2 [MAJOR / C3-2] CFL — code docstring の §番号と paper §番号が乖離

[src/twophase/time_integration/cfl.py:4](../../src/twophase/time_integration/cfl.py#L4):
> Implements **§8 (Eq. 84)** of the paper.

[paper/sections/07_time_integration.tex:883-890](../../paper/sections/07_time_integration.tex#L883-L890) — **paper の正しい位置**:
> \begin{equation} \Delta t_\text{ch13} = \min(...) \label{eq:dt_per_term} \end{equation}

CFL 合成式は paper §7.9 eq:dt_per_term (L889)。code 側 cfl.py docstring は §8 Eq. 84 を参照、これも **完全乖離**。

[src/twophase/time_integration/cfl.py:9](../../src/twophase/time_integration/cfl.py#L9):
> Capillary CFL: ... (**§8.4** Eq.(dt_sigma))

paper の毛管 CFL は §7.9 eq:dt_sigma (L906) で、§8.4 ではない。

**修正提案**: cfl.py docstring の §8 / §8.4 → §7.9 に置換。

### D-3 [MAJOR / C3-3] IMEX-BDF2 — paper-eq citation 完全欠落

[src/twophase/simulation/viscous_predictors.py:195-225](../../src/twophase/simulation/viscous_predictors.py#L195-L225):
```python
def predict_bdf2(self, ...):
    """Solve u* - (2/3)dt V(u*) = 4/3 uⁿ - 1/3 uⁿ⁻¹ + (2/3)dt E."""
    base_velocity = [
        (4.0 / 3.0) * u - (1.0 / 3.0) * u_prev,
        ...
    ]
    ...
    dt_effective=IMPLICIT_BDF2_PROJECTION_FACTOR * dt,  # = (2/3) * dt
```

paper の対応式: §7.3 eq:predictor_imex_bdf2 (L367) および §7.4 eq:helmholtz_implicit_bdf2 (L430)。

**疑義**:
- BDF2 係数 (`4/3`, `-1/3`, `2/3`) は **論文 eq への ref 無く inline で書かれる**
- module docstring に「§X Eq. Y」citation 完全欠落
- 5 schemes 中で **A3 traceability が最も乏しい** (Phase 1 agent 2 の判定)

**修正提案**: viscous_predictors.py の `ImplicitBDF2ViscousPredictor` class docstring に `Implements §7.3 eq:predictor_imex_bdf2 (BDF2 係数 4/3, -1/3, 2/3) and §7.4 eq:helmholtz_implicit_bdf2 (Helmholtz 形 dt_effective = (2/3) dt).` を追加。

### D-4 [MAJOR / C3-4] CN paper §7.4 vs code Heun (PicardCN) — 非 A-stable 差

paper §7.4 sec:viscous_cn_defect_v7 [paper/sections/07_time_integration.tex:577-582](../../paper/sections/07_time_integration.tex#L577-L582):
> \begin{equation}
>   \Bigl(I - \tfrac{\Delta t}{2\rho}L_H\Bigr)\mathbf{u}^* = \text{RHS}, \qquad L_H = \bnabla\cdot(2\mu\mathbf{D}_h^{(H)}),
>   \label{eq:viscous_cn_helmholtz_v7}
> \end{equation}

これは **true implicit CN** (左辺が陰)。

code 側 [src/twophase/time_integration/cn_advance/picard_cn.py:1-22](../../src/twophase/time_integration/cn_advance/picard_cn.py#L1-L22):
> 1-step Picard iteration on the CN equation. Algebraically equivalent to **Heun's predictor-corrector (explicit trapezoid)**: ...
> Stability: **NOT unconditionally stable** -- this is a fully explicit evaluation of V at u^n and u_pred, so a parabolic (viscous) CFL condition Δt ≲ h²/(4 ν_max) is formally required.

つまり paper §7.4 は **true CN (A-stable)** を定式化、code は **Heun (非 A-stable)** を実装。

**緩和要素**:
- paper L574-575 で「ch13 production stack の既定は **implicit-BDF2** であるが、比較・検証用に CN を採用する場合」と明記、production は CN を使わない
- code 側 docstring は極めて誠実に「True implicit CN (A-stable) and Padé-(2,2) variants arrive in later phases」と将来計画を明記

**しかし依然として MAJOR である理由**:
1. paper §7.4 の「比較・検証用」記述は subsection title `(CN 採用時)` の括弧内補足にしか反映されておらず、**読者が paper §7.4 を独立に読むと "true implicit CN が実装されている" と誤解しやすい**
2. paper L578 の eq:viscous_cn_helmholtz_v7 を見て「これを試す」と期待する読者は、code の `cn_viscous=True` パスを通すと **実は Heun が走る**
3. cfl.py の docstring (L12-19) ですら「the current cn_viscous=True path ... is a 1-step Picard iteration on the CN equation — algebraically a Heun predictor-corrector — which is O(Δt²) accurate but NOT unconditionally stable」と **本人が認めている乖離**

**修正提案**: paper §7.4 sec:viscous_cn_defect_v7 内に **明示的な warnbox** を追加 — 「現在の実装は Heun corrector (1-step Picard); true implicit CN は将来 Phase」と paper 側で transparency を担保。

---

## Section E: 懸念 4 (third-order memo との緊張・production/comparison 境界 2 件)

### E-1 [MAJOR / C4-1] 第三次精度 memo (2026-04-18) の知見が §7 に反映されていない

[docs/memo/2026-04-18_third_order_time_integration.md](../2026-04-18_third_order_time_integration.md) は **Route B (AB3 + Richardson-CN + rotational IPC)** で global O(Δt³) を達成する設計を提示しており、特に:
- AB3 は虚軸近傍で零安定でない (R1 risk High)
- rotational IPC は L²-norm で O(Δt^{5/2}), L∞ で O(Δt²) (Q2 unresolved)
- Richardson-CN は richardson_cn.py に既実装

§7 でこの memo の知見への言及は [paper/sections/07_time_integration.tex:971](../../paper/sections/07_time_integration.tex#L971) と L976 の `\S\ref{sec:future_work}` への single forward-ref のみ。具体的には:
1. なぜ standard IPC を選んだか (rotational IPC を採用しない理由) の paper 内議論が無い
2. なぜ AB2 で十分か (AB3 の advective CFL 厳格化トレードオフ) の paper 内議論が無い
3. 「全体 O(Δt²) で閉じる根拠」と「O(Δt³) 化が possible である根拠」の **対比** が paper 内で見えない

**修正提案**: §7.8 末尾に短い paragraph (1/2 page) で「O(Δt³) 化への展望と現状で O(Δt²) を選ぶ理由」を追加し、memo の Route B 結論を ref。

### E-2 [MAJOR / C4-2] §7.8 表 (tab:time_accuracy_prod) で production と比較研究の境界が不明瞭

[paper/sections/07_time_integration.tex:828-845](../../paper/sections/07_time_integration.tex#L828-L845):
表 `tab:time_accuracy_prod` は production stack の項別時間精度を示すが、§7.4 で導入された **CN 比較研究 (sec:viscous_cn_defect_v7)** の行が無い。読者が §7.4 で CN 詳細を見た直後に §7.8 表を見ると、「CN は production に含まれるのか、含まれないのか」が判別困難。

加えて L843 の脚注 † (「界面粘性クロス項 O(Δt)」) は **production の限界** を率直に開示しており評価できるが、表内行が refer する eq 番号 (eq:cross_cfl) への back-link が無い。

**修正提案**: 表 `tab:time_accuracy_prod` に「CN (比較研究)」行を斜体 / 別マーカで追加するか、表脚注で「§7.4.1 sec:viscous_cn_defect_v7 は production stack 外」と明示。各行に対応 eq label を併記。

---

## Section F: 懸念間の coupling

### F-1 (B-1 + D-3) Helmholtz A の対称性主張 ↔ IMEX-BDF2 code 側 paper-eq 欠落
- B-1 で paper L435 が「対称正定値」と書き、D-3 で code viscous_predictors.py が paper-eq citation を欠落している
- 両者を同時に修正すれば、A3 chain ("paper L426-435: A の properties → code: ImplicitBDF2ViscousPredictor.predict_bdf2") が一気に閉じる

### F-2 (C-2 + C-3) Pyo-Shen 系列引用欠落 ↔ standard IPC vs rotational IPC 論理飛躍
- C-2 (Pyo-Shen の \cite{} key 欠落) は C-3 (Guermond2006 §6.2 が rotational なのに standard IPC で variable-density O(Δt²) を主張) の論理飛躍を**そのまま埋める文献**を欠いた状態
- 解決順序: まず Pyo-Shen / Guermond-Quartapelle を \cite{} key で登録 → 次に L727-729 の論理を「standard IPC の variable-density O(Δt²) は Pyo-Shen / Guermond-Quartapelle で確立」に書き換え

### F-3 (D-1 + D-2 + D-4) §番号系統的不整合 ↔ paper-code temporal mismatch
- D-1, D-2 は code docstring の **§番号 obsolete** (CHK-225 rename の追従漏れ); D-4 は **paper-code 実装乖離**
- 共通根因: paper renumbering / restructuring に code 側 trace が連動していない (CHK-216, 220, 222, 223 系統の章再編が複数回行われた結果)
- 修正にあたり: code 全体の `grep -rn "§[0-9]" src/twophase/` で **全 §番号 audit** を一括実施するのが効率的

### F-4 (E-1 + B-2) 第三次精度展望欠落 ↔ Lie splitting 説明不足
- E-1 で「O(Δt³) 化が possible だが O(Δt²) を選ぶ理由」が不明、B-2 で「O(Δt²) を支える Lie splitting の根拠」が citation 欠落
- 両者は **「現行 O(Δt²) を選ぶ正当化」** という同じテーマを違う切り口で要請している。§7.1 / §7.8 で統合的な「O(Δt²) 設計判断と将来展望」paragraph を新設すれば両方解決

---

## Section G: §7 narrative arc 評価

### G-1. 章頭 → 各節 → 表 → Δt 合成 の流れは強固

[paper/sections/07_time_integration.tex:13-80](../../paper/sections/07_time_integration.tex#L13-L80) の章頭は (i) Part 1 連続式との結合 → (ii) ch13 production stack tcolorbox 表 → (iii) IMEX 3 形式分類 → (iv) 項別 5 itemize → (v) 節構成 listing という **5 段の前置き**を持ち、CHK-228 で指摘された §11 のような「巨大 algbox」は無い。

各 §7.3-§7.7 は **「production の選択 + 安定性 + 精度」の triple**を持つ統一 schema で書かれており、章としての構造的均質性は高い。

### G-2. 弱点: 「production」と「比較研究」の境界レイヤが薄い

§7 内で "ch13 production stack" の語が頻出するが、`sec:viscous_cn_defect_v7` が production の外側であることは L574-575 の **1 文のみで分離** され、subsection title の括弧内補足にしか反映されない。

CHK-228 で §11 review が指摘した「Level 1/2/3 分類削除残存」と類似の構造的欠陥が、§7 では「比較研究 sec の混在」という形で再発している。改善余地: **「§7.4 production = implicit-BDF2」と「§7.4.1 比較研究 = CN」を別 subsection として明示分離**。

### G-3. 装飾: CHK-NNN migration markers が公開状態で残置

[paper/sections/07_time_integration.tex:2](../../paper/sections/07_time_integration.tex#L2): `% §7 (CHK-223 NEW; 旧 §5 + 移行 5 件): ...`
[paper/sections/07_time_integration.tex:262](../../paper/sections/07_time_integration.tex#L262): `% label 名は §10_3 等の外部参照保護のため保持（CHK-222 で rename 検討）`
[paper/sections/07_time_integration.tex:331](../../paper/sections/07_time_integration.tex#L331): `% Migrated from 07d_cls_stages.tex L128-143 (CHK-223 Phase 4.2)`
[paper/sections/07_time_integration.tex:571](../../paper/sections/07_time_integration.tex#L571): `% Migrated from 07e_viscous_3layer.tex L185-220 (CHK-223 Phase 4.2)`
[paper/sections/07_time_integration.tex:673](../../paper/sections/07_time_integration.tex#L673): `% 旧 §5.5 subsection 本文は CHK-222 で除去．label のみ後方互換のため保持．`
[paper/sections/07_time_integration.tex:937](../../paper/sections/07_time_integration.tex#L937): `% Migrated from 07b_reinitialization.tex L435-468 (CHK-223 Phase 4.3)`

これらは LaTeX comment であり PDF 出力には現れないため publication blocker ではないが、 **journal submission 直前の sweep 対象**としてマーク。

### G-4. その他 MINOR narrative 点

- L349 で IPC を「§\ref{sec:ipc_derivation}（**§7.5**）」と hardcode しているが、現 paper では IPC は **§7.6** (sec:ipc_derivation の親 subsection 番号)。確認: `\input{}` 順序を main.tex で確認すると §7.5 = sec:time_csf, §7.6 = sec:ipc_derivation。**hardcode "§7.5" は誤り**。修正: 「§\ref{sec:ipc_derivation}」のみで parens hardcode 削除。
- L686 のコメント `% Phase 6: §5.6 として 界面張力後・浮力前に配置` は CHK-223 章再編前の旧 §5.6 番号残置。

---

## Section H: 再構成 options 3 案

### Option α — 最小修正 (publication-blocker のみ)

**対象**: C-2 (Pyo-Shen 引用欠落), C-3 (standard vs rotational IPC 論理), D-1 / D-2 / D-3 / D-4 (code §番号 + paper-code mismatch)、E-2 (表境界明確化)

**作業内容**:
- bibliography.bib に Pyo-Shen / Guermond-Quartapelle 系列追加 (~10 LOC)
- L727-729 書き換え (~5 LOC)
- code side: tvd_rk3.py / cfl.py / viscous_predictors.py docstring 修正 (3 ファイル × ~5 LOC)
- paper §7.4 に「現行 CN 実装は Heun」warnbox 追加 (~10 LOC)
- §7.8 表に CN 行追加 + 脚注で production/comparison 境界 (~5 LOC)

**LOC 推定**: paper +30 / code +15 / bib +10 = **総計 +55 LOC**
**影響 chapter**: §7 のみ修正、bibliography.bib のみ追加。他章への影響無し
**所要 effort**: 2-3 hours
**残存 finding**: B-1 (Helmholtz 対称性), B-2 (Lie splitting), B-3 (σ_max 数値計算), B-4 (C_cross), C-1 (HairerWanner Sec)、E-1 (third-order memo 言及), G-3 (CHK markers), G-4 (§7.5 hardcode) の 8 件 MINOR/MAJOR が残る

### Option β — 中規模再構成 (理論側 + 構造側 同時整理)

**対象**: B-1 ~ B-4 + C-1 ~ C-4 + D-1 ~ D-4 + E-1 ~ E-2 + G-2 + G-4 (計 14 件 / FATAL 0)

**作業内容**:
- Option α 全件
- §7.4 を「§7.4 implicit-BDF2 (production)」+「§7.4.1 比較: CN (Heun corrector)」に再構成 (~50 LOC)
- §7.1 L146-148 の Lie splitting 主張を §7.6 IPC への forward-ref と Marchuk citation 付きで書き換え (~15 LOC)
- L435 の Helmholtz 演算子記述を「変密度に伴う非対称性 → GMRES」に書き換え (~10 LOC)
- App. D.1 に dispersion curve figure 追加 (~30 LOC; 図要画像生成)
- App. D.1/D.2 に C_cross / C_σ の値定義 (~20 LOC)
- §7.8 末尾に「O(Δt³) への展望と O(Δt²) 設計判断」paragraph 追加 (~30 LOC)
- §7 内 L349 etc の §番号 hardcode を全削除 (~10 LOC)

**LOC 推定**: paper +200 / code +15 / bib +10 / fig +1 PDF = **総計 +225 LOC + 1 図**
**影響 chapter**: §7 + App.D 主体。§14 (val_capillary) と §15 (future_work) への back-link 修正
**所要 effort**: 1-2 days
**残存 finding**: G-3 (CHK marker comment 残置) のみ MINOR

### Option γ — 全面書き直し (Route B 連動)

**対象**: §7 全体を「Route B (AB3 + Richardson-CN + rotational IPC) で O(Δt³)」前提に書き換え

**前提条件**: third-order memo の Route B 実装 (richardson_cn.py 拡張 + AB3 buffer + rotational IPC) が **完了済み**であること。現状未実装 (memo 自身が "theory only. Implementation is a separate future effort." と明記)

**作業内容**:
- まず Route B を src/twophase/ に実装 (~80 LOC + 3 experiment file)
- §7 全 sub-section を AB3 / Richardson-CN / rotational IPC 前提に書き換え (~500 LOC)
- §7 章タイトルを「時間積分 (O(Δt³))」に変更
- §14 ベンチマークで O(Δt³) 検証実験を追加 (~3 figures)

**LOC 推定**: paper +500 / code +80 / experiment +200 = **総計 +780 LOC**
**影響 chapter**: §7 全面 + §14 主要 + §1 (introduction)・§15 (conclusion) で精度主張更新 + ch13 production stack の再 freeze
**所要 effort**: 1-2 weeks
**Risk**: memo が flagged R1 (AB3 imaginary axis instability) と R2 (rotational IPC near-interface amplification) が解決しない可能性

**Reviewer 推奨**: **Option α または β** (γ は scope 外 — 別 CHK で扱うべき)

---

## Section I: User 判断要請

### Q1. **Option α / β / γ の選択は？**
α (最小、2-3h, MAJOR 6 件解決) / β (中規模、1-2d, MAJOR 全件解決) / γ (全面書き直し、1-2w, Route B 実装込み) の 3 択。reviewer 推奨は **β** (12 件 MAJOR を全件解決し、Route B 展望は paper 内 forward-ref で扱う)。

### Q2. **Pyo-Shen / Guermond-Quartapelle 系列の \cite{} key は何を採用するか？**
候補: `\cite{PyoShen2007}` (2007 J. Comput. Phys.), `\cite{GuermondQuartapelle1998}` (Numer. Math.) など。bibliography.bib 既存 entry の有無を確認したうえで命名統一が必要。reviewer は具体 entry を bib に登録する権限が無いため、user が候補を確定する必要あり。

### Q3. **§7.4 sec:viscous_cn_defect_v7 を「比較研究」明示する書き換えは可か？**
現状 production = implicit-BDF2、比較研究 = CN という境界が L574-575 の 1 文のみ。これを §7.4.1 として subsection 切り出しするか、warnbox 1 つで明示する程度に留めるかの選択。

### Q4. **CHK-NNN migration marker (6 件) 削除タイミングは？**
今回の CHK-240 修正と同時に sweep するか、journal submission 直前の独立 CHK で扱うか。reviewer 推奨は **同時 sweep** (Option β に含める)。

---

## Section J: ch13 production stack との fact-check

### J-1. paper 記述と実装の一致点 (PR-5 OK)

| paper 記述 | 実装位置 | 状態 |
|---|---|---|
| TVD-RK3 Shu-Osher 係数 (3/4, 1/4, 1/3, 2/3) | [tvd_rk3.py:45-47](../../src/twophase/time_integration/tvd_rk3.py#L45-L47) | ✓ paper-exact |
| BDF2 履歴係数 (4/3, -1/3) | [viscous_predictors.py:212-213](../../src/twophase/simulation/viscous_predictors.py#L212-L213) | ✓ paper-exact |
| BDF2 投影係数 γ = 2/3 | [viscous_predictors.py:18](../../src/twophase/simulation/viscous_predictors.py#L18) (`IMPLICIT_BDF2_PROJECTION_FACTOR = 2.0 / 3.0`) | ✓ paper-exact |
| Velocity-PPE ordering (Predictor → PPE → Corrector) | [_core.py:123-163](../../src/twophase/simulation/_core.py#L123-L163) | ✓ §7.3 sec:cls_velocity_consistency_v7 と整合 |
| 毛管 CFL (Denner-van Wachem 形式) | [cfl.py:78](../../src/twophase/time_integration/cfl.py#L78) | ✓ App. D.2 eq:dt_sigma と整合 |
| Directional Courant sum | [cfl.py:111](../../src/twophase/time_integration/cfl.py#L111) | ✓ §7.9 eq:dt_adv と整合 |

### J-2. paper 記述と実装の乖離 (PR-5 緊張 — 既出)

| paper 記述 | 実装位置 | 乖離 |
|---|---|---|
| §7.4 eq:viscous_cn_helmholtz_v7 (true implicit CN) | [picard_cn.py](../../src/twophase/time_integration/cn_advance/picard_cn.py) (Heun corrector) | **D-4 既出 MAJOR** |
| §7.3 eq:tvd_rk3 | tvd_rk3.py:4 docstring `§8 Eq. 79–81` | **D-1 既出 MAJOR** |
| §7.9 eq:dt_per_term | cfl.py:4 docstring `§8 (Eq. 84)` | **D-2 既出 MAJOR** |
| §7.3 eq:predictor_imex_bdf2 | viscous_predictors.py:195-225 (paper-eq citation 完全欠落) | **D-3 既出 MAJOR** |

### J-3. paper に書かれない実装 magic number (paper-trace 欠落 — 公開時 risk)

| 実装値 | 位置 | paper 内記述 |
|---|---|---|
| `_TVD_RK3_SAFETY = 0.5` | [reinitialize.py:178](../../src/twophase/levelset/reinitialize.py#L178) | **無し** (§7.9 sec:time_guide も触れず) |
| `cfl=0.5` (FieldExtender) | [field_extender.py:60](../../src/twophase/levelset/field_extender.py#L60) | **無し** |
| `C_τ = 2.0` (PPE pseudo-time LTS) | [iim_solver.py:89](../../src/twophase/ppe/iim_solver.py#L89) | **無し** (§7.9 言及のみ; 値は §13 委譲) |
| GMRES `tolerance=1e-8` | [viscous_predictors.py:155-157](../../src/twophase/simulation/viscous_predictors.py#L155-L157) | **無し** (§7.4 L443-446 では「具体的な収束反復回数や restart 値の設計は検証章 §sec:val_summary に委ねる」とのみ) |
| GMRES `max_iterations=80, restart=40` | 同上 | **無し** (§14 委譲) |
| PPE defect-correction `max_corrections=3, tolerance=1e-8` | [defect_correction.py:39-40](../../src/twophase/ppe/defect_correction.py#L39-L40) | §7.6 L735 で「2-3 反復」と paper 内に範囲記述あり (一部 trace 可) |

**Reviewer 判断**: GMRES tol/iter/restart は paper §7.4 で「§14 委譲」と書かれているため OK。ただし **`_TVD_RK3_SAFETY = 0.5` と `C_τ = 2.0` は paper §7.9 に対応記述が無く、再現性の観点で MINOR risk**。

### J-4. 結論

PR-5 fidelity の judgement: **production 部分は paper-exact** (J-1)、**比較研究 (CN) は paper-code 乖離** (J-2 D-4)、**docstring §番号は systemic obsolete** (J-2 D-1, D-2, D-3)、**magic number は概ね trace 可だが §7.9 で補足する余地あり** (J-3)。

**ch13 production stack それ自体の正しさ** には reviewer として疑義を持たない。Option α/β を実施することで paper-code transparency が改善する。

---

## Section K: assistant の advisory

### K-1. 優先度ランキング (修正実施順序の推奨)

1. **D-1 / D-2 / D-3 (code docstring §番号)** — 機械的 sweep で 30 分以内、PR-5 audit の最低ライン回復
2. **C-2 / C-3 (Pyo-Shen \cite{} 欠落 + standard vs rotational IPC 論理)** — publication blocker。bibliography 確定後に L727-729 書き換え
3. **D-4 (CN paper-code 乖離)** — paper §7.4 への warnbox 追加で transparency 担保
4. **B-1 (Helmholtz 対称性)** — 1 行修正だが mathematical correctness の核
5. **E-1 / E-2 (third-order memo + 表境界)** — Option β でまとめて
6. **B-2 / B-3 / B-4 (Lie splitting / σ_max / C_cross)** — App. D 補強で対処
7. **C-1 / G-3 / G-4 (HairerWanner Sec / CHK marker / hardcode §)** — sweep 系 MINOR

### K-2. 査読者として「PASS にしない」理由の核心

CHK-227 / CHK-228 と同様、**FATAL は無く章としての理論的価値は高い**が、以下の 3 点で major revision を求める:
1. **A3 / PR-5 systemic violation** (D-1, D-2, D-3): code docstring の §番号が paper rename に追従していない。PR-5 audit の「paper-code 同一参照」前提が崩れている。
2. **load-bearing claim の citation 欠落** (C-2): variable-density IPC の O(Δt²) 主張を裏付ける Pyo-Shen / Guermond-Quartapelle が \cite{} key 無しで人名のみ。これは reviewer として「論文として最低限引用が辿れること」の基準を満たさない。
3. **production / comparison 境界の不明瞭** (D-4 + E-2 + G-2): paper を独立に読む読者が、ch13 production と CN 比較研究を区別できない。誤実装が起こり得る。

### K-3. 査読者として評価する点

CHK-227 (§9) と CHK-228 (§11) の review が指摘した「Level 分類削除残存」「巨大 algbox」「YAML 実装の話」のような構造的欠陥は §7 には **無い**。章頭 tcolorbox 表 → 形式分類 → 剛性 map → 項別 5 節 → 全体精度表 → Δt 合成式 という arc は CHK-216 ch4 review でほめられた arc と同等以上に強固であり、**§7 章の根本的な書き直しは不要**。Option α/β で十分に publication-ready になる。

特に §7.6 IPC proof sketch (L705-723) と §7.8 表脚注 † (界面粘性クロス項 O(Δt) 開示) は **reviewer として高く評価する誠実な記述**。後者は多くの paper が隠蔽する「想定外の精度劣化」を表に明示しており、再現性の観点で模範的。

---

## 付録 A: §7 + App. D 構造マップ

| Line | Label | Title | 重要度 |
|---|---|---|---|
| 7-9 | `ch:time_integration` / `sec:time_int` | 時間積分スキーム — 項別設計と ch13 production stack | 章 root |
| 82-83 | `sec:time_accuracy_principle` | §7.1 時間積分形式の分類と精度整合性 | sub root |
| 113-114 | `sec:time_accuracy_lax` | (subsubsection*) 精度整合性と零安定性 | |
| 151-153 | `sec:time_operator_stiffness` | §7.2 演算子別剛性マップ | sub root |
| 188-190 | `sec:cfl_definitions` | (subsubsection*) CFL 数と固有値マップ | |
| 225-227 | `sec:von_neumann` | (subsubsection*) von Neumann 解析と安定領域分類 | |
| 260-262 | `sec:time_level1` | §7.3 移流項：CLS 用 TVD-RK3 + NS 用 IMEX-BDF2 | sub root |
| 327-330 | `sec:cls_velocity_consistency_v7` | (subsubsection) 速度--PPE 整合性 | |
| 415-416 | `sec:time_viscous` | §7.4 粘性項：implicit-BDF2 (GMRES) | sub root |
| 566-570 | `sec:viscous_cn_defect_v7` | (subsubsection) CN 粘性 Helmholtz とデフェクト補正 | **比較研究** |
| 611-613 | `sec:time_csf` | §7.5 界面張力項：PPE 内蔵 jump-decomposed CSF | sub root |
| 685-687 | `sec:ipc_derivation` | §7.6 圧力投影：IPC + FCCD PPE | sub root |
| 750-753 | `sec:time_buoyancy` | §7.7 浮力項：balanced-buoyancy | sub root |
| 821-822 | `sec:time_accuracy_table` | §7.8 全体時間精度 (`tab:time_accuracy_prod`) | **集約表** |
| 875-878 | `sec:time_guide` / `sec:dt_synthesis` / `sec:stability` | §7.9 時間刻みガイド：項別律速合成 (`eq:dt_per_term`) | **集約式** |
| 933-936 | `warn:cls_dtau_stability_v7` | (subsubsection) CLS 再初期化の擬似時間安定性（旧実装） | warnbox |

| App. D ファイル | Label | 内容 |
|---|---|---|
| `appendix_advection.tex` | `app:stability_constraints` | 安定性制約 (wrapper) |
| `appendix_stability_analysis.tex` | `app:stability_derivation` | D.1 TVD-RK3 + DCCD 安定性 (47 lines) |
| `appendix_numerics_solver_s1.tex:1` | `app:capillary_cfl` | D.2 毛管波制約の導出 |
| `appendix_numerics_solver_s1.tex:51` | `app:grid_ale` | D.3 時間変化格子と ALE 効果 (本稿では未実装) |

---

## 付録 B: 各 finding の line-cite 詳細表

| ID | 重大度 | file:line | verbatim quote (要点) | 修正提案 |
|---|---|---|---|---|
| **B-1** | MAJOR | [07_time_integration.tex:435](../../paper/sections/07_time_integration.tex#L435) | "$A = I - \gamma\Delta t\,\mathcal{L}_{\nu}$ は対称正定値" | 「(重み付き内積で) 対称正定値」or 「変密度のため非対称、GMRES 採用」に修正 |
| **B-2** | MAJOR | [07_time_integration.tex:146-148](../../paper/sections/07_time_integration.tex#L146-L148) | "Lie splitting...splitting 誤差は $\Ord{\Delta t^2}$" | §7.6 への forward-ref + Marchuk 引用追加 |
| **B-3** | MAJOR | [appendix_stability_analysis.tex:35-38](../../paper/sections/appendix_stability_analysis.tex#L35-L38) | "$\sigma_{\max} = \sqrt{3}/1.9 \approx 0.91$ ... 数値計算による" | dispersion curve figure or script ref を App.D.1 に追加 |
| **B-4** | MAJOR | [07_time_integration.tex:497-501](../../paper/sections/07_time_integration.tex#L497-L501) | "$C_{\mathrm{cross}} = O(1)$" | 数値見積もり derivation を App.D に追加 |
| **C-1** | MINOR | [07_time_integration.tex:256](../../paper/sections/07_time_integration.tex#L256) vs L397/L449 | "Sec.~V" vs "Sec.~V.1" | 三箇所を Sec. V.1 に統一 |
| **C-2** | MAJOR | [07_time_integration.tex:729](../../paper/sections/07_time_integration.tex#L729) | "Pyo--Shen / Guermond--Quartapelle 系列を参照" | bibliography 登録 + \cite{} key 引用 |
| **C-3** | MAJOR | [07_time_integration.tex:727-729](../../paper/sections/07_time_integration.tex#L727-L729) | "Guermond...§6.2 (rotational pressure correction)...本節の精度評価は変密度下でも保たれる" | citation source を standard IPC 結果論文に変更 or 補助 lemma 明示 |
| **C-4** | MINOR | [appendix_numerics_solver_s1.tex:31](../../paper/sections/appendix_numerics_solver_s1.tex#L31) | "CFL 安全係数 $C_\sigma < 1$ で補正" | $C_\sigma$ の定義を App.D.2 に追加 |
| **D-1** | MAJOR | [tvd_rk3.py:4](../../src/twophase/time_integration/tvd_rk3.py#L4) | "Implements §8 (Eq. 79–81)" | `§7.3 eq:tvd_rk3` に修正 |
| **D-2** | MAJOR | [cfl.py:4](../../src/twophase/time_integration/cfl.py#L4) | "Implements §8 (Eq. 84)" | `§7.9 eq:dt_per_term` に修正 |
| **D-3** | MAJOR | [viscous_predictors.py:195-225](../../src/twophase/simulation/viscous_predictors.py#L195-L225) | (BDF2 係数 inline, paper-eq citation 無し) | `§7.3 eq:predictor_imex_bdf2 + §7.4 eq:helmholtz_implicit_bdf2` を docstring 追加 |
| **D-4** | MAJOR | [picard_cn.py:1-22](../../src/twophase/time_integration/cn_advance/picard_cn.py#L1-L22) vs [07_time_integration.tex:577-582](../../paper/sections/07_time_integration.tex#L577-L582) | paper = true CN, code = Heun (非 A-stable) | paper §7.4 に warnbox「現行実装は Heun」追加 |
| **E-1** | MAJOR | [07_time_integration.tex:971](../../paper/sections/07_time_integration.tex#L971) ([memo](../2026-04-18_third_order_time_integration.md)) | `\S\ref{sec:future_work}` への single forward-ref のみ | §7.8 末尾に「O(Δt³) 展望と O(Δt²) 設計判断」paragraph 追加 |
| **E-2** | MAJOR | [07_time_integration.tex:828-849](../../paper/sections/07_time_integration.tex#L828-L849) | `tab:time_accuracy_prod` に CN 行無し | 表に「CN (比較研究)」行追加 + production/comparison 境界明示 |
| **G-3** | MINOR | L2, L262, L331, L571, L673, L937 | `% CHK-NNN ...` migration markers 6 件 | journal submission sweep |
| **G-4-1** | MINOR | [07_time_integration.tex:349](../../paper/sections/07_time_integration.tex#L349) | `\S\ref{sec:ipc_derivation}（§7.5）` (実際は §7.6) | parens hardcode 削除 |
| **G-4-2** | MINOR | [07_time_integration.tex:686](../../paper/sections/07_time_integration.tex#L686) | `% Phase 6: §5.6 として 界面張力後・浮力前に配置` | 旧章番号削除 |
| **J-3** | MINOR | [reinitialize.py:178](../../src/twophase/levelset/reinitialize.py#L178), [iim_solver.py:89](../../src/twophase/ppe/iim_solver.py#L89) | `_TVD_RK3_SAFETY = 0.5`, `C_τ = 2.0` | §7.9 で補足 or code docstring に paper-trace 追加 |

**Severity 集計**: FATAL 0 / **MAJOR 12** (B-1〜B-4, C-2, C-3, D-1〜D-4, E-1, E-2) / MINOR 7 (C-1, C-4, G-3, G-4-1, G-4-2, J-3 + 1 implicit)

---

## 付録 C: A3 traceability matrix (5 scheme × code-path × test × paper-eq)

| Scheme | code 主モジュール | code docstring の §引用 | 正しい paper §引用 | unit test | A3 状態 |
|---|---|---|---|---|---|
| TVD-RK3 | [tvd_rk3.py](../../src/twophase/time_integration/tvd_rk3.py) | `§8 Eq. 79-81` | **§7.3 eq:tvd_rk3** | `test_tvd_rk3_temporal_order` (引用も誤; `§4 / §9 eq:tvd_rk3`) | **NG (D-1)** |
| IMEX-BDF2 | [viscous_predictors.py](../../src/twophase/simulation/viscous_predictors.py) | (無し) | **§7.3 eq:predictor_imex_bdf2 + §7.4 eq:helmholtz_implicit_bdf2** | `test_imex_bdf2_predictor_uses_ext2_and_projection_dt` | **NG (D-3)** |
| CN (Picard/Heun) | [picard_cn.py](../../src/twophase/time_integration/cn_advance/picard_cn.py) | `extended_cn_impl_design.md §1.2` (内部 memo) | **§7.4 eq:viscous_cn_helmholtz_v7** だが実装は Heun (D-4) | `test_cn_mode_factory_picard` (smoke のみ) | **NG (D-4 + 順序試験欠落)** |
| PPE Defect-Correction | [defect_correction.py](../../src/twophase/ppe/defect_correction.py) | `§9 variable-density PPE` (chain) | §7.6 L731-740 で言及 (PPE 用)、**§7.4 sec:viscous_cn_defect_v7** とは別 | `test_fvm_defect_correction_with_direct_base_matches_direct_fvm` | **△ (PPE 用は OK、CN 粘性用 defect-correction 実装は別途)** |
| Velocity-PPE ordering | [_core.py](../../src/twophase/simulation/_core.py) | `§9.1 Eq. 85-94` (古い) + `§7.1 Eq. 57` + `§7.3 Eq. 62-63` + `§7.4 Eq. 65` (PPE/RC modules) | **§7.3 sec:cls_velocity_consistency_v7** | `test_pressure_projection_uses_projection_dt`, `test_step_uniform_no_nan` | **△ (一部 OK、`§9.1` は obsolete)** |
| CFL (pseudo-time) | [cfl.py](../../src/twophase/time_integration/cfl.py) | `§8 Eq. 84` + `§8.4 Eq.(dt_sigma)` | **§7.9 eq:dt_per_term + eq:dt_sigma + App.D.2 app:capillary_cfl** | `test_dt_max_uses_directional_courant_sum`, `test_dt_max_capillary_wave_bound_uses_h_min` | **NG (D-2)** |

**A3 audit 結果**: 6 schemes 中 **NG 4 / △ 2 / OK 0**。**CHK-225 で paper rename を実施したが、code docstring の §番号 sweep が伴っていない**。これは reviewer から見ると PR-5 audit の最低ラインを下回る systemic 不整合。

---

## 付録 D: §7 outbound \ref impact range

§7 内記述を **outbound 参照**している他章 (§7 修正による影響範囲):

| 参照元 | line | 参照先 (§7 内 label) | 影響 |
|---|---|---|---|
| [05_reinitialization.tex:19, 28, 447-448](../../paper/sections/05_reinitialization.tex#L19) | 4 件 | `ch:time_integration`, `warn:cls_dtau_stability_v7`, `sec:dt_synthesis` | §7 reinit pseudo-time 議論への delegation |
| [05b_cls_stages.tex:84, 91, 136, 142](../../paper/sections/05b_cls_stages.tex#L84) | 4 件 | `eq:cls_tvd_rk3_psi`, `sec:cls_velocity_consistency` | TVD-RK3 / velocity-PPE ordering の正本 location |
| [06_scheme_per_variable.tex:24, 85, 96](../../paper/sections/06_scheme_per_variable.tex#L24) | 3 件 | `ch:time_integration`, `sec:cls_velocity_consistency_v7` | 時間結合の delegation |
| [06d_viscous_3layer.tex:8, 204, 219, 235, 251, 305](../../paper/sections/06d_viscous_3layer.tex#L8) | 6 件 | `sec:viscous_cn_defect_v7`, `sec:time_viscous` 系 | CN/defect-correction + ρ/μ ordering |
| [08b_pressure.tex:2, 108](../../paper/sections/08b_pressure.tex#L2) | 2 件 (header comment) | §7.2, §7.5 対応位置 | header documentation のみ |
| [08c-08f_*.tex](../../paper/sections/08c_bf_failure.tex) | 4 ファイル (header) | §7.2.0, §7.3, §7.5 | comment のみ、本文 \ref 無し |
| [12_component_verification.tex:9](../../paper/sections/12_component_verification.tex#L9) | 1 件 | `sec:impl_collocate` (backward compat) | 既 deprecated label |
| [appendix_pressure.tex:3, 23](../../paper/sections/appendix_pressure.tex#L3) | 2 件 (header comment) | §7-8 対応 | header documentation のみ |

**Reviewer 結論**: §7 内 label の outbound impact は **5 章 (§5, §5b, §6, §6d, §8b) + 1 appendix (App.E)** に渡る。Option α/β で §7 内 label rename を行わない場合、outbound 影響は無い。Option γ で大規模再構成すれば label rename 必須となり、上記 5 章への一括 sweep が必要。

---

> 査読所要時間: 約 4 時間 (Phase 1 並列 Explore + Phase 2-5 直接照合 + Phase 6 執筆)
> 次の action: Section I の Q1-Q4 への user 回答待ち。回答後、Option α/β/γ いずれかで PaperWriter (or 担当 agent) が修正実施 → その後再 review 不要 (本 review で finding 集約完了)。
