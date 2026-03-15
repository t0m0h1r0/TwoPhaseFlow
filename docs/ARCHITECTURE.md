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
    ├── config.py            ← GridConfig / FluidConfig / NumericsConfig / SolverConfig + SimulationConfig
    ├── core/
    ├── ccd/
    ├── levelset/
    ├── ns_terms/
    ├── pressure/
    ├── time_integration/
    ├── interfaces/          ← IPPESolver / INSTerm / ILevelSetAdvection / IReinitializer / ICurvatureCalculator
    ├── simulation/          ← TwoPhaseSimulation + SimulationBuilder + BC + Diagnostics
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
| `config` | GridConfig / FluidConfig / NumericsConfig / SolverConfig + 集約 SimulationConfig |
| `interfaces/` | IPPESolver / INSTerm / ILevelSetAdvection / IReinitializer / ICurvatureCalculator |
| `simulation/` | TwoPhaseSimulation / SimulationBuilder / BC / 診断 |
| `core/` | グリッドとフィールドコンテナ |
| `ccd/` | コンパクト有限差分 (6次精度) |
| `levelset/` | 界面追跡 (CLS) — LevelSetAdvection/Reinitializer/CurvatureCalculator はコンストラクタ注入 |
| `ns_terms/` | Navier–Stokes 各項 (全クラスが `INSTerm` を継承) — Predictor はオプション注入対応 |
| `pressure/` | 圧力ポアソン方程式ソルバー群 — RhieChow/VelocityCorrector はコンストラクタ注入 |
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
interfaces/ (全 ABC — 依存なし)
  IPPESolver           ← 圧力ソルバー統一インターフェース
  INSTerm              ← NS 各項マーカーインターフェース (abstractmethod なし; 各項クラスが独自シグネチャで compute() を実装)
  ILevelSetAdvection   ← CLS 移流演算子
  IReinitializer       ← 再初期化演算子
  ICurvatureCalculator ← 曲率計算
        ▲ 実装
pressure/
  PPESolver            ← PPEBuilder を内包
  PPESolverPseudoTime
  ppe_solver_factory   ← create_ppe_solver(config, backend, grid)
  RhieChowInterpolator ← ccd をコンストラクタ注入
  VelocityCorrector    ← ccd をコンストラクタ注入

levelset/
  LevelSetAdvection    ← ILevelSetAdvection 実装; ccd をコンストラクタ注入
  Reinitializer        ← IReinitializer 実装; ccd をコンストラクタ注入
  CurvatureCalculator  ← ICurvatureCalculator 実装; ccd をコンストラクタ注入

ns_terms/
  Predictor            ← convection/viscous/gravity/st をオプション注入
        ▲ 使用
simulation/
  SimulationBuilder    ← 具象クラスを知る唯一の場所 (SRP)
  TwoPhaseSimulation   ← インターフェースのみに依存 (DIP)
  BoundaryConditionHandler
  DiagnosticsReporter

config/
  GridConfig           ← グリッド設定のみ
  FluidConfig          ← 流体物性のみ
  NumericsConfig       ← 数値スキーム設定
  SolverConfig         ← PPEソルバー設定
  SimulationConfig     ← 上記4サブ設定 + use_gpu の純粋な合成

io/
  HDF5Serializer       ← state dict の HDF5 I/O
  NpzSerializer        ← state dict の NPZ I/O
  CheckpointManager    ← Serializer を使うコーディネータ
```

### PPE ソルバーの追加方法

1. `IPPESolver` を継承した新クラスを作成
2. `solve(rhs, rho, dt, p_init=None)` を実装
3. `pressure/ppe_solver_factory.py` に条件分岐を追加
4. `SolverConfig` に新しい `ppe_solver_type` を追加

→ `TwoPhaseSimulation` 自体の変更は不要（OCP 準拠）

---

### SimulationConfig の使い方

```python
from twophase.config import SimulationConfig, GridConfig, FluidConfig, NumericsConfig, SolverConfig
from twophase.simulation.builder import SimulationBuilder

cfg = SimulationConfig(
    grid=GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0)),
    fluid=FluidConfig(Re=100., Fr=1., We=10.),
    numerics=NumericsConfig(t_end=2.0, cfl_number=0.3),
    solver=SolverConfig(ppe_solver_type="bicgstab"),
)
sim = SimulationBuilder(cfg).build()
```

`TwoPhaseSimulation(cfg)` 直接呼び出しは廃止。構築は `SimulationBuilder` 経由のみ。

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
