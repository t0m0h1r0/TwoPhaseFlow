# §13 conditional-pass root-cause research: V1-b / V2 / V4

Date: 2026-04-30

Scope: ResearchArchitect 調査フェーズ。実装は変更しない。対象は §13 単相 NS 検証のうち △ 評価の V1-b, V2, V4。目的は「script が実際に何を測っているか」と「理論・paper が期待している性能」のギャップを特定すること。

## V1-b

### 観測事実
- 設計次数: paper 上は AB2 predictor の $O(\Delta t^2)$ 設計。実測 slope: **1.00**。
- 固定格子: `N=64`。`experiment/ch13/exp_V1_tgv_energy_decay.py:L55-L59` で `T_FINAL=0.05`, `TIME_N=64`, `TIME_DT_TARGETS=(4e-3,2e-3,1e-3)`。実際の $\Delta t$ は `ceil(T_FINAL/dt_target)` で丸められ、paper 表では $3.846, 2.000, 1.000 \times 10^{-3}$。
- 時間積分: `experiment/ch13/exp_V1_tgv_energy_decay.py:L143-L165`。初回は Forward Euler、2 step 目以降は `u + dt*(1.5*rhs_n - 0.5*rhs_prev)` の AB2。開始ステップは 1 次 FE だが、単発 startup なので通常は全体 1 次化の主因とは限らない。
- 射影 form: `experiment/ch13/exp_V1_tgv_energy_decay.py:L126-L131` は `div(u*)/dt` を PPE に入れ、`u^{n+1}=u^*-dt grad(p)` とする非増分の standard projection。旧圧力 $p^n$ を predictor に入れず、PPE 解を $\delta p$ として蓄積もしない。rotational correction も見当たらない。
- PPE は `PPEBuilder(backend, grid, bc_type="periodic")` だが、`_solve_ppe` は `build()` 後に `rhs_flat[ppe_builder._pin_dof]=0` だけを行う。`PPEBuilder.prepare_rhs()` なら periodic image DOF もゼロ化するが、V1 script はそれを使っていない。根拠: `experiment/ch13/exp_V1_tgv_energy_decay.py:L107-L113`, `src/twophase/ppe/ppe_builder.py:L171-L185`, `src/twophase/ppe/ppe_builder_helpers.py:L75-L81`。
- PPE 残差許容値: この script では iterative tolerance はない。`sparse_solve_2d()` は SciPy/CuPy `spsolve` の直接解法であり、dt-scaled tolerance は存在しない。根拠: `src/twophase/tools/experiment/gpu.py:L46-L65`。
- 作用素整合性: 速度 RHS と div/grad は CCD。PPE operator は `PPEBuilder` の FVM 5-point/face-coefficient operator。`PPEBuilder` 自身も FVM $O(h^2)$ と明記している。根拠: `src/twophase/ppe/ppe_builder.py:L49-L56`。

### 理論的に予測される性能
- AB2 単体は滑らかな RHS に対して $O(\Delta t^2)$。ただし V1 script が測るのは AB2 ODE 積分ではなく、非線形項・拡散項を pressure-free predictor で進めた後、standard projection で圧力を後処理する fractional-step 解である。
- standard projection / Chorin 型は圧力を predictor に入れず、圧力補正を非増分に扱うため splitting error が $O(\Delta t)$ に残るのが基本的な理論予測である。Brown--Cortez--Minion 2001 は projection method の高次化には pressure update / boundary condition の扱いが要ることを論じ、Guermond--Quartapelle 1998 と Guermond--Minev--Shen 2006 は pressure Poisson 型 projection の安定性・収束を整理している。
- production 側の `src/twophase/time_integration/ab2_predictor.py` は AB2 + IPC と書かれており、`-\nabla p^n` を predictor に加え、PPE は $\delta p$ を解く設計になっている。根拠: `src/twophase/time_integration/ab2_predictor.py:L1-L33`, `src/twophase/time_integration/ab2_predictor.py:L171-L187`。しかし V1-b script はこの production `Predictor` を使わない手書き実験で、IPC ではない。
- rotational/incremental projection であれば速度 2 次が期待可能になるが、V1 script には old pressure, pressure increment accumulation, rotational correction のいずれもない。従って実測 slope 1.00 は AB2 自体の失敗というより「AB2 と standard projection を結合した実験 identity」の自然な帰結と見るのが妥当。
- 追加の要検証点: periodic PPE RHS の image rows をゼロ化しない実装は、`PPEBuilder` の periodic row constraints と不整合になりうる。これが slope 1.00 の主因か、standard projection の 1 次 splitting が主因かは切り分け実験が必要。ただしどちらも「AB2 単体 2 次」の pass 基準から外れる要因である。

### Pass 基準の理論的妥当性
- 現基準: `O(Δt²)` 設計に対して `|p_meas-p_design|≤0.5` 相当なら、slope 1.00 は不合格。
- ただし実装された V1-b は IPC/rotational projection ではなく standard projection なので、理論上の設計次数を $O(\Delta t)$ と置く方が自然である。この場合 slope 1.00 は「AB2 predictor の 2 次検証」ではなく「standard projection 結合 stack の 1 次診断」として合格扱いにできる。
- paper の現在記述はこの再解釈を一部採用しており、「AB2 単体 2 次設計は PPE 射影との fractional-step 結合では維持されない」と明記している。一方、error budget 表はまだ設計次数欄に `$O(\Delta t^2)$ 設計` を残しているため、判定基準としては二重化している。

### 該当 paper 行
- `paper/sections/13a_single_phase_ns.tex:L20-L24`: V1 設定、N と dt 範囲。
- `paper/sections/13a_single_phase_ns.tex:L42-L57`: V1-b 表、slope 1.00。
- `paper/sections/13a_single_phase_ns.tex:L76-L86`: 判定と制約条件。
- `paper/sections/13f_error_budget.tex:L31-L35`: V1-b summary は slope 1.00 を △ fractional-step 結合としつつ、設計欄は $O(\Delta t^2)$。
- `paper/sections/13f_error_budget.tex:L47-L53`, `paper/sections/13f_error_budget.tex:L72-L75`, `paper/sections/13f_error_budget.tex:L86-L90`: error-source と条件付き合格要約。

### 文献・bib 状態
- `paper/bibliography.bib:L177-L185`: Chorin 1968。
- `paper/bibliography.bib:L267-L276`: van Kan 1986。
- `paper/bibliography.bib:L279-L286`: Guermond--Minev--Shen 2006。
- `paper/bibliography.bib:L529-L538`: Guermond--Quartapelle 1998。
- `paper/bibliography.bib:L754-L762`: Kim--Moin 1985。
- `paper/bibliography.bib:L776-L784`: Bell--Colella--Glaz 1989。
- 未確認 / bib 欠落: Brown--Cortez--Minion 2001 は paper bib に存在しない。外部一次情報として OSTI entry は確認済みだが、paper へ論拠として使うなら bib 追加が必要。

## V2

### 観測事実
- 指示ファイル `experiment/ch13/exp_V2_kovasznay.py` は存在せず、現行実体は `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py`。
- 設計次数: paper/error budget 上は CCD $O(h^6)$ 設計。実測 slope: **3.95**。
- 空間 sweep: `N_LIST=(32,64,128,256)`。domain は `X0=-0.5`, `LX=1.5`, `LY=1.0` なので $x\in[-0.5,1.0]$, $y\in[0,1]$。script の報告 h は `LX/N` で、y spacing は `LY/N`。根拠: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L53-L72`。
- analytic solution: Re=40, $\lambda = Re/2 - \sqrt{(Re/2)^2+4\pi^2}$, $u=1-e^{\lambda x}\cos(2\pi y)$, $v=(\lambda/2\pi)e^{\lambda x}\sin(2\pi y)$, $p=0.5(1-e^{2\lambda x})`。根拠: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L61-L81`。
- BC 形式: PDE solve はしていないため inflow/outflow Dirichlet/Neumann BC は課していない。analytic field を grid nodes に置き、`CCDSolver(..., bc_type="wall")` の one-sided compact closure で微分している。根拠: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L65-L72`。
- residual: $R=(u u_x+v u_y+p_x-\nu\Delta u,\; u v_x+v v_y+p_y-\nu\Delta v)$。norm は vector magnitude の $L_\infty$。評価は `core=(slice(4,-4), slice(4,-4))` で境界 4 点を除いた interior max。full residual / full divergence も保存するが slope は `Linf_res`。根拠: `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L95-L120`, `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L148-L156`, `experiment/ch13/exp_V2_kovasznay_imex_bdf2.py:L243-L256`。
- manufactured solution の出力域: 旧 manufactured periodic residual は legacy に移されており、現 V2 は manufactured periodic ではなく Kovasznay 解析解を直接出力する。field figure は N=256 の $x\in[-0.5,1.0]$, $y\in[0,1]$。

### 理論的に予測される性能
- CCD interior は Chu--Fan 1998 型の 3 点 combined compact difference で、内部式は 6 次。根拠: `src/twophase/ccd/ccd_solver.py:L1-L27`, `src/twophase/ccd/ccd_solver.py:L67-L74`。
- ただし wall boundary closure は interior と同じ 6 次ではない。`CCDSolver` docstring は wall を one-sided compact boundary $O(h^5)$ と記述し、実際の boundary coefficient は d1 が $O(h^5)$、d2 は n_pts>=6 でも $O(h^4)$ の 6-point formula。根拠: `src/twophase/ccd/ccd_solver.py:L84-L90`, `src/twophase/ccd/ccd_solver.py:L388-L418`, `src/twophase/ccd/ccd_solver.py:L421-L445`。
- V2 residual は Laplacian を含むため、d2 boundary closure の $O(h^4)$ が自然な律速候補になる。さらに compact solve は境界値と内部 unknown を同時に解くため、境界 4 点を除いても global compact coupling で interior residual に低次成分が残りうる。
- Kovasznay は x 方向が非周期 outflow を含む解析解であり、periodic manufactured test とは異なる。純粋な periodic smooth function に対する CCD operator unit test なら $O(h^6)$ が期待できても、wall one-sided closure + nonlinear residual + pressure gradient + Laplacian の統合残差では $O(h^4)$ が理論的に妥当な上限に近い。
- divergence が $10^{-12}$ まで下がる一方で momentum residual が 4 次に留まることは、非圧縮条件の失敗ではなく、momentum residual 内の二階微分・圧力境界・非線形結合が支配していることを示す。

### Pass 基準の理論的妥当性
- 現基準: CCD 設計 $O(h^6)$ に対して observed slope 3.95 は不合格または △。
- しかし現 V2 が測るのは interior-only periodic CCD operator ではなく、wall one-sided boundary を持つ Kovasznay steady NS residual である。実装の d2 boundary が $O(h^4)$ である以上、この script に $O(h^6)$ を要求するのは理論的に過大である。
- 妥当な基準は、(a) 現 V2 を「Kovasznay wall residual は実効 4 次」として pass design を $O(h^4)$ に変更する、または (b) 真に CCD $O(h^6)$ を検証したいなら periodic manufactured solution / exact boundary derivative injection / 6 次以上の boundary closure へ実験 identity を変更する、のいずれか。
- 未確認 / 要検証: boundary 4 点除外幅を 4 から 6, 8, 12 に増やしたときも slope 3.95 が維持されるか。維持されるなら compact global coupling の影響、改善するなら residual norm が boundary halo にまだ支配されている可能性が高い。

### 該当 paper 行
- `paper/sections/13a_single_phase_ns.tex:L91-L105`: V2 の対象、設定、interior $L_\infty$。
- `paper/sections/13a_single_phase_ns.tex:L107-L123`: V2 表、slope 3.95。
- `paper/sections/13a_single_phase_ns.tex:L134-L152`: field figure note と判定条件。
- `paper/sections/13f_error_budget.tex:L31-L35`: V2 summary は slope 3.95 を △ としつつ、設計欄は $O(h^6)$。
- `paper/sections/13f_error_budget.tex:L47-L53`, `paper/sections/13f_error_budget.tex:L72-L75`, `paper/sections/13f_error_budget.tex:L86-L90`: V2 を実効 4 次として扱う説明。

### 文献・bib 状態
- `paper/bibliography.bib:L51-L60`: Chu--Fan 1998。CCD interior 6 次の主要根拠。
- `paper/bibliography.bib:L188-L197`: Lele 1992。compact finite-difference / spectral-like resolution の一般論。
- `paper/bibliography.bib:L684-L692`: Kovasznay 1948。
- `paper/sections/04_ccd.tex:L148-L149` は CCD を $O(h^6)$ と表にしているが、V2 の wall d2 boundary $O(h^4)$ とは別の claim として扱う必要がある。

## V4

### 観測事実
- 期待: 厳密 Galilean invariance なら参照系シフト後の差は 0。実測: **$\|\Delta u\|_\infty^{end}=2.07e-1$**、max は paper で $2.63e-1$。
- 設定: `N=64`, `h=1/N`, `dt=0.20h=3.125e-3`, `n_steps=50`, したがって $T=0.15625$。`U_offset=(0.1,0.0)`。根拠: `experiment/ch13/exp_V4_galilean.py:L82-L96`, `experiment/ch13/exp_V4_galilean.py:L128-L132`。
- フレームシフト方法: script は座標変換 $x'=x-Ut$ や interface advection を実装していない。`phi`, `psi`, `rho`, `kappa`, `f_x,f_y` は 1 回だけ作られ、static / offset の両 trajectory で同じ固定液滴を使う。offset は `_trajectory(U)` の初期速度を一様 `U` にするだけ。根拠: `experiment/ch13/exp_V4_galilean.py:L97-L123`。
- BC 種別: `CCDSolver(..., bc_type="wall")`, `PPEBuilder(..., bc_type="wall")`。速度は `_wall_bc` で全境界をゼロにする。根拠: `experiment/ch13/exp_V4_galilean.py:L71-L90`, `experiment/ch13/exp_V4_galilean.py:L107-L119`。
- 評価方式: 各 step 後に `hist.append((u-U[0], v-U[1]))` を保存し、static と offset の差の full-domain $L_\infty$ を取る。境界を除外しない。根拠: `experiment/ch13/exp_V4_galilean.py:L119-L126`。
- 重要な下限: offset run では wall に `u=0` を強制した後で `u-U` を評価するため、壁上の perturbation は少なくとも `-0.1` になる。static run の壁 perturbation は 0。従って full-domain norm で期待 0 は script 上不可能で、最低でも $O(\|U\|)$ の差が入る。
- 圧力ゲージ固定点: `PPEBuilder` wall では `centre_idx=tuple(n//2 for n in self.N)` を pin にする。N=(64,64), shape=(65,65) なので pin は index `(32,32)`、物理的には domain center。根拠: `src/twophase/ppe/ppe_builder.py:L83-L90`。V4 は wall なので periodic image RHS 問題はない。

### 理論的に予測される性能
- 連続 NS の Galilean invariance は、無限/周期領域、または境界も同じ速度で変換される moving frame で成立する。固定 no-slip wall に一様速度 offset を重ね、同じ wall でゼロ速度を課す設定は、そもそも Galilean 変換後の物理問題と一致しない。
- V4 script の offset field は「内部は U、壁は 0」の shear layer を初期から持つ。さらに評価時に全領域で U を引くため、壁では `-U` が残る。このため理論期待値は 0 ではなく、少なくとも $O(\|U\|)$。観測 0.207 は $2\|U\|$ 程度で、paper の「$O(\|U\|)$ residual」解釈とは整合するが、「Galilean invariance proof」とは別物。
- PPE gauge pin は Neumann Poisson の additive nullspace を除くために必要だが、理想的な連続解では圧力定数の選び方は速度勾配に影響しない。離散 pinned-row PPE では pin 周辺の局所誤差や compatibility 処理が速度差に入る可能性はある。ただし V4 の 0.207 を説明する最も直接的な原因は、full-domain wall norm と offset wall clamping の不整合である。
- paper は「初期化の格子サンプリング」を誤差源に挙げるが、script は static と offset で同じ `phi/psi/rho/kappa/f` を使っており、interface を $Ut$ だけ shift して再サンプリングしていない。この paper 側説明は現 script とは対応が弱い。
- 厳密な Galilean test をしたいなら、周期 BC、moving-wall BC、または ALE / shifted sampling を使い、評価も物理的に対応する座標へ補間した interior norm にする必要がある。現 V4 は「固定壁 + pinned PPE + static interface の offset perturbation residual」テストである。

### Pass 基準の理論的妥当性
- 現基準を「期待 0」と置くなら、V4 script は構造的に不合格である。wall で offset を消してから全領域で U を引くため、0 は達成不能。
- 現 paper のように「固定 Eulerian + 参照点固定 PPE の制約下で $O(\|U\|)$ residual に収まる」ことを基準にするなら、2.07e-1 は $\|U\|=0.1$ と同じ order であり、条件付き合格の解釈は可能。
- ただしその場合、テスト名・paper claim は「Galilean invariance」ではなく「fixed-wall Galilean-offset residual」と明確に限定すべきである。期待値欄に 0 を置くのは理論的に不適切。
- 未確認 / 要検証: norm を boundary-excluded core に変更した場合、または wall も U で moving-wall BC にした場合、residual が 0 近傍へ落ちるか。これで wall clamping と PPE gauge の寄与を分離できる。

### 該当 paper 行
- `paper/sections/13c_galilean_offset.tex:L8-L20`: V4 は厳密 Galilean invariance ではなく fixed Eulerian / wall / pinned PPE residual と定義。
- `paper/sections/13c_galilean_offset.tex:L22-L24`: max 2.63e-1, end 2.07e-1。
- `paper/sections/13c_galilean_offset.tex:L26-L42`: paper 側の誤差源分解。ただし初期化 sampling 説明は script と対応が弱い。
- `paper/sections/13c_galilean_offset.tex:L44-L56`: 条件付き診断と $O(\|U\|)$ residual の主張。
- `paper/sections/13f_error_budget.tex:L31-L35`: V4 summary。
- `paper/sections/13f_error_budget.tex:L72-L75`: V4 条件付き合格要約。

### 文献・bib 状態
- paper bib 内に「Galilean invariance in projection methods」を直接扱う文献は見当たらない。
- projection method 一般としては `paper/bibliography.bib:L177-L185` Chorin 1968、`paper/bibliography.bib:L279-L286` Guermond--Minev--Shen 2006、`paper/bibliography.bib:L754-L762` Kim--Moin 1985 がある。
- V4 の主因は文献以前に boundary condition の変換不整合で説明できる。文献を補強するなら、projection method の wall boundary accuracy よりも「Galilean transform under moving / stationary boundaries」の基本条件を明文化する資料が必要。

## Cross-test conclusions

- V1-b: AB2 の 2 次性ではなく、script は standard non-incremental projection + FVM/CCD operator mismatch + possible periodic RHS constraint mismatch を測っている。理論期待は $O(\Delta t)$ 寄り。
- V2: CCD interior 6 次を Kovasznay wall residual にそのまま要求しているのがギャップ。実装 boundary d2 は $O(h^4)$ なので observed 3.95 は理論的に自然。
- V4: strict Galilean zero residual を測る script ではない。wall clamping と full-domain norm により $O(\|U\|)$ residual が構造的に入る。
- Brown--Cortez--Minion 2001 は paper bib にない。V1-b の理論説明に使うなら bib 追加候補。
- V2 の `pressure boundary / interface outer low-order contribution` という error-budget 文言のうち「interface」は単相 Kovasznay には存在しないため、より正確には「wall one-sided boundary / global compact coupling / nonlinear residual」と書く方がよい。

## External primary sources checked

- Kim and Moin 1985, NASA NTRS entry: https://ntrs.nasa.gov/citations/19860050402
- Brown, Cortez and Minion 2001, OSTI entry: https://www.osti.gov/biblio/1429358
- Guermond and Quartapelle 1998, author-hosted PDF: https://people.tamu.edu/~guermond/PUBLICATIONS/guermond_quartapelle_IJNMF_1998.pdf
