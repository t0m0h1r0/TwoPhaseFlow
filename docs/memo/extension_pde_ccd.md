# Extension PDE × CCD: 界面近傍O(h⁶)精度の実現

**Technical Note — Extension PDE と CCD compact scheme の接続**

---

## 1. 問題設定

### 1.1 CCD の制約

Combined Compact Difference (CCD) は5点コンパクトステンシル $(i-2, \ldots, i+2)$ で
$f, f', f''$ を同時に $O(h^6)$ で求解する:

$$
\alpha_1(f'_{i-1} + f'_{i+1}) + f'_i
= \frac{a_1}{h}(f_{i+1} - f_{i-1})
+ b_1 h(f''_{i+1} - f''_{i-1})
$$

$$
\beta_2(f''_{i-1} + f''_{i+1}) + f''_i
= \frac{a_2}{h^2}(f_{i-1} - 2f_i + f_{i+1})
+ \frac{b_2}{h}(f'_{i+1} - f'_{i-1})
$$

**根本的制約**: ステンシルが界面 $\Gamma$ を跨ぐと、不連続面を微分して Gibbs 振動が発生する。
CCD は **場が滑らか ($C^\infty$) であること**を前提とする。

### 1.2 既存手法の限界

| 手法 | 界面表現 | CCD親和性 | 界面近傍精度 | 問題 |
|------|---------|-----------|-------------|------|
| CSF | 正則化 $\delta_\varepsilon$ | ○（場が滑らか） | $O(\varepsilon^2) \approx O(h^2)$ | モデル誤差が律速 |
| GFM | 不連続 $[p] = \kappa/\mathrm{We}$ | ×（ステンシル破綻） | $O(h^2)$† | CCD演算子が不定値 |

> **† GFM+CCD の実験結果**: CCD product-rule PPE 演算子が不定値（固有値に正値が混在）であるため、
> LGMRES が発散し圧力符号が反転。直接LU法では正しい符号だが振幅が $O(h^{-2})$ で発散。
> 根本原因は CCD boundary stencil の非対称性に由来する正の固有値。

### 1.3 目標

**Extension PDE** により、CCD ステンシルが参照する場を
界面の両側で $C^\infty$ に保ち、界面直近まで $O(h^6)$ 精度を維持する。

---

## 2. Extension PDE の理論

### 2.1 基本方程式

Aslam (2004) に基づく定常場延長:

$$
\frac{\partial q}{\partial\tau} + S(\phi)\,\hat{\mathbf{n}} \cdot \nabla q = 0
\tag{ext-pde}
$$

| 記号 | 定義 |
|------|------|
| $q$ | 延長する物理量（$p, u, v, \ldots$） |
| $\tau$ | 仮想時間（物理時間 $t$ とは独立） |
| $\phi$ | signed distance function（液体 $> 0$, 気体 $< 0$） |
| $\hat{\mathbf{n}} = \nabla\phi / \|\nabla\phi\|$ | 界面法線（液体→気体方向） |
| $S(\phi) = \mathrm{sign}(\phi)$ | 伝搬方向の符号 |

### 2.2 物理的意味

(ext-pde) は **法線方向に沿った定数外挿** を仮想時間で伝搬する:

- $S(\phi) = +1$（液体側, $\phi > 0$）: 液体の値を気体側に向かって延長
- $S(\phi) = -1$（気体側, $\phi < 0$）: 気体の値を液体側に向かって延長

$$
\lim_{\tau \to \infty} q(\mathbf{x}, \tau)
= q_\Gamma\bigl(\mathbf{x}_\Gamma(\mathbf{x})\bigr)
$$

ここで $\mathbf{x}_\Gamma(\mathbf{x})$ は $\mathbf{x}$ から界面 $\Gamma$ への最近接点。
収束後、$q$ は界面での値を法線方向に一定に延長した場となる。

### 2.3 CCD との整合性

Extension PDE 適用後:

| 領域 | $q$ の性質 | CCD精度 |
|------|-----------|---------|
| 界面から離れた液体 | 元の物理量（変更なし） | $O(h^6)$ |
| 界面近傍液体 | 元の物理量 | $O(h^6)$ |
| 界面近傍気体（延長済み） | **液体側から滑らかに延長** | **$O(h^6)$** |
| 界面から離れた気体 | 延長値（物理的意味なし） | $O(h^6)$ |

CCD ステンシルが界面を跨いでも、参照する場は $C^\infty$ → Gibbs 振動なし → **$O(h^6)$ 維持**。

---

## 3. 再初期化 PDE との構造比較

### 3.1 再初期化 PDE（§05c, 実装済み）

$$
\frac{\partial\psi}{\partial\tau}
+ \underbrace{\nabla \cdot \bigl[\psi(1-\psi)\hat{\mathbf{n}}\bigr]}_{\text{圧縮（陽的）}}
= \underbrace{\nabla \cdot (\varepsilon \nabla \psi)}_{\text{拡散（陰的CN）}}
$$

演算子分離: 圧縮は CCD+Dissipative filter（陽的 Euler）、拡散は CCD Eq-II CN（陰的 Thomas）。

### 3.2 Extension PDE

$$
\frac{\partial q}{\partial\tau} + S(\phi)\,\hat{\mathbf{n}} \cdot \nabla q = 0
$$

純粋な双曲型（拡散項なし）。CCD $D^{(1)}$ による空間微分 + 陽的時間積分のみ。

### 3.3 構造対応表

| 要素 | 再初期化 | Extension PDE |
|------|---------|---------------|
| 型 | 放物型（圧縮+拡散） | 双曲型（移流のみ） |
| 空間微分 | CCD $D^{(1)}$ + Dissipative filter | CCD $D^{(1)}$ |
| 時間積分 | Forward Euler + CN | Forward Euler（or RK） |
| CFL制約 | $\Delta\tau \leq \min(0.5h^2/(2N_d\varepsilon),\;0.5h)$ | $\Delta\tau \leq 0.5h$（双曲CFL） |
| 反復回数 | 4回（固定） | 3–5回（界面近傍のみ） |
| 対象変数 | $\psi$（CLS場） | $p, u, v$（任意の物理量） |
| 拡散項 | $\varepsilon\nabla^2\psi$（CN陰的） | なし |

Extension PDE は再初期化の**圧縮ステージの亜型**であり、拡散を持たない分さらに単純。

---

## 4. アルゴリズム設計

### 4.1 Extension PDE の CCD 離散化

仮想時間ステップ $m$ における更新:

$$
q_i^{m+1} = q_i^m - \Delta\tau\,S(\phi_i)\sum_{d=1}^{N_d}\hat{n}_{d,i}\left(D_d^{(1)}q^m\right)_i
\tag{ext-discrete}
$$

ここで $D_d^{(1)}$ は CCD 1次微分演算子（$O(h^6)$ 精度）。

**DCCD フィルタの適用**:

界面近傍の高周波安定化のため、Dissipative CCD フィルタ $\varepsilon_d = 0.05$ を適用:

$$
\widetilde{(D_d^{(1)}q)}_i
= (D_d^{(1)}q)_i
+ \varepsilon_d^{(\mathrm{ext})}\bigl[(D_d^{(1)}q)_{i+1} - 2(D_d^{(1)}q)_i + (D_d^{(1)}q)_{i-1}\bigr]
$$

### 4.2 CFL 条件

(ext-pde) の特性速度は $|S(\phi)\hat{\mathbf{n}}| \leq 1$ であるため:

$$
\Delta\tau_{\mathrm{ext}} \leq C_{\mathrm{CFL}}\,h, \qquad C_{\mathrm{CFL}} = 0.5
$$

### 4.3 全体アルゴリズム（1物理タイムステップ内）

```
Step 1–2: CLS移流 + 再初期化         （既存）
Step 3:   物性値更新 ρ̃, μ̃             （既存）
Step 4:   曲率 κ 計算（CCD）           （既存）
──────────────────────────────────────────────
Step 5:   Predictor u* 計算            （既存）
Step 5b:  壁面BC適用                    （既存）
──────────────────────────────────────────────
Step 5c:  ★ u* を Extension PDE で延長  （新規）
          φ = H_ε⁻¹(ψ)（既存キャッシュ）
          n̂ = ∇φ / |∇φ|  via CCD
          for m = 1, ..., n_ext:
            u*_ext ← u* − Δτ S(φ) (n̂·∇u*_ext)
          u* ← u*_ext
──────────────────────────────────────────────
Step 6:   PPE求解 L(δp) = (1/Δt)∇·u*   （既存CCD PPE）
Step 6b:  ★ δp を Extension PDE で延長   （新規）
          for m = 1, ..., n_ext:
            δp_ext ← δp − Δτ S(φ) (n̂·∇δp_ext)
          δp ← δp_ext
──────────────────────────────────────────────
Step 7:   速度補正 u^{n+1} = u* − (Δt/ρ̃)∇(δp)  （CCD, 延長済み場で O(h⁶)）
Step 7b:  圧力更新 p^{n+1} = p^n + δp
```

### 4.4 延長対象と戦略

| 物理量 | 延長方向 | 理由 |
|--------|---------|------|
| $u^*, v^*$（予測速度） | 両相→対岸 | PPE divergence 計算で CCD ステンシルが界面を跨ぐ |
| $\delta p$（圧力増分） | 両相→対岸 | 速度補正 $\nabla(\delta p)$ で CCD が界面を跨ぐ |
| $p^n$（IPC圧力） | 両相→対岸 | Predictor IPC項 $-\nabla p^n$ で CCD が界面を跨ぐ |

**注**: 密度 $\rho$ と粘性 $\mu$ は CLS 正則化 Heaviside $H_\varepsilon$ で既に滑らかであるため延長不要。
曲率 $\kappa$ も $\psi$ から直接計算（$\psi$ は CLS で滑らか）であるため延長不要。

---

## 5. 表面張力の扱い

### 5.1 CSF + Extension PDE（推奨）

Extension PDE は界面力モデルではなく、**場の滑らか化手法**である。
表面張力の扱いは CSF（Balanced-Force）を維持:

$$
\mathbf{f}_\sigma = \frac{\kappa}{\mathrm{We}}\nabla\psi
$$

**精度構造**:

| コンポーネント | Extension なし | Extension あり |
|--------------|--------------|---------------|
| CSF モデル誤差 | $O(\varepsilon^2)$ | $O(\varepsilon^2)$ |
| CCD 微分精度（内部） | $O(h^6)$ | $O(h^6)$ |
| CCD 微分精度（界面近傍） | $O(h^6)$（場が滑らか） | $O(h^6)$ |
| PPE 解の界面精度 | $O(h^6)$（CSF場が滑らか） | $O(h^6)$ |
| $\nabla(\delta p)$ 界面精度 | **$O(1)$**（圧力ジャンプ）† | **$O(h^6)$** |

> **† 重要**: CSF でも圧力場 $p$ には Laplace ジャンプ $\Delta p = \kappa/\mathrm{We}$ が存在する。
> ジャンプ幅は $O(\varepsilon)$ で平滑化されているが、CCD の5点ステンシルが
> この遷移領域を跨ぐと $O(h^4)$ 程度の精度劣化が起こりうる。
> Extension PDE で $\delta p$ を延長すれば、この劣化も除去できる。

### 5.2 GFM なしでも Extension PDE は有効

GFM は不要。Extension PDE の真の価値は:

1. **圧力勾配の高精度化**: $\nabla(\delta p)$ が界面近傍でも $O(h^6)$
2. **IPC 項の安定化**: $\nabla p^n$ のステンシル問題を解消
3. **CSF Balanced-Force の強化**: 全演算子が同一CCD → parasitic current さらに低減

---

## 6. 精度解析

### 6.1 延長誤差

Extension PDE の離散化誤差:

$$
q_{\mathrm{ext}} = q_\Gamma + O(\Delta\tau^p \cdot n_{\mathrm{ext}}) + O(h^6)
$$

- 時間積分誤差: Forward Euler $p=1$、RK3 $p=3$
- 空間微分誤差: CCD $O(h^6)$
- $n_{\mathrm{ext}} = 3$–$5$ 反復で界面から2–3セル幅を延長

### 6.2 全体精度バジェット

| コンポーネント | 精度 | 律速? |
|--------------|------|-------|
| CLS 移流 | $O(h^5)$（DCCD + TVD-RK3） | |
| 曲率 $\kappa$ | $O(h^6)$（CCD from $\psi$） | |
| CSF 表面張力モデル | $O(\varepsilon^2) \approx O(h^2)$ | **律速** |
| PPE 求解 | $O(h^6)$（CCD product-rule） | |
| 速度補正 $\nabla(\delta p)$ | $O(h^6)$（Extension 後） | |
| IPC $\nabla p^n$ | $O(h^6)$（Extension 後） | |
| **全体空間精度** | **$O(h^2)$（CSF律速）** | |

CSF モデル誤差 $O(\varepsilon^2)$ が依然として律速。
ただし Extension PDE により **CSF 以外の全コンポーネントが $O(h^5)$ 以上**となり、
CSF モデル誤差のみが純粋に測定可能になる。

### 6.3 CSF律速の将来的解消

Extension PDE インフラが整えば、将来的に CSF → GFM 移行時の障壁が除去される:

1. Extension PDE で場を延長 → CCD が $C^\infty$ 場を参照
2. GFM ジャンプ条件を CCD PPE に直接組み込み（IIM/MIB 的アプローチ）
3. 界面近傍まで $O(h^6)$ 精度

Extension PDE は CSF→GFM 移行の**前提条件**であり、今回の実装は将来への投資でもある。

---

## 7. 実装ノート

### 7.1 既存インフラとの対応

```python
class FieldExtender:
    """Extension PDE: ∂q/∂τ + S(φ) n̂·∇q = 0
    
    Reinitializer の圧縮ステージと同型。
    CCD D^(1) + Forward Euler（or TVD-RK3）で求解。
    """
    def __init__(self, backend, grid, ccd, n_iter=5, cfl=0.5):
        self.ccd = ccd          # 既存 CCDSolver
        self.n_iter = n_iter    # 仮想時間反復回数
        self.cfl = cfl
        
    def extend(self, q, phi, direction=+1):
        """q を direction 方向に延長。
        
        direction = +1: φ>0 側の値を φ<0 側に延長
        direction = -1: φ<0 側の値を φ>0 側に延長
        """
```

### 7.2 計算コスト

| 操作 | コスト/反復 | 反復数 | 合計 |
|------|-----------|--------|------|
| CCD $D^{(1)}$ per axis | $O(N)$ | $N_d$ axes | $O(N_d \cdot N)$ |
| 法線 $\hat{\mathbf{n}}$ | $O(N)$ | 1回（キャッシュ） | $O(N_d \cdot N)$ |
| Euler更新 | $O(N)$ | 1 | $O(N)$ |
| **合計 per 反復** | | | $O(N_d \cdot N)$ |
| **全反復** | | $n_{\mathrm{ext}}$ | $O(n_{\mathrm{ext}} \cdot N_d \cdot N)$ |

$n_{\mathrm{ext}} = 5$, $N_d = 2$ の場合: CCD 微分10回/物理量。
Predictor 全体が CCD 微分 $O(10)$ 回であることを考えると、
延長の追加コストは **既存ステップの $O(1)$ 倍**。

---

## 8. 参考文献

- Aslam, T.D. (2004). "A partial differential equation approach to multidimensional extrapolation." *J. Comput. Phys.* 193(1), 349–355.
- Fedkiw, R.P., Aslam, T., Merriman, B., Osher, S. (1999). "A Non-Oscillatory Eulerian Approach to Interfaces in Multimaterial Flows (the Ghost Fluid Method)." *J. Comput. Phys.* 152(2), 457–492.
- Kang, M., Fedkiw, R.P., Liu, X.D. (2000). "A Boundary Condition Capturing Method for Multiphase Incompressible Flow." *J. Sci. Comput.* 15(3), 323–360.
