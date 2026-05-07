"""
可視化モジュール。

スカラー場・ベクトル場のポスト処理可視化と
リアルタイム表示機能を提供する。
シミュレーション本体はこのモジュールに依存しない設計。
"""

from .plot_scalar import (
    plot_scalar_field,
    plot_pressure,
    plot_level_set,
    plot_density,
)
from .plot_vector import (
    plot_velocity,
    plot_vorticity,
    plot_streamlines,
)
from .plot_fields import (
    DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR,
    DEFAULT_SPEED_CMAP,
    DEFAULT_VECTOR_CMAP,
    DEFAULT_VECTOR_COLOR,
    DEFAULT_VECTOR_OUTLINE_COLOR,
    draw_clean_velocity_arrows,
    field_with_contour,
    positive_range,
    streamlines_colored,
    velocity_arrows,
    symmetric_range,
)
from .realtime_viewer import RealtimeViewer

__all__ = [
    "plot_scalar_field",
    "plot_pressure",
    "plot_level_set",
    "plot_density",
    "plot_velocity",
    "plot_vorticity",
    "plot_streamlines",
    "DEFAULT_SPEED_CMAP",
    "DEFAULT_VECTOR_CMAP",
    "DEFAULT_VECTOR_COLOR",
    "DEFAULT_VECTOR_OUTLINE_COLOR",
    "DEFAULT_QUIVER_OUTLINE_WIDTH_FACTOR",
    "draw_clean_velocity_arrows",
    "field_with_contour",
    "positive_range",
    "streamlines_colored",
    "velocity_arrows",
    "symmetric_range",
    "RealtimeViewer",
]
