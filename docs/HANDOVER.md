# HANDOVER

Last update: 2026-03-15 (backward compat removal)
Status: All legacy compatibility code removed — SimulationConfig is now pure sub-config composition; SimulationBuilder is the sole construction path

---

# Recent Changes (2026-03-15) — Backward Compatibility Removal

## 変更の目的

後方互換のために残存していたコードをすべて削除し、設計を単純化した。

## 修正ファイル

### `src/twophase/config.py`
- `SimulationConfig` のフラットフィールド（`ndim`, `N`, `L`, `Re`, `Fr`, `We` 等 19 フィールド）を完全削除。
- `to_grid_config()` / `to_fluid_config()` / `to_numerics_config()` / `to_solver_config()` メソッドを削除。
- `from_sub_configs()` クラスメソッドを削除。
- `SimulationConfig` は `grid / fluid / numerics / solver / use_gpu` の 5 フィールドのみの純粋な合成に。

### `src/twophase/simulation/_core.py`
- `TwoPhaseSimulation.__init__(config)` を完全削除（`SimulationBuilder` が唯一の構築経路）。
- `_from_components()` が内部ファクトリメソッドとして唯一残る。
- `run()` / `step_forward()` 内の設定アクセスを `config.grid.*` / `config.numerics.*` 等に統一。

### 全消費者ファイル（フラット config アクセスを修正）

| ファイル | 変更内容 |
|---------|---------|
| `simulation/builder.py` | `config.L[ax]` → `config.grid.L[ax]` 等 |
| `simulation/boundary_condition.py` | `config.bc_type` → `config.numerics.bc_type` 等 |
| `core/grid.py` | `config.ndim` → `config.grid.ndim` 等 |
| `ns_terms/predictor.py` | `config.Re` → `config.fluid.Re` 等 |
| `pressure/ppe_solver.py` | `config.bicgstab_tol` → `config.solver.bicgstab_tol` 等 |
| `pressure/ppe_solver_pseudotime.py` | `config.pseudo_tol` → `config.solver.pseudo_tol` 等 |
| `pressure/ppe_solver_factory.py` | `config.ppe_solver_type` → `config.solver.ppe_solver_type` |
| `main.py` | フラットアクセス修正 + `TwoPhaseSimulation(cfg)` → `SimulationBuilder(cfg).build()` |
| `configs/config_loader.py` | flat YAML キーを各サブ設定クラスに振り分けて構築 |
| `io/checkpoint.py` | `sim.config.ndim` → `sim.config.grid.ndim` 等 |
| `benchmarks/*.py` | サブ設定構文 + `SimulationBuilder` 使用に全更新 |
| `tests/*.py` | `SimulationConfig(ndim=2, ...)` → `SimulationConfig(grid=GridConfig(...))` に全更新 |

## 削減行数

| 削除対象 | 削減量 |
|---------|--------|
| `SimulationConfig` フラット19フィールド | ~40行 |
| `to_*_config()` × 4 メソッド | ~40行 |
| `from_sub_configs()` | ~30行 |
| `TwoPhaseSimulation.__init__()` | ~60行 |
| 後方互換コメント・重複 docstring | ~20行 |
| **合計** | **~190行** |

## 検証

```
pytest src/twophase/tests
→ 28 passed
```

---

# Current State

Two-phase flow solver implemented from scratch.

All tests pass.

```
pytest src/twophase/tests
→ 28 passed
```

Python ≥ 3.9

---

# Recent Changes (2026-03-15) — Architecture Refinement (3rd Pass)

## 削除ファイル

### `src/twophase/simulation.py`
- 旧バージョンのデッドコード（パッケージ `simulation/` が存在するため到達不能）。
- 旧 API（`reinitialize(psi, ccd)` 等）が残存し混乱の元になっていたため削除。

## 修正ファイル

### `src/twophase/ns_terms/predictor.py`
- `ccd` をコンストラクタ注入に変更（`Reinitializer`, `CurvatureCalculator` 等と統一）。
- `__init__(backend, config, ccd, ...)` — `ccd` を第3引数として追加。
- `compute(vel, rho, mu, kappa, psi, dt)` — `ccd` をシグネチャから除去。
- 内部では `self.ccd` を使用する。

### `src/twophase/interfaces/ns_terms.py`
- `INSTerm.compute()` から `ccd` 引数を除去（ISP改善）。
- 新しい NS 項実装はコンストラクタで `ccd` を受け取る設計を推奨する旨をドキュメント化。

### `src/twophase/simulation/_core.py`
- `Predictor(self.backend, config, self.ccd)` — `ccd` を渡すよう更新。
- `predictor.compute(vel_n, rho, mu, kappa, psi, dt)` — `ccd` 引数を削除。

### `src/twophase/simulation/builder.py`
- `Predictor(backend, config, ccd, ...)` — `ccd` を渡すよう更新。
- `with_convection/viscous/gravity/surface_tension()` の型ヒントを `INSTerm` に変更（DIP改善）。
- 内部フィールドも `Optional[INSTerm]` に変更。

### `src/twophase/__init__.py`
- ドキュメント修正: `sim.phi.data` → `sim.psi.data`（存在しないフィールドへの参照を修正）。

### `src/twophase/tests/test_ns_terms.py`
- `Predictor(backend, cfg, ccd)` — 新 API に更新。
- `pred.compute([u, v], rho, mu, kappa, psi, dt=0.01)` — `ccd` 引数を削除。

## 適用したアーキテクチャ改善

| 問題 | 解決策 | 原則 |
|------|--------|------|
| `simulation.py` レガシーデッドコード残存 | ファイル削除 | 一貫性 |
| `Predictor.compute(ccd)` — 他演算子と不整合 | コンストラクタ注入に統一 | ISP |
| `INSTerm.compute(ccd)` — fat interface | `ccd` をシグネチャから除去 | ISP |
| `SimulationBuilder.with_*()` が具象型を要求 | `INSTerm` インターフェース型に変更 | DIP, OCP |
| `__init__.py` に存在しない `sim.phi.data` | `sim.psi.data` に修正 | 正確性 |

---

---

# Recent Changes (2026-03-15) — Architecture Refinement (2nd Pass)

## 新規ファイル

### `src/twophase/interfaces/ns_terms.py`
- `INSTerm` ABC — Navier-Stokes 各項の共通インターフェース。
- `compute(vel, rho, mu, kappa, psi, ccd, dt) -> List` を定義。
- OCP 準拠: 新物理項（熱伝導、磁場等）を Predictor 変更なしに追加可能。

### `src/twophase/interfaces/levelset.py`
- `ILevelSetAdvection` — CLS 移流演算子の ABC。
- `IReinitializer` — 再初期化演算子の ABC（`reinitialize(psi)` シグネチャ）。
- `ICurvatureCalculator` — 曲率計算の ABC（`compute(psi)` シグネチャ）。

### `src/twophase/simulation/builder.py`
- `SimulationBuilder` — TwoPhaseSimulation の構築を担当するビルダー。
- `with_ppe_solver()` / `with_convection()` 等で個別コンポーネントを差し替え可能（OCP）。
- God Constructor 問題を解消（SRP）。

## 修正ファイル

### `src/twophase/config.py`
- `GridConfig`, `FluidConfig`, `NumericsConfig`, `SolverConfig` の 4 サブ設定クラスを追加（SRP）。
- `SimulationConfig` をサブ設定の合成に変更（後方互換フィールドは後続パスで削除済み）。

### `src/twophase/levelset/reinitialize.py`
- `IReinitializer` を実装。
- コンストラクタに `ccd` を追加（`Reinitializer(backend, grid, ccd, eps, n_steps)`）。
- `reinitialize(psi, ccd)` → `reinitialize(psi)` — シグネチャ簡潔化。

### `src/twophase/levelset/curvature.py`
- `ICurvatureCalculator` を実装。
- コンストラクタに `ccd` を追加（`CurvatureCalculator(backend, ccd, eps)`）。
- `compute(psi, ccd)` → `compute(psi)` — シグネチャ簡潔化。

### `src/twophase/pressure/rhie_chow.py`
- コンストラクタに `ccd` を追加（`RhieChowInterpolator(backend, grid, ccd)`）。
- `face_velocity_divergence(..., ccd, dt)` → `face_velocity_divergence(..., dt)` — シグネチャ簡潔化。

### `src/twophase/pressure/velocity_corrector.py`
- コンストラクタに `ccd` を追加（`VelocityCorrector(backend, ccd)`）。
- `correct(..., ccd, dt)` → `correct(..., dt)` — シグネチャ簡潔化。

### `src/twophase/ns_terms/predictor.py`
- DIP 改善: `convection`, `viscous`, `gravity`, `surface_tension` をコンストラクタで注入可能に。
- 省略時はデフォルト生成（後方互換維持）。

### `src/twophase/simulation/_core.py`
- サブモジュール構築をコンストラクタ注入パターンに更新。
- `_from_components()` クラスメソッドを追加（SimulationBuilder 用）。

### `src/twophase/interfaces/__init__.py`
- `INSTerm`, `ILevelSetAdvection`, `IReinitializer`, `ICurvatureCalculator` を追加エクスポート。

### テストファイル
- `test_levelset.py`, `test_ns_terms.py`, `test_pressure.py` — 新 API に更新。

## 適用したアーキテクチャ改善

| 問題 | 解決策 | 原則 |
|------|--------|------|
| SimulationConfig が5関心事を混在 | 4サブ設定クラスへ分割 | SRP |
| God Constructor (13+ 直接生成) | SimulationBuilder に構築を委譲 | SRP, DIP |
| ccd が毎呼び出しで引き渡される | コンストラクタ注入に統一 | ISP |
| Predictor が具象クラスを直接生成 | オプション注入パターンに変更 | DIP, OCP |
| レベルセット演算子に抽象なし | ILevelSetAdvection 等 ABC を追加 | DIP, OCP |

---

# Recent Changes (2026-03-15)

## Pressure solver improvements

### `src/twophase/pressure/rhie_chow.py`
- Vectorized `_rc_flux_1d`: replaced Python `for` loop with `slice`-based numpy ops.

### `src/twophase/pressure/ppe_solver.py`
- Added `p_init` (warm-start) parameter to `solve()`.
- `simulation.py` now passes previous-step pressure `p^n` as `x0` to BiCGSTAB.

### `src/twophase/pressure/ppe_solver_pseudotime.py` (new)
- `PPESolverPseudoTime`: alternative solver using **MINRES** + warm-start.
- Assembles the same FVM matrix as `PPEBuilder` but uses **symmetric pinning**
  (row AND column 0 zeroed), preserving matrix symmetry for MINRES.
- Warm-starts from `p^n` for fast convergence on slowly-varying solutions.
- Enabled via `SimulationConfig(ppe_solver_type="pseudotime")`.

### `src/twophase/config.py`
- New fields: `ppe_solver_type` (`"bicgstab"` | `"pseudotime"`),
  `pseudo_tol`, `pseudo_maxiter`.

### `src/twophase/simulation.py`
- Solver selection based on `config.ppe_solver_type`.
- BiCGSTAB path passes `p_init=self.pressure.data` (warm-start).
- MINRES path calls `PPESolverPseudoTime.solve(p_init, rhs, rho, ccd)`.

---

# Recent Changes (2026-03-15) — Visualization / IO / Config / Benchmarks

## New modules

### `src/twophase/visualization/`
- `plot_scalar.py` — 2D scalar field plots (pressure, ψ, density). `plot_multi_field` for side-by-side layout.
- `plot_vector.py` — velocity magnitude+quiver, vorticity (via CCD), streamlines.
- `realtime_viewer.py` — `RealtimeViewer`: matplotlib interactive callback for `sim.run(callback=viewer)`.

### `src/twophase/io/checkpoint.py`
- `CheckpointManager`: HDF5 (h5py) or npz fallback.
- `save(sim)` / `restore(sim, path)` / `make_callback(interval)`.
- Saves: step, time, ψ, pressure, velocity (all axes), SimulationConfig JSON.
- After `restore()` calls `_update_properties()` + `_update_curvature()` automatically.

### `src/twophase/configs/config_loader.py`
- `load_config(path)` → `(SimulationConfig, output_cfg_dict)`.
- `config_to_yaml(config, path)` for config export.
- Unknown YAML keys emit `UserWarning` (not error).

### `src/twophase/benchmarks/`
- `rising_bubble.py` — Hysing et al. (2009) TC1; records centroid_y, rise velocity, volume error.
- `zalesak_disk.py` — 1-revolution slotted-disk advection test; L1 shape error + volume error.
- `rayleigh_taylor.py` — RT instability; spike/bubble tip tracking.
- `run_all_benchmarks.py` — CLI runner: `python -m twophase.benchmarks.run_all_benchmarks --N 32`.

### `src/main.py`
- CLI entry point: `python src/main.py configs/bubble_2d.yaml [--restart PATH] [--visualize] [--benchmark]`.

### `src/configs/`
- `bubble_2d.yaml` — example config (Re=35, N=64×128).
- `rayleigh_taylor.yaml` — example config (Re=3000, N=64×256).

## Updated
- `src/pyproject.toml` — added optional extras: `vis`, `io`, `all`.

---

# Recent Changes (2026-03-15) — SOLID Refactoring

## 新規モジュール

### `src/twophase/interfaces/`
- `ppe_solver.py` — `IPPESolver` 抽象基底クラス（ABC）。
  - 統一シグネチャ `solve(rhs, rho, dt, p_init=None) → p` を定義。
  - LSP 違反（異なる `solve()` シグネチャ）と DIP 違反（具象クラスへの依存）を解消。

### `src/twophase/pressure/ppe_solver_factory.py`
- `create_ppe_solver(config, backend, grid) → IPPESolver`。
- `SimulationConfig.ppe_solver_type` に基づいてソルバーを生成するファクトリ関数。
- OCP 準拠: 新ソルバー追加時に `TwoPhaseSimulation` の変更が不要になった。

### `src/twophase/simulation/` (パッケージに昇格)
- `_core.py` — `TwoPhaseSimulation` 本体（旧 `simulation.py` から移動）。
- `boundary_condition.py` — `BoundaryConditionHandler`: 壁面 BC の適用ロジックを分離（SRP）。
- `diagnostics.py` — `DiagnosticsReporter`: 発散・体積の診断出力ロジックを分離（SRP）。

### `src/twophase/io/serializers.py`
- `HDF5Serializer` — HDF5 形式の state dict 保存・読込。
- `NpzSerializer` — NumPy npz 形式の state dict 保存・読込。
- `CheckpointManager` から形式別 I/O を分離（SRP）。

## 修正モジュール

### `src/twophase/pressure/ppe_solver.py`
- `IPPESolver` を実装。
- `PPEBuilder` を内部に保持し、呼び出し側が triplet を渡す必要をなくした。
- 統一シグネチャ `solve(rhs, rho, dt, p_init=None)` を採用。

### `src/twophase/pressure/ppe_solver_pseudotime.py`
- `IPPESolver` を実装。
- 旧シグネチャ `solve(p_init, q_h, rho, ccd)` を廃止。
- 統一シグネチャ `solve(rhs, rho, dt, p_init=None)` を採用。

### `src/twophase/simulation.py` → `src/twophase/simulation/_core.py`
- `isinstance(ppe_solver, PPESolverPseudoTime)` チェックを削除（LSP 修正）。
- `_apply_wall_bc()` → `BoundaryConditionHandler.apply()` に委譲。
- `_print_diagnostics()` → `DiagnosticsReporter.report()` に委譲。
- `ppe_builder` フィールドを削除（PPESolver が内包）。
- `create_ppe_solver()` ファクトリ経由でソルバーを取得。

### `src/twophase/io/checkpoint.py`
- `HDF5Serializer` / `NpzSerializer` に I/O を委譲。
- `CheckpointManager` はコーディネータ責務に特化。

### `src/twophase/tests/test_pressure.py`
- 新統一 API `PPESolver(backend, config, grid)` に更新。
- `solve(rhs, rho, dt, p_init=None)` シグネチャに合わせて全テストを更新。

## 適用した SOLID 原則

| 原則 | 対応内容 |
|------|---------|
| SRP | BC・診断・I/O形式別処理を独立クラスに分離 |
| OCP | IPPESolver + factory により新ソルバー追加時に simulation.py 変更不要 |
| LSP | 統一 `solve()` シグネチャで両ソルバーが完全に置換可能 |
| ISP | IPPESolver は最小インターフェースのみ定義 |
| DIP | TwoPhaseSimulation は IPPESolver 抽象に依存、factory で注入 |

---

# Important

Previous `base/` directory has been removed.

Do not reference it.

---

# TODO

- GPU optimization (CuPy kernels)
- Non-uniform grid tests
- 3D verification
- Periodic boundary support
- VTK output writer

---

# Possible Next Tasks

1. Run benchmarks at higher resolution (N=128) and compare to reference values
2. GPU backend verification (CuPy)
3. 3D test case
4. VTK output writer
5. Convergence plots for benchmark problems