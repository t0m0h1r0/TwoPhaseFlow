# CCD-PPE ソルバ収束解析 — 総括レポート

**日付**: 2026-04-05  
**実験**: exp10_16（FD-DC 収束限界）, exp10_17（CCD-ADI 失敗確認）  
**結論**: ADI 系は O(h⁴) 収束 → 不可。DC+ω 緩和 + 全 2D FD 解法が有望。

---

## 1. 問題設定

$$\nabla \cdot \left(\frac{1}{\rho} \nabla p\right) = q, \quad \Omega=[0,1]^d,\; \partial_n p\big|_{\partial\Omega}=0$$

- **L\_H**（高精度）: CCD O(h⁶) 演算子（`eval_LH`）
- **L\_FD**（前処理）: 2 次 FD（可変密度対応）
- **CCD は必須**（圧力勾配 dp/dx の精度保証）

---

## 2. DC 反復の正しい定式化

### 2.1 符号規約

DC 反復の標準形（pseudo-time なし）：

$$p^{(k+1)} = p^{(k)} + \omega L_{FD}^{-1}\underbrace{(q - L_H p^{(k)})}_{R^{(k)}}$$

誤差 $e^{(k)} = p^{(k)} - p^*$ の伝播：

$$e^{(k+1)} = \underbrace{\left(I - \omega L_{FD}^{-1} L_H\right)}_{A(\omega)} e^{(k)}$$

### 2.2 スペクトル半径条件

反復行列固有値（Fourier モード $k$）：

$$\mu(k) = 1 - \omega \frac{\lambda_H(k)}{\lambda_{FD}(k)}$$

収束条件：$|\mu(k)| < 1$ すべての $k$ で成立 $\Leftrightarrow$ $\omega < \dfrac{2}{\max_k \lambda_H(k)/\lambda_{FD}(k)}$

### 2.3 CCD 完全変形波数解析

Eq-I（$p'$ 結合）と Eq-II（$p''$ 結合）を連立した正確な解析（N=32, 均一密度）：

| $kh/\pi$ | $\lambda_H h^2$ | $\lambda_{FD} h^2$ | 比 $r(k)$ | $\omega_{\max}$ |
|----------|-----------------|---------------------|-----------|-----------------|
| 0 (smooth) | $\approx -k^2 h^2$ | $\approx -k^2 h^2$ | 1.000 | 2.000 |
| 0.50 | −4.957 | −4.000 | 1.239 | 1.614 |
| 0.75 | −11.660 | −6.828 | 1.707 | 1.171 |
| 0.90 | −17.269 | −7.804 | 2.213 | 0.904 |
| **1.00 (Nyquist)** | **−19.200** | **−8.000** | **2.400** | **0.833** |

$$\boxed{r_{\max} = \max_k \frac{\lambda_H(k)}{\lambda_{FD}(k)} = 2.400 \text{ (Nyquist)}}$$

$$\omega^* = \frac{2}{r_{\max}} = 0.833 \quad \Longrightarrow \quad \omega \in (0,\, 0.833) \text{ で DC 収束}$$

### 2.4 実用的 $\omega$ 選択と収束速度

| $\omega$ | Nyquist モード $|\mu|$ | $k=1$ モード $|\mu|$ | 評価 |
|---------|----------------------|---------------------|------|
| 1.0（ω なし） | 1.40 → 発散 | 0.00 | ✗ |
| 0.83 (最大) | 1.00 → 停滞 | ~0.17 | △（境界不安定） |
| **0.50** | **0.20** | **~0.50** | ✓（速い） |
| **0.30** | **0.28** | **~0.70** | ✓（安全） |

$\omega = 0.3$ では Nyquist モードが 10 反復で $(0.28)^{10} \approx 2 \times 10^{-6}$ に減衰。

---

## 3. ADI 系の失敗分析

### 3.1 Pseudo-time ADI（Thomas sweep）

ADI 反復行列固有値（2D モード $(k_x, k_y)$，`p = p - dp`）：

$$\mu_{\rm ADI}(k_x, k_y) = 1 + \frac{\lambda_H(k_x, k_y)}{(1/\Delta\tau - \lambda_{FD,x}(k_x))(1/\Delta\tau - \lambda_{FD,y}(k_y))}$$

**問題のモード** $(k_x = \pi/N, k_y = \pi/N)$（最重要滑らかモード）：

$$\mu_{\rm ADI} \approx 1 + \lambda_H \cdot \Delta\tau^2 = 1 + O(h^4)$$

$\Delta\tau = c_\tau \rho h^2/2 = h^2$ のとき有効補正は $O(h^4)$ → **収束に $O(h^{-4}) = O(N^4)$ 反復が必要**。

N=32 では ~100 万回。N=64 では ~1600 万回。**実用不可**。

### 3.2 CCD-ADI（Idea B の失敗）

N=32, c_τ=2 での反復行列固有値：

| モード | FD-ADI | CCD-ADI | 結果 |
|--------|--------|---------|------|
| k=(1,1) smooth | 1.000000 | 1.000000 | どちらも停滞 |
| k=(N,0) x-Nyquist | 0.998125 | **0.999116** | CCD-ADI が**遅い** |
| k=(N,N) 2D-Nyquist | 0.999250 | **0.999833** | CCD-ADI が**遅い** |

**根本原因**：ADI 構造では x-sweep が y-方向成分を処理できない（逆も同様）。β₂ 結合の追加は 1D 固有値を改善するが、2D ADI の $(1/\Delta\tau)^2$ ボトルネックを解決しない。むしろ高波数での有効前処理が弱まり FD-ADI より遅くなる。

実験 exp10_17（2026-04-05）：FD と CCD-ADI で残差が 0.1% 以内で同一 → 理論予測と一致。

---

## 4. 失敗分類

| 手法 | 失敗原因 |
|------|---------|
| DC + FD-ADI sweep（ω=1） | ADI: $O(h^4)$ 有効補正 + $\omega=1$ > $\omega_{\max}=0.833$ |
| DC + CCD-ADI sweep | ADI 構造のボトルネックを解決しない。FD より遅い |
| DC + LU（ω=1） | $\omega=1 > 0.833$ → Nyquist 発散 |
| DC + LU（ω=0.3，旧コード）| **収束するはず**（以下参照） |

---

## 5. 収束する手法の候補

### 5.1 DC + ω 緩和 + FD 直接 LU（最もシンプル）

$$p \leftarrow p + \omega L_{FD}^{-1} R, \quad \omega = 0.3\text{〜}0.8$$

旧コードの `omega=0.3` は正しい設計だった（ただし BC が Dirichlet だった）。Neumann BC に修正した後、$\omega=0.3\text{〜}0.5$ で収束すると予測。

- 2D コスト: $O(N^3)$ per step（sparse LU）× 反復
- **3D では不可**（direct LU が $O(N^{4.5})$ → メモリ超過）

### 5.2 DC + ω 緩和 + ILU 前処理（3D 対応）

FD 直接 LU を不完全 LU (ILU(k)) または AMG で置換：

$$L_{FD} \approx \tilde{L}_{FD} = (\text{ILU または AMG}), \quad p \leftarrow p + \omega \tilde{L}_{FD}^{-1} R$$

- $\omega$ 条件は同じ（$\lambda_H/\lambda_{FD}$ スペクトル比に依存）
- ILU 前処理では $\lambda_{\tilde{L}^{-1} L_H}/\lambda_{\tilde{L}^{-1} L_{FD}}$ 比が増える可能性 → $\omega$ を小さめに
- LGMRES が失敗した先例あり（2026-04-03, $\rho_l/\rho_g \geq 10$）— ILU の質が鍵

### 5.3 Matrix-free GMRES + FD 前処理（最も有望）

CCD 演算子 `eval_LH` を matrix-free matvec として GMRES に渡す：

$$\min_p \|L_H p - q\|, \quad \text{preconditioner: } L_{FD}$$

前処理行列 $L_{FD}^{-1} L_H$ の固有値分布: $r(k) \in [1.0, 2.4]$（Nyquist まで単調増加）。固有値が **コンパクトな区間 $[1, 2.4]$ にクラスタ** → GMRES は理論上 **$\sim 2$ 反復で収束**（2 つの固有値クラスタ）。

前処理適用の選択:
- 直接 LU（2D 小規模）: $O(N^{1.5})$
- ILU(1) または CG-inner（3D 中規模）
- AMG（3D 大規模）

**高密度比の懸念**: $\rho' \neq 0$ の場合、$L_H$ の密度勾配項が非対称性を導入 → BiCGSTAB の方が安定する可能性。

### 5.4 Multigrid with CCD residual（最終的な最適解）

- Fine grid: CCD 残差評価（高精度）
- Coarse grid: FD 粗解（低コスト）
- Smoother: Gauss-Seidel または SOR（FD 基盤）

O(N²) (2D) / O(N³) (3D) でスケール。3D 化時の本命候補。実装コスト大。

---

## 6. 推奨ロードマップ

```
Phase 1（即時検証）
  → dc_lu_solve に ω=0.5 を再導入し Neumann BC で収束を実験確認
  → exp10_18: ω vs 密度比 の収束マップ作成

Phase 2（3D 対応）
  → matrix-free GMRES + FD 直接 LU 前処理（2D 大規模 N=128 まで）
  → ω の最適化: スペクトル半径を最小化する ω* = 2/(1 + r_max) の解析

Phase 3（スケール）
  → BiCGSTAB + ILU(k) 前処理（3D N=64〜128）
  → AMG 前処理（3D N=256+）
  → PPESolverSweep をソルバ選択インターフェースに変更
```

---

## 7. 教訓

| 問題 | 判明した事実 |
|------|-------------|
| 旧 `ω=0.3` の除去 | 正しい安定化策だった。スペクトル比から導出可能 |
| `p + dp` → `p - dp` sign fix | Pseudo-time ADI では符号が複雑。DC+LU には不要な変更 |
| ADI が遅い原因 | $\Delta\tau^2$ 2乗による $O(h^4)$ 補正。演算子選択の問題ではない |
| CCD-ADI Idea B | 1D では改善するが 2D ADI では FD より劣化 |
| Nyquist 比 $r_{\max}$ | 完全 CCD (Eq-I+II) で = 2.400。Eq-II のみでは = 4.0（誤り） |
