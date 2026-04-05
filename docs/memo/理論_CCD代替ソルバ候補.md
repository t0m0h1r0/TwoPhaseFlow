# CCD+DC 代替ソルバ候補の理論比較

**日付**: 2026-04-05  
**前提**: CCD は必須（O(h⁶) 残差評価に使用）  
**背景**: exp10_16 で CCD+FD-DC が全条件で発散することを確認（→ 理論_CCD-DC反復収束性解析.md）

---

## 1. 発散の根本原因（定量的）

CCD Eq-II の変形波数（uniform density, 1D）：

$$\lambda_H^{(k)} = \frac{A_2/h^2 \cdot (2\cos kh - 2)}{1 + 2\beta_2 \cos kh}$$

$A_2 = 3,\; \beta_2 = -1/8$。Nyquist モード $kh = \pi$：

$$\lambda_H(\pi) = \frac{3/h^2 \cdot (-4)}{1 + 1/4} = -\frac{9.6}{h^2}$$

FD 5点スキーム Nyquist：$\lambda_{FD}(\pi) = -4/h^2$

$$\boxed{\frac{\lambda_H(\pi)}{\lambda_{FD}(\pi)} = 2.4 > 2}$$

**この比が収束閾値 2 を超えるため，FD 前処理による DC は Nyquist モードで無条件発散。**

旧コードの $\omega = 0.3$ が意味していたこと：
$|1 - 0.3 \times 2.4| = |1 - 0.72| = 0.28 < 1$ → 収束（ただし全モードで 2.4 が上限の場合）

---

## 2. 代替案一覧

### Option A: Kronecker 積 + 直接 LU ☆☆☆

**原理**: $L_H$ を Kronecker 積でスパース行列として組み立て，`spsolve` で一発解く。

$$L = \text{diag}(1/\rho)\left[D_2^x \otimes I_y + I_x \otimes D_2^y\right] - \text{diag}(\partial_x\rho/\rho^2)(D_1^x \otimes I_y) - \cdots$$

反復なし → 固有値比問題は無関係。既に論文付録 `app:ccd_kronecker` に記述済み。

**収束**: 単一直接解 → 収束保証あり（反復なし）  
**コスト**: $O(n^{1.5})$ / タイムステップ（$N \leq 128$ で現実的）  
**欠点**: $N$ 大では遅い。$\rho$ 変化時に毎回再組み立て・再因子分解が必要。

---

### Option B: CCD-ADI 修正三重対角スイープ ☆☆☆（本稿の主題）

**詳細は §3 参照。**

CCD Eq-II の暗陽結合 $\beta_2$ を pseudo-time 前処理に取り込んだ修正トーマス法。スペクトル比 $\lambda_H / \lambda_{\rm prec} \approx 1$ が全モードで成立 → DC 反復が収束。

**収束**: 理論保証あり（§3 参照）  
**コスト**: FD Thomas の 1.2 倍程度（三重対角係数の変更のみ）  
**欠点**: $\rho'$ 項（密度勾配）を第一近似で省略。高密度比では収束速度が若干低下する可能性。

---

### Option C: Helmholtz フィルタ付き DC ☆☆

**原理**: DC 各ステップ前に残差を低域通過フィルタリングし，高波数成分を除去。

$$R^* = (I - \kappa^2 \nabla^2)^{-1} R, \quad p \leftarrow p + L_{FD}^{-1} R^*$$

フィルタ後は $\lambda_H^* / \lambda_{FD}^* < 2$ が保証されるように $\kappa$ を選ぶ。

**転送関数**: $H(\xi) = 1/(1 + \alpha \xi^2)$ → 中間波数も効果的に除去  
**参考**: survey_filters_high_order_diff.md §7 (Helmholtz-κ)  
**欠点**: $\kappa$ の決定に変形波数解析が必要。DC ループのコストが増加。

---

### Option D: Matrix-free GMRES + 可変密度 FD 前処理 ☆

**原理**: GMRES に `eval_LH`（CCD 演算子）を matrix-free で渡す。前処理に変数密度 FD Laplacian の直接 LU を使用。

**理由で不採用**: LGMRES + ILU は $\rho_l/\rho_g \geq 10$ で info=500（実験確認済み，2026-04-03）。LU 前処理の改善案だが，memory 制約と界面型密度場での不安定性が懸念。

---

## 3. Option B 詳細：CCD-ADI 修正三重対角スイープ

### 3.1 定式化

CCD Eq-II（1D, 均一格子）：

$$\beta_2(p''_{i-1} + p''_{i+1}) + p''_i = \frac{A_2}{h^2}(p_{i-1} - 2p_i + p_{i+1}) + \frac{B_2}{h}(p'_{i+1} - p'_{i-1})$$

$B_2$ 項（$p'$ との結合）を省いた第一近似：

$$(I + \beta_2 T) p'' \approx \frac{A_2}{h^2} \delta^2 p$$

これより：

$$L_{\rm prec} p \approx \frac{1}{\rho} (I + \beta_2 T)^{-1} \frac{A_2}{h^2} \delta^2 p$$

Pseudo-time 前処理系：

$$(1/\Delta\tau - L_{\rm prec}) \delta p = R$$

両辺に $(I + \beta_2 T)$ を乗じると修正三重対角系：

$$\underbrace{(1/\Delta\tau)(I + \beta_2 T) - \frac{A_2}{h^2}\frac{1}{\rho}\delta^2}_{\text{修正三重対角}} \delta p = (I + \beta_2 T) R$$

### 3.2 係数（内点 $1 \leq i \leq N-1$）

$$a_i = c_i = \frac{\beta_2}{\Delta\tau_i} - \frac{A_2}{h^2 \rho_i}, \qquad b_i = \frac{1}{\Delta\tau_i} + \frac{2A_2}{h^2 \rho_i}$$

$$d_i = R_i + \beta_2(R_{i-1} + R_{i+1})$$

$\Delta\tau_i = c_\tau \rho_i h^2 / 2$ を代入（$\kappa = 1/c_\tau$）：

$$a_i = c_i = (2\kappa\beta_2 - A_2) \cdot \text{inv\_rho\_h2}$$
$$b_i = (2\kappa + 2A_2) \cdot \text{inv\_rho\_h2}$$

### 3.3 Neumann BC（ゴースト反射 $\delta p_{-1} = \delta p_1$）

境界 $i=0$：
$$b_0 = \frac{1}{\Delta\tau_0} + \frac{2A_2}{h^2\rho_0}, \quad c_0 = 2a_0 \text{ (倍増)}, \quad d_0 = R_0 + 2\beta_2 R_1$$

境界 $i=N$：
$$b_N = \frac{1}{\Delta\tau_N} + \frac{2A_2}{h^2\rho_N}, \quad a_N = 2a_N \text{ (倍増)}, \quad d_N = R_N + 2\beta_2 R_{N-1}$$

### 3.4 対角優位性（トーマス安定性）

$$b_i - (|a_i| + |c_i|) = \frac{0.75}{\Delta\tau_i} > 0 \quad \forall i$$

厳密対角優位 → トーマス法は全条件で数値安定。

### 3.5 変形波数解析（収束保証）

$$\lambda_{\rm prec}(k) = \frac{A_2/h^2 \cdot (2\cos kh - 2)/\rho}{1 + 2\beta_2 \cos kh}$$

| $kh$ | $\lambda_H(k)$ | $\lambda_{\rm prec}(k)$ | 比 |
|------|---------------|------------------------|-----|
| 0 | 0 | 0 | — |
| $\pi/4$ | $\approx -1.0/h^2\rho$ | $\approx -1.0/h^2\rho$ | ≈ 1 |
| $\pi/2$ | $\approx -2/h^2\rho$ | $\approx -2/h^2\rho$ | ≈ 1 |
| $\pi$ (Nyquist) | $-9.6/h^2\rho$ | $-9.6/h^2\rho$ | **1.0** |

Nyquist でも比 = 1 → 反復行列固有値 $\approx 0$ → **1〜数ステップで収束**。

（比較：FD 前処理では比 = 2.4 → 無条件発散）

### 3.6 ADI 分解誤差

2D では $L_{\rm prec} \neq L_{\rm prec,x} + L_{\rm prec,y}$（各軸 CCD-ADI の合成は完全な 2D 演算子ではない）。

ADI 誤差は $O(\Delta\tau^2)$ オーダーで，$\Delta\tau \to 0$ で消える。実用的には $c_\tau = 2$ 程度で誤差は小さい。

---

## 4. Option B の失敗と根本原因（exp10_17, 2026-04-05）

実験 exp10_17 で FD-ADI と CCD-ADI の収束挙動が**ほぼ同一**であることを確認。

### 2D ADI 固有値解析

2D ADI 反復行列の固有値（N=32, c_τ=2, ρ=1, `p = p - dp`）：

| モード | FD-ADI | CCD-ADI |
|--------|--------|---------|
| k=(1,1) 滑らか | 1.000000 | 1.000000 |
| k=(N,0) x-Nyquist | 0.998125 | 0.999116 |
| k=(N,N) 2D-Nyquist | 0.999250 | 0.999833 |

**CCD-ADI は FD-ADI より遅い**（固有値が 1 に近い）。

### 根本原因

ADI 構造により k=(1,1) モードの固有値が：

$$1 + \lambda_H \cdot \underbrace{\frac{1}{1/\Delta\tau}}_{\approx h^2} \cdot \underbrace{\frac{1}{1/\Delta\tau}}_{\approx h^2} = 1 + O(h^4)$$

有効補正 = O(h⁴) / 反復 → 収束に O(h⁻⁴) = O(N⁴) 反復が必要（N=32 で ~10⁶）。

**問題は 1D 演算子の選択（FD vs CCD）ではなく、ADI スプリッティング構造そのもの。**

---

## 5. 修正推奨ロードマップ

| 優先度 | 手法 | 理由 |
|--------|------|------|
| **1（即時）** | **Option A: Kronecker+LU** | 反復なし。1 ステップで解。付録に既記述。ADI 問題を回避。 |
| 2（中期） | GMRES / BiCGSTAB + CCD matrix-free | Krylov は 2D 全モードを同時処理。O(√n) 反復期待。 |
| 3（研究） | Multigrid with CCD smoothing | 滑らかモードの粗グリッド補正 + 細グリッド CCD 残差。 |
| ~~削除~~ | ~~Option B: CCD-ADI~~ | ~~ADI 構造の問題を解決しない。FD と同等以下の性能。~~ |
| 3（研究） | Option C: Filtered-DC | フィルタで高波数を除去してから DC。DC は O(h²) 補正のみ有効。 |
