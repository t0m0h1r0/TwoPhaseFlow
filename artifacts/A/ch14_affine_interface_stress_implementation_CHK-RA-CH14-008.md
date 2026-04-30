# CHK-RA-CH14-008 — affine interface-stress closure implementation

## 要旨

CHK-RA-CH14-006/007 の設計に従い，毛管波専用ではない
汎用 interface-stress closure を実装した。

実装方針：

- legacy `jump_decomposition` は削除しない。
- 新しい物理 benchmark 経路として `affine_jump` を追加する。
- `J=σ κ(1-ψ)` を通常圧力場として作らない。
- PPE RHS と速度補正の両方で同じ face affine jump
  `G_Γ(p;j)=G(p)-B_Γj` を使う。
- ch14 capillary / rising bubble / Rayleigh--Taylor は同じ
  `affine_jump` 経路を使う。

## 実装内容

### C1: interface-stress data contract

追加：

- `src/twophase/simulation/interface_stress_closure.py`

主な API：

- `InterfaceStressContext`
- `build_interface_stress_context(...)`
- `signed_pressure_jump_gradient(...)`

符号契約：

```text
j = p_gas - p_liquid = σ κ
G_Γ(p;j)_f = (p_hi - p_lo - s_f j_f) / d_f
```

液体から気体へ向かう cut face では `s_f=+1`，
気体から液体へ向かう cut face では `s_f=-1`。

### C2: jump-aware face gradient

変更：

- `src/twophase/simulation/divergence_ops.py`

`FCCDDivergenceOperator.pressure_fluxes(...)` に
`interface_coupling_scheme="affine_jump"` と
`interface_stress_context` を追加した。

重要点：

- same-phase face は従来の pressure gradient。
- cut face は `G(p)-B_Γ(j)`。
- `phase_separated` の zero mask は legacy 経路には残す。
- `affine_jump` では cut-face jump flux を zero mask で消さない。

### C3: affine PPE path

変更：

- `src/twophase/ppe/fccd_matrixfree.py`
- `src/twophase/ppe/fccd_matrixfree_helpers.py`
- `src/twophase/ppe/fccd_matrixfree_lifecycle.py`
- `src/twophase/ppe/defect_correction.py`

新経路：

```text
D_f α_f G(p)_f = rhs + D_f α_f B_Γ(j)_f
```

禁止したこと：

- `rhs - L(J)` を使わない。
- solve 後に `p_total=p_base+J` を作らない。
- `apply_interface_jump(...)` は `affine_jump` では identity。

gauge：

- legacy `jump_decomposition` は phase-separated block gauge を維持する。
- `affine_jump` は cut face が連結するため global single gauge にする。

### C4: velocity correction 接続

変更：

- `src/twophase/simulation/ns_step_services.py`

`correct_ns_velocity_stage(...)` が `affine_jump` のとき
PPE と同じ `InterfaceStressContext` を projection に渡す。
これにより PPE residual と velocity correction が同じ
`D_f α_f G_Γ` を使う。

### C5: ch14 config 移行

変更：

- `experiment/ch14/config/ch14_capillary.yaml`
- `experiment/ch14/config/ch14_rising_bubble.yaml`
- `experiment/ch14/config/ch14_rayleigh_taylor.yaml`
- `experiment/ch14/config/README.md`

3 benchmark はすべて：

```yaml
interface_coupling: affine_jump
```

へ移行した。

## 追加テスト

追加：

- `src/twophase/tests/test_interface_stress_closure.py`

追加・更新：

- `test_signed_pressure_jump_gradient_orientation`
- `test_affine_jump_pressure_flux_preserves_cut_face_jump`
- `test_affine_jump_flux_vanishes_when_pressure_satisfies_jump`
- `test_affine_jump_ppe_rhs_keeps_nonzero_cut_face_drive`
- `test_pressure_jump_accepts_affine_jump_coupling`
- `test_pressure_jump_constructor_accepts_affine_jump`
- `test_affine_jump_corrector_forwards_interface_context`
- `test_affine_jump_pressure_stack_one_step_no_nan`

## 検証

### Local targeted

```text
12 passed
```

対象：

- `test_interface_stress_closure.py`
- affine config validation
- legacy pressure-jump smoke
- affine correction forwarding
- affine one-step NS smoke

### Remote targeted

Command:

```text
make test PYTEST_ARGS="-k affine_jump -q"
```

Result:

```text
7 passed, 425 deselected
```

### Remote full-test note

`make test PYTEST_ARGS="<node ids>"` は `remote.sh test` が内部で
`python -m pytest twophase/tests "$@"` を実行するため，
node id 指定でも `twophase/tests` 全体が収集・実行された。

その full remote run は 7 件失敗したが，失敗原因は本変更ではなく，
remote workdir に次の ch13 config が存在しないことだった。

- `experiment/ch13/config/ch13_capillary_water_air_alpha2_n128.yaml`
- `experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256.yaml`

本変更対象の affine tests は remote `-k affine_jump` で通過済み。

## コミット

- `bc4034e2` — `feat: add affine interface stress closure`
- `ed171595` — `config: use affine jump for ch14 interface stress`
- `962f4ea2` — `test: cover affine jump ns smoke`

## 残る検証

今回の実装は one-step NS smoke まで完了した。
次に実験結果として論文へ反映するには，ch14 capillary / rising bubble /
Rayleigh--Taylor の本実行を remote で回し，時系列・保存性・理論応答を
更新する必要がある。

推奨順：

1. `make cycle EXP=experiment/run.py ARGS="--config ch14_capillary"`
2. capillary signed mode / velocity response を確認。
3. `make cycle EXP=experiment/run.py ARGS="--config ch14_rising_bubble"`
4. bubble centroid / rise velocity を確認。
5. `make cycle EXP=experiment/run.py ARGS="--config ch14_rayleigh_taylor"`
6. §14 paper figures and text を affine results に更新。

## SOLID audit

[SOLID-X] なし。

- 新規 contract は `InterfaceStressContext` に分離した。
- PPE solver，projection，config parser の既存責務を保った。
- legacy `jump_decomposition` は削除せず比較経路として保持した。
