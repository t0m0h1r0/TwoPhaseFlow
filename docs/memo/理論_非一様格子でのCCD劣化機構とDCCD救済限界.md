# 理論ショートペーパー：非一様格子での CCD 劣化機構と DCCD 救済限界

## 0. 要旨
本メモは、非一様格子採用時に観測される「精度悪化・不安定化・破綻」の根因を、座標変換付き CCD 離散化の数式レベルで切り分ける。結論は次の2点である。

1. 主因は「CCD 演算子単体の破綻」ではなく、メトリクス誤差増幅、前漸近定数増大、再初期化/時間離散との結合誤差の複合である。  
2. DCCD/フィルタは高波数ノイズ抑制には有効だが、メトリクス不整合や再初期化起因の誤差を原理的には修復できない。

## 1. 問題設定
非一様格子では、物理座標微分は計算座標微分に

\[
\frac{\partial f}{\partial x} = J_x \frac{\partial f}{\partial \xi}, \quad
\frac{\partial^2 f}{\partial x^2}
= J_x^2 \frac{\partial^2 f}{\partial \xi^2}
+ J_x \frac{\partial J_x}{\partial \xi}\frac{\partial f}{\partial \xi}
\]

で変換される（`paper/sections/06_grid.tex`, Eq. `transform_1st_correct`, `transform_2nd_correct`）。

このとき、非一様格子問題は「`f_\xi, f_{\xi\xi}` の精度」だけでなく「`J_x, \partial_\xi J_x` の精度」も同等に支配的となる。

## 2. 劣化機構（数式レベル）
### 2.1 メトリクス誤差の主項化
離散誤差を
\[
\delta(f_{\xi})=\Ord(h_\xi^p),\;
\delta(f_{\xi\xi})=\Ord(h_\xi^p),\;
\delta(J_x)=\Ord(h_\xi^q),\;
\delta(\partial_\xi J_x)=\Ord(h_\xi^r)
\]
とすると、`f_xx` の誤差は概略
\[
\delta(f_{xx})
\sim 2J_x\,\delta J_x\,f_{\xi\xi}
+ J_x^2\,\delta(f_{\xi\xi})
+ \delta J_x\,(\partial_\xi J_x)f_\xi
+ J_x\,\delta(\partial_\xi J_x)f_\xi
+ J_x(\partial_\xi J_x)\delta(f_\xi)
\]
となる。非一様格子では `J_x` と `\partial_\xi J_x` が空間変動を持つため、`q,r` が十分高くないと `p` より低次項が主項化する。

## 2.2 連続写像と離散写像のギャップ
格子生成が離散求積（標準実装は台形則）ベースの場合、写像 `x(\xi)` 自体が `\Ord(\Delta\xi^2)` の離散誤差を持つ。  
したがって、連続写像前提の理想高次理論をそのまま離散写像へ適用することはできず、前漸近域では次数振動・定数悪化が発生し得る（`paper/sections/06_grid.tex` の注意書きと整合）。

## 2.3 GCL 合格と精度劣化は両立する
GCL（定数場の1階偽微分）合格は「保存則破綻がない」ことを示すが、`f_xx` の高次精度まで保証しない。  
実際に、GCL が機械精度で成立しても、非一様格子で前漸近の次数振動 (`p=3.4..7.9`) は残存し得る（`paper/sections/11a_spatial_discretization.tex`）。

## 2.4 破綻を増幅する結合要因
非一様格子で破綻が顕在化するケースでは、空間離散に加えて以下が重なる。

- 再初期化器が一様格子幅仮定のまま動作し、局所 CFL を破る
- 格子再生成・補間・再初期化・表面張力項が同時に有効化される
- 時間積分での累積誤差が幾何更新と共鳴する

本件では、非一様格子での質量悪化 23% は再初期化器側の格子幅仮定不整合が主要因であり、DGR 化で `2.6e-4` まで回復済み（`paper/sections/11d_interface_field.tex`）。

## 3. DCCD/フィルタで救えるか
### 3.1 救える領域（高波数）
DCCD 3点フィルタの伝達関数は
\[
H(\xi;\varepsilon_d)=1-4\varepsilon_d\sin^2(\xi/2)
\]
であり、`ε_d=1/4` なら Nyquist をゼロ化できる。よって格子スケールの高周波モード抑制には有効。

### 3.2 救えない領域（メトリクス不整合・幾何結合誤差）
一方、DCCD は「既に計算された微分場」のフィルタ後処理であり、

- `J_x`, `\partial_\xi J_x` の低次誤差
- 座標変換項 `J_x(\partial_\xi J_x)f_\xi` の不整合
- 再初期化器の局所格子幅不適合

を直接は修正しない。  
したがって DCCD は「ノイズ抑制による安定化」はできるが、「次数回復」や「幾何誤差の根治」はできない。

## 4. 理論的帰結
非一様格子での悪化・破綻は次の分解で理解するのが妥当である。

\[
\text{総誤差}
= E_{\text{metric}}
+ E_{\text{operator}}
+ E_{\text{reinit/geometry}}
+ E_{\text{time-coupling}}
+ E_{\text{HF-noise}}
\]

ここで DCCD が直接削減できるのは主として `E_HF-noise` のみ。  
`E_metric` と `E_reinit/geometry` が卓越する局面では、DCCD 単独では不十分。

## 5. 実装上の示唆（最小要件）
1. `J_x` と `\partial_\xi J_x` の評価精度を空間主演算子と同等階数で維持する。  
2. 非一様格子上の再初期化は局所格子幅ベース（または DGR）を必須化する。  
3. DCCD は「高波数安定化」用途として位置づけ、メトリクス補正の代替と見なさない。  
4. 検証は GCL pass/fail だけでなく、変換2階項を含む MMS で次数分解して確認する。

## 6. 本稿の立場（要約）
- 「CCD が非一様格子で壊れる」というより、「非一様格子で顕在化する複合誤差により、CCD の理想次数が観測されにくくなる」が正確。  
- DCCD は必要条件（高波数抑制）だが十分条件ではない。  
- 根治には、メトリクス評価・再初期化・幾何/時間結合を同時に整合化する設計が必要。

## 7. 2026-04-16 追記：GPU A/B 実験による反証データ
`experiment/ch12/exp12_19_gfm_nonuniform_ablation.py` をリモートGPU（`use_gpu=True`）で実行し、  
`CSF/GFM × 一様/非一様` の4ケースを同一条件で比較した。

- 出力: `experiment/ch12/results/19_gfm_nonuniform_ablation/data.npz`
- 判定指標: `failed`, `step_fail`, `u_peak`, `dp_err`, `mass_err`

結果は以下の通り。

- `uniform_csf`: `step_fail=8`, `failed=1`
- `uniform_gfm`: `step_fail=9`, `failed=1`
- `nonuniform_csf`: `step_fail=9`, `failed=1`
- `nonuniform_gfm`: `step_fail=10`, `failed=1`

解釈:

1. GFM は破綻ステップを 1–2 ステップ遅延させるが、安定化の十分条件ではない。  
2. 非一様格子のみが単独原因ではない（`uniform_*` も同様に短時間で破綻）。  
3. 「DCCD が主因」という仮説は弱く、`E_reinit/geometry`・`E_time-coupling`・PPE/補正結合の寄与が支配的という本稿の立場と整合する。  

したがって、実装優先順位は引き続き
`E_metric`/`E_reinit/geometry`/`E_time-coupling` の整合化を先行し、  
DCCD は高波数抑制の補助として扱うべきである。
