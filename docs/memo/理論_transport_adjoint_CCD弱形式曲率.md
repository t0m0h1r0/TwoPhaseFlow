# 理論: transport-adjoint CCD 弱形式曲率

## 目的

N64 alpha-2 振動液滴で確認された界面形状破綻を、damping、CFL tuning、
smoothing、curvature cap ではなく、表面張力の離散変分構造を正すことで
解決する。

既存の `transport_variational` route は
`dE_Γ/dt + P_Γ = 0` の仕事契約を大きく改善したが、marching-squares の
区分線形エネルギー微分は切断 topology 変化に対して `C0` であり、高次界面
モードを注入しうる。次の理論的修正は、同じ transport-adjoint 契約を保った
まま、`δE_Γ/δψ` を CCD 弱形式曲率 mass solve で置き換えることである。

## 連続系の非交渉契約

液相から気相へ向く法線を `n_lg`、曲率を

```text
κ_lg = div_Γ n_lg
```

と定義する。液滴円なら `κ_lg > 0`。Young--Laplace jump は

```text
j_gl = p_g - p_l = -σ κ_lg .
```

界面速度の法線成分を `V_lg = u_Γ · n_lg` とすると、表面エネルギー

```text
E_Γ = σ |Γ|
```

は

```text
dE_Γ/dt = σ ∫_Γ κ_lg V_lg dS
```

を満たす。したがって pressure jump が流体へ与える仕事は

```text
P_Γ = ∫_Γ j_gl V_lg dS = - dE_Γ/dt .
```

これは表面張力の物理的本質であり、離散化でも絶対に保つべき契約である。

## 弱形式曲率

曲率を pointwise に `κ = div n` で計算するのではなく、平均曲率ベクトル

```text
H = κ_lg n_lg
```

を面積汎関数の第一変分として定義する。任意の界面ベクトル試験関数 `η` に
対して

```text
∫_Γ H · η dS = ∫_Γ ∇_s X : ∇_s η dS .
```

ここで `X` は界面の位置写像である。この式は、円では外向き
`H = (1/R) n_lg` を返し、面積変化

```text
δ|Γ| = ∫_Γ H · δX dS
```

と整合する。

## CCD 離散界面

### 離散空間 v1: 採用する未知量

Eulerian scalar unknown は格子 node 上の conservative level-set 値

```text
ψ = {ψ_i}_{i∈I_Ω}
```

である。CCD reconstruction operator を

```text
Π_h : {ψ_i} -> ψ_h(x)
```

と書く。`Π_h` は solver の FCCD/CCD trace と同じ線形 reconstruction で
なければならない。別の reconstruction で曲率だけを作ると、transport-adjoint
契約が破れる。

界面は cell-local implicit CCD trace

```text
Γ_h = { x ∈ Ω | ψ_h(x) = c },  c = 0.5
```

で定義する。法線は `ψ=1` liquid, `ψ=0` gas の規約から

```text
n_lg,h = - ∇ψ_h / |∇ψ_h|
```

である。

Lagrangian interface mesh は、各 cut cell 内の CCD trace を曲線要素

```text
γ_e : ξ ∈ [-1,1] -> x ∈ Γ_h ∩ K
```

として持つ graph

```text
G_Γ = (A_Γ, E_Γ)
```

である。node 集合 `A_Γ` は少なくとも cut-edge roots を含み、曲線要素の次数に
応じて cell 内 node を追加する。

採用する最小 production 空間は **P2 isoparametric CCD trace** とする。

```text
X_h|_e(ξ) = Σ_{a∈e} N_a(ξ) X_a,       N_a ∈ P2([-1,1])
H_h|_e(ξ) = Σ_{a∈e} N_a(ξ) H_a .
```

`X_a` は CCD implicit equation `ψ_h(X_a)=c` を満たす点であり、直線
marching-squares の交点ではない。P1 straight segment は diagnostic baseline
としては許すが、production fix としては採用しない。理由は、P1 polygon で
`M H = K X` を解いても、force vector `M H = K X` は線分長の既存直接変分と
数学的に同じであり、高次 mode 注入の根を変えないからである。

### CCD trace node の決め方

各 cut cell で、edge root は CCD edge trace

```text
ψ_e(λ; ψ) = c,       λ∈[0,1]
```

の単純根として求める。P2 midpoint node は、linear chord midpoint を初期値に
cell-local Newton iteration で

```text
ψ_h(X_m; ψ) = c
```

を満たす点へ投影する。投影方向は `n_lg,h` とし、tangential 方向の arbitrary
shift を入れない。これにより `X_h` は同じ CCD implicit curve の近似になる。

各 interface node `a` は search line

```text
X_a = ℓ_a(λ_a)
```

を持つ。edge root では `ℓ_a` は grid edge、midpoint では法線投影線である。
search direction を

```text
r_a = ∂_λ ℓ_a(λ_a)
```

とする。regular node の条件は

```text
∇ψ_h(X_a) · r_a ≠ 0 .
```

接触・接線・topology change でこの条件が破れる場合、その step は変分が
非正則であり、固定値 epsilon でごまかさず event として扱う。

### 弱形式曲率 mass solve

interface scalar space を

```text
V_h^Γ = { continuous P2 functions on G_Γ }
```

とする。vector space は `[V_h^Γ]^2`。曲線要素の metric は

```text
J_e(ξ) = |∂_ξ X_h(ξ)|
ds = J_e dξ
∂_s = J_e^{-1} ∂_ξ .
```

質量行列と剛性行列は同じ曲線要素・同じ quadrature で

```text
M_ab = Σ_e ∫_{-1}^1 N_a N_b J_e dξ
K_ab = Σ_e ∫_{-1}^1 (∂_s N_a)(∂_s N_b) J_e dξ
```

として組む。P2 geometry なので quadrature は最低 3 点 Gauss、検証では 4 点
Gauss も比較して quadrature error を分離する。

弱曲率ベクトルは

```text
Σ_b M_ab H_b = Σ_b K_ab X_b .
```

で定義する。これは smoothing ではない。選んだ曲線エネルギー

```text
E_Γ,h(X) = σ Σ_e ∫_{-1}^1 J_e dξ
```

の第一変分を `L2(Γ_h)` へ表現する mass solve である。実際、

```text
δE_Γ,h = σ δX^T K X = σ δX^T M H .
```

pressure jump に入れる scalar curvature は quadrature 点で

```text
κ_h(q) = H_h(q) · n_lg,h(q)
```

とする。接線成分は再パラメータ化誤差であり、物理的な pressure jump へは
入れない。

## Level-set 変分への写像

### 厳密な chain rule

界面 node `X_a(ψ)` は constraint

```text
F_a(X_a, ψ) = ψ_h(X_a; ψ) - c = 0
```

を満たす。変分は

```text
∇ψ_h(X_a) · δX_a + δψ_h(X_a) = 0 .
```

node displacement は、その node を定義した search line 上に限定する。

```text
δX_a = r_a δλ_a
δλ_a = - δψ_h(X_a) / (∇ψ_h(X_a) · r_a)
```

ここで

```text
δψ_h(X_a) = Σ_i Φ_i(X_a) δψ_i
```

であり、`Φ_i` は `Π_h` の nodal basis trace である。したがって曲線 node から
Eulerian ψ node への Jacobian は

```text
∂X_a/∂ψ_i
  = - r_a Φ_i(X_a) / (∇ψ_h(X_a) · r_a) .
```

curve energy の nodal force covector は

```text
F_a^X = σ (K X)_a = σ (M H)_a .
```

よって level-set covector は

```text
g_i = ∂E_Γ,h/∂ψ_i
    = - Σ_a F_a^X · r_a Φ_i(X_a) / (∇ψ_h(X_a) · r_a) .
```

これは `κ_h δ_Γ / |∇ψ_h|` の離散版だが、実装ではこの chain rule を
primary とする。quadrature 点で直接 `κ/|∇ψ|` を撒く実装は、同じ `M,K,X`
から導出される場合に限って許す。

midpoint node のように `r_a=n_lg,h` を選んだ場合は

```text
∂X_a/∂ψ_i = n_lg,h Φ_i / |∇ψ_h|
```

へ戻る。edge root では `r_a` は grid-edge tangent なので、この簡約形を
使ってはならない。

### P1 polygon との違い

P1 polygon の場合も同じ chain rule は成り立つ。しかしその場合

```text
F^X = σ K_P1 X
```

は現行 marching-segment length derivative と等価である。したがって弱形式
mass solve という名前だけを導入しても、離散エネルギーは変わらない。

問題を解くには、`E_Γ,h` 自体を CCD trace 上の曲線エネルギーへ上げる必要が
ある。これが P2 isoparametric CCD trace を採用する理由である。

## Transport-adjoint face source

実際の interface transport は face velocity を使う。

```text
ψ_t = R_h(ψ, u_f) = - Σ_a D_a( ψ_f^a u_f^a )
```

この `R_h` は solver が実際に使う transport そのものでなければならない。
surface-energy rate は

```text
dE_Γ,h/dt = < g, R_h(ψ, u_f) > .
```

よって capillary face covector は

```text
C_f = - (∂R_h/∂u_f)^T g
```

で定義する。このとき任意の face velocity に対して

```text
Σ_f u_f C_f = - < g, R_h(ψ, u_f) > = - dE_Γ,h/dt
```

が恒等的に成り立つ。

既存 pressure-gradient jump API に入れる量は、face distance `d_f` と
face area `A_f` を用いて

```text
B_f = C_f / (d_f A_f)
```

とする。pressure correction 側では従来通り

```text
G_Γ(p) = G_f(p) - B_f
```

を使う。

## 陰的化の正しい意味

ここでいう implicit は、任意の smoothing parameter を入れることではない。
正しい候補は二つだけである。

1. **空間的 implicit mass solve**
   `M H = K X` を consistent mass で解く。これは曲率の L2 射影であり、
   pointwise `div n` のノイズを避ける。

2. **時間的 semi-implicit variational update**
   必要なら

   ```text
   X^{n+θ} = X^n + θ Δt T_h u_f^{n+1}
   M(X^n) H^{n+θ} = K(X^n) X^{n+θ}
   ```

   として、capillary source を `H^{n+θ}` から作る。この場合も、増える項は
   すべて discrete energy の変分として pressure/projection operator に入れる。
   damping や curvature cap とは別物である。

## 棄却すべき案

- `κ` だけを平滑化して pressure jump に入れる。
- marching-squares derivative を scalar 倍で補正する。
- high-mode を見て curvature cap を入れる。
- CFL を下げて破綻を遅らせる。
- CCD 曲率方程式を解くが、transport-adjoint source へ写像しない。

これらは `Σ_f u_f C_f = -dE_Γ,h/dt` を保証しない。

## 検証ゲート

実装は以下をすべて通すまで本番 1 周期へ進めない。

1. **弱曲率 manufactured geometry**
   - 円: `κ_h = 1/R` へ収束。
   - 楕円: analytic curvature との RMS 収束。
   - `∫_Γ H dS = 0`、`∫_Γ X × H dS = 0`。

2. **変分 finite-difference check**
   - 任意の scalar perturbation `δψ` について
     `δE_Γ,h ≈ <g, δψ>`。
   - edge-root perturbation では `r_a` 方向 chain rule を使い、法線方向の
     簡約式を使わないこと。

3. **transport-adjoint work gate**
   - 任意の face velocity について
     `Σ_f u_f C_f + <g, R_h(ψ,u_f)> = 0`。

4. **P1 equivalence rejection gate**
   - P1 polygon + weak mass solve が現行 marching-segment derivative と
     同じ force vector を返すことを確認する。
   - この test は P1 route を production fix として採用しない理由の証明で
     あり、合格しても改善とはみなさない。

5. **curved CCD benefit gate**
   - P2 CCD trace energy の `δE` が P1 polygon と異なること。
   - 円・楕円で P2 trace の curvature/energy error が P1 より下がること。

6. **static droplet gate**
   - pressure contrast `p_l - p_g ≈ σ/R`。
   - net velocity and KE remain small without damping/caps.

7. **oscillating droplet short gates**
   - N32/T=4 and N64/T=1 deformation error does not regress.
   - high-mode ratio decreases or remains bounded.
   - volume drift remains comparable to existing good route.

## 時間方向の最小閉包: P2 midpoint pressure-jump geometry

P2 trace energyを空間方向で変分閉包しても、時間方向で常に
`ψ^{n+1}` の幾何を陽的にPPEへ差し込むだけでは、capillary workの
時間積分点がtransport updateとずれる。そこで最初の半陰的閉包として

```text
ψ^{n+1/2} = (ψ^n + ψ^{n+1}) / 2,
g_Γ^{n+1/2} = ∂E_{Γ,h}(ψ^{n+1/2}),
C_f^{n+1/2} = -(∂R_h/∂u_f)^T g_Γ^{n+1/2}
```

を使う。これは完全なNewton--Krylov同時解法ではないが、空間の
transport-adjoint contractを壊さず、capillary jumpの評価点だけを
midpoint quadratureへ進める最小の理論的前進である。

`ψ^n` はキャッシュではなく1 stepの状態変数であり、fitted grid rebuildが
入る場合は同じ現在gridへremapしてから `ψ^{n+1/2}` を構成する。これにより
PPE jump contextとprojection face corrector contextは同一の
backend-native temporaryを参照する。

## 結論

正しい次手は

```text
CCD Γ_h
  -> P2 isoparametric CCD trace space V_h^Γ
  -> weak curvature mass solve M H = K X
  -> scalar κ = H · n_lg
  -> exact chain-rule covector g = (∂X/∂ψ)^T σ K X
  -> transport-adjoint face covector C = -(∂R/∂u_f)^T g
  -> pressure jump gradient B = C / (d_f A_f)
```

である。

この route は表面張力の物理契約、Young--Laplace jump、CLS transport、PPE の
face work を同じ変分構造へ閉じる。実装はこの chain のどこかを省略しては
ならない。
