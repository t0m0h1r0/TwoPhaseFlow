"""
TwoPhaseFlow シミュレーション CLIエントリポイント。

使用例::

    # YAML 設定で実行
    python src/main.py configs/bubble_2d.yaml

    # チェックポイントからリスタート
    python src/main.py configs/bubble_2d.yaml --restart checkpoints/step_00000200.h5

    # リアルタイム可視化あり
    python src/main.py configs/bubble_2d.yaml --visualize

    # ベンチマーク全実行
    python src/main.py --benchmark --N 32

オプション::

    config           YAML 設定ファイルのパス
    --restart PATH   チェックポイントファイルからリスタート
    --visualize      リアルタイム可視化を有効化
    --benchmark      全ベンチマークを実行（config 不要）
    --N N            ベンチマーク用格子点数（デフォルト: 32）
    --save-dir DIR   ベンチマーク出力ディレクトリ
    --verbose        詳細ログを表示
"""

from __future__ import annotations
import argparse
import os
import sys

# src/ をインポートパスに追加（pip install なしで実行可能にする）
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)


def run_simulation(args: argparse.Namespace) -> None:
    """YAML 設定ファイルに基づいてシミュレーションを実行する。"""
    import numpy as np
    from twophase.configs import load_config
    from twophase.io.checkpoint import CheckpointManager
    from twophase.simulation import TwoPhaseSimulation

    # ── 設定読み込み ────────────────────────────────────────────────
    print(f"設定ファイル読み込み: {args.config}")
    cfg, out_cfg = load_config(args.config)
    print(f"  ndim={cfg.ndim}, N={cfg.N}, L={cfg.L}")
    print(f"  Re={cfg.Re}, Fr={cfg.Fr}, We={cfg.We}")
    print(f"  t_end={cfg.t_end}, cfl={cfg.cfl_number}")
    print(f"  PPEソルバー: {cfg.ppe_solver_type}")

    # ── シミュレーション構築 ─────────────────────────────────────────
    sim = TwoPhaseSimulation(cfg)
    mgr = CheckpointManager(
        directory=out_cfg.get("checkpoint_dir", "checkpoints"),
        use_hdf5=None,
    )

    # ── 初期条件またはリスタート ──────────────────────────────────────
    if args.restart:
        print(f"\nリスタート: {args.restart}")
        mgr.restore(sim, args.restart)
        print(f"  t={sim.time:.6f}, step={sim.step} から再開")
    else:
        _set_default_initial_condition(sim)

    # ── コールバック設定 ─────────────────────────────────────────────
    ckpt_interval = out_cfg.get("checkpoint_interval", 100)
    callbacks = [mgr.make_callback(interval=ckpt_interval)]

    if args.visualize:
        try:
            from twophase.visualization import RealtimeViewer
            viewer = RealtimeViewer(
                sim,
                fields=["psi", "pressure", "velocity"],
                save_dir=os.path.join(out_cfg.get("output_dir", "results"), "frames"),
            )
            callbacks.append(viewer)
            print("リアルタイム可視化: 有効")
        except ImportError:
            print("警告: matplotlib が見つかりません。可視化をスキップします。")

    def combined_callback(s):
        for cb in callbacks:
            cb(s)

    # ── 実行 ─────────────────────────────────────────────────────────
    print(f"\nシミュレーション開始  t={sim.time:.4f} → {cfg.t_end:.4f}\n")
    vis_interval = out_cfg.get("visualization_interval", 50)

    sim.run(
        t_end=cfg.t_end,
        output_interval=vis_interval,
        verbose=True,
        callback=combined_callback,
    )

    # ── 終了処理 ─────────────────────────────────────────────────────
    final_path = mgr.save(sim)
    print(f"\n最終チェックポイント保存: {final_path}")

    if out_cfg.get("save_figures", True):
        _save_final_figures(sim, out_cfg)


def _set_default_initial_condition(sim) -> None:
    """デフォルト初期条件: ドメイン中心付近に球形気泡を配置する。"""
    import numpy as np

    cfg = sim.config
    X_mg = sim.grid.meshgrid()
    X = X_mg[0]
    Y = X_mg[1]

    # 中心は各軸の 1/3 付近、半径はドメイン幅の 0.2 倍
    cx = cfg.L[0] * 0.5
    cy = cfg.L[1] * 0.33
    r0 = min(cfg.L) * 0.2

    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    eps = sim.eps
    psi0 = 1.0 / (1.0 + np.exp((r - r0) / eps))
    sim.psi.data = sim.backend.to_device(psi0)
    print(f"デフォルト初期条件: 中心=({cx:.2f},{cy:.2f}), 半径={r0:.3f}")


def _save_final_figures(sim, out_cfg: dict) -> None:
    """最終フィールドの図を保存する。"""
    try:
        import matplotlib
        matplotlib.use("Agg")  # ヘッドレス環境対応
        import matplotlib.pyplot as plt
        import numpy as np
        from twophase.visualization import plot_level_set, plot_pressure, plot_velocity
    except ImportError:
        print("警告: matplotlib が見つかりません。図の保存をスキップします。")
        return

    out_dir = out_cfg.get("output_dir", "results")
    os.makedirs(out_dir, exist_ok=True)
    be = sim.backend
    grid = sim.grid

    psi_np = np.asarray(be.to_host(sim.psi.data))
    p_np   = np.asarray(be.to_host(sim.pressure.data))
    u_np   = np.asarray(be.to_host(sim.velocity[0]))
    v_np   = np.asarray(be.to_host(sim.velocity[1]))

    fig = plot_level_set(psi_np, grid,
                         title=f"ψ  t={sim.time:.4f}",
                         save_path=os.path.join(out_dir, "final_psi.png"))
    plt.close(fig)

    fig = plot_pressure(p_np, grid,
                        title=f"p  t={sim.time:.4f}",
                        interface_psi=psi_np,
                        save_path=os.path.join(out_dir, "final_pressure.png"))
    plt.close(fig)

    fig = plot_velocity(u_np, v_np, grid,
                        title=f"|u|  t={sim.time:.4f}",
                        interface_psi=psi_np,
                        save_path=os.path.join(out_dir, "final_velocity.png"))
    plt.close(fig)

    print(f"最終フィールド図を保存: {out_dir}/")


def run_benchmarks(args: argparse.Namespace) -> None:
    """全ベンチマークを実行する。"""
    # run_all_benchmarks.py の main() を呼び出す
    import sys
    bench_args = ["--N", str(args.N),
                  "--save-dir", args.save_dir]
    if args.verbose:
        bench_args.append("--verbose")

    # argparse を使わず直接呼び出す
    sys.argv = ["run_all_benchmarks"] + bench_args
    from twophase.benchmarks.run_all_benchmarks import main
    main()


def main():
    parser = argparse.ArgumentParser(
        description="TwoPhaseFlow シミュレーション / ベンチマーク実行ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # シミュレーション用引数
    parser.add_argument("config", nargs="?",
                        help="YAML 設定ファイルのパス")
    parser.add_argument("--restart", type=str, default=None,
                        help="リスタート元チェックポイントファイルのパス")
    parser.add_argument("--visualize", action="store_true",
                        help="リアルタイム可視化を有効化する")

    # ベンチマーク用引数
    parser.add_argument("--benchmark", action="store_true",
                        help="全ベンチマークを実行する（config 不要）")
    parser.add_argument("--N", type=int, default=32,
                        help="ベンチマーク用格子点数（デフォルト: 32）")
    parser.add_argument("--save-dir", type=str, default="results/benchmarks",
                        dest="save_dir",
                        help="ベンチマーク出力ディレクトリ")
    parser.add_argument("--verbose", action="store_true",
                        help="詳細ログを表示する")

    args = parser.parse_args()

    if args.benchmark:
        run_benchmarks(args)
    elif args.config:
        run_simulation(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
