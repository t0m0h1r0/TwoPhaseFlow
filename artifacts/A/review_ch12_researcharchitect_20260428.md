# Strict Peer Review — Chapter 12 (Component Verification, U1–U9)

| Item            | Value                                                                  |
| --------------- | ---------------------------------------------------------------------- |
| Reviewer        | ResearchArchitect (acting as 査読官 — strict peer reviewer)            |
| Date            | 2026-04-28                                                              |
| Worktree        | `worktree-ra-ch12-13-review-20260428`                                  |
| Session id      | `CHK-RA-CH12-001`                                                      |
| Rubric          | `prompts/agents-claude/PaperReviewer.md` (FATAL / MAJOR / MINOR; AP-01) |
| Pass condition  | 0 FATAL + 0 MAJOR                                                      |
| Files reviewed  | `paper/sections/12_component_verification.tex`, `12u1`–`12u9`, `12h_summary.tex` (11 files) |
| Cross-checks    | `experiment/ch12/exp_U1..U9*.py`, `experiment/ch12/results/*/data.npz` (selected) |

---

## Section A — Stance and per-file verdict

### Summary stance

Chapter 12 contains **two parallel and mutually-contradictory arithmetic narratives**. The nine sub-experiment files [12u1_ccd_operator.tex](paper/sections/12u1_ccd_operator.tex)–[12u9_dccd_pressure_prohibition.tex](paper/sections/12u9_dccd_pressure_prohibition.tex) are internally honest: tables, figure captions, and evaluation prose all agree with the underlying experiment outputs. The summary file [12h_summary.tex](paper/sections/12h_summary.tex), however, presents a **separate set of numbers** in `tab:verification_summary` that contradicts the sub-files in **eight independent rows**, and then propagates those contradicted numbers into the concluding `tcolorbox`. Multiple summary rows describe experiments that **do not exist** in the corresponding sub-file (U4 "再初期化界面シフト累積 ≈7.6 倍", U9 "200-step で寄生流れ噴出"). Most of the contradicted numbers look like **stale values from before the CHK-256 / CHK-244 / CHK-242 rerun** that propagated unchanged into the summary table.

Separately, [12u4_ridge_eikonal_reinit.tex](paper/sections/12u4_ridge_eikonal_reinit.tex) describes a Ridge-Eikonal Hamilton-Jacobi pseudo-time flow with iteration count `n_τ`, while [exp_U4_ridge_eikonal_reinit.py:44](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L44) imports `godunov_sweep` from `reinit_eikonal_godunov`. The exp_U4 docstring at lines 17-21 explicitly acknowledges the substitution: *"The codebase's RidgeEikonalReinitializer is single-shot FMM (no n_tau); ... so it's not the right primitive for the paper's "n_tau convergence" claim."* This is an **explicit, documented PR-5 (Algorithm Fidelity) violation** confessed in the experiment source itself.

### Per-experiment one-line verdicts

| File           | Verdict       | Notes                                                                  |
| -------------- | ------------- | ---------------------------------------------------------------------- |
| 12_component_verification.tex | PASS  | Tier I–VII framework reasonable; tab:U_summary 23-test count consistent |
| 12u1 (CCD ops) | △ conditional | U1-c FCCD result internally consistent (4.00, conditional △), but cross-reference to U3-b is broken (F-12-13) |
| 12u2 (Poisson) | PASS          | Internally consistent; minor expected-vs-12h_summary mismatch (M-12-1) |
| 12u3 (non-uniform) | PASS      | Internally consistent (5.98 / 4.00 / 4.09 / D₁–D₄ machine-zero)        |
| 12u4 (reinit)  | **FAIL**      | PR-5 violation: paper claims Ridge-Eikonal, code uses Godunov sweep (F-12-12) |
| 12u5 (Hδ)      | PASS          | Internally consistent                                                  |
| 12u6 (PPE+DC+HFE) | △          | Internally consistent in tables; but evaluation prose 5.05 vs table 5.10 (M-12-2) |
| 12u7 (BF)      | PASS          | Internally consistent (0.6 % at N=128, slope 1.91/1.81/1.91)          |
| 12u8 (time int)| PASS          | Internally consistent (3.00 / 2.04 / 2.00 / Layer A 2.0 / B,C 1.0)     |
| 12u9 (DCCD prohibition) | PASS | Negation test framing clear; internally consistent (ratio 2.66e5 → 6.55e7) |
| **12h_summary** | **FAIL** | **8 of 23 rows in `tab:verification_summary` contradict the sub-files** (F-12-1 through F-12-9); concluding `tcolorbox` propagates the false numbers (F-12-10) |

### Overall ch12 verdict — **FAIL**

- 13 FATAL / 5 MAJOR / 5 MINOR.
- The PASS condition (0 FATAL + 0 MAJOR) is **not met**.
- The 13 FATAL findings are concentrated in two locations: (a) [12h_summary.tex](paper/sections/12h_summary.tex) (12 of 13), and (b) [12u4_ridge_eikonal_reinit.tex](paper/sections/12u4_ridge_eikonal_reinit.tex) ↔ [exp_U4](experiment/ch12/exp_U4_ridge_eikonal_reinit.py) algorithm-fidelity gap (1 of 13).
- The other nine sub-experiment files are paper-ready in isolation, so the recommended fix routing is targeted: rewrite [12h_summary.tex](paper/sections/12h_summary.tex) `tab:verification_summary` and concluding `tcolorbox` against the actual U1–U9 outputs, then either (i) align [12u4](paper/sections/12u4_ridge_eikonal_reinit.tex) text with the Godunov-sweep code path or (ii) refit the experiment to actually use `RidgeEikonalReinitializer`.

---

## Section B — FATAL findings

> Each finding cites file:line + verbatim quote (AP-01).

### F-12-1 (FATAL): 12h_summary U3-b row contradicts 12u3 measured slope by ~38 %

[paper/sections/12h_summary.tex:41](paper/sections/12h_summary.tex#L41) states:
> ```
> U3-b & FCCD non-uniform face   & $\Ord{h^5}$ 以上          & $\Ord{h^{5.5}}$        & \checkmark
> ```

[paper/sections/12u3_nonuniform_spatial.tex:83](paper/sections/12u3_nonuniform_spatial.tex#L83) (the underlying experiment table tab:U3_fccd_nonuniform) shows:
> ```
> \multicolumn{2}{r}{slope} & $\mathbf{4.00}$ & $\mathbf{4.09}$ \\
> ```

[paper/sections/12u3_nonuniform_spatial.tex:71](paper/sections/12u3_nonuniform_spatial.tex#L71) caption confirms the design:
> *「均一格子 U1-c と同様に 4 次律速を示す」*

[paper/sections/12u3_nonuniform_spatial.tex:122](paper/sections/12u3_nonuniform_spatial.tex#L122) evaluation:
> *「U3-b FCCD 非一様：slope $4.00$（face value）/ $4.09$（face grad）」*

Both the **expected ($\Ord{h^5}$ 以上)** and **measured ($\Ord{h^{5.5}}$)** values in the summary are wrong. The actual experiment is a 4-th order operator that hits 4.00/4.09 — well below the summary's claim. Severity FATAL because the result claim is unsupported by the cited data and contradicts the paper's own sub-section.

### F-12-2 (FATAL): 12h_summary U6-b ρ-ratio claim "$\Ord{h^{7.0}}$ 全 ρ 比で同一" directly contradicts 12u6

[paper/sections/12h_summary.tex:54](paper/sections/12h_summary.tex#L54):
> ```
> U6-b & Split-PPE $\rho$-ratio 1:1--1:1000 & $\Ord{h^7}$（液相内部）& $\Ord{h^{7.0}}$ 全 $\rho$ 比で同一 & \checkmark
> ```

[paper/sections/12u6_split_ppe_dc_hfe.tex:99](paper/sections/12u6_split_ppe_dc_hfe.tex#L99) figure caption:
> *「高密度比 $\rho_l = 1000$ で N--sweep slope $\approx 0.78$（lumped--PPE 構造的制約）」*

[paper/sections/12u6_split_ppe_dc_hfe.tex:53-56](paper/sections/12u6_split_ppe_dc_hfe.tex#L53-L56) table caption:
> *「高密度比では DC が $\Ord{h^{0.5\text{--}1.0}}$ で律速（lumped--PPE の構造的限界； §\ref{sec:varrho_ppe_limitation} の議論と整合）」*

[paper/sections/12u6_split_ppe_dc_hfe.tex:111-114](paper/sections/12u6_split_ppe_dc_hfe.tex#L111-L114) evaluation:
> *「U6-b $N/\rho$ sweep：高密度比 $\rho_l=1000$ では slope $\approx 0.78$（$N=32 \to 128$）に律速．これは **lumped--PPE の構造的制約**であり」*

The summary claims uniform $\Ord{h^7}$ across all ρ-ratios; the sub-file says the slope **collapses to 0.78** at ρ=1000 and frames this as a known structural limit motivating the split-PPE switch. Order-of-magnitude wrong. FATAL.

### F-12-3 (FATAL): 12h_summary U6-c HFE 1D measured slope is reported as $\Ord{h^{7.0}}$ but 12u6 shows 5.91

[paper/sections/12h_summary.tex:55](paper/sections/12h_summary.tex#L55):
> ```
> U6-c & HFE 1D step extension  & $\Ord{h^6}$              & $\Ord{h^{7.0}}$（1D）   & \checkmark
> ```

[paper/sections/12u6_split_ppe_dc_hfe.tex:89](paper/sections/12u6_split_ppe_dc_hfe.tex#L89) (tab:U6_hfe slope row):
> ```
> \multicolumn{2}{r}{slope ($N\!=\!32\!\to\!256$)} & $\mathbf{5.91}$ & $\mathbf{5.10}$ & $\mathbf{3.21}$ \\
> ```

[paper/sections/12u6_split_ppe_dc_hfe.tex:75-76](paper/sections/12u6_split_ppe_dc_hfe.tex#L75-L76) table caption:
> *「**1D** は設計通り 6 次近傍（slope $\approx 5.91$, $N=32\!\to\!256$）」*

Summary measured value: 7.0 (with super-convergence implied). Actual: 5.91 (described as "6th-order near design"). FATAL — contradicts the cited table by more than one full order.

### F-12-4 (FATAL): 12h_summary U6-c HFE 2D measured slope and N-range are both wrong

[paper/sections/12h_summary.tex:56](paper/sections/12h_summary.tex#L56):
> ```
> U6-c & HFE 2D テンソル積       & $\Ord{h^6}$              & $\Ord{h^{5.8}}$（$N\le128$） & $\triangle$
> ```

[paper/sections/12u6_split_ppe_dc_hfe.tex:89](paper/sections/12u6_split_ppe_dc_hfe.tex#L89) actual 2D slopes (max / med):
> ```
> & $\mathbf{5.10}$ & $\mathbf{3.21}$ \\
> ```

[paper/sections/12u6_split_ppe_dc_hfe.tex:99-100](paper/sections/12u6_split_ppe_dc_hfe.tex#L99-L100) figure caption:
> *「2D band 診断は max $5.10$ / med $3.21$」*

[paper/sections/12u6_split_ppe_dc_hfe.tex:84-87](paper/sections/12u6_split_ppe_dc_hfe.tex#L84-L87) the underlying table goes to $N=256$, **not** $N\le128$.

The summary value 5.8 is between the actual 5.10 (max) and the misreported 7.0 — it appears to be an averaged or stale figure. The "$N\le128$" qualifier is also factually incorrect since the experiment does include N=256 data points. FATAL.

### F-12-5 (FATAL): 12h_summary U7-a $\Delta p$ relative-error range "0.16–0.31 %" contradicts 12u7

[paper/sections/12h_summary.tex:71](paper/sections/12h_summary.tex#L71):
> ```
> U7-a & BF 整合：$\Delta p=\sigma\kappa$ vs 計算値 & 相対誤差 ${<}1\%$ & $0.16$--$0.31\%$ & \checkmark
> ```

[paper/sections/12u7_bf_static_droplet.tex:42-49](paper/sections/12u7_bf_static_droplet.tex#L42-L49) (tab:U7_bf):
> ```
> $32$  & match    & $7.72$  & $0.930$    & $1.66\times 10^{-3}$ \\
> $32$  & mismatch & $7.94$  & $0.985$    & $1.75\times 10^{-3}$ \\
> $64$  & match    & $4.084$ & $0.0210$   & $7.57\times 10^{-5}$ \\
> $64$  & mismatch & $4.096$ & $0.0240$   & $8.45\times 10^{-5}$ \\
> $128$ & match    & $3.976$ & $0.00608$  & $2.99\times 10^{-5}$ \\
> $128$ & mismatch & $3.974$ & $0.00646$  & $3.18\times 10^{-5}$ \\
> ```

[paper/sections/12u7_bf_static_droplet.tex:34-37](paper/sections/12u7_bf_static_droplet.tex#L34-L37) caption:
> *「$N=32$ では under--resolved（$\Delta p$ 相対誤差 93\%）；$N \ge 64$ で 2\% 以下，$N=128$ で 0.6\% に到達．」*

The actual relative-error range across the experiment is **0.6 %–98.5 %** (across N=32, 64, 128 / match, mismatch). At the finest grid N=128 it is **0.6 %** (not 0.16 %). The value "0.16–0.31 %" appears nowhere in the sub-experiment. FATAL.

### F-12-6 (FATAL): 12h_summary U7-a parasitic-flow amplification "$10^3$–$10^6$ 倍" is unsupported by 12u7

[paper/sections/12h_summary.tex:72](paper/sections/12h_summary.tex#L72):
> ```
> U7-a & BF 不整合：寄生流れ増幅 & 整合比 ${\gg}1$ & $10^3$--$10^6$ 倍 & \checkmark \textsuperscript{‡}
> ```

[paper/sections/12u7_bf_static_droplet.tex:42-49](paper/sections/12u7_bf_static_droplet.tex#L42-L49) shows match/mismatch ‖u‖∞ values that are **within a few percent of each other** (e.g. N=64: match 7.57e-5 vs mismatch 8.45e-5 — ratio 1.12, **not** 10³). The "10³–10⁶ 倍" amplification figure does not appear anywhere in [12u7](paper/sections/12u7_bf_static_droplet.tex). FATAL.

### F-12-7 (FATAL): 12h_summary U4 row "再初期化界面シフト累積 ≈ 7.6 倍" describes an experiment that does not exist

[paper/sections/12h_summary.tex:47](paper/sections/12h_summary.tex#L47):
> ```
> U4   & 再初期化界面シフト累積 & $\sim 10$ 倍（理想） & $\approx 7.6$ 倍（$N{=}256$） & $\triangle$ \textsuperscript{(c)}
> ```

[paper/sections/12u4_ridge_eikonal_reinit.tex:18-27](paper/sections/12u4_ridge_eikonal_reinit.tex#L18-L27) defines exactly two sub-experiments:
> *「U4-a Ridge--Eikonal 反復回数 $n_\tau \in \{0,1,5,10,20,50,100\}$ ... U4-b DGR：初期 $\eps_{\eff}^{\mathrm{init}} = 2 h_{\min}$ ... target $\eps_{\eff}^{\star} = 1.5 h_{\min}$ への補正．」*

There is **no "interface-shift accumulation" experiment** in 12u4, no "≈ 7.6 倍" figure in any 12u4 table, and no $N=256$ result (the entire chapter runs at $N=128$ per [12u4_ridge_eikonal_reinit.tex:19](paper/sections/12u4_ridge_eikonal_reinit.tex#L19)). FATAL — fabricated row.

### F-12-8 (FATAL): 12h_summary U9 "200-step で寄生流れ噴出" mischaracterises the experiment type

[paper/sections/12h_summary.tex:67](paper/sections/12h_summary.tex#L67):
> ```
> U9   & DCCD-on-pressure 違反   & 発散誤差 $\Ord{h^2}$    & $\Ord{h^{2.0}}$（200-step で寄生流れ噴出） & \checkmark
> ```

[paper/sections/12u9_dccd_pressure_prohibition.tex:18-28](paper/sections/12u9_dccd_pressure_prohibition.tex#L18-L28) actually describes a **single-step gradient-ratio measurement** on a 2D MMS pressure field — not a 200-step time-marched experiment:
> *「2D MMS 圧力場 $p^\star = \sin(2\pi x)\sin(2\pi y)$ ... ベースライン：CCD（フィルタ無）で $\nabla^2 p$ を計算 ... 違反試行：DCCD（$\eps_d > 0$）で圧力を先に平滑化し，その後 $\nabla^2 \tilde p$ を計算 ... ratio $\mathcal{R} = L_\infty^{\mathrm{diff}} / L_\infty^{\mathrm{unfiltered}}$」*

There is no time-stepping, no "parasitic flow eruption", no 200-step run in [12u9](paper/sections/12u9_dccd_pressure_prohibition.tex). The "$\Ord{h^{2.0}}$" measured slope claim is also inconsistent with [12u9_dccd_pressure_prohibition.tex:36-37](paper/sections/12u9_dccd_pressure_prohibition.tex#L36-L37): *「ratio $\mathcal{R}$ は **$h$ 細分化で巨大化**」* (the ratio grows, not stays at $h^2$). FATAL.

### F-12-9 (FATAL): 12h_summary U3-a measured "前漸近 $p = 5.2$–$5.8$" contradicts 12u3 slope 5.98

[paper/sections/12h_summary.tex:39](paper/sections/12h_summary.tex#L39):
> ```
> U3-a & CCD on stretched grid + 2D $D_{xy}$ & $\Ord{h^6}$ & 前漸近 $p=5.2$--$5.8$ & $\triangle$ \textsuperscript{(a)}
> ```

[paper/sections/12u3_nonuniform_spatial.tex:63](paper/sections/12u3_nonuniform_spatial.tex#L63) (tab:U3_ccd_nonuniform):
> ```
> \multicolumn{2}{r}{slope ($N\!=\!16\!\to\!128$)} & $\mathbf{5.98}$ & $\mathbf{5.98}$ \\
> ```

[paper/sections/12u3_nonuniform_spatial.tex:120-121](paper/sections/12u3_nonuniform_spatial.tex#L120-L121) evaluation:
> *「U3-a CCD 非一様：slope $5.98$．設計 6 次の機械零域近接，**合格** \checkmark」*

The actual measured slope is 5.98 with a **clean ✓ pass**, both for α=1 and α=2. The summary's "5.2–5.8 △ (前漸近)" reflects an earlier rerun before CHK-256 / CHK-244 / CHK-242 — but the live sub-experiment now passes outright at 5.98. FATAL.

### F-12-10 (FATAL): The concluding tcolorbox propagates the false summary numbers verbatim

[paper/sections/12h_summary.tex:91-104](paper/sections/12h_summary.tex#L91-L104) repeats the now-disproved summary numbers as paper conclusions:
> *「**空間（非一様）：** 前漸近 $p = 5.2$–$5.8$（$\triangle$）」* (vs. actual 5.98 ✓)
>
> *「**圧力ソルバ：** 分相 PPE + DC $k = 3$ + HFE が 全密度比 $\rho_l/\rho_g = 1$–$1000$ で液相内部 $\Ord{h^{7.0}}$ Dirichlet を達成」* (vs. actual 0.78 at ρ=1000)
>
> *「**coupling：** BF 整合 Laplace 圧 $0.16$–$0.31\%$，不整合で寄生流れが $10^3$–$10^6$ 倍増幅」* (vs. actual 0.6 % at N=128, no amplification figure)

Three of the six summary bullets contain numbers that **do not exist** in the corresponding U-test outputs. FATAL. (Note: this finding is logically downstream of F-12-1..6,9, but it warrants its own catalog entry because the wrong numbers are already in the chapter's headline conclusions, where they are most likely to be cited by the reader.)

### F-12-11 (FATAL): 12h_summary U1-c "$\Ord{h^{6.0}}$ ✓" contradicts 12u1 4.00 conditional △

[paper/sections/12h_summary.tex:32](paper/sections/12h_summary.tex#L32):
> ```
> U1-c & FCCD face value/grad   & $\Ord{h^6}$              & $\Ord{h^{6.0}}$        & \checkmark
> ```

[paper/sections/12u1_ccd_operator.tex:89](paper/sections/12u1_ccd_operator.tex#L89) (tab:U1_fccd_uccd6):
> ```
> slope ($N\!=\!16\!\to\!128$) & $\mathbf{4.00}$ & $\mathbf{4.00}$ & $\mathbf{7.00}$ \\
> ```

[paper/sections/12u1_ccd_operator.tex:112-114](paper/sections/12u1_ccd_operator.tex#L112-L114) evaluation:
> *「U1-c FCCD：周期重複端点を含む MMS face 評価で実効 4 次（条件付き合格 $\triangle$;」*

The summary table promotes a 4.00 conditional-pass result to a 6.0 full-pass result. FATAL — contradicts the cited table by 50 % and changes the verdict symbol from △ to ✓.

### F-12-12 (FATAL): PR-5 / A3 violation — 12u4 claims Ridge-Eikonal but exp_U4 imports `godunov_sweep`

[paper/sections/12u4_ridge_eikonal_reinit.tex:11-13](paper/sections/12u4_ridge_eikonal_reinit.tex#L11-L13):
> *「Ridge--Eikonal 再初期化（§\ref{sec:eikonal_reinit}：擬似時間 $\tau$ 上の Hamilton--Jacobi PDE $\partial_\tau \phi + \mathrm{sgn}(\phi)(|\nabla\phi|-1) = 0$）」*

[paper/sections/12u4_ridge_eikonal_reinit.tex:93-95](paper/sections/12u4_ridge_eikonal_reinit.tex#L93-L95) A3 trace:
> *「再初期化擬似時間刻み定義（Hamilton--Jacobi 形）→ §\ref{sec:eikonal_reinit} 離散化 → \texttt{src/twophase/levelset/reinit\_eikonal.py} および \texttt{src/twophase/levelset/ridge\_eikonal\_reinitializer.py}；」*

[experiment/ch12/exp_U4_ridge_eikonal_reinit.py:44](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L44):
> ```python
> from twophase.levelset.reinit_eikonal_godunov import godunov_sweep
> ```

[experiment/ch12/exp_U4_ridge_eikonal_reinit.py:17-21](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L17-L21) (docstring — author confession):
> *"Reinit semantics: paper's "n_tau" maps to godunov_sweep's n_iter. The codebase's RidgeEikonalReinitializer is single-shot FMM (no n_tau); iterating FMM hits a band-floor ~0.36 set by ridge-extraction's eps_scale, so it's not the right primitive for the paper's "n_tau convergence" claim."*

The paper text and A3 traceability cite `RidgeEikonalReinitializer` and `reinit_eikonal.py`, while the actual code uses a different file (`reinit_eikonal_godunov.py`) and a different algorithm (`godunov_sweep`). The experiment author has explicitly documented in the docstring that the substitution was necessary because `RidgeEikonalReinitializer` cannot produce the paper's claimed n_τ-convergence behavior. This is **PR-5 Algorithm Fidelity** failure (paper-exact behavior is mandatory) and **A3 Traceability** failure (the equation→discretization→code chain points at a file that the experiment does not call). FATAL.

### F-12-13 (FATAL): 12u1 cross-reference "U3-b で別途検証" is broken

[paper/sections/12u1_ccd_operator.tex:113-114](paper/sections/12u1_ccd_operator.tex#L113-L114):
> *「U1-c FCCD：周期重複端点を含む MMS face 評価で実効 4 次（条件付き合格 $\triangle$; **界面 advection 用途では §\ref{sec:fccd_def} の設計通り 6 次が達成される — U3-b で別途検証**）」*

This explicitly promises that U3-b verifies the 6-th order. [paper/sections/12u3_nonuniform_spatial.tex:83](paper/sections/12u3_nonuniform_spatial.tex#L83) (tab:U3_fccd_nonuniform) shows U3-b slope 4.00/4.09 — i.e. the same 4-th order ceiling as U1-c. The separate verification promised by U1-c **does not exist**; U3-b confirms 4-th order, not 6-th. FATAL — broken paper-internal proof obligation.

---

## Section C — MAJOR findings

### M-12-1 (MAJOR): 12h_summary U2-a expected "$\Ord{h^6}$" contradicts 12u2's stated theory $\Ord{h^7}$ for $k\ge3$

[paper/sections/12h_summary.tex:34](paper/sections/12h_summary.tex#L34):
> ```
> U2-a & Poisson MMS（DC $k\geq3$） & $\Ord{h^6}$ (Dirichlet) & $\Ord{h^{7.0}}$（超収束）& \checkmark
> ```

[paper/sections/12u2_ccd_poisson_ppe_bc.tex:20-23](paper/sections/12u2_ccd_poisson_ppe_bc.tex#L20-L23) explicitly states the design:
> *「理論期待：$k=1 \to \Ord{h^2}$，$k=2 \to \Ord{h^4}$, $k \ge 3 \to \Ord{h^7}$（スーパー収束）」*

[paper/sections/12u2_ccd_poisson_ppe_bc.tex:47](paper/sections/12u2_ccd_poisson_ppe_bc.tex#L47) actual measured slope at $k=3$:
> ```
> ... & $\mathbf{6.90}$ ...
> ```

The expected value in the summary is wrong (says O(h^6) when 12u2 says O(h^7)), and the measured value claims a clean 7.0 when the actual is 6.90 (close, but rounded up). MAJOR rather than FATAL because the magnitude of the discrepancy is small and the verdict is unaffected.

### M-12-2 (MAJOR): 12u6 evaluation prose contradicts its own table by 1 % (5.05 vs 5.10)

[paper/sections/12u6_split_ppe_dc_hfe.tex:118-119](paper/sections/12u6_split_ppe_dc_hfe.tex#L118-L119):
> *「2D circular band は closest-point 幾何と界面跨ぎセルの配置誤差を含む診断であり, **max $5.05$** / med $3.21$ に律速する．」*

[paper/sections/12u6_split_ppe_dc_hfe.tex:89](paper/sections/12u6_split_ppe_dc_hfe.tex#L89) (tab:U6_hfe slope row):
> ```
> & $\mathbf{5.10}$ & $\mathbf{3.21}$
> ```

The same chapter's evaluation prose and table give different max-slope values (5.05 vs 5.10). One of them is an editing artifact from a re-run that did not propagate fully. MAJOR — internal inconsistency in a single sub-section.

### M-12-3 (MAJOR): 12h_summary U1-a wall slope "$\Ord{h^{5.0}}$" cited but 12u1 presents no wall measurement

[paper/sections/12h_summary.tex:30](paper/sections/12h_summary.tex#L30):
> ```
> U1-a & CCD 1D MMS（周期/壁）  & $\Ord{h^6}$/$\Ord{h^5}$  & $\Ord{h^{6.0}}$/$\Ord{h^{5.0}}$ & \checkmark
> ```

[paper/sections/12u1_ccd_operator.tex:24](paper/sections/12u1_ccd_operator.tex#L24) declares both:
> *「U1-a CCD 1D MMS 周期 BC d1/d2 + 壁 BC d1.」*

…but [paper/sections/12u1_ccd_operator.tex:36-57](paper/sections/12u1_ccd_operator.tex#L36-L57) only contains `tab:U1_ccd_periodic` (periodic), and the evaluation [paper/sections/12u1_ccd_operator.tex:109](paper/sections/12u1_ccd_operator.tex#L109) only mentions the periodic result. The wall O(h^5) measurement is announced but never tabulated or evaluated. MAJOR — missing experimental evidence for a value cited in the summary.

### M-12-4 (MAJOR): Compiled-chapter numbering convention mismatch (§11 vs §12 in code/ledger)

[paper/main.tex:92](paper/main.tex#L92) says the old §11 was removed:
> *「§11（旧：完全アルゴリズム / DCCD ブートストラップ / 純 FCCD DNS）は完全排除．」*

[paper/main.tex:95](paper/main.tex#L95) input order:
> ```latex
> \input{sections/12_component_verification}
> ```

This means files prefixed `12_*.tex` compile as **§11** in the PDF (since old §11 is gone). However:

- [experiment/ch12/exp_U4_ridge_eikonal_reinit.py:3](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L3) docstring: *"Paper ref: Chapter 11 U4"* — agrees with compiled output but contradicts the 12 prefix.
- [docs/02_ACTIVE_LEDGER.md](docs/02_ACTIVE_LEDGER.md) CHK-256 entry refers to "§12 / §13" — uses file-prefix numbering.

Reader-facing risk: the LaTeX cross-references inside ch12 (e.g. `§12.3` printed by `\ref{}`) will display as §11.x, while ledger entries and code docstrings call it §12. MAJOR — paper-vs-meta numbering inconsistency that will confuse external readers.

### M-12-5 (MAJOR): 12h_summary footnote (c) groups two unrelated mechanisms under one label

[paper/sections/12h_summary.tex:75-83](paper/sections/12h_summary.tex#L75-L83):
> *「**(c) 精度床到達**：HFE 2D 高解像度で丸め・補間床，再初期化シフト累積が DGR で補償．」*

This footnote is referenced by **both** U6-c (HFE 2D) and U4 (re-initialization). However, the two mechanisms are physically and numerically unrelated:
- U6-c HFE 2D: closest-point band geometry produces a med-3.21 / max-5.10 slope ceiling (per [12u6_split_ppe_dc_hfe.tex:75-77](paper/sections/12u6_split_ppe_dc_hfe.tex#L75-L77)).
- U4: pseudo-time iteration for $|\nabla\phi|=1$ recovery, decay to ~$h$ band error.

Lumping them under one footnote claim ("DGR が補償") is incorrect for U6-c (DGR has nothing to do with HFE band geometry). MAJOR — misleading taxonomy.

---

## Section D — MINOR findings

### m-12-1 (MINOR): 12u4 caption "$\sim h$ 程度" loose wording

[paper/sections/12u4_ridge_eikonal_reinit.tex:32-36](paper/sections/12u4_ridge_eikonal_reinit.tex#L32-L36):
> *「$n_\tau = 100$ で $9.16\times 10^{-3}$（$\sim h$）まで単調減衰」*

The actual band err at $n_\tau=100$ is 9.16e-3 versus h_min = 7.81e-3 → ratio 1.17. The "$\sim h$" is qualitatively correct but should be quantified (e.g. *「$\sim 1.17 h_{\min}$」*).

### m-12-2 (MINOR): 12u8 Layer B/C ADI cross-term not traced to specific file/line

[paper/sections/12u8_time_integration.tex:97-99](paper/sections/12u8_time_integration.tex#L97-L99):
> *「Layer B, C は ADI 分割誤差 $\Ord{\mathrm{d}t}$ が支配」*

The A3 trace at [paper/sections/12u8_time_integration.tex:127](paper/sections/12u8_time_integration.tex#L127) points to the directory `src/twophase/time_integration/cn_advance/` rather than a specific file/line where the explicit cross-term lives. This is below the C2/A3 standard used in other sub-sections (e.g. 12u3 cites `src/twophase/core/grid.py:91`).

### m-12-3 (MINOR): 12u3 caption cross-references U1-c without table-cell anchor

[paper/sections/12u3_nonuniform_spatial.tex:71](paper/sections/12u3_nonuniform_spatial.tex#L71):
> *「均一格子 U1-c と同様に 4 次律速を示す」*

Should specify which U1-c table cell (tab:U1_fccd_uccd6) and slope row.

### m-12-4 (MINOR): exp_U*.py docstrings still say "Chapter 11 U*"

E.g. [experiment/ch12/exp_U4_ridge_eikonal_reinit.py:3](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L3): *"Paper ref: Chapter 11 U4 (sec:U4_ridge_eikonal_reinit; paper/sections/12u4_ridge_eikonal_reinit.tex)."*. Internally inconsistent: file is in `experiment/ch12/`, points to `12u4_*.tex`, but says "Chapter 11". This may be intentional if the compiled PDF has §11 (per M-12-4), but should be made explicit (e.g. "Paper §11 / file 12u4 / dir ch12 — see ch12/13 numbering note").

### m-12-5 (MINOR): 12h_summary §12.8 heading vs file content

[paper/sections/12h_summary.tex:3](paper/sections/12h_summary.tex#L3) header comment: *「§12.8 検証結果の総括」*. If compiled output is §11.8 (per M-12-4), the comment is stale — same numbering convention issue as the other files but worth flagging since 12h_summary is the chapter's final-output cap.

---

## Section E — Reviewer Skepticism Checklist (P4 5-step protocol)

| # | Step                                                                 | Result                                                                                       |
| - | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| 1 | Did you cite from primary source (file:line + verbatim quote)?       | YES — every FATAL/MAJOR finding cites tex/code path + line + quoted text.                   |
| 2 | Did you cross-check the experiment data (npz/PDF) against the table? | YES — sub-file tables (12u1–12u9) read in full; 12u4 cross-checked against exp_U4 source.   |
| 3 | Have you verified each hypothesis (H-12-1..5) and either confirmed/dismissed? | YES — see closure log below.                                                          |
| 4 | Are FATAL findings reproducible? (Two random spot-checks pass?)      | YES — F-12-1 (U3-b 4.00 vs 5.5) and F-12-12 (godunov_sweep import) re-verified by direct file read. |
| 5 | Did you avoid AP-01 (citing from memory/summary, not source)?        | YES — no finding was sourced from a summary; all line numbers re-checked against current worktree files. |

### Hypothesis closure log

| Hypothesis | Status                | Becomes finding | Note |
| ---------- | --------------------- | --------------- | ---- |
| H-12-1 (compiled §11 vs code/ledger §12 numbering) | CONFIRMED | M-12-4 | main.tex line 92 explicit; line 95 input order verified |
| H-12-2 (U3 FCCD 4.00/4.09 vs 6th-order claim)      | CONFIRMED | F-12-1, F-12-13 | 12u3 line 83 confirms 4.00/4.09; cross-ref to U1-c is broken |
| H-12-3 (U4 RidgeEikonalReinitializer single-shot)  | CONFIRMED | F-12-12 | exp_U4 lines 17-21 docstring + line 44 import are explicit |
| H-12-4 (U6 HFE 2D median 3.21 vs uniform 5th-order)| CONFIRMED | F-12-3, F-12-4, M-12-2 | 12u6 line 89 actual 5.10/3.21; summary claims 7.0/5.8 |
| H-12-5 (U9 negation-test framing clarity)          | DISMISSED | (none)  | 12u9 lines 14-16 explicitly frame as "negation test (PR-5 algorithm fidelity)"; the prose is clear |

---

## Section F — Recommended follow-ups (out of scope, recorded only)

1. **CHK-FOLLOWUP-A (priority: HIGH)** — Rewrite [12h_summary.tex](paper/sections/12h_summary.tex) `tab:verification_summary` and concluding `tcolorbox` against the actual U1–U9 outputs. Estimated cost: ~1 hour (table rewrite from sub-file numbers). Affects 12 of 13 FATAL findings.
2. **CHK-FOLLOWUP-B (priority: HIGH)** — Resolve U4 PR-5 violation: either (i) update [12u4_ridge_eikonal_reinit.tex](paper/sections/12u4_ridge_eikonal_reinit.tex) to describe the Godunov-sweep flow that the code actually runs, OR (ii) reinstate `RidgeEikonalReinitializer` as the experiment primitive (requires resolving the FMM band-floor 0.36 problem). Affects F-12-12.
3. **CHK-FOLLOWUP-C (priority: MEDIUM)** — Either tabulate U1-a wall results in [12u1](paper/sections/12u1_ccd_operator.tex), or remove the wall slope claim from the [12h_summary](paper/sections/12h_summary.tex) row. Affects M-12-3.
4. **CHK-FOLLOWUP-D (priority: LOW)** — Sweep all `exp_U*.py` docstrings and tex header comments to use a single chapter-numbering convention (recommend: keep file prefix `12_*` but state "compiled as §11" in a single header note in `12_component_verification.tex`, then have all sub-files and code docstrings just reference U-IDs). Affects M-12-4 and m-12-4.
5. **CHK-FOLLOWUP-E (priority: LOW)** — Tighten 12h_summary footnote (c) to distinguish HFE band geometry from re-initialization shift. Affects M-12-5.

---

## Verdict line (one sentence)

**ch12: FAIL — 13 FATAL + 5 MAJOR + 5 MINOR.** Most FATAL findings are concentrated in [12h_summary.tex](paper/sections/12h_summary.tex), which carries stale pre-CHK-256 numbers that contradict the live U1–U9 sub-file outputs in 8 of 23 summary rows; the remaining FATAL is a documented PR-5 Algorithm-Fidelity gap between [12u4_ridge_eikonal_reinit.tex](paper/sections/12u4_ridge_eikonal_reinit.tex) (Ridge-Eikonal Hamilton-Jacobi narrative) and [exp_U4_ridge_eikonal_reinit.py:44](experiment/ch12/exp_U4_ridge_eikonal_reinit.py#L44) (`godunov_sweep` import).
