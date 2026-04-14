"""
全ベンチマーク一括実行スクリプト。

``python -m twophase.benchmarks.run_all_benchmarks`` または
``python src/twophase/benchmarks/run_all_benchmarks.py`` で実行する。

オプション::

    --N N           格子点数（デフォルト: 32, 粗め検証用）
    --save-dir DIR  出力ディレクトリ（デフォルト: results/benchmarks）
    --skip NAME     スキップするベンチマーク名（複数指定可）
                    選択肢: rising_bubble, zalesak_disk, rayleigh_taylor
    --verbose       詳細ログを表示

使用例::

    python -m twophase.benchmarks.run_all_benchmarks --N 32 --verbose
    python -m twophase.benchmarks.run_all_benchmarks --N 64 --skip rayleigh_taylor
"""

from __future__ import annotations
import argparse
import os
import time
import traceback


def run_rising_bubble(N: int, save_dir: str, verbose: bool) -> dict:
    from .rising_bubble import RisingBubbleBenchmark
    bench = RisingBubbleBenchmark(N=N, t_end=3.0, verbose=verbose)
    results = bench.run()
    bench.print_metrics(results)
    bench.plot(results, save_dir=os.path.join(save_dir, "rising_bubble"))
    return {
        "name":         "rising_bubble",
        "l1_or_cy":     results["final_centroid_y"],
        "volume_error": results["volume_error"],
    }


def run_zalesak_disk(N: int, save_dir: str, verbose: bool) -> dict:
    from .zalesak_disk import ZalesakDiskBenchmark
    bench = ZalesakDiskBenchmark(N=N, n_rev=1.0)
    results = bench.run(verbose=verbose)
    bench.print_metrics(results)
    bench.plot(results, save_dir=os.path.join(save_dir, "zalesak_disk"))
    return {
        "name":         "zalesak_disk",
        "l1_or_cy":     results["l1_error"],
        "volume_error": results["volume_error"],
    }


def run_rayleigh_taylor(N: int, save_dir: str, verbose: bool) -> dict:
    from .rayleigh_taylor import RayleighTaylorBenchmark
    bench = RayleighTaylorBenchmark(N=N, t_end=3.0)
    results = bench.run(verbose=verbose)
    bench.print_metrics(results)
    bench.plot(results, save_dir=os.path.join(save_dir, "rayleigh_taylor"))
    return {
        "name":         "rayleigh_taylor",
        "l1_or_cy":     results["spike_tips"][-1],
        "volume_error": results["volume_error"],
    }


BENCHMARKS = {
    "rising_bubble":   run_rising_bubble,
    "zalesak_disk":    run_zalesak_disk,
    "rayleigh_taylor": run_rayleigh_taylor,
}


def main():
    parser = argparse.ArgumentParser(
        description="全ベンチマーク問題を実行し、結果を保存する。"
    )
    parser.add_argument("--N", type=int, default=32,
                        help="格子点数（デフォルト: 32）")
    parser.add_argument("--save-dir", type=str, default="results/benchmarks",
                        help="出力ディレクトリ（デフォルト: results/benchmarks）")
    parser.add_argument("--skip", nargs="*", default=[],
                        choices=list(BENCHMARKS.keys()),
                        help="スキップするベンチマーク名")
    parser.add_argument("--verbose", action="store_true",
                        help="詳細ログを表示する")
    args = parser.parse_args()

    os.makedirs(args.save_dir, exist_ok=True)
    summary = []

    print("=" * 60)
    print("  TwoPhaseFlow ベンチマーク実行")
    print(f"  格子点数 N = {args.N}")
    print(f"  出力先   = {args.save_dir}")
    print("=" * 60)

    for name, runner in BENCHMARKS.items():
        if name in args.skip:
            print(f"\n  [{name}] スキップ\n")
            continue

        print(f"\n{'='*60}")
        print(f"  実行中: {name}")
        print(f"{'='*60}")
        t_start = time.time()

        try:
            metrics = runner(args.N, args.save_dir, args.verbose)
            elapsed = time.time() - t_start
            metrics["elapsed_sec"] = elapsed
            metrics["status"] = "OK"
            print(f"  完了: {elapsed:.1f} 秒")
        except Exception as e:
            elapsed = time.time() - t_start
            print(f"\n  [エラー] {name}: {e}")
            traceback.print_exc()
            metrics = {
                "name": name, "status": "ERROR",
                "error": str(e), "elapsed_sec": elapsed,
            }

        summary.append(metrics)

    # ── サマリー表示 ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  ベンチマーク完了サマリー")
    print("=" * 60)
    print(f"  {'ベンチマーク名':<22} {'状態':<8} {'主要指標':<14} {'体積誤差':<14} {'時間(秒)'}")
    print("  " + "-" * 58)
    for m in summary:
        if m["status"] == "OK":
            print(
                f"  {m['name']:<22} {'OK':<8} "
                f"{m['l1_or_cy']:<14.4f} "
                f"{m['volume_error']:<14.2e} "
                f"{m['elapsed_sec']:.1f}"
            )
        else:
            print(f"  {m['name']:<22} {'ERROR':<8} {'---':<14} {'---':<14}")
    print("=" * 60)


if __name__ == "__main__":
    main()
