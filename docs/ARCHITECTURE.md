# Architecture

## Repository structure

```
src/
├── pyproject.toml
├── README.md
├── main.py
├── configs/
│   ├── bubble_2d.yaml
│   └── rayleigh_taylor.yaml
└── twophase/
    ├── backend.py
    ├── config.py
    ├── core/
    ├── ccd/
    ├── levelset/
    ├── ns_terms/
    ├── pressure/
    ├── time_integration/
    ├── interfaces/        ← NEW (SOLID refactoring)
    ├── simulation/        ← NEW (SOLID refactoring; 旧 simulation.py)
    ├── visualization/
    ├── io/
    ├── configs/
    ├── benchmarks/
    └── tests/
```

---

## Module roles

| Module | Purpose |
|--------|---------|
| `backend` | numpy/cupy スイッチ |
| `config` | シミュレーションパラメータ (SimulationConfig dataclass) |
| `interfaces/` | 抽象インターフェース (IPPESolver ABC) |
| `simulation/` | メインタイムループ / BC / 診断 |
| `core/` | グリッドとフィールドコンテナ |
| `ccd/` | コンパクト有限差分 (6次精度) |
| `levelset/` | 界面追跡 (CLS) |
| `ns_terms/` | Navier–Stokes 各項 |
| `pressure/` | 圧力ポアソン方程式ソルバー群 |
| `time_integration/` | CFL 計算 / TVD-RK3 |
| `visualization/` | スカラー・ベクトル場プロット、リアルタイム表示 |
| `io/` | チェックポイント保存・リスタート |
| `configs/` | YAML 設定ファイルローダー |
| `benchmarks/` | Rising bubble / Zalesak / Rayleigh-Taylor |

---

## Solver Workflow

```
sim.run()
  ├── Step 1: CLS advection        (levelset/advection.py)
  ├── Step 2: Reinitialization     (levelset/reinitialize.py)
  ├── Step 3: Material properties  (levelset/heaviside.py)
  ├── Step 4: Curvature            (levelset/curvature.py)
  ├── Step 5: Predictor u*         (ns_terms/predictor.py)
  ├── Step 6: PPE solve            (pressure/ via IPPESolver)
  │     ├── Rhie-Chow divergence   (pressure/rhie_chow.py)
  │     └── IPPESolver.solve()     (PPESolver or PPESolverPseudoTime)
  ├── Step 7: Velocity correction  (pressure/velocity_corrector.py)
  └── BC apply                     (simulation/boundary_condition.py)
```

---

## SOLID Architecture (2026-03-15 以降)

### Dependency flow

```
interfaces/IPPESolver  (ABC)
        ▲ 実装
pressure/
  PPESolver            ← PPEBuilder を内包
  PPESolverPseudoTime
  ppe_solver_factory   ← create_ppe_solver(config, backend, grid)
        ▲ 使用
simulation/
  TwoPhaseSimulation   ← IPPESolver に依存（具象クラスに依存しない）
  BoundaryConditionHandler
  DiagnosticsReporter

io/
  HDF5Serializer       ← state dict の HDF5 I/O
  NpzSerializer        ← state dict の NPZ I/O
  CheckpointManager    ← Serializer を使うコーディネータ
```

### PPE ソルバーの追加方法

1. `IPPESolver` を継承した新クラスを作成
2. `solve(rhs, rho, dt, p_init=None)` を実装
3. `pressure/ppe_solver_factory.py` に条件分岐を追加
4. `SimulationConfig` に新しい `ppe_solver_type` を追加

→ `TwoPhaseSimulation` 自体の変更は不要（OCP 準拠）

---

## Key design decisions

- **`xp = backend.xp`** — 全数値モジュールは直接 numpy/cupy を import せず、backend 経由で配列名前空間を取得する。
- **コールバックパターン** — `sim.run(callback=f)` で可視化・チェックポイントを注入。ソルバーは可視化モジュールに依存しない。
- **統一 PPE インターフェース** — `IPPESolver.solve(rhs, rho, dt, p_init=None)` により、呼び出し側は具体的なソルバー実装を知らなくてよい。
- **global mutable state 禁止** — 全状態はシミュレーションインスタンスが保持する。

---

## Known Issues

1. **非一様格子テスト未整備** — `alpha_grid > 1` パスのテストは存在しない。
2. **3次元未検証** — コードは `ndim=3` をサポートしているが、テストは 2次元のみ。
3. **周期境界条件** — `bc_type="periodic"` の実装は未完了。
