"""
圧力ポアソン方程式 (PPE) ソルバーの抽象インターフェース。

リスコフ置換の原則 (LSP) と依存性逆転の原則 (DIP) を実現するために、
すべての PPE ソルバー実装が準拠すべき共通インターフェースを定義する。

従来の問題:
    PPESolver と PPESolverPseudoTime のシグネチャが異なっていたため、
    TwoPhaseSimulation.step_forward() で isinstance チェックが必要だった。

解決策:
    IPPESolver を導入し、全実装で統一シグネチャ
        solve(rhs, rho, dt, p_init=None) → p
    を使用することで、呼び出し側を実装の詳細から分離する。
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # 循環インポートを避けるため型ヒントのみ


class MatrixAssemblyUnavailable(RuntimeError):
    """Raised when a PPE solver intentionally does not expose a sparse matrix."""


class IPPESolver(ABC):
    """圧力ポアソン方程式ソルバーの抽象基底クラス。

    すべての具体的なソルバー実装はこのクラスを継承し、
    ``solve`` メソッドを実装しなければならない。

    統一されたシグネチャにより、TwoPhaseSimulation は
    isinstance チェックを行わずにどの実装でも利用できる。
    """

    @abstractmethod
    def solve(
        self,
        rhs,
        rho,
        dt: float,
        p_init=None,
    ):
        """PPE を解き、圧力フィールドを返す。

        ∇·[(1/ρ̃) ∇p] = rhs を解く。

        Parameters
        ----------
        rhs    : array, shape ``grid.shape`` — 右辺 (1/Δt) ∇·u*_RC
        rho    : array, shape ``grid.shape`` — 密度フィールド ρ̃^{n+1}
        dt     : float — タイムステップ幅（行列組立に使用しないが一貫性のため受け取る）
        p_init : optional array, shape ``grid.shape`` — ウォームスタート初期値 p^n

        Returns
        -------
        p : array, shape ``grid.shape`` — 解圧力フィールド p^{n+1}
        """

    def get_matrix(self, rho):
        """Return a sparse PPE matrix for correction methods that require one.

        Matrix-free solvers remain valid :class:`IPPESolver` implementations by
        raising :class:`MatrixAssemblyUnavailable`.  Callers must depend on this
        interface contract rather than checking concrete solver classes or
        probing attributes.
        """
        raise MatrixAssemblyUnavailable(
            f"{type(self).__name__} does not provide an assembled PPE matrix"
        )

    def update_grid(self, grid) -> None:
        """Refresh grid-dependent solver caches after mesh rebuild."""
        return None

    def invalidate_cache(self) -> None:
        """Invalidate backend-specific cached matrix data if any."""
        return None
