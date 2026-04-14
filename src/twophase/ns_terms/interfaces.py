"""
Navier-Stokes 各項のマーカーインターフェース。

DIP（依存性逆転原則）に基づき、SimulationBuilder が NS 各項を
型安全に受け取るためのタグインターフェース。

設計方針:
    - 各 NS 項（対流・粘性・重力・表面張力）は物理的に異なる引数を必要とするため、
      統一した compute() シグネチャを強制しない。
    - このインターフェースは「NS 右辺の1項である」ことを表明するマーカーとして機能する。
    - Predictor は各具象クラスの実際のシグネチャでメソッドを呼ぶ。
      SimulationBuilder.with_convection() 等の型ヒントで安全性を担保する。

新しい物理モデル（熱伝導項、磁場項等）を追加する場合:
    1. INSTerm を継承したクラスを作成する
    2. 必要な引数でコンストラクタと compute() を実装する
    3. SimulationBuilder で注入し、Predictor の呼び出し側を拡張する
    → 他の NS 項クラスへの変更は不要（OCP準拠）
"""

from __future__ import annotations
from abc import ABC


class INSTerm(ABC):
    """Navier-Stokes 右辺の各項のマーカーインターフェース。

    具象クラス（ConvectionTerm, ViscousTerm 等）はこのクラスを継承し、
    それぞれの物理計算に適したシグネチャで compute() を実装する。
    SimulationBuilder の with_*() メソッドはこの型を受け取り、
    カスタム実装の注入を型ヒントレベルで表明する。
    """
