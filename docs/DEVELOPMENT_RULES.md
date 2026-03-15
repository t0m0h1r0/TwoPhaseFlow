# Development Rules

General

- Follow the numerical method defined in `paper/`
- Implementation must be inside `src/`
- Tests must be added for new functionality

Coding Rules

- No global mutable state
- Dependencies via constructor injection
- Backend must use `xp = backend.xp`
- Support `ndim = 2 or 3`

Testing

Every new feature must include:

- unit test
- numerical validation when possible

Prohibited

- referencing deleted directories
- hardcoding numpy when backend exists
- adding external dependencies without reason

---

## SOLID Rules (2026-03-15 以降)

### PPE ソルバーの追加

新しい PPE ソルバーを実装する場合:

1. `twophase/interfaces/ppe_solver.py` の `IPPESolver` を継承する
2. `solve(rhs, rho, dt, p_init=None)` を実装する
3. `pressure/ppe_solver_factory.py` にエントリを追加する
4. `SolverConfig.ppe_solver_type` に新しい値を追加する

`TwoPhaseSimulation` 自体を変更してはならない（OCP）。

### シミュレーション補助ロジックの追加

境界条件・診断・初期化など、ソルバーコアとは無関係な処理は
`twophase/simulation/` 内の専用クラスに実装し、
`TwoPhaseSimulation` はそれを使うだけにする（SRP）。

### I/O 形式の追加

新しいチェックポイント形式を追加する場合:

1. `twophase/io/serializers.py` に `save(path, state)` / `load(path)` を持つクラスを追加する
2. `CheckpointManager.__init__` でそのシリアライザを選択するロジックを追加する

`CheckpointManager` に形式固有のコードを直接書いてはならない（SRP）。

### Config 設定の追加

新しいシミュレーションパラメータを追加する場合:

- グリッド設定 → `GridConfig` に追加する
- 流体物性 → `FluidConfig` に追加する
- 数値スキーム → `NumericsConfig` に追加する
- ソルバー設定 → `SolverConfig` に追加する

`SimulationConfig` には直接フィールドを追加しない。サブ設定クラスが真実の源泉。

### レベルセット演算子の差し替え

`Reinitializer`, `CurvatureCalculator` の代替実装を追加する場合:

1. `IReinitializer` / `ICurvatureCalculator` を継承する
2. `reinitialize(psi)` / `compute(psi)` を実装する（ccd はコンストラクタ注入）
3. `SimulationBuilder` で注入する

### NS 物理項の追加

新しい Navier-Stokes 右辺項（例: 熱伝導項、磁場項）を追加する場合:

1. `INSTerm` を継承したクラスを作成する
2. `compute(vel, rho, mu, kappa, psi, dt) -> List` を実装する（`ccd` はコンストラクタ注入）
3. `SimulationBuilder` または `Predictor` のコンストラクタ引数で注入する

`Predictor` 自体を変更してはならない（OCP）。

### シミュレーション構築のカスタマイズ

コンポーネントを差し替えてシミュレーションを構築する場合:

```python
from twophase.simulation.builder import SimulationBuilder

sim = (SimulationBuilder(config)
       .with_ppe_solver(my_custom_solver)
       .with_convection(my_custom_convection)
       .build())
```

`TwoPhaseSimulation.__init__` を直接変更してはならない（OCP）。