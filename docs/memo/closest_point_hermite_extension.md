# Closest-Point Hermite Extension: O(h^6) 界面越し場延長

**Technical Memo — Extension PDE の代替: CCD Hermite 補間による直接延長**

Date: 2026-04-03

---

## 1. 動機

### 1.1 現状の律速

現行 Extension PDE (Aslam 2004) は1次風上差分で離散化され、
延長帯の精度は $O(h^1)$ に留まる（§10.2.2, 表 10.7 で実測確認済み）。

これが本手法のパイプライン全体で唯一の低次精度コンポーネントであり、
CCD $O(h^6)$ の恩恵を界面近傍で損なっている。

### 1.2 根本的な問い

Extension PDE の定常解は **最近接点延長** そのものである:

$$
\lim_{\tau \to \infty} q_\mathrm{ext}(\mathbf{x}) = q\bigl(\mathbf{x}_\Gamma(\mathbf{x})\bigr)
$$

ここで $\mathbf{x}_\Gamma(\mathbf{x})$ は $\mathbf{x}$ から界面 $\Gamma$ への最近接点。

**であれば、PDE を解かずに最近接点の値を直接補間すればよいのではないか？**

CCD は各格子点で $(f, f', f'')$ を同時に返す。
この Hermite データを用いれば、任意点での $O(h^6)$ 補間が可能である。

---

## 2. アルゴリズム

### 2.1 1D の基本構造

ソース側（$\phi < 0$、液体）の場 $q$ をターゲット側（$\phi \geq 0$、気体）へ延長する。

```
ターゲット点 x  (φ(x) > 0)
  │
  │ Step 1: 最近接点
  │   x_Γ = x − φ(x) · n̂(x)          ← CCD ∇φ で O(h^6)
  │
  │ Step 2: ソース側セル特定
  │   x_Γ が [x_{i-1}, x_i] に属する   ← x_i はソース側最近傍格子点
  │
  │ Step 3: Hermite 補間
  │   P(x_Γ) = Hermite₅(f_{i-1}, f'_{i-1}, f''_{i-1},
  │                       f_i,    f'_i,    f''_i;    x_Γ)
  │
  └── q_ext(x) = P(x_Γ)               ← O(h^6) 精度
```

### 2.2 CCD Hermite 5次補間

CCD は各格子点 $x_i$ で $(f_i, f'_i, f''_i)$ を同時求解する。
隣接2点 $x_a, x_b$ ($h = x_b - x_a$) の6個のデータから5次 Hermite 多項式を構成する:

$$
P(\xi) = \sum_{k=0}^{5} c_k \xi^k, \qquad \xi = \frac{x - x_a}{h}
$$

**拘束条件** (6個 → 一意):

| $k$ | $\xi = 0$ | $\xi = 1$ |
|-----|-----------|-----------|
| 値 | $P(0) = f_a$ | $P(1) = f_b$ |
| 1階 | $P'(0) = h f'_a$ | $P'(1) = h f'_b$ |
| 2階 | $P''(0) = h^2 f''_a$ | $P''(1) = h^2 f''_b$ |

**係数の閉形式:**

$$
\begin{aligned}
c_0 &= f_a \\
c_1 &= h f'_a \\
c_2 &= \tfrac{1}{2} h^2 f''_a \\
c_3 &= 10(f_b - f_a) - h(6f'_a + 4f'_b) + \tfrac{h^2}{2}(3f''_b - f''_a - \tfrac{1}{2}h^2 f''_a)
\end{aligned}
$$

ただし $c_3, c_4, c_5$ は6元連立を解いて得る（後述 §2.5）。

### 2.3 片側ステンシルの扱い

$x_\Gamma$ が界面の直近（ソース側最端セル）にある場合、
標準の2点 Hermite 補間は両方のステンシル点がソース側にある必要がある。

**場合分け:**

```
Case 1: x_Γ ∈ [x_{i-1}, x_i], 両方ソース側
  → 標準 Hermite₅(x_{i-1}, x_i)  ← 補間、O(h^6)

Case 2: x_Γ ∈ [x_i, x_{i+1}], x_{i+1} がターゲット側
  → 片側外挿 Hermite₅(x_{i-1}, x_i)  ← 外挿距離 ≤ h
```

**外挿誤差の評価:**

Hermite₅ の補間誤差は:
$$
|P(x) - f(x)| \leq \frac{|f^{(6)}(\zeta)|}{6!}\, |(x-x_a)^3(x-x_b)^3|
$$

Case 2（外挿）では $x_\Gamma \in [x_i, x_i + h]$:

$$
|(x_\Gamma - x_{i-1})^3(x_\Gamma - x_i)^3| \leq (2h)^3 \cdot h^3 = 8h^6
$$

よって **外挿でも $O(h^6)$ が保たれる**。

### 2.4 2D への拡張: テンソル積逐次補間

2D の最近接点 $\mathbf{x}_\Gamma = (\xi, \eta)$ に対して:

```
Step 1: y 方向の各行 j = j₀, j₀+1 について:
  → x 方向に Hermite₅ 補間で q(ξ, y_j), q_y(ξ, y_j), q_yy(ξ, y_j) を評価

Step 2: 得られた y 方向データで Hermite₅ 補間:
  → q_ext = Hermite₅(η; [q(ξ,y_{j₀}), q_y, q_yy], [q(ξ,y_{j₀+1}), q_y, q_yy])
```

**必要な CCD データ:**

| データ | CCD 演算 | 用途 |
|--------|---------|------|
| $q, q_x, q_{xx}$ | `ccd.differentiate(q, axis=0)` | x 方向 Hermite |
| $q_y, q_{yy}$ | `ccd.differentiate(q, axis=1)` | y 方向 Hermite |
| $q_{xy}$ | `ccd.differentiate(q_y, axis=0)` | y微分の x 方向補間 |
| $q_{xyy}$ | `ccd.differentiate(q_{yy}, axis=0)` | y2階微分の x 方向補間 |

合計: CCD 微分 4 回。現行 Extension PDE（$n_\mathrm{ext} \times 2$ 軸 = 10 回）より少ない。

### 2.5 Hermite 5次補間の係数導出

正規化座標 $\xi = (x - x_a)/h \in [0, 1]$ として:

$$
P(\xi) = c_0 + c_1\xi + c_2\xi^2 + c_3\xi^3 + c_4\xi^4 + c_5\xi^5
$$

$F_a = f_a,\ F_b = f_b,\ G_a = hf'_a,\ G_b = hf'_b,\ H_a = h^2f''_a,\ H_b = h^2f''_b$ として:

$$
\begin{aligned}
c_0 &= F_a \\
c_1 &= G_a \\
c_2 &= \tfrac{1}{2}H_a \\
c_3 &= 10(F_b - F_a) - 6G_a - 4G_b + \tfrac{1}{2}(H_b - 3H_a) \\
c_4 &= 15(F_a - F_b) + 8G_a + 7G_b + \tfrac{1}{2}(3H_a - 2H_b) \\
c_5 &= 6(F_b - F_a) - 3(G_a + G_b) + \tfrac{1}{2}(H_b - H_a)
\end{aligned}
$$

**検証**: $P(0) = c_0 = F_a$ ✓,
$P(1) = c_0 + c_1 + c_2 + c_3 + c_4 + c_5 = F_b$ ✓
（代入して確認可能）。

---

## 3. 誤差解析

### 3.1 誤差の分解

延長値の全誤差:

$$
|q_\mathrm{ext}(\mathbf{x}) - q(\mathbf{x}_\Gamma^\mathrm{true})| \leq E_\mathrm{loc} + E_\mathrm{interp}
$$

| 成分 | 定義 | オーダー |
|------|------|----------|
| $E_\mathrm{loc}$ | 最近接点の位置誤差 $\|\mathbf{x}_\Gamma - \mathbf{x}_\Gamma^\mathrm{true}\|$ による $q$ の変化 | $O(h^6) \cdot \|\nabla q\|$ |
| $E_\mathrm{interp}$ | Hermite 補間誤差 | $O(h^6)$ |

**$E_\mathrm{loc}$ の詳細:**

$$
\mathbf{x}_\Gamma = \mathbf{x} - \phi(\mathbf{x})\,\hat{\mathbf{n}}(\mathbf{x})
$$

- $\phi$ の CCD 精度: $O(h^6)$（滑らかな CLS 場 $\psi$ からの逆変換）
- $\hat{\mathbf{n}} = \nabla\phi/|\nabla\phi|$ の CCD 精度: $O(h^6)$

位置誤差: $\|\delta\mathbf{x}_\Gamma\| = O(h^6)$（$|\nabla\phi| \approx 1$ の SDF 条件下）

### 3.2 現行手法との精度比較

| 手法 | 延長帯精度 | 理論的根拠 |
|------|-----------|-----------|
| 風上 Extension PDE | $O(h^1)$ | 1次風上差分 |
| WENO5 Extension PDE | $O(h^5)$ | WENO5 空間精度 |
| Aslam 2次延長 | $O(h^3)$ | 法線2階微分まで延長 |
| **最近接点 Hermite** | **$O(h^6)$** | **CCD Hermite 補間** |

**5桁の精度向上**: $O(h^1) \to O(h^6)$。
$N = 128$ ($h = 1/128$) で $10^{-2} \to 10^{-12}$ のオーダー差。

### 3.3 延長場の滑らかさ

最近接点延長は法線方向定数延長を与える:

$$
\frac{\partial q_\mathrm{ext}}{\partial n} = 0
$$

延長場の微分:

$$
\frac{\partial q_\mathrm{ext}}{\partial x_i} = \sum_j \frac{\partial q}{\partial x_j}\bigg|_{\mathbf{x}_\Gamma} \cdot \frac{\partial (x_\Gamma)_j}{\partial x_i}
$$

最近接点写像 $\mathbf{x} \mapsto \mathbf{x}_\Gamma$ の Jacobian:

$$
\frac{\partial (x_\Gamma)_j}{\partial x_i} = \delta_{ij} - n_i n_j - \phi\,\frac{\partial n_j}{\partial x_i}
$$

界面の曲率半径 $R = 1/\kappa$ に対し $|\phi| \leq 2h$ の延長帯では:

$$
\left\|\frac{\partial \mathbf{x}_\Gamma}{\partial \mathbf{x}}\right\| = O(1) \quad (\text{if } \kappa h \ll 1)
$$

したがって $q_\mathrm{ext}$ は延長帯内で **$C^\infty$ に近い滑らかさ**を持ち、
CCD ステンシルの前提条件を満たす。

### 3.4 特異点: 中心軸問題

凹界面では、異なる界面点からの法線が交差する **中心軸 (medial axis)** が存在する。
中心軸上では最近接点が多価となり、延長場に折れ目（$C^0$ 不連続）が生じる。

**影響の評価:**

中心軸までの距離 $d_\mathrm{MA} \approx R = 1/\kappa$。
延長帯幅は $2$--$3h$ であるため:

$$
d_\mathrm{MA} \gg 3h \iff \kappa h \ll 1/3
$$

この条件は通常の格子解像度で満たされる
（$\kappa h \geq 1/3$ では界面自体が解像不足）。

---

## 4. 計算コスト比較

### 4.1 操作量

| 手法 | CCD 微分回数 | 反復 | 合計コスト |
|------|------------|------|-----------|
| 風上 Extension PDE | $2 n_\mathrm{ext}$ = 10 | $n_\mathrm{ext}$ = 5 | $10 \times O(N)$ |
| **最近接点 Hermite** | **4** | **0** | **$4 \times O(N) + O(N_\Gamma)$** |

$N_\Gamma$: ターゲット側延長点の数（全格子点の一部、$O(\sqrt{N})$〜$O(N)$）。

### 4.2 コスト削減の本質

Extension PDE は「PDE 求解→定常解→最近接点値」の間接経路を辿る。
最近接点 Hermite は定常解を **直接計算**する → 仮想時間反復が不要。

---

## 5. 実装設計

### 5.1 `ClosestPointExtender` クラス

```python
class ClosestPointExtender:
    """Closest-point extension via CCD Hermite interpolation.

    Replaces FieldExtender (Aslam 2004 upwind PDE) with direct
    Hermite interpolation using CCD's (f, f', f'') data.
    Achieves O(h^6) vs O(h^1) in the extension band.
    """

    def __init__(self, backend, grid, ccd):
        self.backend = backend
        self.grid = grid
        self.ccd = ccd
        self.ndim = grid.ndim

    def extend(self, q, phi):
        """Extend q from source (phi<0) to target (phi>=0).

        Returns:
            q_ext: extended field, smooth across interface.
        """
        # 1. Compute normals via CCD
        n_hat = self._compute_normal(phi)

        # 2. CCD derivatives of q (source side)
        dq = self._compute_derivatives(q)

        # 3. For each target point, find closest point and interpolate
        q_ext = q.copy()
        target_mask = phi >= 0

        for idx in zip(*np.where(target_mask)):
            x_gamma = self._closest_point(idx, phi, n_hat)
            q_ext[idx] = self._hermite_interp_2d(
                x_gamma, q, dq, phi
            )

        return q_ext
```

### 5.2 1D Hermite 補間の実装

```python
def _hermite_interp_1d(self, xi, f, fp, fpp, x_nodes):
    """Quintic Hermite interpolation at xi using CCD data.

    Args:
        xi: evaluation point
        f, fp, fpp: arrays of (value, 1st deriv, 2nd deriv) at x_nodes
        x_nodes: grid positions

    Returns:
        interpolated value at xi
    """
    # Find bracketing source-side interval
    i = self._find_source_interval(xi, x_nodes)
    h = x_nodes[i+1] - x_nodes[i]
    t = (xi - x_nodes[i]) / h  # normalized coordinate [0,1] or slightly outside

    Fa, Ga, Ha = f[i], h*fp[i], h**2*fpp[i]
    Fb, Gb, Hb = f[i+1], h*fp[i+1], h**2*fpp[i+1]

    c0 = Fa
    c1 = Ga
    c2 = 0.5 * Ha
    c3 = 10*(Fb-Fa) - 6*Ga - 4*Gb + 0.5*(Hb - 3*Ha)
    c4 = 15*(Fa-Fb) + 8*Ga + 7*Gb + 0.5*(3*Ha - 2*Hb)
    c5 = 6*(Fb-Fa) - 3*(Ga+Gb) + 0.5*(Hb - Ha)

    return c0 + t*(c1 + t*(c2 + t*(c3 + t*(c4 + t*c5))))
```

### 5.3 Builder への統合

```python
# builder.py: ClosestPointExtender を FieldExtender の代替として注入
if config.numerics.extension_method == "hermite":
    field_extender = ClosestPointExtender(backend, grid, ccd)
elif config.numerics.n_extend > 0:
    field_extender = FieldExtender(backend, grid, ccd, n_iter=config.numerics.n_extend)
```

---

## 6. 検証計画

### 6.1 単体テスト（§10.2.2 再実験）

**(a) 場延長の格子収束テスト（1D）**

現行テスト（表 10.7）と同一条件:
- $q(x) = 1 + \cos(\pi x)$（$x < 0.5$）、界面 $x = 0.5$
- $N = 32, 64, 128, 256$
- 計測: $L^\infty$ 誤差（延長帯 $x \in [0.52, 0.55]$）

**期待結果:**

| $N$ | 風上 PDE (現行) | Hermite (提案) |
|-----|----------------|----------------|
| 32  | $9.8 \times 10^{-2}$ | $\sim 10^{-6}$ |
| 64  | $4.9 \times 10^{-2}$ | $\sim 10^{-8}$ |
| 128 | $2.5 \times 10^{-2}$ | $\sim 10^{-10}$ |
| 256 | $1.2 \times 10^{-2}$ | $\sim 10^{-12}$ |

収束次数: $O(h^1) \to O(h^6)$。

**(b) Young-Laplace 圧力跳びテスト**

現行テスト（表 10.8）と同一条件:
- 円形液滴 $R=0.25$, $\rho_l/\rho_g = 1000$, $We = 1$
- $N = 32, 64, 128$

期待: $N = 64$ での相対誤差が大幅に改善。
$N = 32$ の破綻は曲率解像不足に起因するため、改善は限定的。

### 6.2 波及効果の検証

Extension PDE 精度が $O(h^6)$ になると、以下が変化する:

| 影響箇所 | 現行の記述 | 改訂後 |
|---------|-----------|--------|
| §10.1.3 曲率結論 | 「Extension PDE の $O(h^1)$ が律速するため経路選択は無影響」 | 経路 A/B の差が全体精度に寄与しうる |
| §10.4 総括表 | Extension PDE: $O(h^1)$ | $O(h^6)$ |
| §8.4 離散化節 | 「1次精度風上差分」 | Hermite 補間 |
| §8.6 精度まとめ | Extension PDE が律速 | CSF $O(\varepsilon^2)$ のみが律速 |

---

## 7. 理論的位置づけ

### 7.1 Extension PDE との等価性

最近接点 Hermite 補間は、Extension PDE の**解析的定常解を直接計算**する手法である。

```
Extension PDE:  ∂q/∂τ + sgn(φ) n̂·∇q = 0
                        ↓ (τ → ∞)
定常解:         q_ext(x) = q(x_Γ(x))     ← 最近接点の値
                        ↓
Hermite 補間:   q_ext(x) ≈ P₅(x_Γ(x))   ← CCD データで O(h^6) 近似
```

PDE は定常解への到達経路（仮想時間発展）を提供するが、
定常解の形が既知である以上、経路を辿る必要はない。

### 7.2 Aslam 高次延長との関係

Aslam (2004) の高次延長は法線微分も延長する:

- 0次: $q_\mathrm{ext} = q(\mathbf{x}_\Gamma)$ （定数延長）
- 1次: $q_\mathrm{ext} = q(\mathbf{x}_\Gamma) + (\nabla q \cdot \hat{\mathbf{n}})|_\Gamma \cdot d$ （線形延長）
- 2次: $+ \frac{1}{2}(\nabla^2 q \cdot \hat{\mathbf{n}}^2)|_\Gamma \cdot d^2$ （2次延長）

ここで $d$ は界面からの法線距離。

最近接点 Hermite は Aslam 0次と等価だが、
数値精度が $O(h^6)$（PDE の $O(h^1)$--$O(h^3)$ と比較して格段に高い）。
CCD ステンシルの要件（延長帯 2--3 セルの滑らかさ）に対しては、
高精度な0次延長で十分である。

### 7.3 CCD との自然な整合

CCD の設計思想は「$(f, f', f'')$ を同時求解して高次精度を実現する」こと。
最近接点 Hermite 補間は、この CCD の出力を**そのまま**補間基底として利用する。

```
CCD:    f_i, f'_i, f''_i を O(h^6) で同時求解
         ↓
Hermite: 2点 × 3DOF = 6DOF → 5次多項式 → O(h^6) 補間
```

これは CCD 基盤の二相流ソルバにとって**自然な拡張**であり、
外部スキーム（WENO, ENO）の導入を必要としない。

---

## 8. リスクと対策

| リスク | 深刻度 | 対策 |
|--------|--------|------|
| 高曲率 ($\kappa h \gtrsim 1/3$): 中心軸近接 | 中 | 曲率チェック: $\kappa h > 0.3$ なら風上 PDE にフォールバック |
| 片側外挿の安定性 | 低 | 外挿距離 $\leq h$、Hermite₅ の理論誤差は $O(h^6)$ |
| ソース側ステンシル不足（薄膜構造） | 低 | ソース側点が 2 点未満なら1次延長にフォールバック |
| CCD 境界スキーム精度 ($O(h^5)$) の影響 | 低 | 境界近傍では Interior $O(h^6)$ と同等 |

---

## 9. 結論

1. **最近接点 Hermite 補間は Extension PDE の解析的定常解を直接近似する**
   — PDE の仮想時間反復を完全に回避

2. **$O(h^1) \to O(h^6)$ の精度向上**（5桁）
   — CCD パイプライン全体の精度ボトルネックを除去

3. **計算コスト削減**: CCD 微分 10 回 → 4 回（反復なし）

4. **CCD との自然な整合**: $(f, f', f'')$ を Hermite 基底として直接再利用

5. **§8/§10 への波及**: 精度まとめ表、律速要因の記述が根本的に変化
   — Extension PDE が律速から外れ、CSF $O(\varepsilon^2)$ のみが律速に

---

## 参考文献

- Aslam, T.D. (2004). "A partial differential equation approach to multidimensional extrapolation." *J. Comput. Phys.* 193(1), 349--355.
- Chu, P.C. & Fan, C. (1998). "A three-point combined compact difference scheme." *J. Comput. Phys.* 140, 370--399.
- Ruuth, S.J. & Merriman, B. (2008). "A simple embedding method for solving partial differential equations on surfaces." *J. Comput. Phys.* 227(3), 1943--1961.
