# CHK-RA-CH14-007 — interface-stress closure implementation plan

## 要旨

今回の研究成果は，毛管波だけの特別処理として実装しない。
既存の PPE / face-flux projection / config 設計を保ちつつ，
表面張力・浮力・界面応力条件を一つの汎用
**interface-stress closure** として差し込む。

結論：

1. 現行の `pressure_jump` 実装は legacy として保持する。
2. 新しい物理ベンチマーク用経路として
   `interface_coupling: affine_jump` を追加する。
3. `J=σ κ(1-ψ)` を通常の節点圧力として足す設計は禁止する。
4. 圧力ジャンプは affine 条件
   `G_Γ(p;j)=G(p)-B_Γ j` として，PPE と速度補正の両方で
   同じ離散演算子に通す。
5. 毛管波，上昇気泡，Rayleigh--Taylor は同じ closure を使う。

## 既存設計で踏襲するもの

### D1: PPE solver 境界

現行の `PPESolverFCCDMatrixFree` / defect-correction wrapper は維持する。
置き換えるのではなく，`interface_coupling_scheme` の新分岐として
affine jump を追加する。

踏襲する理由：

- 既存の matrix-free FCCD operator を再利用できる。
- defect correction, preconditioner, residual monitor の資産を残せる。
- `jump_decomposition` を比較用 legacy として保存できる。

### D2: face-flux projection 境界

速度補正は現行の face projection 経路を使う。
新設するのは「圧力勾配の作り方」であって，
投影そのものを別物にしない。

踏襲する理由：

- 離散非圧縮制約 `D_f u_f^{n+1}=0` を現在の projection と同じ場所で保てる。
- ch14 毛管波だけでなく，上昇気泡の flux 補正にもそのまま使える。
- cell-centered velocity と face velocity の二重実装を避けられる。

### D3: config 駆動

現行の YAML 設計を保ち，物理モデルは config で切り替える。

提案：

```yaml
surface_tension:
  formulation: pressure_jump
  stress_closure: affine_jump

poisson:
  operator:
    interface_coupling: affine_jump

projection:
  face_flux_projection: true
  interface_stress_closure: affine_jump
```

互換性：

- `jump_decomposition` は残す。
- 既存結果の再現性確認には `jump_decomposition` を使える。
- 新しい物理ベンチマークでは `affine_jump` を既定にする。

## 最小実装単位

### M1: 汎用 data contract

新規に `InterfaceStressContext` を導入する。
候補配置は `src/twophase/simulation/interface_stress_closure.py`。

責務：

- phase indicator `psi`
- curvature `kappa`
- surface tension `sigma`
- density / inverse-density face coefficient
- face cut 判定
- face normal orientation
- pressure jump `j = [[p]]`
- optional tangential / viscous jump placeholder
- body acceleration face flux `a_f`

最初の実装では `[[p]]=σ κ` のみ必須とし，
粘性応力ジャンプは API に slot だけ用意してゼロにする。

設計上の禁止：

- `capillary_wave_context` のような専用名を作らない。
- `rising_bubble` 分岐を closure 内に入れない。
- `J=σ κ(1-ψ)` の節点圧力場を返さない。

### M2: jump-aware face gradient

face gradient を次の affine 形に拡張する。

```text
G_Γ(p;j)_f = G(p)_f - B_Γ(j)_f
```

cut face では，符号を phase orientation から決める。

```text
G_Γ(p;j)_f = (p_R - p_L - s_f j_f) / d_f
```

ここで `s_f=+1` は `j=p_R-p_L` と同じ向き，
`s_f=-1` は逆向きを表す。

同相 face では現行の `G(p)_f` をそのまま使う。
異相 cut face では現行の `phase_separated` zero mask で
jump contribution まで消してはならない。

### M3: affine PPE operator

PPE は次を解く。

```text
D_f α_f G_Γ(p;j)_f = D_f (u_f^*/Δt + a_f)
```

すなわち operator は affine である。

```text
L_Γ(p;j) = D_f α_f G(p)_f - D_f α_f B_Γ(j)_f
```

実装上は，未知数 `p` に対する linear part は現行 operator を再利用し，
jump contribution は RHS 側の known affine term として一度だけ加える。

重要な違い：

- 現行 legacy: `rhs - L(J)` を解き，最後に `p_total=p_base+J` を作る。
- 新方式: `J` という通常圧力場を作らない。
- 新方式: `B_Γ(j)` は face gradient 内だけに現れる。
- 新方式: 速度補正も同じ `G_Γ(p;j)` を使う。

### M4: correction path の一致

PPE で使った `G_Γ` と，速度補正で使う `G_Γ` は同一でなければならない。

必要な変更点：

- `projection.pressure_fluxes` に `interface_stress_context` を渡せるようにする。
- `project_faces` が cut-face jump flux を受け取れるようにする。
- `correct_ns_velocity_stage` は `p_total` を前提にしない。
- `return_pressure` は unknown pressure `p` と diagnostic jump を分けて返す。

この一致が崩れると，PPE で満たした離散 divergence が速度補正で壊れる。

### M5: body force との統合

上昇気泡を同じ logic で扱うため，浮力は interface 専用処理にしない。
既存の `balanced_buoyancy` が作る face acceleration を
PPE RHS の `a_f` として closure に渡す。

投影後速度は次で決まる。

```text
u_f^{n+1} = u_f^* + Δt a_f - Δt α_f G_Γ(p;j)_f
```

静水圧平衡では `a_f` と `G_Γ` が相殺し，
上昇気泡では重力と曲率ジャンプの非両立 residual が上昇を生む。

## 実装順序

### C1: contract 追加

変更範囲：

- `src/twophase/simulation/interface_stress_closure.py`
- 必要なら `src/twophase/simulation/ns_step_services.py`

内容：

- `InterfaceStressContext` dataclass を追加する。
- `None` のときは現行挙動と bitwise 同等を目標にする。
- `from_surface_tension_state(...)` のような builder を作る。

検証：

- context 無効時に既存 smoke が変化しない。
- sign convention unit test を追加する。

### C2: face affine jump helper

変更範囲：

- `src/twophase/simulation/divergence_ops.py`
- 必要なら `src/twophase/ppe/fccd_matrixfree_helpers.py`

内容：

- cut-face 判定を helper 化する。
- `G_Γ(p;j)` と `B_Γ(j)` を同じ helper から生成する。
- phase-separated coefficient は同相 face に限って適用し，
  cut-face jump term は消さない。

検証：

- manufactured two-cell jump。
- `p_R-p_L=j` なら cut-face flux が 0 になる。
- `j=0` なら現行 gradient と一致する。

### C3: PPE affine path

変更範囲：

- `src/twophase/ppe/fccd_matrixfree.py`
- `src/twophase/ppe/defect_correction.py`

内容：

- `interface_coupling_scheme == "affine_jump"` を追加する。
- legacy の `_subtract_interface_jump_operator` は使わない。
- affine RHS contribution は `D α B_Γ(j)` として一度だけ入れる。
- solve 後に `apply_interface_jump` で pressure field を足さない。

検証：

- `ptp(J)` が大きい manufactured case で
  returned pressure が `-J` に吸収されない。
- `jump_decomposition` legacy は従来通り再現する。

### C4: velocity correction 統合

変更範囲：

- `src/twophase/simulation/ns_step_services.py`
- `src/twophase/simulation/divergence_ops.py`

内容：

- PPE solve と同じ `InterfaceStressContext` を correction に渡す。
- `pressure_fluxes` の返す face correction を jump-aware にする。
- face projection path と cell correction path の符号を揃える。

検証：

- PPE residual と projection 後 divergence が同じ演算子で評価される。
- static droplet で寄生速度が数値丸めレベルに落ちる。

### C5: config と実験の移行

変更範囲：

- `experiment/ch14/config/*.yaml`
- rising bubble / RT 系 config
- 必要なら `docs/01_PROJECT_MAP.md`

内容：

- 物理ベンチマークに `affine_jump` を明示する。
- legacy config は比較用に残す。
- paper 用 experiment は `affine_jump` を使う。

検証：

- ch14 毛管波で signed mode が初期から復元方向へ加速する。
- 上昇気泡で重心加速度が重力・浮力方向と一致する。

## 検証計画

### T0: algebraic cancellation guard

目的：

- 今回の根本原因の再発を検出する。

条件：

- 非ゼロ `j(x)` を与える。
- `rhs≈0` の one-step projection を実施する。

合格：

- `p` が `-J` という通常圧力場として返らない。
- `G_Γ(p;j)` が物理的 jump flux を保持する。

### T1: static droplet equilibrium

目的：

- 定数曲率ジャンプが寄生流れを作らないことを確認する。

合格：

- `||u||_inf` は roundoff / solver tolerance scale。
- volume drift は既存 CLS 誤差 scale 以下。

### T2: manufactured sinusoidal jump

目的：

- 非定数 jump が正しい harmonic pressure response を作ることを確認する。

合格：

- `D α G_Γ(p;j)` が manufactured RHS と一致する。
- 符号反転 test で response も反転する。

### T3: hydrostatic flat column

目的：

- 浮力と圧力投影が静水圧を壊さないことを確認する。

合格：

- flat interface では spurious current が発生しない。
- pressure gauge を変えても face flux は不変。

### T4: capillary wave

目的：

- Prosperetti 型の復元機構が戻ることを確認する。

合格：

- signed mode の初期加速度が `-ω^2 A` と同符号。
- 短時間の位相が理論周期 scale に乗る。
- `kappa` cap の有無で初期物理応答が消えない。

### T5: rising bubble residual

目的：

- 同じ closure が上昇気泡にも使えることを確認する。

合格：

- 初期重心加速度が浮力方向。
- 曲率ジャンプを外すと residual が変わる。
- capillary-only 分岐を通らない。

### T6: no double counting

目的：

- CSF と pressure jump を二重計上しないことを保証する。

合格：

- `stress_closure=affine_jump` では CSF body force が無効。
- `formulation=csf` では affine pressure jump が無効。
- 混在指定は config validation error。

## 数学的な実装契約

### S1: orientation

`j=[[p]]=p^+ - p^-` の `+/-` は `psi` の相定義から一意に決める。
face 法線の向きと phase orientation は別物なので，
必ず `s_f` で変換する。

### S2: gauge invariance

圧力に定数を足しても `G_Γ` と速度補正は変わってはならない。
したがって jump は pressure gauge に混ぜない。

### S3: operator consistency

PPE residual，correction flux，diagnostic divergence は同じ
`D_f α_f G_Γ` を使う。
演算子が一つでもずれると balanced-force ではなくなる。

### S4: legacy preservation

`jump_decomposition` は削除しない。
ただし物理 benchmark の既定経路からは外し，
「代数的相殺を起こす比較対象」として扱う。

## 完了条件

この実装は，次を満たしたときに完了とする。

1. `affine_jump` を選んだとき，`apply_interface_jump` が pressure field を足さない。
2. PPE と velocity correction が同じ `InterfaceStressContext` を使う。
3. static droplet は静止し，capillary wave は復元加速度を持つ。
4. rising bubble が同じ closure 経路で動く。
5. legacy `jump_decomposition` は比較用に残る。
6. paper §14 の capillary result を `affine_jump` 結果で更新できる。

## 推奨コミット分割

1. `interface stress context` — dataclass と config plumbing。
2. `jump-aware face gradient` — cut-face affine gradient と sign tests。
3. `affine PPE path` — `rhs-L(J)` を通らない solver branch。
4. `jump-aware correction` — projection/correction の operator 一致。
5. `benchmark configs` — ch14 / bubble / RT を `affine_jump` へ移行。
6. `validation artifacts` — T0--T6 の結果と §14 paper 更新。

## リスクと対策

| Risk | Failure mode | 対策 |
|---|---|---|
| sign convention | capillary wave が増幅方向へ加速 | two-cell orientation test を最初に固定 |
| cut geometry | jump face の面積・距離が不連続 | 初期版は face-crossing 判定に限定し，後で面積率へ拡張 |
| phase-separated coefficient | jump flux まで 0 になる | cut-face jump term は zero mask の外側で加算 |
| defect correction | wrapper が legacy jump を再適用 | affine path では `apply_interface_jump` を禁止 |
| pressure diagnostics | `p_total` 前提の plot が壊れる | unknown pressure と jump diagnostic を別系列で保存 |
| GPU backend | NumPy 固定 helper が混入 | array ops は `backend.xp` 経由に限定 |

## 直近の実装判断

最初に本体へ入れるべき変更は C1 と C2 である。
理由は，符号・face orientation・zero mask の契約が固まらない限り，
PPE 側を触ると再び「見かけ上収束するが物理が消える」状態になるため。

したがって次の作業では，まず manufactured two-cell / sinusoidal jump の
小さな unit test を作り，`G_Γ(p;j)` の数学契約を固定する。
その後に PPE と correction を接続する。
