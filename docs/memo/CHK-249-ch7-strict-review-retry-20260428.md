# CHK-249 -- §7 時間積分 厳正査読レビュー retry

**Date**: 2026-04-28
**Branch**: `worktree-ra-ch7-strict-review`
**Trigger**: user request -- `Execute ResearchArchitect` / "7章について、査読官になったつもりで厳正にレビュー"
**Scope**: `paper/sections/07_time_integration.tex` (1024 lines), with targeted A3 checks against `src/twophase/simulation/viscous_predictors.py`, `src/twophase/simulation/ns_step_services.py`, `src/twophase/time_integration/cfl.py`, and `paper/sections/appendix_numerics_solver_s1.tex`.

---

## Resolution Status

**2026-04-28 update**: user request "指摘の全件に対応して" により、下記 pre-fix findings は同一ワークツリーで対応済み。

**2026-04-28 rereview**: user request "再レビューして" により再監査。FATAL 0 / MAJOR 0 / MINOR 0。`git diff --check` clean、`latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex` clean (218 pp)。判定: **PASS**。

| Finding | Status | Main edit |
|---|---|---|
| M-1 | addressed | AB2/EXT2 の純虚軸安定性主張を撤回し、UCCD6/FCCD 離散スペクトル依存の運用係数に変更 |
| M-2 | addressed | `CFL_sigma` を `Delta t / Delta t_sigma` に統一し、毛管波式を appendix/code と整合 |
| M-3 | addressed | `Delta t_proj` を導入し、BDF2 では `gamma Delta t`、startup では `Delta t` と明示 |
| M-4 | addressed | 全体 2 次精度を均質流域に限定し、変粘性界面クロス項の 1 次律速を本文・表で整合 |
| M-5 | addressed | CLS 移流 TVD-RK3 と Ridge--Eikonal 再初期化を分離し、仮想時間 TVD-RK3 を比較構成に降格 |
| M-6 | addressed | Lie splitting 一般の 2 次主張を撤回し、IPC pressure-correction の 2 次性に限定 |
| M-7 | addressed | `src/`, `docs/memo`, `production stack`, `ch13` 等の公開本文 artifact を除去 |
| m-1..m-4 | addressed | starred label 参照、零安定用語、Hysing claim、appendix ch13 leakage を整理 |

---

## Pre-Fix Verdict

**判定: major revision / 現状採録不可.**

§7 は章構造自体は読みやすいが、時間安定性・毛管 CFL・BDF2 投影係数・全体 2 次精度の主張に、査読で止まる load-bearing な不整合が残っていた。特に Findings 1--4 は、単なる表現修正ではなく「本文の数式主張を再定義する」必要があった。

Severity summary:

| Severity | Count | Summary |
|---|---:|---|
| FATAL | 0 | 即時破綻までは確認せず |
| MAJOR | 7 | 安定領域、CFL 次元、BDF2/IPC 係数、全体精度、A3/論文境界 |
| MINOR | 4 | label 粒度、用語、根拠提示、公開原稿 hygiene |

---

## Major Findings

### M-1. EXT2/AB2 の虚軸安定性主張が成立していない

**Location**:
- `paper/sections/07_time_integration.tex:210`
- `paper/sections/07_time_integration.tex:250`
- `paper/sections/07_time_integration.tex:397`
- `paper/sections/07_time_integration.tex:949`

**Issue**:
本文は対流固有値を「純虚軸」と置いたうえで、AB2/EXT2 が虚軸近傍に実用的な安定領域を持ち、`CFL_adv <= 1` で運用できると主張している。しかし標準 AB2 は純虚軸上に非自明な安定区間を持たない。BDF2 time derivative + EXT2 explicit extrapolation の特性方程式でも、純虚軸上の安定区間は実質的にゼロである。SSPRK3 は虚軸区間を持つため、CLS 側と NS EXT2 側を同列に置けない。

**Impact**:
§7.2 の stability map、§7.3 の IMEX-BDF2 安定性説明、§7.9 の `dt_adv` ガイドが同時に崩れる。査読者は「対流演算子に数値散逸があるから安定」なのか、「純虚軸解析で安定」なのかを区別できない。

**Required fix**:
AB2/EXT2 の純虚軸安定性主張を撤回し、UCCD6/FCCD の離散固有値に負実部が入る場合の実測/解析安定域に置き換える。少なくとも `C_adv` は「理論値 1」ではなく、離散演算子込みの spectral-radius bound または検証値として提示する。

### M-2. 毛管 CFL の定義が章内で次元不整合

**Location**:
- `paper/sections/07_time_integration.tex:201`
- `paper/sections/07_time_integration.tex:218`
- `paper/sections/07_time_integration.tex:951`
- `paper/sections/appendix_numerics_solver_s1.tex:7`
- `src/twophase/time_integration/cfl.py:73`

**Issue**:
`eq:cfl_number` は
`CFL_sigma = Delta t sqrt(sigma kappa / (rho_min h^3))`
と書くが、§7.9・appendix・code は
`Delta t_sigma = sqrt((rho_l + rho_g) h^3 / (2 pi sigma))`
を採用している。前者の `kappa` が曲率なら次元が合わず、波数なら §7 全体で使う曲率 `kappa` と衝突する。さらに密度も `rho_min` と `rho_l + rho_g` で不一致。

**Impact**:
毛管波 CFL は §7 の律速合成式の中核であり、ここが曖昧だと `dt_syn` の意味が確定しない。A3 上も paper と `CFLCalculator` の式が一致していない。

**Required fix**:
`eq:cfl_number` から曲率 `kappa` を除去し、波数を使うなら `k` と明示する。§7.2, §7.9, appendix, code docstring を同一式に統一する。曲率由来の局所毛管制約を別に導入するなら、毛管波 CFL と別名にする。

### M-3. BDF2 投影では `gamma Delta t`、IPC 節では `Delta t` になっている

**Location**:
- `paper/sections/07_time_integration.tex:384`
- `paper/sections/07_time_integration.tex:714`
- `paper/sections/07_time_integration.tex:729`
- `src/twophase/simulation/ns_step_services.py:424`
- `src/twophase/simulation/ns_step_services.py:523`
- `src/twophase/simulation/ns_step_services.py:674`

**Issue**:
§7.3 は BDF2 predictor 後の projection に `gamma Delta t = 2 Delta t / 3` を使う。一方、§7.6 の IPC derivation と proof sketch は generic `Delta t` で PPE RHS と corrector を導く。code は `projection_dt = 2/3 * dt` を PPE RHS・solver・corrector に一貫して渡しており、§7.3 側に合っている。

**Impact**:
§7.6 をそのまま読むと、BDF2 production path ではなく forward-Euler/first-order projection path の導出に見える。`delta p` のスケール、PPE RHS、corrector の A3 trace が曖昧になる。

**Required fix**:
§7.6 の式を `Delta t_p` または `Delta t_proj` で書き直し、BDF2 では `Delta t_proj = gamma Delta t`、BE startup では `Delta t_proj = Delta t` と明示する。proof sketch の `O(Delta t)` 規模評価も `Delta t_proj` に合わせて更新する。

### M-4. 全体 `O(Delta t^2)` 主張と粘性クロス項の `O(Delta t)` 開示が衝突している

**Location**:
- `paper/sections/07_time_integration.tex:117`
- `paper/sections/07_time_integration.tex:142`
- `paper/sections/07_time_integration.tex:184`
- `paper/sections/07_time_integration.tex:491`
- `paper/sections/07_time_integration.tex:873`
- `paper/sections/07_time_integration.tex:906`

**Issue**:
章前半と §7.8 は「本稿構成は全体 2 次」と強く主張する。しかし §7.4 warnbox と表脚注は、変粘性界面ではクロス微分項の陽的処理が `O(Delta t)` に律速し得ると認めている。水--空気級を対象にする本稿では、この例外は周辺条件ではなく主対象に近い。

**Impact**:
読者は「本稿の production は全体 2 次」なのか「界面では 1 次に落ちる」のか判断できない。これは time-convergence validation の合格基準にも直結する。

**Required fix**:
全体 2 次主張を「均質流域 / EXT2 cross-term 採用時 / クロス項が十分小さい場合」に限定する。production が `EXT2` cross-term を採るなら本文と code の A3 を提示し、採らないなら §7 の総合判定を `interface-local O(Delta t)` に下げる。

### M-5. CLS 再初期化に TVD-RK3 を使う記述と Ridge--Eikonal 1-shot 主軸が矛盾

**Location**:
- `paper/sections/07_time_integration.tex:277`
- `paper/sections/07_time_integration.tex:318`
- `paper/sections/07_time_integration.tex:971`
- `paper/sections/07_time_integration.tex:983`
- `paper/sections/07_time_integration.tex:1016`

**Issue**:
§7.3 冒頭と warnbox は、TVD-RK3 を CLS 移流方程式と再初期化方程式の 2 箇所に適用すると書く。ところが §7.9 末尾では、本稿主軸は Ridge--Eikonal の反復不要 1-shot 再構成であり、再初期化方程式の仮想時間積分は旧実装参考とされる。

**Impact**:
production path と legacy path が混線している。§5 から §7 への delegation を読む査読者は、再初期化が時間積分 scheme の対象なのか幾何再構成なのか判断できない。

**Required fix**:
§7.3 の TVD-RK3 適用範囲から production 再初期化を外し、再初期化方程式の TVD-RK3 は「legacy / verification only」と明示する。Stage A の CLS 保存形移流と Ridge--Eikonal 再構成を別物として整理する。

### M-6. Lie splitting が 2 次になる説明が標準理論と衝突したまま

**Location**:
- `paper/sections/07_time_integration.tex:144`
- `paper/sections/07_time_integration.tex:184`
- `paper/sections/07_time_integration.tex:677`
- `paper/sections/07_time_integration.tex:729`

**Issue**:
本文は Lie splitting 自体は標準的に 1 次と認めつつ、IPC と BDF2 self-consistency により全体 splitting 誤差が 2 次に緩和されると述べる。しかしこれは「projection pressure-correction の分離誤差」に対する主張であり、CLS advance, surface-tension jump, buoyancy residual, viscous cross term を含む全 operator split に対する 2 次 theorem にはなっていない。

**Impact**:
標準的な splitting 論に詳しい査読者ほど、ここで立ち止まる。`Lie splitting but O(dt^2)` は補題か検証結果を要求される強い主張。

**Required fix**:
「IPC pressure-correction error は 2 次」と「全 operator splitting が 2 次」を分離する。後者を主張するなら、交換子誤差を消す条件、または time-convergence 実験を §12/§14 から直接引用する。

### M-7. 論文本文に implementation artifact が残る

**Location**:
- `paper/sections/07_time_integration.tex:589`
- `paper/sections/07_time_integration.tex:592`
- `paper/sections/07_time_integration.tex:917`
- `paper/sections/07_time_integration.tex:920`

**Issue**:
本文中に `src/twophase/.../picard_cn.py`、`docs/memo/extended_cn_impl_design.md`、`docs/memo/route_b_third_order.md`、`production stack` という内部実装・計画 artifact が残っている。§7 は理論・離散化の章であり、公開論文本文にローカル repo path と内部 memo path を置くのは査読原稿として不適切。

**Impact**:
A4 separation (theory / discretization / implementation / verification) を損ねる。特に以前の ch13 言及除去方針と同じ種類の hygiene 問題である。

**Required fix**:
公開本文から repo path・memo path・production stack 語を除去し、必要なら「比較実装」「将来検討する 3 次化案」といった論文内語彙に置換する。実装ファイル参照は docs/memo 側に移す。

---

## Minor Findings

### m-1. Starred subsubsection labels are used as if numbered sections

`sec:cfl_definitions`, `sec:von_neumann`, `sec:time_accuracy_lax` are attached to `\subsubsection*{...}` but referenced via `§\ref{...}`. In LaTeX this usually resolves to the previous numbered counter, not a real subsubsection number. Use numbered subsubsections or replace references with prose anchors.

### m-2. AB2/EXT2 zero-stability terminology is inaccurate

`paper/sections/07_time_integration.tex:130` calls AB2/EXT2 "弱零安定の境界". AB2 has roots `1, 0` and is zero-stable in the usual root-condition sense; the problem is absolute stability for imaginary eigenvalues, not zero-stability.

### m-3. Hysing benchmark claim needs local evidence

`paper/sections/07_time_integration.tex:685` says parasitic currents are one order smaller under the same `Delta t` and spatial discretization. `Hysing2009` is a benchmark reference, not necessarily evidence for this implementation. Cite a local experiment or phrase as an expected design effect.

### m-4. `ch13` still appears in the capillary appendix reached from §7

`paper/sections/appendix_numerics_solver_s1.tex:32` contains "本実装 ch13 既定". §7 points to this appendix at `paper/sections/07_time_integration.tex:960`. Even if outside §7 proper, this leaks the implementation-stack vocabulary through a §7 dependency.

---

## A3 Notes

- BDF2 projection path is consistent in code: `ns_step_services.py:424` sets `projection_dt = 2/3 dt`, and the PPE RHS / corrector use that value at `ns_step_services.py:523`, `ns_step_services.py:533`, `ns_step_services.py:550`, `ns_step_services.py:674`.
- BDF2 viscous predictor cites §7 equations in code: `viscous_predictors.py:210`--`viscous_predictors.py:226`. This supports M-3: the code is clearer than the paper derivation.
- `CFLCalculator` implements the §7.9 / appendix capillary-wave formula, not the `eq:cfl_number` curvature formula. This supports M-2.

---

## Recommended Revision Order

1. Fix stability theory first: M-1 and M-2 change the mathematical basis of `dt_syn`.
2. Normalize time-step symbols: introduce `Delta t_proj` and propagate it through §7.3/§7.6.
3. Decide the global-order claim: either prove/measure full `O(Delta t^2)` including cross-viscous terms, or qualify it.
4. Separate production vs legacy paths for CLS reinit and CN comparison.
5. Sweep public-paper hygiene: remove repo paths, memo paths, `production stack`, and appendix `ch13` leakage.
