"""
数値ソルバーおよび物理演算子の抽象インターフェース。

依存性逆転の原則 (DIP) に基づき、具体的な実装ではなく
抽象に依存する設計を実現するためのモジュール。

インターフェース一覧:
    IPPESolver          — 圧力ポアソン方程式ソルバー（統一シグネチャ）
    INSTerm             — Navier-Stokes 右辺の各項
    ILevelSetAdvection  — CLS 場の移流演算子
    IReinitializer      — CLS 場の再初期化演算子
    ICurvatureCalculator — 界面曲率計算
"""

from .ppe_solver import IPPESolver
from .ns_terms import INSTerm
from .levelset import ILevelSetAdvection, IReinitializer, ICurvatureCalculator

__all__ = [
    "IPPESolver",
    "INSTerm",
    "ILevelSetAdvection",
    "IReinitializer",
    "ICurvatureCalculator",
]
