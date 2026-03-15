# HANDOVER

Last update: 2026-03-15
Status: SOLID refactoring applied — interfaces / factory / SRP decomposition

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