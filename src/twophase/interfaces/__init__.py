"""
数値ソルバーの抽象インターフェース。

依存性逆転の原則 (DIP) に基づき、具体的な実装ではなく
抽象に依存する設計を実現するためのモジュール。
"""

from .ppe_solver import IPPESolver

__all__ = ["IPPESolver"]
