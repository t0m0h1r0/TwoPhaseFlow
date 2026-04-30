# CHK-RA-CH14-006 — generic interface-stress closure design

## 要旨

毛管波だけを直す専用ロジックは作らない。必要なのは，
毛管波・上昇気泡・Rayleigh--Taylor を同じ数学契約で扱う
**汎用 interface-stress closure** である。

結論：

> 表面張力を `J = σ κ (1-ψ)` という通常の節点圧力場として PPE に入れてはならない。
> `J` は同じ pressure space の自由度に吸収され，`p_base≈-J`，
> `p_total=p_base+J≈0` という代数的相殺を起こす。
> 物理的に正しい表面張力は，圧力場の通常自由度ではなく，
> 界面上の応力ジャンプ条件 `[T]n = σ κ n` として入れる。

したがって対応方針は，
**surface tension / buoyancy / projection を一つの jump-aware affine projection に統合する**
ことである。

## 守る物理法則

本設計で絶対に破ってはいけない法則は次の通り。

### P1: 非圧縮制約

```text
∇ · u = 0
```

離散的にも，投影後の face flux は PPE の divergence と同じ演算子で
`D_f u_f^{n+1}=0` を満たす。

### P2: 一流体運動量保存

```text
ρ(∂_t u + u·∇u) = -∇p + ∇·(2 μ D(u)) + ρ g + f_σ
```

ここで表面張力は体積全域の任意ポテンシャルではなく，界面測度上の力

```text
f_σ = σ κ n δ_Γ
```

または等価な界面応力ジャンプである。

### P3: 界面応力ジャンプ

定数表面張力では

```text
[[T]] n = σ κ n,
T = -p I + 2 μ D(u).
```

低粘性・投影段階の圧力ジャンプとしては，第一近似で

```text
[[p]] = σ κ
```

を満たす。これは「圧力場に足す滑らかな関数」ではなく，
左右相の trace の差に対する制約である。

### P4: 運動学的条件

界面は流体速度で移流する。

```text
V_Γ = u · n
```

したがって，毛管波の signed mode も，上昇気泡の重心も，
同じ投影後速度場から出なければならない。

### P5: エネルギー整合

閉じた no-slip 系では，外部仕事を除き，

```text
d/dt [ ∫ 1/2 ρ |u|^2 dV + σ |Γ| + ∫ ρ g y dV ]
  = - ∫ 2 μ |D(u)|^2 dV
```

である。離散法も少なくとも次を満たすべき：

- 静止平衡を勝手に動かさない。
- 非平衡の界面エネルギー勾配を消さない。
- 数値的に界面エネルギーを無根拠に増幅しない。

## なぜ current `jump_decomposition` は原理的にまずいか

現実装の失敗した構造は次である。

```text
J = σ κ (1 - ψ)
L(p_base) = rhs - L(J)
p_total = p_base + J
```

初期静止毛管波では `rhs≈0` なので，

```text
L(p_base) ≈ -L(J)
=> p_base ≈ -J + nullspace
=> p_total ≈ 0
```

となる。これは「well-balanced」ではない。
物理平衡だけでなく，非平衡の毛管復元力まで消してしまう。

この失敗は毛管波専用ではない。上昇気泡でも，表面張力と浮力の不整合から
生じるべき残差を pressure space に吸収させる危険がある。

## 汎用対応の中核

### C1: 表面張力は通常 pressure field ではなく affine jump として扱う

新しい projection は通常の gradient `G p` ではなく，
既知の界面ジャンプ `j = σ κ` を持つ affine gradient を使う。

```text
G_Γ(p; j) = G(p) - B_Γ j
```

ここで `B_Γ j` は，界面を横切る face にだけ現れる既知ジャンプ寄与である。
1D の cut face なら概念的には

```text
(G_Γ p)_f = (p^+ - p^- - j_Γ) / d_f
```

である。重要なのは，`j_Γ` が pressure unknown ではなく
**operator の affine part** である点。

このとき投影は

```text
u_f^{n+1}
  = u_f^*
    + Δt a_f
    - Δt α_f G_Γ(p; j)_f,

D_f u_f^{n+1} = 0,
α_f = (1/ρ)_f.
```

したがって pressure equation は

```text
D_f [ α_f G_Γ(p; j)_f ]
  = D_f [ u_f^* / Δt + a_f ].
```

この形では `j` は消去されない。非同次界面条件として楕円問題を駆動する。

### C2: 静止平衡と非平衡を同じ式で分ける

#### 静止液滴

円形液滴で `κ` が定数，`g=0` のとき，

```text
[[p]] = σ κ = const
```

を満たす piecewise constant pressure が存在する。
その場合

```text
G_Γ(p; j) = 0
=> u^{n+1}=0.
```

寄生流れは出ない。これが balanced force の本来の役割。

#### 毛管波

毛管波では

```text
κ(x) ≈ -η_xx(x)
```

なので `j(x)=σ κ(x)` は界面上で変化する。
piecewise constant pressure では `[[p]]=j(x)` を満たせない。
各相内で harmonic pressure が立ち，界面を加速する。

```text
G_Γ(p; j) ≠ 0
=> u_t ≠ 0
=> η_tt + ω^2 η = 0
```

したがって同じ `G_Γ(p;j)` が，静止液滴ではゼロ速度，
毛管波では復元速度を出す。

#### 上昇気泡

上昇気泡では `g≠0` で，body force と interface stress の同時平衡を考える。
もし静止解が存在するなら

```text
α ∇p = g,
[[p]] = σ κ
```

を同時に満たす必要がある。
軽い気泡が重い液体中にある場合，この二条件は一般には両立しない。
両立しない部分が buoyancy residual として残り，気泡を上昇させる。

したがって上昇気泡も毛管波も，同じ判定でよい：

```text
residual = u_f^*/Δt + a_f - α_f G_Γ(p; j)_f
```

の divergence-free 成分が運動を生む。

## buoyancy の扱い

浮力も専用ロジックにしない。
body acceleration `a_f` として projection に渡し，同じ jump-aware operator で
勾配成分を除く。

```text
a_f = g_f + a_viscous/explicit + ...
```

投影は

```text
P_Γ(a) = a - α G_Γ L_Γ^{-1} D a
```

を実現する。ここで `L_Γ = D α G_Γ`。

この構造により：

- 完全な hydrostatic equilibrium は相殺される。
- 密度差と界面ジャンプ条件が両立しない場合だけ residual が残る。
- 上昇気泡はその residual で動く。
- 毛管波は `j(x)` の非定数性で動く。

## 実装設計

### 新しい抽象

```text
InterfaceStressClosure
  inputs:
    psi, phi/interface_geometry, kappa, sigma, rho, mu, gravity
  outputs:
    pressure_jump j_p = σ κ
    optional_normal_derivative_jump j_q
    face_cut_geometry Γ_f
    body_acceleration_faces a_f
```

`ch14_capillary`，`ch14_rising_bubble`，`ch14_rayleigh_taylor` は
全てこの closure を使う。

### projection 側

```text
AffineJumpProjection
  G_affine(p, jump_ctx) -> face pressure acceleration
  L_affine(p, jump_ctx) = D α G_affine(p, jump_ctx)
  solve:
    L_affine(p; j) = D(u*/dt + a)
  correct:
    u_new = u* + dt a - dt α G_affine(p; j)
```

禁止事項：

- `p_total = p_base + σ κ (1-ψ)` として通常圧力場に戻すこと。
- `L(J)` を RHS から引き，最後に `J` を足すこと。
- cross-interface face coefficient を常に 0 にして，jump flux まで消すこと。

### face flux

phase-separated coefficient で cross-interface normal flux を 0 にする場合でも，
jump contribution まで 0 にしてはいけない。

概念的には

```text
α_f G_Γ(p;j)_f
  = α_f (p^+ - p^- - j_Γ) / d_f
```

であり，`p^+ - p^- - j_Γ` がゼロなら flux はゼロ，
非ゼロなら物理的な jump residual が face acceleration になる。

## CSF との関係

表面張力の表現は二つのどちらか一つにする。

### A: jump form

```text
[[p]] = σ κ
```

を `G_Γ` に入れる。今回の推奨。

### B: force form

```text
f_σ = σ κ n δ_Γ
```

を face force として入れる。この場合も，
`f_σ` と `∇p` は同じ discrete force space で balanced に組む必要がある。

禁止：

- jump form と CSF form を同時に入れること。
- jump form を通常 pressure potential に変換して消せる形にすること。

## 汎用検証計画

毛管波専用テストではなく，interface-stress closure の共通テストとして設計する。

### T1: constant-curvature static droplet

条件：

```text
g=0, κ=const, [[p]]=σ κ.
```

期待：

```text
||u||_inf ≈ 0,
D u ≈ 0,
pressure jump error ≈ 0.
```

目的：balanced equilibrium を守る。

### T2: manufactured sinusoidal jump on flat interface

条件：

```text
j(x)=j0 cos(kx), u*=0, g=0.
```

解析解：各相 pressure は Laplace 方程式の harmonic extension。

期待：

```text
p_total not ≈ 0,
G_Γ(p;j) nonzero,
divergence-free acceleration has correct sign and scale.
```

目的：現在の `p_base≈-J` cancellation を禁止する。

### T3: small-amplitude capillary wave

条件：

```text
A0 k << 1, g=0.
```

期待：

```text
a_m(t) crosses zero near T_omega/4,
phase error decreases with resolution,
volume drift remains small.
```

目的：毛管復元力が動的に働くことを確認する。

### T4: hydrostatic flat two-phase column

条件：

```text
flat interface, g≠0, κ=0.
```

期待：

```text
u=0,
hydrostatic pressure gradient balances rho g.
```

目的：buoyancy の well-balanced 性を確認する。

### T5: rising bubble residual

条件：

```text
circle bubble, g≠0, σ>0.
```

期待：

```text
static compatibility residual nonzero,
initial acceleration upward,
volume drift small,
terminal/rise diagnostics physical.
```

目的：毛管波と同じ closure が上昇気泡の浮力 residual を作ることを確認する。

### T6: energy audit

条件：closed no-slip domain。

期待：

```text
Δ[K + σ|Γ| + gravitational potential] <= external work - viscous dissipation + tolerance.
```

目的：見た目だけの fix を排除する。

## 実装順序

1. `InterfaceStressClosure` の data contract を追加する。
2. `AffineJumpProjection` の operator-only unit test を作る。
3. 現在の `jump_decomposition` を production から外し，legacy として保持する。
4. `ch14_capillary.yaml`，`ch14_rising_bubble.yaml`，`ch14_rayleigh_taylor.yaml`
   を同じ `pressure_jump_affine` closure に接続する。
5. T1/T2 を最初に通す。T2 が通らない限り毛管波を回さない。
6. T3/T4/T5 を順に実験する。
7. 最後に §14 の物理 benchmark を更新する。

## 判断

Balanced Force は捨てない。
むしろ，Balanced Force を **equilibrium-only cancellation** に限定し，
非平衡の界面応力 residual を保存するよう数学契約を作り直す。

正しい原理は：

```text
静止平衡は消す。
物理的非平衡は消さない。
どちらかは同じ jump-aware projection が判定する。
```

[SOLID-X] Design artifact only; no production code changed.
