# CCD–DC 反復法の収束性解析

**日付**: 2026-04-05  
**関連実験**: experiment/ch10/exp10_16_dc_sweep_convergence_limit.py  
**論文参照**: §8d (defect correction + LTS), Appendix E.5

---

## 1. 問題設定

可変密度 PPE：

$$\nabla \cdot \!\left(\frac{1}{\rho}\nabla p\right) = q, \quad \text{on } [0,1]^2,\; \partial_n p\big|_{\partial\Omega}=0$$

離散化：
- **L\_H**（高精度）: CCD O(h⁶) 演算子
- **L\_FD**（前処理）: 2 次 FD 演算子（Thomas sweep または直接 LU）

---

## 2. DC 反復の定式化

残差 $R^{(k)} = q - L_H p^{(k)}$ に対し，前処理系を解く：

$$(1/\Delta\tau - L_{FD})\, \delta p = R^{(k)}$$

更新式（疑似時間形式）：

$$\frac{\partial p}{\partial \tau} = L p - q = -R \quad \Longrightarrow \quad p^{(k+1)} = p^{(k)} - \delta p$$

---

## 3. 符号誤りによる発散（旧コード）

旧コードは `p = p + dp` を使用していた。反復行列を導出する。

$\delta p = (1/\Delta\tau - L_{FD})^{-1} R^{(k)} = (1/\Delta\tau - L_{FD})^{-1}(q - L_H p^{(k)})$

| 更新式 | 反復行列 $A$ |
|--------|------------|
| `p ← p + δp`（旧・誤り）| $I - (1/\Delta\tau - L_{FD})^{-1} L_H$ |
| `p ← p − δp`（新・正） | $I + (1/\Delta\tau - L_{FD})^{-1} L_H$ |

両者とも固定点は $L_H p^* = q$（正しい解）だが，スペクトル半径が異なる。

### 旧符号の固有値

$L_H,\, L_{FD}$ は負半定値。固有値 $\lambda_H < 0,\; \lambda_{FD} < 0$，分母 $1/\Delta\tau - \lambda_{FD} > 0$。

$$\mu_{\rm old} = 1 - \frac{\lambda_H}{1/\Delta\tau - \lambda_{FD}}$$

$\lambda_H < 0$ より右辺第 2 項 $< 0$，よって $\mu_{\rm old} > 1$。  
**→ 全固有値が 1 より大きい = 無条件発散。**

---

## 4. 正しい符号の収束条件

$$\mu_{\rm new} = 1 + \frac{\lambda_H}{1/\Delta\tau - \lambda_{FD}} \in (0,\, 1) \text{ が条件}$$

$|\mu_{\rm new}| < 1$ を整理すると：

$$\frac{\lambda_H}{1/\Delta\tau - \lambda_{FD}} \in (-2,\, 0)$$

右側（$< 0$）は自明。左側の条件：

$$\lambda_H > -2\!\left(\frac{1}{\Delta\tau} - \lambda_{FD}\right)$$

$\Delta\tau \to \infty$（直接 LU，$1/\Delta\tau \to 0$）の極限では：

$$\boxed{\frac{\lambda_H}{\lambda_{FD}} < 2}$$

すなわち **CCD と FD の固有値比が全モードで 2 未満** であれば収束。

### $\Delta\tau$ 依存性

Thomas sweep の場合 $\Delta\tau = c_\tau \rho h^2 / 2$（可変）。$c_\tau$ が小さいほど収束が遅くなるが安定域は広がる。

---

## 5. 高密度比における破綻メカニズム

### 5.1 条件数の増大

演算子の条件数 $\kappa(L) = O(\rho_l/\rho_g \cdot h^{-2})$（§8.4）。  
$\rho_l/\rho_g \gg 1$ で $L_{FD}$ の最小固有値が $O(\rho_g/h^2)$ まで縮小。

### 5.2 固有値比の崩れ

界面付近の高波数モードで $L_H$ と $L_{FD}$ の離散化誤差が異なる方向に偏る。  
CCD は界面を跨ぐ連立系を解くため，界面近傍で FD とは異なる固有値分布を持つ可能性がある。

固有値比 $\lambda_H/\lambda_{FD} > 2$ のモードが存在すると $|\mu_{\rm new}| > 1$ となり，**その成分が発散**。

### 5.3 ADI 分解誤差（Thomas sweep 固有）

2D では $L_{FD} \neq L_{FD,x} + L_{FD,y}$（正確には等しいが，各軸 Thomas は $1/\Delta\tau - L_{FD,x}$ と $1/\Delta\tau - L_{FD,y}$ を別々に解く）。

ADI の反復行列：

$$A_{\rm ADI} = (1/\Delta\tau - L_{FD,x})^{-1}(1/\Delta\tau - L_{FD,y})^{-1} L_H$$

これは $A_{\rm LU} = (1/\Delta\tau - L_{FD})^{-1} L_H$ とは異なり，高波数で $|A_{\rm ADI}| > |A_{\rm LU}|$ となりうる。

---

## 6. DC+LU との比較による分離検証

実験 exp10_16 では同一問題を 2 ソルバで解く：

| ソルバ | 前処理 | ADI 誤差 |
|--------|--------|---------|
| DC sweep (Thomas ADI) | FD（各軸）| あり |
| DC + direct LU | FD（2D 全体）| なし |

両者の収束曲線を比較することで，  
- **LU が収束 → sweep が発散**: ADI 分解誤差が原因  
- **両者とも発散**: 固有値比 $\lambda_H/\lambda_{FD} \geq 2$ が原因（密度比依存）

---

## 7. 実験結果（exp10_16, 2026-04-05）

```
N=32:  全密度比 ρ_l/ρ_g = 1〜1000 で sweep FAIL, LU FAIL
N=64:  全密度比 ρ_l/ρ_g = 1〜1000 で sweep FAIL, LU FAIL

sweep: 残差が単調増大（~10²〜10⁵, 2000 iter 後）
LU:    残差が ~200 iter で 10²⁰ にオーバーフロー
```

**重要な観察**: ρ=1（一様密度）でも発散 → 密度比依存ではなく，**CCD と FD の固有値比問題**が原因。

### 解釈

| 観察 | 意味 |
|------|------|
| sweep も LU も全 ρ で発散 | ADI 分解誤差だけが原因ではない |
| ρ=1 でも発散 | 密度比の問題ではない |
| LU が sweep より速く発散 | pseudo-time 正則化が発散を抑制している（ただし防げない）|
| 残差が単調増大 | スペクトル半径 > 1（振動なし → 実正の固有値が支配的）|

**根本原因**: Nyquist 付近の高波数モードで $\lambda_H/\lambda_{FD} > 2$。  
CCD は FD と同じ演算子を離散化するが，変形波数（modified wavenumber）の分布が大きく異なる。この比が 2 を超えるモードが存在する限り，符号を直しても DC 反復は収束しない。

---

## 8. まとめ

| 問題 | 結論 |
|------|------|
| 旧符号 `p + δp`（sweep） | 無条件発散（理論的に正しくない，§3） |
| 新符号 `p − δp`（sweep） | 発散（スペクトル比 > 2 が存在するため）|
| LU 版 `p + δp` | 発散（同一根本原因） |
| 密度比依存性 | ρ=1 でも発散 → 主要因ではない |
| 符号修正の意義 | 必要条件だが十分条件ではない |

### 次のステップ

1. **CCD の変形波数を数値的に算出**し，$\lambda_H/\lambda_{FD}$ 比を確認
2. **安定化戦略を検討**:
   - Option A: FD の代わりに CCD 系の前処理（コスト大）
   - Option B: 高波数フィルタを DC ループ内に挿入（survey_filters_high_order_diff.md 参照）
   - Option C: DC 反復を収束ソルバとして使わず，数ステップの smoother として使う
3. **§8d の記述を修正**: DC sweep が収束保証を持たない旨を明記し，LU fallback の必要性を理論的に正当化する
