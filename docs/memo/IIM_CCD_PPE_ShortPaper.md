# Application of the Immersed Interface Method to CCD-Based Pressure Poisson Equations in Two-Phase Flow

**IIM を CCD-PPE 解法に適用する理論的枠組み**

---

## 1. 問題設定と動機

現行ソルバ（§8）は **CSF + smoothed Heaviside** による smeared-interface アプローチを採る。
圧力 $p$ は連続場であり、界面ジャンプを陽に持たないため、CCD が $O(h^6)$ 精度を界面近傍でも維持できる。
しかし高密度比（$\rho_l/\rho_g \gg 1$）では、$\varepsilon$-smearing 幅 $\varepsilon \sim h$ に起因する物理誤差 $O(\varepsilon^2) = O(h^2)$ が寄生流れを支配する。

これを根本的に解消するには **sharp-interface（分相 PPE）解法**が必要であり、その場合に現れる
**変密度 PPE の界面ジャンプを CCD でどう扱うか** が本稿の問いである。

---

## 2. Sharp-Interface Variable-Density PPE の定式化

分相 PPE では各相で独立に解を定義する。$\Gamma$ を界面、$\hat{\bm{n}}$ を液相から気相への法線とすると、
IPC 増分形式の PPE は：

$$
\nabla \cdot\!\left(\frac{1}{\rho}\,\nabla\,\delta p\right) = \frac{1}{\Delta t}\,\nabla\cdot\bm{u}^*
\quad \text{in } \Omega_l \cup \Omega_g
\tag{1}
$$

界面 $\Gamma$ 上の **ジャンプ条件（Jump Conditions）** は：

$$
[\delta p]_\Gamma = \sigma\kappa
\tag{JC-0}
$$

$$
\left[\frac{1}{\rho}\,\frac{\partial \delta p}{\partial n}\right]_\Gamma = 0
\tag{JC-1}
$$

**導出**：JC-0 は Young--Laplace 則から直接得られる。
JC-1 は速度補正 $\bm{u}^{n+1} = \bm{u}^* - (\Delta t/\rho)\nabla(\delta p)$ において、
$\nabla\cdot\bm{u}^{n+1}$ が界面を跨いでも連続になる条件（投影法の基本要請）から導かれる：

$$
[\bm{u}^{n+1}\cdot\hat{\bm{n}}]_\Gamma = 0
\;\Longrightarrow\;
\left[\frac{\Delta t}{\rho}\frac{\partial\delta p}{\partial n}\right]_\Gamma = 0
\;\Longrightarrow\;
\left[\frac{1}{\rho}\frac{\partial\delta p}{\partial n}\right]_\Gamma = 0
$$

---

## 3. 高階ジャンプ条件の系統的導出

CCD が $O(h^6)$ 精度を持つには、ステンシルが跨ぐ界面の **高階微分ジャンプ** $[p^{(k)}]_\Gamma$（$k=0,\ldots,5$）が既知でなければならない。以下 1D で導出する（$\delta p$ を $p$ と略記）。

### 3.1 低階ジャンプ（JC-0, JC-1 から）

1D PPE を product rule で展開：

$$
\frac{1}{\rho}\,p'' - \frac{\rho'}{\rho^2}\,p' = q
\tag{2}
$$

**$[p]_\Gamma$**（JC-0）：

$$
[p]_\Gamma = \sigma\kappa \equiv C_0
\tag{k=0}
$$

**$[p']_\Gamma$**（JC-1 から）：

JC-1: $\left[\tfrac{1}{\rho}p'\right] = 0$

$$
\frac{p'_g}{\rho_g} = \frac{p'_l}{\rho_l}
\;\Longrightarrow\;
[p']_\Gamma = \left(\frac{\rho_g}{\rho_l} - 1\right)p'_l\big|_\Gamma \equiv C_1
\tag{k=1}
$$

ここで $p'_l|_\Gamma$ は液相側の界面圧力勾配（既知量として扱う）。

### 3.2 高階ジャンプの漸化式

式 (2) を微分してジャンプを取ると、**漸化式**が得られる。

まず $[\cdot]$ 作用素の線形性と積の法則 $[fg] = [f]\bar{g} + \bar{f}[g]$（$\bar{f} = (f^+ + f^-)/2$）を用いる。

式 (2) の界面での値：

$$
\left[\frac{1}{\rho}p''\right] - \left[\frac{\rho'}{\rho^2}p'\right] = [q]
$$

$$
\frac{[p'']}{\bar\rho} + p''\left[\frac{1}{\rho}\right] - \frac{[p']\bar{\rho'}}{\bar{\rho}^2} - p'\left[\frac{\rho'}{\rho^2}\right] = [q]
\tag{3}
$$

$[1/\rho] = -[\rho]/(\rho_l\rho_g)$ および $C_1$ を代入して $[p''] = C_2$ を解く：

$$
C_2 = \bar\rho\left([q] + \frac{\bar\rho'}{\bar\rho^2}C_1 + p'\left[\frac{\rho'}{\rho^2}\right] - p''\frac{-[\rho]}{\rho_l\rho_g}\right)
\tag{k=2}
$$

**一般的漸化式**（$k \geq 2$）：

$$
C_k = [p^{(k)}]_\Gamma = \bar\rho\Bigl([\partial_x^{k-2}q] + \sum_{j=0}^{k-1} \alpha_{k,j}\,C_j + \text{(known interface geometry terms)}\Bigr)
\tag{★}
$$

$k=3,4,5$ まで繰り返し微分すれば、$C_3,C_4,C_5$ が順次求まる。各 $C_k$ は $O(h^0)$（$h$ によらない有限量）であり、$O(h^6)$ CCD 補正項に $C_k h^k$ として寄与するため、数値精度は維持される。

---

## 4. IIM-CCD ステンシル修正

### 4.1 1D CCD の標準形

CCD の 5 次関係式：

$$
\alpha p_{i-1} + p_i + \alpha p_{i+1}
+ h(\beta p'_{i-1} - \beta p'_{i+1})
= h^2(p''_{i-1}/\delta + p''_i/\eta_0 + p''_{i+1}/\delta)
\tag{CCD}
$$

### 4.2 界面交差ステンシルの修正

界面 $\Gamma$ が $x_i < x^* < x_{i+1}$ を通過する場合（$\alpha_\Gamma = (x^* - x_i)/h$）、
ステンシルに現れる **気相側の値** $p_{i+1}, p'_{i+1}, p''_{i+1}$ を液相側の値に換算する：

$$
p_{i+1}^{(\text{gas})} = p_{i+1}^{(\text{liq})} + C_0 + C_1 h + \frac{C_2 h^2}{2} + \cdots
$$

$$
p'^{(\text{gas})}_{i+1} = p'^{(\text{liq})}_{i+1} + C_1 + C_2 h + \frac{C_3 h^2}{2} + \cdots
$$

$$
p''^{(\text{gas})}_{i+1} = p''^{(\text{liq})}_{i+1} + C_2 + C_3 h + \cdots
$$

これを CCD 方程式に代入し整理すると、**修正された RHS**：

$$
\boxed{
\text{RHS}_i^{\text{IIM}} = \text{RHS}_i^{\text{std}}
- \alpha\,C_0 - h\beta\,C_1 - \frac{h^2}{\delta}\,C_2 + O(h^3)
}
\tag{IIM-CCD}
$$

正確には $\alpha_\Gamma$ 依存の重み行列 $\bm{W}(\alpha_\Gamma)$ を介して：

$$
\text{RHS}^{\text{IIM}} = \text{RHS}^{\text{std}} - \bm{W}(\alpha_\Gamma)\,\bm{C}
\tag{4}
$$

$\bm{C} = [C_0, C_1, C_2, C_3, C_4, C_5]^T$,
$\bm{W}$ は $\alpha_\Gamma$ の多項式で構成される $1 \times 6$ ベクトル。

### 4.3 $p', p''$ 方程式への修正

CCD は $p, p', p''$ の連立系を解くため、3本の方程式すべてに修正が必要である：

| 方程式 | 修正量の最低次項 |
|--------|----------------|
| $p$ 方程式 | $\alpha\,C_0$ |
| $p'$ 方程式 | $\beta\,C_1$ |
| $p''$ 方程式 | $C_2/\delta$ |

これが **IIM x CCD の本質的差異**：標準 IIM（FD 用）が $C_0$ 項のみを補正するのに対し、
CCD では Hermite データ 3 本に対して $C_0, C_1, C_2$（以上）を同時に補正する必要がある。

---

## 5. Defect Correction との整合性

§8c の欠陥補正法は：

$$
L_H p^{(k+1)} = b + (L_H - L_L)\,p^{(k)}
$$

IIM-CCD では $L_H$ の評価（Step 1：欠陥算出）時に **式 (4) の RHS 補正を含める**：

$$
d^{(k)} = b^{\text{IIM}} - L_H^{\text{IIM}}\,p^{(k)}
\tag{DC+IIM}
$$

- $L_H^{\text{IIM}}$：界面交差ステンシルで式 (4) を適用した CCD 演算子
- $L_L$：変更なし（FD 2次精度 -- 界面近傍で局所的に $O(h)$ に落ちるが収束は保たれる）
- 収束速度：$L_H^{\text{IIM}}$ の残差が $O(h^6)$ で落ちるため、DC $k=3$ 回で $O(h^6)$ が達成される

**理論的正当性**：$L_L$ の $O(h^2)$ 誤差は内部反復の収束先には影響しない（DC の収束先は $L_H^{\text{IIM}} p = b^{\text{IIM}}$ の解であり、$L_L$ は前処理子として機能）。

---

## 6. 2次元への拡張

2D では界面 $\Gamma$ が格子セルを一般的な曲線で横切るため、以下の追加事項が必要である。

### 6.1 2D ジャンプ条件

1D の $[p^{(k)}]$ を法線方向微分 $(\partial/\partial n)^k$ に置き換えた **法線微分ジャンプ条件**に加え、
接線方向微分のジャンプも必要となる：

$$
[p]_\Gamma = C_0,\quad
\left[\frac{\partial p}{\partial n}\right] = C_{n1},\quad
\left[\frac{\partial p}{\partial s}\right] = 0
$$

（接線方向：$p$ が各相で滑らかなため接線微分ジャンプはゼロ）

混合導関数のジャンプ：

$$
\left[\frac{\partial^2 p}{\partial n \partial s}\right] = -\kappa_s C_0 + \frac{\partial C_0}{\partial s} = C_{ns}
$$

$\kappa_s$: 界面曲率の接線微分（界面形状から計算可能）

### 6.2 テンソル積構造との整合

CCD の 2D 演算子はテンソル積 $L_H = L_H^{(x)} + L_H^{(y)}$ で分離される。
IIM 修正は各方向ごとに独立に適用可能である：

- $x$ 方向スイープ時：$\Gamma$ が $x$ 軸方向に交差するステンシルを修正
- $y$ 方向スイープ時：$\Gamma$ が $y$ 軸方向に交差するステンシルを修正

**テンソル積分離は IIM-CCD でも保持される**（各方向修正が独立のため）。

---

## 7. HFE との比較：理論的優劣

| 観点 | HFE（§8d 現行） | IIM-CCD（本稿提案） |
|------|----------------|-------------------|
| 界面処理 | 液相側から気相側へ $\nabla q \cdot \hat{n} = 0$ で延長 | ジャンプ条件 $[p] = \sigma\kappa$ を陽に強制 |
| 圧力ジャンプ | 延長により消去（近似） | 厳密に保持 |
| 精度（滑らか場） | $O(h^6)$ | $O(h^6)$ |
| 精度（界面近傍） | $O(h^6)$（延長域） / $O(h^2)$（未延長域） | $O(h^6)$（界面直近まで） |
| 追加計算 | 最近接点計算 + Hermite 5次補間 | $C_k$ 漸化式 + ステンシル修正 |
| 曲率依存性 | $\kappa$ 不要 | $\kappa, \kappa_s$ が必要（$O(h^4)$ 以上の精度要） |
| 適用可能性 | CSF + smoothed Heaviside でも使用可 | **split-PPE（sharp interface）専用** |

**結論**：HFE は smeared-interface 上での「フォールバック基盤技術」として有効だが、
sharp-interface split-PPE における圧力ジャンプの厳密な表現には IIM が理論的に優れる。

---

## 8. 数値精度の理論的保証

### 8.1 全体精度の律速要因

IIM-CCD の全体精度 $O(h^q)$ は以下の最小：

$$
q = \min\!\Big(\underbrace{6}_{\text{CCD}},\; \underbrace{k_{\max}+1}_{\text{jump truncation}},\; \underbrace{p_\kappa}_{\text{curvature}}\Big)
$$

| 要因 | 次数 |
|------|------|
| CCD 空間離散化 | $O(h^6)$ |
| $C_k$ 漸化式の打ち切り次数 | $O(h^{k_{\max}+1})$ -- $k_{\max}=5$ なら $O(h^6)$ |
| 曲率 $\kappa$ の精度 | 通常 $O(h^2)$（CLS Level Set） |
| 界面位置 $x^*$ の精度 | $O(h^2)$（CLS Level Set） |

**律速は曲率精度 $O(h^2)$**。$O(h^6)$ CCD の恩恵を得るには、$\kappa$ を $O(h^4)$ 以上で計算する必要がある（例：高次 WENO + 再初期化 + 補間）。

### 8.2 ジャンプ条件の $C_k$ 有限性

$C_k$ は界面近傍で $O(1)$（$h$ によらない定数）であることが重要である：

$$
[p^{(k)}] = O(1) \quad\Rightarrow\quad C_k h^k = O(h^k)
$$

したがって IIM 補正項 $C_k h^k$ は $h \to 0$ で消えるが、有限格子では無視できない -- これが IIM の本質的役割。

### 8.3 安定性：修正 CCD 系の条件数

標準 CCD のスペクトル半径 $\approx 3.43/h^2$ に対し、IIM 修正は **RHS のみの変更**（行列 $L_H^{\text{IIM}}$ の係数は界面 $O(N_\Gamma)$ 点で変化）であるため、条件数への影響は局所的であり、大域的な安定性は保たれる。

---

## 9. 実装上の難点と開放的課題

1. **$C_k$ の漸化式計算**：$k=5$ まで必要。係数 $[\rho^{(j)}]|_\Gamma$（密度の高階界面微分）は CLS Level Set から評価するが、$h$ の精度が律速。

2. **2D 混合微分ジャンプ** $[p_{xy}], [p_{xxy}], \ldots$：法線 $\hat{n}$ が格子軸に非平行の場合に必要。テンソル積構造での取り扱いに注意。

3. **DCCD フィルタとの整合**：現行の DCCD-PPE は CSF smeared-interface 専用の RHS であり、sharp-interface IIM では DCCD フィルタ項の再設計が必要。

4. **高密度比 $\rho_l/\rho_g \gg 1$**：JC-1 から $C_1 = (\rho_g/\rho_l - 1)p'_l|_\Gamma$ であり、$\rho_l/\rho_g = 1000$（水/空気）では $|C_1| \approx 999\,|p'_l|_\Gamma|$ となる。IIM 補正項が $O(10^3)$ オーダーに増幅され、界面近傍の CCD 係数行列の条件数を悪化させる。調和平均係数との組み合わせで緩和できる。

5. **欠陥補正の収束速度**：IIM 修正後 $L_H^{\text{IIM}}$ の残差が $O(h^6)$ に落ちるが、前処理子 $L_L$（FD 2次精度）は界面近傍で $O(h)$ の誤差を持つ。DC の反復回数が増加する可能性があり、$k=3$ が十分かを再検証する必要がある。

---

## 10. まとめと理論的結論

本稿では、CCD に基づく変密度 PPE 解法への IIM 適用が **理論的・数学的・論理的に成立する**ことを示した。

### 定理（IIM-CCD の成立条件）

以下の 3 条件が全て満たされるとき、IIM-CCD は sharp-interface split-PPE において $O(h^q)$ 精度を保証する：

$$
q = \min\!\Big(\underbrace{6}_{\text{CCD}},\; \underbrace{k_{\max}+1}_{\text{jump truncation}},\; \underbrace{p_\kappa}_{\text{curvature}}\Big)
$$

| 条件 | 要件 |
|------|------|
| **C1（Hermite 一貫性）** | CCD の 3 未知量 $(p, p', p'')$ 全てに IIM 補正 $C_0, C_1, C_2$（以上）を適用 |
| **C2（漸化式完結性）** | $C_k$（$k=0,\ldots,5$）を式 (★) の漸化式で $O(h^6)$ まで計算 |
| **C3（曲率精度）** | $\kappa$ を $O(h^{p_\kappa})$ 精度で評価（現行 CLS では $p_\kappa = 2$ が律速） |

### 論理的整合性のまとめ

```
sharp-interface PPE の支配方程式 (1)
    |-- ジャンプ条件 JC-0, JC-1（NS + Young-Laplace から導出）
    |-- 高階ジャンプ漸化式 (★)（PDE を繰り返し微分）
    |-- IIM-CCD ステンシル修正 (4)（Hermite 3 本に同時適用）
    |-- DC との整合（L_H^{IIM} は RHS 修正のみ）
    |-- テンソル積分離保持（2D も各方向独立）
    |-- O(h^6) 精度（曲率精度が律速）
```

### 現行ソルバへの推奨パス

```
現行（CSF + smeared）
    -> HFE（§8d）：split-PPE への第1段階（曲率精度 O(h^2) でも機能）
    -> IIM-CCD（本稿）：高密度比での厳密解法（曲率 O(h^4) 以上が必要）
```

GFM + DCCD 実装がキャンセルされた（2026-04-04）現時点では、IIM-CCD は **理論的基盤として §8d の HFE と対比させる形で論文に記録**し、将来の split-PPE 実装への設計文書として位置づけることが適切である。

---

## 参考文献

- LeVeque & Li (1994): *The Immersed Interface Method for Elliptic Equations with Discontinuous Coefficients and Singular Sources.* SIAM J. Numer. Anal. **31**(4), 1019--1044.
- Li & Ito (2006): *The Immersed Interface Method: Numerical Solutions of PDEs Involving Interfaces and Irregular Domains.* SIAM.
- Aslam (2004): *A partial differential equation approach to multidimensional extrapolation.* JCP **193**(1).
- Leal (2007): *Advanced Transport Phenomena.* -- 変密度流れのジャンプ条件の物理的導出
