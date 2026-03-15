"""
ベンチマーク問題モジュール。

論文 Section 10.3 に記載されたベンチマーク問題の実装。

各ベンチマークは独立した実行可能モジュールとして実装されており、
設定・実行・検証・可視化を含む。

利用可能なベンチマーク:
    - rising_bubble   : 上昇気泡（浮力駆動の 2 相流れ）
    - zalesak_disk    : Zalesak のスロット付き円盤（移流精度の検証）
    - rayleigh_taylor : Rayleigh-Taylor 不安定性
"""

from .rising_bubble import RisingBubbleBenchmark
from .zalesak_disk import ZalesakDiskBenchmark
from .rayleigh_taylor import RayleighTaylorBenchmark

__all__ = [
    "RisingBubbleBenchmark",
    "ZalesakDiskBenchmark",
    "RayleighTaylorBenchmark",
]
