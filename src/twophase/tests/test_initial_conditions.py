"""
Tests for twophase.initial_conditions.

Coverage
--------
1. Circle: ψ ≈ 1 at center (liquid interior), ψ ≈ 0 far away.
2. Circle gas bubble in liquid: ψ ≈ 0 inside bubble, ψ ≈ 1 outside.
3. Two overlapping liquid circles: merged liquid region (no gap).
4. Rectangle: inside → liquid, outside → gas.
5. HalfSpace: lower half liquid.
6. from_dict / YAML round-trip for each shape type.
7. InitialConditionBuilder.from_dict with multiple shapes.
8. background_phase='liquid' with gas circle carved out.
"""

import numpy as np
import pytest

from ..simulation.initial_conditions import (
    InitialConditionBuilder,
    Circle,
    Ellipse,
    Rectangle,
    HalfSpace,
    SinusoidalInterface,
    shape_from_dict,
    VelocityField,
    RigidRotation,
    UniformFlow,
    velocity_field_from_dict,
)
from ..simulation.runtime_setup import normalise_ic_dict
from ..core.grid import Grid
from ..config import GridConfig
from ..backend import Backend


# ── テスト用グリッド ───────────────────────────────────────────────────────────

@pytest.fixture
def grid_2d():
    """64×64 uniform grid on [0,1]²."""
    backend = Backend(use_gpu=False)
    cfg = GridConfig(ndim=2, N=(64, 64), L=(1.0, 1.0))
    return Grid(cfg, backend)


def _eps(grid):
    """デフォルトの ε = 1.5 × dx_min。"""
    dx_min = min(grid.L[ax] / grid.N[ax] for ax in range(grid.ndim))
    return 1.5 * dx_min


# ── 1. 液体円（気体背景） ─────────────────────────────────────────────────────

def test_circle_liquid_center_value(grid_2d):
    """Center node should be fully liquid (ψ ≈ 1)."""
    grid = grid_2d
    eps = _eps(grid)
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase="liquid"))
    psi = builder.build(grid, eps)

    # (0.5, 0.5) に最も近いノードのインデックス
    idx_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_x, idx_y] > 0.99, f"Center ψ = {psi[idx_x, idx_y]:.6f}, expected > 0.99"


def test_circle_liquid_far_value(grid_2d):
    """Corner (0, 0) is far from the liquid droplet and should be nearly gas (ψ ≈ 0)."""
    grid = grid_2d
    eps = _eps(grid)
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(Circle(center=(0.5, 0.5), radius=0.25, interior_phase="liquid"))
    psi = builder.build(grid, eps)

    assert psi[0, 0] < 0.01, f"Corner ψ = {psi[0, 0]:.6f}, expected < 0.01"


# ── 2. 気泡（液体背景に気体円） ────────────────────────────────────────────────

def test_gas_bubble_in_liquid_background(grid_2d):
    """Gas bubble in liquid: ψ ≈ 0 inside bubble, ψ ≈ 1 outside."""
    grid = grid_2d
    eps = _eps(grid)
    builder = InitialConditionBuilder(background_phase="liquid")
    builder.add(Circle(center=(0.5, 0.5), radius=0.20, interior_phase="gas"))
    psi = builder.build(grid, eps)

    idx_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_x, idx_y] < 0.01, (
        f"Bubble center ψ = {psi[idx_x, idx_y]:.6f}, expected < 0.01"
    )
    # 外側（角）は液体
    assert psi[0, 0] > 0.99, f"Corner ψ = {psi[0, 0]:.6f}, expected > 0.99"


# ── 3. 重なる液体円の合成（ギャップなし） ──────────────────────────────────────

def test_two_overlapping_liquid_circles(grid_2d):
    """Two side-by-side liquid circles should leave no dry gap between them.

    Centers at (0.3, 0.5) and (0.7, 0.5) with r=0.32.
    At the midpoint (0.5, 0.5) the SDF is 0.2 - 0.32 = -0.12.
    With ε ≈ 0.023: |φ/ε| ≈ 5.1, so ψ > 0.99.
    """
    grid = grid_2d
    eps = _eps(grid)
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(Circle(center=(0.3, 0.5), radius=0.32, interior_phase="liquid"))
    builder.add(Circle(center=(0.7, 0.5), radius=0.32, interior_phase="liquid"))
    psi = builder.build(grid, eps)

    # それぞれの中心
    for cx in (0.3, 0.7):
        idx_x = np.argmin(np.abs(grid.coords[0] - cx))
        idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
        assert psi[idx_x, idx_y] > 0.99, (
            f"Circle center ({cx}, 0.5): ψ = {psi[idx_x, idx_y]:.6f}"
        )

    # 中間点 (0.5, 0.5): SDF = -0.12 ≪ -ε → ψ > 0.99
    idx_mid_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_mid_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_mid_x, idx_mid_y] > 0.99, (
        f"Midpoint ψ = {psi[idx_mid_x, idx_mid_y]:.6f}, circles overlap so expected > 0.99"
    )


# ── 4. 矩形 ──────────────────────────────────────────────────────────────────

def test_rectangle_liquid(grid_2d):
    """Rectangle interior is liquid, exterior is gas."""
    grid = grid_2d
    eps = _eps(grid)
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(Rectangle(
        bounds=[(0.2, 0.8), (0.3, 0.7)],
        interior_phase="liquid",
    ))
    psi = builder.build(grid, eps)

    # 矩形中心 (0.5, 0.5) → 液体
    idx_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_x, idx_y] > 0.99, f"Rectangle center ψ = {psi[idx_x, idx_y]:.6f}"

    # 外側の角 (0.0, 0.0) → 気体
    assert psi[0, 0] < 0.01, f"Exterior ψ = {psi[0, 0]:.6f}"


# ── 5. 半空間 ─────────────────────────────────────────────────────────────────

def test_half_space_lower_liquid(grid_2d):
    """HalfSpace: lower half (y ≤ 0.5) is liquid, upper half is gas."""
    grid = grid_2d
    eps = _eps(grid)
    # 法線 (0, 1)（+y 方向外向き）、オフセット 0.5 → y ≤ 0.5 が液体
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(HalfSpace(normal=(0.0, 1.0), offset=0.5, interior_phase="liquid"))
    psi = builder.build(grid, eps)

    # y = 0.1（液体側）
    idx_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_y_low = np.argmin(np.abs(grid.coords[1] - 0.1))
    assert psi[idx_x, idx_y_low] > 0.99, (
        f"Lower half ψ = {psi[idx_x, idx_y_low]:.6f}, expected > 0.99"
    )

    # y = 0.9（気体側）
    idx_y_high = np.argmin(np.abs(grid.coords[1] - 0.9))
    assert psi[idx_x, idx_y_high] < 0.01, (
        f"Upper half ψ = {psi[idx_x, idx_y_high]:.6f}, expected < 0.01"
    )


# ── 6. shape_from_dict ラウンドトリップ ────────────────────────────────────────

def test_shape_from_dict_circle(grid_2d):
    """shape_from_dict should produce a Circle identical to manual construction."""
    grid = grid_2d
    eps = _eps(grid)

    s_manual = Circle(center=(0.5, 0.5), radius=0.2, interior_phase="liquid")
    s_dict = shape_from_dict(
        {"type": "circle", "center": [0.5, 0.5], "radius": 0.2, "interior_phase": "liquid"}
    )

    coords = grid.meshgrid()
    np.testing.assert_allclose(s_manual.sdf(*coords), s_dict.sdf(*coords))
    assert s_dict.interior_phase == "liquid"


def test_shape_from_dict_bubble_defaults_to_gas():
    s = shape_from_dict({"type": "bubble", "center": [0.5, 0.5], "radius": 0.2})

    assert isinstance(s, Circle)
    assert s.interior_phase == "gas"


def test_shape_from_dict_rectangle_bounds(grid_2d):
    grid = grid_2d
    eps = _eps(grid)

    s = shape_from_dict({
        "type": "rectangle",
        "bounds": [[0.2, 0.8], [0.1, 0.6]],
        "interior_phase": "gas",
    })
    assert isinstance(s, Rectangle)
    assert s.interior_phase == "gas"
    assert s.bounds == ((0.2, 0.8), (0.1, 0.6))


def test_shape_from_dict_rectangle_flat_keys(grid_2d):
    """Flat x_min/x_max/y_min/y_max keys should also work."""
    s = shape_from_dict({
        "type": "rectangle",
        "x_min": 0.1, "x_max": 0.9,
        "y_min": 0.2, "y_max": 0.8,
    })
    assert isinstance(s, Rectangle)
    assert s.bounds[0] == (0.1, 0.9)
    assert s.bounds[1] == (0.2, 0.8)


def test_shape_from_dict_half_space(grid_2d):
    s = shape_from_dict({
        "type": "half_space",
        "normal": [0.0, 1.0],
        "offset": 0.5,
        "interior_phase": "liquid",
    })
    assert isinstance(s, HalfSpace)
    assert s.interior_phase == "liquid"
    # 法線は自動正規化されているはず
    np.testing.assert_allclose(np.linalg.norm(s.normal), 1.0)


def test_shape_from_dict_ellipse(grid_2d):
    """shape_from_dict should deserialize a 2-D ellipse."""
    grid = grid_2d
    eps = _eps(grid)
    s = shape_from_dict({
        "type": "ellipse",
        "center": [0.5, 0.5],
        "semi_axes": [0.30, 0.15],
        "interior_phase": "liquid",
    })
    assert isinstance(s, Ellipse)

    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(s)
    psi = builder.build(grid, eps)

    idx_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_x, idx_y] > 0.99
    assert psi[0, 0] < 0.01


def test_shape_from_dict_unknown_type():
    with pytest.raises(ValueError, match="Unknown shape type"):
        shape_from_dict({"type": "annulus", "center": [0.5, 0.5]})


# ── 7. InitialConditionBuilder.from_dict ──────────────────────────────────────

def test_builder_from_dict(grid_2d):
    """from_dict should produce the same ψ as manual construction."""
    grid = grid_2d
    eps = _eps(grid)

    d = {
        "background_phase": "gas",
        "shapes": [
            {"type": "circle", "center": [0.5, 0.5], "radius": 0.2,
             "interior_phase": "liquid"},
        ],
    }
    psi_dict = InitialConditionBuilder.from_dict(d).build(grid, eps)

    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(Circle(center=(0.5, 0.5), radius=0.2, interior_phase="liquid"))
    psi_manual = builder.build(grid, eps)

    np.testing.assert_allclose(psi_dict, psi_manual)


def test_builder_from_dict_multiple_shapes(grid_2d):
    """from_dict with multiple shapes: two bubbles in liquid."""
    grid = grid_2d
    eps = _eps(grid)

    d = {
        "background_phase": "liquid",
        "shapes": [
            # 中心から各気泡境界まで距離 = 0.25 - 0.08 = 0.17 > 7ε → 中間点は液体 ψ > 0.99
            {"type": "circle", "center": [0.25, 0.5], "radius": 0.08,
             "interior_phase": "gas"},
            {"type": "circle", "center": [0.75, 0.5], "radius": 0.08,
             "interior_phase": "gas"},
        ],
    }
    psi = InitialConditionBuilder.from_dict(d).build(grid, eps)

    # 各気泡の中心 → 気体（SDF = -0.08; |φ/ε| ≈ 3.4 → ψ ≈ 0.032, threshold 0.05）
    for cx in (0.25, 0.75):
        ix = np.argmin(np.abs(grid.coords[0] - cx))
        iy = np.argmin(np.abs(grid.coords[1] - 0.5))
        assert psi[ix, iy] < 0.05, f"Bubble at ({cx}, 0.5): ψ = {psi[ix, iy]:.6f}"

    # 中間点 (0.5, 0.5): 最寄り気泡境界まで距離 = 0.25 - 0.08 = 0.17 ≈ 7ε → ψ > 0.99
    ix_mid = np.argmin(np.abs(grid.coords[0] - 0.5))
    iy_mid = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[ix_mid, iy_mid] > 0.99, (
        f"Between bubbles ψ = {psi[ix_mid, iy_mid]:.6f}, expected > 0.99"
    )


def test_builder_from_dict_multiple_objects_with_bubble_alias(grid_2d):
    """YAML-style objects can place multiple gas bubbles in liquid."""
    grid = grid_2d
    eps = _eps(grid)

    d = {
        "background_phase": "liquid",
        "objects": [
            {"type": "bubble", "center": [0.25, 0.5], "radius": 0.08},
            {"type": "bubble", "center": [0.75, 0.5], "radius": 0.08},
        ],
    }
    psi = InitialConditionBuilder.from_dict(d).build(grid, eps)

    for center_x in (0.25, 0.75):
        idx_x = np.argmin(np.abs(grid.coords[0] - center_x))
        idx_y = np.argmin(np.abs(grid.coords[1] - 0.5))
        assert psi[idx_x, idx_y] < 0.05

    idx_mid_x = np.argmin(np.abs(grid.coords[0] - 0.5))
    idx_mid_y = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert psi[idx_mid_x, idx_mid_y] > 0.99


def test_normalise_ic_dict_infers_liquid_background_for_objects_bubbles():
    normalised = normalise_ic_dict({
        "type": "objects",
        "objects": [
            {"type": "bubble", "center": [0.5, 0.5], "radius": 0.2},
        ],
    })

    assert normalised["background_phase"] == "liquid"
    assert "objects" in normalised


def test_builder_from_dict_rejects_mixed_shape_keys():
    with pytest.raises(ValueError, match="either 'shapes' or 'objects'"):
        InitialConditionBuilder.from_dict({"shapes": [], "objects": []})


# ── 8. background_phase='liquid' + 気体円 ─────────────────────────────────────

def test_liquid_background_no_shapes(grid_2d):
    """Liquid background with no shapes → all liquid."""
    grid = grid_2d
    eps = _eps(grid)
    psi = InitialConditionBuilder(background_phase="liquid").build(grid, eps)
    assert np.all(psi > 0.99), "All-liquid background failed"


def test_gas_background_no_shapes(grid_2d):
    """Gas background with no shapes → all gas."""
    grid = grid_2d
    eps = _eps(grid)
    psi = InitialConditionBuilder(background_phase="gas").build(grid, eps)
    assert np.all(psi < 0.01), "All-gas background failed"


# ── 9. SinusoidalInterface ────────────────────────────────────────────────────

def test_sinusoidal_interface_flat(grid_2d):
    """Flat sinusoidal interface (amplitude=0) behaves like a horizontal HalfSpace."""
    grid = grid_2d
    eps = _eps(grid)

    # 振幅 0: y < 0.5 が液体、y > 0.5 が気体
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(SinusoidalInterface(axis=1, mean=0.5, amplitude=0.0,
                                    wavelength=1.0, interior_phase="liquid"))
    psi = builder.build(grid, eps)

    # 液体側 (y = 0.1)
    ix = np.argmin(np.abs(grid.coords[0] - 0.5))
    iy_low = np.argmin(np.abs(grid.coords[1] - 0.1))
    assert psi[ix, iy_low] > 0.99, f"Low side ψ = {psi[ix, iy_low]:.6f}"

    # 気体側 (y = 0.9)
    iy_high = np.argmin(np.abs(grid.coords[1] - 0.9))
    assert psi[ix, iy_high] < 0.01, f"High side ψ = {psi[ix, iy_high]:.6f}"


def test_sinusoidal_interface_matches_rayleigh_taylor_ic(grid_2d):
    """SinusoidalInterface IC should match the hand-coded RT initial condition."""
    grid = grid_2d
    eps = _eps(grid)
    X, Y = grid.meshgrid()
    Lx = grid.L[0]  # = 1.0 for grid_2d

    # 手動 RT 初期条件（rayleigh_taylor.py と同じ式）
    y_interface = 0.5 + 0.05 * np.cos(2.0 * np.pi * X / Lx)  # 64x64 グリッドに合わせる
    dist = Y - y_interface
    psi_manual = 1.0 / (1.0 + np.exp(dist / eps))

    # SinusoidalInterface で同じ IC を生成
    builder = InitialConditionBuilder(background_phase="gas")
    builder.add(SinusoidalInterface(
        axis=1, mean=0.5, amplitude=0.05, wavelength=Lx, interior_phase="liquid"
    ))
    psi_shape = builder.build(grid, eps)

    np.testing.assert_allclose(
        psi_shape, psi_manual, rtol=1e-10, atol=1e-12,
        err_msg="SinusoidalInterface does not match manual RT IC formula"
    )


def test_sinusoidal_interface_from_dict(grid_2d):
    """shape_from_dict should deserialize sinusoidal_interface correctly."""
    grid = grid_2d
    eps = _eps(grid)

    d = {
        "type": "sinusoidal_interface",
        "axis": 1,
        "mean": 0.6,
        "amplitude": 0.05,
        "wavelength": 0.5,
        "interior_phase": "liquid",
    }
    s = shape_from_dict(d)
    assert isinstance(s, SinusoidalInterface)
    assert s.axis == 1
    assert s.mean == 0.6
    assert s.amplitude == 0.05
    assert s.wavelength == 0.5
    assert s.interior_phase == "liquid"

    # SDF: 下側 (y = 0.1) が液体
    X, Y = grid.meshgrid()
    phi = s.sdf(X, Y)
    # y=0.1 < 0.6 + small_perturbation → φ < 0 (interior = liquid)
    assert phi[0, 0] < 0, "Bottom-left node should be inside (φ < 0)"


def test_capillary_wave_from_dict_mode_phase_alias(grid_2d):
    """capillary_wave YAML should define a sinusoidal interface by mode."""
    grid = grid_2d

    s = shape_from_dict({
        "type": "capillary_wave",
        "axis": "y",
        "mean": 0.5,
        "amplitude": 0.02,
        "mode": 2,
        "length": 1.0,
        "phase": np.pi / 2.0,
        "interior_phase": "liquid",
    })

    assert isinstance(s, SinusoidalInterface)
    assert s.axis == 1
    assert s.wavelength == pytest.approx(0.5)
    assert s.phase == pytest.approx(np.pi / 2.0)

    X, Y = grid.meshgrid()
    phi = s.sdf(X, Y)
    ix = np.argmin(np.abs(grid.coords[0] - 0.0))
    iy = np.argmin(np.abs(grid.coords[1] - 0.5))
    assert phi[ix, iy] == pytest.approx(0.0, abs=grid.h[1])


def test_sinusoidal_interface_zalesak_slotted_disk(grid_2d):
    """Zalesak IC from YAML dict (circle + gas rectangle) matches expected shape."""
    grid = grid_2d
    eps = _eps(grid)

    d = {
        "background_phase": "gas",
        "shapes": [
            {"type": "circle", "center": [0.5, 0.75], "radius": 0.15,
             "interior_phase": "liquid"},
            {"type": "rectangle", "bounds": [[0.475, 0.525], [0.60, 0.90]],
             "interior_phase": "gas"},
        ],
    }
    psi = InitialConditionBuilder.from_dict(d).build(grid, eps)

    # 円内かつスロット外 (x=0.63, y=0.75): 円の右ウィング領域（ψ > 0.5 = 液体優勢）
    # スロット右端まで: 0.63 - 0.525 = 0.105 ≈ 4.5ε, 円境界まで: 0.15-0.13 = 0.02 ≈ 0.9ε
    # phi_final = max(-0.02, -0.105) = -0.02 → ψ ≈ 0.7 (液体優勢を確認)
    ix_off = np.argmin(np.abs(grid.coords[0] - 0.63))
    iy = np.argmin(np.abs(grid.coords[1] - 0.75))
    assert psi[ix_off, iy] > 0.5, f"Disk right-wing ψ = {psi[ix_off, iy]:.6f}, expected > 0.5"

    # スロット中心 (x=0.5, y=0.75): 円内かつスロット内 → 気体優勢 (ψ < 0.5)
    # 注: スロット半幅 0.025 ≈ ε=0.023 なので smooth Heaviside による遷移帯の影響あり
    ix_center = np.argmin(np.abs(grid.coords[0] - 0.5))
    iy_slot = np.argmin(np.abs(grid.coords[1] - 0.75))
    assert psi[ix_center, iy_slot] < 0.5, (
        f"Slot center ψ = {psi[ix_center, iy_slot]:.6f}, expected < 0.5 (gas-dominant)"
    )

    # ドメイン角 (0.0, 0.0) は気体背景
    assert psi[0, 0] < 0.01, f"Corner ψ = {psi[0, 0]:.6f}"

    # 円の外側 (0.5, 0.2): 気体背景
    ix_center = np.argmin(np.abs(grid.coords[0] - 0.5))
    iy_out = np.argmin(np.abs(grid.coords[1] - 0.2))
    assert psi[ix_center, iy_out] < 0.01, f"Outside disk ψ = {psi[ix_center, iy_out]:.6f}"


# ── 10. バリデーション ─────────────────────────────────────────────────────────

def test_invalid_background_phase():
    with pytest.raises(ValueError, match="background_phase"):
        InitialConditionBuilder(background_phase="water")


def test_invalid_interior_phase():
    with pytest.raises(ValueError, match="interior_phase"):
        Circle(center=(0.5, 0.5), radius=0.1, interior_phase="water")


def test_half_space_zero_normal():
    with pytest.raises(ValueError, match="non-zero"):
        HalfSpace(normal=(0.0, 0.0), offset=0.5)


# ── 11. VelocityField: RigidRotation ─────────────────────────────────────────

def test_rigid_rotation_center_velocity_zero(grid_2d):
    """At the rotation center, (u, v) should be (0, 0)."""
    grid = grid_2d
    X, Y = grid.meshgrid()
    vf = RigidRotation(center=(0.5, 0.5), period=1.0)
    u, v = vf.compute(X, Y)

    # 中心 (0.5, 0.5) に最も近いノード
    ix = np.argmin(np.abs(grid.coords[0] - 0.5))
    iy = np.argmin(np.abs(grid.coords[1] - 0.5))
    np.testing.assert_allclose(u[ix, iy], 0.0, atol=1e-10)
    np.testing.assert_allclose(v[ix, iy], 0.0, atol=1e-10)


def test_rigid_rotation_antisymmetry(grid_2d):
    """u(x, y) = -u(-x+1, y) and v(x, y) = -v(x, -y+1) about center (0.5, 0.5)."""
    grid = grid_2d
    X, Y = grid.meshgrid()
    vf = RigidRotation(center=(0.5, 0.5), period=1.0)
    u, v = vf.compute(X, Y)

    # u は y 方向の反対称: u(x, y) = -u(x, 1-y) for center=0.5
    np.testing.assert_allclose(u, -u[:, ::-1], atol=1e-12)
    # v は x 方向の反対称: v(x, y) = -v(1-x, y)
    np.testing.assert_allclose(v, -v[::-1, :], atol=1e-12)


def test_rigid_rotation_speed_proportional_to_radius(grid_2d):
    """Speed |u| = ω r must be proportional to distance from center."""
    grid = grid_2d
    X, Y = grid.meshgrid()
    cx, cy = 0.5, 0.5
    period = 2.0
    vf = RigidRotation(center=(cx, cy), period=period)
    u, v = vf.compute(X, Y)

    speed = np.sqrt(u ** 2 + v ** 2)
    r = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    omega = 2.0 * np.pi / period
    np.testing.assert_allclose(speed, omega * r, rtol=1e-10)


def test_rigid_rotation_from_dict():
    """velocity_field_from_dict should produce a RigidRotation with correct params."""
    d = {"type": "rigid_rotation", "center": [0.5, 0.5], "period": 2.0}
    vf = velocity_field_from_dict(d)
    assert isinstance(vf, RigidRotation)
    assert vf.center == (0.5, 0.5)
    assert vf.period == 2.0


# ── 12. VelocityField: UniformFlow ───────────────────────────────────────────

def test_uniform_flow_constant_value(grid_2d):
    """UniformFlow returns arrays filled with the prescribed velocity."""
    grid = grid_2d
    X, Y = grid.meshgrid()
    vf = UniformFlow(velocity=(1.5, -0.3))
    u, v = vf.compute(X, Y)

    np.testing.assert_allclose(u, 1.5, rtol=1e-12)
    np.testing.assert_allclose(v, -0.3, rtol=1e-12)
    assert u.shape == X.shape
    assert v.shape == Y.shape


def test_uniform_flow_from_dict():
    """velocity_field_from_dict should produce a UniformFlow with correct velocity."""
    d = {"type": "uniform", "velocity": [2.0, -1.0]}
    vf = velocity_field_from_dict(d)
    assert isinstance(vf, UniformFlow)
    assert vf.velocity == (2.0, -1.0)


def test_velocity_field_from_dict_unknown_type():
    with pytest.raises(ValueError, match="Unknown velocity_field type"):
        velocity_field_from_dict({"type": "vortex"})


def test_velocity_field_from_dict_no_type():
    with pytest.raises(ValueError, match="'type' key"):
        velocity_field_from_dict({"center": [0.5, 0.5]})


# ── 13. RigidRotation バリデーション ──────────────────────────────────────────

def test_rigid_rotation_invalid_center():
    with pytest.raises(ValueError, match="2-element"):
        RigidRotation(center=(0.5, 0.5, 0.5), period=1.0)


def test_rigid_rotation_invalid_period():
    with pytest.raises(ValueError, match="positive"):
        RigidRotation(center=(0.5, 0.5), period=0.0)
