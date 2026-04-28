# Strict Peer Review — Chapter 13 (Integration Verification, V1–V10)

| Item | Value |
| --- | --- |
| Reviewer | ResearchArchitect (acting as strict peer reviewer) |
| Date | 2026-04-28 |
| Worktree | `worktree-ra-ch12-13-review-retry-20260428` |
| Session id | `CHK-RA-CH12-001` |
| Rubric | `prompts/agents-claude/PaperReviewer.md` (FATAL / MAJOR / MINOR; AP-01) |
| Pass condition | 0 FATAL + 0 MAJOR |
| Files reviewed | `paper/sections/13_verification.tex`, `13a`–`13f` |
| Cross-checks | `experiment/ch13/exp_V1..V10*.py`, `experiment/ch13/results/`, `paper/figures/ch13_v*.pdf`, `remote.sh` |

---

## Section A — Stance and per-file verdict

### Summary stance

Chapter 13 currently reads like a polished integration-verification chapter, but the audit shows that many V-tests are not the experiments described in the paper. Several scripts are standalone NumPy or reduced-model probes, while the paper claims project CCD / IMEX-BDF2 / split-PPE / DC / HFE / Ridge-Eikonal chains. This is a PR-5 Algorithm Fidelity failure, not a prose polish issue.

The most serious cross-cutting defect is reproducibility: [13_verification.tex](paper/sections/13_verification.tex#L29) says all numerical values come from `experiment/ch13/results/V[1-10]_*/data.npz`, but this checkout has no `experiment/ch13/results/` directory and no tracked files under `experiment/ch13/results/**`. Only the copied paper PDFs exist (`paper/figures/ch13_v*.pdf`, 10 files). Therefore the paper tables cannot be independently audited from the stated data package in this worktree.

### Per-experiment one-line verdicts

| File | Verdict | Notes |
| --- | --- | --- |
| 13_verification | **FAIL** | Stated data source is absent; PR-5/A3 claims overpromise |
| V1 | **FAIL** | Paper claims CCD + AB2/IMEX-BDF2 + PPE; script uses NumPy FFT spectral solver/projection |
| V2 | **FAIL** | Paper claims Kovasznay residual; script uses periodic manufactured sine/cosine field |
| V3 | **FAIL** | Paper says equal density; script uses `rho_l/rho_g=10` |
| V4 | **FAIL** | Galilean and RT settings in paper do not match script; RT gamma text is inconsistent |
| V5 | △ | Result table may be useful, but script/paper still inherit the split-PPE/HFE overclaim |
| V6 | **FAIL** | Paper claims split-PPE + DC + HFE; script uses plain `PPEBuilder` on smoothed density |
| V7 | **FAIL** | Paper blames CLS reinit frequency, but script has no reinit path |
| V8 | **FAIL** | Paper settings (`rho`, `sigma`, `r`, `dt`) do not match script constants |
| V9 | **FAIL** | Same setting mismatch as V8 |
| V10 | **FAIL** | Paper claims FCCD/CLS/Ridge-Eikonal reinit; script uses WENO advection without reinit |
| 13f synthesis | **FAIL** | A3 code paths include nonexistent modules and wrong subsystem names |

### Overall ch13 verdict — **FAIL**

- 11 FATAL / 4 MAJOR / 3 MINOR.
- PASS condition is not met.
- The dominant failure mode is PR-5: the paper repeatedly claims one algorithmic chain while the experiment scripts execute another.
- Recommended route: do not patch individual table cells first. Re-establish each V-test contract (equation → discretization → code → data artifact), then rewrite the chapter from those contracts.

---

## Section B — FATAL findings

> Each finding cites file:line + quoted text from the actual source.

### F-13-1 (FATAL): stated V1–V10 `data.npz` source is absent from this worktree

[paper/sections/13_verification.tex:29](paper/sections/13_verification.tex#L29) states:

> `全数値は \texttt{experiment/ch13/results/V[1-10]\_*/data.npz}`

[paper/sections/13_verification.tex:30](paper/sections/13_verification.tex#L30) continues:

> `から numpy で抽出した値のみを表に記載`

Audit result: `find experiment/ch13/results -maxdepth 2 -type f -name 'data.npz'` reports `No such file or directory`, and `git ls-files 'experiment/ch13/results/**'` returns zero entries. This makes all V1–V10 numerical tables unsupported by the stated source package in the review checkout. FATAL.

### F-13-2 (FATAL): V1 is not the project CCD / IMEX-BDF2 / PPE pipeline claimed by the paper

[paper/sections/13a_single_phase_ns.tex:18](paper/sections/13a_single_phase_ns.tex#L18) claims:

> `CCD 空間離散 ... + AB2 / IMEX-BDF2 時間離散`

[paper/sections/13a_single_phase_ns.tex:19](paper/sections/13a_single_phase_ns.tex#L19) adds:

> `\textsc{HHO}-PPE 圧力射影`

But [experiment/ch13/exp_V1_tgv_energy_decay.py:76](experiment/ch13/exp_V1_tgv_energy_decay.py#L76) defines a local spectral projection:

> `def _project_div_free(u: np.ndarray, v: np.ndarray, KX, KY, K2_inv)`

[experiment/ch13/exp_V1_tgv_energy_decay.py:78](experiment/ch13/exp_V1_tgv_energy_decay.py#L78) uses FFT:

> `u_hat = np.fft.fft2(u)`

and [experiment/ch13/exp_V1_tgv_energy_decay.py:87](experiment/ch13/exp_V1_tgv_energy_decay.py#L87) defines:

> `def _ccd_periodic_advdiff(u, v, KX, KY, K2):`

whose docstring at [line 88](experiment/ch13/exp_V1_tgv_energy_decay.py#L88) says:

> `Spectral advection-diffusion RHS for periodic 2D NS.`

The script does not call the project CCD solver, IMEX-BDF2 integrator, or PPE solver. The paper's A3 chain is therefore false. FATAL.

### F-13-3 (FATAL): V2 is described as Kovasznay, but the script uses a different manufactured periodic flow

[paper/sections/13a_single_phase_ns.tex:86](paper/sections/13a_single_phase_ns.tex#L86) states:

> `Kovasznay 流（解析定常解）に対し CCD 演算子を反復適用`

[paper/sections/13a_single_phase_ns.tex:91](paper/sections/13a_single_phase_ns.tex#L91) gives the Kovasznay form:

> `u_{\mathrm{exact}}(x,y) = 1 - \mathrm{e}^{\lambda x}\cos(2\pi y)`

But [experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:6](experiment/ch13/exp_V2_kovasznay_imex_bdf2.py#L6) says the script verifies:

> `the project's CCD spatial discretization (periodic BC)`

and [experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:15](experiment/ch13/exp_V2_kovasznay_imex_bdf2.py#L15) defines:

> `u(x,y,t) = sin(x)*cos(y)*exp(-2*nu*t)`

The V2 code is a periodic sine/cosine manufactured solution, not Kovasznay flow. The paper's title, setting, and physical interpretation are wrong. FATAL.

### F-13-4 (FATAL): V3 paper setting says equal-density static droplet, but the script runs density ratio 10

[paper/sections/13b_twophase_static.tex:24](paper/sections/13b_twophase_static.tex#L24) states:

> `\sigma = 1.0, \rho_l = \rho_g = 1`

But [experiment/ch13/exp_V3_static_droplet_longterm.py:14](experiment/ch13/exp_V3_static_droplet_longterm.py#L14) states:

> `rho_l/rho_g = 10, We = 10, sigma = 1`

and the constants are [experiment/ch13/exp_V3_static_droplet_longterm.py:67](experiment/ch13/exp_V3_static_droplet_longterm.py#L67)–[70](experiment/ch13/exp_V3_static_droplet_longterm.py#L70):

> `SIGMA = 1.0`, `WE = 1.0`, `RHO_L = 10.0`, `RHO_G = 1.0`

The table may still be numerically plausible, but the experiment described in the paper is not the experiment encoded in the script. FATAL.

### F-13-5 (FATAL): V4-a is not a single-phase Galilean test as described

[paper/sections/13c_galilean_rt.tex:21](paper/sections/13c_galilean_rt.tex#L21) states:

> `\rho_l=1, \rho_g=1 (単相検証), \bm U = (0.1, 0)`

The script's own docstring instead says [experiment/ch13/exp_V4_galilean_rt.py:8](experiment/ch13/exp_V4_galilean_rt.py#L8):

> `A static droplet (R=0.25, sigma>0)`

and the executed constants are [experiment/ch13/exp_V4_galilean_rt.py:110](experiment/ch13/exp_V4_galilean_rt.py#L110)–[112](experiment/ch13/exp_V4_galilean_rt.py#L112):

> `R = 0.25; SIGMA = 1.0; WE = 10.0`, `rho_l, rho_g = 10.0, 1.0`

This is a two-phase static-droplet test with wall PPE, not the single-phase Galilean test described in the paper. FATAL.

### F-13-6 (FATAL): V4-b RT theory line contradicts both its own arithmetic and the script settings

[paper/sections/13c_galilean_rt.tex:73](paper/sections/13c_galilean_rt.tex#L73) says:

> `単一波長 (\lambda = L_x = 1, k = 2\pi) 摂動`

[paper/sections/13c_galilean_rt.tex:74](paper/sections/13c_galilean_rt.tex#L74) says:

> `\rho_h = 3, \rho_l = 1 (\mathcal{A} = 0.5), g = 1`

but [paper/sections/13c_galilean_rt.tex:75](paper/sections/13c_galilean_rt.tex#L75) concludes:

> `\sqrt{0.5\!\cdot\!1\!\cdot\!2\pi} = 2.894`

That arithmetic is false: the left side is about 1.77. The script reaches 2.894 by using different settings: [experiment/ch13/exp_V4_galilean_rt.py:193](experiment/ch13/exp_V4_galilean_rt.py#L193) sets `mode: int = 2`, [line 197](experiment/ch13/exp_V4_galilean_rt.py#L197) sets `rho_l, rho_g = 5.0, 1.0`, and [line 207](experiment/ch13/exp_V4_galilean_rt.py#L207) uses `k = 2.0 * np.pi * mode / Lx`. The paper's stated RT setup is not the setup that generated the table. FATAL.

### F-13-7 (FATAL): V6 claims split-PPE + DC + HFE, but the script uses plain `PPEBuilder`

[paper/sections/13d_density_ratio.tex:17](paper/sections/13d_density_ratio.tex#L17) claims:

> `分相 PPE + DC + HFE 統合`

[paper/sections/13d_density_ratio.tex:84](paper/sections/13d_density_ratio.tex#L84)–[87](paper/sections/13d_density_ratio.tex#L87) gives an A3 chain to:

> `\texttt{src/twophase/poisson/split\_ppe.py}`, `\texttt{src/twophase/poisson/density\_correction.py}`

The script imports [experiment/ch13/exp_V6_density_ratio_convergence.py:49](experiment/ch13/exp_V6_density_ratio_convergence.py#L49):

> `from twophase.ppe.ppe_builder import PPEBuilder`

constructs [experiment/ch13/exp_V6_density_ratio_convergence.py:125](experiment/ch13/exp_V6_density_ratio_convergence.py#L125):

> `ppe_builder = PPEBuilder(backend, grid, bc_type="wall")`

and solves [experiment/ch13/exp_V6_density_ratio_convergence.py:152](experiment/ch13/exp_V6_density_ratio_convergence.py#L152):

> `p = np.asarray(_solve_ppe(rhs, rho_h, ppe_builder, backend))`

No split-PPE, density correction, or HFE primitive is invoked. FATAL.

### F-13-8 (FATAL): V7 blames CLS reinitialization, but the V7 script has no reinit path

[paper/sections/13d_density_ratio.tex:139](paper/sections/13d_density_ratio.tex#L139) says:

> `CLS reinit の頻度差`

[paper/sections/13d_density_ratio.tex:140](paper/sections/13d_density_ratio.tex#L140) claims:

> `各時間ステップで reinit を実施する`

But in the V7 script, `rg reinit experiment/ch13/exp_V7_imex_bdf2_twophase_time.py` finds no reinit implementation; the only `phi`/`psi` operations are the initial setup. [experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:133](experiment/ch13/exp_V7_imex_bdf2_twophase_time.py#L133)–[143](experiment/ch13/exp_V7_imex_bdf2_twophase_time.py#L143) compute fixed `phi`, `psi`, `kappa`, `f_x`, `f_y`, and the time loop [line 152](experiment/ch13/exp_V7_imex_bdf2_twophase_time.py#L152) only calls:

> `u_new, v_new = _bdf2_step(...)`

The paper's causal explanation for slope 0.56 is therefore not supported by the experiment code. FATAL.

### F-13-9 (FATAL): V8/V9 paper settings contradict the scripts

[paper/sections/13e_nonuniform_ns.tex:23](paper/sections/13e_nonuniform_ns.tex#L23) states for V8:

> `\rho_l=\rho_g=1`

and [paper/sections/13e_nonuniform_ns.tex:24](paper/sections/13e_nonuniform_ns.tex#L24) states:

> `実装値 \sigma=0.025, r=0.0625`

But [experiment/ch13/exp_V8_nonuniform_ns_static.py:61](experiment/ch13/exp_V8_nonuniform_ns_static.py#L61)–[69](experiment/ch13/exp_V8_nonuniform_ns_static.py#L69) define:

> `R = 0.25`, `SIGMA = 1.0`, `WE = 10.0`, `RHO_L = 10.0`, `RHO_G = 1.0`

V9 repeats the same paper setting at [paper/sections/13e_nonuniform_ns.tex:79](paper/sections/13e_nonuniform_ns.tex#L79):

> `V8 と同条件 (r=0.0625, \sigma=0.025)`

while [experiment/ch13/exp_V9_local_eps_nonuniform.py:64](experiment/ch13/exp_V9_local_eps_nonuniform.py#L64)–[72](experiment/ch13/exp_V9_local_eps_nonuniform.py#L72) again use `R = 0.25`, `SIGMA = 1.0`, `WE = 10.0`, `RHO_L = 10.0`, `RHO_G = 1.0`. FATAL.

### F-13-10 (FATAL): V10 claims FCCD / Ridge-Eikonal reinit, but the script uses WENO advection without reinit

[paper/sections/13e_nonuniform_ns.tex:136](paper/sections/13e_nonuniform_ns.tex#L136)–[137](paper/sections/13e_nonuniform_ns.tex#L137) claims V10 combines CLS advection with:

> `非一様格子上の高次保存形差分 (\autoref{sec:fccd_def})`

[paper/sections/13e_nonuniform_ns.tex:170](paper/sections/13e_nonuniform_ns.tex#L170) attributes the failure to:

> `非一様格子上の CLS reinit 補正`

The script imports [experiment/ch13/exp_V10_cls_advection_nonuniform.py:55](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L55):

> `from twophase.levelset.advection_weno import LevelSetAdvection as WenoLS`

defines [experiment/ch13/exp_V10_cls_advection_nonuniform.py:96](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L96):

> `def _weno_advect(psi_h, u, v, ls_adv, backend, dt):`

and the loop [experiment/ch13/exp_V10_cls_advection_nonuniform.py:155](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L155)–[156](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L156) only performs:

> `psi_h = _weno_advect(psi_h, u, v, ls_adv, backend, dt)`

`RidgeEikonalReinitializer` is imported but unused. There is no reinitialization every 10 steps despite the script docstring's claim at [line 23](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L23). FATAL.

### F-13-11 (FATAL): §13f A3 synthesis cites nonexistent or wrong implementation paths

[paper/sections/13f_error_budget.tex:89](paper/sections/13f_error_budget.tex#L89) cites:

> `src/twophase/integrator/{ab2,imex_bdf2}.py`

[paper/sections/13f_error_budget.tex:101](paper/sections/13f_error_budget.tex#L101) cites:

> `src/twophase/poisson/{split_ppe,density_correction}.py`

[paper/sections/13f_error_budget.tex:106](paper/sections/13f_error_budget.tex#L106) cites:

> `src/twophase/cls/{advection,reinit}.py`

Targeted filesystem checks show these paths do not exist in this checkout (`src/twophase/time_integration/ab2_predictor.py`, `src/twophase/ppe/`, `src/twophase/levelset/`, and `src/twophase/hfe/` are the live namespaces). A3 traceability is mandatory; pointing readers at nonexistent code paths is a FATAL traceability failure.

---

## Section C — MAJOR findings

### M-13-1 (MAJOR): copied paper PDFs are not tied to script output names

[paper/sections/13a_single_phase_ns.tex:65](paper/sections/13a_single_phase_ns.tex#L65) embeds:

> `figures/ch13_v1_tgv_energy.pdf`

but [experiment/ch13/exp_V1_tgv_energy_decay.py:216](experiment/ch13/exp_V1_tgv_energy_decay.py#L216) saves:

> `OUT / "V1_tgv_energy_decay"`

Similar renaming exists for other V figures. Manual copy/rename may be legitimate, but the chapter currently lacks a provenance note mapping each script output to each `paper/figures/ch13_v*.pdf`. MAJOR reproducibility gap.

### M-13-2 (MAJOR): V7 paper says project IMEX-BDF2, but the script uses a local helper

[paper/sections/13d_density_ratio.tex:93](paper/sections/13d_density_ratio.tex#L93)–[95](paper/sections/13d_density_ratio.tex#L95) frames V7 as an IMEX-BDF2 time-discretization test. The script implements a local function [experiment/ch13/exp_V7_imex_bdf2_twophase_time.py:97](experiment/ch13/exp_V7_imex_bdf2_twophase_time.py#L97):

> `def _bdf2_step(...)`

This is not automatically invalid, but the paper does not disclose that V7 bypasses the production time-integration module. Given the reported failure slope, this distinction matters. MAJOR.

### M-13-3 (MAJOR): V4-a is titled "Galilean invariance" although the paper itself says it does not exclude violation

[paper/sections/13c_galilean_rt.tex:55](paper/sections/13c_galilean_rt.tex#L55) states:

> `本検証の結論は「ソルバが Galilean 不変性を破る」ことを\textbf{排除}するものではなく`

This is refreshingly honest, but it conflicts with [paper/sections/13c_galilean_rt.tex:14](paper/sections/13c_galilean_rt.tex#L14)–[18](paper/sections/13c_galilean_rt.tex#L18), where the subsection is framed as confirming Galilean invariance. The subsection should be retitled as a residual/limitation probe. MAJOR.

### M-13-4 (MAJOR): V6 density-ratio conclusion overstates what the measured static-droplet proxy proves

[paper/sections/13d_density_ratio.tex:37](paper/sections/13d_density_ratio.tex#L37)–[38](paper/sections/13d_density_ratio.tex#L38) claims:

> `分相 PPE + DC + HFE が密度ジャンプ越えで設計通りの \rho_r ロバスト性を発揮することを定量証明`

Even ignoring F-13-7, the V6 script is a held-interface static-droplet proxy: [experiment/ch13/exp_V6_density_ratio_convergence.py:145](experiment/ch13/exp_V6_density_ratio_convergence.py#L145)–[152](experiment/ch13/exp_V6_density_ratio_convergence.py#L152) repeats a fixed CSF/PPE loop over 50 steps. It does not establish general density-jump robustness for moving interfaces. MAJOR.

---

## Section D — MINOR findings

### m-13-1 (MINOR): parent overview says V8–V10 test "robustness" even when two tests are explicit failures

[paper/sections/13_verification.tex:25](paper/sections/13_verification.tex#L25):

> `V8--V10 で非一様格子上の堅牢性を検証する`

V9 and V10 are later marked as not recommended / outside guarantee. "Robustness limits" would be more accurate.

### m-13-2 (MINOR): V10 `dt` formula in text omits velocity scaling

[paper/sections/13e_nonuniform_ns.tex:144](paper/sections/13e_nonuniform_ns.tex#L144):

> `\Delta t = h_{\min} \cdot \mathrm{CFL}_{\max}`

The script uses [experiment/ch13/exp_V10_cls_advection_nonuniform.py:138](experiment/ch13/exp_V10_cls_advection_nonuniform.py#L138):

> `dt = 0.25 * h_min / max(u_max, 1e-3)`

The paper formula should include division by `u_max`.

### m-13-3 (MINOR): V2 script filename still says `imex_bdf2` although V2 is spatial-only

[experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:2](experiment/ch13/exp_V2_kovasznay_imex_bdf2.py#L2) says:

> `CCD spatial residual on periodic single-phase NS`

The filename suffix `imex_bdf2` is stale and invites exactly the confusion seen in the paper. MINOR naming issue after the larger V2 correction.

---

## Section E — Reviewer Skepticism Checklist (P4 5-step protocol)

| # | Step | Result |
| - | --- | --- |
| 1 | Did every cited error use actual file:line evidence? | YES — all FATAL/MAJOR items cite current worktree source lines. |
| 2 | Did the review avoid relying on ledger summaries alone? | YES — ledger used only as task context; findings cite paper/scripts/filesystem audit. |
| 3 | Were the H-13 hypotheses closed? | YES — see closure log. |
| 4 | Are two random FATALs reproducible? | YES — F-13-3 (V2 not Kovasznay) and F-13-10 (V10 no reinit) re-check directly from source lines. |
| 5 | Did the review stop short of proposing paper edits as if implemented? | YES — fixes are routed as follow-up CHKs only. |

### Hypothesis closure log

| Hypothesis | Status | Becomes finding | Note |
| --- | --- | --- | --- |
| H-13-1 V result subfolders absent | CONFIRMED | F-13-1 | no `experiment/ch13/results/` in worktree |
| H-13-2 V7 slope 0.56 vs BDF2 ≥1.8 | CONFIRMED | F-13-8, M-13-2 | paper honestly reports 0.56, but causal/A3 story is unsupported |
| H-13-3 V10 α=2 out-of-guarantee | PARTLY DISMISSED | F-13-10 | paper marks α=2 outside guarantee, but code path is not the claimed path |
| H-13-4 V8/V9 α=2 instability | REFRAMED | F-13-9 | paper reports stable V8 / unstable local ε; bigger issue is setting mismatch |
| H-13-5 V2 filename/content mismatch | CONFIRMED | F-13-3, m-13-3 | paper adopted the stale Kovasznay label |

---

## Section F — Recommended follow-ups (out of scope, recorded only)

1. **CHK-FOLLOWUP-A (priority: CRITICAL)** — Define authoritative V1–V10 contracts: for each V-test, record equation, production/discrete operator, script, result `data.npz`, figure copy target, and pass/fail criterion.
2. **CHK-FOLLOWUP-B (priority: CRITICAL)** — Decide whether V1/V2 are allowed to be reduced standalone numerical probes. If yes, rewrite the paper as such; if no, replace scripts with production pipeline calls.
3. **CHK-FOLLOWUP-C (priority: HIGH)** — Rebuild `experiment/ch13/results/V[1-10]_*/data.npz` or change the paper provenance statement to point at the actual archived data package.
4. **CHK-FOLLOWUP-D (priority: HIGH)** — Fix A3 paths in §13a/§13d/§13f to the live namespaces (`time_integration`, `ppe`, `levelset`, `hfe`) and only cite files actually invoked by each script.
5. **CHK-FOLLOWUP-E (priority: MEDIUM)** — Add a figure-provenance manifest mapping each script output PDF to each `paper/figures/ch13_v*.pdf`.

---

## Verdict line (one sentence)

**ch13: FAIL — 11 FATAL + 4 MAJOR + 3 MINOR.** The chapter is not submission-ready because V1–V10 repeatedly violate PR-5/A3 traceability: stated data packages are absent, several paper settings do not match scripts, and key claims about CCD / IMEX-BDF2 / split-PPE / DC / HFE / Ridge-Eikonal are not the algorithms executed by the reviewed experiment code.
